"""Modern HTTP security, stateless routing, and worker-thread isolation gates."""

from __future__ import annotations

import hashlib
import json
import time
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import anyio
from mcp import Client
from mcp.server import MCPServer
from starlette.testclient import TestClient

from dietary_mcp.server import create_server
from dietary_mcp.transport.http import create_http_app


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "2026-07-28"


def _request(method, params=None, request_id=1):
    params = {**(params or {}), "_meta": {"io.modelcontextprotocol/protocolVersion": PROTOCOL,
               "io.modelcontextprotocol/clientCapabilities": {}}}
    body = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    headers = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": PROTOCOL,
               "Mcp-Method": method}
    if method in {"tools/call", "resources/read"}:
        headers["Mcp-Name"] = params.get("name", params.get("uri", ""))
    return body, headers


def _post(client, method, params=None, request_id=1):
    body, headers = _request(method, params, request_id)
    return client.post("/mcp", json=body, headers=headers)


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("DIETARY_MCP_ALLOW_UNAUTHENTICATED_HTTP", "true")
    return create_http_app()


def test_modern_http_needs_no_initialize_or_session_and_has_private_catalog_hints(app):
    with TestClient(app, base_url="http://localhost:8000") as client:
        tools = _post(client, "tools/list")
        assert tools.status_code == 200
        assert "mcp-session-id" not in tools.headers
        result = tools.json()["result"]
        assert len(result["tools"]) == 49
        assert result["ttlMs"] == 60_000
        assert result["cacheScope"] == "private"
        resources = _post(client, "resources/list").json()["result"]
        assert len(resources["resources"]) == 34
        assert resources["cacheScope"] == "private"
        discovered = _post(client, "server/discover")
        assert discovered.status_code == 200
        assert PROTOCOL in discovered.json()["result"]["supportedVersions"]


@pytest.mark.parametrize("header,value", [("Mcp-Method", "resources/list"),
                                         ("Mcp-Name", "other_tool"),
                                         ("Mcp-Method", None), ("Mcp-Name", None)])
def test_modern_http_rejects_missing_or_mismatched_headers(app, header, value):
    body, headers = _request("tools/call", {"name": "dietary_lookup_reference_values",
                            "arguments": {"request": {"substanceKey": "glyphosate"}}})
    if value is None:
        headers.pop(header)
    else:
        headers[header] = value
    with TestClient(app, base_url="http://localhost:8000") as client:
        response = client.post("/mcp", json=body, headers=headers)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == -32020


@pytest.mark.parametrize("header,value,status", [("Host", "attacker.example", 421),
                                                ("Origin", "https://attacker.example", 403)])
def test_modern_http_rejects_untrusted_host_or_origin(app, header, value, status):
    body, headers = _request("tools/list")
    headers[header] = value
    with TestClient(app, base_url="http://localhost:8000") as client:
        assert client.post("/mcp", json=body, headers=headers).status_code == status


def test_modern_http_rejects_malformed_unknown_and_oversized_requests(app):
    with TestClient(app, base_url="http://localhost:8000") as client:
        _, headers = _request("tools/list")
        malformed = client.post("/mcp", content="{", headers={**headers,
                                "Content-Type": "application/json"})
        assert malformed.status_code == 400
        assert malformed.json()["error"]["code"] == -32700
        unknown = _post(client, "unknown/method")
        assert unknown.status_code == 404
        assert unknown.json()["error"]["code"] == -32601
        oversized = client.post("/mcp", content=b"x" * (1_048_576 + 1), headers=headers)
        assert oversized.status_code == 413
        assert _post(client, "tools/list").status_code == 200


def test_modern_http_domain_errors_retain_wire_contract_and_unique_trace_ids(app):
    with TestClient(app, base_url="http://localhost:8000") as client:
        ids = set()
        for _ in range(2):
            result = _post(client, "tools/call", {"name": "dietary_select_consumption_profile",
                           "arguments": {"request": {"population_group": "invalid",
                           "intake_window": "chronic"}}}).json()["result"]
            assert result["isError"] is True
            error = result["structuredContent"]["result"]
            assert error["code"] == "missing_consumption_profile"
            assert json.loads(result["content"][0]["text"]) == error
            ids.add(error["details"]["requestId"])
        assert len(ids) == 2


def _stable(value):
    if isinstance(value, dict):
        return {key: _stable(item) for key, item in value.items()
                if key not in {"generated_at", "generatedAt", "requestId"}}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def test_concurrent_seeded_calculations_and_exports_are_isolated_and_do_not_write(app):
    fixture_names = {
        "dietary_lookup_reference_values": "lookupReferenceValuesRequest",
        "dietary_build_probabilistic_intake_summary": "buildProbabilisticIntakeSummaryRequest",
        "dietary_export_metals_monitoring_interpretation_bundle": "exportMetalsMonitoringInterpretationBundleRequest",
    }
    jobs = []
    for tool, fixture in fixture_names.items():
        request = json.loads((ROOT / "schemas/examples" / f"{fixture}.v1.json").read_text())
        jobs.append((tool, request))
    tracked = [ROOT / "docs/contracts/schemas/manifest.json", ROOT / "defaults/manifest.json"]
    before = [(path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
              for path in tracked]
    with TestClient(app, base_url="http://localhost:8000") as client:
        def run(job):
            tool, request = job
            # Reusing an ID on independent requests must not reuse another result.
            response = _post(client, "tools/call", {"name": tool,
                             "arguments": {"request": request}}, request_id=7)
            assert response.status_code == 200
            result = response.json()["result"]
            assert result["isError"] is False
            return _stable(result["structuredContent"])

        expected = [run(job) for job in jobs]
        with ThreadPoolExecutor(max_workers=6) as pool:
            observed = list(pool.map(run, jobs * 4))
        assert observed == expected * 4
    assert before == [(path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
                      for path in tracked]


def test_stateless_modern_and_legacy_calls_can_move_between_two_independent_apps(monkeypatch):
    monkeypatch.setenv("DIETARY_MCP_ALLOW_UNAUTHENTICATED_HTTP", "true")
    with (TestClient(create_http_app(create_server()), base_url="http://localhost:8000") as first,
          TestClient(create_http_app(create_server()), base_url="http://localhost:8000") as second):
        initialized = first.post("/mcp", headers={"Accept": "application/json, text/event-stream"},
                                 json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                       "params": {"protocolVersion": "2025-11-25",
                                                  "capabilities": {}, "clientInfo": {
                                                      "name": "legacy", "version": "1"}}})
        assert initialized.status_code == 200
        assert "mcp-session-id" not in initialized.headers
        old = second.post("/mcp", headers={"Accept": "application/json, text/event-stream",
                          "MCP-Protocol-Version": "2025-11-25"},
                          json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert old.status_code == 200
        assert len(old.json()["result"]["tools"]) == 49
        assert _post(first, "server/discover").status_code == 200
        assert _post(second, "tools/list").status_code == 200


@pytest.mark.anyio
async def test_cancelled_modern_call_does_not_poison_later_requests():
    server = MCPServer("cancellation-regression")
    started = anyio.Event()
    finished = anyio.Event()

    @server.tool()
    async def slow() -> str:
        started.set()
        try:
            await anyio.sleep(30)
        finally:
            finished.set()
        return "late"

    @server.tool()
    async def fast() -> str:
        return "healthy"

    async with Client(server) as client:
        assert client.protocol_version == PROTOCOL
        async def cancelled_call():
            await client.call_tool("slow", {})
        async with anyio.create_task_group() as group:
            group.start_soon(cancelled_call)
            await started.wait()
            group.cancel_scope.cancel()
        with anyio.fail_after(2):
            await finished.wait()
        healthy = await client.call_tool("fast", {})
        assert healthy.structured_content == {"result": "healthy"}


def test_parallel_release_resource_reads_do_not_duplicate_report_cache_fills(app, monkeypatch):
    from dietary_mcp import server_resources
    guard = Lock()
    active = 0
    peak = 0

    def reports(root):
        nonlocal active, peak
        with guard:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        with guard:
            active -= 1
        return {"metadata-report": {"version": "test"}}

    monkeypatch.setattr(server_resources, "build_release_reports", reports)
    with TestClient(app, base_url="http://localhost:8000") as client:
        def read(_):
            response = _post(client, "resources/read", {"uri": "release://metadata-report"})
            assert response.status_code == 200
            return json.loads(response.json()["result"]["contents"][0]["text"])
        with ThreadPoolExecutor(max_workers=4) as pool:
            assert list(pool.map(read, range(8))) == [{"version": "test"}] * 8
    assert peak == 1
