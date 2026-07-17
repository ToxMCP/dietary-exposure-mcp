from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    BuildDietaryResidueProfileRequest,
    BuildProbabilisticIntakeSummaryRequest,
    DietaryCommodityResidueInput,
    ParseRawSurveyDatasetRequest,
    RawSurveyRecordInput,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def _matches_number(observed: float | None, expected: float | None, tolerance: float) -> bool:
    if expected is None:
        return observed is None
    if observed is None:
        return False
    return abs(observed - expected) <= tolerance


def _matches_text(observed: str | None, expected: str | None) -> bool:
    if expected is None:
        return observed is None
    return observed == expected


def run_probabilistic_intake_summary_cases(repo_root: Path) -> dict[str, Any]:
    runtime = get_cached_dietary_runtime(repo_root)
    payload = json.loads((_validation_root(repo_root) / "probabilistic_intake_summary_cases.json").read_text())
    results: list[dict[str, Any]] = []
    fingerprints_by_case: dict[str, str] = {}

    for case in payload["cases"]:
        # Exact expected values are generated from deterministic random.Random(seed)
        # cohort bootstrap draws over the current governed subject-exposure cohort.
        raw_dataset_req = ParseRawSurveyDatasetRequest(
            datasetId=case["datasetId"],
            regionId=case["regionId"],
            populationGroup=case["populationGroup"],
            rawRecords=[RawSurveyRecordInput.model_validate(record) for record in case["rawRecords"]],
        )
        dataset = runtime.parse_raw_survey_dataset(raw_dataset_req)

        residue_profile = runtime.build_residue_profile(
            BuildDietaryResidueProfileRequest(
                chemical_identity=case["chemicalIdentity"],
                residue_records=[
                    DietaryCommodityResidueInput(
                        commodity_code=record["commodityCode"],
                        residue_concentration_mg_per_kg=record["residueConcentrationMgPerKg"],
                        lower_bound_mg_per_kg=record.get("lowerBoundMgPerKg"),
                        upper_bound_mg_per_kg=record.get("upperBoundMgPerKg"),
                        source_type=record.get("sourceType", "monitoring"),
                    )
                    for record in case["residueRecords"]
                ],
            )
        )

        summary = runtime.build_probabilistic_intake_summary(
            BuildProbabilisticIntakeSummaryRequest(
                dataset=dataset,
                residue_profile=residue_profile,
                iteration_count=case["iterationCount"],
                random_seed=case["randomSeed"],
            )
        )

        observed_quality_flag_codes = sorted(flag.code for flag in summary.quality_flags)
        observed_limitation_codes = sorted(note.code for note in summary.limitations)
        observed_provenance_source_ids = sorted(
            reference.source_id for reference in summary.provenance.source_references
        )

        tolerance = case.get("tolerance", 1e-9)
        status = "ok"
        if summary.total_subjects != case.get("expectedTotalSubjects", summary.total_subjects):
            status = "mismatch"
        elif summary.consumers_only_count != case.get(
            "expectedConsumersOnlyCount", summary.consumers_only_count
        ):
            status = "mismatch"
        elif not _matches_number(
            summary.zero_intake_prevalence,
            case.get("expectedZeroIntakePrevalence", summary.zero_intake_prevalence),
            tolerance,
        ):
            status = "mismatch"
        elif not _matches_number(
            summary.mean_intake_mg_per_kg_bw_per_day,
            case.get("expectedMeanMgPerKgBwPerDay", summary.mean_intake_mg_per_kg_bw_per_day),
            tolerance,
        ):
            status = "mismatch"
        elif not _matches_number(
            summary.percentile_95_mg_per_kg_bw_per_day,
            case.get(
                "expectedPercentile95MgPerKgBwPerDay",
                summary.percentile_95_mg_per_kg_bw_per_day,
            ),
            tolerance,
        ):
            status = "mismatch"
        elif not _matches_number(
            summary.percentile_99_mg_per_kg_bw_per_day,
            case.get(
                "expectedPercentile99MgPerKgBwPerDay",
                summary.percentile_99_mg_per_kg_bw_per_day,
            ),
            tolerance,
        ):
            status = "mismatch"
        elif not _matches_number(
            summary.percentile_99_9_mg_per_kg_bw_per_day,
            case.get(
                "expectedPercentile999MgPerKgBwPerDay",
                summary.percentile_99_9_mg_per_kg_bw_per_day,
            ),
            tolerance,
        ):
            status = "mismatch"
        elif not _matches_number(
            summary.max_mg_per_kg_bw_per_day,
            case.get("expectedMaxMgPerKgBwPerDay", summary.max_mg_per_kg_bw_per_day),
            tolerance,
        ):
            status = "mismatch"
        elif not _matches_number(
            summary.consumers_only_mean_mg_per_kg_bw_per_day,
            case.get(
                "expectedConsumersOnlyMeanMgPerKgBwPerDay",
                summary.consumers_only_mean_mg_per_kg_bw_per_day,
            ),
            tolerance,
        ):
            status = "mismatch"
        elif not _matches_number(
            summary.consumers_only_percentile_95_mg_per_kg_bw_per_day,
            case.get(
                "expectedConsumersOnlyPercentile95MgPerKgBwPerDay",
                summary.consumers_only_percentile_95_mg_per_kg_bw_per_day,
            ),
            tolerance,
        ):
            status = "mismatch"
        elif not _matches_number(
            summary.consumers_only_percentile_99_mg_per_kg_bw_per_day,
            case.get(
                "expectedConsumersOnlyPercentile99MgPerKgBwPerDay",
                summary.consumers_only_percentile_99_mg_per_kg_bw_per_day,
            ),
            tolerance,
        ):
            status = "mismatch"
        elif not _matches_number(
            summary.consumers_only_percentile_99_9_mg_per_kg_bw_per_day,
            case.get(
                "expectedConsumersOnlyPercentile999MgPerKgBwPerDay",
                summary.consumers_only_percentile_99_9_mg_per_kg_bw_per_day,
            ),
            tolerance,
        ):
            status = "mismatch"
        elif not _matches_text(
            summary.cohort_fingerprint,
            case.get("expectedCohortFingerprint", summary.cohort_fingerprint),
        ):
            status = "mismatch"
        elif not summary.cohort_fingerprint.startswith(
            case.get("expectedCohortFingerprintPrefix", "cohort-")
        ):
            status = "mismatch"
        elif not set(case.get("expectedQualityFlagCodes", [])).issubset(observed_quality_flag_codes):
            status = "mismatch"
        elif not set(case.get("expectedLimitationCodes", [])).issubset(observed_limitation_codes):
            status = "mismatch"
        elif not set(case.get("expectedProvenanceSourceIds", [])).issubset(observed_provenance_source_ids):
            status = "mismatch"

        fingerprints_by_case[case["name"]] = summary.cohort_fingerprint
        results.append(
            {
                "name": case["name"],
                "status": status,
                "observed": {
                    "total_subjects": summary.total_subjects,
                    "consumers_only_count": summary.consumers_only_count,
                    "zero_intake_prevalence": summary.zero_intake_prevalence,
                    "mean_mg_per_kg_bw_per_day": summary.mean_intake_mg_per_kg_bw_per_day,
                    "percentile_95_mg_per_kg_bw_per_day": summary.percentile_95_mg_per_kg_bw_per_day,
                    "percentile_99_mg_per_kg_bw_per_day": summary.percentile_99_mg_per_kg_bw_per_day,
                    "percentile_99_9_mg_per_kg_bw_per_day": summary.percentile_99_9_mg_per_kg_bw_per_day,
                    "max_mg_per_kg_bw_per_day": summary.max_mg_per_kg_bw_per_day,
                    "consumers_only_mean_mg_per_kg_bw_per_day": summary.consumers_only_mean_mg_per_kg_bw_per_day,
                    "consumers_only_percentile_95_mg_per_kg_bw_per_day": summary.consumers_only_percentile_95_mg_per_kg_bw_per_day,
                    "consumers_only_percentile_99_mg_per_kg_bw_per_day": summary.consumers_only_percentile_99_mg_per_kg_bw_per_day,
                    "consumers_only_percentile_99_9_mg_per_kg_bw_per_day": summary.consumers_only_percentile_99_9_mg_per_kg_bw_per_day,
                    "cohort_fingerprint": summary.cohort_fingerprint,
                    "quality_flag_codes": observed_quality_flag_codes,
                    "limitation_codes": observed_limitation_codes,
                    "provenance_source_ids": observed_provenance_source_ids,
                },
            }
        )

    comparison_results: list[dict[str, str]] = []
    for comparison in payload.get("fingerprintComparisons", []):
        left = fingerprints_by_case.get(comparison["leftCase"])
        right = fingerprints_by_case.get(comparison["rightCase"])
        relation = comparison["relation"]
        status = "ok"
        if left is None or right is None:
            status = "mismatch"
        elif relation == "equal" and left != right:
            status = "mismatch"
        elif relation == "not_equal" and left == right:
            status = "mismatch"
        comparison_results.append(
            {
                "name": comparison["name"],
                "status": status,
                "leftFingerprint": left or "",
                "rightFingerprint": right or "",
            }
        )

    overall_status = "ok"
    if not all(item["status"] == "ok" for item in results):
        overall_status = "review_required"
    elif not all(item["status"] == "ok" for item in comparison_results):
        overall_status = "review_required"

    return {"status": overall_status, "cases": results, "fingerprintComparisons": comparison_results}
