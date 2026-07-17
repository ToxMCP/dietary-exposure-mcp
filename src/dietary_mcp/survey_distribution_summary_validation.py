import json
from pathlib import Path
from typing import Any

from dietary_mcp.models import (
    BuildDietaryResidueProfileRequest,
    DietaryCommodityResidueInput,
    ParseRawSurveyDatasetRequest,
    RawSurveyRecordInput,
    SummarizeSurveyDistributionRequest,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


def _matches_number(observed: float | None, expected: float | None, tolerance: float) -> bool:
    if expected is None:
        return observed is None
    if observed is None:
        return False
    return abs(observed - expected) <= tolerance


def run_survey_distribution_summary_cases(repo_root: Path) -> dict[str, Any]:
    runtime = get_cached_dietary_runtime(repo_root)
    path = repo_root / "validation" / "v1" / "survey_distribution_summary_cases.json"
    if not path.exists():
        from dietary_mcp.assets import runtime_asset_root
        path = runtime_asset_root() / "validation" / "v1" / "survey_distribution_summary_cases.json"
    
    payload = json.loads(path.read_text())
    cases = payload["cases"]
    results = []

    for case in cases:
        raw_dataset_req = ParseRawSurveyDatasetRequest(
            datasetId=case["datasetId"],
            regionId=case["regionId"],
            populationGroup=case["populationGroup"],
            rawRecords=[RawSurveyRecordInput.model_validate(r) for r in case["rawRecords"]],
        )
        dataset = runtime.parse_raw_survey_dataset(raw_dataset_req)

        residue_profile = runtime.build_residue_profile(
            BuildDietaryResidueProfileRequest(
                chemical_identity=case["chemicalIdentity"],
                residue_records=[
                    DietaryCommodityResidueInput(
                        commodity_code=r["commodityCode"],
                        residue_concentration_mg_per_kg=r["residueConcentrationMgPerKg"],
                        lower_bound_mg_per_kg=r.get("lowerBoundMgPerKg"),
                        upper_bound_mg_per_kg=r.get("upperBoundMgPerKg"),
                        source_type=r.get("sourceType", "monitoring"),
                    )
                    for r in case["residueRecords"]
                ],
            )
        )

        summary_req = SummarizeSurveyDistributionRequest(
            dataset=dataset,
            residue_profile=residue_profile,
        )
        summary = runtime.summarize_survey_distribution(summary_req)

        tolerance = case["tolerance"]
        expectations = {
            "expectedMeanMgPerKgBwPerDay": summary.mean_intake_mg_per_kg_bw_per_day,
            "expectedPercentile95MgPerKgBwPerDay": summary.percentile_95_mg_per_kg_bw_per_day,
            "expectedPercentile99MgPerKgBwPerDay": summary.percentile_99_mg_per_kg_bw_per_day,
            "expectedPercentile999MgPerKgBwPerDay": summary.percentile_99_9_mg_per_kg_bw_per_day,
            "expectedMaxMgPerKgBwPerDay": summary.max_mg_per_kg_bw_per_day,
            "expectedConsumersOnlyMeanMgPerKgBwPerDay": summary.consumers_only_mean_mg_per_kg_bw_per_day,
            "expectedConsumersOnlyPercentile95MgPerKgBwPerDay": (
                summary.consumers_only_percentile_95_mg_per_kg_bw_per_day
            ),
            "expectedConsumersOnlyPercentile99MgPerKgBwPerDay": (
                summary.consumers_only_percentile_99_mg_per_kg_bw_per_day
            ),
            "expectedConsumersOnlyPercentile999MgPerKgBwPerDay": (
                summary.consumers_only_percentile_99_9_mg_per_kg_bw_per_day
            ),
        }
        observed_values = {
            "expectedMeanMgPerKgBwPerDay": summary.mean_intake_mg_per_kg_bw_per_day,
            "expectedPercentile95MgPerKgBwPerDay": summary.percentile_95_mg_per_kg_bw_per_day,
            "expectedPercentile99MgPerKgBwPerDay": summary.percentile_99_mg_per_kg_bw_per_day,
            "expectedPercentile999MgPerKgBwPerDay": summary.percentile_99_9_mg_per_kg_bw_per_day,
            "expectedMaxMgPerKgBwPerDay": summary.max_mg_per_kg_bw_per_day,
            "expectedConsumersOnlyMeanMgPerKgBwPerDay": summary.consumers_only_mean_mg_per_kg_bw_per_day,
            "expectedConsumersOnlyPercentile95MgPerKgBwPerDay": (
                summary.consumers_only_percentile_95_mg_per_kg_bw_per_day
            ),
            "expectedConsumersOnlyPercentile99MgPerKgBwPerDay": (
                summary.consumers_only_percentile_99_mg_per_kg_bw_per_day
            ),
            "expectedConsumersOnlyPercentile999MgPerKgBwPerDay": (
                summary.consumers_only_percentile_99_9_mg_per_kg_bw_per_day
            ),
        }

        case_status = "ok"
        if summary.total_subjects != case["expectedTotalSubjects"]:
            case_status = "failed"
        elif summary.consumers_only_count != case["expectedConsumersOnlyCount"]:
            case_status = "failed"
        elif not _matches_number(
            summary.zero_intake_prevalence,
            case["expectedZeroIntakePrevalence"],
            tolerance,
        ):
            case_status = "failed"
        elif not all(
            _matches_number(observed_values[key], case.get(key, expected), tolerance)
            for key, expected in expectations.items()
        ):
            case_status = "failed"

        results.append(
            {
                "name": case["name"],
                "status": case_status,
                "observed": {
                    "total_subjects": summary.total_subjects,
                    "consumers_only_count": summary.consumers_only_count,
                    "zero_intake_prevalence": summary.zero_intake_prevalence,
                    "mean_mg_per_kg_bw_per_day": summary.mean_intake_mg_per_kg_bw_per_day,
                    "percentile_95_mg_per_kg_bw_per_day": summary.percentile_95_mg_per_kg_bw_per_day,
                    "percentile_99_mg_per_kg_bw_per_day": summary.percentile_99_mg_per_kg_bw_per_day,
                    "percentile_99_9_mg_per_kg_bw_per_day": summary.percentile_99_9_mg_per_kg_bw_per_day,
                    "max_mg_per_kg_bw_per_day": summary.max_mg_per_kg_bw_per_day,
                    "consumers_only_mean_mg_per_kg_bw_per_day": (
                        summary.consumers_only_mean_mg_per_kg_bw_per_day
                    ),
                    "consumers_only_percentile_95_mg_per_kg_bw_per_day": (
                        summary.consumers_only_percentile_95_mg_per_kg_bw_per_day
                    ),
                    "consumers_only_percentile_99_mg_per_kg_bw_per_day": (
                        summary.consumers_only_percentile_99_mg_per_kg_bw_per_day
                    ),
                    "consumers_only_percentile_99_9_mg_per_kg_bw_per_day": (
                        summary.consumers_only_percentile_99_9_mg_per_kg_bw_per_day
                    ),
                },
            }
        )

    status = "ok" if all(r["status"] == "ok" for r in results) else "failed"
    return {"status": status, "cases": results}
