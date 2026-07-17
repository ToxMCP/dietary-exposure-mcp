from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.adapter_validation import run_adapter_normalization_cases
from dietary_mcp.adapter_harness import (
    build_external_adapter_summary_from_csv,
    build_external_adapter_summary_from_rows,
    normalize_external_adapter_summary,
)
from dietary_mcp.contaminant_monitoring_bundle_validation import (
    run_contaminant_monitoring_bundle_cases,
)
from dietary_mcp.contaminant_monitoring_signoff_validation import (
    run_contaminant_monitoring_signoff_cases,
)
from dietary_mcp.contaminant_monitoring_review_dossier_validation import (
    run_contaminant_monitoring_review_dossier_cases,
)
from dietary_mcp.integrations import export_pbpk_oral_input, export_toxclaw_dietary_evidence_bundle
from dietary_mcp.food_vocabulary_validation import run_food_vocabulary_cases
from dietary_mcp.contaminant_monitoring_validation import run_contaminant_monitoring_check_cases
from dietary_mcp.interoperability_readiness_validation import run_interoperability_readiness_cases
from dietary_mcp.interoperability_remediation_validation import run_interoperability_remediation_cases
from dietary_mcp.interoperability_signoff_validation import run_interoperability_signoff_cases
from dietary_mcp.interoperability_validation import run_interoperability_preview_cases
from dietary_mcp.metals_monitoring_validation import run_metals_monitoring_bundle_cases
from dietary_mcp.metals_monitoring_review_dossier_validation import (
    run_metals_monitoring_review_dossier_cases,
)
from dietary_mcp.metals_monitoring_signoff_validation import run_metals_monitoring_signoff_cases
from dietary_mcp.models import (
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    BuildBoundedIntakeSummaryRequest,
    DietaryCommodityResidueInput,
    ExportPbpkOralInputRequest,
    ExportToxclawDietaryEvidenceBundleRequest,
    IntakeWindowSemantic,
    ModelFamily,
    ResidueSourceType,
    ScenarioClass,
    SelectConsumptionProfileRequest,
    SourceReference,
)
from dietary_mcp.package_metadata import VERSION
from dietary_mcp.readiness_validation import run_review_dossier_readiness_cases
from dietary_mcp.reference_validation import run_dietary_reference_cases
from dietary_mcp.runtime import get_cached_dietary_runtime
from dietary_mcp.scientific_follow_up_bundle_validation import run_scientific_follow_up_queue_bundle_cases
from dietary_mcp.scientific_follow_up_owner_handoff_validation import (
    run_scientific_follow_up_owner_handoff_cases,
)
from dietary_mcp.scientific_follow_up_owner_remediation_validation import (
    run_scientific_follow_up_owner_remediation_cases,
)
from dietary_mcp.scientific_follow_up_owner_signoff_validation import (
    run_scientific_follow_up_owner_signoff_cases,
)
from dietary_mcp.scientific_follow_up_owner_signoff_dossier_validation import (
    run_scientific_follow_up_owner_signoff_dossier_cases,
)
from dietary_mcp.scientific_follow_up_review_board_validation import run_scientific_follow_up_review_board_cases
from dietary_mcp.sanitisation_validation import run_sanitised_public_review_cases
from dietary_mcp.survey_distribution_summary_validation import run_survey_distribution_summary_cases
from dietary_mcp.probabilistic_intake_summary_validation import run_probabilistic_intake_summary_cases
from dietary_mcp.source_database_validation import run_source_database_cases
from dietary_mcp.uncertainty_validation import (
    run_censored_residue_policy_cases,
    run_health_reference_exceedance_cases,
    run_uncertainty_intake_assessment_cases,
    run_uncertainty_reproducibility_cases,
    run_uncertainty_sensitivity_cases,
)


def run_downstream_dry_runs(repo_root: Path) -> dict:
    runtime = get_cached_dietary_runtime(repo_root)
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Dry run substance", "casrn": "100-00-0"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                    source_reference=SourceReference(
                        source_id="dryrun.apples.monitoring",
                        title="Dry run apples residue",
                        effective_date="2026-04-08",
                    ),
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                    source_reference=SourceReference(
                        source_id="dryrun.milk.curated",
                        title="Dry run milk residue",
                        effective_date="2026-04-08",
                    ),
                ),
            ],
        )
    )
    profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            required_commodity_codes=["apples", "milk"],
        )
    ).profile
    scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=residue_profile.chemical_identity,
            residue_profile=residue_profile,
            consumption_profile=profile,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
        )
    )
    summary = runtime.summarize_intake(BuildBoundedIntakeSummaryRequest(scenario=scenario))
    pbpk_bundle = export_pbpk_oral_input(
        ExportPbpkOralInputRequest(scenario=scenario, summary=summary),
        runtime.provenance,
    )
    toxclaw_bundle = export_toxclaw_dietary_evidence_bundle(
        ExportToxclawDietaryEvidenceBundleRequest(scenario=scenario, summary=summary),
        runtime.provenance,
    )
    adult_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="adult_general",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["apples", "milk"],
        )
    ).profile
    adult_reference_summary = runtime.summarize_intake(
        BuildBoundedIntakeSummaryRequest(
            scenario=runtime.build_dietary_intake_scenario(
                BuildDietaryIntakeScenarioRequest(
                    chemical_identity=residue_profile.chemical_identity,
                    residue_profile=residue_profile,
                    consumption_profile=adult_profile,
                    scenario_class=ScenarioClass.POINT_ESTIMATE,
                    intake_window_semantic=IntakeWindowSemantic.CHRONIC,
                )
            )
        )
    )
    primo_scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=residue_profile.chemical_identity,
            residue_profile=residue_profile,
            consumption_profile=profile,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
        )
    )
    primo_payload = build_external_adapter_summary_from_rows(
        model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
        external_case_id="primo-harness-dry-run",
        external_engine_version="3.1-harness",
        total_intake_mg_per_kg_bw_per_day=summary.total_intake_mg_per_kg_bw_per_day,
        lower_bound_total_intake_mg_per_kg_bw_per_day=summary.lower_bound_total_intake_mg_per_kg_bw_per_day,
        upper_bound_total_intake_mg_per_kg_bw_per_day=summary.upper_bound_total_intake_mg_per_kg_bw_per_day,
        rows=[
            {
                "commodity": "apple"
                if item.commodity.commodity_code == "apples"
                else item.commodity.commodity_code,
                "iesti_mgkgbwday": item.contribution_mg_per_kg_bw_per_day,
                "residue_mgkg": item.residue_concentration_mg_per_kg,
                "consumption_kg_day": item.consumption_kg_per_day,
                "pf": item.applied_processing_factor,
                "lb_mgkgbwday": item.lower_bound_intake_mg_per_kg_bw_per_day,
                "ub_mgkgbwday": item.upper_bound_intake_mg_per_kg_bw_per_day,
            }
            for item in summary.commodity_contributions
        ],
        assumptions_applied=[
            runtime.provenance.derived(
                parameter="adapter_population_label",
                value="PRIMo acute child harness",
                unit=None,
                rationale="Synthetic PRIMo-aligned population label preserved in the dry run.",
            )
        ],
        notes=["Synthetic PRIMo-aligned dry run using aliased commodity codes for normalization testing."],
    )
    primo_summary = normalize_external_adapter_summary(
        primo_payload,
        primo_scenario,
        runtime.defaults,
        runtime.provenance,
    )
    primo_pbpk = export_pbpk_oral_input(
        ExportPbpkOralInputRequest(scenario=primo_scenario, summary=primo_summary),
        runtime.provenance,
    )

    deem_scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=residue_profile.chemical_identity,
            residue_profile=residue_profile,
            consumption_profile=adult_profile,
            scenario_class=ScenarioClass.POINT_ESTIMATE,
            intake_window_semantic=IntakeWindowSemantic.CHRONIC,
            model_family=ModelFamily.EPA_DEEM_ADAPTER,
        )
    )
    deem_rows = ["food,exposure_mg_per_kg_bw_per_day,stmr_mgkg,food_consumption_kg_per_day,processing_factor"]
    for item in adult_reference_summary.commodity_contributions:
        deem_rows.append(
            ",".join(
                [
                    "apples_raw"
                    if item.commodity.commodity_code == "apples"
                    else "cow_milk"
                    if item.commodity.commodity_code == "milk"
                    else item.commodity.commodity_code,
                    str(item.contribution_mg_per_kg_bw_per_day),
                    str(item.residue_concentration_mg_per_kg),
                    str(item.consumption_kg_per_day),
                    str(item.applied_processing_factor),
                ]
            )
        )
    deem_payload = build_external_adapter_summary_from_csv(
        model_family=ModelFamily.EPA_DEEM_ADAPTER,
        external_case_id="deem-harness-dry-run",
        external_engine_version="4.02-harness",
        total_intake_mg_per_kg_bw_per_day=adult_reference_summary.total_intake_mg_per_kg_bw_per_day,
        csv_text="\n".join(deem_rows),
        assumptions_applied=[
            runtime.provenance.derived(
                parameter="adapter_population_label",
                value="DEEM chronic adult harness",
                unit=None,
                rationale="Synthetic DEEM-aligned population label preserved in the dry run.",
            )
        ],
        notes=["Synthetic DEEM-aligned dry run using NHANES-style alias placeholders for normalization testing."],
    )
    deem_summary = normalize_external_adapter_summary(
        deem_payload,
        deem_scenario,
        runtime.defaults,
        runtime.provenance,
    )
    deem_pbpk = export_pbpk_oral_input(
        ExportPbpkOralInputRequest(scenario=deem_scenario, summary=deem_summary),
        runtime.provenance,
    )
    return {
        "version": VERSION,
        "status": "pass",
        "pbpkDryRun": {
            "status": "pass",
            "route": pbpk_bundle.route_dose_estimate.route.value,
            "doseMetric": pbpk_bundle.route_dose_estimate.dose_metric,
            "schedule": pbpk_bundle.dosing_regimen.schedule,
            "dependencyCount": len(pbpk_bundle.dependencies),
        },
        "toxclawDryRun": {
            "status": "pass",
            "bundleId": toxclaw_bundle.bundle_id,
            "assumptionCount": len(toxclaw_bundle.assumptions),
            "evidenceItemCount": len(toxclaw_bundle.evidence_items),
        },
        "adapterDryRuns": {
            "efsaPrimoHarness": {
                "status": "pass",
                "scenarioId": primo_summary.scenario_id,
                "modelFamily": primo_scenario.model_family.value,
                "dependencyCount": len(primo_pbpk.dependencies),
                "qualityFlagCount": len(primo_summary.quality_flags),
            },
            "epaDeemHarness": {
                "status": "pass",
                "scenarioId": deem_summary.scenario_id,
                "modelFamily": deem_scenario.model_family.value,
                "dependencyCount": len(deem_pbpk.dependencies),
                "qualityFlagCount": len(deem_summary.quality_flags),
            },
        },
        "scenarioId": summary.scenario_id,
        "notes": [
            "Dry runs reuse public dietary contracts without ad hoc field mapping.",
            "PBPK handoff exports oral external dose semantics only.",
            "ToxClaw bundle preserves scenario, summary, route dose, assumptions, and evidence references.",
            "Adapter dry runs normalize synthetic PRIMo- and DEEM-shaped outputs into the same contracts.",
        ],
    }


def build_validation_dossier(repo_root: Path) -> dict:
    benchmark_cases = json.loads((repo_root / "validation" / "v1" / "benchmark_cases.json").read_text())
    reference_cases = json.loads((repo_root / "validation" / "v1" / "dietary_reference_cases.json").read_text())
    gap_report = json.loads((repo_root / "validation" / "v1" / "commodity_mapping_gap_report.json").read_text())
    adapter_cases = json.loads((repo_root / "validation" / "v1" / "adapter_normalization_cases.json").read_text())
    food_vocabulary_cases = json.loads((repo_root / "validation" / "v1" / "food_vocabulary_cases.json").read_text())
    source_database_cases = json.loads((repo_root / "validation" / "v1" / "source_database_cases.json").read_text())
    contaminant_monitoring_cases = json.loads(
        (repo_root / "validation" / "v1" / "contaminant_monitoring_check_cases.json").read_text()
    )
    contaminant_monitoring_bundle_cases = json.loads(
        (repo_root / "validation" / "v1" / "contaminant_monitoring_bundle_cases.json").read_text()
    )
    contaminant_monitoring_signoff_cases = json.loads(
        (repo_root / "validation" / "v1" / "contaminant_monitoring_signoff_cases.json").read_text()
    )
    contaminant_monitoring_review_dossier_cases = json.loads(
        (repo_root / "validation" / "v1" / "contaminant_monitoring_review_dossier_cases.json").read_text()
    )
    interoperability_cases = json.loads((repo_root / "validation" / "v1" / "interoperability_preview_cases.json").read_text())
    interoperability_readiness_cases = json.loads(
        (repo_root / "validation" / "v1" / "interoperability_readiness_cases.json").read_text()
    )
    interoperability_remediation_cases = json.loads(
        (repo_root / "validation" / "v1" / "interoperability_remediation_cases.json").read_text()
    )
    interoperability_signoff_cases = json.loads(
        (repo_root / "validation" / "v1" / "interoperability_signoff_cases.json").read_text()
    )
    readiness_cases = json.loads((repo_root / "validation" / "v1" / "review_dossier_readiness_cases.json").read_text())
    scientific_follow_up_bundle_cases = json.loads(
        (repo_root / "validation" / "v1" / "scientific_follow_up_queue_bundle_cases.json").read_text()
    )
    scientific_follow_up_review_board_cases = json.loads(
        (repo_root / "validation" / "v1" / "scientific_follow_up_review_board_cases.json").read_text()
    )
    scientific_follow_up_owner_handoff_cases = json.loads(
        (repo_root / "validation" / "v1" / "scientific_follow_up_owner_handoff_cases.json").read_text()
    )
    scientific_follow_up_owner_remediation_cases = json.loads(
        (repo_root / "validation" / "v1" / "scientific_follow_up_owner_remediation_cases.json").read_text()
    )
    scientific_follow_up_owner_signoff_cases = json.loads(
        (repo_root / "validation" / "v1" / "scientific_follow_up_owner_signoff_cases.json").read_text()
    )
    scientific_follow_up_owner_signoff_dossier_cases = json.loads(
        (repo_root / "validation" / "v1" / "scientific_follow_up_owner_signoff_dossier_cases.json").read_text()
    )
    sanitised_cases = json.loads((repo_root / "validation" / "v1" / "sanitised_public_review_cases.json").read_text())
    survey_distribution_summary_cases = json.loads(
        (repo_root / "validation" / "v1" / "survey_distribution_summary_cases.json").read_text()
    )
    probabilistic_intake_summary_cases = json.loads(
        (repo_root / "validation" / "v1" / "probabilistic_intake_summary_cases.json").read_text()
    )
    uncertainty_intake_assessment_cases = json.loads(
        (repo_root / "validation" / "v1" / "uncertainty_intake_assessment_cases.json").read_text()
    )
    censored_residue_policy_cases = json.loads(
        (repo_root / "validation" / "v1" / "censored_residue_policy_cases.json").read_text()
    )
    uncertainty_sensitivity_cases = json.loads(
        (repo_root / "validation" / "v1" / "uncertainty_sensitivity_cases.json").read_text()
    )
    health_reference_exceedance_cases = json.loads(
        (repo_root / "validation" / "v1" / "health_reference_exceedance_cases.json").read_text()
    )
    uncertainty_reproducibility_cases = json.loads(
        (repo_root / "validation" / "v1" / "uncertainty_reproducibility_cases.json").read_text()
    )

    reference_results = run_dietary_reference_cases(repo_root)
    adapter_results = run_adapter_normalization_cases(repo_root)
    food_vocabulary_results = run_food_vocabulary_cases(repo_root)
    source_database_results = run_source_database_cases(repo_root)
    contaminant_monitoring_results = run_contaminant_monitoring_check_cases(repo_root)
    contaminant_monitoring_bundle_results = run_contaminant_monitoring_bundle_cases(repo_root)
    contaminant_monitoring_signoff_results = run_contaminant_monitoring_signoff_cases(repo_root)
    contaminant_monitoring_review_dossier_results = run_contaminant_monitoring_review_dossier_cases(repo_root)
    metals_monitoring_cases = json.loads(
        (repo_root / "validation" / "v1" / "metals_monitoring_bundle_cases.json").read_text()
    )
    metals_monitoring_results = run_metals_monitoring_bundle_cases(repo_root)
    metals_monitoring_signoff_cases = json.loads(
        (repo_root / "validation" / "v1" / "metals_monitoring_signoff_cases.json").read_text()
    )
    metals_monitoring_signoff_results = run_metals_monitoring_signoff_cases(repo_root)
    metals_monitoring_review_dossier_cases = json.loads(
        (repo_root / "validation" / "v1" / "metals_monitoring_review_dossier_cases.json").read_text()
    )
    metals_monitoring_review_dossier_results = run_metals_monitoring_review_dossier_cases(repo_root)
    interoperability_results = run_interoperability_preview_cases(repo_root)
    interoperability_readiness_results = run_interoperability_readiness_cases(repo_root)
    interoperability_remediation_results = run_interoperability_remediation_cases(repo_root)
    interoperability_signoff_results = run_interoperability_signoff_cases(repo_root)
    readiness_results = run_review_dossier_readiness_cases(repo_root)
    scientific_follow_up_bundle_results = run_scientific_follow_up_queue_bundle_cases(repo_root)
    scientific_follow_up_review_board_results = run_scientific_follow_up_review_board_cases(repo_root)
    scientific_follow_up_owner_handoff_results = run_scientific_follow_up_owner_handoff_cases(repo_root)
    scientific_follow_up_owner_remediation_results = run_scientific_follow_up_owner_remediation_cases(repo_root)
    scientific_follow_up_owner_signoff_results = run_scientific_follow_up_owner_signoff_cases(repo_root)
    scientific_follow_up_owner_signoff_dossier_results = run_scientific_follow_up_owner_signoff_dossier_cases(
        repo_root
    )
    sanitised_results = run_sanitised_public_review_cases(repo_root)
    survey_distribution_summary_results = run_survey_distribution_summary_cases(repo_root)
    probabilistic_intake_summary_results = run_probabilistic_intake_summary_cases(repo_root)
    uncertainty_intake_assessment_results = run_uncertainty_intake_assessment_cases(repo_root)
    censored_residue_policy_results = run_censored_residue_policy_cases(repo_root)
    uncertainty_sensitivity_results = run_uncertainty_sensitivity_cases(repo_root)
    health_reference_exceedance_results = run_health_reference_exceedance_cases(repo_root)
    uncertainty_reproducibility_results = run_uncertainty_reproducibility_cases(repo_root)
    return {
        "version": VERSION,
        "status": "draft_ready",
        "benchmarkCaseCount": len(benchmark_cases["cases"]),
        "referenceCaseCount": len(reference_cases["cases"]),
        "referenceCaseStatus": reference_results["status"],
        "mappingGapCount": len(gap_report["gaps"]),
        "adapterNormalizationCaseCount": len(adapter_cases["cases"]),
        "adapterNormalizationStatus": adapter_results["status"],
        "foodVocabularyCaseCount": len(food_vocabulary_cases["cases"]),
        "foodVocabularyStatus": food_vocabulary_results["status"],
        "sourceDatabaseCaseCount": len(source_database_cases["cases"]),
        "sourceDatabaseStatus": source_database_results["status"],
        "contaminantMonitoringCheckCaseCount": len(contaminant_monitoring_cases["cases"]),
        "contaminantMonitoringCheckStatus": contaminant_monitoring_results["status"],
        "contaminantMonitoringBundleCaseCount": len(contaminant_monitoring_bundle_cases["cases"]),
        "contaminantMonitoringBundleStatus": contaminant_monitoring_bundle_results["status"],
        "contaminantMonitoringSignoffCaseCount": len(contaminant_monitoring_signoff_cases["cases"]),
        "contaminantMonitoringSignoffStatus": contaminant_monitoring_signoff_results["status"],
        "contaminantMonitoringReviewDossierCaseCount": len(contaminant_monitoring_review_dossier_cases["cases"]),
        "contaminantMonitoringReviewDossierStatus": contaminant_monitoring_review_dossier_results["status"],
        "metalsMonitoringBundleCaseCount": len(metals_monitoring_cases["cases"]),
        "metalsMonitoringBundleStatus": metals_monitoring_results["status"],
        "metalsMonitoringSignoffCaseCount": len(metals_monitoring_signoff_cases["cases"]),
        "metalsMonitoringSignoffStatus": metals_monitoring_signoff_results["status"],
        "metalsMonitoringReviewDossierCaseCount": len(metals_monitoring_review_dossier_cases["cases"]),
        "metalsMonitoringReviewDossierStatus": metals_monitoring_review_dossier_results["status"],
        "interoperabilityPreviewCaseCount": len(interoperability_cases["cases"]),
        "interoperabilityPreviewStatus": interoperability_results["status"],
        "interoperabilityReadinessCaseCount": len(interoperability_readiness_cases["cases"]),
        "interoperabilityReadinessStatus": interoperability_readiness_results["status"],
        "interoperabilityRemediationCaseCount": len(interoperability_remediation_cases["cases"]),
        "interoperabilityRemediationStatus": interoperability_remediation_results["status"],
        "interoperabilitySignoffCaseCount": len(interoperability_signoff_cases["cases"]),
        "interoperabilitySignoffStatus": interoperability_signoff_results["status"],
        "reviewDossierReadinessCaseCount": len(readiness_cases["cases"]),
        "reviewDossierReadinessStatus": readiness_results["status"],
        "scientificFollowUpQueueBundleCaseCount": len(scientific_follow_up_bundle_cases["cases"]),
        "scientificFollowUpQueueBundleStatus": scientific_follow_up_bundle_results["status"],
        "scientificFollowUpReviewBoardCaseCount": len(scientific_follow_up_review_board_cases["cases"]),
        "scientificFollowUpReviewBoardStatus": scientific_follow_up_review_board_results["status"],
        "scientificFollowUpOwnerHandoffCaseCount": len(scientific_follow_up_owner_handoff_cases["cases"]),
        "scientificFollowUpOwnerHandoffStatus": scientific_follow_up_owner_handoff_results["status"],
        "scientificFollowUpOwnerRemediationCaseCount": len(
            scientific_follow_up_owner_remediation_cases["cases"]
        ),
        "scientificFollowUpOwnerRemediationStatus": scientific_follow_up_owner_remediation_results["status"],
        "scientificFollowUpOwnerSignoffCaseCount": len(scientific_follow_up_owner_signoff_cases["cases"]),
        "scientificFollowUpOwnerSignoffStatus": scientific_follow_up_owner_signoff_results["status"],
        "scientificFollowUpOwnerSignoffDossierCaseCount": len(
            scientific_follow_up_owner_signoff_dossier_cases["cases"]
        ),
        "scientificFollowUpOwnerSignoffDossierStatus": scientific_follow_up_owner_signoff_dossier_results[
            "status"
        ],
        "sanitisedPublicReviewCaseCount": len(sanitised_cases["cases"]),
        "sanitisedPublicReviewStatus": sanitised_results["status"],
        "surveyDistributionSummaryCaseCount": len(survey_distribution_summary_cases["cases"]),
        "surveyDistributionSummaryStatus": survey_distribution_summary_results["status"],
        "probabilisticIntakeSummaryCaseCount": len(probabilistic_intake_summary_cases["cases"]),
        "probabilisticIntakeSummaryStatus": probabilistic_intake_summary_results["status"],
        "uncertaintyIntakeAssessmentCaseCount": len(uncertainty_intake_assessment_cases["cases"]),
        "uncertaintyIntakeAssessmentStatus": uncertainty_intake_assessment_results["status"],
        "censoredResiduePolicyCaseCount": len(censored_residue_policy_cases["cases"]),
        "censoredResiduePolicyStatus": censored_residue_policy_results["status"],
        "uncertaintySensitivityCaseCount": len(uncertainty_sensitivity_cases["cases"]),
        "uncertaintySensitivityStatus": uncertainty_sensitivity_results["status"],
        "healthReferenceExceedanceCaseCount": len(health_reference_exceedance_cases["cases"]),
        "healthReferenceExceedanceStatus": health_reference_exceedance_results["status"],
        "uncertaintyReproducibilityCaseCount": len(uncertainty_reproducibility_cases["cases"]),
        "uncertaintyReproducibilityStatus": uncertainty_reproducibility_results["status"],
        "populationCoverage": sorted({case["populationGroup"] for case in reference_cases["cases"]}),
        "documents": [
            "validation/v1/benchmark_cases.json",
            "validation/v1/dietary_reference_cases.json",
            "validation/v1/commodity_mapping_gap_report.json",
            "validation/v1/adapter_normalization_cases.json",
            "validation/v1/food_vocabulary_cases.json",
            "validation/v1/source_database_cases.json",
            "validation/v1/contaminant_monitoring_check_cases.json",
            "validation/v1/contaminant_monitoring_bundle_cases.json",
            "validation/v1/contaminant_monitoring_signoff_cases.json",
            "validation/v1/contaminant_monitoring_review_dossier_cases.json",
            "validation/v1/metals_monitoring_bundle_cases.json",
            "validation/v1/metals_monitoring_signoff_cases.json",
            "validation/v1/metals_monitoring_review_dossier_cases.json",
            "validation/v1/regulatory_rules.json",
            "validation/v1/interoperability_profiles.json",
            "validation/v1/interoperability_preview_cases.json",
            "validation/v1/interoperability_readiness_profiles.json",
            "validation/v1/interoperability_rules.json",
            "validation/v1/interoperability_readiness_cases.json",
            "validation/v1/interoperability_remediation_actions.json",
            "validation/v1/interoperability_remediation_cases.json",
            "validation/v1/interoperability_signoff_cases.json",
            "validation/v1/sanitisation_rules.json",
            "validation/v1/review_dossier_readiness_cases.json",
            "validation/v1/scientific_follow_up_queue_bundle_cases.json",
            "validation/v1/scientific_follow_up_review_board_cases.json",
            "validation/v1/scientific_follow_up_owner_handoff_cases.json",
            "validation/v1/scientific_follow_up_owner_remediation_cases.json",
            "validation/v1/scientific_follow_up_owner_signoff_cases.json",
            "validation/v1/scientific_follow_up_owner_signoff_dossier_cases.json",
            "validation/v1/sanitised_public_review_cases.json",
            "validation/v1/survey_distribution_summary_cases.json",
            "validation/v1/probabilistic_intake_summary_cases.json",
            "validation/v1/uncertainty_intake_assessment_cases.json",
            "validation/v1/censored_residue_policy_cases.json",
            "validation/v1/uncertainty_sensitivity_cases.json",
            "validation/v1/health_reference_exceedance_cases.json",
            "validation/v1/uncertainty_reproducibility_cases.json",
            "docs/validation_framework.md",
        ],
    }
