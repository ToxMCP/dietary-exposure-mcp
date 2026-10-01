"""Collect real-client contracts and calculations using either SDK generation.

Run this script with an isolated SDK 1.30 client interpreter for legacy proof,
or SDK 2.2 with --modern. It never imports the Dietary server into the client.
The server can be an installed wheel, a source checkout, or a running HTTP app.
"""

from __future__ import annotations

import argparse
import json
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def stable(value):
    """Remove only declared per-invocation timestamps and trace IDs."""
    if isinstance(value, dict):
        return {key: stable(item) for key, item in value.items()
                if key not in {"generated_at", "generatedAt", "executed_at", "executedAt", "requestId"}}
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value


@asynccontextmanager
async def connection(args):
    server = args.url or StdioServerParameters(
        command=args.server_python, args=["-m", "dietary_mcp"],
        env={"PYTHONPATH": str(Path(args.server_root) / "src")} if args.server_root else {},
    )
    if args.modern:
        from mcp import Client

        async with Client(server) as client:
            yield client, client.protocol_version
    else:
        if args.url:
            from mcp.client.streamable_http import streamablehttp_client

            transport = streamablehttp_client(args.url)
        else:
            transport = stdio_client(server)
        async with transport as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                initialized = await session.initialize()
                wire = initialized.model_dump(mode="json", by_alias=True)
                yield session, wire["protocolVersion"]


async def collect(args):
    fixtures = Path(args.fixtures)
    async with connection(args) as (client, protocol):
        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        catalog = {
            "tools": [item.model_dump(mode="json", by_alias=True, exclude_none=True)
                      for item in tools.tools],
            "resources": [item.model_dump(mode="json", by_alias=True, exclude_none=True)
                          for item in resources.resources],
            "templates": [item.model_dump(mode="json", by_alias=True, exclude_none=True)
                          for item in getattr(templates, "resource_templates", [])]
                         if args.modern else templates.model_dump(
                             mode="json", by_alias=True, exclude_none=True)["resourceTemplates"],
        }
        results = {}

        async def call(name, request):
            response = await client.call_tool(name, {"request": request})
            wire = response.model_dump(mode="json", by_alias=True)
            assert wire["isError"] is False, (name, wire)
            # Both representations must continue to carry the same payload.
            structured = wire["structuredContent"]
            assert stable(json.loads(wire["content"][0]["text"])) == stable(structured["result"])
            results[name] = stable(structured)
            return structured["result"]

        for name, fixture in [
            ("dietary_lookup_reference_values", "lookupReferenceValuesRequest"),
            ("dietary_build_probabilistic_intake_summary", "buildProbabilisticIntakeSummaryRequest"),
            ("dietary_build_uncertainty_intake_assessment", "buildUncertaintyIntakeAssessmentRequest"),
            ("dietary_export_metals_monitoring_interpretation_bundle",
             "exportMetalsMonitoringInterpretationBundleRequest"),
        ]:
            await call(name, json.loads((fixtures / f"{fixture}.v1.json").read_text()))
        scenario = json.loads((fixtures / "dietaryIntakeScenarioDefinition.v1.json").read_text())
        summary = await call("dietary_build_bounded_intake_summary", {"scenario": scenario})
        await call("dietary_export_pbpk_oral_input", {"scenario": scenario, "summary": summary})
        await call("dietary_export_toxclaw_dietary_evidence_bundle",
                   {"scenario": scenario, "summary": summary})
        failed = await client.call_tool("dietary_select_consumption_profile", {"request": {
            "population_group": "invalid", "intake_window": "chronic"}})
        failed = failed.model_dump(mode="json", by_alias=True)
        assert failed["isError"] is True
        assert failed["structuredContent"]["result"]["code"] == "missing_consumption_profile"
        assert failed["structuredContent"]["result"]["details"]["requestId"]
        results["domain_error"] = stable(failed["structuredContent"])
        resource = await client.read_resource("defaults://manifest")
        results["defaults_manifest"] = resource.model_dump(mode="json", by_alias=True)["contents"]
    return {"clientSdk": version("mcp"), "protocol": protocol, "catalog": catalog,
            "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-python")
    parser.add_argument("--server-root")
    parser.add_argument("--url")
    parser.add_argument("--modern", action="store_true")
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not args.url and not args.server_python:
        parser.error("--url or --server-python is required")
    result = anyio.run(collect, args)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"clientSdk": result["clientSdk"], "protocol": result["protocol"],
                      "tools": len(result["catalog"]["tools"]),
                      "resources": len(result["catalog"]["resources"]),
                      "calculations": len(result["results"]) - 2}))


if __name__ == "__main__":
    main()
