from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    AssessInteroperabilityPreviewReadinessRequest,
    ExportInteroperabilityPreviewRequest,
    ExportInteroperabilityRemediationBundleRequest,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_interoperability_remediation_cases(repo_root: Path) -> dict:
    from dietary_mcp.readiness_validation import _build_example_dossier

    cases_payload = json.loads((_validation_root(repo_root) / "interoperability_remediation_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []
    for case in cases_payload["cases"]:
        dossier = _build_example_dossier(runtime, case["scenario"])
        if case.get("omitModelGovernanceSnapshot"):
            dossier = dossier.model_copy(update={"model_governance_snapshot": None})
        preview = runtime.export_interoperability_preview(
            ExportInteroperabilityPreviewRequest(
                dossier=dossier,
                target_profile="oht_85_iuclid_json_preview",
            )
        )
        assessment = runtime.assess_interoperability_preview_readiness(
            AssessInteroperabilityPreviewReadinessRequest(
                dossier=dossier,
                preview=preview,
                target_profile=case["targetProfile"],
            )
        )
        bundle = runtime.export_interoperability_remediation_bundle(
            ExportInteroperabilityRemediationBundleRequest(
                dossier=dossier,
                preview=preview,
                assessment=assessment,
            )
        )
        action_ids = [item.action_id for item in bundle.action_items]
        status = (
            "ok"
            if bundle.overall_status.value == case["expectedOverallStatus"]
            and bundle.blocking_action_count == case["expectedBlockingActionCount"]
            and bundle.warning_action_count == case["expectedWarningActionCount"]
            and action_ids == case["expectedActionIds"]
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedOverallStatus": case["expectedOverallStatus"],
                "observedOverallStatus": bundle.overall_status.value,
                "expectedBlockingActionCount": case["expectedBlockingActionCount"],
                "observedBlockingActionCount": bundle.blocking_action_count,
                "expectedWarningActionCount": case["expectedWarningActionCount"],
                "observedWarningActionCount": bundle.warning_action_count,
                "expectedActionIds": case["expectedActionIds"],
                "observedActionIds": action_ids,
            }
        )
    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
