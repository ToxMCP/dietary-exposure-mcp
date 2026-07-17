from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    LookupAnalyticalMethodEvidenceRequest,
    LookupContaminantLegalLimitsRequest,
    LookupConsumptionDatasetSupportRequest,
    LookupMetalsOccurrenceRequest,
    LookupMetalsReviewFocusRequest,
    LookupMethodSupportRequest,
    LookupOccurrenceEvidenceRequest,
    LookupReportingProfilesRequest,
    LookupReferenceValuesRequest,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_source_database_cases(repo_root: Path) -> dict:
    cases_payload = json.loads((_validation_root(repo_root) / "source_database_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in cases_payload["cases"]:
        if case["kind"] == "reference_values":
            response = runtime.lookup_reference_values(
                LookupReferenceValuesRequest.model_validate(case["request"])
            )
            observed_record_ids = sorted(item.record_id for item in response.matched_records)
            observed_conflict_ids = sorted(item.conflict_group_id for item in response.visible_conflicts)
            observed_authorities = sorted(item.authority for item in response.authorities)
            observed_quality_flag_codes = sorted({item.code for item in response.quality_flags})
            observed_coverage_ids = sorted(item.coverage_id for item in response.coverage_summaries)
            observed_coverage_levels = sorted({item.coverage_level.value for item in response.coverage_summaries})
            observed_requested_jurisdiction_status = response.requested_jurisdiction_status.value
            status = (
                "ok"
                if set(case.get("expectedRecordIds", [])).issubset(observed_record_ids)
                and set(case.get("expectedConflictGroupIds", [])).issubset(observed_conflict_ids)
                and set(case.get("expectedAuthorities", [])).issubset(observed_authorities)
                and set(case.get("expectedQualityFlagCodes", [])).issubset(observed_quality_flag_codes)
                and set(case.get("expectedCoverageIds", [])).issubset(observed_coverage_ids)
                and set(case.get("expectedCoverageLevels", [])).issubset(observed_coverage_levels)
                and observed_requested_jurisdiction_status
                == case.get("expectedRequestedJurisdictionStatus", observed_requested_jurisdiction_status)
                else "mismatch"
            )
            results.append(
                {
                    "name": case["name"],
                    "status": status,
                    "observedRecordIds": observed_record_ids,
                    "observedConflictGroupIds": observed_conflict_ids,
                    "observedAuthorities": observed_authorities,
                    "observedQualityFlagCodes": observed_quality_flag_codes,
                    "observedCoverageIds": observed_coverage_ids,
                    "observedCoverageLevels": observed_coverage_levels,
                    "observedRequestedJurisdictionStatus": observed_requested_jurisdiction_status,
                }
            )
            continue

        if case["kind"] == "contaminant_legal_limits":
            response = runtime.lookup_contaminant_legal_limits(
                LookupContaminantLegalLimitsRequest.model_validate(case["request"])
            )
            observed_record_ids = sorted(item.record_id for item in response.matched_records)
            observed_legal_authority_ids = sorted(item.authority_id for item in response.legal_authorities)
            observed_quality_flag_codes = sorted({item.code for item in response.quality_flags})
            observed_coverage_ids = sorted(item.coverage_id for item in response.coverage_summaries)
            observed_coverage_levels = sorted({item.coverage_level.value for item in response.coverage_summaries})
            observed_requested_lane_status = response.requested_lane_status.value
            status = (
                "ok"
                if set(case.get("expectedRecordIds", [])).issubset(observed_record_ids)
                and set(case.get("expectedLegalAuthorityIds", [])).issubset(observed_legal_authority_ids)
                and set(case.get("expectedQualityFlagCodes", [])).issubset(observed_quality_flag_codes)
                and set(case.get("expectedCoverageIds", [])).issubset(observed_coverage_ids)
                and set(case.get("expectedCoverageLevels", [])).issubset(observed_coverage_levels)
                and response.overall_submission_use.value == case["expectedOverallSubmissionUse"]
                and observed_requested_lane_status == case.get("expectedRequestedLaneStatus", observed_requested_lane_status)
                else "mismatch"
            )
            results.append(
                {
                    "name": case["name"],
                    "status": status,
                    "observedRecordIds": observed_record_ids,
                    "observedLegalAuthorityIds": observed_legal_authority_ids,
                    "observedQualityFlagCodes": observed_quality_flag_codes,
                    "observedCoverageIds": observed_coverage_ids,
                    "observedCoverageLevels": observed_coverage_levels,
                    "observedRequestedLaneStatus": observed_requested_lane_status,
                    "observedOverallSubmissionUse": response.overall_submission_use.value,
                }
            )
            continue

        if case["kind"] == "method_support":
            response = runtime.lookup_method_support(
                LookupMethodSupportRequest.model_validate(case["request"])
            )
            observed_method_ids = sorted(item.method_id for item in response.methods)
            observed_legal_authority_ids = sorted(item.authority_id for item in response.legal_authorities)
            status = (
                "ok"
                if set(case.get("expectedMethodIds", [])).issubset(observed_method_ids)
                and set(case.get("expectedLegalAuthorityIds", [])).issubset(observed_legal_authority_ids)
                and response.overall_submission_use.value == case["expectedOverallSubmissionUse"]
                and response.submission_candidate_allowed == case["expectedSubmissionCandidateAllowed"]
                else "mismatch"
            )
            results.append(
                {
                    "name": case["name"],
                    "status": status,
                    "observedMethodIds": observed_method_ids,
                    "observedLegalAuthorityIds": observed_legal_authority_ids,
                    "observedOverallSubmissionUse": response.overall_submission_use.value,
                    "observedSubmissionCandidateAllowed": response.submission_candidate_allowed,
                }
            )
            continue

        if case["kind"] == "consumption_datasets":
            response = runtime.lookup_consumption_dataset_support(
                LookupConsumptionDatasetSupportRequest.model_validate(case["request"])
            )
            observed_dataset_ids = sorted(item.dataset_id for item in response.datasets)
            status = (
                "ok"
                if set(case.get("expectedDatasetIds", [])).issubset(observed_dataset_ids)
                and response.overall_submission_use.value == case["expectedOverallSubmissionUse"]
                else "mismatch"
            )
            results.append(
                {
                    "name": case["name"],
                    "status": status,
                    "observedDatasetIds": observed_dataset_ids,
                    "observedOverallSubmissionUse": response.overall_submission_use.value,
                }
            )
            continue

        if case["kind"] == "occurrence_evidence":
            response = runtime.lookup_occurrence_evidence(
                LookupOccurrenceEvidenceRequest.model_validate(case["request"])
            )
            observed_record_ids = sorted(item.record_id for item in response.records)
            status = (
                "ok"
                if set(case.get("expectedRecordIds", [])).issubset(observed_record_ids)
                and response.overall_submission_use.value == case["expectedOverallSubmissionUse"]
                and response.submission_candidate_allowed == case["expectedSubmissionCandidateAllowed"]
                else "mismatch"
            )
            results.append(
                {
                    "name": case["name"],
                    "status": status,
                    "observedRecordIds": observed_record_ids,
                    "observedOverallSubmissionUse": response.overall_submission_use.value,
                    "observedSubmissionCandidateAllowed": response.submission_candidate_allowed,
                }
            )
            continue

        if case["kind"] == "reporting_profiles":
            response = runtime.lookup_reporting_profiles(
                LookupReportingProfilesRequest.model_validate(case["request"])
            )
            observed_profile_ids = sorted(item.profile_id for item in response.profiles)
            status = (
                "ok"
                if set(case.get("expectedProfileIds", [])).issubset(observed_profile_ids)
                and set(case.get("expectedRecommendedPrimaryProfileIds", [])).issubset(
                    response.recommended_primary_profile_ids
                )
                else "mismatch"
            )
            results.append(
                {
                    "name": case["name"],
                    "status": status,
                    "observedProfileIds": observed_profile_ids,
                    "observedRecommendedPrimaryProfileIds": response.recommended_primary_profile_ids,
                }
            )
            continue

        if case["kind"] == "analytical_method_evidence":
            response = runtime.lookup_analytical_method_evidence(
                LookupAnalyticalMethodEvidenceRequest.model_validate(case["request"])
            )
            observed_record_ids = sorted(item.record_id for item in response.records)
            status = (
                "ok"
                if set(case.get("expectedRecordIds", [])).issubset(observed_record_ids)
                and response.overall_submission_use.value == case["expectedOverallSubmissionUse"]
                and response.submission_candidate_allowed == case["expectedSubmissionCandidateAllowed"]
                else "mismatch"
            )
            results.append(
                {
                    "name": case["name"],
                    "status": status,
                    "observedRecordIds": observed_record_ids,
                    "observedOverallSubmissionUse": response.overall_submission_use.value,
                    "observedSubmissionCandidateAllowed": response.submission_candidate_allowed,
                }
            )
            continue

        if case["kind"] == "metals_occurrence":
            response = runtime.lookup_metals_occurrence(
                LookupMetalsOccurrenceRequest.model_validate(case["request"])
            )
            observed_record_ids = sorted(item.record_id for item in response.records)
            observed_priority_food_groups = sorted(
                {food_group for item in response.records for food_group in item.priority_food_groups}
            )
            observed_high_attention_foods = sorted(
                {food for item in response.records for food in item.high_attention_foods}
            )
            status = (
                "ok"
                if set(case.get("expectedRecordIds", [])).issubset(observed_record_ids)
                and set(case.get("expectedPriorityFoodGroups", [])).issubset(observed_priority_food_groups)
                and set(case.get("expectedHighAttentionFoods", [])).issubset(observed_high_attention_foods)
                and response.overall_submission_use.value == case["expectedOverallSubmissionUse"]
                and response.submission_candidate_allowed == case["expectedSubmissionCandidateAllowed"]
                else "mismatch"
            )
            results.append(
                {
                    "name": case["name"],
                    "status": status,
                    "observedRecordIds": observed_record_ids,
                    "observedPriorityFoodGroups": observed_priority_food_groups,
                    "observedHighAttentionFoods": observed_high_attention_foods,
                    "observedOverallSubmissionUse": response.overall_submission_use.value,
                    "observedSubmissionCandidateAllowed": response.submission_candidate_allowed,
                }
            )
            continue

        if case["kind"] == "metals_review_focus":
            response = runtime.lookup_metals_review_focus(
                LookupMetalsReviewFocusRequest.model_validate(case["request"])
            )
            observed_focus_ids = sorted(item.focus_id for item in response.records)
            observed_commodity_groups = sorted(
                {commodity_group for item in response.records for commodity_group in item.commodity_groups}
            )
            observed_focus_foods = sorted({food for item in response.records for food in item.focus_foods})
            status = (
                "ok"
                if set(case.get("expectedFocusIds", [])).issubset(observed_focus_ids)
                and set(case.get("expectedCommodityGroups", [])).issubset(observed_commodity_groups)
                and set(case.get("expectedFocusFoods", [])).issubset(observed_focus_foods)
                and response.overall_submission_use.value == case["expectedOverallSubmissionUse"]
                and response.submission_candidate_allowed == case["expectedSubmissionCandidateAllowed"]
                else "mismatch"
            )
            results.append(
                {
                    "name": case["name"],
                    "status": status,
                    "observedFocusIds": observed_focus_ids,
                    "observedCommodityGroups": observed_commodity_groups,
                    "observedFocusFoods": observed_focus_foods,
                    "observedOverallSubmissionUse": response.overall_submission_use.value,
                    "observedSubmissionCandidateAllowed": response.submission_candidate_allowed,
                }
            )
            continue

        raise ValueError(f"Unknown source-database validation case kind: {case['kind']}")

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
