from __future__ import annotations

import pytest

from dietary_mcp.__main__ import validate_transport_security
from dietary_mcp.server import create_server
from dietary_mcp.transport.http import (
    RequestBodyLimitMiddleware,
    build_transport_security_settings,
    max_request_bytes,
)


def test_stdio_transport_is_allowed_by_default() -> None:
    validate_transport_security("stdio")


def test_http_transports_fail_closed_without_explicit_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DIETARY_MCP_ALLOW_UNAUTHENTICATED_HTTP", raising=False)
    with pytest.raises(SystemExit, match="Refusing to start unauthenticated"):
        validate_transport_security("streamable-http")


def test_http_transports_can_be_overridden_for_authenticated_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DIETARY_MCP_ALLOW_UNAUTHENTICATED_HTTP", "true")
    validate_transport_security("sse")


def test_http_transport_defaults_to_local_dns_rebinding_allowlists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DIETARY_MCP_ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("DIETARY_MCP_ALLOWED_ORIGINS", raising=False)

    settings = build_transport_security_settings()

    assert settings.enable_dns_rebinding_protection is True
    assert settings.allowed_hosts == ["localhost:*", "127.0.0.1:*", "[::1]:*"]
    assert settings.allowed_origins == [
        "http://localhost:*",
        "http://127.0.0.1:*",
        "http://[::1]:*",
    ]


def test_http_transport_uses_explicit_gateway_allowlists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DIETARY_MCP_ALLOWED_HOSTS", "mcp.example.test, internal.example.test:8443")
    monkeypatch.setenv("DIETARY_MCP_ALLOWED_ORIGINS", "https://app.example.test")

    settings = build_transport_security_settings()
    server = create_server(stateless_http=True, transport_security=settings)

    assert settings.allowed_hosts == ["mcp.example.test", "internal.example.test:8443"]
    assert settings.allowed_origins == ["https://app.example.test"]
    assert server.settings.stateless_http is True
    assert server.settings.transport_security == settings


@pytest.mark.parametrize("name", ["DIETARY_MCP_ALLOWED_HOSTS", "DIETARY_MCP_ALLOWED_ORIGINS"])
def test_http_transport_rejects_empty_allowlists(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    monkeypatch.setenv(name, " , ")
    with pytest.raises(SystemExit, match="at least one explicit allowlisted value"):
        build_transport_security_settings()


def test_http_transport_defaults_to_one_megabyte_request_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DIETARY_MCP_MAX_REQUEST_BYTES", raising=False)
    assert max_request_bytes() == 1_048_576


@pytest.mark.parametrize("value", ["0", "-1", "not-an-integer"])
def test_http_transport_rejects_invalid_request_limits(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("DIETARY_MCP_MAX_REQUEST_BYTES", value)
    with pytest.raises(SystemExit, match="positive integer"):
        max_request_bytes()


@pytest.mark.anyio
async def test_http_transport_rejects_oversized_chunked_body_before_dispatch() -> None:
    dispatched = False

    async def inner_app(scope, receive, send) -> None:
        nonlocal dispatched
        dispatched = True

    requests = [
        {"type": "http.request", "body": b"1234", "more_body": True},
        {"type": "http.request", "body": b"5678", "more_body": False},
    ]
    responses = []

    async def receive():
        return requests.pop(0)

    async def send(message) -> None:
        responses.append(message)

    middleware = RequestBodyLimitMiddleware(inner_app, limit=7)
    await middleware({"type": "http", "headers": []}, receive, send)

    assert dispatched is False
    assert responses[0]["status"] == 413


@pytest.mark.anyio
@pytest.mark.parametrize("content_length", [b"-1", b"not-an-integer"])
async def test_http_transport_rejects_invalid_content_length(content_length: bytes) -> None:
    dispatched = False

    async def inner_app(scope, receive, send) -> None:
        nonlocal dispatched
        dispatched = True

    responses = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message) -> None:
        responses.append(message)

    middleware = RequestBodyLimitMiddleware(inner_app, limit=7)
    await middleware(
        {"type": "http", "headers": [(b"content-length", content_length)]},
        receive,
        send,
    )

    assert dispatched is False
    assert responses[0]["status"] == 400


@pytest.mark.anyio
async def test_http_transport_replays_bounded_body_to_mcp_app() -> None:
    received_body = b""

    async def inner_app(scope, receive, send) -> None:
        nonlocal received_body
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            received_body += message.get("body", b"")
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    requests = [{"type": "http.request", "body": b"1234567", "more_body": False}]
    responses = []

    async def receive():
        return requests.pop(0)

    async def send(message) -> None:
        responses.append(message)

    middleware = RequestBodyLimitMiddleware(inner_app, limit=7)
    await middleware({"type": "http", "headers": []}, receive, send)

    assert received_body == b"1234567"
    assert responses[0]["status"] == 204
