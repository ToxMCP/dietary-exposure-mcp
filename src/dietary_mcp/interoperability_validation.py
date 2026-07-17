from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import ExportInteroperabilityPreviewRequest
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_interoperability_preview_cases(repo_root: Path) -> dict:
    from dietary_mcp.readiness_validation import _build_example_dossier

    cases_payload = json.loads((_validation_root(repo_root) / "interoperability_preview_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []
    for case in cases_payload["cases"]:
        dossier = _build_example_dossier(runtime, case["scenario"])
        if case.get("omitModelGovernanceSnapshot"):
            dossier = dossier.model_copy(update={"model_governance_snapshot": None})
        preview = runtime.export_interoperability_preview(
            ExportInteroperabilityPreviewRequest(
                dossier=dossier,
                target_profile=case["targetProfile"],
            )
        )
        missing_required_fields = sorted(preview.missing_required_fields)
        unsupported_field_paths = sorted(item.local_path for item in preview.unsupported_fields)
        expected_missing = sorted(case.get("expectedMissingRequiredFields", []))
        expected_unsupported = sorted(case.get("expectedUnsupportedFieldPaths", []))
        status = (
            "ok"
            if preview.preview_status.value == case["expectedPreviewStatus"]
            and missing_required_fields == expected_missing
            and unsupported_field_paths == expected_unsupported
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedPreviewStatus": case["expectedPreviewStatus"],
                "observedPreviewStatus": preview.preview_status.value,
                "expectedMissingRequiredFields": expected_missing,
                "observedMissingRequiredFields": missing_required_fields,
                "expectedUnsupportedFieldPaths": expected_unsupported,
                "observedUnsupportedFieldPaths": unsupported_field_paths,
            }
        )
    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
