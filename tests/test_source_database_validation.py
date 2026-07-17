import pytest

from pathlib import Path

from dietary_mcp.source_database_validation import run_source_database_cases


pytestmark = [pytest.mark.slow]


def test_source_database_cases_pass() -> None:
    results = run_source_database_cases(Path(__file__).resolve().parents[1])

    assert results["status"] == "ok"
    assert {item["name"] for item in results["cases"]} >= {
        "glyphosate_reference_value_conflict_is_preserved",
        "acetamiprid_reference_values_expose_current_efsa_outputs",
        "us_glyphosate_reference_value_gap_is_explicit",
        "codex_imidacloprid_reference_value_lookup_stays_jurisdiction_specific",
        "china_acetamiprid_reference_value_lookup_exposes_final_official_adi",
        "us_acetamiprid_reference_value_stays_anchor_only_not_gap",
        "us_pfas_reference_value_gap_is_explicit",
        "codex_cadmium_reference_value_gap_is_explicit",
        "china_lead_reference_value_gap_is_anchor_only_not_silent",
        "us_lead_legal_limit_lookup_exposes_final_processed_food_limits",
        "codex_apple_juice_lead_legal_limit_lookup_is_exact",
        "codex_olive_oil_inorganic_arsenic_legal_limit_lookup_is_exact",
        "codex_rice_inorganic_arsenic_legal_limit_gap_stays_explicit",
        "codex_salmon_methylmercury_legal_limit_stays_anchor_only",
        "us_apple_juice_inorganic_arsenic_legal_limit_lookup_is_exact",
        "china_rice_inorganic_arsenic_legal_limit_lookup_is_exact",
        "china_inorganic_mercury_legal_limit_gap_is_explicit",
        "pfas_reference_value_lookup_exposes_group_twi",
        "acrylamide_reference_values_expose_bmdl_records",
        "bpa_reference_value_lookup_exposes_current_efsa_tdi",
        "cadmium_reference_value_lookup_exposes_current_efsa_twi",
        "lead_reference_value_lookup_exposes_current_efsa_bmdl_records",
        "inorganic_arsenic_reference_value_lookup_exposes_current_efsa_bmdl_record",
        "methylmercury_reference_value_lookup_exposes_current_efsa_twi_record",
        "inorganic_mercury_reference_value_lookup_exposes_current_efsa_twi_record",
        "eu_pesticide_dataset_support_exposes_efsa_backbone",
        "pfas_dataset_support_uses_efsa_food_consumption_and_monitoring_metadata",
        "acrylamide_dataset_support_uses_efsa_backbone_and_monitoring_metadata",
        "bpa_dataset_support_uses_efsa_food_consumption_context",
        "cadmium_dataset_support_uses_efsa_food_consumption_context",
        "lead_dataset_support_uses_efsa_food_consumption_context",
        "inorganic_arsenic_dataset_support_uses_efsa_food_consumption_context",
        "mercury_dataset_support_uses_efsa_food_consumption_context",
        "cadmium_occurrence_evidence_exposes_official_monitoring_context",
        "mercury_occurrence_evidence_exposes_species_sensitive_monitoring_context",
        "lead_analytical_method_evidence_exposes_official_control_context",
        "inorganic_arsenic_analytical_method_evidence_exposes_official_control_context",
        "cadmium_metals_occurrence_registry_exposes_exposure_and_control_context",
        "lead_metals_occurrence_registry_exposes_exposure_and_control_context",
        "inorganic_arsenic_metals_occurrence_registry_exposes_exposure_and_control_context",
        "mercury_metals_occurrence_registry_exposes_exposure_and_control_context",
        "cadmium_metals_review_focus_exposes_staple_and_mollusc_context",
        "lead_metals_review_focus_exposes_game_meat_and_current_contributor_context",
        "inorganic_arsenic_metals_review_focus_exposes_rice_context",
        "mercury_metals_review_focus_exposes_species_and_sensitive_population_context",
        "eu_pesticide_method_support_preserves_primo_boundary",
        "pfas_method_support_stays_review_required_and_non_pesticide",
        "acrylamide_method_support_stays_review_required_and_process_contaminant_specific",
        "bpa_method_support_stays_review_required_and_food_contact_specific",
        "cadmium_method_support_stays_review_required_and_metals_specific",
        "lead_method_support_stays_review_required_and_metals_specific",
        "inorganic_arsenic_method_support_stays_review_required_and_metals_specific",
        "mercury_method_support_stays_review_required_and_metals_specific",
        "microplastics_method_support_hard_blocks_submission_candidate_use",
        "pfas_reporting_profiles_expose_primary_eu_and_optional_dutch_profiles_for_eggs",
        "pfas_reporting_profiles_filter_to_eu_when_requested",
        "pfas_reporting_profiles_expose_optional_dutch_biota_fish_profile_for_fish_review",
    }
