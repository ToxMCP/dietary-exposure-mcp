from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    BuildDietaryResidueProfileRequest,
    BuildUncertaintyIntakeAssessmentRequest,
    DietaryCommodityResidueInput,
    ParseRawSurveyDatasetRequest,
    RawSurveyRecordInput,
    ResidueUncertaintyModel,
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


def _case_path(repo_root: Path, filename: str) -> Path:
    return _validation_root(repo_root) / filename


def _run_case_file(repo_root: Path, filename: str) -> dict[str, Any]:
    runtime = get_cached_dietary_runtime(repo_root)
    payload = json.loads(_case_path(repo_root, filename).read_text())
    results: list[dict[str, Any]] = []

    for case in payload["cases"]:
        dataset = runtime.parse_raw_survey_dataset(
            ParseRawSurveyDatasetRequest(
                datasetId=case["datasetId"],
                regionId=case["regionId"],
                populationGroup=case["populationGroup"],
                rawRecords=[RawSurveyRecordInput.model_validate(record) for record in case["rawRecords"]],
            )
        )
        residue_profile = runtime.build_residue_profile(
            BuildDietaryResidueProfileRequest(
                chemical_identity=case["chemicalIdentity"],
                residue_records=[
                    DietaryCommodityResidueInput(
                        commodity_code=record["commodityCode"],
                        residue_concentration_mg_per_kg=record["residueConcentrationMgPerKg"],
                        source_type=record.get("sourceType", "monitoring"),
                        lower_bound_mg_per_kg=record.get("lowerBoundMgPerKg"),
                        upper_bound_mg_per_kg=record.get("upperBoundMgPerKg"),
                    )
                    for record in case["residueRecords"]
                ],
            )
        )
        request = BuildUncertaintyIntakeAssessmentRequest(
            dataset=dataset,
            residue_profile=residue_profile,
            random_seed=case["randomSeed"],
            outer_iteration_count=case["outerIterationCount"],
            inner_iteration_count=case["innerIterationCount"],
            residue_uncertainty_models=[
                ResidueUncertaintyModel.model_validate(model)
                for model in case["residueUncertaintyModels"]
            ],
            censored_data_policy=case.get("censoredDataPolicy", "three_bound_sensitivity"),
            health_reference=case.get("healthReference"),
        )
        assessment = runtime.build_uncertainty_intake_assessment(request)
        observed_ledger_codes = sorted(
            entry.code for entry in assessment.uncertainty_assumption_ledger.entries
        )
        observed_policy_keys = sorted(assessment.censored_policy_summaries.keys())
        observed_sensitivity_inputs = sorted(item.input_name for item in assessment.sensitivity_ranking)
        tolerance = case.get("tolerance", 1e-9)

        checks = [
            _matches_number(
                assessment.distribution_summary.mean.median,
                case.get("expectedMeanMedian"),
                tolerance,
            ),
            _matches_number(
                assessment.distribution_summary.percentile_95.median,
                case.get("expectedPercentile95Median"),
                tolerance,
            ),
            _matches_number(
                assessment.distribution_summary.percentile_99.median,
                case.get("expectedPercentile99Median"),
                tolerance,
            ),
            _matches_number(
                assessment.distribution_summary.max.median,
                case.get("expectedMaxMedian"),
                tolerance,
            ),
            _matches_number(
                (
                    assessment.health_reference_exceedance.exceedance_probability.median
                    if assessment.health_reference_exceedance
                    else None
                ),
                case.get("expectedExceedanceProbabilityMedian"),
                tolerance,
            ),
            _matches_number(
                (
                    assessment.health_reference_exceedance.high_percentile_exposure_ratio.median
                    if assessment.health_reference_exceedance
                    and assessment.health_reference_exceedance.high_percentile_exposure_ratio
                    else None
                ),
                case.get("expectedHighPercentileExposureRatioMedian"),
                tolerance,
            ),
            _matches_number(
                (
                    assessment.health_reference_exceedance.margin_of_exposure.median
                    if assessment.health_reference_exceedance
                    and assessment.health_reference_exceedance.margin_of_exposure
                    else None
                ),
                case.get("expectedMarginOfExposureMedian"),
                tolerance,
            ),
        ]
        if "expectedHighPercentileMetric" in case:
            checks.append(
                bool(assessment.health_reference_exceedance)
                and assessment.health_reference_exceedance.high_percentile_metric
                == case["expectedHighPercentileMetric"]
            )
        if "expectedSimulationFingerprint" in case:
            checks.append(
                assessment.reproducibility.simulation_fingerprint
                == case["expectedSimulationFingerprint"]
            )
        if "expectedModelFingerprint" in case:
            checks.append(
                assessment.reproducibility.model_fingerprint
                == case["expectedModelFingerprint"]
            )
        checks.append(
            set(case.get("expectedLedgerCodes", [])).issubset(observed_ledger_codes)
        )
        checks.append(
            set(case.get("expectedCensoredPolicyKeys", [])).issubset(observed_policy_keys)
        )
        checks.append(
            set(case.get("expectedSensitivityInputs", [])).issubset(observed_sensitivity_inputs)
        )
        if "expectedWeightedSampling" in case:
            checks.append(assessment.weighted_sampling == case["expectedWeightedSampling"])
        results.append(
            {
                "name": case["name"],
                "status": "ok" if all(checks) else "mismatch",
                "observed": {
                    "meanMedian": assessment.distribution_summary.mean.median,
                    "percentile95Median": assessment.distribution_summary.percentile_95.median,
                    "percentile99Median": assessment.distribution_summary.percentile_99.median,
                    "maxMedian": assessment.distribution_summary.max.median,
                    "exceedanceProbabilityMedian": (
                        assessment.health_reference_exceedance.exceedance_probability.median
                        if assessment.health_reference_exceedance
                        else None
                    ),
                    "highPercentileExposureRatioMedian": (
                        assessment.health_reference_exceedance.high_percentile_exposure_ratio.median
                        if assessment.health_reference_exceedance
                        and assessment.health_reference_exceedance.high_percentile_exposure_ratio
                        else None
                    ),
                    "marginOfExposureMedian": (
                        assessment.health_reference_exceedance.margin_of_exposure.median
                        if assessment.health_reference_exceedance
                        and assessment.health_reference_exceedance.margin_of_exposure
                        else None
                    ),
                    "simulationFingerprint": assessment.reproducibility.simulation_fingerprint,
                    "modelFingerprint": assessment.reproducibility.model_fingerprint,
                    "weightedSampling": assessment.weighted_sampling,
                    "ledgerCodes": observed_ledger_codes,
                    "censoredPolicyKeys": observed_policy_keys,
                    "sensitivityInputs": observed_sensitivity_inputs,
                },
            }
        )

    return {
        "status": "ok" if all(case["status"] == "ok" for case in results) else "review_required",
        "cases": results,
    }


def run_uncertainty_intake_assessment_cases(repo_root: Path) -> dict[str, Any]:
    return _run_case_file(repo_root, "uncertainty_intake_assessment_cases.json")


def run_censored_residue_policy_cases(repo_root: Path) -> dict[str, Any]:
    return _run_case_file(repo_root, "censored_residue_policy_cases.json")


def run_uncertainty_sensitivity_cases(repo_root: Path) -> dict[str, Any]:
    return _run_case_file(repo_root, "uncertainty_sensitivity_cases.json")


def run_health_reference_exceedance_cases(repo_root: Path) -> dict[str, Any]:
    return _run_case_file(repo_root, "health_reference_exceedance_cases.json")


def run_uncertainty_reproducibility_cases(repo_root: Path) -> dict[str, Any]:
    return _run_case_file(repo_root, "uncertainty_reproducibility_cases.json")
