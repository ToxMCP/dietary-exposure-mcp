from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import CheckContaminantMonitoringImportRequest
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_contaminant_monitoring_check_cases(repo_root: Path) -> dict:
    cases_payload = json.loads((_validation_root(repo_root) / "contaminant_monitoring_check_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in cases_payload["cases"]:
        response = runtime.check_contaminant_monitoring_import(
            CheckContaminantMonitoringImportRequest.model_validate(case["request"])
        )
        observed_occurrence_ids = sorted(item.record_id for item in response.occurrence_evidence_records)
        observed_method_ids = sorted(item.record_id for item in response.analytical_method_evidence_records)
        observed_high_attention_foods = sorted(response.normalized_projection.high_attention_food_hits)
        observed_linked_focus_ids = sorted(response.normalized_projection.linked_review_focus_ids)
        observed_ledger_entry_ids = sorted(item.entry_id for item in response.uncertainty_and_assumption_ledger)
        status = (
            "ok"
            if response.check_status.value == case["expectedCheckStatus"]
            and observed_occurrence_ids == sorted(case["expectedOccurrenceEvidenceRecordIds"])
            and observed_method_ids == sorted(case["expectedAnalyticalMethodEvidenceRecordIds"])
            and set(case["expectedHighAttentionFoodHits"]).issubset(observed_high_attention_foods)
            and set(case["expectedLinkedReviewFocusIds"]).issubset(observed_linked_focus_ids)
            and set(case.get("expectedLedgerEntryIds", [])).issubset(observed_ledger_entry_ids)
            and len(response.uncertainty_and_assumption_ledger) >= case.get("expectedMinimumLedgerCount", 0)
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "observedCheckStatus": response.check_status.value,
                "observedOccurrenceEvidenceRecordIds": observed_occurrence_ids,
                "observedAnalyticalMethodEvidenceRecordIds": observed_method_ids,
                "observedHighAttentionFoodHits": observed_high_attention_foods,
                "observedLinkedReviewFocusIds": observed_linked_focus_ids,
                "observedLedgerEntryIds": observed_ledger_entry_ids,
                "observedLedgerCount": len(response.uncertainty_and_assumption_ledger),
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
