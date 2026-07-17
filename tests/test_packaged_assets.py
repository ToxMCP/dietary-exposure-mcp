from pathlib import Path

from dietary_mcp.assets import runtime_asset_root, source_checkout_root, sync_packaged_data


def test_source_checkout_is_detected_from_repo_tree() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    assert source_checkout_root() == repo_root
    assert runtime_asset_root() == repo_root


def test_packaged_assets_match_source_after_sync() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    packaged_root = sync_packaged_data(repo_root)

    comparisons = [
        (
            repo_root / "defaults" / "v1" / "core_defaults.json",
            packaged_root / "defaults" / "v1" / "core_defaults.json",
        ),
        (
            repo_root / "defaults" / "v1" / "commodity_taxonomy.json",
            packaged_root / "defaults" / "v1" / "commodity_taxonomy.json",
        ),
        (
            repo_root / "defaults" / "v1" / "consumption_profiles_who_gems_public.json",
            packaged_root / "defaults" / "v1" / "consumption_profiles_who_gems_public.json",
        ),
        (
            repo_root / "defaults" / "v1" / "source_catalog.json",
            packaged_root / "defaults" / "v1" / "source_catalog.json",
        ),
        (
            repo_root / "defaults" / "v1" / "reference_values.json",
            packaged_root / "defaults" / "v1" / "reference_values.json",
        ),
        (
            repo_root / "defaults" / "v1" / "contaminant_legal_limits_wave2.json",
            packaged_root / "defaults" / "v1" / "contaminant_legal_limits_wave2.json",
        ),
        (
            repo_root / "defaults" / "v1" / "consumption_datasets.json",
            packaged_root / "defaults" / "v1" / "consumption_datasets.json",
        ),
        (
            repo_root / "defaults" / "v1" / "method_registry.json",
            packaged_root / "defaults" / "v1" / "method_registry.json",
        ),
        (
            repo_root / "defaults" / "v1" / "legal_authorities.json",
            packaged_root / "defaults" / "v1" / "legal_authorities.json",
        ),
        (
            repo_root / "defaults" / "v1" / "legal_authorities_contaminant_legal_limits_wave2.json",
            packaged_root / "defaults" / "v1" / "legal_authorities_contaminant_legal_limits_wave2.json",
        ),
        (
            repo_root / "defaults" / "v1" / "source_catalog_contaminant_legal_limits_wave2.json",
            packaged_root / "defaults" / "v1" / "source_catalog_contaminant_legal_limits_wave2.json",
        ),
        (
            repo_root / "defaults" / "v1" / "reporting_profiles.json",
            packaged_root / "defaults" / "v1" / "reporting_profiles.json",
        ),
        (
            repo_root / "defaults" / "v1" / "occurrence_evidence_registry.json",
            packaged_root / "defaults" / "v1" / "occurrence_evidence_registry.json",
        ),
        (
            repo_root / "defaults" / "v1" / "analytical_method_evidence_registry.json",
            packaged_root / "defaults" / "v1" / "analytical_method_evidence_registry.json",
        ),
        (
            repo_root / "defaults" / "v1" / "metals_occurrence_registry.json",
            packaged_root / "defaults" / "v1" / "metals_occurrence_registry.json",
        ),
        (
            repo_root / "defaults" / "v1" / "metals_review_focus_registry.json",
            packaged_root / "defaults" / "v1" / "metals_review_focus_registry.json",
        ),
        (
            repo_root / "defaults" / "v1" / "emerging_contaminants.json",
            packaged_root / "defaults" / "v1" / "emerging_contaminants.json",
        ),
        (
            repo_root / "defaults" / "v1" / "model_governance.json",
            packaged_root / "defaults" / "v1" / "model_governance.json",
        ),
        (
            repo_root / "defaults" / "v1" / "food_vocabulary_crosswalk.json",
            packaged_root / "defaults" / "v1" / "food_vocabulary_crosswalk.json",
        ),
        (
            repo_root / "defaults" / "v1" / "regulatory_readiness_profiles.json",
            packaged_root / "defaults" / "v1" / "regulatory_readiness_profiles.json",
        ),
        (
            repo_root / "defaults" / "extensions" / "README.md",
            packaged_root / "defaults" / "extensions" / "README.md",
        ),
        (
            repo_root / "defaults" / "extensions" / "v1" / "reporting_profiles" / "netherlands_pfas_reporting.json",
            packaged_root / "defaults" / "extensions" / "v1" / "reporting_profiles" / "netherlands_pfas_reporting.json",
        ),
        (
            repo_root / "config" / "release_gates.json",
            packaged_root / "config" / "release_gates.json",
        ),
        (
            repo_root / "validation" / "v1" / "adapter_normalization_cases.json",
            packaged_root / "validation" / "v1" / "adapter_normalization_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "food_vocabulary_cases.json",
            packaged_root / "validation" / "v1" / "food_vocabulary_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "manifest.json",
            packaged_root / "validation" / "v1" / "manifest.json",
        ),
        (
            repo_root / "validation" / "v1" / "regulatory_rules.json",
            packaged_root / "validation" / "v1" / "regulatory_rules.json",
        ),
        (
            repo_root / "validation" / "v1" / "source_database_cases.json",
            packaged_root / "validation" / "v1" / "source_database_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "survey_distribution_summary_cases.json",
            packaged_root / "validation" / "v1" / "survey_distribution_summary_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "probabilistic_intake_summary_cases.json",
            packaged_root / "validation" / "v1" / "probabilistic_intake_summary_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "uncertainty_intake_assessment_cases.json",
            packaged_root / "validation" / "v1" / "uncertainty_intake_assessment_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "censored_residue_policy_cases.json",
            packaged_root / "validation" / "v1" / "censored_residue_policy_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "uncertainty_sensitivity_cases.json",
            packaged_root / "validation" / "v1" / "uncertainty_sensitivity_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "health_reference_exceedance_cases.json",
            packaged_root / "validation" / "v1" / "health_reference_exceedance_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "uncertainty_reproducibility_cases.json",
            packaged_root / "validation" / "v1" / "uncertainty_reproducibility_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "contaminant_monitoring_check_cases.json",
            packaged_root / "validation" / "v1" / "contaminant_monitoring_check_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "contaminant_monitoring_bundle_cases.json",
            packaged_root / "validation" / "v1" / "contaminant_monitoring_bundle_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "contaminant_monitoring_signoff_cases.json",
            packaged_root / "validation" / "v1" / "contaminant_monitoring_signoff_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "contaminant_monitoring_review_dossier_cases.json",
            packaged_root / "validation" / "v1" / "contaminant_monitoring_review_dossier_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "metals_monitoring_bundle_cases.json",
            packaged_root / "validation" / "v1" / "metals_monitoring_bundle_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "metals_monitoring_signoff_cases.json",
            packaged_root / "validation" / "v1" / "metals_monitoring_signoff_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "metals_monitoring_review_dossier_cases.json",
            packaged_root / "validation" / "v1" / "metals_monitoring_review_dossier_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "sanitisation_rules.json",
            packaged_root / "validation" / "v1" / "sanitisation_rules.json",
        ),
        (
            repo_root / "validation" / "v1" / "interoperability_profiles.json",
            packaged_root / "validation" / "v1" / "interoperability_profiles.json",
        ),
        (
            repo_root / "validation" / "v1" / "interoperability_preview_cases.json",
            packaged_root / "validation" / "v1" / "interoperability_preview_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "interoperability_readiness_profiles.json",
            packaged_root / "validation" / "v1" / "interoperability_readiness_profiles.json",
        ),
        (
            repo_root / "validation" / "v1" / "interoperability_rules.json",
            packaged_root / "validation" / "v1" / "interoperability_rules.json",
        ),
        (
            repo_root / "validation" / "v1" / "interoperability_readiness_cases.json",
            packaged_root / "validation" / "v1" / "interoperability_readiness_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "interoperability_remediation_actions.json",
            packaged_root / "validation" / "v1" / "interoperability_remediation_actions.json",
        ),
        (
            repo_root / "validation" / "v1" / "interoperability_remediation_cases.json",
            packaged_root / "validation" / "v1" / "interoperability_remediation_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "interoperability_signoff_cases.json",
            packaged_root / "validation" / "v1" / "interoperability_signoff_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "review_dossier_readiness_cases.json",
            packaged_root / "validation" / "v1" / "review_dossier_readiness_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "scientific_follow_up_queue_bundle_cases.json",
            packaged_root / "validation" / "v1" / "scientific_follow_up_queue_bundle_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "scientific_follow_up_review_board_cases.json",
            packaged_root / "validation" / "v1" / "scientific_follow_up_review_board_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "scientific_follow_up_owner_handoff_cases.json",
            packaged_root / "validation" / "v1" / "scientific_follow_up_owner_handoff_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "scientific_follow_up_owner_remediation_cases.json",
            packaged_root / "validation" / "v1" / "scientific_follow_up_owner_remediation_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "scientific_follow_up_owner_signoff_cases.json",
            packaged_root / "validation" / "v1" / "scientific_follow_up_owner_signoff_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "scientific_follow_up_owner_signoff_dossier_cases.json",
            packaged_root / "validation" / "v1" / "scientific_follow_up_owner_signoff_dossier_cases.json",
        ),
        (
            repo_root / "validation" / "v1" / "sanitised_public_review_cases.json",
            packaged_root / "validation" / "v1" / "sanitised_public_review_cases.json",
        ),
        (
            repo_root / "docs" / "operator_guide.md",
            packaged_root / "docs" / "operator_guide.md",
        ),
        (
            repo_root / "docs" / "regulatory_seed_data.md",
            packaged_root / "docs" / "regulatory_seed_data.md",
        ),
        (
            repo_root / "docs" / "adapter_input_templates.md",
            packaged_root / "docs" / "adapter_input_templates.md",
        ),
        (
            repo_root / "docs" / "adapter_import_walkthroughs.md",
            packaged_root / "docs" / "adapter_import_walkthroughs.md",
        ),
        (
            repo_root / "docs" / "regulatory_governance.md",
            packaged_root / "docs" / "regulatory_governance.md",
        ),
        (
            repo_root / "docs" / "extension_hooks.md",
            packaged_root / "docs" / "extension_hooks.md",
        ),
        (
            repo_root / "docs" / "regulatory_source_databases.md",
            packaged_root / "docs" / "regulatory_source_databases.md",
        ),
        (
            repo_root / "docs" / "reporting_profiles_registry.md",
            packaged_root / "docs" / "reporting_profiles_registry.md",
        ),
        (
            repo_root / "docs" / "occurrence_evidence_registry.md",
            packaged_root / "docs" / "occurrence_evidence_registry.md",
        ),
        (
            repo_root / "docs" / "analytical_method_evidence_registry.md",
            packaged_root / "docs" / "analytical_method_evidence_registry.md",
        ),
        (
            repo_root / "docs" / "contaminant_monitoring_import.md",
            packaged_root / "docs" / "contaminant_monitoring_import.md",
        ),
        (
            repo_root / "docs" / "contaminant_monitoring_interpretation.md",
            packaged_root / "docs" / "contaminant_monitoring_interpretation.md",
        ),
        (
            repo_root / "docs" / "contaminant_monitoring_signoff.md",
            packaged_root / "docs" / "contaminant_monitoring_signoff.md",
        ),
        (
            repo_root / "docs" / "contaminant_monitoring_review_dossier.md",
            packaged_root / "docs" / "contaminant_monitoring_review_dossier.md",
        ),
        (
            repo_root / "docs" / "scientific_follow_up_queue_bundle.md",
            packaged_root / "docs" / "scientific_follow_up_queue_bundle.md",
        ),
        (
            repo_root / "docs" / "scientific_follow_up_review_board.md",
            packaged_root / "docs" / "scientific_follow_up_review_board.md",
        ),
        (
            repo_root / "docs" / "scientific_follow_up_owner_handoff.md",
            packaged_root / "docs" / "scientific_follow_up_owner_handoff.md",
        ),
        (
            repo_root / "docs" / "scientific_follow_up_owner_remediation.md",
            packaged_root / "docs" / "scientific_follow_up_owner_remediation.md",
        ),
        (
            repo_root / "docs" / "scientific_follow_up_owner_signoff.md",
            packaged_root / "docs" / "scientific_follow_up_owner_signoff.md",
        ),
        (
            repo_root / "docs" / "scientific_follow_up_owner_signoff_dossier.md",
            packaged_root / "docs" / "scientific_follow_up_owner_signoff_dossier.md",
        ),
        (
            repo_root / "docs" / "metals_occurrence_registry.md",
            packaged_root / "docs" / "metals_occurrence_registry.md",
        ),
        (
            repo_root / "docs" / "metals_review_focus_registry.md",
            packaged_root / "docs" / "metals_review_focus_registry.md",
        ),
        (
            repo_root / "docs" / "metals_monitoring_interpretation.md",
            packaged_root / "docs" / "metals_monitoring_interpretation.md",
        ),
        (
            repo_root / "docs" / "metals_monitoring_signoff.md",
            packaged_root / "docs" / "metals_monitoring_signoff.md",
        ),
        (
            repo_root / "docs" / "metals_monitoring_review_dossier.md",
            packaged_root / "docs" / "metals_monitoring_review_dossier.md",
        ),
        (
            repo_root / "docs" / "food_vocabulary_crosswalk.md",
            packaged_root / "docs" / "food_vocabulary_crosswalk.md",
        ),
        (
            repo_root / "docs" / "interoperability_preview.md",
            packaged_root / "docs" / "interoperability_preview.md",
        ),
        (
            repo_root / "docs" / "interoperability_readiness.md",
            packaged_root / "docs" / "interoperability_readiness.md",
        ),
        (
            repo_root / "docs" / "interoperability_remediation.md",
            packaged_root / "docs" / "interoperability_remediation.md",
        ),
        (
            repo_root / "docs" / "interoperability_signoff.md",
            packaged_root / "docs" / "interoperability_signoff.md",
        ),
        (
            repo_root / "docs" / "confidentiality_bundles.md",
            packaged_root / "docs" / "confidentiality_bundles.md",
        ),
        (
            repo_root / "templates" / "adapter_inputs" / "manifest.json",
            packaged_root / "templates" / "adapter_inputs" / "manifest.json",
        ),
        (
            repo_root / "templates" / "adapter_inputs" / "efsa_primo_tabular_template.csv",
            packaged_root / "templates" / "adapter_inputs" / "efsa_primo_tabular_template.csv",
        ),
        (
            repo_root / "templates" / "adapter_inputs" / "epa_deem_csv_template.csv",
            packaged_root / "templates" / "adapter_inputs" / "epa_deem_csv_template.csv",
        ),
        (
            repo_root / "evals" / "dietary_mcp_readonly.xml",
            packaged_root / "evals" / "dietary_mcp_readonly.xml",
        ),
    ]

    for source_path, packaged_path in comparisons:
        assert packaged_path.exists()
        assert source_path.read_text() == packaged_path.read_text()
