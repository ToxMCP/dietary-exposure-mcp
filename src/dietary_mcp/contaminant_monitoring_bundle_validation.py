from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    CheckContaminantMonitoringImportRequest,
    ExportContaminantMonitoringInterpretationBundleRequest,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_contaminant_monitoring_bundle_cases(repo_root: Path) -> dict:
    cases_payload = json.loads((_validation_root(repo_root) / "contaminant_monitoring_bundle_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in cases_payload["cases"]:
        check_result = runtime.check_contaminant_monitoring_import(
            CheckContaminantMonitoringImportRequest.model_validate(case["request"])
        )
        bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
            ExportContaminantMonitoringInterpretationBundleRequest(
                check_result=check_result,
                bundle_note=case.get("bundleNote"),
            )
        )
        observed_occurrence_ids = sorted(item.record_id for item in bundle.check_result.occurrence_evidence_records)
        observed_method_ids = sorted(item.record_id for item in bundle.check_result.analytical_method_evidence_records)
        observed_focus_ids = sorted(item.focus_id for item in bundle.linked_review_focus_records)
        observed_ledger_entry_ids = sorted(item.entry_id for item in bundle.uncertainty_and_assumption_ledger)
        status = (
            "ok"
            if bundle.check_status.value == case["expectedCheckStatus"]
            and observed_occurrence_ids == sorted(case["expectedOccurrenceEvidenceRecordIds"])
            and observed_method_ids == sorted(case["expectedAnalyticalMethodEvidenceRecordIds"])
            and set(case["expectedFocusIds"]).issubset(observed_focus_ids)
            and set(case["expectedHighAttentionFoodHits"]).issubset(bundle.check_result.normalized_projection.high_attention_food_hits)
            and bundle.overall_submission_use.value == case["expectedOverallSubmissionUse"]
            and bundle.submission_candidate_allowed == case["expectedSubmissionCandidateAllowed"]
            and len(bundle.review_prompts) >= case.get("expectedMinimumPromptCount", 0)
            and set(case.get("expectedLedgerEntryIds", [])).issubset(observed_ledger_entry_ids)
            and len(bundle.uncertainty_and_assumption_ledger) >= case.get("expectedMinimumLedgerCount", 0)
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "observedCheckStatus": bundle.check_status.value,
                "observedOccurrenceEvidenceRecordIds": observed_occurrence_ids,
                "observedAnalyticalMethodEvidenceRecordIds": observed_method_ids,
                "observedFocusIds": observed_focus_ids,
                "observedHighAttentionFoodHits": bundle.check_result.normalized_projection.high_attention_food_hits,
                "observedOverallSubmissionUse": bundle.overall_submission_use.value,
                "observedSubmissionCandidateAllowed": bundle.submission_candidate_allowed,
                "observedPromptCount": len(bundle.review_prompts),
                "observedLedgerEntryIds": observed_ledger_entry_ids,
                "observedLedgerCount": len(bundle.uncertainty_and_assumption_ledger),
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
