from pathlib import Path

from dietary_mcp.tool_surface_validation import run_tool_surface_cases


def test_tool_surface_validation_cases_pass() -> None:
    results = run_tool_surface_cases(Path(__file__).resolve().parents[1])

    assert results["status"] == "ok"
    assert {case["name"] for case in results["cases"]} >= {
        "tool_count",
        "all_tools_have_titles",
        "all_tools_have_output_schemas",
        "tool_read_only_annotations_match_policy",
        "tool_idempotent_annotations_match_policy",
        "all_tools_include_structured_error_payload",
    }
    assert all(case["status"] == "ok" for case in results["cases"])
