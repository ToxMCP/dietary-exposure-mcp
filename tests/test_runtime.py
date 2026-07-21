from datetime import date
from pathlib import Path

import pytest

from dietary_mcp.errors import DietaryRegistryError, DietaryValidationError
from dietary_mcp.models import (
    AssessInteroperabilityPreviewReadinessRequest,
    AssessReviewDossierReadinessRequest,
    ApplyResidueEvidenceRequest,
    CheckAdapterImportRequest,
    CheckContaminantMonitoringImportRequest,
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    BuildBoundedIntakeSummaryRequest,
    CompareAdapterImportToWalkthroughRequest,
    DietaryCommodityResidueInput,
    ExportAdapterReviewBundleRequest,
    ExportContaminantMonitoringInterpretationBundleRequest,
    ExportContaminantMonitoringSignoffPacketRequest,
    ExportVersionPinnedContaminantMonitoringReviewDossierRequest,
    ExportInteroperabilityPreviewRequest,
    ExportInteroperabilityRemediationBundleRequest,
    ExportInteroperabilitySignoffPacketRequest,
    ExportMetalsMonitoringInterpretationBundleRequest,
    ExportMetalsMonitoringSignoffPacketRequest,
    ExportScientificFollowUpQueueBundleRequest,
    ExportScientificFollowUpOwnerHandoffPacketRequest,
    ExportScientificFollowUpOwnerRemediationPacketRequest,
    ExportScientificFollowUpOwnerSignoffPacketRequest,
    ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest,
    ExportScientificFollowUpReviewBoardRequest,
    ExportVersionPinnedMetalsMonitoringReviewDossierRequest,
    ExportSanitisedPublicReviewDossierRequest,
    ExportVersionPinnedAdapterReviewDossierRequest,
    IntakeWindowSemantic,
    InteroperabilityActionDecisionStatus,
    InteroperabilitySignoffDecisionInput,
    ContaminantMonitoringSignoffDecisionInput,
    MetalsMonitoringSignoffDecisionInput,
    LookupConsumptionDatasetSupportRequest,
    LookupOccurrenceEvidenceRequest,
    LookupAnalyticalMethodEvidenceRequest,
    LookupContaminantLegalLimitsRequest,
    LookupMetalsOccurrenceRequest,
    LookupMetalsReviewFocusRequest,
    LookupMethodSupportRequest,
    LookupReportingProfilesRequest,
    LookupReferenceValuesRequest,
    ModelFamily,
    ContaminantFamily,
    ResidueSourceType,
    ScenarioClass,
    SelectConsumptionProfileRequest,
    ParseRawSurveyDatasetRequest,
    RawSurveyRecordInput,
    SummarizeSurveyDistributionRequest,
)
from dietary_mcp.runtime import DietaryRuntime


def test_reference_runtime_produces_point_and_bounded_summaries() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.2,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="spinach",
                    residue_concentration_mg_per_kg=0.05,
                    lower_bound_mg_per_kg=0.03,
                    upper_bound_mg_per_kg=0.08,
                    source_type=ResidueSourceType.MODELED,
                ),
            ],
        )
    )
    chronic_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="adult_general",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["apples", "spinach"],
        )
    ).profile
    acute_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            required_commodity_codes=["apples", "spinach"],
        )
    ).profile

    point_summary = runtime.summarize_intake(
        BuildBoundedIntakeSummaryRequest(
            scenario=runtime.build_dietary_intake_scenario(
                BuildDietaryIntakeScenarioRequest(
                    chemical_identity=residue_profile.chemical_identity,
                    residue_profile=residue_profile,
                    consumption_profile=chronic_profile,
                    scenario_class=ScenarioClass.POINT_ESTIMATE,
                    intake_window_semantic=IntakeWindowSemantic.CHRONIC,
                )
            )
        )
    )
    bounded_summary = runtime.summarize_intake(
        BuildBoundedIntakeSummaryRequest(
            scenario=runtime.build_dietary_intake_scenario(
                BuildDietaryIntakeScenarioRequest(
                    chemical_identity=residue_profile.chemical_identity,
                    residue_profile=residue_profile,
                    consumption_profile=acute_profile,
                    scenario_class=ScenarioClass.BOUNDED_ACUTE,
                )
            )
        )
    )

    assert point_summary.total_intake_mg_per_kg_bw_per_day > 0.0
    assert bounded_summary.lower_bound_total_intake_mg_per_kg_bw_per_day is not None
    assert bounded_summary.upper_bound_total_intake_mg_per_kg_bw_per_day is not None
    assert bounded_summary.upper_bound_total_intake_mg_per_kg_bw_per_day >= bounded_summary.total_intake_mg_per_kg_bw_per_day


def test_extended_screening_profiles_cover_new_populations_and_aliases() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    adolescent = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="adolescent_11_17",
            intake_window=IntakeWindowSemantic.ACUTE,
            required_commodity_codes=[
                "orange",
                "fresh_tomatoes",
                "potatoes_raw",
                "wheat_grain",
                "chicken_meat",
                "atlantic_salmon",
            ],
        )
    )
    older_adult = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="older_adult_65_plus",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["apple", "cow_milk", "rice", "salmon_fillet"],
        )
    )

    assert adolescent.profile.profile_id == "eu_adolescent_screening_v1"
    assert adolescent.profile.body_weight_kg == 52.0
    assert sorted(adolescent.matched_commodities) == [
        "chicken",
        "oranges",
        "potatoes",
        "salmon",
        "tomatoes",
        "wheat",
    ]
    assert older_adult.profile.profile_id == "eu_older_adult_screening_v1"
    assert older_adult.profile.body_weight_kg == 68.0
    assert sorted(older_adult.matched_commodities) == ["apples", "milk", "rice", "salmon"]


def test_pregnant_screening_profile_and_new_processed_aliases_are_supported() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    pregnant = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="pregnant_adult",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["egg", "oatmeal", "canned_beans", "whole_milk", "salmon_fillet"],
        )
    )

    assert pregnant.profile.profile_id == "eu_pregnant_adult_screening_v1"
    assert pregnant.profile.body_weight_kg == 62.0
    assert sorted(pregnant.matched_commodities) == [
        "beans_and_pulses",
        "eggs",
        "milk",
        "oats",
        "salmon",
    ]


def test_processed_derivative_alias_uses_governed_processing_factor_and_food_vocabulary_fields() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apple_juice",
                    residue_concentration_mg_per_kg=0.2,
                    source_type=ResidueSourceType.MONITORING,
                )
            ],
        )
    )

    record = residue_profile.records[0]
    assert record.commodity.commodity_code == "apples"
    assert record.commodity.food_group == "fruit_processed"
    assert record.commodity.foodex2_code == "EXAMPLE_FDX2_APPLE_JUICE"
    assert record.commodity.processed_status.value == "processed_derivative"
    assert record.processing_factor == 0.65


def test_apply_residue_evidence_merges_records() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.2,
                    source_type=ResidueSourceType.MONITORING,
                )
            ],
        )
    )
    merged = runtime.apply_residue_evidence(
        ApplyResidueEvidenceRequest(
            residue_profile=residue_profile,
            additional_records=[
                DietaryCommodityResidueInput(
                    commodity_code="rice",
                    residue_concentration_mg_per_kg=0.05,
                    source_type=ResidueSourceType.USER_SUPPLIED,
                )
            ],
        )
    )
    assert {item.commodity.commodity_code for item in merged.residue_profile.records} == {"apples", "rice"}


def test_invalid_residue_unit_and_unknown_commodity_fail() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    with pytest.raises(ValueError):
        runtime.build_residue_profile(
            BuildDietaryResidueProfileRequest(
                chemical_identity={"preferredName": "Example"},
                residue_records=[
                    DietaryCommodityResidueInput(
                        commodity_code="apples",
                        residue_concentration_mg_per_kg=0.2,
                        residue_unit="ppm",
                        source_type=ResidueSourceType.MONITORING,
                    )
                ],
            )
        )


def test_primo_and_deem_adapter_harnesses_emit_explicit_flags() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.2,
                    source_type=ResidueSourceType.MONITORING,
                )
            ],
        )
    )
    chronic_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="adult_general",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["apples"],
        )
    ).profile

    primo_summary = runtime.summarize_intake(
        BuildBoundedIntakeSummaryRequest(
            scenario=runtime.build_dietary_intake_scenario(
                BuildDietaryIntakeScenarioRequest(
                    chemical_identity=residue_profile.chemical_identity,
                    residue_profile=residue_profile,
                    consumption_profile=chronic_profile,
                    scenario_class=ScenarioClass.POINT_ESTIMATE,
                    intake_window_semantic=IntakeWindowSemantic.CHRONIC,
                    model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
                )
            )
        )
    )
    deem_summary = runtime.summarize_intake(
        BuildBoundedIntakeSummaryRequest(
            scenario=runtime.build_dietary_intake_scenario(
                BuildDietaryIntakeScenarioRequest(
                    chemical_identity=residue_profile.chemical_identity,
                    residue_profile=residue_profile,
                    consumption_profile=chronic_profile,
                    scenario_class=ScenarioClass.POINT_ESTIMATE,
                    intake_window_semantic=IntakeWindowSemantic.CHRONIC,
                    model_family=ModelFamily.EPA_DEEM_ADAPTER,
                )
            )
        )
    )

    assert any(flag.code == "efsa_primo_adapter_harness" for flag in primo_summary.quality_flags)
    assert any(ref.source_id == "efsa.primo" for ref in primo_summary.provenance.source_references)
    assert any(flag.code == "epa_deem_adapter_harness" for flag in deem_summary.quality_flags)
    assert any(ref.source_id == "epa.deem.fcid.4_02" for ref in deem_summary.provenance.source_references)

    with pytest.raises(DietaryRegistryError):
        runtime.build_residue_profile(
            BuildDietaryResidueProfileRequest(
                chemical_identity={"preferredName": "Example"},
                residue_records=[
                    DietaryCommodityResidueInput(
                        commodity_code="dragonfruit_powder_capsule",
                        residue_concentration_mg_per_kg=0.2,
                        source_type=ResidueSourceType.MONITORING,
                    )
                ],
            )
        )


def test_check_adapter_import_returns_stable_projection() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday,comment\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448,dominant\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008,secondary\n"
            ),
        )
    )

    assert result.template_name == "efsa_primo_tabular_template"
    assert result.walkthrough_name == "efsa_primo_tabular_alias_case"
    assert result.unmapped_headers == ["comment"]
    assert result.normalized_projection.commodity_codes == ["apples", "milk"]
    assert result.normalized_projection.commodity_contributions[0].foodex2_code == "EXAMPLE_FDX2_APPLES_RAW"
    assert result.normalized_projection.commodity_contributions[0].processed_status.value == "raw_primary_commodity"
    assert "external_adapter_normalized" in result.normalized_projection.quality_flag_codes
    assert "efsa.primo" in result.normalized_projection.source_ids


def test_check_adapter_import_retains_processed_derivative_food_vocabulary_mapping() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apple_juice",
                    residue_concentration_mg_per_kg=0.18,
                    source_type=ResidueSourceType.MONITORING,
                )
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.003276,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf\n"
                "apple_juice,0.003276,0.18,0.28,0.65\n"
            ),
        )
    )

    contribution = result.normalized_projection.commodity_contributions[0]
    assert result.normalized_projection.commodity_codes == ["apples"]
    assert contribution.foodex2_code == "EXAMPLE_FDX2_APPLE_JUICE"
    assert contribution.rpcd_code == "EXAMPLE_RPCD_APPLE_JUICE"
    assert contribution.processed_status.value == "processed_derivative"


def test_compare_adapter_import_to_walkthrough_emits_match_and_review_required() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    matching_result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
            ),
        )
    )
    matching_diff = runtime.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=matching_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )

    assert matching_diff.status == "match"
    assert not matching_diff.mismatch_fields

    review_result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday,comment\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448,dominant\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008,secondary\n"
            ),
        )
    )
    review_diff = runtime.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=review_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )

    assert review_diff.status == "review_required"
    assert "unmapped_headers" in review_diff.mismatch_fields


def test_export_adapter_review_bundle_packages_review_handoff() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
            ),
        )
    )
    comparison = runtime.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=check_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )
    bundle = runtime.export_adapter_review_bundle(
        ExportAdapterReviewBundleRequest(
            check_result=check_result,
            comparison_result=comparison,
        )
    )

    assert bundle.review_status == "match"
    assert bundle.template_name == "efsa_primo_tabular_template"
    assert bundle.walkthrough_name == "efsa_primo_tabular_alias_case"
    assert bundle.matched_field_count == len(comparison.matched_fields)
    assert bundle.mismatch_field_count == 0
    assert any(item.role == "template" for item in bundle.referenced_resources)
    assert any(item.role == "walkthrough" for item in bundle.referenced_resources)


def test_export_version_pinned_adapter_review_dossier_pins_release_and_resources() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
            ),
        )
    )
    comparison = runtime.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=check_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )
    bundle = runtime.export_adapter_review_bundle(
        ExportAdapterReviewBundleRequest(
            check_result=check_result,
            comparison_result=comparison,
        )
    )
    dossier = runtime.export_version_pinned_adapter_review_dossier(
        ExportVersionPinnedAdapterReviewDossierRequest(review_bundle=bundle)
    )

    assert dossier.dossier_status == "match"
    assert dossier.release_metadata.resource_uri == "release://metadata-report"
    assert "adapterTemplateManifest" in dossier.release_metadata.artifact_hashes
    assert "modelGovernanceManifest" in dossier.release_metadata.artifact_hashes
    assert any(item.role == "template_manifest" for item in dossier.pinned_resources)
    assert any(item.role == "walkthrough_manifest" for item in dossier.pinned_resources)
    assert any(item.role == "source_catalog_manifest" for item in dossier.pinned_resources)
    assert any(item.role == "model_governance_manifest" for item in dossier.pinned_resources)
    assert dossier.model_governance_snapshot is not None
    assert dossier.source_governance_snapshot


def test_export_sanitised_public_review_dossier_redacts_confidential_content() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
            ),
        )
    )
    comparison = runtime.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=check_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )
    dossier = runtime.export_version_pinned_adapter_review_dossier(
        ExportVersionPinnedAdapterReviewDossierRequest(
            review_bundle=runtime.export_adapter_review_bundle(
                ExportAdapterReviewBundleRequest(
                    check_result=check_result,
                    comparison_result=comparison,
                )
            )
        )
    )

    sanitised = runtime.export_sanitised_public_review_dossier(
        ExportSanitisedPublicReviewDossierRequest(dossier=dossier)
    )

    assert sanitised.bundle_profile.value == "sanitised_public"
    assert sanitised.source_workflow == "adapter_review_dossier"
    assert sanitised.public_review_bundle.bundle_profile.value == "sanitised_public"
    assert sanitised.legal_limit_reviews == []
    assert sanitised.escalation_required is False
    assert not any(item.confidentiality_tag.value == "confidential" for item in sanitised.pinned_resources)
    assert any(
        item.target_path == "check_result.chemical_identity"
        and item.sanitisation_state.value == "redacted"
        for item in sanitised.sanitisation_records
    )
    assert any(
        item.target_path == "pinned_resources.release_metadata_report"
        and item.sanitisation_state.value == "removed"
        for item in sanitised.sanitisation_records
    )


def test_export_sanitised_public_review_dossier_supports_monitoring_workflows() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    contaminant_check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    contaminant_interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=contaminant_check_result)
    )
    contaminant_dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=contaminant_interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=contaminant_interpretation_bundle,
                    reviewer_id="runtime.sanitised.contaminant",
                    reviewer_role="scientific_reviewer",
                )
            ),
        )
    )

    contaminant_sanitised = runtime.export_sanitised_public_review_dossier(
        ExportSanitisedPublicReviewDossierRequest(dossier=contaminant_dossier)
    )

    assert contaminant_sanitised.source_workflow == "contaminant_monitoring_review_dossier"
    assert len(contaminant_sanitised.legal_limit_reviews) == len(
        contaminant_interpretation_bundle.legal_limit_reviews
    )
    assert contaminant_sanitised.escalation_required == contaminant_dossier.escalation_required
    assert contaminant_sanitised.escalation_action_ids == [
        item.action_id for item in contaminant_dossier.escalation_items
    ]
    assert contaminant_sanitised.emerging_contaminant_snapshot is not None
    assert (
        contaminant_sanitised.public_review_bundle.contaminant_family
        == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS
    )
    assert any(
        item.target_path == "pinned_resources.release_metadata_report"
        and item.sanitisation_state.value == "removed"
        for item in contaminant_sanitised.sanitisation_records
    )

    metals_occurrence_result = runtime.lookup_metals_occurrence(
        LookupMetalsOccurrenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )
    metals_review_focus_result = runtime.lookup_metals_review_focus(
        LookupMetalsReviewFocusRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )
    metals_interpretation_bundle = runtime.export_metals_monitoring_interpretation_bundle(
        ExportMetalsMonitoringInterpretationBundleRequest(
            occurrence_result=metals_occurrence_result,
            review_focus_result=metals_review_focus_result,
        )
    )
    metals_dossier = runtime.export_version_pinned_metals_monitoring_review_dossier(
        ExportVersionPinnedMetalsMonitoringReviewDossierRequest(
            interpretation_bundle=metals_interpretation_bundle,
            signoff_packet=runtime.export_metals_monitoring_signoff_packet(
                ExportMetalsMonitoringSignoffPacketRequest(
                    interpretation_bundle=metals_interpretation_bundle,
                    reviewer_id="runtime.sanitised.metals",
                    reviewer_role="scientific_reviewer",
                )
            ),
        )
    )

    metals_sanitised = runtime.export_sanitised_public_review_dossier(
        ExportSanitisedPublicReviewDossierRequest(dossier=metals_dossier)
    )

    assert metals_sanitised.source_workflow == "metals_monitoring_review_dossier"
    assert len(metals_sanitised.legal_limit_reviews) == len(metals_interpretation_bundle.legal_limit_reviews)
    assert metals_sanitised.escalation_required == metals_dossier.escalation_required
    assert metals_sanitised.escalation_action_ids == [item.action_id for item in metals_dossier.escalation_items]
    assert metals_sanitised.emerging_contaminant_snapshot is not None
    assert (
        metals_sanitised.public_review_bundle.contaminant_family
        == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS
    )
    assert "swordfish" in metals_sanitised.public_review_bundle.high_attention_foods


def test_assess_review_dossier_readiness_returns_profile_specific_status() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
            ),
        )
    )
    comparison = runtime.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=check_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )
    dossier = runtime.export_version_pinned_adapter_review_dossier(
        ExportVersionPinnedAdapterReviewDossierRequest(
            review_bundle=runtime.export_adapter_review_bundle(
                ExportAdapterReviewBundleRequest(
                    check_result=check_result,
                    comparison_result=comparison,
                )
            )
        )
    )

    internal_review = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="eu_internal_review",
        )
    )
    consultation_review = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="eu_consultation_exploratory",
        )
    )
    submission_review = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="eu_submission_candidate",
        )
    )

    assert internal_review.overall_status.value == "review_required"
    assert consultation_review.overall_status.value == "pass"
    assert submission_review.overall_status.value == "fail"
    assert internal_review.scientific_follow_up_items == []
    assert internal_review.scientific_follow_up_queues.open_action_ids == []
    assert internal_review.scientific_follow_up_queues.pending_action_ids == []
    assert any(item.rule_id == "model_submission_not_allowed" for item in submission_review.blocking_rules)


def test_assess_review_dossier_readiness_supports_contaminant_and_metals_dossiers() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    contaminant_check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    contaminant_interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=contaminant_check_result)
    )
    contaminant_signoff_packet = runtime.export_contaminant_monitoring_signoff_packet(
        ExportContaminantMonitoringSignoffPacketRequest(
            interpretation_bundle=contaminant_interpretation_bundle,
            reviewer_id="runtime.contaminant.reviewer",
            reviewer_role="scientific_reviewer",
            decisions=[
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_header_resolution_and_quality_flags",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Header alias resolution and quality flags were reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_occurrence_evidence_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Occurrence evidence context was reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_analytical_method_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Analytical-method context was reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_linked_focus_records",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Linked review-focus records were reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_governance_links",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Governance links were reviewed.",
                    supporting_uris=["docs://contaminant-monitoring-signoff"],
                ),
            ],
        )
    )
    contaminant_dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=contaminant_interpretation_bundle,
            signoff_packet=contaminant_signoff_packet,
        )
    )

    contaminant_internal_review = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=contaminant_dossier,
            target_profile="mercury_internal_review",
        )
    )
    contaminant_consultation_review = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=contaminant_dossier.model_copy(
                update={
                    "notes": contaminant_dossier.notes
                    + ["Consultation-oriented exploratory review remains explicit for this dossier."]
                }
            ),
            target_profile="mercury_consultation_exploratory",
        )
    )
    contaminant_ledger_action_ids = {
        f"review_scientific_ledger.{item.entry_id}"
        for item in contaminant_interpretation_bundle.uncertainty_and_assumption_ledger
        if item.entry_id not in {"governance_submission_posture", "unresolved_review_focus_linkage"}
    }

    assert contaminant_internal_review.overall_status.value == "pass"
    assert contaminant_internal_review.model_governance is None
    assert contaminant_internal_review.emerging_contaminant is not None
    assert len(contaminant_internal_review.legal_limit_reviews) == len(
        contaminant_interpretation_bundle.legal_limit_reviews
    )
    assert (
        contaminant_internal_review.emerging_contaminant.family_id
        == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS
    )
    contaminant_legal_limit_rule = next(
        item
        for item in contaminant_internal_review.applied_rules
        if item.rule_id == "legal_limit_support_explicit"
    )
    assert contaminant_legal_limit_rule.status.value == "pass"
    assert "no_curated_family_coverage" in (contaminant_legal_limit_rule.note or "")
    assert not any(
        item.rule_id == "model_submission_not_allowed"
        for item in contaminant_internal_review.warning_rules
    )
    assert {
        item.action_id for item in contaminant_internal_review.scientific_follow_up_items
    } == contaminant_ledger_action_ids
    assert set(contaminant_internal_review.scientific_follow_up_queues.open_action_ids) == contaminant_ledger_action_ids
    assert set(contaminant_internal_review.scientific_follow_up_queues.pending_action_ids) == contaminant_ledger_action_ids
    assert contaminant_internal_review.scientific_follow_up_queues.acknowledged_action_ids == []
    assert contaminant_internal_review.scientific_follow_up_queues.completed_action_ids == []
    assert contaminant_internal_review.scientific_follow_up_queues.waived_action_ids == []
    assert contaminant_internal_review.scientific_follow_up_queues.escalated_action_ids == []
    assert all(
        item.decision_status == InteroperabilityActionDecisionStatus.PENDING
        for item in contaminant_internal_review.scientific_follow_up_items
    )
    assert contaminant_consultation_review.overall_status.value == "pass"
    assert {
        item.action_id for item in contaminant_consultation_review.scientific_follow_up_items
    } == contaminant_ledger_action_ids
    assert set(contaminant_consultation_review.scientific_follow_up_queues.open_action_ids) == contaminant_ledger_action_ids
    assert set(contaminant_consultation_review.scientific_follow_up_queues.pending_action_ids) == contaminant_ledger_action_ids

    metals_occurrence_result = runtime.lookup_metals_occurrence(
        LookupMetalsOccurrenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )
    metals_review_focus_result = runtime.lookup_metals_review_focus(
        LookupMetalsReviewFocusRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )
    metals_interpretation_bundle = runtime.export_metals_monitoring_interpretation_bundle(
        ExportMetalsMonitoringInterpretationBundleRequest(
            occurrence_result=metals_occurrence_result,
            review_focus_result=metals_review_focus_result,
        )
    )
    metals_signoff_packet = runtime.export_metals_monitoring_signoff_packet(
        ExportMetalsMonitoringSignoffPacketRequest(
            interpretation_bundle=metals_interpretation_bundle,
            reviewer_id="runtime.metals.reviewer",
            reviewer_role="scientific_reviewer",
            decisions=[
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_occurrence_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Occurrence context reviewed.",
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_priority_food_groups",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Priority foods reviewed.",
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_sensitive_populations",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Sensitive populations reviewed.",
                    supporting_uris=["docs://metals-monitoring-signoff"],
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_commodity_focus_prompts",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Commodity prompts reviewed.",
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_governance_links",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Governance links reviewed.",
                    supporting_uris=["docs://metals-monitoring-signoff"],
                ),
            ],
        )
    )
    metals_dossier = runtime.export_version_pinned_metals_monitoring_review_dossier(
        ExportVersionPinnedMetalsMonitoringReviewDossierRequest(
            interpretation_bundle=metals_interpretation_bundle,
            signoff_packet=metals_signoff_packet,
        )
    )
    metals_submission_review = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=metals_dossier,
            target_profile="mercury_submission_candidate",
        )
    )
    metals_ledger_action_ids = {
        f"review_scientific_ledger.{item.entry_id}"
        for item in metals_interpretation_bundle.uncertainty_and_assumption_ledger
        if item.entry_id not in {"governance_submission_posture", "unresolved_occurrence_linkage"}
    }

    assert metals_submission_review.overall_status.value == "review_required"
    assert metals_submission_review.model_governance is None
    assert metals_submission_review.emerging_contaminant is not None
    assert len(metals_submission_review.legal_limit_reviews) == len(
        metals_interpretation_bundle.legal_limit_reviews
    )
    assert {item.action_id for item in metals_submission_review.scientific_follow_up_items} == metals_ledger_action_ids
    assert set(metals_submission_review.scientific_follow_up_queues.open_action_ids) == metals_ledger_action_ids
    assert set(metals_submission_review.scientific_follow_up_queues.pending_action_ids) == metals_ledger_action_ids
    assert metals_submission_review.scientific_follow_up_queues.acknowledged_action_ids == []
    assert metals_submission_review.scientific_follow_up_queues.completed_action_ids == []
    assert metals_submission_review.scientific_follow_up_queues.waived_action_ids == []
    assert metals_submission_review.scientific_follow_up_queues.escalated_action_ids == []
    assert all(
        item.decision_status == InteroperabilityActionDecisionStatus.PENDING
        for item in metals_submission_review.scientific_follow_up_items
    )
    assert any(item.rule_id == "technical_report_dependencies" for item in metals_submission_review.warning_rules)
    assert any(item.rule_id == "legal_limit_support_explicit" for item in metals_submission_review.warning_rules)
    assert not any(item.rule_id == "model_submission_not_allowed" for item in metals_submission_review.blocking_rules)


def test_assess_review_dossier_readiness_surfaces_scientific_follow_up_queues() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.contaminant.reviewer",
                    reviewer_role="scientific_reviewer",
                    decisions=[
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_header_resolution_and_quality_flags",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Header resolution reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_occurrence_evidence_context",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Occurrence evidence reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_analytical_method_context",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Analytical-method evidence reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_linked_focus_records",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Linked focus records reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.row_level_lod_coverage",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Row-level LOD coverage gap reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                            decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                            rationale="Lower-bound handling assumption retained as explicit waiver.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Storage-stability context reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Sampling-plan context reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_governance_links",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Governance links reviewed.",
                            supporting_uris=["docs://contaminant-monitoring-signoff"],
                        ),
                    ],
                )
            ),
        )
    )

    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )

    assert readiness.overall_status.value == "pass"
    assert set(readiness.scientific_follow_up_queues.open_action_ids) == set()
    assert set(readiness.scientific_follow_up_queues.pending_action_ids) == set()
    assert set(readiness.scientific_follow_up_queues.acknowledged_action_ids) == set()
    assert set(readiness.scientific_follow_up_queues.completed_action_ids) == {
        "review_scientific_ledger.row_level_lod_coverage",
        "review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
        "review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
    }
    assert set(readiness.scientific_follow_up_queues.waived_action_ids) == {
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
    }
    assert set(readiness.scientific_follow_up_queues.escalated_action_ids) == {
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
    }


def test_export_scientific_follow_up_queue_bundle_reflects_pending_monitoring_actions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.followup.pending",
                    reviewer_role="scientific_reviewer",
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )

    bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(
            dossier=dossier,
            assessment=readiness,
        )
    )

    assert bundle.source_workflow == "contaminant_monitoring_review_dossier"
    assert bundle.documentation_resource_uri == "docs://contaminant-monitoring-review-dossier"
    assert bundle.open_action_count == 4
    assert bundle.pending_action_count == 4
    assert bundle.escalated_action_count == 0
    assert len(bundle.legal_limit_reviews) == len(readiness.legal_limit_reviews)
    assert bundle.recommended_sequence == readiness.scientific_follow_up_queues.open_action_ids
    assert {item.requested_lane_status.value for item in bundle.legal_limit_reviews} == {
        "no_curated_family_coverage"
    }
    assert {item.action_id for item in bundle.action_items} == {
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
        "review_scientific_ledger.row_level_lod_coverage",
        "review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
        "review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
    }
    assert {
        resource.uri for resource in bundle.referenced_resources
    } >= {
        "contaminant-legal-limits://manifest",
        "contaminant-legal-limits://family/mercury_food_contaminants",
        "contaminant-legal-limits://jurisdiction/eu",
        "jurisdiction-coverage://manifest",
        "jurisdiction-coverage://jurisdiction/eu",
    }
    assert any("Legal-limit support reviews are inherited unchanged from readiness" in note for note in bundle.notes)
    assert all(
        [label.value for label in item.queue_labels] == ["open", "pending"]
        for item in bundle.action_items
    )


def test_export_scientific_follow_up_queue_bundle_prioritizes_escalated_actions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.followup.completed",
                    reviewer_role="scientific_reviewer",
                    decisions=[
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.row_level_lod_coverage",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="LOD coverage reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                            decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                            rationale="Lower-bound handling retained as waiver.",
                            supporting_uris=["docs://contaminant-monitoring-signoff"],
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Storage stability reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Sampling plan reviewed.",
                        ),
                    ],
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )

    bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(
            dossier=dossier,
            assessment=readiness,
        )
    )

    queue_labels_by_action = {
        item.action_id: [label.value for label in item.queue_labels]
        for item in bundle.action_items
    }
    assert bundle.recommended_sequence[0] == (
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    )
    assert queue_labels_by_action[
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ] == ["escalated", "waived"]
    assert queue_labels_by_action["review_scientific_ledger.row_level_lod_coverage"] == ["completed"]
    assert queue_labels_by_action[
        "review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control"
    ] == ["completed"]


def test_export_scientific_follow_up_review_board_routes_pending_actions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.reviewboard.pending",
                    reviewer_role="scientific_reviewer",
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(
            dossier=dossier,
            assessment=readiness,
        )
    )

    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(
            queue_bundle=queue_bundle,
        )
    )

    assert board.source_workflow == "contaminant_monitoring_review_dossier"
    assert board.documentation_resource_uri == "docs://scientific-follow-up-review-board"
    assert board.immediate_action_ids == []
    assert board.current_cycle_action_ids == queue_bundle.recommended_sequence
    assert board.in_progress_action_ids == []
    assert board.closed_action_ids == []
    assert board.recommended_triage_sequence == queue_bundle.recommended_sequence
    assert len(board.legal_limit_reviews) == len(queue_bundle.legal_limit_reviews)
    assert [lane.owner_lane.value for lane in board.owner_lanes] == ["scientific_reviewer"]
    assert [due.due_state.value for due in board.due_state_groups] == ["current_cycle"]
    assert all(item.owner_lane.value == "scientific_reviewer" for item in board.action_items)
    assert all(item.due_state.value == "current_cycle" for item in board.action_items)


def test_export_scientific_follow_up_review_board_prioritizes_review_lead_actions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.reviewboard.mixed",
                    reviewer_role="scientific_reviewer",
                    decisions=[
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.row_level_lod_coverage",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="LOD coverage reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                            decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                            rationale="Lower-bound handling retained as waiver.",
                            supporting_uris=["docs://contaminant-monitoring-signoff"],
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Storage stability reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Sampling plan reviewed.",
                        ),
                    ],
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(
            dossier=dossier,
            assessment=readiness,
        )
    )

    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(
            queue_bundle=queue_bundle,
        )
    )

    owner_lane_by_action = {item.action_id: item.owner_lane.value for item in board.action_items}
    due_state_by_action = {item.action_id: item.due_state.value for item in board.action_items}
    assert board.recommended_triage_sequence[0] == (
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    )
    assert board.immediate_action_ids == [
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ]
    assert owner_lane_by_action[
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ] == "review_lead"
    assert due_state_by_action[
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ] == "immediate"
    assert set(board.closed_action_ids) == {
        "review_scientific_ledger.row_level_lod_coverage",
        "review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
        "review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
    }


def test_export_scientific_follow_up_owner_handoff_packet_filters_scientific_lane() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.ownerhandoff.pending",
                    reviewer_role="scientific_reviewer",
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(
            dossier=dossier,
            assessment=readiness,
        )
    )
    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(
            queue_bundle=queue_bundle,
        )
    )

    packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(
            board=board,
            owner_lane="scientific_reviewer",
        )
    )

    assert packet.source_workflow == "contaminant_monitoring_review_dossier"
    assert packet.documentation_resource_uri == "docs://scientific-follow-up-owner-handoff"
    assert packet.owner_lane.value == "scientific_reviewer"
    assert packet.action_count == 4
    assert packet.blocking_action_ids == []
    assert packet.current_cycle_action_ids == board.current_cycle_action_ids
    assert packet.immediate_action_ids == []
    assert len(packet.legal_limit_reviews) == len(board.legal_limit_reviews)
    assert packet.recommended_owner_sequence == board.recommended_triage_sequence
    assert [group.due_state.value for group in packet.due_state_groups] == ["current_cycle"]


def test_export_scientific_follow_up_owner_handoff_packet_filters_review_lead_due_state() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.ownerhandoff.mixed",
                    reviewer_role="scientific_reviewer",
                    decisions=[
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.row_level_lod_coverage",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="LOD coverage reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                            decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                            rationale="Lower-bound handling retained as waiver.",
                            supporting_uris=["docs://contaminant-monitoring-signoff"],
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Storage stability reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Sampling plan reviewed.",
                        ),
                    ],
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(
            dossier=dossier,
            assessment=readiness,
        )
    )
    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(
            queue_bundle=queue_bundle,
        )
    )

    packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(
            board=board,
            owner_lane="review_lead",
            due_state_filter=["immediate"],
        )
    )

    assert packet.owner_lane.value == "review_lead"
    assert [due_state.value for due_state in packet.due_state_filter] == ["immediate"]
    assert [item.action_id for item in packet.action_items] == [
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ]
    assert packet.immediate_action_ids == [
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ]
    assert packet.closed_action_ids == []
    assert packet.recommended_owner_sequence == [
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ]


def test_export_scientific_follow_up_owner_remediation_packet_routes_current_cycle_actions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.ownerremediation.pending",
                    reviewer_role="scientific_reviewer",
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(
            dossier=dossier,
            assessment=readiness,
        )
    )
    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(queue_bundle=queue_bundle)
    )
    handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(
            board=board,
            owner_lane="scientific_reviewer",
        )
    )

    packet = runtime.export_scientific_follow_up_owner_remediation_packet(
        ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=handoff_packet)
    )

    assert packet.source_workflow == "contaminant_monitoring_review_dossier"
    assert packet.documentation_resource_uri == "docs://scientific-follow-up-owner-remediation"
    assert packet.owner_lane.value == "scientific_reviewer"
    assert packet.action_count == 4
    assert len(packet.legal_limit_reviews) == len(handoff_packet.legal_limit_reviews)
    assert packet.resolve_now_action_ids == []
    assert packet.review_this_cycle_action_ids == [
        "review_scientific_ledger.row_level_lod_coverage",
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
        "review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
        "review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
    ]
    assert packet.record_closure_action_ids == []
    assert [group.remediation_class.value for group in packet.remediation_class_groups] == ["review_this_cycle"]


def test_export_scientific_follow_up_owner_remediation_packet_routes_immediate_actions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.ownerremediation.mixed",
                    reviewer_role="scientific_reviewer",
                    decisions=[
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.row_level_lod_coverage",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="LOD coverage reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                            decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                            rationale="Lower-bound handling retained as waiver.",
                            supporting_uris=["docs://contaminant-monitoring-signoff"],
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Storage stability reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Sampling plan reviewed.",
                        ),
                    ],
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(
            dossier=dossier,
            assessment=readiness,
        )
    )
    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(queue_bundle=queue_bundle)
    )
    handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(
            board=board,
            owner_lane="review_lead",
            due_state_filter=["immediate"],
        )
    )

    packet = runtime.export_scientific_follow_up_owner_remediation_packet(
        ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=handoff_packet)
    )

    assert packet.owner_lane.value == "review_lead"
    assert [due_state.value for due_state in packet.due_state_filter] == ["immediate"]
    assert packet.resolve_now_action_ids == [
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ]
    assert packet.review_this_cycle_action_ids == []
    assert packet.recommended_remediation_sequence == [
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ]
    assert [group.remediation_class.value for group in packet.remediation_class_groups] == ["resolve_now"]


def test_export_scientific_follow_up_owner_remediation_packet_routes_closed_actions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.ownerremediation.closed",
                    reviewer_role="scientific_reviewer",
                    decisions=[
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.row_level_lod_coverage",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="LOD coverage reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                            decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                            rationale="Lower-bound handling retained as waiver.",
                            supporting_uris=["docs://contaminant-monitoring-signoff"],
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Storage stability reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Sampling plan reviewed.",
                        ),
                    ],
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(
            dossier=dossier,
            assessment=readiness,
        )
    )
    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(queue_bundle=queue_bundle)
    )
    handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(
            board=board,
            owner_lane="scientific_reviewer",
            due_state_filter=["closed"],
        )
    )

    packet = runtime.export_scientific_follow_up_owner_remediation_packet(
        ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=handoff_packet)
    )

    assert [due_state.value for due_state in packet.due_state_filter] == ["closed"]
    assert packet.resolve_now_action_ids == []
    assert packet.record_closure_action_ids == [
        "review_scientific_ledger.row_level_lod_coverage",
        "review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
        "review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
    ]
    assert [group.remediation_class.value for group in packet.remediation_class_groups] == ["record_closure"]
    assert packet.recommended_remediation_sequence == [
        "review_scientific_ledger.row_level_lod_coverage",
        "review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
        "review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
    ]


def test_export_scientific_follow_up_owner_signoff_packet_tracks_pending_actions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.owner.signoff.pending",
                    reviewer_role="scientific_reviewer",
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(dossier=dossier, assessment=readiness)
    )
    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(queue_bundle=queue_bundle)
    )
    handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(board=board, owner_lane="scientific_reviewer")
    )
    remediation_packet = runtime.export_scientific_follow_up_owner_remediation_packet(
        ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=handoff_packet)
    )

    packet = runtime.export_scientific_follow_up_owner_signoff_packet(
        ExportScientificFollowUpOwnerSignoffPacketRequest(
            remediation_packet=remediation_packet,
            reviewer_id="runtime.owner.signoff.pending",
            reviewer_role="scientific_reviewer",
        )
    )

    assert packet.overall_signoff_status.value == "open"
    assert packet.documentation_resource_uri == "docs://scientific-follow-up-owner-signoff"
    assert len(packet.legal_limit_reviews) == len(remediation_packet.legal_limit_reviews)
    assert packet.pending_action_ids == remediation_packet.review_this_cycle_action_ids
    assert packet.acknowledged_action_ids == []
    assert packet.completed_action_ids == []
    assert packet.waived_action_ids == []


def test_export_scientific_follow_up_owner_signoff_packet_tracks_waiver_state() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.owner.signoff.waiver",
                    reviewer_role="scientific_reviewer",
                    decisions=[
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.row_level_lod_coverage",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="LOD coverage reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                            decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                            rationale="Lower-bound handling retained as waiver.",
                            supporting_uris=["docs://contaminant-monitoring-signoff"],
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Storage stability reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Sampling plan reviewed.",
                        ),
                    ],
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(dossier=dossier, assessment=readiness)
    )
    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(queue_bundle=queue_bundle)
    )
    handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(
            board=board,
            owner_lane="review_lead",
            due_state_filter=["immediate"],
        )
    )
    remediation_packet = runtime.export_scientific_follow_up_owner_remediation_packet(
        ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=handoff_packet)
    )

    packet = runtime.export_scientific_follow_up_owner_signoff_packet(
        ExportScientificFollowUpOwnerSignoffPacketRequest(
            remediation_packet=remediation_packet,
            reviewer_id="runtime.owner.signoff.review_lead",
            reviewer_role="review_lead",
            decisions=[
                {
                    "actionId": "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                    "decisionStatus": "waived",
                    "rationale": "Lower-bound handling retained with explicit waiver.",
                    "reviewedAt": "2026-04-12",
                }
            ],
        )
    )

    assert packet.overall_signoff_status.value == "signed_off_with_waivers"
    assert packet.pending_action_ids == []
    assert packet.waived_action_ids == [
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ]
    assert packet.resolve_now_action_ids == [
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ]


def test_export_scientific_follow_up_owner_signoff_packet_tracks_completed_state() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.owner.signoff.completed",
                    reviewer_role="scientific_reviewer",
                    decisions=[
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.row_level_lod_coverage",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="LOD coverage reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                            decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                            rationale="Lower-bound handling retained as waiver.",
                            supporting_uris=["docs://contaminant-monitoring-signoff"],
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Storage stability reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Sampling plan reviewed.",
                        ),
                    ],
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(dossier=dossier, assessment=readiness)
    )
    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(queue_bundle=queue_bundle)
    )
    handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(
            board=board,
            owner_lane="scientific_reviewer",
            due_state_filter=["closed"],
        )
    )
    remediation_packet = runtime.export_scientific_follow_up_owner_remediation_packet(
        ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=handoff_packet)
    )

    packet = runtime.export_scientific_follow_up_owner_signoff_packet(
        ExportScientificFollowUpOwnerSignoffPacketRequest(
            remediation_packet=remediation_packet,
            reviewer_id="runtime.owner.signoff.completed",
            reviewer_role="scientific_reviewer",
            decisions=[
                {
                    "actionId": "review_scientific_ledger.row_level_lod_coverage",
                    "decisionStatus": "completed",
                    "rationale": "Closed action retained as completed review.",
                    "reviewedAt": "2026-04-12",
                },
                {
                    "actionId": "review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                    "decisionStatus": "completed",
                    "rationale": "Closed action retained as completed review.",
                    "reviewedAt": "2026-04-12",
                },
                {
                    "actionId": "review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                    "decisionStatus": "completed",
                    "rationale": "Closed action retained as completed review.",
                    "reviewedAt": "2026-04-12",
                },
            ],
        )
    )

    assert packet.overall_signoff_status.value == "signed_off"
    assert packet.pending_action_ids == []
    assert packet.completed_action_ids == [
        "review_scientific_ledger.row_level_lod_coverage",
        "review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
        "review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
    ]
    assert packet.record_closure_action_ids == [
        "review_scientific_ledger.row_level_lod_coverage",
        "review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
        "review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
    ]


def test_export_version_pinned_scientific_follow_up_owner_signoff_dossier_tracks_open_lane() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    source_dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.owner.signoff.dossier.pending",
                    reviewer_role="scientific_reviewer",
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=source_dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(dossier=source_dossier, assessment=readiness)
    )
    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(queue_bundle=queue_bundle)
    )
    handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(board=board, owner_lane="scientific_reviewer")
    )
    remediation_packet = runtime.export_scientific_follow_up_owner_remediation_packet(
        ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=handoff_packet)
    )
    signoff_packet = runtime.export_scientific_follow_up_owner_signoff_packet(
        ExportScientificFollowUpOwnerSignoffPacketRequest(
            remediation_packet=remediation_packet,
            reviewer_id="runtime.owner.signoff.dossier.pending",
            reviewer_role="scientific_reviewer",
        )
    )

    dossier = runtime.export_version_pinned_scientific_follow_up_owner_signoff_dossier(
        ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest(
            source_dossier=source_dossier,
            signoff_packet=signoff_packet,
        )
    )

    assert dossier.dossier_status.value == "open"
    assert dossier.source_workflow == "contaminant_monitoring_review_dossier"
    assert dossier.escalation_required is False
    assert dossier.model_governance_snapshot is None
    assert dossier.emerging_contaminant_snapshot is not None
    assert len(dossier.legal_limit_reviews) == len(signoff_packet.legal_limit_reviews)
    assert [item.action_id for item in dossier.escalation_items] == signoff_packet.unresolved_blocking_action_ids


def test_export_version_pinned_scientific_follow_up_owner_signoff_dossier_tracks_waiver() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    source_dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.owner.signoff.dossier.waiver",
                    reviewer_role="scientific_reviewer",
                    decisions=[
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.row_level_lod_coverage",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="LOD coverage reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                            decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                            rationale="Lower-bound handling retained as waiver.",
                            supporting_uris=["docs://contaminant-monitoring-signoff"],
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Storage stability reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Sampling plan reviewed.",
                        ),
                    ],
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=source_dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(dossier=source_dossier, assessment=readiness)
    )
    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(queue_bundle=queue_bundle)
    )
    handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(
            board=board,
            owner_lane="review_lead",
            due_state_filter=["immediate"],
        )
    )
    remediation_packet = runtime.export_scientific_follow_up_owner_remediation_packet(
        ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=handoff_packet)
    )
    signoff_packet = runtime.export_scientific_follow_up_owner_signoff_packet(
        ExportScientificFollowUpOwnerSignoffPacketRequest(
            remediation_packet=remediation_packet,
            reviewer_id="runtime.owner.signoff.dossier.review_lead",
            reviewer_role="review_lead",
            decisions=[
                {
                    "actionId": "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                    "decisionStatus": "waived",
                    "rationale": "Lower-bound handling retained with explicit waiver.",
                    "reviewedAt": "2026-04-12",
                }
            ],
        )
    )

    dossier = runtime.export_version_pinned_scientific_follow_up_owner_signoff_dossier(
        ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest(
            source_dossier=source_dossier,
            signoff_packet=signoff_packet,
        )
    )

    assert dossier.dossier_status.value == "signed_off_with_waivers"
    assert dossier.escalation_required is True
    assert [item.action_id for item in dossier.escalation_items] == [
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ]
    assert dossier.escalation_items[0].escalation_type.value == "waiver_review"


def test_export_version_pinned_scientific_follow_up_owner_signoff_dossier_supports_adapter_source() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example", "casrn": "100-00-0"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
            ),
        )
    )
    comparison = runtime.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=check_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )
    review_bundle = runtime.export_adapter_review_bundle(
        ExportAdapterReviewBundleRequest(
            check_result=check_result,
            comparison_result=comparison,
        )
    )
    source_dossier = runtime.export_version_pinned_adapter_review_dossier(
        ExportVersionPinnedAdapterReviewDossierRequest(review_bundle=review_bundle)
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=source_dossier,
            target_profile="eu_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(dossier=source_dossier, assessment=readiness)
    )
    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(queue_bundle=queue_bundle)
    )
    handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(board=board, owner_lane="scientific_reviewer")
    )
    remediation_packet = runtime.export_scientific_follow_up_owner_remediation_packet(
        ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=handoff_packet)
    )
    signoff_packet = runtime.export_scientific_follow_up_owner_signoff_packet(
        ExportScientificFollowUpOwnerSignoffPacketRequest(
            remediation_packet=remediation_packet,
            reviewer_id="runtime.owner.signoff.dossier.adapter",
            reviewer_role="scientific_reviewer",
        )
    )

    dossier = runtime.export_version_pinned_scientific_follow_up_owner_signoff_dossier(
        ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest(
            source_dossier=source_dossier,
            signoff_packet=signoff_packet,
        )
    )

    assert dossier.source_workflow == "adapter_review_dossier"
    assert dossier.dossier_status.value == "signed_off"
    assert dossier.escalation_required is False
    assert dossier.model_governance_snapshot is not None
    assert dossier.emerging_contaminant_snapshot is None


def test_export_interoperability_preview_returns_governed_projection() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
            ),
        )
    )
    comparison = runtime.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=check_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )
    dossier = runtime.export_version_pinned_adapter_review_dossier(
        ExportVersionPinnedAdapterReviewDossierRequest(
            review_bundle=runtime.export_adapter_review_bundle(
                ExportAdapterReviewBundleRequest(
                    check_result=check_result,
                    comparison_result=comparison,
                )
            )
        )
    )

    preview = runtime.export_interoperability_preview(
        ExportInteroperabilityPreviewRequest(
            dossier=dossier,
            target_profile="oht_85_iuclid_json_preview",
        )
    )

    assert preview.preview_status.value == "review_required"
    assert preview.target_profile.profile_id == "oht_85_iuclid_json_preview"
    assert preview.target_document["oht85_8"]["dietaryExposure"]["commodityContributions"]
    assert any(item.local_path == "review_bundle.check_result.input_headers" for item in preview.unsupported_fields)


def test_assess_interoperability_preview_readiness_returns_gate_specific_status() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
            ),
        )
    )
    comparison = runtime.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=check_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )
    dossier = runtime.export_version_pinned_adapter_review_dossier(
        ExportVersionPinnedAdapterReviewDossierRequest(
            review_bundle=runtime.export_adapter_review_bundle(
                ExportAdapterReviewBundleRequest(
                    check_result=check_result,
                    comparison_result=comparison,
                )
            )
        )
    )
    preview = runtime.export_interoperability_preview(
        ExportInteroperabilityPreviewRequest(
            dossier=dossier,
            target_profile="oht_85_iuclid_json_preview",
        )
    )

    internal_exchange = runtime.assess_interoperability_preview_readiness(
        AssessInteroperabilityPreviewReadinessRequest(
            dossier=dossier,
            preview=preview,
            target_profile="eu_internal_exchange_preview",
        )
    )
    submission_candidate = runtime.assess_interoperability_preview_readiness(
        AssessInteroperabilityPreviewReadinessRequest(
            dossier=dossier,
            preview=preview,
            target_profile="eu_submission_xml_candidate",
        )
    )

    assert internal_exchange.overall_status.value == "review_required"
    assert submission_candidate.overall_status.value == "fail"
    assert any(item.rule_id == "preview_unsupported_fields_allowed" for item in internal_exchange.warning_rules)
    assert any(item.rule_id == "linked_dossier_readiness" for item in submission_candidate.blocking_rules)


def test_export_interoperability_remediation_bundle_returns_governed_actions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
            ),
        )
    )
    comparison = runtime.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=check_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )
    dossier = runtime.export_version_pinned_adapter_review_dossier(
        ExportVersionPinnedAdapterReviewDossierRequest(
            review_bundle=runtime.export_adapter_review_bundle(
                ExportAdapterReviewBundleRequest(
                    check_result=check_result,
                    comparison_result=comparison,
                )
            )
        )
    )
    preview = runtime.export_interoperability_preview(
        ExportInteroperabilityPreviewRequest(
            dossier=dossier,
            target_profile="oht_85_iuclid_json_preview",
        )
    )
    assessment = runtime.assess_interoperability_preview_readiness(
        AssessInteroperabilityPreviewReadinessRequest(
            dossier=dossier,
            preview=preview,
            target_profile="eu_internal_exchange_preview",
        )
    )
    bundle = runtime.export_interoperability_remediation_bundle(
        ExportInteroperabilityRemediationBundleRequest(
            dossier=dossier,
            preview=preview,
            assessment=assessment,
        )
    )

    assert bundle.overall_status == assessment.overall_status
    assert bundle.blocking_action_count == 0
    assert bundle.warning_action_count == 3
    assert [item.action_id for item in bundle.action_items] == [
        "upgrade_linked_dossier_readiness",
        "review_unsupported_preview_fields",
        "replace_non_direct_mappings",
    ]
    assert bundle.catalog_resource_uri == "interoperability-remediation://catalog"
    assert bundle.documentation_resource_uri == "docs://interoperability-remediation"
    assert any(item.role == "interoperability_remediation_docs" for item in bundle.referenced_resources)


def test_export_interoperability_signoff_packet_tracks_waivers_and_unresolved_blocking_actions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
            ),
        )
    )
    comparison = runtime.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=check_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )
    dossier = runtime.export_version_pinned_adapter_review_dossier(
        ExportVersionPinnedAdapterReviewDossierRequest(
            review_bundle=runtime.export_adapter_review_bundle(
                ExportAdapterReviewBundleRequest(
                    check_result=check_result,
                    comparison_result=comparison,
                )
            )
        )
    )
    preview = runtime.export_interoperability_preview(
        ExportInteroperabilityPreviewRequest(
            dossier=dossier,
            target_profile="oht_85_iuclid_json_preview",
        )
    )
    assessment = runtime.assess_interoperability_preview_readiness(
        AssessInteroperabilityPreviewReadinessRequest(
            dossier=dossier,
            preview=preview,
            target_profile="eu_internal_exchange_preview",
        )
    )
    remediation_bundle = runtime.export_interoperability_remediation_bundle(
        ExportInteroperabilityRemediationBundleRequest(
            dossier=dossier,
            preview=preview,
            assessment=assessment,
        )
    )

    packet = runtime.export_interoperability_signoff_packet(
        ExportInteroperabilitySignoffPacketRequest(
            remediation_bundle=remediation_bundle,
            reviewer_id="runtime.reviewer",
            reviewer_role="regulatory_reviewer",
            decisions=[
                InteroperabilitySignoffDecisionInput(
                    action_id="upgrade_linked_dossier_readiness",
                    decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                    rationale="Internal example waiver retained explicitly in the signoff packet.",
                    reviewed_at="2026-04-11",
                    supporting_uris=["docs://regulatory-governance"],
                ),
                InteroperabilitySignoffDecisionInput(
                    action_id="review_unsupported_preview_fields",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Unsupported preview fields were reviewed.",
                    reviewed_at="2026-04-11",
                ),
                InteroperabilitySignoffDecisionInput(
                    action_id="replace_non_direct_mappings",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Derived mappings were accepted for this staged preview packet.",
                    reviewed_at="2026-04-11",
                ),
            ],
        )
    )

    assert packet.overall_signoff_status.value == "signed_off_with_waivers"
    assert packet.waived_action_ids == ["upgrade_linked_dossier_readiness"]
    assert set(packet.completed_action_ids) == {
        "review_unsupported_preview_fields",
        "replace_non_direct_mappings",
    }
    assert not packet.unresolved_blocking_action_ids
    assert any(item.role == "interoperability_signoff_docs" for item in packet.referenced_resources)


def test_export_interoperability_signoff_packet_rejects_duplicate_action_decisions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
            ),
        )
    )
    comparison = runtime.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=check_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )
    dossier = runtime.export_version_pinned_adapter_review_dossier(
        ExportVersionPinnedAdapterReviewDossierRequest(
            review_bundle=runtime.export_adapter_review_bundle(
                ExportAdapterReviewBundleRequest(
                    check_result=check_result,
                    comparison_result=comparison,
                )
            )
        )
    )
    preview = runtime.export_interoperability_preview(
        ExportInteroperabilityPreviewRequest(
            dossier=dossier,
            target_profile="oht_85_iuclid_json_preview",
        )
    )
    assessment = runtime.assess_interoperability_preview_readiness(
        AssessInteroperabilityPreviewReadinessRequest(
            dossier=dossier,
            preview=preview,
            target_profile="eu_internal_exchange_preview",
        )
    )
    remediation_bundle = runtime.export_interoperability_remediation_bundle(
        ExportInteroperabilityRemediationBundleRequest(
            dossier=dossier,
            preview=preview,
            assessment=assessment,
        )
    )

    with pytest.raises(DietaryValidationError):
        runtime.export_interoperability_signoff_packet(
            ExportInteroperabilitySignoffPacketRequest(
                remediation_bundle=remediation_bundle,
                reviewer_id="runtime.reviewer",
                reviewer_role="regulatory_reviewer",
                decisions=[
                    InteroperabilitySignoffDecisionInput(
                        action_id="upgrade_linked_dossier_readiness",
                        decision_status=InteroperabilityActionDecisionStatus.ACKNOWLEDGED,
                        rationale="First decision.",
                    ),
                    InteroperabilitySignoffDecisionInput(
                        action_id="upgrade_linked_dossier_readiness",
                        decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                        rationale="Duplicate decision.",
                    ),
                ],
            )
        )


def test_reference_value_lookup_preserves_authority_conflicts() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="glyphosate",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
        )
    )

    assert {item.record_id for item in result.matched_records} >= {
        "efsa.openfoodtox.glyphosate.adi",
        "jmpr.glyphosate.adi",
    }
    assert {item.conflict_group_id for item in result.visible_conflicts} == {"glyphosate.adi.authority_conflict"}


def test_reference_value_lookup_preserves_jurisdiction_separation_and_gap_flags() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    us_result = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="glyphosate",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="us",
        )
    )
    eu_result = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="glyphosate",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="eu",
        )
    )
    codex_result = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="glyphosate",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="codex_global",
        )
    )

    us_records = {item.record_id for item in us_result.matched_records}
    eu_records = {item.record_id for item in eu_result.matched_records}
    codex_records = {item.record_id for item in codex_result.matched_records}

    assert not us_records
    assert {flag.code for flag in us_result.quality_flags} == {
        "no_jurisdiction_specific_reference_value",
        "family_curated_without_reference_value",
    }
    assert {item.coverage_id for item in us_result.coverage_summaries} == {
        "us.pesticide_residue.glyphosate.wave1"
    }
    assert {item.coverage_level.value for item in us_result.coverage_summaries} == {"deep_curated"}
    assert us_result.requested_jurisdiction_status.value == "family_curated_without_reference_value"
    assert us_result.curated_support_types == ["enforcement_records", "legal_anchors"]
    assert eu_records == {
        "efsa.openfoodtox.glyphosate.adi",
        "efsa.openfoodtox.glyphosate.arfd",
        "efsa.openfoodtox.glyphosate.arfd.2015",
    }
    assert codex_records == {"jmpr.glyphosate.adi"}
    assert {item.coverage_level.value for item in codex_result.coverage_summaries} == {"deep_curated"}
    assert eu_result.requested_jurisdiction_status.value == "exact_jurisdiction_value_present"
    assert codex_result.requested_jurisdiction_status.value == "exact_jurisdiction_value_present"
    assert "jmpr.glyphosate.adi" not in eu_records
    assert "efsa.openfoodtox.glyphosate.adi" not in codex_records


def test_reference_value_lookup_supports_acetamiprid_and_pfas_records() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    acetamiprid = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="acetamiprid",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
        )
    )
    pfas = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="sum_pfoa_pfna_pfhxs_pfos",
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
        )
    )

    assert {item.record_id for item in acetamiprid.matched_records} == {
        "efsa.openfoodtox.acetamiprid.adi",
        "efsa.openfoodtox.acetamiprid.arfd",
        "jmpr.acetamiprid.adi.2011",
        "cn.nhc.acetamiprid.adi.2026",
    }
    assert {item.record_id for item in pfas.matched_records} == {"efsa.pfas.sum4.twi"}
    assert not pfas.visible_conflicts


def test_reference_value_lookup_supports_codex_and_china_specific_pesticide_records() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    codex = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="imidacloprid",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="codex_global",
        )
    )
    china = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="acetamiprid",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="cn",
        )
    )

    assert {item.record_id for item in codex.matched_records} == {"jmpr.imidacloprid.adi.2001"}
    assert {item.record_id for item in china.matched_records} == {"cn.nhc.acetamiprid.adi.2026"}
    assert {item.coverage_level.value for item in codex.coverage_summaries} == {"deep_curated"}
    assert {item.coverage_level.value for item in china.coverage_summaries} == {"deep_curated"}
    assert codex.requested_jurisdiction_status.value == "exact_jurisdiction_value_present"
    assert china.requested_jurisdiction_status.value == "exact_jurisdiction_value_present"
    assert not codex.quality_flags
    assert not china.quality_flags


def test_reference_value_lookup_exposes_explicit_gap_flags_for_non_eu_contaminants() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    us_pfas = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="sum_pfoa_pfna_pfhxs_pfos",
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            jurisdiction="us",
        )
    )
    codex_cadmium = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="cadmium",
            contaminant_family=ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
            jurisdiction="codex_global",
        )
    )
    us_acetamiprid = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="acetamiprid",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="us",
        )
    )
    china_lead = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="lead",
            contaminant_family=ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
            jurisdiction="cn",
        )
    )

    assert not us_pfas.matched_records
    assert not codex_cadmium.matched_records
    assert not us_acetamiprid.matched_records
    assert not china_lead.matched_records
    assert {flag.code for flag in us_pfas.quality_flags} == {
        "coverage_gap",
        "no_jurisdiction_specific_reference_value",
    }
    assert {flag.code for flag in codex_cadmium.quality_flags} == {
        "no_jurisdiction_specific_reference_value",
        "family_curated_without_reference_value",
    }
    assert {flag.code for flag in us_acetamiprid.quality_flags} == {
        "no_jurisdiction_specific_reference_value",
        "anchor_only_family_without_reference_value",
    }
    assert {flag.code for flag in china_lead.quality_flags} == {
        "no_jurisdiction_specific_reference_value",
        "family_curated_without_reference_value",
    }
    assert {item.coverage_level.value for item in us_pfas.coverage_summaries} == {"explicit_gap"}
    assert {item.coverage_level.value for item in codex_cadmium.coverage_summaries} == {"deep_curated"}
    assert {item.coverage_level.value for item in us_acetamiprid.coverage_summaries} == {"anchor_only"}
    assert {item.coverage_level.value for item in china_lead.coverage_summaries} == {"deep_curated"}
    assert us_pfas.requested_jurisdiction_status.value == "explicit_gap"
    assert codex_cadmium.requested_jurisdiction_status.value == "family_curated_without_reference_value"
    assert us_acetamiprid.requested_jurisdiction_status.value == "anchor_only_family"
    assert china_lead.requested_jurisdiction_status.value == "family_curated_without_reference_value"


def test_contaminant_legal_limit_lookup_supports_us_codex_and_china_exact_records() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    us_lead = runtime.lookup_contaminant_legal_limits(
        LookupContaminantLegalLimitsRequest(
            contaminant_family=ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
            jurisdiction="us",
            substance_key="lead",
        )
    )
    codex_apple_juice_lead = runtime.lookup_contaminant_legal_limits(
        LookupContaminantLegalLimitsRequest(
            contaminant_family=ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
            jurisdiction="codex_global",
            substance_key="lead",
            commodity_code="apple_juice",
        )
    )
    codex_olive_oil_arsenic = runtime.lookup_contaminant_legal_limits(
        LookupContaminantLegalLimitsRequest(
            contaminant_family=ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
            jurisdiction="codex_global",
            substance_key="inorganic_arsenic",
            commodity_code="olive_oil",
        )
    )
    china_rice_arsenic = runtime.lookup_contaminant_legal_limits(
        LookupContaminantLegalLimitsRequest(
            contaminant_family=ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
            jurisdiction="cn",
            substance_key="inorganic_arsenic",
            commodity_code="rice",
        )
    )

    assert {item.record_id for item in us_lead.matched_records} == {
        "us.fda.lead.processed_foods.general_baby_foods.ml.2025",
        "us.fda.lead.processed_foods.root_vegetables.ml.2025",
        "us.fda.lead.processed_foods.dry_infant_cereals.ml.2025",
    }
    assert {item.authority_id for item in us_lead.legal_authorities} == {
        "us.fda.lead.processed_foods.action_levels.2025"
    }
    assert {item.coverage_level.value for item in us_lead.coverage_summaries} == {"deep_curated"}
    assert us_lead.requested_lane_status.value == "exact_curated_match"
    assert us_lead.overall_submission_use.value == "review_required"

    assert {item.record_id for item in codex_apple_juice_lead.matched_records} == {
        "codex.cxs_193_1995.lead.apple_juice.ml.2025"
    }
    assert {item.authority_id for item in codex_apple_juice_lead.legal_authorities} == {
        "codex.cccf.cxs_193_1995.current_2025.lead"
    }
    assert {item.coverage_level.value for item in codex_apple_juice_lead.coverage_summaries} == {"deep_curated"}
    assert codex_apple_juice_lead.requested_lane_status.value == "exact_curated_match"
    assert codex_apple_juice_lead.overall_submission_use.value == "review_required"

    assert {item.record_id for item in codex_olive_oil_arsenic.matched_records} == {
        "codex.cxs_193_1995.inorganic_arsenic.olive_oil.ml.2025"
    }
    assert {item.authority_id for item in codex_olive_oil_arsenic.legal_authorities} == {
        "codex.cccf.cxs_193_1995.current_2025.inorganic_arsenic"
    }
    assert {item.coverage_level.value for item in codex_olive_oil_arsenic.coverage_summaries} == {"deep_curated"}
    assert codex_olive_oil_arsenic.requested_lane_status.value == "exact_curated_match"
    assert codex_olive_oil_arsenic.overall_submission_use.value == "review_required"

    assert {item.record_id for item in china_rice_arsenic.matched_records} == {
        "cn.nhc.inorganic_arsenic.rice.ml.2025"
    }
    assert {item.authority_id for item in china_rice_arsenic.legal_authorities} == {
        "cn.nhc.inorganic_arsenic.gb_2762_2025"
    }
    assert {item.coverage_level.value for item in china_rice_arsenic.coverage_summaries} == {"deep_curated"}
    assert china_rice_arsenic.overall_submission_use.value == "allowed"


def test_contaminant_legal_limit_lookup_keeps_codex_rice_arsenic_gap_honest() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_contaminant_legal_limits(
        LookupContaminantLegalLimitsRequest(
            contaminant_family=ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
            jurisdiction="codex_global",
            substance_key="inorganic_arsenic",
            commodity_code="rice",
        )
    )

    assert not result.matched_records
    assert {item.authority_id for item in result.legal_authorities} == {
        "codex.cccf.cxs_193_1995.current_2025.inorganic_arsenic"
    }
    assert {flag.code for flag in result.quality_flags} == {
        "no_jurisdiction_specific_legal_limit",
        "no_curated_legal_limit_for_requested_lane",
        "requested_lane_outside_curated_scope",
    }
    assert {item.coverage_level.value for item in result.coverage_summaries} == {"deep_curated"}
    assert result.requested_lane_status.value == "family_curated_but_requested_lane_unmatched"
    assert result.curated_scope_commodity_codes == ["olive_oil"]
    assert result.curated_scope_matrix_groups == ["processed_fat_and_oil"]
    assert result.overall_submission_use.value == "review_required"


def test_contaminant_legal_limit_lookup_keeps_codex_methylmercury_anchor_only_distinct() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_contaminant_legal_limits(
        LookupContaminantLegalLimitsRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="codex_global",
            substance_key="methylmercury",
            commodity_code="salmon",
        )
    )

    assert not result.matched_records
    assert {item.authority_id for item in result.legal_authorities} == {
        "codex.cccf.cxs_193_1995.current_2025.mercury"
    }
    assert {flag.code for flag in result.quality_flags} == {
        "no_jurisdiction_specific_legal_limit",
        "no_curated_legal_limit_for_requested_lane",
        "anchor_only_family_without_exact_legal_limit",
    }
    assert {item.coverage_level.value for item in result.coverage_summaries} == {"anchor_only"}
    assert result.requested_lane_status.value == "anchor_only_family"
    assert not result.curated_scope_commodity_codes
    assert not result.curated_scope_matrix_groups
    assert result.overall_submission_use.value == "review_required"


def test_contaminant_legal_limit_lookup_exposes_explicit_inorganic_mercury_gap() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_contaminant_legal_limits(
        LookupContaminantLegalLimitsRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="cn",
            substance_key="inorganic_mercury",
        )
    )

    assert not result.matched_records
    assert {item.authority_id for item in result.legal_authorities} == {"cn.nhc.mercury.gb_2762_2025"}
    assert {flag.code for flag in result.quality_flags} == {
        "coverage_gap",
        "no_jurisdiction_specific_legal_limit",
        "no_curated_legal_limit_for_requested_lane",
    }
    assert {item.coverage_id for item in result.coverage_summaries} == {
        "cn.mercury_food_contaminants.inorganic_mercury.wave1"
    }
    assert {item.coverage_level.value for item in result.coverage_summaries} == {"explicit_gap"}
    assert result.requested_lane_status.value == "explicit_gap"
    assert result.overall_submission_use.value == "review_required"


def test_reporting_profile_lookup_exposes_primary_eu_and_optional_dutch_pfas_profiles() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_reporting_profiles(
        LookupReportingProfilesRequest(
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            matrix_group="eggs",
        )
    )

    assert {item.profile_id for item in result.profiles} == {
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
        "nl.pfas.rivm_peq.food_advisory",
    }
    assert result.recommended_primary_profile_ids == ["eu.pfas.efsa4.food_risk"]
    assert "primary eu efsa-4" in " ".join(result.notes).lower()


def test_reporting_profile_lookup_exposes_optional_dutch_biota_fish_profile_for_fish() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_reporting_profiles(
        LookupReportingProfilesRequest(
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            matrix_group="fish_and_seafood",
        )
    )

    assert {item.profile_id for item in result.profiles} == {
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
        "nl.pfas.rivm_peq.biota_fish_advisory",
    }
    assert result.recommended_primary_profile_ids == ["eu.pfas.efsa4.food_risk"]


def test_reporting_profile_lookup_can_filter_pfas_profiles_to_eu_only() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_reporting_profiles(
        LookupReportingProfilesRequest(
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            matrix_group="eggs",
        )
    )

    assert {item.profile_id for item in result.profiles} == {
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
    }
    assert result.recommended_primary_profile_ids == ["eu.pfas.efsa4.food_risk"]


def test_reference_value_lookup_supports_acrylamide_and_bpa_records() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    acrylamide = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="acrylamide",
            contaminant_family=ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS,
        )
    )
    bpa = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="bisphenol_a",
            contaminant_family=ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION,
        )
    )

    assert {item.record_id for item in acrylamide.matched_records} == {
        "efsa.acrylamide.neoplastic.bmdl10",
        "efsa.acrylamide.neurotoxicity.bmdl10",
    }
    assert {item.record_id for item in bpa.matched_records} == {"efsa.bpa.tdi.2023"}
    assert not bpa.visible_conflicts


def test_reference_value_lookup_supports_cadmium_records() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    cadmium = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="cadmium",
            contaminant_family=ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
        )
    )

    assert {item.record_id for item in cadmium.matched_records} == {"efsa.cadmium.twi.2009"}
    assert not cadmium.visible_conflicts


def test_reference_value_lookup_supports_lead_and_inorganic_arsenic_records() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    lead = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="lead",
            contaminant_family=ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
        )
    )
    inorganic_arsenic = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="inorganic_arsenic",
            contaminant_family=ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
        )
    )

    assert {item.record_id for item in lead.matched_records} == {
        "efsa.lead.developmental_neurotoxicity.bmdl01",
        "efsa.lead.nephrotoxicity.bmdl10",
    }
    assert {item.record_id for item in inorganic_arsenic.matched_records} == {
        "efsa.inorganic_arsenic.skin_cancer.bmdl05",
    }
    assert not lead.visible_conflicts
    assert not inorganic_arsenic.visible_conflicts


def test_reference_value_lookup_supports_mercury_records() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    methylmercury = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="methylmercury",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )
    inorganic_mercury = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="inorganic_mercury",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )

    assert {item.record_id for item in methylmercury.matched_records} == {"efsa.methylmercury.twi.2012"}
    assert {item.record_id for item in inorganic_mercury.matched_records} == {"efsa.inorganic_mercury.twi.2012"}
    assert not methylmercury.visible_conflicts
    assert not inorganic_mercury.visible_conflicts


def test_reference_value_lookup_preserves_glufosinate_authority_conflicts() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    glufosinate = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="glufosinate",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
        )
    )

    assert {item.record_id for item in glufosinate.matched_records} == {
        "efsa.glufosinate.adi.2007",
        "jmpr.glufosinate.adi.2012",
        "efsa.glufosinate.arfd.2007",
        "jmpr.glufosinate.arfd.2012",
        "cn.nhc.glufosinate.adi.2026",
    }
    assert {item.conflict_group_id for item in glufosinate.visible_conflicts} == {
        "glufosinate.adi.authority_conflict",
        "glufosinate.arfd.authority_conflict",
    }


def test_reference_value_lookup_preserves_oxamyl_authority_conflicts() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    oxamyl = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="oxamyl",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
        )
    )

    assert {item.record_id for item in oxamyl.matched_records} == {
        "efsa.oxamyl.adi.2023",
        "jmpr.oxamyl.adi.2012",
        "efsa.oxamyl.arfd.2023",
        "jmpr.oxamyl.arfd.2012",
        "cn.nhc.oxamyl.adi.2026",
    }
    assert {item.conflict_group_id for item in oxamyl.visible_conflicts} == {
        "oxamyl.adi.authority_conflict",
        "oxamyl.arfd.authority_conflict",
    }


def test_method_support_lookup_keeps_microplastics_separate_and_not_allowed() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_method_support(
        LookupMethodSupportRequest(
            contaminant_family=ContaminantFamily.MICROPLASTICS_EMERGING,
            jurisdiction="eu",
        )
    )

    assert result.emerging_contaminant is not None
    assert all(item.contaminant_family == ContaminantFamily.MICROPLASTICS_EMERGING for item in result.methods)
    assert result.overall_submission_use.value == "not_allowed"
    assert result.submission_candidate_allowed is False


def test_method_support_lookup_exposes_pfas_family_without_reusing_pesticide_methods() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_method_support(
        LookupMethodSupportRequest(
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            jurisdiction="eu",
        )
    )

    assert result.emerging_contaminant is not None
    assert {item.method_id for item in result.methods} == {
        "efsa.pfas.food.2020_opinion",
        "ec.pfas.monitoring.2022_2025",
    }
    assert all(item.contaminant_family == ContaminantFamily.PFAS_FOOD_CONTAMINANTS for item in result.methods)
    assert {item.authority_id for item in result.legal_authorities} == {
        "eu.contaminants.reg_2023_915",
        "eu.pfas.monitoring.reco_2022_1431",
    }
    assert result.overall_submission_use.value == "review_required"
    assert result.submission_candidate_allowed is False


def test_method_support_lookup_exposes_acrylamide_family_without_reusing_pesticide_methods() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_method_support(
        LookupMethodSupportRequest(
            contaminant_family=ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS,
            jurisdiction="eu",
        )
    )

    assert result.emerging_contaminant is not None
    assert {item.method_id for item in result.methods} == {
        "efsa.acrylamide.food.2015_opinion",
        "eu.acrylamide.mitigation.2017",
        "eu.acrylamide.monitoring.2019",
    }
    assert all(item.contaminant_family == ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS for item in result.methods)
    assert {item.authority_id for item in result.legal_authorities} == {
        "eu.acrylamide.reg_2017_2158",
        "eu.acrylamide.monitoring.reco_2019_1888",
    }
    assert result.overall_submission_use.value == "allowed"
    assert result.submission_candidate_allowed is True


def test_method_support_lookup_exposes_bisphenol_family_without_reusing_pesticide_methods() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_method_support(
        LookupMethodSupportRequest(
            contaminant_family=ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION,
            jurisdiction="eu",
        )
    )

    assert result.emerging_contaminant is not None
    assert {item.method_id for item in result.methods} == {
        "efsa.bpa.food.2023_opinion",
        "eu.bpa.fcm.2024_3190",
    }
    assert all(item.contaminant_family == ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION for item in result.methods)
    assert {item.authority_id for item in result.legal_authorities} == {
        "eu.bpa.fcm.reg_2024_3190",
    }
    assert result.overall_submission_use.value == "allowed"
    assert result.submission_candidate_allowed is True


def test_method_support_lookup_exposes_cadmium_family_without_reusing_pesticide_methods() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_method_support(
        LookupMethodSupportRequest(
            contaminant_family=ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
            jurisdiction="eu",
        )
    )

    assert result.emerging_contaminant is not None
    assert {item.method_id for item in result.methods} == {
        "efsa.cadmium.food.2009_opinion",
        "efsa.cadmium.exposure.2012_report",
        "eu.cadmium.official_control.333_2007",
    }
    assert all(item.contaminant_family == ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS for item in result.methods)
    assert {item.authority_id for item in result.legal_authorities} == {
        "eu.cadmium.contaminants.reg_2023_915",
        "eu.cadmium.official_control.reg_333_2007",
    }
    assert result.overall_submission_use.value == "allowed"
    assert result.submission_candidate_allowed is True


def test_method_support_lookup_exposes_lead_and_inorganic_arsenic_without_reusing_pesticide_methods() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    lead = runtime.lookup_method_support(
        LookupMethodSupportRequest(
            contaminant_family=ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
            jurisdiction="eu",
        )
    )
    inorganic_arsenic = runtime.lookup_method_support(
        LookupMethodSupportRequest(
            contaminant_family=ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
            jurisdiction="eu",
        )
    )

    assert lead.emerging_contaminant is not None
    assert {item.method_id for item in lead.methods} == {
        "efsa.lead.food.2010_opinion",
        "efsa.lead.exposure.2012_report",
        "eu.lead.official_control.333_2007",
    }
    assert all(item.contaminant_family == ContaminantFamily.LEAD_FOOD_CONTAMINANTS for item in lead.methods)
    assert {item.authority_id for item in lead.legal_authorities} == {
        "eu.lead.contaminants.reg_2023_915",
        "eu.lead.official_control.reg_333_2007",
    }
    assert lead.overall_submission_use.value == "allowed"
    assert lead.submission_candidate_allowed is True

    assert inorganic_arsenic.emerging_contaminant is not None
    assert {item.method_id for item in inorganic_arsenic.methods} == {
        "efsa.inorganic_arsenic.food.2024_opinion",
        "efsa.inorganic_arsenic.exposure.2021_report",
        "eu.inorganic_arsenic.official_control.333_2007",
    }
    assert all(
        item.contaminant_family == ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS
        for item in inorganic_arsenic.methods
    )
    assert {item.authority_id for item in inorganic_arsenic.legal_authorities} == {
        "eu.inorganic_arsenic.contaminants.reg_2025_1891",
        "eu.inorganic_arsenic.official_control.reg_333_2007",
    }
    assert inorganic_arsenic.overall_submission_use.value == "allowed"
    assert inorganic_arsenic.submission_candidate_allowed is True


def test_method_support_lookup_exposes_mercury_without_reusing_pesticide_methods() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    mercury = runtime.lookup_method_support(
        LookupMethodSupportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
        )
    )

    assert mercury.emerging_contaminant is not None
    assert {item.method_id for item in mercury.methods} == {
        "efsa.mercury.food.2012_opinion",
        "eu.mercury.official_control.333_2007",
    }
    assert all(item.contaminant_family == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS for item in mercury.methods)
    assert {item.authority_id for item in mercury.legal_authorities} == {
        "eu.mercury.contaminants.reg_2023_915",
        "eu.mercury.official_control.reg_333_2007",
    }
    assert mercury.overall_submission_use.value == "allowed"
    assert mercury.submission_candidate_allowed is True


def test_consumption_dataset_lookup_returns_efsa_backbone() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_consumption_dataset_support(
        LookupConsumptionDatasetSupportRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
        )
    )

    assert {item.dataset_id for item in result.datasets} >= {
        "efsa.comprehensive_food_consumption_db",
        "efsa.dietex_support",
    }
    assert result.overall_submission_use.value == "review_required"


def test_consumption_dataset_lookup_supports_pfas_context_without_native_submission_engine() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_consumption_dataset_support(
        LookupConsumptionDatasetSupportRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
        )
    )

    assert {item.dataset_id for item in result.datasets} == {
        "efsa.comprehensive_food_consumption_db.pfas_support",
        "ec.pfas_food_monitoring_2022_2025",
    }
    assert result.overall_submission_use.value == "review_required"


def test_consumption_dataset_lookup_supports_acrylamide_and_bpa_contexts_without_native_submission_engines() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    acrylamide = runtime.lookup_consumption_dataset_support(
        LookupConsumptionDatasetSupportRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS,
        )
    )
    bpa = runtime.lookup_consumption_dataset_support(
        LookupConsumptionDatasetSupportRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION,
        )
    )

    assert {item.dataset_id for item in acrylamide.datasets} == {
        "efsa.comprehensive_food_consumption_db.acrylamide_support",
        "eu.acrylamide_food_monitoring_2019",
    }
    assert {item.dataset_id for item in bpa.datasets} == {
        "efsa.comprehensive_food_consumption_db.bpa_support",
    }
    assert acrylamide.overall_submission_use.value == "allowed"
    assert bpa.overall_submission_use.value == "allowed"


def test_consumption_dataset_lookup_supports_cadmium_lead_and_inorganic_arsenic_contexts() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    cadmium = runtime.lookup_consumption_dataset_support(
        LookupConsumptionDatasetSupportRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
        )
    )
    lead = runtime.lookup_consumption_dataset_support(
        LookupConsumptionDatasetSupportRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
        )
    )
    inorganic_arsenic = runtime.lookup_consumption_dataset_support(
        LookupConsumptionDatasetSupportRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
        )
    )

    assert {item.dataset_id for item in cadmium.datasets} == {
        "efsa.comprehensive_food_consumption_db.cadmium_support",
    }
    assert {item.dataset_id for item in lead.datasets} == {
        "efsa.comprehensive_food_consumption_db.lead_support",
    }
    assert {item.dataset_id for item in inorganic_arsenic.datasets} == {
        "efsa.comprehensive_food_consumption_db.inorganic_arsenic_support",
    }
    assert cadmium.overall_submission_use.value == "allowed"
    assert lead.overall_submission_use.value == "allowed"
    assert inorganic_arsenic.overall_submission_use.value == "allowed"


def test_consumption_dataset_lookup_supports_mercury_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    mercury = runtime.lookup_consumption_dataset_support(
        LookupConsumptionDatasetSupportRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )

    assert {item.dataset_id for item in mercury.datasets} == {
        "efsa.comprehensive_food_consumption_db.mercury_support",
    }
    assert mercury.overall_submission_use.value == "allowed"


def test_occurrence_evidence_lookup_exposes_governed_monitoring_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    mercury = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            analyte="methylmercury",
            matrix_group="fish",
        )
    )

    assert {item.record_id for item in mercury.records} == {
        "eu.mercury.occurrence_evidence.official_monitoring_context"
    }
    assert mercury.overall_submission_use.value == "allowed"
    assert mercury.submission_candidate_allowed is True
    assert "monitoring-context metadata" in " ".join(mercury.notes).lower()


def test_occurrence_evidence_lookup_surfaces_historical_cadmium_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    cadmium = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
            analyte="cadmium",
            matrix_group="staple_plant_foods",
        )
    )

    notes = " ".join(cadmium.notes)
    assert {item.record_id for item in cadmium.records} == {
        "eu.cadmium.occurrence_evidence.official_monitoring_context"
    }
    assert cadmium.overall_submission_use.value == "allowed"
    assert cadmium.submission_candidate_allowed is True
    assert "historical relative to" in notes.lower()
    assert date.today().isoformat() in notes


def test_analytical_method_evidence_lookup_exposes_official_control_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    lead = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
            analyte="lead",
        )
    )

    assert {item.record_id for item in lead.records} == {
        "eu.lead.analytical_method_evidence.official_control"
    }
    assert lead.overall_submission_use.value == "allowed"
    assert lead.submission_candidate_allowed is True
    assert "official-control context" in " ".join(lead.notes).lower()


def test_occurrence_evidence_lookup_exposes_pfas_monitoring_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    pfas = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            analyte="pfos",
            matrix_group="eggs",
        )
    )

    assert {item.record_id for item in pfas.records} == {
        "eu.pfas.occurrence_evidence.food_monitoring_context",
        "eu.pfas.occurrence_evidence.eggs_monitoring_context",
    }
    assert pfas.overall_submission_use.value == "review_required"
    assert pfas.submission_candidate_allowed is False
    assert "pfas occurrence evidence" in " ".join(pfas.notes).lower()


def test_occurrence_evidence_lookup_exposes_pfas_dairy_monitoring_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    pfas = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            analyte="pfna",
            matrix_group="milk_and_dairy_products",
        )
    )

    assert {item.record_id for item in pfas.records} == {
        "eu.pfas.occurrence_evidence.milk_and_dairy_products_context",
    }
    assert pfas.overall_submission_use.value == "review_required"
    assert pfas.submission_candidate_allowed is False


def test_occurrence_evidence_lookup_exposes_pesticide_monitoring_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    glyphosate = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="glyphosate",
            matrix_group="wheat",
        )
    )

    assert {item.record_id for item in glyphosate.records} == {
        "eu.glyphosate.occurrence_evidence.monitoring_context"
    }
    assert glyphosate.overall_submission_use.value == "review_required"
    assert glyphosate.submission_candidate_allowed is False
    assert "pesticide-residue occurrence evidence" in " ".join(glyphosate.notes).lower()


def test_occurrence_evidence_lookup_exposes_imidacloprid_monitoring_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    imidacloprid = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="imidacloprid",
            matrix_group="apples",
        )
    )

    assert {item.record_id for item in imidacloprid.records} == {
        "eu.imidacloprid.occurrence_evidence.monitoring_context"
    }
    assert imidacloprid.overall_submission_use.value == "review_required"
    assert imidacloprid.submission_candidate_allowed is False
    assert "pesticide-residue occurrence evidence" in " ".join(imidacloprid.notes).lower()


def test_occurrence_evidence_lookup_exposes_ethiprole_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    ethiprole = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="ethiprole",
            matrix_group="rice",
        )
    )

    assert {item.record_id for item in ethiprole.records} == {
        "eu.ethiprole.occurrence_evidence.monitoring_context"
    }
    assert ethiprole.overall_submission_use.value == "review_required"
    assert ethiprole.submission_candidate_allowed is False
    assert "pesticide-residue occurrence evidence" in " ".join(ethiprole.notes).lower()


def test_occurrence_evidence_lookup_exposes_tetraconazole_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    tetraconazole = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="tetraconazole",
            matrix_group="linseeds",
        )
    )

    assert {item.record_id for item in tetraconazole.records} == {
        "eu.tetraconazole.occurrence_evidence.monitoring_context"
    }
    assert tetraconazole.overall_submission_use.value == "review_required"
    assert tetraconazole.submission_candidate_allowed is False
    assert "pesticide-residue occurrence evidence" in " ".join(tetraconazole.notes).lower()


def test_occurrence_evidence_lookup_exposes_tebuconazole_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    tebuconazole = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="tebuconazole",
            matrix_group="poppy_seeds",
        )
    )

    assert {item.record_id for item in tebuconazole.records} == {
        "eu.tebuconazole.occurrence_evidence.monitoring_context"
    }
    assert tebuconazole.overall_submission_use.value == "review_required"
    assert tebuconazole.submission_candidate_allowed is False
    assert "pesticide-residue occurrence evidence" in " ".join(tebuconazole.notes).lower()


def test_occurrence_evidence_lookup_exposes_glufosinate_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    glufosinate = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="glufosinate",
            matrix_group="soya_beans",
        )
    )

    assert {item.record_id for item in glufosinate.records} == {
        "eu.glufosinate.occurrence_evidence.monitoring_context"
    }
    assert glufosinate.overall_submission_use.value == "review_required"
    assert glufosinate.submission_candidate_allowed is False
    assert "pesticide-residue occurrence evidence" in " ".join(glufosinate.notes).lower()


def test_occurrence_evidence_lookup_exposes_oxamyl_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    oxamyl = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="oxamyl",
            matrix_group="potatoes",
        )
    )

    assert {item.record_id for item in oxamyl.records} == {
        "eu.oxamyl.occurrence_evidence.monitoring_context"
    }
    assert oxamyl.overall_submission_use.value == "review_required"
    assert oxamyl.submission_candidate_allowed is False
    assert "pesticide-residue occurrence evidence" in " ".join(oxamyl.notes).lower()


def test_occurrence_evidence_lookup_exposes_spirotetramat_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    spirotetramat = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="spirotetramat",
            matrix_group="citrus_fruits",
        )
    )

    assert {item.record_id for item in spirotetramat.records} == {
        "eu.spirotetramat.occurrence_evidence.monitoring_context"
    }
    assert spirotetramat.overall_submission_use.value == "review_required"
    assert spirotetramat.submission_candidate_allowed is False
    assert "pesticide-residue occurrence evidence" in " ".join(spirotetramat.notes).lower()


def test_occurrence_evidence_lookup_exposes_difenoconazole_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    difenoconazole = runtime.lookup_occurrence_evidence(
        LookupOccurrenceEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="difenoconazole",
            matrix_group="wheat_and_rye",
        )
    )

    assert {item.record_id for item in difenoconazole.records} == {
        "eu.difenoconazole.occurrence_evidence.monitoring_context"
    }
    assert difenoconazole.overall_submission_use.value == "review_required"
    assert difenoconazole.submission_candidate_allowed is False
    assert "pesticide-residue occurrence evidence" in " ".join(difenoconazole.notes).lower()


def test_analytical_method_evidence_lookup_exposes_bpa_food_contact_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    bpa = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION,
            analyte="bpa",
            matrix_group="canned",
        )
    )

    assert {item.record_id for item in bpa.records} == {
        "eu.bpa.analytical_method_evidence.food_contact_context",
        "eu.bpa.analytical_method_evidence.canned_foods_context",
    }
    assert bpa.overall_submission_use.value == "allowed"
    assert bpa.submission_candidate_allowed is True
    assert "food-contact and dietary review context" in " ".join(bpa.notes).lower()


def test_analytical_method_evidence_lookup_exposes_acrylamide_coffee_and_bpa_beverage_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    acrylamide = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS,
            analyte="acrylamide",
            matrix_group="coffee_and_coffee_substitutes",
        )
    )
    bpa = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION,
            analyte="bpa",
            matrix_group="beverages_and_drinks",
        )
    )

    assert {item.record_id for item in acrylamide.records} == {
        "eu.acrylamide.analytical_method_evidence.coffee_products_context",
    }
    assert {item.record_id for item in bpa.records} == {
        "eu.bpa.analytical_method_evidence.beverages_context",
    }
    assert acrylamide.overall_submission_use.value == "allowed"
    assert bpa.overall_submission_use.value == "allowed"


def test_analytical_method_evidence_lookup_exposes_pesticide_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    acetamiprid = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="acetamiprid",
            matrix_group="oranges",
        )
    )

    assert {item.record_id for item in acetamiprid.records} == {
        "eu.acetamiprid.analytical_method_evidence.monitoring_context"
    }
    assert acetamiprid.overall_submission_use.value == "review_required"
    assert acetamiprid.submission_candidate_allowed is False
    assert "pesticide-residue analytical-method evidence" in " ".join(acetamiprid.notes).lower()


def test_analytical_method_evidence_lookup_exposes_imidacloprid_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    imidacloprid = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="imidacloprid",
            matrix_group="apples",
        )
    )

    assert {item.record_id for item in imidacloprid.records} == {
        "eu.imidacloprid.analytical_method_evidence.monitoring_context"
    }
    assert imidacloprid.overall_submission_use.value == "review_required"
    assert imidacloprid.submission_candidate_allowed is False
    assert "pesticide-residue analytical-method evidence" in " ".join(imidacloprid.notes).lower()


def test_analytical_method_evidence_lookup_exposes_ethiprole_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    ethiprole = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="ethiprole",
            matrix_group="rice",
        )
    )

    assert {item.record_id for item in ethiprole.records} == {
        "eu.ethiprole.analytical_method_evidence.monitoring_context"
    }
    assert ethiprole.overall_submission_use.value == "review_required"
    assert ethiprole.submission_candidate_allowed is False
    assert "pesticide-residue analytical-method evidence" in " ".join(ethiprole.notes).lower()


def test_analytical_method_evidence_lookup_exposes_tetraconazole_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    tetraconazole = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="tetraconazole",
            matrix_group="linseeds",
        )
    )

    assert {item.record_id for item in tetraconazole.records} == {
        "eu.tetraconazole.analytical_method_evidence.monitoring_context"
    }
    assert tetraconazole.overall_submission_use.value == "review_required"
    assert tetraconazole.submission_candidate_allowed is False
    assert "pesticide-residue analytical-method evidence" in " ".join(tetraconazole.notes).lower()


def test_analytical_method_evidence_lookup_exposes_tebuconazole_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    tebuconazole = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="tebuconazole",
            matrix_group="poppy_seeds",
        )
    )

    assert {item.record_id for item in tebuconazole.records} == {
        "eu.tebuconazole.analytical_method_evidence.monitoring_context"
    }
    assert tebuconazole.overall_submission_use.value == "review_required"
    assert tebuconazole.submission_candidate_allowed is False
    assert "pesticide-residue analytical-method evidence" in " ".join(tebuconazole.notes).lower()


def test_analytical_method_evidence_lookup_exposes_glufosinate_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    glufosinate = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="glufosinate",
            matrix_group="soya_beans",
        )
    )

    assert {item.record_id for item in glufosinate.records} == {
        "eu.glufosinate.analytical_method_evidence.monitoring_context"
    }
    assert glufosinate.overall_submission_use.value == "review_required"
    assert glufosinate.submission_candidate_allowed is False
    assert "pesticide-residue analytical-method evidence" in " ".join(glufosinate.notes).lower()


def test_analytical_method_evidence_lookup_exposes_oxamyl_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    oxamyl = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="oxamyl",
            matrix_group="potatoes",
        )
    )

    assert {item.record_id for item in oxamyl.records} == {
        "eu.oxamyl.analytical_method_evidence.monitoring_context"
    }
    assert oxamyl.overall_submission_use.value == "review_required"
    assert oxamyl.submission_candidate_allowed is False
    assert "pesticide-residue analytical-method evidence" in " ".join(oxamyl.notes).lower()


def test_analytical_method_evidence_lookup_exposes_pfas_fish_and_spirotetramat_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    pfas = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            analyte="pfos",
            matrix_group="fish_and_seafood",
        )
    )
    spirotetramat = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="spirotetramat",
            matrix_group="honey",
        )
    )

    assert {item.record_id for item in pfas.records} == {
        "eu.pfas.analytical_method_evidence.monitoring_context",
        "eu.pfas.analytical_method_evidence.fish_monitoring_context",
    }
    assert {item.record_id for item in spirotetramat.records} == {
        "eu.spirotetramat.analytical_method_evidence.monitoring_context"
    }
    assert pfas.overall_submission_use.value == "review_required"
    assert spirotetramat.overall_submission_use.value == "review_required"


def test_reference_value_lookup_exposes_difenoconazole_arfd_conflict() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substance_key="difenoconazole",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
        )
    )

    assert {item.record_id for item in result.matched_records} == {
        "efsa.openfoodtox.difenoconazole.adi",
        "efsa.openfoodtox.difenoconazole.arfd",
        "jmpr.difenoconazole.arfd.2013",
    }
    assert {item.conflict_group_id for item in result.visible_conflicts} == {
        "difenoconazole.arfd.authority_conflict"
    }


def test_analytical_method_evidence_lookup_exposes_difenoconazole_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    difenoconazole = runtime.lookup_analytical_method_evidence(
        LookupAnalyticalMethodEvidenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            analyte="difenoconazole",
            matrix_group="tree_nuts",
        )
    )

    assert {item.record_id for item in difenoconazole.records} == {
        "eu.difenoconazole.analytical_method_evidence.monitoring_context"
    }
    assert difenoconazole.overall_submission_use.value == "review_required"
    assert difenoconazole.submission_candidate_allowed is False


def test_contaminant_monitoring_import_check_links_governed_evidence() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )

    assert result.check_status.value == "pass"
    assert result.normalized_projection.row_count == 2
    assert result.normalized_projection.units == ["mg/kg"]
    assert result.normalized_projection.high_attention_food_hits == ["bluefin_tuna", "swordfish"]
    assert "efsa.mercury.large_predatory_fish.review_focus" in result.normalized_projection.linked_review_focus_ids
    assert {item.record_id for item in result.occurrence_evidence_records} == {
        "eu.mercury.occurrence_evidence.official_monitoring_context"
    }
    assert {item.record_id for item in result.analytical_method_evidence_records} == {
        "eu.mercury.analytical_method_evidence.official_control"
    }
    assert {item.entry_id for item in result.uncertainty_and_assumption_ledger} >= {
        "row_level_lod_coverage",
        "lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
        "storage_stability.eu.mercury.analytical_method_evidence.official_control",
        "sampling_plan.eu.mercury.analytical_method_evidence.official_control",
    }
    assert "docs://contaminant-monitoring-import" in {item.uri for item in result.referenced_resources}


def test_contaminant_monitoring_import_check_links_pfas_evidence_without_metals_overlay() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="ec.pfas_food_monitoring_2022_2025",
            csv_text=(
                "food,contaminant,result,unit,lod,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "eggs,pfos,0.75,ng/kg,0.10,0.25,92,14,2025\n"
                "fish,pfoa,1.10,ng/kg,0.10,0.25,95,12,2025\n"
            ),
        )
    )

    assert result.check_status.value == "review_required"
    assert {item.record_id for item in result.occurrence_evidence_records} == {
        "eu.pfas.occurrence_evidence.food_monitoring_context",
        "eu.pfas.occurrence_evidence.eggs_monitoring_context",
        "eu.pfas.occurrence_evidence.fish_monitoring_context",
    }
    assert {item.record_id for item in result.analytical_method_evidence_records} == {
        "eu.pfas.analytical_method_evidence.monitoring_context",
        "eu.pfas.analytical_method_evidence.eggs_monitoring_context",
        "eu.pfas.analytical_method_evidence.fish_monitoring_context",
    }
    assert result.applicable_reporting_profile_ids == [
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
        "nl.pfas.rivm_peq.biota_fish_advisory",
        "nl.pfas.rivm_peq.food_advisory",
    ]
    assert result.reporting_profile_summary is not None
    assert result.reporting_profile_summary.recommended_primary_profile_ids == ["eu.pfas.efsa4.food_risk"]
    assert result.reporting_profile_summary.optional_extension_profile_ids == [
        "nl.pfas.rivm_peq.biota_fish_advisory",
        "nl.pfas.rivm_peq.food_advisory",
    ]
    assert result.reporting_profile_summary.compliance_variant_profile_ids == [
        "eu.pfas.efsa4.ml_lower_bound"
    ]
    assert result.reporting_profile_summary.supporting_detail_profile_ids == [
        "eu.pfas.individual_panel_detail"
    ]
    assert {
        link.profile_id: link.not_substitutable_for_profile_ids
        for link in result.reporting_profile_summary.non_substitution_links
    } == {
        "eu.pfas.efsa4.ml_lower_bound": ["eu.pfas.efsa4.food_risk"],
        "eu.pfas.individual_panel_detail": [
            "eu.pfas.efsa4.food_risk",
            "eu.pfas.efsa4.ml_lower_bound",
        ],
        "nl.pfas.rivm_peq.biota_fish_advisory": [
            "eu.pfas.efsa4.food_risk",
            "eu.pfas.efsa4.ml_lower_bound",
        ],
        "nl.pfas.rivm_peq.food_advisory": [
            "eu.pfas.efsa4.food_risk",
            "eu.pfas.efsa4.ml_lower_bound",
        ],
    }
    assert result.normalized_projection.linked_occurrence_record_ids == [
        "efsa.pfas.eggs.occurrence_monitoring.support",
        "efsa.pfas.fish_and_seafood.occurrence_monitoring.support",
        "efsa.pfas.offal.occurrence_monitoring.support",
    ]
    assert result.normalized_projection.linked_review_focus_ids == [
        "efsa.pfas.eggs.review_focus"
    ]
    assert result.overall_submission_use.value == "review_required"
    assert {item.entry_id for item in result.uncertainty_and_assumption_ledger} >= {
        "governance_submission_posture",
        "lower_bound_handling.eu.pfas.occurrence_evidence.food_monitoring_context",
        "storage_stability.eu.pfas.analytical_method_evidence.monitoring_context",
        "sampling_plan.eu.pfas.analytical_method_evidence.monitoring_context",
    }


def test_contaminant_monitoring_interpretation_bundle_carries_reporting_profile_summary_for_pfas() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="ec.pfas_food_monitoring_2022_2025",
            csv_text=(
                "food,contaminant,result,unit,lod,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "eggs,pfos,0.75,ng/kg,0.10,0.25,92,14,2025\n"
                "fish,pfoa,1.10,ng/kg,0.10,0.25,95,12,2025\n"
            ),
        )
    )

    bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )

    assert bundle.reporting_profile_summary is not None
    assert bundle.reporting_profile_summary.recommended_primary_profile_ids == ["eu.pfas.efsa4.food_risk"]
    assert bundle.reporting_profile_summary.optional_extension_profile_ids == [
        "nl.pfas.rivm_peq.biota_fish_advisory",
        "nl.pfas.rivm_peq.food_advisory",
    ]
    assert {
        item.prompt_id
        for item in bundle.review_prompts
        if item.category == "reporting_convention"
    } >= {
        "reporting_profile.primary_selection",
        "reporting_profile.non_substitution.nl.pfas.rivm_peq.food_advisory",
        "reporting_profile.non_substitution.nl.pfas.rivm_peq.biota_fish_advisory",
    }
    assert "reporting-profiles://manifest" in {item.uri for item in bundle.referenced_resources}
    assert "docs://reporting-profiles-registry" in {item.uri for item in bundle.referenced_resources}


def test_contaminant_monitoring_signoff_packet_preserves_reporting_profile_summary_for_pfas() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="ec.pfas_food_monitoring_2022_2025",
            csv_text=(
                "food,contaminant,result,unit,lod,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "eggs,pfos,0.75,ng/kg,0.10,0.25,92,14,2025\n"
                "fish,pfoa,1.10,ng/kg,0.10,0.25,95,12,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )

    packet = runtime.export_contaminant_monitoring_signoff_packet(
        ExportContaminantMonitoringSignoffPacketRequest(
            interpretation_bundle=interpretation_bundle,
            reviewer_id="runtime.pfas.signoff.reviewer",
            reviewer_role="scientific_reviewer",
        )
    )

    assert packet.reporting_profile_summary is not None
    assert packet.reporting_profile_summary.recommended_primary_profile_ids == ["eu.pfas.efsa4.food_risk"]
    assert {item.action_id for item in packet.action_items} >= {
        "review_reporting_profile_conventions",
        "review_governance_links",
    }
    reporting_action = next(
        item for item in packet.action_items if item.action_id == "review_reporting_profile_conventions"
    )
    assert reporting_action.linked_record_ids == [
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
        "nl.pfas.rivm_peq.biota_fish_advisory",
        "nl.pfas.rivm_peq.food_advisory",
    ]


def test_version_pinned_contaminant_monitoring_review_dossier_pins_reporting_profiles_for_pfas() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="ec.pfas_food_monitoring_2022_2025",
            csv_text=(
                "food,contaminant,result,unit,lod,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "eggs,pfos,0.75,ng/kg,0.10,0.25,92,14,2025\n"
                "fish,pfoa,1.10,ng/kg,0.10,0.25,95,12,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    signoff_packet = runtime.export_contaminant_monitoring_signoff_packet(
        ExportContaminantMonitoringSignoffPacketRequest(
            interpretation_bundle=interpretation_bundle,
            reviewer_id="runtime.pfas.dossier.reviewer",
            reviewer_role="scientific_reviewer",
        )
    )

    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=signoff_packet,
        )
    )

    assert dossier.reporting_profile_summary is not None
    assert dossier.reporting_profile_summary.recommended_primary_profile_ids == ["eu.pfas.efsa4.food_risk"]
    assert [item.profile_id for item in dossier.reporting_profile_snapshot] == [
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
        "nl.pfas.rivm_peq.biota_fish_advisory",
        "nl.pfas.rivm_peq.food_advisory",
    ]
    assert "reporting-profiles://manifest" in {item.uri for item in dossier.pinned_resources}
    assert "docs://reporting-profiles-registry" in {item.uri for item in dossier.pinned_resources}
    assert "reporting-profiles://profile/eu.pfas.efsa4.food_risk" in {
        item.uri for item in dossier.pinned_resources
    }
    assert "metals-review-focus://family/pfas_food_contaminants" in {
        item.uri for item in dossier.pinned_resources
    }


def test_contaminant_monitoring_import_check_links_pesticide_evidence() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db",
            csv_text=(
                "food,contaminant,result,unit,lod,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "wheat,glyphosate,0.12,mg/kg,0.01,0.03,88,15,2025\n"
                "beans_and_pulses,glyphosate,0.09,mg/kg,0.01,0.03,91,14,2025\n"
            ),
        )
    )

    assert result.check_status.value == "review_required"
    assert {item.record_id for item in result.occurrence_evidence_records} == {
        "eu.glyphosate.occurrence_evidence.monitoring_context"
    }
    assert {item.record_id for item in result.analytical_method_evidence_records} == {
        "eu.glyphosate.analytical_method_evidence.monitoring_context"
    }
    assert result.normalized_projection.linked_occurrence_record_ids == []
    assert result.normalized_projection.linked_review_focus_ids == []
    assert result.overall_submission_use.value == "review_required"
    assert {item.entry_id for item in result.uncertainty_and_assumption_ledger} >= {
        "governance_submission_posture",
        "lower_bound_handling.eu.glyphosate.occurrence_evidence.monitoring_context",
        "storage_stability.eu.glyphosate.analytical_method_evidence.monitoring_context",
        "sampling_plan.eu.glyphosate.analytical_method_evidence.monitoring_context",
    }


def test_contaminant_monitoring_import_check_links_imidacloprid_pesticide_evidence() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db",
            csv_text=(
                "food,contaminant,result,unit,lod,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "apples,imidacloprid,0.04,mg/kg,0.005,0.01,90,12,2025\n"
                "tomatoes,imidacloprid,0.03,mg/kg,0.005,0.01,92,11,2025\n"
            ),
        )
    )

    assert result.check_status.value == "review_required"
    assert {item.record_id for item in result.occurrence_evidence_records} == {
        "eu.imidacloprid.occurrence_evidence.monitoring_context"
    }
    assert {item.record_id for item in result.analytical_method_evidence_records} == {
        "eu.imidacloprid.analytical_method_evidence.monitoring_context"
    }
    assert result.overall_submission_use.value == "review_required"
    assert {item.entry_id for item in result.uncertainty_and_assumption_ledger} >= {
        "governance_submission_posture",
        "lower_bound_handling.eu.imidacloprid.occurrence_evidence.monitoring_context",
        "storage_stability.eu.imidacloprid.analytical_method_evidence.monitoring_context",
        "sampling_plan.eu.imidacloprid.analytical_method_evidence.monitoring_context",
    }


def test_contaminant_monitoring_import_check_links_ethiprole_pesticide_evidence() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db",
            csv_text=(
                "food,contaminant,result,unit,lod,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "rice,ethiprole,0.03,mg/kg,0.001,0.002,89,13,2025\n"
                "milled_rice,ethiprole,0.02,mg/kg,0.001,0.002,91,12,2025\n"
            ),
        )
    )

    assert result.check_status.value == "review_required"
    assert {item.record_id for item in result.occurrence_evidence_records} == {
        "eu.ethiprole.occurrence_evidence.monitoring_context"
    }
    assert {item.record_id for item in result.analytical_method_evidence_records} == {
        "eu.ethiprole.analytical_method_evidence.monitoring_context"
    }
    assert result.overall_submission_use.value == "review_required"
    assert {item.entry_id for item in result.uncertainty_and_assumption_ledger} >= {
        "governance_submission_posture",
        "lower_bound_handling.eu.ethiprole.occurrence_evidence.monitoring_context",
        "storage_stability.eu.ethiprole.analytical_method_evidence.monitoring_context",
        "sampling_plan.eu.ethiprole.analytical_method_evidence.monitoring_context",
    }


def test_contaminant_monitoring_import_check_links_tetraconazole_pesticide_evidence() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db",
            csv_text=(
                "food,contaminant,result,unit,lod,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "linseeds,tetraconazole,0.04,mg/kg,0.005,0.01,90,11,2025\n"
                "poppy_seeds,tetraconazole,0.03,mg/kg,0.005,0.01,92,10,2025\n"
            ),
        )
    )

    assert result.check_status.value == "review_required"
    assert {item.record_id for item in result.occurrence_evidence_records} == {
        "eu.tetraconazole.occurrence_evidence.monitoring_context"
    }
    assert {item.record_id for item in result.analytical_method_evidence_records} == {
        "eu.tetraconazole.analytical_method_evidence.monitoring_context"
    }
    assert result.overall_submission_use.value == "review_required"
    assert {item.entry_id for item in result.uncertainty_and_assumption_ledger} >= {
        "governance_submission_posture",
        "lower_bound_handling.eu.tetraconazole.occurrence_evidence.monitoring_context",
        "storage_stability.eu.tetraconazole.analytical_method_evidence.monitoring_context",
        "sampling_plan.eu.tetraconazole.analytical_method_evidence.monitoring_context",
    }


def test_contaminant_monitoring_import_check_links_tebuconazole_pesticide_evidence() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db",
            csv_text=(
                "food,contaminant,result,unit,lod,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "poppy_seeds,tebuconazole,0.04,mg/kg,0.01,0.05,91,10,2025\n"
                "oilseeds,tebuconazole,0.03,mg/kg,0.01,0.05,92,9,2025\n"
            ),
        )
    )

    assert result.check_status.value == "review_required"
    assert {item.record_id for item in result.occurrence_evidence_records} == {
        "eu.tebuconazole.occurrence_evidence.monitoring_context"
    }
    assert {item.record_id for item in result.analytical_method_evidence_records} == {
        "eu.tebuconazole.analytical_method_evidence.monitoring_context"
    }
    assert result.overall_submission_use.value == "review_required"
    assert {item.entry_id for item in result.uncertainty_and_assumption_ledger} >= {
        "governance_submission_posture",
        "lower_bound_handling.eu.tebuconazole.occurrence_evidence.monitoring_context",
        "storage_stability.eu.tebuconazole.analytical_method_evidence.monitoring_context",
        "sampling_plan.eu.tebuconazole.analytical_method_evidence.monitoring_context",
    }


def test_contaminant_monitoring_import_check_links_glufosinate_pesticide_evidence() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db",
            csv_text=(
                "food,contaminant,result,unit,lod,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "soya_beans,glufosinate,0.03,mg/kg,0.005,0.01,89,12,2025\n"
                "maize,glufosinate,0.02,mg/kg,0.005,0.01,91,11,2025\n"
            ),
        )
    )

    assert result.check_status.value == "review_required"
    assert {item.record_id for item in result.occurrence_evidence_records} == {
        "eu.glufosinate.occurrence_evidence.monitoring_context"
    }
    assert {item.record_id for item in result.analytical_method_evidence_records} == {
        "eu.glufosinate.analytical_method_evidence.monitoring_context"
    }
    assert result.overall_submission_use.value == "review_required"
    assert {item.entry_id for item in result.uncertainty_and_assumption_ledger} >= {
        "governance_submission_posture",
        "lower_bound_handling.eu.glufosinate.occurrence_evidence.monitoring_context",
        "storage_stability.eu.glufosinate.analytical_method_evidence.monitoring_context",
        "sampling_plan.eu.glufosinate.analytical_method_evidence.monitoring_context",
    }


def test_contaminant_monitoring_import_check_links_oxamyl_pesticide_evidence() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db",
            csv_text=(
                "food,contaminant,result,unit,lod,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "potatoes,oxamyl,0.02,mg/kg,0.002,0.01,88,14,2025\n"
                "melons,oxamyl,0.01,mg/kg,0.002,0.01,91,13,2025\n"
            ),
        )
    )

    assert result.check_status.value == "review_required"
    assert {item.record_id for item in result.occurrence_evidence_records} == {
        "eu.oxamyl.occurrence_evidence.monitoring_context"
    }
    assert {item.record_id for item in result.analytical_method_evidence_records} == {
        "eu.oxamyl.analytical_method_evidence.monitoring_context"
    }
    assert result.overall_submission_use.value == "review_required"
    assert {item.entry_id for item in result.uncertainty_and_assumption_ledger} >= {
        "governance_submission_posture",
        "lower_bound_handling.eu.oxamyl.occurrence_evidence.monitoring_context",
        "storage_stability.eu.oxamyl.analytical_method_evidence.monitoring_context",
        "sampling_plan.eu.oxamyl.analytical_method_evidence.monitoring_context",
    }


def test_contaminant_monitoring_interpretation_bundle_packages_linked_review_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )

    bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(
            check_result=check_result,
            bundle_note="Runtime contaminant monitoring bundle note.",
        )
    )

    assert bundle.contaminant_family == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS
    assert bundle.check_status.value == "pass"
    assert bundle.overall_submission_use.value == "allowed"
    assert bundle.submission_candidate_allowed is True
    assert {item.focus_id for item in bundle.linked_review_focus_records} >= {
        "efsa.mercury.large_predatory_fish.review_focus",
        "efsa.mercury.sensitive_population_advice.review_focus",
    }
    assert bundle.unresolved_linked_review_focus_ids == []
    assert "eu.reg.333_2007" in bundle.covered_source_ids
    assert "efsa.mercury.food.2012" in bundle.covered_source_ids
    assert "eu.mercury.official_control.333_2007" in bundle.covered_method_ids
    assert "eu.mercury.official_control.reg_333_2007" in bundle.covered_legal_authority_ids
    assert "efsa.comprehensive_food_consumption_db.mercury_support" in bundle.covered_dataset_ids
    assert "efsa.methylmercury.twi.2012" in bundle.covered_reference_value_record_ids
    assert "docs://contaminant-monitoring-interpretation" in {
        item.uri for item in bundle.referenced_resources
    }
    assert "contaminant-legal-limits://manifest" in {
        item.uri for item in bundle.referenced_resources
    }
    assert "jurisdiction-coverage://jurisdiction/eu" in {
        item.uri for item in bundle.referenced_resources
    }
    assert "emerging-contaminants://family/mercury_food_contaminants" in {
        item.uri for item in bundle.referenced_resources
    }
    assert {item.matrix_group for item in bundle.legal_limit_reviews} >= {
        "fish_and_seafood",
        "large_predatory_fish",
    }
    assert {item.requested_lane_status.value for item in bundle.legal_limit_reviews} == {
        "no_curated_family_coverage"
    }
    assert {item.entry_id for item in bundle.uncertainty_and_assumption_ledger} >= {
        "row_level_lod_coverage",
        "lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
        "storage_stability.eu.mercury.analytical_method_evidence.official_control",
        "sampling_plan.eu.mercury.analytical_method_evidence.official_control",
    }
    assert any(item.category == "legal_limit_scope" for item in bundle.review_prompts)
    assert {item.code for item in bundle.limitations} >= {
        "legal_limit_scope.fish_and_seafood",
        "legal_limit_scope.large_predatory_fish",
    }
    assert len(bundle.review_prompts) >= 8
    assert bundle.recommended_sequence[0] == "review_header_resolution_and_quality_flags"
    assert bundle.notes[-1] == "Runtime contaminant monitoring bundle note."


def test_contaminant_monitoring_signoff_packet_exports_reviewer_decisions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(
            check_result=check_result,
        )
    )
    ledger_action_ids = {
        f"review_scientific_ledger.{item.entry_id}"
        for item in interpretation_bundle.uncertainty_and_assumption_ledger
        if item.entry_id not in {"governance_submission_posture", "unresolved_review_focus_linkage"}
    }

    packet = runtime.export_contaminant_monitoring_signoff_packet(
        ExportContaminantMonitoringSignoffPacketRequest(
            interpretation_bundle=interpretation_bundle,
            reviewer_id="runtime.contaminant.reviewer",
            reviewer_role="scientific_reviewer",
            decisions=[
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_header_resolution_and_quality_flags",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Header resolution reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_occurrence_evidence_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Occurrence evidence reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_analytical_method_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Analytical-method evidence reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_linked_focus_records",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Linked focus records reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.row_level_lod_coverage",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Row-level LOD coverage gap reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                    decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                    rationale="Lower-bound handling assumption retained as an explicit reviewer waiver.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Storage-stability context reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Sampling-plan context reviewed.",
                ),
                    ContaminantMonitoringSignoffDecisionInput(
                        action_id="review_governance_links",
                        decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                        rationale="Governance links reviewed.",
                        supporting_uris=["docs://contaminant-monitoring-signoff"],
                    ),
            ],
        )
    )

    assert packet.overall_signoff_status.value == "signed_off_with_waivers"
    assert packet.source_bundle_id == interpretation_bundle.bundle_id
    assert packet.dataset_id == "efsa.comprehensive_food_consumption_db.mercury_support"
    assert packet.pending_action_ids == []
    assert packet.unresolved_blocking_action_ids == []
    assert set(packet.waived_action_ids) == {
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
    }
    assert len(packet.legal_limit_reviews) == len(interpretation_bundle.legal_limit_reviews)
    assert any("legal-limit review snapshots" in note for note in packet.notes)
    assert {item.action_id for item in packet.action_items} == {
        "review_header_resolution_and_quality_flags",
        "review_occurrence_evidence_context",
        "review_analytical_method_context",
        "review_linked_focus_records",
        "review_governance_links",
        *ledger_action_ids,
    }
    assert "docs://contaminant-monitoring-signoff" in {item.uri for item in packet.referenced_resources}
    assert packet.notes[-1] != ""


def test_version_pinned_contaminant_monitoring_review_dossier_exports_escalation_overlay() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    ledger_action_ids = {
        f"review_scientific_ledger.{item.entry_id}"
        for item in interpretation_bundle.uncertainty_and_assumption_ledger
        if item.entry_id not in {"governance_submission_posture", "unresolved_review_focus_linkage"}
    }
    signoff_packet = runtime.export_contaminant_monitoring_signoff_packet(
        ExportContaminantMonitoringSignoffPacketRequest(
            interpretation_bundle=interpretation_bundle,
            reviewer_id="runtime.contaminant.reviewer",
            reviewer_role="scientific_reviewer",
            decisions=[
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_header_resolution_and_quality_flags",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Header alias resolution and quality flags were reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_occurrence_evidence_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Occurrence evidence context was reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_analytical_method_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Analytical-method context was reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_linked_focus_records",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Linked review-focus records were reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.row_level_lod_coverage",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Row-level LOD coverage gap reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                    decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                    rationale="Lower-bound handling assumption remains explicit as a controlled reviewer waiver.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Storage-stability context was reviewed.",
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Sampling-plan context was reviewed.",
                ),
                    ContaminantMonitoringSignoffDecisionInput(
                        action_id="review_governance_links",
                        decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                        rationale="Governance links were reviewed.",
                        supporting_uris=["docs://contaminant-monitoring-signoff"],
                    ),
            ],
        )
    )

    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=signoff_packet,
        )
    )

    assert dossier.interpretation_bundle.contaminant_family == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS
    assert dossier.dossier_status.value == "signed_off_with_waivers"
    assert dossier.escalation_required is True
    assert {item.action_id for item in dossier.escalation_items} == {
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
    }
    assert {item.escalation_type.value for item in dossier.escalation_items} == {"waiver_review"}
    assert {
        item.action_id for item in dossier.signoff_packet.action_items
    } >= ledger_action_ids
    assert "release://metadata-report" in {item.uri for item in dossier.pinned_resources}
    assert "docs://contaminant-monitoring-signoff" in {item.uri for item in dossier.pinned_resources}
    assert "contaminant-legal-limits://family/mercury_food_contaminants" in {
        item.uri for item in dossier.pinned_resources
    }
    assert "contaminant-legal-limits://jurisdiction/eu" in {item.uri for item in dossier.pinned_resources}
    assert "jurisdiction-coverage://jurisdiction/eu" in {item.uri for item in dossier.pinned_resources}
    assert {
        item.code for item in dossier.limitations if item.code.startswith("legal_limit_scope.")
    } >= {"legal_limit_scope.fish_and_seafood", "legal_limit_scope.large_predatory_fish"}
    assert dossier.notes[-1].startswith("At least one reviewer waiver")


def test_metals_occurrence_lookup_exposes_governed_occurrence_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    cadmium = runtime.lookup_metals_occurrence(
        LookupMetalsOccurrenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
        )
    )
    lead = runtime.lookup_metals_occurrence(
        LookupMetalsOccurrenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
        )
    )
    inorganic_arsenic = runtime.lookup_metals_occurrence(
        LookupMetalsOccurrenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
        )
    )
    mercury = runtime.lookup_metals_occurrence(
        LookupMetalsOccurrenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )

    assert {item.record_id for item in cadmium.records} == {"efsa.cadmium.occurrence_monitoring.support"}
    assert {item.record_id for item in lead.records} == {"efsa.lead.occurrence_monitoring.support"}
    assert {item.record_id for item in inorganic_arsenic.records} == {
        "efsa.inorganic_arsenic.occurrence_monitoring.support"
    }
    assert {item.record_id for item in mercury.records} == {"efsa.mercury.occurrence_monitoring.support"}
    assert cadmium.overall_submission_use.value == "allowed"
    assert lead.submission_candidate_allowed is True
    assert "potatoes" in cadmium.records[0].high_attention_foods
    assert "game_meat" in lead.records[0].high_attention_foods
    assert "rice_and_rice_based_products" in inorganic_arsenic.records[0].priority_food_groups
    assert "swordfish" in mercury.records[0].high_attention_foods
    assert "women_who_are_pregnant_or_planning_pregnancy" in mercury.records[0].sensitive_population_groups
    assert "historical anchors" in " ".join(cadmium.notes).lower()
    assert "official-control context" in " ".join(inorganic_arsenic.notes).lower()
    assert "fish and seafood sensitivity" in " ".join(mercury.notes).lower()


def test_cadmium_contaminant_dossier_surfaces_historical_data_currency_gate() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.cadmium_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "potatoes,cadmium,0.12,mg/kg,0.01,91,10,2025\n"
                "wheat,cadmium,0.08,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )

    assert any(
        flag.code.startswith("occurrence_evidence_historical_data_period.")
        for flag in check_result.quality_flags
    )
    assert any("historical data context was detected" in note.lower() for note in check_result.notes)

    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    assert {
        item.code for item in interpretation_bundle.limitations
    } >= {"historical_data_context.eu.cadmium.occurrence_evidence.official_monitoring_context"}

    signoff_packet = runtime.export_contaminant_monitoring_signoff_packet(
        ExportContaminantMonitoringSignoffPacketRequest(
            interpretation_bundle=interpretation_bundle,
            reviewer_id="runtime.cadmium.reviewer",
            reviewer_role="scientific_reviewer",
            decisions=[
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_governance_links",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Governance links reviewed with explicit acceptance of the historical cadmium context.",
                    supporting_uris=["docs://contaminant-monitoring-signoff"],
                ),
            ],
        )
    )
    dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=signoff_packet,
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile="cadmium_internal_review",
        )
    )

    assert readiness.overall_status.value == "review_required"
    assert any(item.rule_id == "data_currency_reviewed" for item in readiness.warning_rules)


def test_metals_review_focus_lookup_exposes_food_specific_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    cadmium = runtime.lookup_metals_review_focus(
        LookupMetalsReviewFocusRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
            commodity_group="molluscs",
        )
    )
    mercury = runtime.lookup_metals_review_focus(
        LookupMetalsReviewFocusRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            focus_food="tuna",
        )
    )
    inorganic_arsenic = runtime.lookup_metals_review_focus(
        LookupMetalsReviewFocusRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
            focus_food="rice",
        )
    )

    assert {item.focus_id for item in cadmium.records} == {"efsa.cadmium.molluscs.review_focus"}
    assert cadmium.records[0].linked_occurrence_record_ids == ["efsa.cadmium.occurrence_monitoring.support"]
    assert "bivalve_molluscs" in cadmium.records[0].focus_foods
    assert cadmium.overall_submission_use.value == "allowed"
    assert {item.focus_id for item in mercury.records} >= {
        "efsa.mercury.large_predatory_fish.review_focus",
        "efsa.mercury.sensitive_population_advice.review_focus",
    }
    assert "bigeye_tuna" in {food for item in mercury.records for food in item.focus_foods}
    assert "women_who_are_pregnant_or_planning_pregnancy" in {
        group for item in mercury.records for group in item.sensitive_population_groups
    }
    assert {item.focus_id for item in inorganic_arsenic.records} == {
        "efsa.inorganic_arsenic.rice_products.review_focus"
    }
    assert "rice_based_infant_foods" in inorganic_arsenic.records[0].focus_foods
    assert "rice and rice-based foods" in " ".join(inorganic_arsenic.notes).lower()


def test_metals_monitoring_interpretation_bundle_exports_occurrence_and_focus_context() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    occurrence_result = runtime.lookup_metals_occurrence(
        LookupMetalsOccurrenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )
    review_focus_result = runtime.lookup_metals_review_focus(
        LookupMetalsReviewFocusRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            focus_food="tuna",
        )
    )

    bundle = runtime.export_metals_monitoring_interpretation_bundle(
        ExportMetalsMonitoringInterpretationBundleRequest(
            occurrence_result=occurrence_result,
            review_focus_result=review_focus_result,
            bundle_note="Runtime test bundle note.",
        )
    )

    assert bundle.contaminant_family == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS
    assert bundle.overall_submission_use.value == "allowed"
    assert bundle.submission_candidate_allowed is True
    assert {item.record_id for item in bundle.occurrence_records} == {"efsa.mercury.occurrence_monitoring.support"}
    assert {item.focus_id for item in bundle.review_focus_records} >= {
        "efsa.mercury.large_predatory_fish.review_focus",
        "efsa.mercury.sensitive_population_advice.review_focus",
    }
    assert bundle.linked_occurrence_record_ids == ["efsa.mercury.occurrence_monitoring.support"]
    assert bundle.unresolved_linked_occurrence_record_ids == []
    assert "bigeye_tuna" in bundle.focus_foods
    assert "swordfish" in bundle.high_attention_foods
    assert "women_who_are_pregnant_or_planning_pregnancy" in bundle.sensitive_population_groups
    assert "efsa.methylmercury.twi.2012" in bundle.covered_reference_value_record_ids
    assert "docs://metals-monitoring-interpretation" in {
        item.uri for item in bundle.referenced_resources
    }
    assert "contaminant-legal-limits://manifest" in {
        item.uri for item in bundle.referenced_resources
    }
    assert "jurisdiction-coverage://jurisdiction/eu" in {
        item.uri for item in bundle.referenced_resources
    }
    assert len(bundle.legal_limit_reviews) == 1
    assert bundle.legal_limit_reviews[0].requested_lane_status.value == "no_curated_family_coverage"
    assert {item.entry_id for item in bundle.uncertainty_and_assumption_ledger} >= {
        "monitoring_context.efsa.mercury.occurrence_monitoring.support",
        "sensitive_population_prompt_context",
        "trend_signal_context",
    }
    assert any(item.category == "legal_limit_scope" for item in bundle.review_prompts)
    assert {item.code for item in bundle.limitations} >= {"legal_limit_scope.family"}
    assert len(bundle.review_prompts) >= 7
    assert bundle.recommended_sequence[0] == "review_occurrence_context"
    assert bundle.notes[-1] == "Runtime test bundle note."


def test_metals_monitoring_signoff_packet_exports_reviewer_decisions() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    occurrence_result = runtime.lookup_metals_occurrence(
        LookupMetalsOccurrenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )
    review_focus_result = runtime.lookup_metals_review_focus(
        LookupMetalsReviewFocusRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            focus_food="tuna",
        )
    )
    interpretation_bundle = runtime.export_metals_monitoring_interpretation_bundle(
        ExportMetalsMonitoringInterpretationBundleRequest(
            occurrence_result=occurrence_result,
            review_focus_result=review_focus_result,
        )
    )
    ledger_action_ids = {
        f"review_scientific_ledger.{item.entry_id}"
        for item in interpretation_bundle.uncertainty_and_assumption_ledger
        if item.entry_id not in {"governance_submission_posture", "unresolved_occurrence_linkage"}
    }

    packet = runtime.export_metals_monitoring_signoff_packet(
        ExportMetalsMonitoringSignoffPacketRequest(
            interpretation_bundle=interpretation_bundle,
            reviewer_id="runtime.metals.reviewer",
            reviewer_role="scientific_reviewer",
            decisions=[
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_occurrence_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Occurrence context reviewed.",
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_priority_food_groups",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Priority foods reviewed.",
                ),
                    MetalsMonitoringSignoffDecisionInput(
                        action_id="review_sensitive_populations",
                        decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                        rationale="Sensitive populations reviewed.",
                        supporting_uris=["docs://metals-monitoring-signoff"],
                    ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_commodity_focus_prompts",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Commodity prompts reviewed.",
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.monitoring_context.efsa.mercury.occurrence_monitoring.support",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Monitoring-context assumption reviewed.",
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.sensitive_population_prompt_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Sensitive-population prompt context reviewed.",
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.trend_signal_context",
                    decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                    rationale="Trend-signal context retained as an explicit reviewer waiver.",
                ),
                    MetalsMonitoringSignoffDecisionInput(
                        action_id="review_governance_links",
                        decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                        rationale="Governance links reviewed.",
                        supporting_uris=["docs://metals-monitoring-signoff"],
                    ),
            ],
            packet_note="Runtime test signoff packet note.",
        )
    )

    assert packet.contaminant_family == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS
    assert packet.overall_signoff_status.value == "signed_off_with_waivers"
    assert set(packet.completed_action_ids) == {
        "review_occurrence_context",
        "review_priority_food_groups",
        "review_sensitive_populations",
        "review_commodity_focus_prompts",
        "review_scientific_ledger.monitoring_context.efsa.mercury.occurrence_monitoring.support",
        "review_scientific_ledger.sensitive_population_prompt_context",
        "review_governance_links",
    }
    assert set(packet.waived_action_ids) == {
        "review_scientific_ledger.trend_signal_context",
    }
    assert len(packet.legal_limit_reviews) == 1
    assert any("legal-limit review snapshots" in note for note in packet.notes)
    assert packet.unresolved_blocking_action_ids == []
    assert {item.action_id for item in packet.action_items} >= ledger_action_ids
    assert "docs://metals-monitoring-signoff" in {item.uri for item in packet.referenced_resources}
    assert packet.notes[-1] == "Runtime test signoff packet note."


def test_version_pinned_metals_monitoring_review_dossier_exports_escalation_overlay() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    occurrence_result = runtime.lookup_metals_occurrence(
        LookupMetalsOccurrenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )
    review_focus_result = runtime.lookup_metals_review_focus(
        LookupMetalsReviewFocusRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            focus_food="tuna",
        )
    )
    interpretation_bundle = runtime.export_metals_monitoring_interpretation_bundle(
        ExportMetalsMonitoringInterpretationBundleRequest(
            occurrence_result=occurrence_result,
            review_focus_result=review_focus_result,
        )
    )
    ledger_action_ids = {
        f"review_scientific_ledger.{item.entry_id}"
        for item in interpretation_bundle.uncertainty_and_assumption_ledger
        if item.entry_id not in {"governance_submission_posture", "unresolved_occurrence_linkage"}
    }
    signoff_packet = runtime.export_metals_monitoring_signoff_packet(
        ExportMetalsMonitoringSignoffPacketRequest(
            interpretation_bundle=interpretation_bundle,
            reviewer_id="runtime.metals.reviewer",
            reviewer_role="scientific_reviewer",
            decisions=[
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_occurrence_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Occurrence context reviewed.",
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_priority_food_groups",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Priority foods reviewed.",
                ),
                    MetalsMonitoringSignoffDecisionInput(
                        action_id="review_sensitive_populations",
                        decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                        rationale="Sensitive populations reviewed.",
                        supporting_uris=["docs://metals-monitoring-signoff"],
                    ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_commodity_focus_prompts",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Commodity prompts reviewed.",
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.monitoring_context.efsa.mercury.occurrence_monitoring.support",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Monitoring-context assumption reviewed.",
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.sensitive_population_prompt_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Sensitive-population prompt context reviewed.",
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.trend_signal_context",
                    decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                    rationale="Trend-signal context retained as an explicit reviewer waiver.",
                ),
                    MetalsMonitoringSignoffDecisionInput(
                        action_id="review_governance_links",
                        decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                        rationale="Governance links reviewed.",
                        supporting_uris=["docs://metals-monitoring-signoff"],
                    ),
            ],
        )
    )

    dossier = runtime.export_version_pinned_metals_monitoring_review_dossier(
        ExportVersionPinnedMetalsMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=signoff_packet,
        )
    )

    assert dossier.interpretation_bundle.contaminant_family == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS
    assert dossier.dossier_status.value == "signed_off_with_waivers"
    assert dossier.escalation_required is True
    assert {item.action_id for item in dossier.escalation_items} == {
        "review_scientific_ledger.trend_signal_context",
    }
    assert {item.escalation_type.value for item in dossier.escalation_items} == {"waiver_review"}
    assert "contaminant-legal-limits://family/mercury_food_contaminants" in {
        item.uri for item in dossier.pinned_resources
    }
    assert "contaminant-legal-limits://jurisdiction/eu" in {item.uri for item in dossier.pinned_resources}
    assert "jurisdiction-coverage://jurisdiction/eu" in {item.uri for item in dossier.pinned_resources}
    assert {item.code for item in dossier.limitations} >= {"legal_limit_scope.family"}
    assert {item.action_id for item in dossier.signoff_packet.action_items} >= ledger_action_ids
    assert "release://metadata-report" in {item.uri for item in dossier.pinned_resources}
    assert "docs://metals-monitoring-signoff" in {item.uri for item in dossier.pinned_resources}
    assert dossier.notes[-1].startswith("At least one reviewer waiver")


def test_consumption_dataset_lookup_supports_cadmium_context_without_native_submission_engine() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    cadmium = runtime.lookup_consumption_dataset_support(
        LookupConsumptionDatasetSupportRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
        )
    )

    assert {item.dataset_id for item in cadmium.datasets} == {
        "efsa.comprehensive_food_consumption_db.cadmium_support",
    }
    assert cadmium.overall_submission_use.value == "allowed"


def test_parse_and_summarize_survey_distribution() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    # 1. Parse raw dataset
    raw_dataset_req = ParseRawSurveyDatasetRequest(
        datasetId="test_survey",
        regionId="eu",
        populationGroup="adult_general",
        rawRecords=[
            RawSurveyRecordInput(
                subjectId="s1", bodyWeightKg=70.0, daysInSurvey=2, commodityCode="apples", consumptionKgPerDay=0.4
            ),
            RawSurveyRecordInput(
                subjectId="s2", bodyWeightKg=70.0, daysInSurvey=2, commodityCode="apples", consumptionKgPerDay=0.0
            ),
            RawSurveyRecordInput(
                subjectId="s3", bodyWeightKg=70.0, daysInSurvey=2, commodityCode="apples", consumptionKgPerDay=0.6
            ),
            RawSurveyRecordInput(
                subjectId="s4", bodyWeightKg=70.0, daysInSurvey=2, commodityCode="apples", consumptionKgPerDay=0.2
            ),
        ],
    )
    dataset = runtime.parse_raw_survey_dataset(raw_dataset_req)
    assert len(dataset.records) == 4

    # 2. Build residue profile
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "TestChemical"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples", residue_concentration_mg_per_kg=0.5, source_type="monitoring"
                )
            ],
        )
    )

    # 3. Summarize
    summary_req = SummarizeSurveyDistributionRequest(
        dataset=dataset,
        residue_profile=residue_profile,
    )
    summary = runtime.summarize_survey_distribution(summary_req)

    assert summary.total_subjects == 4
    assert summary.consumers_only_count == 3
    assert summary.zero_intake_prevalence == 0.25
    
    # s1: 0.4 * 0.5 / 70 = 0.002857
    # s2: 0.0
    # s3: 0.6 * 0.5 / 70 = 0.004285
    # s4: 0.2 * 0.5 / 70 = 0.001428
    assert summary.max_mg_per_kg_bw_per_day > 0.004
    assert summary.percentile_99_mg_per_kg_bw_per_day > 0.001
    
    assert any(flag.code == "distribution_summary" for flag in summary.limitations)


def test_probabilistic_and_distribution_summary_use_consistent_exposure_formula() -> None:
    """Both survey tools must produce identical subject-level exposures for the same raw inputs."""
    from pathlib import Path
    from dietary_mcp.runtime import DietaryRuntime
    from dietary_mcp.models import (
        ParseRawSurveyDatasetRequest,
        RawSurveyRecordInput,
        BuildDietaryResidueProfileRequest,
        DietaryCommodityResidueInput,
        SummarizeSurveyDistributionRequest,
        BuildProbabilisticIntakeSummaryRequest,
    )

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    dataset_req = ParseRawSurveyDatasetRequest(
        datasetId="consistency_test",
        regionId="eu",
        populationGroup="adult_general",
        rawRecords=[
            RawSurveyRecordInput(subjectId="s1", bodyWeightKg=70.0, daysInSurvey=3, commodityCode="apples", consumptionKgPerDay=0.4),
            RawSurveyRecordInput(subjectId="s2", bodyWeightKg=70.0, daysInSurvey=3, commodityCode="apples", consumptionKgPerDay=0.0),
            RawSurveyRecordInput(subjectId="s3", bodyWeightKg=70.0, daysInSurvey=3, commodityCode="apples", consumptionKgPerDay=0.6),
        ],
    )
    dataset = runtime.parse_raw_survey_dataset(dataset_req)

    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "ConsistencyChem"},
            residue_records=[
                DietaryCommodityResidueInput(commodity_code="apples", residue_concentration_mg_per_kg=0.5, source_type="monitoring")
            ],
        )
    )

    dist_summary = runtime.summarize_survey_distribution(
        SummarizeSurveyDistributionRequest(dataset=dataset, residue_profile=residue_profile)
    )
    prob_summary = runtime.build_probabilistic_intake_summary(
        BuildProbabilisticIntakeSummaryRequest(
            dataset=dataset,
            residue_profile=residue_profile,
            iteration_count=1000,
            random_seed=42,
        )
    )

    # Cohort statistics must match exactly because both tools aggregate the same exposures
    assert prob_summary.total_subjects == dist_summary.total_subjects == 3
    assert prob_summary.consumers_only_count == dist_summary.consumers_only_count == 2
    assert prob_summary.zero_intake_prevalence == dist_summary.zero_intake_prevalence
    # For a 3-day survey, if days_in_survey were incorrectly applied, the max would be 1/3 of this
    expected_max = 0.6 * 0.5 / 70.0  # ~0.0042857
    assert dist_summary.max_mg_per_kg_bw_per_day == pytest.approx(expected_max, abs=1e-12)
    assert prob_summary.max_mg_per_kg_bw_per_day == pytest.approx(expected_max, abs=1e-12)


def test_mrl_matching_uses_exact_keys_not_substrings() -> None:
    """Substances with similar names must not false-match via substring search."""
    from pathlib import Path
    from dietary_mcp.runtime import DietaryRuntime
    from dietary_mcp.models import (
        BuildDietaryResidueProfileRequest,
        DietaryCommodityResidueInput,
        EvaluateGlobalTradeRiskRequest,
    )

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    # "chlorpyrifos-methyl" should NOT match the "glyphosate" MRL records on apples,
    # and trade-risk evaluation should now return an explicit invalid_request instead
    # of a false "pass" when the governed substance identity cannot be resolved.
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "chlorpyrifos-methyl"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=10.0,
                    source_type="monitoring",
                )
            ],
        )
    )
    assert not any(flag.code == "mrl_violation" for flag in residue_profile.quality_flags)

    from dietary_mcp.models import DietaryCommodityResidueInput
    trade_report = runtime.evaluate_global_trade_risk(
        EvaluateGlobalTradeRiskRequest(
            chemical_identity={"preferredName": "chlorpyrifos-methyl"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=10.0,
                    source_type="monitoring",
                )
            ],
            target_jurisdictions=["us", "eu"],
        )
    )
    for profile in trade_report.jurisdiction_profiles:
        assert profile.trade_status == "invalid_request"
        assert any(flag.code == "unresolvable_trade_risk_chemical_identity" for flag in profile.quality_flags)
        assert not any(flag.code == "trade_mrl_violation" for flag in profile.mrl_violations)
        assert any("stopped before jurisdiction-specific screening" in note for note in profile.notes)

    # Sanity check: actual glyphosate SHOULD still match and trigger violation
    glyphosate_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "glyphosate"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=10.0,
                    source_type="monitoring",
                )
            ],
        )
    )
    assert any(flag.code == "mrl_violation" for flag in glyphosate_profile.quality_flags)


def test_trade_risk_supports_explicit_china_targeting_and_curated_gap_flags() -> None:
    from pathlib import Path
    from dietary_mcp.runtime import DietaryRuntime
    from dietary_mcp.models import DietaryCommodityResidueInput, EvaluateGlobalTradeRiskRequest

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    trade_report = runtime.evaluate_global_trade_risk(
        EvaluateGlobalTradeRiskRequest(
            chemical_identity={"preferredName": "acetamiprid"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="grapes",
                    residue_concentration_mg_per_kg=0.8,
                    source_type="monitoring",
                )
            ],
            target_jurisdictions=["us", "codex_global", "cn"],
        )
    )

    profiles = {profile.jurisdiction: profile for profile in trade_report.jurisdiction_profiles}

    assert set(profiles) == {"us", "codex_global", "cn"}
    assert any("does not borrow MRLs or reference values" in note for note in trade_report.notes)
    assert any("pass status only means" in note for note in trade_report.notes)
    assert profiles["us"].trade_status == "inconclusive_no_limit"
    assert {flag.code for flag in profiles["us"].quality_flags} >= {
        "no_jurisdiction_specific_reference_value",
        "anchor_only_family_without_reference_value",
        "missing_trade_limit",
        "no_curated_mrl_for_requested_pair",
        "anchor_only_family_without_trade_mrl",
    }
    assert {item.coverage_level.value for item in profiles["us"].coverage_summaries} == {"anchor_only"}
    assert profiles["us"].mrl_coverage_status.value == "anchor_only_family"
    assert profiles["us"].mrl_curated_support_types == ["legal_anchors"]
    assert profiles["us"].mrl_curated_scope_commodity_codes == []
    assert any("official family anchor" in note for note in profiles["us"].notes)
    assert profiles["us"].reference_value_jurisdiction_status.value == "anchor_only_family"
    assert profiles["us"].reference_value_curated_support_types == ["legal_anchors"]
    assert profiles["codex_global"].trade_status == "fail"
    assert any(flag.code == "trade_mrl_violation" for flag in profiles["codex_global"].mrl_violations)
    assert {item.coverage_level.value for item in profiles["codex_global"].coverage_summaries} == {"deep_curated"}
    assert profiles["codex_global"].mrl_coverage_status.value == "all_requested_pairs_exactly_curated"
    assert profiles["codex_global"].mrl_curated_support_types == ["enforcement_records", "legal_anchors"]
    assert profiles["codex_global"].mrl_curated_scope_commodity_codes == ["grapes"]
    assert any("jurisdiction-specific MRL coverage" in note for note in profiles["codex_global"].notes)
    assert profiles["codex_global"].reference_value_jurisdiction_status.value == "exact_jurisdiction_value_present"
    assert profiles["cn"].trade_status == "pass"
    assert {item.coverage_level.value for item in profiles["cn"].coverage_summaries} == {"deep_curated"}
    assert profiles["cn"].mrl_coverage_status.value == "all_requested_pairs_exactly_curated"
    assert profiles["cn"].mrl_curated_support_types == ["enforcement_records", "legal_anchors"]
    assert profiles["cn"].mrl_curated_scope_commodity_codes == ["apples", "grapes", "tomatoes"]
    assert any("jurisdiction-specific reference-value record" in note for note in profiles["cn"].notes)
    assert profiles["cn"].reference_value_jurisdiction_status.value == "exact_jurisdiction_value_present"
    assert not any(
        flag.code in {"missing_trade_limit", "no_curated_mrl_for_requested_pair"}
        for flag in profiles["cn"].quality_flags
    )


def test_trade_risk_distinguishes_pair_scope_misses_from_family_curated_without_mrl() -> None:
    from pathlib import Path
    from dietary_mcp.runtime import DietaryRuntime
    from dietary_mcp.models import DietaryCommodityResidueInput, EvaluateGlobalTradeRiskRequest

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    trade_report = runtime.evaluate_global_trade_risk(
        EvaluateGlobalTradeRiskRequest(
            chemical_identity={"preferredName": "glyphosate"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="grapes",
                    residue_concentration_mg_per_kg=0.2,
                    source_type="monitoring",
                )
            ],
            target_jurisdictions=["us", "codex_global"],
        )
    )

    profiles = {profile.jurisdiction: profile for profile in trade_report.jurisdiction_profiles}

    assert profiles["us"].trade_status == "inconclusive_no_limit"
    assert profiles["us"].mrl_coverage_status.value == "requested_pair_outside_curated_scope"
    assert profiles["us"].mrl_curated_support_types == ["enforcement_records", "legal_anchors"]
    assert profiles["us"].mrl_curated_scope_commodity_codes == ["rice"]
    assert any("extends beyond the current shipped scope (rice)" in note for note in profiles["us"].notes)
    assert {flag.code for flag in profiles["us"].quality_flags} >= {
        "missing_trade_limit",
        "no_curated_mrl_for_requested_pair",
        "requested_trade_pair_outside_curated_scope",
    }
    assert "coverage_gap" not in {flag.code for flag in profiles["us"].quality_flags}

    assert profiles["codex_global"].trade_status == "inconclusive_no_limit"
    assert profiles["codex_global"].mrl_coverage_status.value == "family_curated_without_mrl"
    assert profiles["codex_global"].mrl_curated_support_types == ["legal_anchors"]
    assert profiles["codex_global"].mrl_curated_scope_commodity_codes == []
    assert any("does not currently ship a jurisdiction-specific MRL layer" in note for note in profiles["codex_global"].notes)
    assert {flag.code for flag in profiles["codex_global"].quality_flags} >= {
        "missing_trade_limit",
        "no_curated_mrl_for_requested_pair",
        "family_curated_without_trade_mrl",
    }
    assert "coverage_gap" not in {flag.code for flag in profiles["codex_global"].quality_flags}


def test_trade_risk_mrl_coverage_status_surfaces_explicit_gap_and_no_curated_family_coverage() -> None:
    from pathlib import Path
    from dietary_mcp.runtime import DietaryRuntime
    from dietary_mcp.models import (
        ContaminantFamily,
        DietaryCommodityResidueInput,
        EvaluateGlobalTradeRiskRequest,
    )

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    us_pfas_report = runtime.evaluate_global_trade_risk(
        EvaluateGlobalTradeRiskRequest(
            chemical_identity={"preferredName": "sum_pfoa_pfna_pfhxs_pfos"},
            contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.01,
                    source_type="monitoring",
                )
            ],
            target_jurisdictions=["us"],
        )
    )
    us_difenoconazole_report = runtime.evaluate_global_trade_risk(
        EvaluateGlobalTradeRiskRequest(
            chemical_identity={"preferredName": "difenoconazole"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.01,
                    source_type="monitoring",
                )
            ],
            target_jurisdictions=["us"],
        )
    )

    us_pfas = us_pfas_report.jurisdiction_profiles[0]
    us_difenoconazole = us_difenoconazole_report.jurisdiction_profiles[0]

    assert us_pfas.mrl_coverage_status.value == "explicit_gap"
    assert any("explicit MRL coverage gap" in note for note in us_pfas.notes)
    assert {flag.code for flag in us_pfas.quality_flags} >= {
        "missing_trade_limit",
        "no_curated_mrl_for_requested_pair",
        "coverage_gap",
    }
    assert us_difenoconazole.mrl_coverage_status.value == "no_curated_family_coverage"
    assert any("No curated trade-risk MRL coverage record" in note for note in us_difenoconazole.notes)
    assert {flag.code for flag in us_difenoconazole.quality_flags} >= {
        "missing_trade_limit",
        "no_curated_mrl_for_requested_pair",
        "coverage_gap",
    }


def test_trade_risk_review_bundle_and_dossier_freeze_semantics_for_review() -> None:
    from pathlib import Path
    from dietary_mcp.runtime import DietaryRuntime
    from dietary_mcp.models import (
        DietaryCommodityResidueInput,
        EvaluateGlobalTradeRiskRequest,
        ExportTradeRiskReviewBundleRequest,
        ExportVersionPinnedTradeRiskReviewDossierRequest,
    )

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    review_required_report = runtime.evaluate_global_trade_risk(
        EvaluateGlobalTradeRiskRequest(
            chemical_identity={"preferredName": "glyphosate"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="grapes",
                    residue_concentration_mg_per_kg=0.2,
                    source_type="monitoring",
                )
            ],
            target_jurisdictions=["us", "codex_global"],
        )
    )
    assert review_required_report.resolved_substance_key == "glyphosate"

    review_bundle = runtime.export_trade_risk_review_bundle(
        ExportTradeRiskReviewBundleRequest(
            trade_report=review_required_report,
            bundle_note="Illustrative review note for trade-risk bundle testing.",
        )
    )
    assert review_bundle.review_status == "review_required"
    assert review_bundle.documentation_resource_uri == "docs://trade-risk-review"
    assert any(resource.uri == "mrl-enforcement://manifest" for resource in review_bundle.referenced_resources)
    assert any(prompt.category == "mrl_coverage_semantics" for prompt in review_bundle.review_prompts)
    assert any("No-borrowing semantics" in note for note in review_bundle.notes)
    assert review_bundle.covered_source_ids

    review_dossier = runtime.export_version_pinned_trade_risk_review_dossier(
        ExportVersionPinnedTradeRiskReviewDossierRequest(review_bundle=review_bundle)
    )
    assert review_dossier.dossier_status == "review_required"
    assert review_dossier.review_bundle.trade_report.resolved_substance_key == "glyphosate"
    assert any(item.uri == "mrl-enforcement://manifest" for item in review_dossier.pinned_resources)
    assert any(item.uri == "docs://trade-risk-review" for item in review_dossier.pinned_resources)
    assert any("internal review only" in note.lower() for note in review_dossier.notes)

    screening_clear_report = runtime.evaluate_global_trade_risk(
        EvaluateGlobalTradeRiskRequest(
            chemical_identity={"preferredName": "acetamiprid"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="grapes",
                    residue_concentration_mg_per_kg=0.1,
                    source_type="monitoring",
                )
            ],
            target_jurisdictions=["cn"],
        )
    )
    screening_clear_bundle = runtime.export_trade_risk_review_bundle(
        ExportTradeRiskReviewBundleRequest(trade_report=screening_clear_report)
    )
    assert screening_clear_bundle.review_status == "screening_clear"


def test_export_sanitised_public_review_dossier_supports_trade_risk_review() -> None:
    from pathlib import Path
    from dietary_mcp.runtime import DietaryRuntime
    from dietary_mcp.models import (
        DietaryCommodityResidueInput,
        EvaluateGlobalTradeRiskRequest,
        ExportTradeRiskReviewBundleRequest,
        ExportVersionPinnedTradeRiskReviewDossierRequest,
    )

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    trade_report = runtime.evaluate_global_trade_risk(
        EvaluateGlobalTradeRiskRequest(
            chemical_identity={"preferredName": "glyphosate"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="grapes",
                    residue_concentration_mg_per_kg=0.2,
                    source_type="monitoring",
                )
            ],
            target_jurisdictions=["us", "codex_global"],
        )
    )
    review_bundle = runtime.export_trade_risk_review_bundle(
        ExportTradeRiskReviewBundleRequest(trade_report=trade_report)
    )
    review_dossier = runtime.export_version_pinned_trade_risk_review_dossier(
        ExportVersionPinnedTradeRiskReviewDossierRequest(review_bundle=review_bundle)
    )

    sanitised = runtime.export_sanitised_public_review_dossier(
        ExportSanitisedPublicReviewDossierRequest(dossier=review_dossier)
    )

    assert sanitised.source_workflow == "trade_risk_review_dossier"
    assert sanitised.legal_limit_reviews == []
    assert sanitised.escalation_required is False
    assert sanitised.escalation_action_ids == []
    assert sanitised.model_governance_snapshot is None
    assert sanitised.emerging_contaminant_snapshot is None
    assert sanitised.public_review_bundle.review_status == review_bundle.review_status
    assert {
        profile.trade_status for profile in sanitised.public_review_bundle.trade_report.jurisdiction_profiles
    } == {profile.trade_status for profile in review_bundle.trade_report.jurisdiction_profiles}
    assert not any(
        item.uri.startswith("reference-values://substance/")
        or item.uri.startswith("mrl-enforcement://substance/")
        for item in sanitised.public_review_bundle.referenced_resources
    )
    assert not any(
        item.uri.startswith("reference-values://substance/")
        or item.uri.startswith("mrl-enforcement://substance/")
        for item in sanitised.pinned_resources
    )
    assert any(
        item.target_path == "review_bundle.trade_report.chemical_identity"
        and item.sanitisation_state.value == "redacted"
        for item in sanitised.sanitisation_records
    )
    assert any(
        item.target_path == "review_bundle.trade_report.resolved_substance_key"
        and item.sanitisation_state.value == "redacted"
        for item in sanitised.sanitisation_records
    )


def test_export_sanitised_public_review_dossier_supports_scientific_follow_up_owner_signoff() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    source_dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                ExportContaminantMonitoringSignoffPacketRequest(
                    interpretation_bundle=interpretation_bundle,
                    reviewer_id="runtime.owner.public",
                    reviewer_role="scientific_reviewer",
                    decisions=[
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.row_level_lod_coverage",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="LOD coverage reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                            decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                            rationale="Lower-bound handling retained as waiver.",
                            supporting_uris=["docs://contaminant-monitoring-signoff"],
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Storage stability reviewed.",
                        ),
                        ContaminantMonitoringSignoffDecisionInput(
                            action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                            decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                            rationale="Sampling plan reviewed.",
                        ),
                    ],
                )
            ),
        )
    )
    readiness = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=source_dossier,
            target_profile="mercury_internal_review",
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(dossier=source_dossier, assessment=readiness)
    )
    board = runtime.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(queue_bundle=queue_bundle)
    )
    handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(
            board=board,
            owner_lane="review_lead",
            due_state_filter=["immediate"],
        )
    )
    remediation_packet = runtime.export_scientific_follow_up_owner_remediation_packet(
        ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=handoff_packet)
    )
    signoff_packet = runtime.export_scientific_follow_up_owner_signoff_packet(
        ExportScientificFollowUpOwnerSignoffPacketRequest(
            remediation_packet=remediation_packet,
            reviewer_id="runtime.owner.public",
            reviewer_role="review_lead",
            decisions=[
                {
                    "actionId": "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                    "decisionStatus": "waived",
                    "rationale": "Lower-bound handling retained with explicit public waiver trace.",
                    "reviewedAt": "2026-04-12",
                }
            ],
        )
    )
    review_dossier = runtime.export_version_pinned_scientific_follow_up_owner_signoff_dossier(
        ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest(
            source_dossier=source_dossier,
            signoff_packet=signoff_packet,
        )
    )

    sanitised = runtime.export_sanitised_public_review_dossier(
        ExportSanitisedPublicReviewDossierRequest(dossier=review_dossier)
    )

    assert sanitised.source_workflow == "scientific_follow_up_owner_signoff_dossier"
    assert len(sanitised.legal_limit_reviews) == len(review_dossier.legal_limit_reviews)
    assert sanitised.escalation_required is True
    assert sanitised.escalation_action_ids == [
        "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context"
    ]
    assert sanitised.model_governance_snapshot is None
    assert sanitised.emerging_contaminant_snapshot is not None
    assert sanitised.public_review_bundle.owner_lane.value == "review_lead"
    assert sanitised.public_review_bundle.overall_signoff_status == signoff_packet.overall_signoff_status
    assert sanitised.public_review_bundle.waived_action_ids == signoff_packet.waived_action_ids
    assert sanitised.public_review_bundle.unresolved_blocking_action_ids == signoff_packet.unresolved_blocking_action_ids
    assert not any(
        item.uri.startswith("internal://scientific-follow-up-source-dossier/")
        or item.uri.startswith("internal://scientific-follow-up-owner-signoff-packet/")
        for item in sanitised.pinned_resources
    )
    removed_roles = {
        item.target_path.split(".")[-1]
        for item in sanitised.sanitisation_records
        if item.target_kind == "resource" and item.sanitisation_state.value == "removed"
    }
    assert removed_roles >= {"release_metadata_report", "source_dossier_payload", "owner_signoff_packet_payload"}


def test_assess_residue_evidence_fit_flags_missing_bounds_for_bounded_workflow() -> None:
    """Bounded workflows require explicit lower/upper bounds on all residue records."""
    from pathlib import Path
    from dietary_mcp.runtime import DietaryRuntime
    from dietary_mcp.models import (
        BuildDietaryResidueProfileRequest,
        DietaryCommodityResidueInput,
        SelectConsumptionProfileRequest,
        AssessResidueEvidenceFitRequest,
    )
    from dietary_mcp.models import ScenarioClass

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    # Profile without bounds
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "TestChem"},
            residue_records=[
                DietaryCommodityResidueInput(commodity_code="apples", residue_concentration_mg_per_kg=1.0, source_type="monitoring")
            ],
        )
    )

    consumption_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(region_id="eu_screening_default", population_group="adult_general", intake_window="chronic")
    ).profile

    fit = runtime.assess_residue_evidence_fit(
        AssessResidueEvidenceFitRequest(
            residue_profile=residue_profile,
            consumption_profile=consumption_profile,
            scenario_class=ScenarioClass.BOUNDED_CHRONIC,
        )
    )
    assert fit.fit_score < 1.0
    assert any("bounds" in reason.lower() for reason in fit.reasons)


def test_reconcile_residue_evidence_computes_mean_and_bounds() -> None:
    """Reconciling two profiles for the same commodity should produce mean concentration and min/max bounds."""
    from pathlib import Path
    from dietary_mcp.runtime import DietaryRuntime
    from dietary_mcp.models import (
        BuildDietaryResidueProfileRequest,
        DietaryCommodityResidueInput,
        ReconcileResidueEvidenceRequest,
        ResidueSourceType,
    )

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    profile_a = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "TestChem"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples", residue_concentration_mg_per_kg=1.0,
                    lower_bound_mg_per_kg=0.8, upper_bound_mg_per_kg=1.2, source_type="monitoring"
                )
            ],
        )
    )
    profile_b = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "TestChem"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples", residue_concentration_mg_per_kg=2.0,
                    lower_bound_mg_per_kg=1.5, upper_bound_mg_per_kg=2.5, source_type="monitoring"
                )
            ],
        )
    )

    result = runtime.reconcile_residue_evidence(
        ReconcileResidueEvidenceRequest(
            chemical_identity={"preferredName": "TestChem"},
            evidence_profiles=[profile_a, profile_b],
        )
    )

    reconciled = result.reconciled_profile.records[0]
    assert reconciled.residue_concentration_mg_per_kg == pytest.approx(1.5, abs=1e-12)
    assert reconciled.lower_bound_mg_per_kg == pytest.approx(0.8, abs=1e-12)
    assert reconciled.upper_bound_mg_per_kg == pytest.approx(2.5, abs=1e-12)
    assert reconciled.source_type is ResidueSourceType.RECONCILED
    payload = result.model_dump(mode="json")
    assert payload["reconciled_profile"]["records"][0]["source_type"] == "reconciled"


def test_empty_residue_profile_produces_zero_intake() -> None:
    """An empty residue profile should result in zero total intake."""
    from pathlib import Path
    from dietary_mcp.runtime import DietaryRuntime
    from dietary_mcp.models import (
        BuildDietaryResidueProfileRequest,
        SelectConsumptionProfileRequest,
        BuildDietaryIntakeScenarioRequest,
        BuildBoundedIntakeSummaryRequest,
    )

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    empty_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "TestChem"},
            residue_records=[],
        )
    )

    consumption_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(region_id="eu_screening_default", population_group="adult_general", intake_window="chronic")
    ).profile

    scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity={"preferredName": "TestChem"},
            residue_profile=empty_profile,
            consumption_profile=consumption_profile,
        )
    )

    summary = runtime.summarize_intake(BuildBoundedIntakeSummaryRequest(scenario=scenario))
    assert summary.total_intake_mg_per_kg_bw_per_day == 0.0
    assert summary.commodity_contributions == []


def test_unknown_commodity_in_survey_dataset_is_silently_dropped_with_quality_flag() -> None:
    """Survey records for unknown commodities must be dropped and flagged, not crash."""
    from pathlib import Path
    from dietary_mcp.runtime import DietaryRuntime
    from dietary_mcp.models import ParseRawSurveyDatasetRequest, RawSurveyRecordInput

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])

    dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest(
            datasetId="unknown_test",
            regionId="eu",
            populationGroup="adult_general",
            rawRecords=[
                RawSurveyRecordInput(subjectId="s1", bodyWeightKg=70.0, daysInSurvey=1, commodityCode="totally_unknown_food", consumptionKgPerDay=0.5),
            ],
        )
    )

    assert len(dataset.records) == 0
    assert any(flag.code == "unknown_survey_commodity" for flag in dataset.quality_flags)


def test_runtime_soft_limits_reject_large_inputs(monkeypatch) -> None:
    from dietary_mcp.models import BuildProbabilisticIntakeSummaryRequest, EvaluateGlobalTradeRiskRequest

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    residue = DietaryCommodityResidueInput(
        commodity_code="apples",
        residue_concentration_mg_per_kg=0.2,
        source_type=ResidueSourceType.MONITORING,
    )
    raw_record = RawSurveyRecordInput(
        subjectId="s1",
        bodyWeightKg=70.0,
        daysInSurvey=1,
        commodityCode="apples",
        consumptionKgPerDay=0.2,
    )

    monkeypatch.setenv("DIETARY_MCP_MAX_RESIDUE_RECORDS", "1")
    with pytest.raises(DietaryValidationError) as residue_error:
        runtime.build_residue_profile(
            BuildDietaryResidueProfileRequest(
                chemical_identity={"preferredName": "Example"},
                residue_records=[residue, residue],
            )
        )
    assert residue_error.value.payload.code == "input_limit_exceeded"

    monkeypatch.delenv("DIETARY_MCP_MAX_RESIDUE_RECORDS")
    monkeypatch.setenv("DIETARY_MCP_MAX_RAW_SURVEY_RECORDS", "1")
    with pytest.raises(DietaryValidationError) as raw_error:
        runtime.parse_raw_survey_dataset(
            ParseRawSurveyDatasetRequest(
                datasetId="too_many_rows",
                regionId="eu",
                populationGroup="adult_general",
                rawRecords=[raw_record, raw_record],
            )
        )
    assert raw_error.value.payload.code == "input_limit_exceeded"

    monkeypatch.setenv("DIETARY_MCP_MAX_RAW_SURVEY_RECORDS", "2")
    dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest(
            datasetId="small_dataset",
            regionId="eu",
            populationGroup="adult_general",
            rawRecords=[raw_record, raw_record.model_copy(update={"subject_id": "s2"})],
        )
    )
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Example"},
            residue_records=[residue],
        )
    )

    monkeypatch.setenv("DIETARY_MCP_MAX_CSV_BYTES", "10")
    with pytest.raises(DietaryValidationError) as csv_error:
        runtime.check_adapter_import(
            CheckAdapterImportRequest(
                model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
                population_group="adult_general",
                intake_window=IntakeWindowSemantic.CHRONIC,
                scenario_class=ScenarioClass.POINT_ESTIMATE,
                chemical_identity={"preferredName": "Example"},
                residue_records=[residue],
                external_engine_version="test",
                declared_total_intake_mg_per_kg_bw_per_day=0.0,
                csv_text="x" * 11,
            )
        )
    assert csv_error.value.payload.code == "input_limit_exceeded"

    monkeypatch.setenv("DIETARY_MCP_MAX_TARGET_JURISDICTIONS", "1")
    with pytest.raises(DietaryValidationError) as jurisdiction_error:
        runtime.evaluate_global_trade_risk(
            EvaluateGlobalTradeRiskRequest(
                chemical_identity={"preferredName": "glyphosate"},
                residue_records=[residue],
                target_jurisdictions=["eu", "us"],
            )
        )
    assert jurisdiction_error.value.payload.code == "input_limit_exceeded"

    monkeypatch.setenv("DIETARY_MCP_MAX_PROBABILISTIC_ITERATIONS", "100")
    with pytest.raises(DietaryValidationError) as iteration_error:
        runtime.build_probabilistic_intake_summary(
            BuildProbabilisticIntakeSummaryRequest(
                dataset=dataset,
                residue_profile=residue_profile,
                iterationCount=101,
            )
        )
    assert iteration_error.value.payload.code == "input_limit_exceeded"

    monkeypatch.setenv("DIETARY_MCP_MAX_PROBABILISTIC_ITERATIONS", "100")
    monkeypatch.setenv("DIETARY_MCP_MAX_PROBABILISTIC_DRAWS", "199")
    with pytest.raises(DietaryValidationError) as draw_error:
        runtime.build_probabilistic_intake_summary(
            BuildProbabilisticIntakeSummaryRequest(
                dataset=dataset,
                residue_profile=residue_profile,
                iterationCount=100,
            )
        )
    assert draw_error.value.payload.code == "probabilistic_draw_limit_exceeded"


def test_runtime_env_overrides_cannot_bypass_hard_schema_limits(monkeypatch) -> None:
    from pydantic import ValidationError

    from dietary_mcp.models import (
        BuildProbabilisticIntakeSummaryRequest,
        MAX_PROBABILISTIC_ITERATIONS,
        MAX_RESIDUE_RECORDS,
    )

    residue = DietaryCommodityResidueInput(
        commodity_code="apples",
        residue_concentration_mg_per_kg=0.2,
        source_type=ResidueSourceType.MONITORING,
    )
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Example"},
            residue_records=[residue],
        )
    )
    dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest(
            datasetId="schema_limit_dataset",
            regionId="eu",
            populationGroup="adult_general",
            rawRecords=[
                RawSurveyRecordInput(
                    subjectId="s1",
                    bodyWeightKg=70.0,
                    daysInSurvey=1,
                    commodityCode="apples",
                    consumptionKgPerDay=0.2,
                )
            ],
        )
    )

    monkeypatch.setenv("DIETARY_MCP_MAX_RESIDUE_RECORDS", "999999")
    with pytest.raises(ValidationError):
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Example"},
            residue_records=[residue] * (MAX_RESIDUE_RECORDS + 1),
        )

    monkeypatch.setenv("DIETARY_MCP_MAX_PROBABILISTIC_ITERATIONS", "999999999")
    with pytest.raises(ValidationError):
        BuildProbabilisticIntakeSummaryRequest(
            dataset=dataset,
            residue_profile=residue_profile,
            iterationCount=MAX_PROBABILISTIC_ITERATIONS + 1,
        )


def test_probabilistic_summary_requires_deterministic_random_seed() -> None:
    from pydantic import ValidationError

    from dietary_mcp.models import BuildProbabilisticIntakeSummaryRequest

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest(
            datasetId="seed_required_dataset",
            regionId="eu",
            populationGroup="adult_general",
            rawRecords=[
                RawSurveyRecordInput(
                    subjectId="s1",
                    bodyWeightKg=70.0,
                    daysInSurvey=1,
                    commodityCode="apples",
                    consumptionKgPerDay=0.2,
                )
            ],
        )
    )
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.2,
                    source_type=ResidueSourceType.MONITORING,
                )
            ],
        )
    )

    with pytest.raises(ValidationError):
        BuildProbabilisticIntakeSummaryRequest(
            dataset=dataset,
            residue_profile=residue_profile,
            iterationCount=100,
            randomSeed=None,
        )


def test_uncertainty_intake_assessment_reports_weighting_and_reproducibility() -> None:
    from dietary_mcp.models import BuildUncertaintyIntakeAssessmentRequest, ResidueUncertaintyModel

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    base_records = [
        RawSurveyRecordInput(
            subjectId="high_consumer",
            bodyWeightKg=70.0,
            daysInSurvey=1,
            commodityCode="apples",
            consumptionKgPerDay=0.6,
        ),
        RawSurveyRecordInput(
            subjectId="non_consumer",
            bodyWeightKg=70.0,
            daysInSurvey=1,
            commodityCode="apples",
            consumptionKgPerDay=0.0,
        ),
    ]
    weighted_records = [
        base_records[0].model_copy(update={"survey_weight": 0.1}),
        base_records[1].model_copy(update={"survey_weight": 10.0}),
    ]
    unweighted_dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest(
            datasetId="uncertainty_unweighted",
            regionId="eu",
            populationGroup="adult_general",
            rawRecords=base_records,
        )
    )
    weighted_dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest(
            datasetId="uncertainty_weighted",
            regionId="eu",
            populationGroup="adult_general",
            rawRecords=weighted_records,
        )
    )
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "UncertaintyRuntime"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.2,
                    source_type=ResidueSourceType.MONITORING,
                )
            ],
        )
    )
    model = ResidueUncertaintyModel(commodityCode="apples", distribution="point", pointMgPerKg=0.2)

    unweighted = runtime.build_uncertainty_intake_assessment(
        BuildUncertaintyIntakeAssessmentRequest(
            dataset=unweighted_dataset,
            residue_profile=residue_profile,
            randomSeed=17,
            outerIterationCount=20,
            innerIterationCount=60,
            residueUncertaintyModels=[model],
        )
    )
    weighted = runtime.build_uncertainty_intake_assessment(
        BuildUncertaintyIntakeAssessmentRequest(
            dataset=weighted_dataset,
            residue_profile=residue_profile,
            randomSeed=17,
            outerIterationCount=20,
            innerIterationCount=60,
            residueUncertaintyModels=[model],
        )
    )

    assert unweighted.assessment_mode == "two_dimensional_monte_carlo"
    assert unweighted.weighted_sampling is False
    assert weighted.weighted_sampling is True
    assert weighted.reproducibility.rng_algorithm == "numpy.PCG64"
    assert weighted.distribution_summary.mean.median < unweighted.distribution_summary.mean.median
    assert {entry.code for entry in weighted.uncertainty_assumption_ledger.entries} >= {
        "two_dimensional_monte_carlo",
        "survey_weighted_sampling",
        "three_bound_censored_sensitivity",
        "regulatory_acceptance_not_implied",
    }


def test_uncertainty_runtime_rejects_oversized_draws_before_simulation(monkeypatch) -> None:
    from dietary_mcp.models import BuildUncertaintyIntakeAssessmentRequest, ResidueUncertaintyModel

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    raw_record = RawSurveyRecordInput(
        subjectId="s1",
        bodyWeightKg=70.0,
        daysInSurvey=1,
        commodityCode="apples",
        consumptionKgPerDay=0.2,
    )
    dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest(
            datasetId="uncertainty_draw_limit",
            regionId="eu",
            populationGroup="adult_general",
            rawRecords=[raw_record],
        )
    )
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "UncertaintyLimit"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.2,
                    source_type=ResidueSourceType.MONITORING,
                )
            ],
        )
    )

    monkeypatch.setenv("DIETARY_MCP_MAX_UNCERTAINTY_DRAWS", "399")
    with pytest.raises(DietaryValidationError) as draw_error:
        runtime.build_uncertainty_intake_assessment(
            BuildUncertaintyIntakeAssessmentRequest(
                dataset=dataset,
                residue_profile=residue_profile,
                randomSeed=11,
                outerIterationCount=20,
                innerIterationCount=20,
                residueUncertaintyModels=[
                    ResidueUncertaintyModel(
                        commodityCode="apples",
                        distribution="uniform",
                        minMgPerKg=0.1,
                        maxMgPerKg=0.3,
                    )
                ],
            )
        )
    assert draw_error.value.payload.code == "uncertainty_draw_limit_exceeded"


def test_uncertainty_runtime_rejects_model_without_matching_residue_record() -> None:
    from dietary_mcp.models import BuildUncertaintyIntakeAssessmentRequest, ResidueUncertaintyModel

    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest(
            datasetId="uncertainty_bad_model",
            regionId="eu",
            populationGroup="adult_general",
            rawRecords=[
                RawSurveyRecordInput(
                    subjectId="s1",
                    bodyWeightKg=70.0,
                    daysInSurvey=1,
                    commodityCode="apples",
                    consumptionKgPerDay=0.2,
                )
            ],
        )
    )
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "UncertaintyBadModel"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.2,
                    source_type=ResidueSourceType.MONITORING,
                )
            ],
        )
    )

    with pytest.raises(DietaryValidationError) as model_error:
        runtime.build_uncertainty_intake_assessment(
            BuildUncertaintyIntakeAssessmentRequest(
                dataset=dataset,
                residue_profile=residue_profile,
                randomSeed=12,
                outerIterationCount=10,
                innerIterationCount=10,
                residueUncertaintyModels=[
                    ResidueUncertaintyModel(
                        commodityCode="rice",
                        distribution="point",
                        pointMgPerKg=0.1,
                    )
                ],
            )
        )
    assert model_error.value.payload.code == "uncertainty_model_without_residue_record"
