"""Track-A mcp-conformance baseline gate (ADVISORY CI signal).

Spawns the BUILT server entrypoint in a FRESH PROCESS over stdio using the
real MCP client SDK (``mcp.client.stdio.stdio_client`` + ``ClientSession``),
calls ``list_tools`` / ``list_resources``, and asserts the advertised tool-name
set (and resource-URI set) exactly equals an expected checked-in set.

This is intentionally an END-TO-END, cross-process check: unlike the in-process
``tests/test_server_surface.py`` / ``tests/test_tool_surface_validation.py``
(which call ``create_server()`` / ``register_tools()`` and inspect the FastMCP
object directly), this gate exercises the actual stdio transport, the packaged
``dietary-mcp`` console entrypoint, and JSON-RPC ``initialize`` handshake exactly
as a real MCP host would. It catches regressions the in-process tests cannot:
a broken entrypoint, a transport/packaging break, or a stdout-pollution bug that
corrupts the JSON-RPC stream.

MAINTAINERS: ``EXPECTED_TOOL_NAMES`` and ``EXPECTED_RESOURCE_URIS`` below are
hand-maintained literals of the CURRENT registered surface. When you add,
remove, or rename a tool/resource you MUST update these sets in the same change
(the in-process ``test_server_surface.py`` set must move with it). A mismatch
here is a deliberate, attributed failure that surfaces undeclared surface drift.
"""

from __future__ import annotations

import sys
from pathlib import Path

import anyio

# Real MCP client SDK — the proven fleet-reference Python conformance form.
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dietary_mcp.package_metadata import PACKAGE_NAME, VERSION


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# --- Expected runtime surface (hand-maintained literals; keep in sync) --------
EXPECTED_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "dietary_build_residue_profile",
        "dietary_select_consumption_profile",
        "dietary_build_dietary_intake_scenario",
        "dietary_build_bounded_intake_summary",
        "dietary_compare_dietary_scenarios",
        "dietary_assess_residue_evidence_fit",
        "dietary_apply_residue_evidence",
        "dietary_reconcile_residue_evidence",
        "dietary_evaluate_global_trade_risk",
        "dietary_parse_raw_survey_dataset",
        "dietary_summarize_survey_distribution",
        "dietary_build_probabilistic_intake_summary",
        "dietary_build_uncertainty_intake_assessment",
        "dietary_check_adapter_import",
        "dietary_check_contaminant_monitoring_import",
        "dietary_compare_adapter_import_to_walkthrough",
        "dietary_export_adapter_review_bundle",
        "dietary_export_trade_risk_review_bundle",
        "dietary_export_contaminant_monitoring_interpretation_bundle",
        "dietary_export_contaminant_monitoring_signoff_packet",
        "dietary_export_version_pinned_contaminant_monitoring_review_dossier",
        "dietary_export_version_pinned_adapter_review_dossier",
        "dietary_export_version_pinned_trade_risk_review_dossier",
        "dietary_export_sanitised_public_review_dossier",
        "dietary_export_interoperability_preview",
        "dietary_assess_interoperability_preview_readiness",
        "dietary_export_interoperability_remediation_bundle",
        "dietary_export_interoperability_signoff_packet",
        "dietary_assess_review_dossier_readiness",
        "dietary_export_scientific_follow_up_queue_bundle",
        "dietary_export_scientific_follow_up_review_board",
        "dietary_export_scientific_follow_up_owner_handoff_packet",
        "dietary_export_scientific_follow_up_owner_remediation_packet",
        "dietary_export_scientific_follow_up_owner_signoff_packet",
        "dietary_export_version_pinned_scientific_follow_up_owner_signoff_dossier",
        "dietary_lookup_reference_values",
        "dietary_lookup_contaminant_legal_limits",
        "dietary_lookup_method_support",
        "dietary_lookup_consumption_dataset_support",
        "dietary_lookup_reporting_profiles",
        "dietary_lookup_occurrence_evidence",
        "dietary_lookup_analytical_method_evidence",
        "dietary_lookup_metals_occurrence",
        "dietary_lookup_metals_review_focus",
        "dietary_export_metals_monitoring_interpretation_bundle",
        "dietary_export_metals_monitoring_signoff_packet",
        "dietary_export_version_pinned_metals_monitoring_review_dossier",
        "dietary_export_pbpk_oral_input",
        "dietary_export_toxclaw_dietary_evidence_bundle",
    }
)

EXPECTED_RESOURCE_URIS: frozenset[str] = frozenset(
    {
        "adapter-manifest://manifest",
        "adapter-input-templates://manifest",
        "adapter-import-walkthroughs://manifest",
        "contracts://manifest",
        "defaults://manifest",
        "source-catalog://manifest",
        "reference-values://manifest",
        "mrl-enforcement://manifest",
        "contaminant-legal-limits://manifest",
        "consumption-datasets://manifest",
        "method-registry://manifest",
        "legal-authorities://manifest",
        "reporting-profiles://manifest",
        "occurrence-evidence://manifest",
        "analytical-method-evidence://manifest",
        "metals-occurrence://manifest",
        "metals-review-focus://manifest",
        "emerging-contaminants://manifest",
        "jurisdiction-coverage://manifest",
        "model-governance://manifest",
        "consumption-profiles://manifest",
        "commodity-taxonomy://manifest",
        "food-vocabulary://manifest",
        "interoperability://manifest",
        "interoperability-readiness://manifest",
        "interoperability-remediation://catalog",
        "validation://manifest",
        "validation://interoperability-rules",
        "validation://interoperability-readiness-profiles",
        "validation://interoperability-remediation-actions",
        "validation://regulatory-rules",
        "validation://sanitisation-rules",
        "validation://interoperability-profiles",
        "validation://readiness-profiles",
    }
)


def _server_params() -> StdioServerParameters:
    # Spawn the SAME interpreter running the package entrypoint module. Using
    # ``-m dietary_mcp`` (rather than the bare ``dietary-mcp`` console script)
    # keeps the test runnable even when the console script is not on PATH,
    # while still launching the real, fully-built server over stdio.
    # Pass the src-layout path explicitly. Python 3.12.13 on macOS skips .pth
    # files carrying the filesystem hidden flag, which uv applies to .venv;
    # relying on an editable-install .pth would make this process test depend
    # on an unrelated local filesystem attribute. The release gate separately
    # smoke-installs and imports the built wheel in a clean environment.
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "dietary_mcp"],
        env={"PYTHONPATH": str(PROJECT_ROOT / "src")},
        cwd=PROJECT_ROOT,
    )


async def _collect_surface() -> tuple[set[str], set[str], str, str]:
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            resources = await session.list_resources()
    tool_names = {tool.name for tool in tools.tools}
    resource_uris = {str(resource.uri) for resource in resources.resources}
    return tool_names, resource_uris, initialized.serverInfo.name, initialized.serverInfo.version


def test_built_server_advertises_expected_tool_surface_over_stdio() -> None:
    tool_names, resource_uris, server_name, server_version = anyio.run(_collect_surface)

    assert server_name == PACKAGE_NAME
    assert server_version == VERSION

    missing = EXPECTED_TOOL_NAMES - tool_names
    unexpected = tool_names - EXPECTED_TOOL_NAMES
    assert not missing and not unexpected, (
        "listTools surface drift from the built server spawned over stdio.\n"
        f"  missing (expected, not advertised): {sorted(missing)}\n"
        f"  unexpected (advertised, not expected): {sorted(unexpected)}\n"
        "If this change is intentional, update EXPECTED_TOOL_NAMES in this file "
        "AND the expected set in tests/test_server_surface.py."
    )
    assert len(tool_names) == len(EXPECTED_TOOL_NAMES)

    missing_res = EXPECTED_RESOURCE_URIS - resource_uris
    unexpected_res = resource_uris - EXPECTED_RESOURCE_URIS
    assert not missing_res and not unexpected_res, (
        "listResources surface drift from the built server spawned over stdio.\n"
        f"  missing: {sorted(missing_res)}\n"
        f"  unexpected: {sorted(unexpected_res)}\n"
        "If intentional, update EXPECTED_RESOURCE_URIS here AND test_server_surface.py."
    )
