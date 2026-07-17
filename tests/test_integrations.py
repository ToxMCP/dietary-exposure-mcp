from pathlib import Path

from dietary_mcp.integrations import (
    compare_dietary_scenarios,
    export_adapter_review_bundle,
    export_pbpk_oral_input,
    export_toxclaw_dietary_evidence_bundle,
)
from dietary_mcp.models import (
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    BuildBoundedIntakeSummaryRequest,
    CheckAdapterImportRequest,
    CompareAdapterImportToWalkthroughRequest,
    CompareDietaryScenariosRequest,
    DietaryCommodityResidueInput,
    ExportAdapterReviewBundleRequest,
    ExportSanitisedPublicReviewDossierRequest,
    ExportVersionPinnedAdapterReviewDossierRequest,
    ExportPbpkOralInputRequest,
    ExportToxclawDietaryEvidenceBundleRequest,
    IntakeWindowSemantic,
    ModelFamily,
    ResidueSourceType,
    ScenarioClass,
    SelectConsumptionProfileRequest,
)
from dietary_mcp.runtime import DietaryRuntime
from dietary_mcp.review_dossier import export_version_pinned_adapter_review_dossier
from dietary_mcp.sanitisation import export_sanitised_public_review_dossier


def test_compare_dietary_scenarios_and_export_pbpk_bundle() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    base_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.1,
                    source_type=ResidueSourceType.MONITORING,
                )
            ],
        )
    )
    candidate_profile = runtime.build_residue_profile(
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
    consumption_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="adult_general",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["apples"],
        )
    ).profile
    base_scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=base_profile.chemical_identity,
            residue_profile=base_profile,
            consumption_profile=consumption_profile,
            scenario_class=ScenarioClass.POINT_ESTIMATE,
            intake_window_semantic=IntakeWindowSemantic.CHRONIC,
        )
    )
    candidate_scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=candidate_profile.chemical_identity,
            residue_profile=candidate_profile,
            consumption_profile=consumption_profile,
            scenario_class=ScenarioClass.POINT_ESTIMATE,
            intake_window_semantic=IntakeWindowSemantic.CHRONIC,
        )
    )
    base_summary = runtime.summarize_intake(BuildBoundedIntakeSummaryRequest(scenario=base_scenario))
    candidate_summary = runtime.summarize_intake(
        BuildBoundedIntakeSummaryRequest(scenario=candidate_scenario)
    )

    comparison = compare_dietary_scenarios(
        CompareDietaryScenariosRequest(
            base_summary=base_summary,
            candidate_summary=candidate_summary,
        ),
        runtime.provenance,
    )
    assert comparison.intake_delta_mg_per_kg_bw_per_day > 0.0

    bundle = export_pbpk_oral_input(
        ExportPbpkOralInputRequest(
            scenario=candidate_scenario,
            summary=candidate_summary,
            exposurePlausibilityRecords=[
                {
                    "recordId": "csa-high-micromolar",
                    "chemicalId": "DTXSID0020365",
                    "chemicalName": "Cyclosporin A",
                    "classification": "implausible",
                    "decisionEffect": "exclude_from_dose_claims",
                    "ratioToHumanExposure": 151.5,
                    "rationale": (
                        "High-micromolar direct cell injury evidence exceeds plausible "
                        "therapeutic exposure."
                    ),
                }
            ],
        ),
        runtime.provenance,
    )
    assert bundle.route_dose_estimate.value_mg_per_kg_bw_per_day == candidate_summary.total_intake_mg_per_kg_bw_per_day
    assert bundle.dependencies
    assert bundle.exposure_plausibility_records[0].record_id == "csa-high-micromolar"
    assert bundle.exposure_plausibility_records[0].decision_effect == "exclude_from_dose_claims"
    toxclaw_bundle = export_toxclaw_dietary_evidence_bundle(
        ExportToxclawDietaryEvidenceBundleRequest(
            scenario=candidate_scenario,
            summary=candidate_summary,
        ),
        runtime.provenance,
    )
    assert toxclaw_bundle.evidence_items
    assert toxclaw_bundle.route_dose_estimate.scenario_id == candidate_summary.scenario_id


def test_adapter_family_is_carried_into_downstream_dependencies() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.05,
                    source_type=ResidueSourceType.MONITORING,
                )
            ],
        )
    )
    consumption_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="adult_general",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["milk"],
        )
    ).profile
    scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=residue_profile.chemical_identity,
            residue_profile=residue_profile,
            consumption_profile=consumption_profile,
            scenario_class=ScenarioClass.POINT_ESTIMATE,
            intake_window_semantic=IntakeWindowSemantic.CHRONIC,
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
        )
    )
    summary = runtime.summarize_intake(BuildBoundedIntakeSummaryRequest(scenario=scenario))

    bundle = export_pbpk_oral_input(
        ExportPbpkOralInputRequest(scenario=scenario, summary=summary),
        runtime.provenance,
    )
    assert any(
        item.role == "model_family" and item.name == ModelFamily.EFSA_PRIMO_ADAPTER.value
        for item in bundle.dependencies
    )


def test_export_adapter_review_bundle_emits_auditable_handoff() -> None:
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

    bundle = export_adapter_review_bundle(
        ExportAdapterReviewBundleRequest(
            check_result=check_result,
            comparison_result=comparison,
        )
    )

    assert bundle.review_status == "match"
    assert bundle.mismatch_field_count == 0
    assert any(item.role == "documentation" for item in bundle.referenced_resources)
    assert any(item.role == "check_workflow" for item in bundle.dependencies)
    assert any(item.role == "comparison_workflow" for item in bundle.dependencies)


def test_export_version_pinned_adapter_review_dossier_emits_release_fingerprints() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    runtime = DietaryRuntime(repo_root)
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
    bundle = export_adapter_review_bundle(
        ExportAdapterReviewBundleRequest(
            check_result=check_result,
            comparison_result=comparison,
        )
    )
    dossier = export_version_pinned_adapter_review_dossier(
        repo_root,
        ExportVersionPinnedAdapterReviewDossierRequest(review_bundle=bundle),
    )

    assert dossier.dossier_status == "match"
    assert dossier.release_metadata.release_version == "0.1.0"
    assert "adapterManifest" in dossier.release_metadata.artifact_hashes
    assert "adapterTemplateManifest" in dossier.release_metadata.artifact_hashes
    assert "modelGovernanceManifest" in dossier.release_metadata.artifact_hashes
    assert "readinessProfilesManifest" in dossier.release_metadata.artifact_hashes
    assert "regulatoryRulesManifest" in dossier.release_metadata.artifact_hashes
    assert dossier.model_governance_snapshot is not None
    assert dossier.source_governance_snapshot
    assert any(item.role == "walkthrough_payload" for item in dossier.pinned_resources)
    assert any(item.role == "model_governance_manifest" for item in dossier.pinned_resources)

    sanitised = export_sanitised_public_review_dossier(
        ExportSanitisedPublicReviewDossierRequest(dossier=dossier)
    )
    assert sanitised.derived_from_dossier_id == dossier.dossier_id
    assert sanitised.source_workflow == "adapter_review_dossier"
    assert sanitised.legal_limit_reviews == []
    assert sanitised.public_review_bundle.template_name == bundle.template_name
    assert any(item.role == "template_manifest" for item in sanitised.pinned_resources)
    assert not any(item.role == "release_metadata_report" for item in sanitised.pinned_resources)
