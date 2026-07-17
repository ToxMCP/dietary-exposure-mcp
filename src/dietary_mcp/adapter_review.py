from __future__ import annotations

from pathlib import Path

from dietary_mcp.adapter_walkthroughs import build_adapter_walkthrough
from dietary_mcp.models import (
    AdapterImportWalkthroughComparisonField,
    CompareAdapterImportToWalkthroughRequest,
    CompareAdapterImportToWalkthroughResult,
)


def _compare_float(field: str, observed: float | None, expected: float | None, tolerance: float):
    if observed is None or expected is None:
        matches = observed == expected
    else:
        matches = abs(observed - expected) <= tolerance
    return AdapterImportWalkthroughComparisonField(
        field=field,
        matches=matches,
        observed=observed,
        expected=expected,
        note=f"Numeric tolerance: {tolerance:g}.",
    )


def _compare_list(field: str, observed: list[str], expected: list[str], note: str | None = None):
    return AdapterImportWalkthroughComparisonField(
        field=field,
        matches=observed == expected,
        observed=observed,
        expected=expected,
        note=note,
    )


def _compare_required_subset(
    field: str,
    observed: list[str],
    required: list[str],
    note: str,
):
    return AdapterImportWalkthroughComparisonField(
        field=field,
        matches=set(required).issubset(set(observed)),
        observed=observed,
        expected=required,
        note=note,
    )


def _contribution_map(projection: dict) -> dict[str, float]:
    return {
        item["commodityCode"]: item["contributionMgPerKgBwPerDay"]
        for item in projection["commodityContributions"]
    }


def _food_vocabulary_map(projection: dict) -> dict[str, dict[str, str | None]]:
    return {
        item["commodityCode"]: {
            "foodex2Code": item.get("foodex2Code"),
            "rpcCode": item.get("rpcCode"),
            "rpcdCode": item.get("rpcdCode"),
            "processedStatus": item.get("processedStatus"),
            "mappingConfidence": item.get("mappingConfidence"),
        }
        for item in projection["commodityContributions"]
    }


def compare_adapter_import_to_walkthrough(
    repo_root: Path,
    request: CompareAdapterImportToWalkthroughRequest,
) -> CompareAdapterImportToWalkthroughResult:
    walkthrough = build_adapter_walkthrough(repo_root, request.walkthrough_name)
    projection = request.check_result.normalized_projection

    compared_fields = [
        AdapterImportWalkthroughComparisonField(
            field="template_name",
            matches=request.check_result.template_name == walkthrough["templateName"],
            observed=request.check_result.template_name,
            expected=walkthrough["templateName"],
        ),
        AdapterImportWalkthroughComparisonField(
            field="model_family",
            matches=request.check_result.model_family.value == walkthrough["modelFamily"],
            observed=request.check_result.model_family.value,
            expected=walkthrough["modelFamily"],
        ),
        AdapterImportWalkthroughComparisonField(
            field="unmapped_headers",
            matches=not request.check_result.unmapped_headers,
            observed=request.check_result.unmapped_headers,
            expected=[],
            note="Review is required when unrecognized CSV headers are present.",
        ),
        _compare_float(
            "total_intake_mg_per_kg_bw_per_day",
            projection.total_intake_mg_per_kg_bw_per_day,
            walkthrough["expectedNormalizedProjection"]["totalIntakeMgPerKgBwPerDay"],
            request.numeric_tolerance,
        ),
        _compare_float(
            "lower_bound_mg_per_kg_bw_per_day",
            projection.lower_bound_mg_per_kg_bw_per_day,
            walkthrough["expectedNormalizedProjection"]["lowerBoundMgPerKgBwPerDay"],
            request.numeric_tolerance,
        ),
        _compare_float(
            "upper_bound_mg_per_kg_bw_per_day",
            projection.upper_bound_mg_per_kg_bw_per_day,
            walkthrough["expectedNormalizedProjection"]["upperBoundMgPerKgBwPerDay"],
            request.numeric_tolerance,
        ),
        _compare_list(
            "commodity_codes",
            projection.commodity_codes,
            walkthrough["expectedNormalizedProjection"]["commodityCodes"],
        ),
        AdapterImportWalkthroughComparisonField(
            field="commodity_contributions_mg_per_kg_bw_per_day",
            matches=_contribution_map(walkthrough["expectedNormalizedProjection"])
            == {item.commodity_code: item.contribution_mg_per_kg_bw_per_day for item in projection.commodity_contributions},
            observed={item.commodity_code: item.contribution_mg_per_kg_bw_per_day for item in projection.commodity_contributions},
            expected=_contribution_map(walkthrough["expectedNormalizedProjection"]),
            note="Contribution values are compared on canonical commodity codes.",
        ),
        AdapterImportWalkthroughComparisonField(
            field="food_vocabulary_mappings",
            matches=_food_vocabulary_map(walkthrough["expectedNormalizedProjection"])
            == {
                item.commodity_code: {
                    "foodex2Code": item.foodex2_code,
                    "rpcCode": item.rpc_code,
                    "rpcdCode": item.rpcd_code,
                    "processedStatus": item.processed_status.value if item.processed_status else None,
                    "mappingConfidence": item.mapping_confidence.value if item.mapping_confidence else None,
                }
                for item in projection.commodity_contributions
            },
            observed={
                item.commodity_code: {
                    "foodex2Code": item.foodex2_code,
                    "rpcCode": item.rpc_code,
                    "rpcdCode": item.rpcd_code,
                    "processedStatus": item.processed_status.value if item.processed_status else None,
                    "mappingConfidence": item.mapping_confidence.value if item.mapping_confidence else None,
                }
                for item in projection.commodity_contributions
            },
            expected=_food_vocabulary_map(walkthrough["expectedNormalizedProjection"]),
            note="Food vocabulary fields are compared on canonical commodity codes with optional processed-commodity status retained.",
        ),
        _compare_list(
            "dominant_commodity_codes",
            projection.dominant_commodity_codes,
            walkthrough["expectedNormalizedProjection"]["dominantCommodityCodes"],
        ),
        _compare_required_subset(
            "required_source_ids_present",
            projection.source_ids,
            walkthrough["validationExpectation"].get("requiredSourceIds", []),
            "Extra provenance source IDs are allowed; required official source IDs must be present.",
        ),
        _compare_required_subset(
            "required_quality_flag_codes_present",
            projection.quality_flag_codes,
            walkthrough["validationExpectation"].get("requiredQualityFlagCodes", []),
            "Extra quality flags are allowed; required harness quality flags must be present.",
        ),
    ]

    mismatch_fields = [item.field for item in compared_fields if not item.matches]
    matched_fields = [item.field for item in compared_fields if item.matches]
    return CompareAdapterImportToWalkthroughResult(
        status="match" if not mismatch_fields else "review_required",
        walkthrough_name=request.walkthrough_name,
        walkthrough_resource_uri=f"adapter-walkthrough://{request.walkthrough_name}",
        template_name=walkthrough["templateName"],
        model_family=request.check_result.model_family,
        compared_fields=compared_fields,
        matched_fields=matched_fields,
        mismatch_fields=mismatch_fields,
        notes=[
            "This comparison is intentionally focused on stable normalized fields rather than runtime-generated IDs or timestamps.",
            "Required source IDs and required quality flags are checked as subsets so user-supplied provenance can extend the result without causing false mismatches.",
            "Review-required status indicates that at least one compared field diverged from the governed walkthrough baseline.",
        ],
    )
