from __future__ import annotations

from pathlib import Path

import pytest

from dietary_mcp.runtime import DietaryRuntime, _cohort_fingerprint
from dietary_mcp.models import (
    BuildDietaryResidueProfileRequest,
    DietaryCommodityResidueInput,
    ParseRawSurveyDatasetRequest,
    RawSurveyRecordInput,
    SummarizeSurveyDistributionRequest,
    BuildDietaryIntakeScenarioRequest,
    SelectConsumptionProfileRequest,
)
from dietary_mcp.plugins.reference_intake import ReferenceDietaryPlugin
from dietary_mcp.models import ScenarioClass


def test_percentile_calculation_with_known_dataset() -> None:
    """Percentiles from summarize_survey_distribution must match hand-calculated expectations."""
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest(
            datasetId="pct_test",
            regionId="eu",
            populationGroup="adult_general",
            rawRecords=[
                RawSurveyRecordInput(subjectId="s1", bodyWeightKg=70.0, daysInSurvey=1, commodityCode="apples", consumptionKgPerDay=0.1),
                RawSurveyRecordInput(subjectId="s2", bodyWeightKg=70.0, daysInSurvey=1, commodityCode="apples", consumptionKgPerDay=0.2),
                RawSurveyRecordInput(subjectId="s3", bodyWeightKg=70.0, daysInSurvey=1, commodityCode="apples", consumptionKgPerDay=0.3),
                RawSurveyRecordInput(subjectId="s4", bodyWeightKg=70.0, daysInSurvey=1, commodityCode="apples", consumptionKgPerDay=0.4),
            ],
        )
    )

    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "TestChem"},
            residue_records=[
                DietaryCommodityResidueInput(commodity_code="apples", residue_concentration_mg_per_kg=1.0, source_type="monitoring")
            ],
        )
    )

    summary = runtime.summarize_survey_distribution(
        SummarizeSurveyDistributionRequest(dataset=dataset, residue_profile=residue_profile)
    )

    # exposures = [0.00142857, 0.00285714, 0.00428571, 0.00571428]
    # mean = 0.0035714285714285713
    assert summary.mean_intake_mg_per_kg_bw_per_day == pytest.approx(0.0035714285714285713, abs=1e-12)
    # p95: k = 3*0.95 = 2.85 -> f=2, c=3 -> 0.00428571 + 0.85*(0.00571428-0.00428571) = 0.0055
    assert summary.percentile_95_mg_per_kg_bw_per_day == pytest.approx(0.0055, abs=1e-12)
    assert summary.max_mg_per_kg_bw_per_day == pytest.approx(0.005714285714285714, abs=1e-12)


def test_exposure_normalization_for_multi_day_survey() -> None:
    """consumption_kg_per_day is already a daily rate; days_in_survey must not cause extra division."""
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest(
            datasetId="norm_test",
            regionId="eu",
            populationGroup="adult_general",
            rawRecords=[
                RawSurveyRecordInput(subjectId="s1", bodyWeightKg=70.0, daysInSurvey=7, commodityCode="apples", consumptionKgPerDay=0.35),
            ],
        )
    )

    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "TestChem"},
            residue_records=[
                DietaryCommodityResidueInput(commodity_code="apples", residue_concentration_mg_per_kg=2.0, source_type="monitoring")
            ],
        )
    )

    summary = runtime.summarize_survey_distribution(
        SummarizeSurveyDistributionRequest(dataset=dataset, residue_profile=residue_profile)
    )

    # Expected: 0.35 kg/day * 2.0 mg/kg / 70 kg = 0.01 mg/kg bw/day
    assert summary.mean_intake_mg_per_kg_bw_per_day == pytest.approx(0.01, abs=1e-12)
    assert summary.max_mg_per_kg_bw_per_day == pytest.approx(0.01, abs=1e-12)


def test_cohort_fingerprint_uses_structured_encoding() -> None:
    assert _cohort_fingerprint([1.0, 23.0]) != _cohort_fingerprint([1.02, 3.0])
    assert _cohort_fingerprint([1.0, 23.0]) == _cohort_fingerprint([1.0, 23.0])


def test_contribution_fractions_sum_to_one() -> None:
    """Plugin contribution records must normalize to fractions that sum to 1.0."""
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    # Build a simple scenario with two commodities
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "TestChem"},
            residue_records=[
                DietaryCommodityResidueInput(commodity_code="apples", residue_concentration_mg_per_kg=1.0, source_type="monitoring"),
                DietaryCommodityResidueInput(commodity_code="milk", residue_concentration_mg_per_kg=2.0, source_type="monitoring"),
            ],
        )
    )

    consumption_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(region_id="eu_screening_default", population_group="adult_general", intake_window="chronic")
    ).profile

    scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity={"preferredName": "TestChem"},
            residue_profile=residue_profile,
            consumption_profile=consumption_profile,
        )
    )

    plugin = ReferenceDietaryPlugin(runtime.defaults, runtime.provenance, ScenarioClass.POINT_ESTIMATE)
    summary = plugin.run(scenario)

    total_fraction = sum(record.fraction_of_total or 0.0 for record in summary.commodity_contributions)
    assert total_fraction == pytest.approx(1.0, abs=1e-9)

    # Each fraction should be non-negative
    assert all(record.fraction_of_total >= 0.0 for record in summary.commodity_contributions)
