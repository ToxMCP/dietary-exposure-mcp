import json
import math
from pathlib import Path

from dietary_mcp.integrations import (
    export_pbpk_oral_input,
    export_toxclaw_dietary_evidence_bundle,
)
from dietary_mcp.models import (
    BuildBoundedIntakeSummaryRequest,
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    BuildProbabilisticIntakeSummaryRequest,
    BuildUncertaintyIntakeAssessmentRequest,
    EvaluateGlobalTradeRiskRequest,
    ExportPbpkOralInputRequest,
    ExportToxclawDietaryEvidenceBundleRequest,
    IntakeWindowSemantic,
    ParseRawSurveyDatasetRequest,
    PbpkExternalImportBundle,
    ScenarioClass,
    SelectConsumptionProfileRequest,
    SummarizeSurveyDistributionRequest,
)
from dietary_mcp.runtime import DietaryRuntime


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = REPO_ROOT / "examples" / "pesticide_pess_style" / "glyphosate_public_slice"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _assert_close(actual: float, expected: float, *, rel_tol: float = 1e-9) -> None:
    assert math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=1e-15)


def test_glyphosate_public_slice_rebuilds_through_public_contracts() -> None:
    runtime = DietaryRuntime(REPO_ROOT)
    expected = _load_json(CASE_DIR / "outputs" / "output_summary.json")

    source_lock_path = CASE_DIR / "source_lock.json"
    source_lock = _load_json(source_lock_path)
    source_lock_text = source_lock_path.read_text()
    assert source_lock["casePackId"] == "glyphosate_public_slice_v1"
    assert "/Users/" not in source_lock_text
    assert "file:///Users" not in source_lock_text
    assert {
        "efsa.food_consumption.2026_reviewed",
        "efsa.chemical_monitoring.pesticides",
        "ec.eu_pesticides_database",
        "efsa.openfoodtox.3",
        "pess.2026.ecoenvsafety.120201",
    } <= {item["sourceId"] for item in source_lock["sourceAnchors"]}
    assert all(
        {"retrievedAt", "casePackReviewedAt", "publisherLastReviewed", "retrievalMethod"} <= set(item)
        for item in source_lock["sourceAnchors"]
    )
    assert "sourceLastReviewed" not in source_lock_text
    assert source_lock["sourceAnchors"][0]["url"] == "https://doi.org/10.1016/j.ecoenv.2026.120201"
    matrix_semantics = source_lock["screeningInputPosture"]["matrixSemantics"]
    assert matrix_semantics["residueMatrix"] == "raw_primary_commodity"
    assert matrix_semantics["consumptionMatrix"] == "processed_derivative"
    assert matrix_semantics["processingFactorDirection"] == "raw_residue_to_processed_food"
    assert matrix_semantics["consumptionProxy"] is True
    assert matrix_semantics["consumptionValueBasis"] == "governed_apples_profile_used_as_processed_derivative_proxy"
    assert "No EFSA PRIMo, DEEM, or PESS engine execution is claimed." in source_lock["nonClaims"]

    residue_request = BuildDietaryResidueProfileRequest.model_validate(
        _load_json(CASE_DIR / "inputs" / "residue_profile_request.json")
    )
    residue_profile = runtime.build_residue_profile(residue_request)

    apple_record = next(item for item in residue_profile.records if item.commodity.commodity_code == "apples")
    rice_record = next(item for item in residue_profile.records if item.commodity.commodity_code == "rice")
    assert apple_record.commodity.matched_input_code == "apple_juice"
    assert apple_record.commodity.processed_status == "processed_derivative"
    assert apple_record.review_status == "schema_reviewed_not_source_validated"
    assert rice_record.review_status == "schema_reviewed_not_source_validated"
    _assert_close(
        apple_record.processing_factor,
        expected["processingFactorCheck"]["appliedProcessingFactor"],
    )
    _assert_close(rice_record.processing_factor, 1.0)

    adult_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="adult_general",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["apple_juice", "rice"],
        )
    ).profile
    child_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            required_commodity_codes=["apple_juice", "rice"],
        )
    ).profile

    adult_scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=residue_profile.chemical_identity,
            residue_profile=residue_profile,
            consumption_profile=adult_profile,
            scenario_class=ScenarioClass.POINT_ESTIMATE,
            intake_window_semantic=IntakeWindowSemantic.CHRONIC,
        )
    )
    adult_summary = runtime.summarize_intake(BuildBoundedIntakeSummaryRequest(scenario=adult_scenario))
    adult_expected = expected["deterministic"]["adultChronic"]
    assert adult_summary.intake_window_semantic == "chronic"
    assert adult_summary.scenario_class == "point_estimate"
    _assert_close(adult_summary.total_intake_mg_per_kg_bw_per_day, adult_expected["totalIntakeMgPerKgBwPerDay"])
    apple_expected = adult_expected["commodityContributions"]["apples"]
    assert apple_expected["consumptionProxy"] is True
    assert apple_expected["consumptionValueBasis"] == "governed_apples_profile_used_as_processed_derivative_proxy"
    assert any(
        item["code"] == "processed_derivative_consumption_proxy"
        for item in expected["reviewPosture"]["qualityFlags"]
    )

    adult_contrib_by_code = {
        item.commodity.commodity_code: item
        for item in adult_summary.commodity_contributions
    }
    for commodity_code, contribution_expected in adult_expected["commodityContributions"].items():
        contribution = adult_contrib_by_code[commodity_code]
        _assert_close(contribution.consumption_kg_per_day, contribution_expected["consumptionKgPerDay"])
        _assert_close(contribution.applied_processing_factor, contribution_expected["appliedProcessingFactor"])
        _assert_close(
            contribution.contribution_mg_per_kg_bw_per_day,
            contribution_expected["contributionMgPerKgBwPerDay"],
        )

    child_scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=residue_profile.chemical_identity,
            residue_profile=residue_profile,
            consumption_profile=child_profile,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
        )
    )
    child_summary = runtime.summarize_intake(BuildBoundedIntakeSummaryRequest(scenario=child_scenario))
    child_expected = expected["deterministic"]["childAcute"]
    assert child_summary.intake_window_semantic == "acute"
    assert child_summary.scenario_class == "bounded_acute"
    _assert_close(child_summary.total_intake_mg_per_kg_bw_per_day, child_expected["totalIntakeMgPerKgBwPerDay"])
    _assert_close(
        child_summary.lower_bound_total_intake_mg_per_kg_bw_per_day,
        child_expected["lowerBoundTotalIntakeMgPerKgBwPerDay"],
    )
    _assert_close(
        child_summary.upper_bound_total_intake_mg_per_kg_bw_per_day,
        child_expected["upperBoundTotalIntakeMgPerKgBwPerDay"],
    )

    dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest.model_validate(
            _load_json(CASE_DIR / "inputs" / "adult_raw_survey_request.json")
        )
    )
    survey_summary = runtime.summarize_survey_distribution(
        SummarizeSurveyDistributionRequest(dataset=dataset, residue_profile=residue_profile)
    )
    survey_expected = expected["surveyDistribution"]
    assert survey_expected["weightingMode"] == "unweighted_subject_level_fixture"
    assert survey_summary.total_subjects == survey_expected["totalSubjects"]
    assert survey_summary.consumers_only_count == survey_expected["consumersOnlyCount"]
    _assert_close(survey_summary.zero_intake_prevalence, survey_expected["zeroIntakePrevalence"])
    _assert_close(
        survey_summary.mean_intake_mg_per_kg_bw_per_day,
        survey_expected["meanIntakeMgPerKgBwPerDay"],
    )
    _assert_close(
        survey_summary.percentile_95_mg_per_kg_bw_per_day,
        survey_expected["percentile95MgPerKgBwPerDay"],
    )
    _assert_close(
        survey_expected["weightedMeanIntakeMgPerKgBwPerDay"],
        0.00006491532258064516,
    )
    assert any(
        item["code"] == "percentiles_unstable_tiny_fixture"
        for item in survey_expected["qualityFlags"]
    )

    probabilistic_overlay = _load_json(CASE_DIR / "inputs" / "probabilistic_request_overlay.json")
    probabilistic_summary = runtime.build_probabilistic_intake_summary(
        BuildProbabilisticIntakeSummaryRequest(
            dataset=dataset,
            residue_profile=residue_profile,
            **probabilistic_overlay,
        )
    )
    probabilistic_expected = expected["probabilistic"]
    _assert_close(
        probabilistic_summary.mean_intake_mg_per_kg_bw_per_day,
        probabilistic_expected["meanIntakeMgPerKgBwPerDay"],
    )
    _assert_close(
        probabilistic_summary.percentile_95_mg_per_kg_bw_per_day,
        probabilistic_expected["percentile95MgPerKgBwPerDay"],
    )
    _assert_close(
        probabilistic_summary.zero_intake_prevalence,
        probabilistic_expected["zeroIntakePrevalence"],
    )
    assert any(
        item["code"] == "tiny_synthetic_survey_fixture"
        for item in probabilistic_expected["qualityFlags"]
    )

    uncertainty_payload = {
        **_load_json(CASE_DIR / "inputs" / "uncertainty_request_overlay.json"),
        "dataset": dataset.model_dump(mode="json", by_alias=True),
        "residue_profile": residue_profile.model_dump(mode="json", by_alias=True),
    }
    uncertainty = runtime.build_uncertainty_intake_assessment(
        BuildUncertaintyIntakeAssessmentRequest.model_validate(uncertainty_payload)
    )
    uncertainty_expected = expected["uncertainty"]
    assert uncertainty.assessment_mode == uncertainty_expected["assessmentMode"]
    assert uncertainty.censored_data_policy == uncertainty_expected["censoredDataPolicy"]
    assert sorted(uncertainty.censored_policy_summaries) == uncertainty_expected["censoredPolicySummaryKeys"]
    _assert_close(
        uncertainty.distribution_summary.mean.median,
        uncertainty_expected["meanMedianMgPerKgBwPerDay"],
        rel_tol=1e-8,
    )
    _assert_close(
        uncertainty.distribution_summary.percentile_95.median,
        uncertainty_expected["percentile95MedianMgPerKgBwPerDay"],
        rel_tol=1e-8,
    )
    _assert_close(
        uncertainty.health_reference_exceedance.exceedance_probability.median,
        uncertainty_expected["efsaAdiExceedanceProbabilityMedian"],
    )
    assert "chronic-context" in uncertainty_expected["healthReferenceContext"]
    assert any(
        item["code"] == "tiny_synthetic_survey_fixture"
        for item in uncertainty_expected["qualityFlags"]
    )

    trade_report = runtime.evaluate_global_trade_risk(
        EvaluateGlobalTradeRiskRequest(
            chemical_identity=residue_profile.chemical_identity,
            residue_records=residue_request.residue_records,
            target_jurisdictions=expected["tradeRisk"]["targetJurisdictions"],
        )
    )
    status_by_jurisdiction = {
        item.jurisdiction: item.trade_status
        for item in trade_report.jurisdiction_profiles
    }
    coverage_by_jurisdiction = {
        item.jurisdiction: item.mrl_coverage_status.value
        for item in trade_report.jurisdiction_profiles
    }
    assert status_by_jurisdiction == expected["tradeRisk"]["jurisdictionStatuses"]
    assert coverage_by_jurisdiction == expected["tradeRisk"]["jurisdictionMrlCoverageStatuses"]
    assert expected["tradeRisk"]["legalClearance"] is False
    assert expected["tradeRisk"]["requiresHumanReview"] is True
    assert expected["tradeRisk"]["publicFacingJurisdictionStatuses"]["cn"] == (
        "screening_pass_under_curated_fixture_limits_requires_review"
    )
    assert expected["tradeRisk"]["jurisdictionStatusDetails"]["cn"] == {
        "rawRuntimeStatus": "pass",
        "publicStatus": "screening_pass_under_curated_fixture_limits_requires_review",
        "legalClearance": False,
        "requiresHumanReview": True,
    }
    assert any(status != "pass" for status in status_by_jurisdiction.values())

    pbpk_bundle = export_pbpk_oral_input(
        ExportPbpkOralInputRequest(scenario=child_scenario, summary=child_summary),
        runtime.provenance,
    )
    pbpk_expected = PbpkExternalImportBundle.model_validate(
        _load_json(CASE_DIR / "outputs" / "pbpk_oral_handoff.json")
    )
    _assert_close(
        pbpk_bundle.route_dose_estimate.value_mg_per_kg_bw_per_day,
        pbpk_expected.route_dose_estimate.value_mg_per_kg_bw_per_day,
    )
    assert pbpk_bundle.route_dose_estimate.route == pbpk_expected.route_dose_estimate.route
    assert pbpk_bundle.route_dose_estimate.intake_window_semantic == "acute"
    assert pbpk_bundle.dosing_regimen.schedule == expected["pbpkHandoff"]["schedule"]
    assert any(flag.code == "external_oral_dose_only" for flag in pbpk_expected.quality_flags)
    assert any(flag.code == "external_oral_dose_only" for flag in pbpk_expected.route_dose_estimate.quality_flags)

    evidence_bundle = export_toxclaw_dietary_evidence_bundle(
        ExportToxclawDietaryEvidenceBundleRequest(scenario=adult_scenario, summary=adult_summary),
        runtime.provenance,
    )
    assert [
        item.label for item in evidence_bundle.evidence_items
    ] == expected["toxclawEvidenceBundle"]["evidenceItemLabels"]
    assert all(
        item["reviewStatus"]
        for item in expected["toxclawEvidenceBundle"]["evidenceItemMetadata"]
    )
    assert len(expected["toxclawEvidenceBundle"]["evidenceItemMetadata"]) == len(
        expected["toxclawEvidenceBundle"]["evidenceItemLabels"]
    )
    for row in expected["dualUnitReviewTable"]:
        _assert_close(row["ugPerKgBwPerDay"], row["mgPerKgBwPerDay"] * 1000)
