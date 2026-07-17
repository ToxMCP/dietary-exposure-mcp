from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    ExportMetalsMonitoringInterpretationBundleRequest,
    LookupMetalsOccurrenceRequest,
    LookupMetalsReviewFocusRequest,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_metals_monitoring_bundle_cases(repo_root: Path) -> dict:
    cases_payload = json.loads((_validation_root(repo_root) / "metals_monitoring_bundle_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in cases_payload["cases"]:
        occurrence_result = runtime.lookup_metals_occurrence(
            LookupMetalsOccurrenceRequest.model_validate(case["occurrenceRequest"])
        )
        review_focus_result = runtime.lookup_metals_review_focus(
            LookupMetalsReviewFocusRequest.model_validate(case["reviewFocusRequest"])
        )
        bundle = runtime.export_metals_monitoring_interpretation_bundle(
            ExportMetalsMonitoringInterpretationBundleRequest(
                occurrence_result=occurrence_result,
                review_focus_result=review_focus_result,
                bundle_note=case.get("bundleNote"),
            )
        )

        observed_occurrence_record_ids = sorted(item.record_id for item in bundle.occurrence_records)
        observed_focus_ids = sorted(item.focus_id for item in bundle.review_focus_records)
        observed_ledger_entry_ids = sorted(item.entry_id for item in bundle.uncertainty_and_assumption_ledger)
        status = (
            "ok"
            if set(case.get("expectedOccurrenceRecordIds", [])).issubset(observed_occurrence_record_ids)
            and set(case.get("expectedFocusIds", [])).issubset(observed_focus_ids)
            and set(case.get("expectedPriorityFoodGroups", [])).issubset(bundle.priority_food_groups)
            and set(case.get("expectedHighAttentionFoods", [])).issubset(bundle.high_attention_foods)
            and set(case.get("expectedFocusFoods", [])).issubset(bundle.focus_foods)
            and set(case.get("expectedSensitivePopulationGroups", [])).issubset(bundle.sensitive_population_groups)
            and set(case.get("expectedReferenceValueRecordIds", [])).issubset(bundle.covered_reference_value_record_ids)
            and set(case.get("expectedLinkedOccurrenceRecordIds", [])).issubset(bundle.linked_occurrence_record_ids)
            and bundle.unresolved_linked_occurrence_record_ids
            == case.get("expectedUnresolvedLinkedOccurrenceRecordIds", [])
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
                "observedOccurrenceRecordIds": observed_occurrence_record_ids,
                "observedFocusIds": observed_focus_ids,
                "observedPriorityFoodGroups": bundle.priority_food_groups,
                "observedHighAttentionFoods": bundle.high_attention_foods,
                "observedFocusFoods": bundle.focus_foods,
                "observedSensitivePopulationGroups": bundle.sensitive_population_groups,
                "observedReferenceValueRecordIds": bundle.covered_reference_value_record_ids,
                "observedLinkedOccurrenceRecordIds": bundle.linked_occurrence_record_ids,
                "observedUnresolvedLinkedOccurrenceRecordIds": bundle.unresolved_linked_occurrence_record_ids,
                "observedOverallSubmissionUse": bundle.overall_submission_use.value,
                "observedSubmissionCandidateAllowed": bundle.submission_candidate_allowed,
                "observedPromptCount": len(bundle.review_prompts),
                "observedLedgerEntryIds": observed_ledger_entry_ids,
                "observedLedgerCount": len(bundle.uncertainty_and_assumption_ledger),
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
