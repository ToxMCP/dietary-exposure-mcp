from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anyio


EXPECTED_TOOL_COUNT = 49


def _case(name: str, status: str, observed: Any) -> dict[str, Any]:
    return {"name": name, "status": status, "observed": observed}


async def _list_tools() -> list[Any]:
    from mcp.server.fastmcp import FastMCP

    from dietary_mcp.assets import runtime_asset_root
    from dietary_mcp.package_metadata import PACKAGE_NAME
    from dietary_mcp.runtime import DietaryRuntime
    from dietary_mcp.server_tools import register_tools

    server = FastMCP(PACKAGE_NAME, json_response=True)
    register_tools(server, DietaryRuntime(runtime_asset_root()))
    return list(await server.list_tools())


def _annotation_value(tool: Any, field_name: str) -> Any:
    annotations = getattr(tool, "annotations", None)
    if annotations is None:
        return None
    return getattr(annotations, field_name, None)


def _output_schema_text(tool: Any) -> str:
    return json.dumps(getattr(tool, "outputSchema", {}) or {}, sort_keys=True, default=str)


def _has_structured_error_union(tool: Any) -> bool:
    schema_text = _output_schema_text(tool)
    return all(token in schema_text for token in ("code", "message", "suggestion", "details"))


def run_tool_surface_cases(repo_root: Path) -> dict[str, Any]:
    del repo_root
    tools = anyio.run(_list_tools)
    tool_names = [tool.name for tool in tools]
    cases = [
        _case(
            "tool_count",
            "ok" if len(tools) == EXPECTED_TOOL_COUNT else "review_required",
            len(tools),
        ),
        _case(
            "tool_names_are_dietary_scoped",
            "ok" if all(name.startswith("dietary_") for name in tool_names) else "review_required",
            tool_names,
        ),
        _case(
            "all_tools_have_titles",
            "ok" if all(getattr(tool, "title", None) for tool in tools) else "review_required",
            [tool.name for tool in tools if not getattr(tool, "title", None)],
        ),
        _case(
            "all_tools_have_output_schemas",
            "ok" if all(getattr(tool, "outputSchema", None) for tool in tools) else "review_required",
            [tool.name for tool in tools if not getattr(tool, "outputSchema", None)],
        ),
        _case(
            "tool_read_only_annotations_match_policy",
            "ok"
            if all(_annotation_value(tool, "readOnlyHint") is True for tool in tools)
            else "review_required",
            [
                tool.name
                for tool in tools
                if _annotation_value(tool, "readOnlyHint") is not True
            ],
        ),
        _case(
            "all_tools_are_non_destructive",
            "ok"
            if all(_annotation_value(tool, "destructiveHint") is False for tool in tools)
            else "review_required",
            [tool.name for tool in tools if _annotation_value(tool, "destructiveHint") is not False],
        ),
        _case(
            "tool_idempotent_annotations_match_policy",
            "ok"
            if all(_annotation_value(tool, "idempotentHint") is True for tool in tools)
            else "review_required",
            [
                tool.name
                for tool in tools
                if _annotation_value(tool, "idempotentHint") is not True
            ],
        ),
        _case(
            "all_tools_are_closed_world",
            "ok" if all(_annotation_value(tool, "openWorldHint") is False for tool in tools) else "review_required",
            [tool.name for tool in tools if _annotation_value(tool, "openWorldHint") is not False],
        ),
        _case(
            "all_tools_include_structured_error_payload",
            "ok" if all(_has_structured_error_union(tool) for tool in tools) else "review_required",
            [tool.name for tool in tools if not _has_structured_error_union(tool)],
        ),
    ]
    return {
        "status": "ok" if all(case["status"] == "ok" for case in cases) else "review_required",
        "cases": cases,
    }
