from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.integrations import (
    compare_dietary_scenarios,
    export_pbpk_oral_input,
    export_toxclaw_dietary_evidence_bundle,
)
from dietary_mcp.errors import DietaryErrorPayload
from dietary_mcp.models import (
    AssessInteroperabilityPreviewReadinessRequest,
    AssessReviewDossierReadinessRequest,
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    BuildBoundedIntakeSummaryRequest,
    BuildProbabilisticIntakeSummaryRequest,
    BuildUncertaintyIntakeAssessmentRequest,
    CheckAdapterImportRequest,
    CheckContaminantMonitoringImportRequest,
    CompareAdapterImportToWalkthroughRequest,
    CompareDietaryScenariosRequest,
    ContaminantFamily,
    DietaryCommodityResidueInput,
    EvaluateGlobalTradeRiskRequest,
    ExportContaminantMonitoringSignoffPacketRequest,
    ExportAdapterReviewBundleRequest,
    ExportTradeRiskReviewBundleRequest,
    ExportContaminantMonitoringInterpretationBundleRequest,
    ExportVersionPinnedContaminantMonitoringReviewDossierRequest,
    ExportVersionPinnedTradeRiskReviewDossierRequest,
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
    ExportPbpkOralInputRequest,
    ExportToxclawDietaryEvidenceBundleRequest,
    IntakeWindowSemantic,
    InteroperabilityActionDecisionStatus,
    InteroperabilitySignoffDecisionInput,
    LookupAnalyticalMethodEvidenceRequest,
    LookupContaminantLegalLimitsRequest,
    LookupConsumptionDatasetSupportRequest,
    LookupOccurrenceEvidenceRequest,
    LookupReportingProfilesRequest,
    LookupMetalsOccurrenceRequest,
    LookupMetalsReviewFocusRequest,
    LookupMethodSupportRequest,
    LookupReferenceValuesRequest,
    LimitationNote,
    EmergingContaminantRecord,
    ParseRawSurveyDatasetRequest,
    ModelGovernanceRecord,
    ModelFamily,
    ConfidentialityTag,
    PinnedResourceFingerprint,
    ReleaseMetadataSnapshot,
    RawSurveyRecordInput,
    ResidueUncertaintyModel,
    ResidueSourceType,
    ScenarioClass,
    SelectConsumptionProfileRequest,
    SanitisationState,
    SanitisedPublicReviewDossier,
    SourceReference,
    SummarizeSurveyDistributionRequest,
    VersionPinnedContaminantMonitoringReviewDossier,
    ContaminantLegalLimitLookupResult,
    VersionPinnedAdapterReviewDossier,
    VersionPinnedMetalsMonitoringReviewDossier,
)
from dietary_mcp.package_metadata import VERSION
from dietary_mcp.readiness import collect_source_governance_snapshot
from dietary_mcp.runtime import DietaryRuntime


_VOLATILE_EXAMPLE_KEYS = frozenset({"generated_at", "generatedAt", "executed_at", "executedAt"})


def _preserve_volatile_example_values(generated: object, existing: object) -> object:
    """Keep checked-in timestamps stable while regenerating semantic example content."""
    if isinstance(generated, dict) and isinstance(existing, dict):
        return {
            key: (
                existing[key]
                if key in _VOLATILE_EXAMPLE_KEYS and key in existing
                else _preserve_volatile_example_values(value, existing.get(key))
            )
            for key, value in generated.items()
        }
    if isinstance(generated, list) and isinstance(existing, list):
        return [
            _preserve_volatile_example_values(value, existing[index] if index < len(existing) else None)
            for index, value in enumerate(generated)
        ]
    return generated


def build_examples(runtime: DietaryRuntime) -> dict[str, dict]:
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Illustrative residue", "casrn": "100-00-0"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apple",
                    residue_concentration_mg_per_kg=0.15,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.2,
                    source_type=ResidueSourceType.MONITORING,
                    source_reference=SourceReference(
                        source_id="example.apple.monitoring",
                        title="Illustrative apple monitoring record",
                        effective_date="2026-04-08",
                    ),
                ),
                DietaryCommodityResidueInput(
                    commodity_code="spinach",
                    residue_concentration_mg_per_kg=0.05,
                    lower_bound_mg_per_kg=0.03,
                    upper_bound_mg_per_kg=0.08,
                    source_type=ResidueSourceType.MODELED,
                    processing_factor=0.85,
                    source_reference=SourceReference(
                        source_id="example.spinach.modeled",
                        title="Illustrative spinach modeled record",
                        effective_date="2026-04-08",
                    ),
                ),
                DietaryCommodityResidueInput(
                    commodity_code="rice",
                    residue_concentration_mg_per_kg=0.02,
                    source_type=ResidueSourceType.USER_SUPPLIED,
                    source_reference=SourceReference(
                        source_id="example.rice.user",
                        title="Illustrative rice residue input",
                        effective_date="2026-04-08",
                    ),
                ),
            ],
        )
    )

    parse_survey_request = ParseRawSurveyDatasetRequest(
        dataset_id="example_governed_survey",
        region_id="eu_screening_default",
        population_group="adult_general",
        raw_records=[
            RawSurveyRecordInput(
                subject_id="adult-001",
                body_weight_kg=70.0,
                days_in_survey=2,
                commodity_code="apples",
                consumption_kg_per_day=0.35,
            ),
            RawSurveyRecordInput(
                subject_id="adult-002",
                body_weight_kg=64.0,
                days_in_survey=2,
                commodity_code="spinach",
                consumption_kg_per_day=0.08,
            ),
            RawSurveyRecordInput(
                subject_id="adult-003",
                body_weight_kg=82.0,
                days_in_survey=1,
                commodity_code="rice",
                consumption_kg_per_day=0.18,
            ),
            RawSurveyRecordInput(
                subject_id="adult-004",
                body_weight_kg=76.0,
                days_in_survey=2,
                commodity_code="apples",
                consumption_kg_per_day=0.0,
            ),
        ],
    )
    survey_dataset = runtime.parse_raw_survey_dataset(parse_survey_request)
    survey_distribution_request = SummarizeSurveyDistributionRequest(
        dataset=survey_dataset,
        residue_profile=residue_profile,
    )
    survey_distribution_summary = runtime.summarize_survey_distribution(survey_distribution_request)
    probabilistic_request = BuildProbabilisticIntakeSummaryRequest(
        dataset=survey_dataset,
        residue_profile=residue_profile,
        iteration_count=1000,
        random_seed=20260424,
    )
    probabilistic_summary = runtime.build_probabilistic_intake_summary(probabilistic_request)
    uncertainty_request = BuildUncertaintyIntakeAssessmentRequest(
        dataset=survey_dataset,
        residue_profile=residue_profile,
        random_seed=20260424,
        outer_iteration_count=50,
        inner_iteration_count=200,
        residue_uncertainty_models=[
            ResidueUncertaintyModel(
                commodity_code="apples",
                distribution="uniform",
                min_mg_per_kg=0.12,
                max_mg_per_kg=0.2,
                processing_factor_cv=0.05,
            ),
            ResidueUncertaintyModel(
                commodity_code="spinach",
                distribution="triangular",
                min_mg_per_kg=0.03,
                mode_mg_per_kg=0.05,
                max_mg_per_kg=0.08,
            ),
            ResidueUncertaintyModel(
                commodity_code="rice",
                distribution="point",
                point_mg_per_kg=0.02,
            ),
        ],
        health_reference={
            "referenceType": "ADI",
            "value": 0.01,
            "unit": "mg/kg bw/day",
            "sourceId": "example.reference.adi",
        },
    )
    uncertainty_assessment = runtime.build_uncertainty_intake_assessment(uncertainty_request)

    chronic_selection = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="adult_general",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["apples", "spinach", "rice"],
        )
    )
    acute_selection = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            required_commodity_codes=["apples", "spinach", "rice"],
        )
    )

    point_scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=residue_profile.chemical_identity,
            residue_profile=residue_profile,
            consumption_profile=chronic_selection.profile,
            scenario_class=ScenarioClass.POINT_ESTIMATE,
            intake_window_semantic=IntakeWindowSemantic.CHRONIC,
        )
    )
    bounded_scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=residue_profile.chemical_identity,
            residue_profile=residue_profile,
            consumption_profile=acute_selection.profile,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
        )
    )

    point_summary = runtime.summarize_intake(BuildBoundedIntakeSummaryRequest(scenario=point_scenario))
    bounded_summary = runtime.summarize_intake(BuildBoundedIntakeSummaryRequest(scenario=bounded_scenario))
    comparison = compare_dietary_scenarios(
        CompareDietaryScenariosRequest(
            base_summary=point_summary,
            candidate_summary=bounded_summary,
        ),
        runtime.provenance,
    )
    pbpk_bundle = export_pbpk_oral_input(
        ExportPbpkOralInputRequest(scenario=bounded_scenario, summary=bounded_summary),
        runtime.provenance,
    )
    toxclaw_bundle = export_toxclaw_dietary_evidence_bundle(
        ExportToxclawDietaryEvidenceBundleRequest(scenario=bounded_scenario, summary=bounded_summary),
        runtime.provenance,
    )
    adapter_check_request = CheckAdapterImportRequest(
        model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
        population_group="child_1_6",
        intake_window=IntakeWindowSemantic.ACUTE,
        scenario_class=ScenarioClass.BOUNDED_ACUTE,
        chemical_identity={"preferredName": "Illustrative residue", "casrn": "100-00-0"},
        residue_records=[
            DietaryCommodityResidueInput(
                commodity_code="apples",
                residue_concentration_mg_per_kg=0.18,
                lower_bound_mg_per_kg=0.12,
                upper_bound_mg_per_kg=0.24,
                source_type=ResidueSourceType.MONITORING,
                source_reference=SourceReference(
                    source_id="example.adapter.apples.monitoring",
                    title="Illustrative adapter apples residue input",
                    effective_date="2026-04-08",
                ),
            ),
            DietaryCommodityResidueInput(
                commodity_code="milk",
                residue_concentration_mg_per_kg=0.03,
                source_type=ResidueSourceType.CURATED_DEFAULT,
                source_reference=SourceReference(
                    source_id="example.adapter.milk.default",
                    title="Illustrative adapter milk residue input",
                    effective_date="2026-04-08",
                ),
            ),
        ],
        external_engine_version="3.1-harness",
        external_case_id="example-primo-check",
        declared_total_intake_mg_per_kg_bw_per_day=0.00416,
        declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
        declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
        csv_text=(
            "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
            "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
            "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
        ),
    )
    adapter_check_result = runtime.check_adapter_import(adapter_check_request)
    adapter_compare_request = CompareAdapterImportToWalkthroughRequest(
        check_result=adapter_check_result,
        walkthrough_name="efsa_primo_tabular_alias_case",
    )
    adapter_compare_result = runtime.compare_adapter_import_to_walkthrough(adapter_compare_request)
    adapter_review_bundle_request = ExportAdapterReviewBundleRequest(
        check_result=adapter_check_result,
        comparison_result=adapter_compare_result,
    )
    adapter_review_bundle = runtime.export_adapter_review_bundle(adapter_review_bundle_request)
    adapter_review_dossier_request = ExportVersionPinnedAdapterReviewDossierRequest(
        review_bundle=adapter_review_bundle,
    )
    example_model_governance = ModelGovernanceRecord.model_validate(
        runtime.defaults.get_model_governance_record(ModelFamily.EFSA_PRIMO_ADAPTER.value)
    )
    example_source_governance = collect_source_governance_snapshot(
        runtime.defaults,
        adapter_check_result.normalized_projection.source_ids + example_model_governance.source_ids,
    )
    adapter_review_dossier = VersionPinnedAdapterReviewDossier(
        dossier_status=adapter_review_bundle.review_status,
        review_bundle=adapter_review_bundle,
        release_metadata=ReleaseMetadataSnapshot(
            resource_uri="release://metadata-report",
            release_version=VERSION,
            defaults_version=runtime.defaults.build_manifest()["defaultsVersion"],
            metadata_report_sha256="example-release-metadata-sha256",
            artifact_hashes={
                "adapterManifest": "example-adapter-manifest-sha256",
                "adapterTemplateManifest": "example-template-manifest-sha256",
                "adapterWalkthroughManifest": "example-walkthrough-manifest-sha256",
                "modelGovernanceManifest": "example-model-governance-manifest-sha256",
                "foodVocabularyCrosswalkManifest": "example-food-vocabulary-manifest-sha256",
                "interoperabilityProfilesManifest": "example-interoperability-profiles-manifest-sha256",
                "interoperabilityReadinessProfilesManifest": "example-interoperability-readiness-profiles-manifest-sha256",
                "interoperabilityRulesManifest": "example-interoperability-rules-manifest-sha256",
                "interoperabilityRemediationActionsManifest": "example-interoperability-remediation-actions-manifest-sha256",
                "readinessProfilesManifest": "example-readiness-profiles-manifest-sha256",
                "regulatoryRulesManifest": "example-regulatory-rules-manifest-sha256",
                "sanitisationRulesManifest": "example-sanitisation-rules-manifest-sha256",
            },
        ),
        source_governance_snapshot=example_source_governance,
        model_governance_snapshot=example_model_governance,
        pinned_resources=[
            PinnedResourceFingerprint(
                role="release_metadata_report",
                uri="release://metadata-report",
                sha256="example-release-metadata-sha256",
                description="Illustrative release metadata report fingerprint.",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                sanitisation_state=SanitisationState.RETAINED,
            ),
            PinnedResourceFingerprint(
                role="template_manifest",
                uri="adapter-input-templates://manifest",
                sha256="example-template-manifest-sha256",
                description="Illustrative template manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="template_payload",
                uri="adapter-template://efsa_primo_tabular_template",
                sha256="example-template-payload-sha256",
                description="Illustrative template payload fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="walkthrough_manifest",
                uri="adapter-import-walkthroughs://manifest",
                sha256="example-walkthrough-manifest-sha256",
                description="Illustrative walkthrough manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="walkthrough_payload",
                uri="adapter-walkthrough://efsa_primo_tabular_alias_case",
                sha256="example-walkthrough-payload-sha256",
                description="Illustrative walkthrough payload fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="source_catalog_manifest",
                uri="source-catalog://manifest",
                sha256="example-source-catalog-manifest-sha256",
                description="Illustrative source catalog manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="model_governance_manifest",
                uri="model-governance://manifest",
                sha256="example-model-governance-manifest-sha256",
                description="Illustrative model governance manifest fingerprint.",
            ),
        ],
        confidentiality_annotations=adapter_review_bundle.confidentiality_annotations
        + [
            {
                "targetPath": "pinned_resources.release_metadata_report",
                "targetKind": "resource",
                "confidentialityTag": "confidential",
                "rationale": "Illustrative public dossier export removes the full release metadata report resource.",
            }
        ],
        limitations=[
            LimitationNote(
                code="version_pinned_not_signed",
                message="Illustrative dossier example uses placeholder hashes and is not cryptographically signed.",
            )
        ],
        notes=[
            "Example dossier shows the version-pinned export shape without requiring live release-report generation during artifact writing.",
            "This dossier supports internal review or consultation-oriented exploration only and is not a submission-capable regulatory package in v0.1.",
            "No claim of official PRIMo engine equivalence, proprietary dataset reproduction, or regulatory endorsement is implied.",
            "EFSA PRIMo adapter outputs are for internal review or consultation-oriented compatibility checks only.",
        ],
    )
    adapter_readiness_request = AssessReviewDossierReadinessRequest(
        dossier=adapter_review_dossier,
        target_profile="eu_internal_review",
    )
    adapter_readiness_result = runtime.assess_review_dossier_readiness(adapter_readiness_request)
    reference_value_lookup_request = LookupReferenceValuesRequest(
        substance_key="glyphosate",
        contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
    )
    reference_value_lookup_result = runtime.lookup_reference_values(reference_value_lookup_request)
    trade_risk_request = EvaluateGlobalTradeRiskRequest(
        chemical_identity={"preferredName": "glyphosate"},
        residue_records=[
            DietaryCommodityResidueInput(
                commodity_code="grapes",
                residue_concentration_mg_per_kg=0.2,
                source_type=ResidueSourceType.MONITORING,
                source_reference=SourceReference(
                    source_id="example.trade.grapes.monitoring",
                    title="Illustrative trade-risk grapes residue input",
                    effective_date="2026-04-21",
                ),
            )
        ],
        target_jurisdictions=["us", "codex_global", "cn"],
    )
    trade_risk_report = runtime.evaluate_global_trade_risk(trade_risk_request)
    trade_risk_review_bundle_request = ExportTradeRiskReviewBundleRequest(
        trade_report=trade_risk_report,
        bundle_note="Illustrative governed trade-risk review bundle for cross-jurisdiction residue screening.",
    )
    trade_risk_review_bundle = runtime.export_trade_risk_review_bundle(trade_risk_review_bundle_request)
    trade_risk_review_dossier_request = ExportVersionPinnedTradeRiskReviewDossierRequest(
        review_bundle=trade_risk_review_bundle,
    )
    trade_risk_review_dossier = runtime.export_version_pinned_trade_risk_review_dossier(
        trade_risk_review_dossier_request
    )
    contaminant_legal_limit_lookup_request = LookupContaminantLegalLimitsRequest(
        contaminant_family=ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
        jurisdiction="cn",
        substance_key="inorganic_arsenic",
        commodity_code="rice",
    )
    contaminant_legal_limit_lookup_result = ContaminantLegalLimitLookupResult.model_validate(
        runtime.lookup_contaminant_legal_limits(contaminant_legal_limit_lookup_request)
    )
    method_support_lookup_request = LookupMethodSupportRequest(
        contaminant_family=ContaminantFamily.MICROPLASTICS_EMERGING,
        jurisdiction="eu",
    )
    method_support_lookup_result = runtime.lookup_method_support(method_support_lookup_request)
    dataset_support_lookup_request = LookupConsumptionDatasetSupportRequest(
        jurisdiction="eu",
        contaminant_family=ContaminantFamily.PESTICIDE_RESIDUE,
    )
    dataset_support_lookup_result = runtime.lookup_consumption_dataset_support(dataset_support_lookup_request)
    reporting_profile_lookup_request = LookupReportingProfilesRequest(
        contaminant_family=ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
        matrix_group="eggs",
    )
    reporting_profile_lookup_result = runtime.lookup_reporting_profiles(reporting_profile_lookup_request)
    occurrence_evidence_lookup_request = LookupOccurrenceEvidenceRequest(
        contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        jurisdiction="eu",
        analyte="methylmercury",
        matrix_group="fish",
    )
    occurrence_evidence_lookup_result = runtime.lookup_occurrence_evidence(occurrence_evidence_lookup_request)
    analytical_method_evidence_lookup_request = LookupAnalyticalMethodEvidenceRequest(
        contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        jurisdiction="eu",
        analyte="methylmercury",
    )
    analytical_method_evidence_lookup_result = runtime.lookup_analytical_method_evidence(
        analytical_method_evidence_lookup_request
    )
    contaminant_monitoring_check_request = CheckContaminantMonitoringImportRequest(
        contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        jurisdiction="eu",
        dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
        csv_text=(
            "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
            "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
            "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
        ),
    )
    contaminant_monitoring_check_result = runtime.check_contaminant_monitoring_import(
        contaminant_monitoring_check_request
    )
    contaminant_monitoring_bundle_request = ExportContaminantMonitoringInterpretationBundleRequest(
        check_result=contaminant_monitoring_check_result,
        bundle_note="Illustrative contaminant monitoring interpretation bundle for governed mercury monitoring review.",
    )
    contaminant_monitoring_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        contaminant_monitoring_bundle_request
    )
    contaminant_monitoring_signoff_request = ExportContaminantMonitoringSignoffPacketRequest(
        interpretation_bundle=contaminant_monitoring_bundle,
        reviewer_id="example.contaminant.reviewer",
        reviewer_role="contaminant_monitoring_reviewer",
        decisions=[
            {
                "actionId": "review_header_resolution_and_quality_flags",
                "decisionStatus": "completed",
                "rationale": "Header alias resolution and quality flags were reviewed against the governed import-check context.",
                "reviewedAt": "2026-04-11",
                "supportingUris": ["docs://contaminant-monitoring-import"],
            },
            {
                "actionId": "review_occurrence_evidence_context",
                "decisionStatus": "completed",
                "rationale": "Occurrence-evidence context was reviewed for monitored fish commodities and methylmercury interpretation.",
                "reviewedAt": "2026-04-11",
                "supportingUris": ["docs://occurrence-evidence-registry"],
            },
            {
                "actionId": "review_analytical_method_context",
                "decisionStatus": "completed",
                "rationale": "Analytical-method evidence was reviewed for LOQ, recovery, and measurement-uncertainty context.",
                "reviewedAt": "2026-04-11",
                "supportingUris": ["docs://analytical-method-evidence-registry"],
            },
            {
                "actionId": "review_linked_focus_records",
                "decisionStatus": "completed",
                "rationale": "Linked review-focus records were reviewed for large predatory fish and sensitive populations.",
                "reviewedAt": "2026-04-11",
                "supportingUris": ["docs://contaminant-monitoring-interpretation"],
            },
            {
                "actionId": "review_governance_links",
                "decisionStatus": "completed",
                "rationale": "Source, method, legal, dataset, and reference-value links were reviewed as governed monitoring context.",
                "reviewedAt": "2026-04-11",
                "supportingUris": ["docs://regulatory-source-databases"],
            },
        ],
        packet_note="Illustrative reviewer packet for governed contaminant monitoring signoff.",
    )
    contaminant_monitoring_signoff_packet = runtime.export_contaminant_monitoring_signoff_packet(
        contaminant_monitoring_signoff_request
    )
    contaminant_monitoring_review_dossier_request = ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
        interpretation_bundle=contaminant_monitoring_bundle,
        signoff_packet=contaminant_monitoring_signoff_packet,
    )
    contaminant_emerging_snapshot = EmergingContaminantRecord.model_validate(
        runtime.defaults.get_emerging_contaminant_record(contaminant_monitoring_bundle.contaminant_family.value)
    )
    contaminant_source_governance = collect_source_governance_snapshot(
        runtime.defaults,
        contaminant_monitoring_bundle.covered_source_ids + contaminant_emerging_snapshot.source_ids,
    )
    contaminant_monitoring_review_dossier = VersionPinnedContaminantMonitoringReviewDossier(
        dossier_status=contaminant_monitoring_signoff_packet.overall_signoff_status,
        interpretation_bundle=contaminant_monitoring_bundle,
        signoff_packet=contaminant_monitoring_signoff_packet,
        release_metadata=ReleaseMetadataSnapshot(
            resource_uri="release://metadata-report",
            release_version=VERSION,
            defaults_version=runtime.defaults.build_manifest()["defaultsVersion"],
            metadata_report_sha256="example-release-metadata-sha256",
            artifact_hashes={
                "sourceCatalogManifest": "example-source-catalog-manifest-sha256",
                "referenceValuesManifest": "example-reference-values-manifest-sha256",
                "consumptionDatasetsManifest": "example-consumption-datasets-manifest-sha256",
                "methodRegistryManifest": "example-method-registry-manifest-sha256",
                "legalAuthoritiesManifest": "example-legal-authorities-manifest-sha256",
                "occurrenceEvidenceManifest": "example-occurrence-evidence-manifest-sha256",
                "analyticalMethodEvidenceManifest": "example-analytical-method-evidence-manifest-sha256",
                "metalsReviewFocusManifest": "example-metals-review-focus-manifest-sha256",
                "emergingContaminantsManifest": "example-emerging-contaminants-manifest-sha256",
            },
        ),
        source_governance_snapshot=contaminant_source_governance,
        emerging_contaminant_snapshot=contaminant_emerging_snapshot,
        pinned_resources=[
            PinnedResourceFingerprint(
                role="release_metadata_report",
                uri="release://metadata-report",
                sha256="example-release-metadata-sha256",
                description="Illustrative release metadata report fingerprint for a contaminant monitoring dossier.",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                sanitisation_state=SanitisationState.RETAINED,
            ),
            PinnedResourceFingerprint(
                role="source_catalog_manifest",
                uri="source-catalog://manifest",
                sha256="example-source-catalog-manifest-sha256",
                description="Illustrative source catalog manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="reference_values_manifest",
                uri="reference-values://manifest",
                sha256="example-reference-values-manifest-sha256",
                description="Illustrative reference-values manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="consumption_datasets_manifest",
                uri="consumption-datasets://manifest",
                sha256="example-consumption-datasets-manifest-sha256",
                description="Illustrative consumption-datasets manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="method_registry_manifest",
                uri="method-registry://manifest",
                sha256="example-method-registry-manifest-sha256",
                description="Illustrative method-registry manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="legal_authorities_manifest",
                uri="legal-authorities://manifest",
                sha256="example-legal-authorities-manifest-sha256",
                description="Illustrative legal-authorities manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="occurrence_evidence_manifest",
                uri="occurrence-evidence://manifest",
                sha256="example-occurrence-evidence-manifest-sha256",
                description="Illustrative occurrence-evidence manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="occurrence_evidence_family",
                uri="occurrence-evidence://family/mercury_food_contaminants",
                sha256="example-occurrence-evidence-family-sha256",
                description="Illustrative occurrence-evidence family fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="analytical_method_evidence_manifest",
                uri="analytical-method-evidence://manifest",
                sha256="example-analytical-method-evidence-manifest-sha256",
                description="Illustrative analytical-method-evidence manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="analytical_method_evidence_family",
                uri="analytical-method-evidence://family/mercury_food_contaminants",
                sha256="example-analytical-method-evidence-family-sha256",
                description="Illustrative analytical-method-evidence family fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="metals_review_focus_manifest",
                uri="metals-review-focus://manifest",
                sha256="example-metals-review-focus-manifest-sha256",
                description="Illustrative review-focus manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="metals_review_focus_family",
                uri="metals-review-focus://family/mercury_food_contaminants",
                sha256="example-metals-review-focus-family-sha256",
                description="Illustrative review-focus family fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="emerging_contaminants_manifest",
                uri="emerging-contaminants://manifest",
                sha256="example-emerging-contaminants-manifest-sha256",
                description="Illustrative emerging-contaminants manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="emerging_contaminant_family",
                uri="emerging-contaminants://family/mercury_food_contaminants",
                sha256="example-emerging-contaminant-family-sha256",
                description="Illustrative emerging contaminant family fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="interpretation_documentation",
                uri="docs://contaminant-monitoring-interpretation",
                sha256="example-contaminant-monitoring-interpretation-doc-sha256",
                description="Illustrative contaminant monitoring interpretation documentation fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="signoff_documentation",
                uri="docs://contaminant-monitoring-signoff",
                sha256="example-contaminant-monitoring-signoff-doc-sha256",
                description="Illustrative contaminant monitoring signoff documentation fingerprint.",
            ),
        ],
        escalation_required=False,
        escalation_items=[],
        confidentiality_annotations=[
            {
                "targetPath": "release_metadata",
                "targetKind": "field",
                "confidentialityTag": "public",
                "rationale": "Illustrative release metadata snapshot is retained in the dossier payload.",
            },
            {
                "targetPath": "pinned_resources.release_metadata_report",
                "targetKind": "resource",
                "confidentialityTag": "confidential",
                "rationale": "Illustrative full release metadata report reference remains internal-review material.",
            },
        ],
        sanitisation_records=[
            {
                "targetPath": "pinned_resources.release_metadata_report",
                "targetKind": "resource",
                "confidentialityTag": "confidential",
                "sanitisationState": "retained",
                "note": "Illustrative confidential release metadata pin is retained on the internal-review dossier.",
            }
        ],
        limitations=[
            LimitationNote(
                code="version_pinned_not_signed",
                message="Illustrative dossier example uses placeholder hashes and is not cryptographically signed.",
            ),
            LimitationNote(
                code="review_only_contaminant_monitoring_dossier",
                message="Illustrative dossier records contaminant monitoring review and escalation posture only.",
            ),
        ],
        notes=[
            "Example dossier shows the version-pinned contaminant monitoring export shape without requiring live release-report generation during artifact writing.",
            "Escalation items remain derived from reviewer waivers or unresolved blocking actions only.",
            "This dossier is built from a submission-capable contaminant monitoring package for mercury in v0.1.",
            "All reviewer actions are completed and no waivers or unresolved blocking actions remain.",
        ],
    )
    scientific_follow_up_bundle_request = ExportScientificFollowUpQueueBundleRequest(
        dossier=contaminant_monitoring_review_dossier,
        assessment=runtime.assess_review_dossier_readiness(
            AssessReviewDossierReadinessRequest(
                dossier=contaminant_monitoring_review_dossier,
                target_profile="mercury_internal_review",
            )
        ),
        bundle_note="Illustrative machine-readable handoff for readiness-side scientific follow-up queues.",
    )
    scientific_follow_up_queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        scientific_follow_up_bundle_request
    )
    scientific_follow_up_review_board_request = ExportScientificFollowUpReviewBoardRequest(
        queue_bundle=scientific_follow_up_queue_bundle,
        board_note="Illustrative reviewer-routing board derived from readiness-side scientific follow-up queues.",
    )
    scientific_follow_up_review_board = runtime.export_scientific_follow_up_review_board(
        scientific_follow_up_review_board_request
    )
    scientific_follow_up_owner_handoff_request = ExportScientificFollowUpOwnerHandoffPacketRequest(
        board=scientific_follow_up_review_board,
        owner_lane="scientific_reviewer",
        packet_note="Illustrative owner-scoped handoff packet derived from readiness-side scientific follow-up routing.",
    )
    scientific_follow_up_owner_handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
        scientific_follow_up_owner_handoff_request
    )
    scientific_follow_up_owner_remediation_request = ExportScientificFollowUpOwnerRemediationPacketRequest(
        handoff_packet=scientific_follow_up_owner_handoff_packet,
        packet_note="Illustrative owner-scoped remediation packet derived from scientific follow-up handoff.",
    )
    scientific_follow_up_owner_remediation_packet = runtime.export_scientific_follow_up_owner_remediation_packet(
        scientific_follow_up_owner_remediation_request
    )
    scientific_follow_up_owner_signoff_request = ExportScientificFollowUpOwnerSignoffPacketRequest(
        remediation_packet=scientific_follow_up_owner_remediation_packet,
        reviewer_id="example.scientific.owner",
        reviewer_role="scientific_reviewer",
        decisions=[
            {
                "actionId": "review_scientific_ledger.row_level_lod_coverage",
                "decisionStatus": "completed",
                "rationale": "LOD coverage was reviewed for the current cycle.",
                "reviewedAt": "2026-04-12",
                "supportingUris": ["docs://scientific-follow-up-owner-signoff"],
            },
            {
                "actionId": (
                    "review_scientific_ledger.lower_bound_handling."
                    "eu.mercury.occurrence_evidence.official_monitoring_context"
                ),
                "decisionStatus": "acknowledged",
                "rationale": "Lower-bound handling requires further owner follow-up this cycle.",
                "reviewedAt": "2026-04-12",
                "supportingUris": ["docs://scientific-follow-up-owner-remediation"],
            },
        ],
        packet_note="Illustrative owner-scoped signoff packet derived from scientific follow-up remediation.",
    )
    scientific_follow_up_owner_signoff_packet = runtime.export_scientific_follow_up_owner_signoff_packet(
        scientific_follow_up_owner_signoff_request
    )
    scientific_follow_up_owner_signoff_dossier_request = (
        ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest(
            source_dossier=contaminant_monitoring_review_dossier,
            signoff_packet=scientific_follow_up_owner_signoff_packet,
        )
    )
    scientific_follow_up_owner_signoff_dossier = (
        runtime.export_version_pinned_scientific_follow_up_owner_signoff_dossier(
            scientific_follow_up_owner_signoff_dossier_request
        )
    )
    metals_occurrence_lookup_request = LookupMetalsOccurrenceRequest(
        contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        jurisdiction="eu",
    )
    metals_occurrence_lookup_result = runtime.lookup_metals_occurrence(metals_occurrence_lookup_request)
    metals_review_focus_lookup_request = LookupMetalsReviewFocusRequest(
        contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        jurisdiction="eu",
        focus_food="tuna",
    )
    metals_review_focus_lookup_result = runtime.lookup_metals_review_focus(metals_review_focus_lookup_request)
    metals_monitoring_bundle_request = ExportMetalsMonitoringInterpretationBundleRequest(
        occurrence_result=metals_occurrence_lookup_result,
        review_focus_result=metals_review_focus_lookup_result,
        bundle_note="Illustrative metals monitoring interpretation bundle for governed mercury review context.",
    )
    metals_monitoring_bundle = runtime.export_metals_monitoring_interpretation_bundle(
        metals_monitoring_bundle_request
    )
    metals_monitoring_signoff_request = ExportMetalsMonitoringSignoffPacketRequest(
        interpretation_bundle=metals_monitoring_bundle,
        reviewer_id="example.metals.reviewer",
        reviewer_role="metals_regulatory_reviewer",
        decisions=[
            {
                "actionId": "review_occurrence_context",
                "decisionStatus": "completed",
                "rationale": "Occurrence context was reviewed against the governed mercury occurrence support record.",
                "reviewedAt": "2026-04-11",
                "supportingUris": ["docs://metals-occurrence-registry"],
            },
            {
                "actionId": "review_priority_food_groups",
                "decisionStatus": "completed",
                "rationale": "Priority food groups and high-attention fish species were reviewed explicitly.",
                "reviewedAt": "2026-04-11",
                "supportingUris": ["docs://metals-monitoring-interpretation"],
            },
            {
                "actionId": "review_sensitive_populations",
                "decisionStatus": "completed",
                "rationale": "Sensitive-population context was reviewed for pregnancy-related and child-focused advice.",
                "reviewedAt": "2026-04-11",
                "supportingUris": ["docs://metals-review-focus-registry"],
            },
            {
                "actionId": "review_commodity_focus_prompts",
                "decisionStatus": "completed",
                "rationale": "Commodity-focus prompts were reviewed for tuna and other predatory fish.",
                "reviewedAt": "2026-04-11",
                "supportingUris": ["docs://metals-review-focus-registry"],
            },
            {
                "actionId": "review_governance_links",
                "decisionStatus": "completed",
                "rationale": "Source, method, dataset, legal, and reference-value links were reviewed as governed context.",
                "reviewedAt": "2026-04-11",
                "supportingUris": ["docs://regulatory-source-databases"],
            },
        ],
        packet_note="Illustrative reviewer packet for governed metals monitoring signoff.",
    )
    metals_monitoring_signoff_packet = runtime.export_metals_monitoring_signoff_packet(
        metals_monitoring_signoff_request
    )
    metals_emerging_snapshot = EmergingContaminantRecord.model_validate(
        runtime.defaults.get_emerging_contaminant_record(metals_monitoring_bundle.contaminant_family.value)
    )
    metals_source_governance = collect_source_governance_snapshot(
        runtime.defaults,
        metals_monitoring_bundle.covered_source_ids + metals_emerging_snapshot.source_ids,
    )
    metals_monitoring_review_dossier_request = ExportVersionPinnedMetalsMonitoringReviewDossierRequest(
        interpretation_bundle=metals_monitoring_bundle,
        signoff_packet=metals_monitoring_signoff_packet,
    )
    metals_monitoring_review_dossier = VersionPinnedMetalsMonitoringReviewDossier(
        dossier_status=metals_monitoring_signoff_packet.overall_signoff_status,
        interpretation_bundle=metals_monitoring_bundle,
        signoff_packet=metals_monitoring_signoff_packet,
        release_metadata=ReleaseMetadataSnapshot(
            resource_uri="release://metadata-report",
            release_version=VERSION,
            defaults_version=runtime.defaults.build_manifest()["defaultsVersion"],
            metadata_report_sha256="example-release-metadata-sha256",
            artifact_hashes={
                "sourceCatalogManifest": "example-source-catalog-manifest-sha256",
                "referenceValuesManifest": "example-reference-values-manifest-sha256",
                "consumptionDatasetsManifest": "example-consumption-datasets-manifest-sha256",
                "methodRegistryManifest": "example-method-registry-manifest-sha256",
                "legalAuthoritiesManifest": "example-legal-authorities-manifest-sha256",
                "metalsOccurrenceManifest": "example-metals-occurrence-manifest-sha256",
                "metalsReviewFocusManifest": "example-metals-review-focus-manifest-sha256",
                "emergingContaminantsManifest": "example-emerging-contaminants-manifest-sha256",
            },
        ),
        source_governance_snapshot=metals_source_governance,
        emerging_contaminant_snapshot=metals_emerging_snapshot,
        pinned_resources=[
            PinnedResourceFingerprint(
                role="release_metadata_report",
                uri="release://metadata-report",
                sha256="example-release-metadata-sha256",
                description="Illustrative release metadata report fingerprint for a metals monitoring dossier.",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                sanitisation_state=SanitisationState.RETAINED,
            ),
            PinnedResourceFingerprint(
                role="source_catalog_manifest",
                uri="source-catalog://manifest",
                sha256="example-source-catalog-manifest-sha256",
                description="Illustrative source catalog manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="reference_values_manifest",
                uri="reference-values://manifest",
                sha256="example-reference-values-manifest-sha256",
                description="Illustrative reference-values manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="consumption_datasets_manifest",
                uri="consumption-datasets://manifest",
                sha256="example-consumption-datasets-manifest-sha256",
                description="Illustrative consumption-datasets manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="method_registry_manifest",
                uri="method-registry://manifest",
                sha256="example-method-registry-manifest-sha256",
                description="Illustrative method-registry manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="legal_authorities_manifest",
                uri="legal-authorities://manifest",
                sha256="example-legal-authorities-manifest-sha256",
                description="Illustrative legal-authorities manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="metals_occurrence_manifest",
                uri="metals-occurrence://manifest",
                sha256="example-metals-occurrence-manifest-sha256",
                description="Illustrative metals-occurrence manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="metals_occurrence_family",
                uri="metals-occurrence://family/mercury_food_contaminants",
                sha256="example-metals-occurrence-family-sha256",
                description="Illustrative family-specific metals-occurrence fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="metals_review_focus_manifest",
                uri="metals-review-focus://manifest",
                sha256="example-metals-review-focus-manifest-sha256",
                description="Illustrative metals-review-focus manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="metals_review_focus_family",
                uri="metals-review-focus://family/mercury_food_contaminants",
                sha256="example-metals-review-focus-family-sha256",
                description="Illustrative family-specific metals-review-focus fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="emerging_contaminants_manifest",
                uri="emerging-contaminants://manifest",
                sha256="example-emerging-contaminants-manifest-sha256",
                description="Illustrative emerging-contaminants manifest fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="emerging_contaminant_family",
                uri="emerging-contaminants://family/mercury_food_contaminants",
                sha256="example-emerging-contaminant-family-sha256",
                description="Illustrative family-specific emerging-contaminant fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="interpretation_documentation",
                uri="docs://metals-monitoring-interpretation",
                sha256="example-metals-interpretation-doc-sha256",
                description="Illustrative interpretation workflow documentation fingerprint.",
            ),
            PinnedResourceFingerprint(
                role="signoff_documentation",
                uri="docs://metals-monitoring-signoff",
                sha256="example-metals-signoff-doc-sha256",
                description="Illustrative signoff workflow documentation fingerprint.",
            ),
        ],
        escalation_required=False,
        escalation_items=[],
        confidentiality_annotations=[
            {
                "targetPath": "release_metadata",
                "targetKind": "field",
                "confidentialityTag": "public",
                "rationale": "Illustrative release metadata snapshot is retained as dossier provenance.",
            },
            {
                "targetPath": "pinned_resources.release_metadata_report",
                "targetKind": "resource",
                "confidentialityTag": "confidential",
                "rationale": "Illustrative full release metadata report resource is kept internal to the review dossier.",
            },
        ],
        sanitisation_records=[
            {
                "targetPath": "pinned_resources.release_metadata_report",
                "targetKind": "resource",
                "confidentialityTag": "confidential",
                "sanitisationState": "retained",
                "note": "Illustrative confidential release metadata pin retained for the internal-review dossier.",
            }
        ],
        limitations=[
            LimitationNote(
                code="version_pinned_not_signed",
                message="Illustrative metals dossier example uses placeholder hashes and is not cryptographically signed.",
            ),
            LimitationNote(
                code="review_only_metals_dossier",
                message="Illustrative metals dossier records review and escalation posture only, not a native exposure engine or final regulatory decision package.",
            ),
        ],
        notes=[
            "Example dossier shows the version-pinned metals monitoring export shape without requiring live release-report generation during artifact writing.",
            "Escalation overlay is driven only by explicit waivers or unresolved blocking actions recorded in the signoff packet.",
            "This dossier is built from a submission-capable metals monitoring package for mercury in v0.1.",
        ],
    )
    sanitised_dossier_request = ExportSanitisedPublicReviewDossierRequest(dossier=adapter_review_dossier)
    sanitised_dossier = SanitisedPublicReviewDossier.model_validate(
        runtime.export_sanitised_public_review_dossier(sanitised_dossier_request)
    )
    interoperability_preview_request = ExportInteroperabilityPreviewRequest(
        dossier=adapter_review_dossier,
        target_profile="oht_85_iuclid_json_preview",
    )
    interoperability_preview = runtime.export_interoperability_preview(interoperability_preview_request)
    interoperability_readiness_request = AssessInteroperabilityPreviewReadinessRequest(
        dossier=adapter_review_dossier,
        preview=interoperability_preview,
        target_profile="eu_internal_exchange_preview",
    )
    interoperability_readiness_result = runtime.assess_interoperability_preview_readiness(
        interoperability_readiness_request
    )
    interoperability_remediation_request = ExportInteroperabilityRemediationBundleRequest(
        dossier=adapter_review_dossier,
        preview=interoperability_preview,
        assessment=interoperability_readiness_result,
    )
    interoperability_remediation_bundle = runtime.export_interoperability_remediation_bundle(
        interoperability_remediation_request
    )
    interoperability_signoff_request = ExportInteroperabilitySignoffPacketRequest(
        remediation_bundle=interoperability_remediation_bundle,
        reviewer_id="example.regulatory.reviewer",
        reviewer_role="regulatory_reviewer",
        decisions=[
            InteroperabilitySignoffDecisionInput(
                action_id="upgrade_linked_dossier_readiness",
                decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                rationale="Current adapter family remains explicitly internal-review only; waiver retained for controlled example exchange use.",
                reviewed_at="2026-04-11",
                supporting_uris=["docs://regulatory-governance"],
            ),
            InteroperabilitySignoffDecisionInput(
                action_id="review_unsupported_preview_fields",
                decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                rationale="Unsupported diagnostics were reviewed and retained in the MCP-only review bundle.",
                reviewed_at="2026-04-11",
                supporting_uris=["docs://interoperability-preview"],
            ),
            InteroperabilitySignoffDecisionInput(
                action_id="replace_non_direct_mappings",
                decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                rationale="Derived mappings were accepted as governed preview-only mappings for this illustrative packet.",
                reviewed_at="2026-04-11",
                supporting_uris=["docs://interoperability-readiness"],
            ),
        ],
        packet_note="Illustrative reviewer packet for governed interoperability remediation signoff.",
    )
    interoperability_signoff_packet = runtime.export_interoperability_signoff_packet(
        interoperability_signoff_request
    )

    return {
        "dietaryErrorPayload.v1": DietaryErrorPayload(
            code="input_limit_exceeded",
            message="The submitted request exceeded a configured Dietary MCP runtime limit.",
            suggestion="Reduce the request size or raise the documented environment override within the hard schema ceiling.",
            details={
                "requestId": "example-error-0001",
                "runtimeLimit": 100000,
                "hardCeiling": 1000000,
                "envVar": "DIETARY_MCP_MAX_PROBABILISTIC_ITERATIONS",
            },
        ).model_dump(mode="json"),
        "checkAdapterImportRequest.v1": adapter_check_request.model_dump(mode="json"),
        "adapterImportCheckResult.v1": adapter_check_result.model_dump(mode="json"),
        "compareAdapterImportToWalkthroughRequest.v1": adapter_compare_request.model_dump(mode="json"),
        "compareAdapterImportToWalkthroughResult.v1": adapter_compare_result.model_dump(mode="json"),
        "exportAdapterReviewBundleRequest.v1": adapter_review_bundle_request.model_dump(mode="json"),
        "adapterReviewBundle.v1": adapter_review_bundle.model_dump(mode="json"),
        "exportVersionPinnedAdapterReviewDossierRequest.v1": adapter_review_dossier_request.model_dump(mode="json"),
        "versionPinnedAdapterReviewDossier.v1": adapter_review_dossier.model_dump(mode="json"),
        "exportSanitisedPublicReviewDossierRequest.v1": sanitised_dossier_request.model_dump(mode="json"),
        "sanitisedPublicReviewDossier.v1": sanitised_dossier.model_dump(mode="json"),
        "exportInteroperabilityPreviewRequest.v1": interoperability_preview_request.model_dump(mode="json"),
        "interoperabilityExportPreview.v1": interoperability_preview.model_dump(mode="json"),
        "assessInteroperabilityPreviewReadinessRequest.v1": interoperability_readiness_request.model_dump(
            mode="json"
        ),
        "interoperabilityPreviewReadinessAssessment.v1": interoperability_readiness_result.model_dump(mode="json"),
        "exportInteroperabilityRemediationBundleRequest.v1": interoperability_remediation_request.model_dump(
            mode="json"
        ),
        "interoperabilityRemediationBundle.v1": interoperability_remediation_bundle.model_dump(mode="json"),
        "exportInteroperabilitySignoffPacketRequest.v1": interoperability_signoff_request.model_dump(mode="json"),
        "interoperabilitySignoffPacket.v1": interoperability_signoff_packet.model_dump(mode="json"),
        "assessReviewDossierReadinessRequest.v1": adapter_readiness_request.model_dump(mode="json"),
        "reviewDossierReadinessAssessment.v1": adapter_readiness_result.model_dump(mode="json"),
        "exportScientificFollowUpQueueBundleRequest.v1": scientific_follow_up_bundle_request.model_dump(
            mode="json"
        ),
        "scientificFollowUpQueueBundle.v1": scientific_follow_up_queue_bundle.model_dump(mode="json"),
        "exportScientificFollowUpReviewBoardRequest.v1": scientific_follow_up_review_board_request.model_dump(
            mode="json"
        ),
        "scientificFollowUpReviewBoard.v1": scientific_follow_up_review_board.model_dump(mode="json"),
        "exportScientificFollowUpOwnerHandoffPacketRequest.v1": scientific_follow_up_owner_handoff_request.model_dump(
            mode="json"
        ),
        "scientificFollowUpOwnerHandoffPacket.v1": scientific_follow_up_owner_handoff_packet.model_dump(
            mode="json"
        ),
        "exportScientificFollowUpOwnerRemediationPacketRequest.v1": (
            scientific_follow_up_owner_remediation_request.model_dump(mode="json")
        ),
        "scientificFollowUpOwnerRemediationPacket.v1": scientific_follow_up_owner_remediation_packet.model_dump(
            mode="json"
        ),
        "exportScientificFollowUpOwnerSignoffPacketRequest.v1": (
            scientific_follow_up_owner_signoff_request.model_dump(mode="json")
        ),
        "scientificFollowUpOwnerSignoffPacket.v1": scientific_follow_up_owner_signoff_packet.model_dump(
            mode="json"
        ),
        "exportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest.v1": (
            scientific_follow_up_owner_signoff_dossier_request.model_dump(mode="json")
        ),
        "versionPinnedScientificFollowUpOwnerSignoffDossier.v1": (
            scientific_follow_up_owner_signoff_dossier.model_dump(mode="json")
        ),
        "lookupReferenceValuesRequest.v1": reference_value_lookup_request.model_dump(mode="json"),
        "referenceValueLookupResult.v1": reference_value_lookup_result.model_dump(mode="json"),
        "evaluateGlobalTradeRiskRequest.v1": trade_risk_request.model_dump(mode="json"),
        "globalTradeRiskReport.v1": trade_risk_report.model_dump(mode="json"),
        "exportTradeRiskReviewBundleRequest.v1": trade_risk_review_bundle_request.model_dump(mode="json"),
        "tradeRiskReviewBundle.v1": trade_risk_review_bundle.model_dump(mode="json"),
        "exportVersionPinnedTradeRiskReviewDossierRequest.v1": trade_risk_review_dossier_request.model_dump(mode="json"),
        "versionPinnedTradeRiskReviewDossier.v1": trade_risk_review_dossier.model_dump(mode="json"),
        "lookupContaminantLegalLimitsRequest.v1": contaminant_legal_limit_lookup_request.model_dump(mode="json"),
        "contaminantLegalLimitLookupResult.v1": contaminant_legal_limit_lookup_result.model_dump(mode="json"),
        "lookupMethodSupportRequest.v1": method_support_lookup_request.model_dump(mode="json"),
        "methodSupportLookupResult.v1": method_support_lookup_result.model_dump(mode="json"),
        "lookupConsumptionDatasetSupportRequest.v1": dataset_support_lookup_request.model_dump(mode="json"),
        "consumptionDatasetSupportLookupResult.v1": dataset_support_lookup_result.model_dump(mode="json"),
        "lookupReportingProfilesRequest.v1": reporting_profile_lookup_request.model_dump(mode="json"),
        "reportingProfileLookupResult.v1": reporting_profile_lookup_result.model_dump(mode="json"),
        "lookupOccurrenceEvidenceRequest.v1": occurrence_evidence_lookup_request.model_dump(mode="json"),
        "occurrenceEvidenceLookupResult.v1": occurrence_evidence_lookup_result.model_dump(mode="json"),
        "lookupAnalyticalMethodEvidenceRequest.v1": analytical_method_evidence_lookup_request.model_dump(
            mode="json"
        ),
        "analyticalMethodEvidenceLookupResult.v1": analytical_method_evidence_lookup_result.model_dump(mode="json"),
        "checkContaminantMonitoringImportRequest.v1": contaminant_monitoring_check_request.model_dump(mode="json"),
        "contaminantMonitoringImportCheckResult.v1": contaminant_monitoring_check_result.model_dump(mode="json"),
        "exportContaminantMonitoringInterpretationBundleRequest.v1": contaminant_monitoring_bundle_request.model_dump(
            mode="json"
        ),
        "contaminantMonitoringInterpretationBundle.v1": contaminant_monitoring_bundle.model_dump(mode="json"),
        "exportContaminantMonitoringSignoffPacketRequest.v1": contaminant_monitoring_signoff_request.model_dump(
            mode="json"
        ),
        "contaminantMonitoringSignoffPacket.v1": contaminant_monitoring_signoff_packet.model_dump(mode="json"),
        "exportVersionPinnedContaminantMonitoringReviewDossierRequest.v1": (
            contaminant_monitoring_review_dossier_request.model_dump(mode="json")
        ),
        "versionPinnedContaminantMonitoringReviewDossier.v1": contaminant_monitoring_review_dossier.model_dump(
            mode="json"
        ),
        "lookupMetalsOccurrenceRequest.v1": metals_occurrence_lookup_request.model_dump(mode="json"),
        "metalsOccurrenceLookupResult.v1": metals_occurrence_lookup_result.model_dump(mode="json"),
        "lookupMetalsReviewFocusRequest.v1": metals_review_focus_lookup_request.model_dump(mode="json"),
        "metalsReviewFocusLookupResult.v1": metals_review_focus_lookup_result.model_dump(mode="json"),
        "exportMetalsMonitoringInterpretationBundleRequest.v1": metals_monitoring_bundle_request.model_dump(
            mode="json"
        ),
        "metalsMonitoringInterpretationBundle.v1": metals_monitoring_bundle.model_dump(mode="json"),
        "exportMetalsMonitoringSignoffPacketRequest.v1": metals_monitoring_signoff_request.model_dump(
            mode="json"
        ),
        "metalsMonitoringSignoffPacket.v1": metals_monitoring_signoff_packet.model_dump(mode="json"),
        "exportVersionPinnedMetalsMonitoringReviewDossierRequest.v1": (
            metals_monitoring_review_dossier_request.model_dump(mode="json")
        ),
        "versionPinnedMetalsMonitoringReviewDossier.v1": metals_monitoring_review_dossier.model_dump(
            mode="json"
        ),
        "parseRawSurveyDatasetRequest.v1": parse_survey_request.model_dump(mode="json"),
        "dietarySurveyDatasetRecord.v1": survey_dataset.model_dump(mode="json"),
        "summarizeSurveyDistributionRequest.v1": survey_distribution_request.model_dump(mode="json"),
        "surveyDistributionSummaryReport.v1": survey_distribution_summary.model_dump(mode="json"),
        "buildProbabilisticIntakeSummaryRequest.v1": probabilistic_request.model_dump(mode="json"),
        "probabilisticIntakeSummary.v1": probabilistic_summary.model_dump(mode="json"),
        "residueUncertaintyModel.v1": uncertainty_request.residue_uncertainty_models[0].model_dump(mode="json"),
        "uncertaintyAssumptionLedger.v1": uncertainty_assessment.uncertainty_assumption_ledger.model_dump(
            mode="json"
        ),
        "buildUncertaintyIntakeAssessmentRequest.v1": uncertainty_request.model_dump(mode="json"),
        "uncertaintyIntakeAssessment.v1": uncertainty_assessment.model_dump(mode="json"),
        "dietaryResidueProfile.v1": residue_profile.model_dump(mode="json"),
        "dietaryConsumptionProfile.v1": chronic_selection.profile.model_dump(mode="json"),
        "dietaryIntakeScenarioDefinition.v1": point_scenario.model_dump(mode="json"),
        "dietaryIntakeSummary.pointEstimate.v1": point_summary.model_dump(mode="json"),
        "dietaryIntakeSummary.boundedAcute.v1": bounded_summary.model_dump(mode="json"),
        "dietaryScenarioComparisonRecord.v1": comparison.model_dump(mode="json"),
        "routeDoseEstimate.v1": pbpk_bundle.route_dose_estimate.model_dump(mode="json"),
        "pbpkExternalImportBundle.v1": pbpk_bundle.model_dump(mode="json"),
        "toxclawDietaryEvidenceBundle.v1": toxclaw_bundle.model_dump(mode="json"),
    }


def write_examples(repo_root: Path, runtime: DietaryRuntime) -> dict[str, dict]:
    examples = build_examples(runtime)
    target_dir = repo_root / "schemas" / "examples"
    target_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in examples.items():
        target_path = target_dir / f"{name}.json"
        if target_path.exists():
            existing = json.loads(target_path.read_text())
            payload = _preserve_volatile_example_values(payload, existing)  # type: ignore[assignment]
        target_path.write_text(json.dumps(payload, indent=2) + "\n")
    manifest = {
        "examples": [
            {"name": name, "path": f"schemas/examples/{name}.json"} for name in sorted(examples.keys())
        ]
    }
    (target_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return examples
