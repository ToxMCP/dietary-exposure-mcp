from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    AssessInteroperabilityPreviewReadinessRequest,
    ExportInteroperabilityPreviewRequest,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_interoperability_readiness_cases(repo_root: Path) -> dict:
    from dietary_mcp.readiness_validation import _build_example_dossier

    cases_payload = json.loads((_validation_root(repo_root) / "interoperability_readiness_cases.json").read_text())
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
        blocking_rule_ids = sorted(item.rule_id for item in assessment.blocking_rules)
        warning_rule_ids = sorted(item.rule_id for item in assessment.warning_rules)
        expected_blocking = sorted(case.get("expectedBlockingRuleIds", []))
        expected_warning = sorted(case.get("expectedWarningRuleIds", []))
        status = (
            "ok"
            if assessment.overall_status.value == case["expectedOverallStatus"]
            and blocking_rule_ids == expected_blocking
            and warning_rule_ids == expected_warning
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedOverallStatus": case["expectedOverallStatus"],
                "observedOverallStatus": assessment.overall_status.value,
                "expectedBlockingRuleIds": expected_blocking,
                "observedBlockingRuleIds": blocking_rule_ids,
                "expectedWarningRuleIds": expected_warning,
                "observedWarningRuleIds": warning_rule_ids,
            }
        )
    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
