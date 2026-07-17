import json
import shutil
from pathlib import Path

import pytest

from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.errors import DietaryRegistryError


def test_defaults_manifest_contains_versioned_files() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.build_manifest()
    assert manifest["defaultsVersion"] == "v1"
    assert any(item["path"].endswith("core_defaults.json") for item in manifest["files"])
    assert any(item["path"].endswith("commodity_taxonomy.json") for item in manifest["files"])
    assert any(item["path"].endswith("food_vocabulary_crosswalk.json") for item in manifest["files"])
    assert any(item["path"].endswith("model_governance.json") for item in manifest["files"])
    assert any(item["path"].endswith("regulatory_readiness_profiles.json") for item in manifest["files"])
    assert any(item["path"].endswith("reference_values.json") for item in manifest["files"])
    assert any(item["path"].endswith("contaminant_legal_limits_wave2.json") for item in manifest["files"])
    assert any(item["path"].endswith("consumption_datasets.json") for item in manifest["files"])
    assert any(item["path"].endswith("method_registry.json") for item in manifest["files"])
    assert any(item["path"].endswith("legal_authorities.json") for item in manifest["files"])
    assert any(item["path"].endswith("jurisdiction_coverage_wave1.json") for item in manifest["files"])
    assert any(item["path"].endswith("reporting_profiles.json") for item in manifest["files"])
    assert any(item["path"].endswith("occurrence_evidence_registry.json") for item in manifest["files"])
    assert any(item["path"].endswith("analytical_method_evidence_registry.json") for item in manifest["files"])
    assert any(item["path"].endswith("metals_occurrence_registry.json") for item in manifest["files"])
    assert any(item["path"].endswith("metals_review_focus_registry.json") for item in manifest["files"])
    assert any(item["path"].endswith("emerging_contaminants.json") for item in manifest["files"])


def test_defaults_expose_governance_manifests() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])

    assert registry.source_catalog_manifest()["sources"]
    assert registry.reference_values_manifest()["records"]
    assert registry.contaminant_legal_limits_manifest()["records"]
    assert registry.consumption_datasets_manifest()["datasets"]
    assert registry.method_registry_manifest()["methods"]
    assert registry.legal_authorities_manifest()["authorities"]
    assert registry.reporting_profiles_manifest()["profiles"]
    assert registry.occurrence_evidence_manifest()["records"]
    assert registry.analytical_method_evidence_manifest()["records"]
    assert registry.metals_occurrence_manifest()["records"]
    assert registry.metals_review_focus_manifest()["records"]
    assert registry.emerging_contaminants_manifest()["families"]
    assert registry.jurisdiction_coverage_manifest()["records"]
    assert registry.model_governance_manifest()["families"]
    assert registry.regulatory_readiness_profiles_manifest()["profiles"]
    assert registry.food_vocabulary_crosswalk_manifest()["commodityMappings"]


def test_defaults_infer_source_origin_tags_and_reference_provenance() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])

    official = registry.get_source_catalog_record("eu.reg.2023_915")
    taxonomy = registry.get_source_catalog_record("dietary.taxonomy.apples")
    illustrative = registry.get_source_catalog_record("dietary.profile.eu_adult_general")

    assert official["originTag"] == "official_regulatory"
    assert taxonomy["originTag"] == "curated_derived"
    assert illustrative["originTag"] == "illustrative_placeholder"
    assert registry.source_catalog_reference("dietary.profile.eu_adult_general").origin_tag.value == (
        "illustrative_placeholder"
    )
    assert registry.parameter_source_reference("default_processing_factor").origin_tag.value == (
        "internal_operational"
    )


def test_screening_defaults_cover_broader_populations_and_commodities() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])

    population_groups = {item["populationGroup"] for item in registry.consumption_profiles_manifest()["profiles"]}
    commodity_codes = {item["commodityCode"] for item in registry.commodity_taxonomy_manifest()["commodities"]}
    food_vocab_codes = {
        item["commodityCode"] for item in registry.food_vocabulary_crosswalk_manifest()["commodityMappings"]
    }

    assert {
        "adult_general",
        "child_1_6",
        "adolescent_11_17",
        "older_adult_65_plus",
        "pregnant_adult",
    } <= population_groups
    assert {
        "apples",
        "oranges",
        "spinach",
        "tomatoes",
        "potatoes",
        "rice",
        "wheat",
        "milk",
        "chicken",
        "salmon",
        "eggs",
        "oats",
        "beans_and_pulses",
    } <= commodity_codes
    assert commodity_codes <= food_vocab_codes


def test_defaults_registry_falls_back_to_runtime_assets_outside_repo(tmp_path: Path) -> None:
    registry = DefaultsRegistry(tmp_path)

    assert registry.core_defaults["defaultsVersion"] == "v1"
    assert registry.model_governance_manifest()["families"]


def test_reference_value_conflicts_and_emerging_contaminant_registries_are_available() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])

    glyphosate_records = [
        item for item in registry.list_reference_value_records() if item["substanceKey"] == "glyphosate"
    ]
    acetamiprid_records = [
        item for item in registry.list_reference_value_records() if item["substanceKey"] == "acetamiprid"
    ]
    ethiprole_records = [
        item for item in registry.list_reference_value_records() if item["substanceKey"] == "ethiprole"
    ]
    tetraconazole_records = [
        item for item in registry.list_reference_value_records() if item["substanceKey"] == "tetraconazole"
    ]
    tebuconazole_records = [
        item for item in registry.list_reference_value_records() if item["substanceKey"] == "tebuconazole"
    ]
    glufosinate_records = [
        item for item in registry.list_reference_value_records() if item["substanceKey"] == "glufosinate"
    ]
    oxamyl_records = [
        item for item in registry.list_reference_value_records() if item["substanceKey"] == "oxamyl"
    ]
    difenoconazole_records = [
        item for item in registry.list_reference_value_records() if item["substanceKey"] == "difenoconazole"
    ]
    pfas_record = next(
        item
        for item in registry.list_reference_value_records()
        if item["recordId"] == "efsa.pfas.sum4.twi"
    )
    acrylamide_records = [
        item for item in registry.list_reference_value_records() if item["substanceKey"] == "acrylamide"
    ]
    bpa_record = next(
        item
        for item in registry.list_reference_value_records()
        if item["recordId"] == "efsa.bpa.tdi.2023"
    )
    cadmium_record = next(
        item
        for item in registry.list_reference_value_records()
        if item["recordId"] == "efsa.cadmium.twi.2009"
    )
    lead_records = [item for item in registry.list_reference_value_records() if item["substanceKey"] == "lead"]
    inorganic_arsenic_record = next(
        item
        for item in registry.list_reference_value_records()
        if item["recordId"] == "efsa.inorganic_arsenic.skin_cancer.bmdl05"
    )
    methylmercury_record = next(
        item
        for item in registry.list_reference_value_records()
        if item["recordId"] == "efsa.methylmercury.twi.2012"
    )
    inorganic_mercury_record = next(
        item
        for item in registry.list_reference_value_records()
        if item["recordId"] == "efsa.inorganic_mercury.twi.2012"
    )
    cadmium_occurrence = registry.get_metals_occurrence_record("efsa.cadmium.occurrence_monitoring.support")
    lead_occurrence = registry.get_metals_occurrence_record("efsa.lead.occurrence_monitoring.support")
    inorganic_arsenic_occurrence = registry.get_metals_occurrence_record(
        "efsa.inorganic_arsenic.occurrence_monitoring.support"
    )
    mercury_occurrence = registry.get_metals_occurrence_record("efsa.mercury.occurrence_monitoring.support")
    mercury_review_focus = registry.get_metals_review_focus_record("efsa.mercury.large_predatory_fish.review_focus")
    arsenic_review_focus = registry.get_metals_review_focus_record("efsa.inorganic_arsenic.rice_products.review_focus")
    mercury_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.mercury.occurrence_evidence.official_monitoring_context"
    )
    pfas_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.pfas.occurrence_evidence.food_monitoring_context"
    )
    pfas_egg_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.pfas.occurrence_evidence.eggs_monitoring_context"
    )
    pfas_fish_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.pfas.occurrence_evidence.fish_monitoring_context"
    )
    pfas_dairy_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.pfas.occurrence_evidence.milk_and_dairy_products_context"
    )
    acrylamide_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.acrylamide.occurrence_evidence.monitoring_context"
    )
    acrylamide_fried_potato_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.acrylamide.occurrence_evidence.fried_potato_products_context"
    )
    acrylamide_coffee_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.acrylamide.occurrence_evidence.coffee_products_context"
    )
    bpa_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.bpa.occurrence_evidence.canned_foods_context"
    )
    bpa_beverages_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.bpa.occurrence_evidence.beverages_context"
    )
    lead_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.lead.analytical_method_evidence.official_control"
    )
    bpa_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.bpa.analytical_method_evidence.food_contact_context"
    )
    bpa_canned_foods_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.bpa.analytical_method_evidence.canned_foods_context"
    )
    pfas_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.pfas.analytical_method_evidence.monitoring_context"
    )
    pfas_egg_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.pfas.analytical_method_evidence.eggs_monitoring_context"
    )
    pfas_fish_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.pfas.analytical_method_evidence.fish_monitoring_context"
    )
    pfas_dairy_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.pfas.analytical_method_evidence.milk_and_dairy_products_context"
    )
    acrylamide_fried_potato_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.acrylamide.analytical_method_evidence.fried_potato_products_context"
    )
    acrylamide_coffee_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.acrylamide.analytical_method_evidence.coffee_products_context"
    )
    glyphosate_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.glyphosate.occurrence_evidence.monitoring_context"
    )
    acetamiprid_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.acetamiprid.occurrence_evidence.monitoring_context"
    )
    imidacloprid_records = [
        item for item in registry.list_reference_value_records() if item["substanceKey"] == "imidacloprid"
    ]
    imidacloprid_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.imidacloprid.occurrence_evidence.monitoring_context"
    )
    ethiprole_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.ethiprole.occurrence_evidence.monitoring_context"
    )
    tetraconazole_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.tetraconazole.occurrence_evidence.monitoring_context"
    )
    tebuconazole_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.tebuconazole.occurrence_evidence.monitoring_context"
    )
    glufosinate_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.glufosinate.occurrence_evidence.monitoring_context"
    )
    oxamyl_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.oxamyl.occurrence_evidence.monitoring_context"
    )
    spirotetramat_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.spirotetramat.occurrence_evidence.monitoring_context"
    )
    difenoconazole_occurrence_evidence = registry.get_occurrence_evidence_record(
        "eu.difenoconazole.occurrence_evidence.monitoring_context"
    )
    glyphosate_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.glyphosate.analytical_method_evidence.monitoring_context"
    )
    acetamiprid_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.acetamiprid.analytical_method_evidence.monitoring_context"
    )
    imidacloprid_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.imidacloprid.analytical_method_evidence.monitoring_context"
    )
    ethiprole_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.ethiprole.analytical_method_evidence.monitoring_context"
    )
    tetraconazole_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.tetraconazole.analytical_method_evidence.monitoring_context"
    )
    tebuconazole_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.tebuconazole.analytical_method_evidence.monitoring_context"
    )
    glufosinate_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.glufosinate.analytical_method_evidence.monitoring_context"
    )
    oxamyl_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.oxamyl.analytical_method_evidence.monitoring_context"
    )
    spirotetramat_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.spirotetramat.analytical_method_evidence.monitoring_context"
    )
    difenoconazole_method_evidence = registry.get_analytical_method_evidence_record(
        "eu.difenoconazole.analytical_method_evidence.monitoring_context"
    )
    eu_pfas_reporting_profile = registry.get_reporting_profile_record("eu.pfas.efsa4.food_risk")
    nl_pfas_reporting_profile = registry.get_reporting_profile_record("nl.pfas.rivm_peq.food_advisory")
    nl_pfas_biota_reporting_profile = registry.get_reporting_profile_record("nl.pfas.rivm_peq.biota_fish_advisory")
    pfas_reporting_profiles = registry.get_reporting_profile_records_for_family("pfas_food_contaminants")
    microplastics = registry.get_emerging_contaminant_record("microplastics_emerging")
    pfas = registry.get_emerging_contaminant_record("pfas_food_contaminants")
    acrylamide = registry.get_emerging_contaminant_record("acrylamide_process_contaminants")
    bisphenol = registry.get_emerging_contaminant_record("bisphenol_food_contact_migration")
    cadmium = registry.get_emerging_contaminant_record("cadmium_food_contaminants")
    lead = registry.get_emerging_contaminant_record("lead_food_contaminants")
    inorganic_arsenic = registry.get_emerging_contaminant_record("inorganic_arsenic_food_contaminants")
    mercury = registry.get_emerging_contaminant_record("mercury_food_contaminants")

    assert {item["recordId"] for item in glyphosate_records} >= {
        "efsa.openfoodtox.glyphosate.adi",
        "jmpr.glyphosate.adi",
    }
    assert {item["recordId"] for item in acetamiprid_records} == {
        "efsa.openfoodtox.acetamiprid.adi",
        "efsa.openfoodtox.acetamiprid.arfd",
        "jmpr.acetamiprid.adi.2011",
        "cn.nhc.acetamiprid.adi.2026",
    }
    assert {item["recordId"] for item in ethiprole_records} == {
        "efsa.ethiprole.adi.2024",
        "efsa.ethiprole.arfd.2024",
    }
    assert {item["recordId"] for item in tetraconazole_records} == {
        "efsa.tetraconazole.adi.2019",
        "efsa.tetraconazole.arfd.2019",
    }
    assert {item["recordId"] for item in tebuconazole_records} == {
        "efsa.tebuconazole.adi.2013",
        "efsa.tebuconazole.arfd.2013",
    }
    assert {item["recordId"] for item in glufosinate_records} == {
        "efsa.glufosinate.adi.2007",
        "jmpr.glufosinate.adi.2012",
        "efsa.glufosinate.arfd.2007",
        "jmpr.glufosinate.arfd.2012",
        "cn.nhc.glufosinate.adi.2026",
    }
    assert {item["recordId"] for item in oxamyl_records} == {
        "efsa.oxamyl.adi.2023",
        "jmpr.oxamyl.adi.2012",
        "efsa.oxamyl.arfd.2023",
        "jmpr.oxamyl.arfd.2012",
        "cn.nhc.oxamyl.adi.2026",
    }
    assert {item["recordId"] for item in difenoconazole_records} == {
        "efsa.openfoodtox.difenoconazole.adi",
        "efsa.openfoodtox.difenoconazole.arfd",
        "jmpr.difenoconazole.arfd.2013",
    }
    assert {item["recordId"] for item in imidacloprid_records} == {
        "efsa.openfoodtox.imidacloprid.adi",
        "efsa.openfoodtox.imidacloprid.arfd",
        "jmpr.imidacloprid.adi.2001",
        "cn.nhc.imidacloprid.adi.2026",
    }
    assert pfas_record["value"] == 4.4
    assert {item["recordId"] for item in acrylamide_records} == {
        "efsa.acrylamide.neoplastic.bmdl10",
        "efsa.acrylamide.neurotoxicity.bmdl10",
    }
    assert bpa_record["value"] == 0.2
    assert cadmium_record["value"] == 2.5
    assert {item["recordId"] for item in lead_records} == {
        "efsa.lead.developmental_neurotoxicity.bmdl01",
        "efsa.lead.nephrotoxicity.bmdl10",
    }
    assert inorganic_arsenic_record["value"] == 0.06
    assert methylmercury_record["value"] == 1.3
    assert inorganic_mercury_record["value"] == 4.0
    assert cadmium_occurrence["datasetIds"] == ["efsa.comprehensive_food_consumption_db.cadmium_support"]
    assert cadmium_occurrence["referenceValueRecordIds"] == ["efsa.cadmium.twi.2009"]
    assert "potatoes" in cadmium_occurrence["highAttentionFoods"]
    assert lead_occurrence["legalAuthorityIds"] == [
        "eu.lead.contaminants.reg_2023_915",
        "eu.lead.official_control.reg_333_2007",
    ]
    assert "efsa.lead.exposure.2025" in lead_occurrence["sourceIds"]
    assert "game_meat" in lead_occurrence["highAttentionFoods"]
    assert inorganic_arsenic_occurrence["matrixScope"] == ["broad_food_supply", "rice_and_cereal_products"]
    assert "rice_and_rice_based_products" in inorganic_arsenic_occurrence["priorityFoodGroups"]
    assert mercury_occurrence["focusSubstances"] == ["methylmercury", "inorganic_mercury"]
    assert "efsa.mercury.fish_consumption.2026" in mercury_occurrence["sourceIds"]
    assert "swordfish" in mercury_occurrence["highAttentionFoods"]
    assert "women_who_are_pregnant_or_planning_pregnancy" in mercury_occurrence["sensitivePopulationGroups"]
    assert mercury_review_focus["linkedOccurrenceRecordIds"] == ["efsa.mercury.occurrence_monitoring.support"]
    assert "bigeye_tuna" in mercury_review_focus["focusFoods"]
    assert "rice_based_infant_foods" in arsenic_review_focus["focusFoods"]
    assert mercury_occurrence_evidence["methodEvidenceRecordIds"] == [
        "eu.mercury.analytical_method_evidence.official_control"
    ]
    assert "efsa.mercury.large_predatory_fish.review_focus" in mercury_occurrence_evidence["linkedReviewFocusIds"]
    assert pfas_occurrence_evidence["datasetIds"] == [
        "efsa.comprehensive_food_consumption_db.pfas_support",
        "ec.pfas_food_monitoring_2022_2025",
    ]
    assert pfas_occurrence_evidence["referenceValueRecordIds"] == ["efsa.pfas.sum4.twi"]
    assert pfas_occurrence_evidence["reportingProfileIds"] == [
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
    ]
    assert pfas_egg_occurrence_evidence["reportingProfileIds"] == [
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
    ]
    assert pfas_fish_occurrence_evidence["reportingProfileIds"] == [
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
    ]
    assert pfas_dairy_occurrence_evidence["reportingProfileIds"] == [
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
    ]
    assert pfas_method_evidence["reportingProfileIds"] == [
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
    ]
    assert pfas_egg_method_evidence["reportingProfileIds"] == [
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
    ]
    assert pfas_fish_method_evidence["reportingProfileIds"] == [
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
    ]
    assert pfas_dairy_method_evidence["reportingProfileIds"] == [
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
    ]
    assert acrylamide_occurrence_evidence["referenceValueRecordIds"] == [
        "efsa.acrylamide.neoplastic.bmdl10",
        "efsa.acrylamide.neurotoxicity.bmdl10",
    ]
    assert acrylamide_fried_potato_occurrence_evidence["matrixGroups"] == ["fried_potato_products"]
    assert acrylamide_coffee_occurrence_evidence["matrixGroups"] == ["coffee_and_coffee_substitutes"]
    assert acrylamide_fried_potato_method_evidence["methodIds"] == [
        "efsa.acrylamide.food.2015_opinion",
        "eu.acrylamide.mitigation.2017",
        "eu.acrylamide.monitoring.2019",
    ]
    assert acrylamide_coffee_method_evidence["methodIds"] == [
        "efsa.acrylamide.food.2015_opinion",
        "eu.acrylamide.mitigation.2017",
        "eu.acrylamide.monitoring.2019",
    ]
    assert lead_method_evidence["methodIds"] == [
        "eu.lead.official_control.333_2007",
        "efsa.lead.food.2010_opinion",
    ]
    assert lead_method_evidence["submissionUse"] == "allowed"
    assert bpa_method_evidence["methodIds"] == [
        "efsa.bpa.food.2023_opinion",
        "eu.bpa.fcm.2024_3190",
    ]
    assert bpa_method_evidence["submissionUse"] == "allowed"
    assert bpa_occurrence_evidence["matrixGroups"] == ["canned_foods"]
    assert bpa_beverages_occurrence_evidence["matrixGroups"] == ["beverages_and_drinks"]
    assert bpa_canned_foods_method_evidence["methodIds"] == [
        "efsa.bpa.food.2023_opinion",
        "eu.bpa.fcm.2024_3190",
    ]
    assert registry.get_analytical_method_evidence_record(
        "eu.bpa.analytical_method_evidence.beverages_context"
    )["methodIds"] == [
        "efsa.bpa.food.2023_opinion",
        "eu.bpa.fcm.2024_3190",
    ]
    assert glyphosate_occurrence_evidence["datasetIds"] == [
        "efsa.comprehensive_food_consumption_db",
        "efsa.eu_menu_programme",
    ]
    assert glyphosate_occurrence_evidence["referenceValueRecordIds"] == [
        "efsa.openfoodtox.glyphosate.adi",
        "efsa.openfoodtox.glyphosate.arfd",
    ]
    assert acetamiprid_occurrence_evidence["referenceValueRecordIds"] == [
        "efsa.openfoodtox.acetamiprid.adi",
        "efsa.openfoodtox.acetamiprid.arfd",
    ]
    assert "efsa.acetamiprid.statement.2024" in acetamiprid_occurrence_evidence["sourceIds"]
    assert imidacloprid_occurrence_evidence["referenceValueRecordIds"] == [
        "efsa.openfoodtox.imidacloprid.adi",
        "efsa.openfoodtox.imidacloprid.arfd",
    ]
    assert "efsa.pesticide_residues.organic_findings.2025" in imidacloprid_occurrence_evidence["sourceIds"]
    assert ethiprole_occurrence_evidence["referenceValueRecordIds"] == [
        "efsa.ethiprole.adi.2024",
        "efsa.ethiprole.arfd.2024",
    ]
    assert "efsa.ethiprole.trv.2024" in ethiprole_occurrence_evidence["sourceIds"]
    assert "rice" in ethiprole_occurrence_evidence["matrixGroups"]
    assert tetraconazole_occurrence_evidence["referenceValueRecordIds"] == [
        "efsa.tetraconazole.adi.2019",
        "efsa.tetraconazole.arfd.2019",
    ]
    assert "efsa.tetraconazole.mrl_opinion.2019" in tetraconazole_occurrence_evidence["sourceIds"]
    assert "linseeds" in tetraconazole_occurrence_evidence["matrixGroups"]
    assert tebuconazole_occurrence_evidence["referenceValueRecordIds"] == [
        "efsa.tebuconazole.adi.2013",
        "efsa.tebuconazole.arfd.2013",
    ]
    assert "efsa.tebuconazole.mrl_opinion.2013" in tebuconazole_occurrence_evidence["sourceIds"]
    assert "poppy_seeds" in tebuconazole_occurrence_evidence["matrixGroups"]
    assert glufosinate_occurrence_evidence["referenceValueRecordIds"] == [
        "efsa.glufosinate.adi.2007",
        "jmpr.glufosinate.adi.2012",
        "efsa.glufosinate.arfd.2007",
        "jmpr.glufosinate.arfd.2012",
    ]
    assert "efsa.glufosinate.call_for_data.2024" in glufosinate_occurrence_evidence["sourceIds"]
    assert "soya_beans" in glufosinate_occurrence_evidence["matrixGroups"]
    assert oxamyl_occurrence_evidence["referenceValueRecordIds"] == [
        "efsa.oxamyl.adi.2023",
        "jmpr.oxamyl.adi.2012",
        "efsa.oxamyl.arfd.2023",
        "jmpr.oxamyl.arfd.2012",
    ]
    assert "efsa.oxamyl.statement.2023" in oxamyl_occurrence_evidence["sourceIds"]
    assert "potatoes" in oxamyl_occurrence_evidence["matrixGroups"]
    assert difenoconazole_occurrence_evidence["referenceValueRecordIds"] == [
        "efsa.openfoodtox.difenoconazole.adi",
        "efsa.openfoodtox.difenoconazole.arfd",
        "jmpr.difenoconazole.arfd.2013",
    ]
    assert "efsa.difenoconazole.import_tolerance.2025" in difenoconazole_occurrence_evidence["sourceIds"]
    assert "wheat_and_rye" in difenoconazole_occurrence_evidence["matrixGroups"]
    assert glyphosate_method_evidence["methodIds"] == [
        "oecd.analytical_methods.guidance",
        "oecd.residue_definition.guidance",
        "efsa.pesticide_residues.2023_annual_report",
        "efsa.pesticide_residues.2023_national_summary",
    ]
    assert glyphosate_method_evidence["submissionUse"] == "review_required"
    assert "efsa.acetamiprid.statement.2024" in acetamiprid_method_evidence["sourceIds"]
    assert acetamiprid_method_evidence["legalAuthorityIds"] == [
        "eu.pesticide_residues.reg_396_2005",
        "eu.active_substances.reg_283_2013",
    ]
    assert "efsa.imidacloprid.dnt.2013" in imidacloprid_method_evidence["sourceIds"]
    assert "efsa.pesticide_residues.organic_findings.2025" in imidacloprid_method_evidence["sourceIds"]
    assert ethiprole_method_evidence["methodIds"] == [
        "oecd.analytical_methods.guidance",
        "oecd.residue_definition.guidance",
        "efsa.ethiprole.residue_definitions_and_trv.2024",
    ]
    assert ethiprole_method_evidence["submissionUse"] == "review_required"
    assert tetraconazole_method_evidence["methodIds"] == [
        "oecd.analytical_methods.guidance",
        "oecd.residue_definition.guidance",
        "efsa.tetraconazole.mrl_review.2019",
    ]
    assert tetraconazole_method_evidence["submissionUse"] == "review_required"
    assert tebuconazole_method_evidence["methodIds"] == [
        "oecd.analytical_methods.guidance",
        "oecd.residue_definition.guidance",
        "efsa.tebuconazole.mrl_review.2013",
    ]
    assert tebuconazole_method_evidence["submissionUse"] == "review_required"
    assert glufosinate_method_evidence["methodIds"] == [
        "oecd.analytical_methods.guidance",
        "oecd.residue_definition.guidance",
        "efsa.glufosinate.mrl_review.2015",
    ]
    assert "jmpr.glufosinate.summary.2013" in glufosinate_method_evidence["sourceIds"]
    assert glufosinate_method_evidence["submissionUse"] == "review_required"
    assert oxamyl_method_evidence["methodIds"] == [
        "oecd.analytical_methods.guidance",
        "oecd.residue_definition.guidance",
        "efsa.oxamyl.peer_review.2022",
    ]
    assert "jmpr.oxamyl.summary.2012" in oxamyl_method_evidence["sourceIds"]
    assert oxamyl_method_evidence["submissionUse"] == "review_required"
    assert spirotetramat_occurrence_evidence["methodEvidenceRecordIds"] == [
        "eu.spirotetramat.analytical_method_evidence.monitoring_context"
    ]
    assert "efsa.spirotetramat.mrl_opinion.2022" in spirotetramat_occurrence_evidence["sourceIds"]
    assert spirotetramat_method_evidence["methodIds"] == [
        "oecd.analytical_methods.guidance",
        "oecd.residue_definition.guidance",
        "efsa.spirotetramat.mrl_review.2022",
    ]
    assert "jmpr.spirotetramat.report.2013" in spirotetramat_method_evidence["sourceIds"]
    assert difenoconazole_method_evidence["methodIds"] == [
        "oecd.analytical_methods.guidance",
        "oecd.residue_definition.guidance",
        "efsa.difenoconazole.mrl_review.2025",
    ]
    assert "jmpr.difenoconazole.report.2013" in difenoconazole_method_evidence["sourceIds"]
    assert eu_pfas_reporting_profile["profileRole"] == "primary_regulatory"
    assert eu_pfas_reporting_profile["referenceValueRecordIds"] == ["efsa.pfas.sum4.twi"]
    assert nl_pfas_reporting_profile["profileRole"] == "national_advisory_optional"
    assert nl_pfas_reporting_profile["matrixGroups"] == ["eggs"]
    assert nl_pfas_reporting_profile["reportedUnit"] == "ng/kg PFOA-equivalent"
    assert nl_pfas_reporting_profile["notSubstitutableForProfileIds"] == [
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
    ]
    assert nl_pfas_biota_reporting_profile["profileRole"] == "national_advisory_optional"
    assert nl_pfas_biota_reporting_profile["matrixGroups"] == ["fish_and_seafood"]
    assert "rivm.pfas.peq_tool.v3.2025" in nl_pfas_biota_reporting_profile["sourceIds"]
    assert {item["profileId"] for item in pfas_reporting_profiles} == {
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
        "nl.pfas.rivm_peq.food_advisory",
        "nl.pfas.rivm_peq.biota_fish_advisory",
    }
    assert microplastics["submissionUse"] == "not_allowed"
    assert pfas["submissionUse"] == "review_required"
    assert acrylamide["submissionUse"] == "allowed"
    assert bisphenol["submissionUse"] == "allowed"
    assert cadmium["submissionUse"] == "allowed"
    assert lead["submissionUse"] == "allowed"
    assert inorganic_arsenic["submissionUse"] == "allowed"
    assert mercury["submissionUse"] == "allowed"


def test_processed_commodity_mapping_drives_resolution_and_default_processing_factor() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])

    resolution = registry.resolve_commodity("apple_juice")
    processing_factor, source_reference = registry.default_processing_factor("apple_juice")

    assert resolution.commodity.commodity_code == "apples"
    assert resolution.commodity.foodex2_code == "EXAMPLE_FDX2_APPLE_JUICE"
    assert resolution.commodity.processed_status.value == "processed_derivative"
    assert processing_factor == 0.65
    assert source_reference.source_id == "dietary.food_vocab.processed.apple_juice"


def test_wave1_jurisdiction_expansion_records_are_available() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])

    us_source = registry.get_source_catalog_record("us.govinfo.cfr.40_180.472.2024")
    codex_source = registry.get_source_catalog_record("codex.pesticide_database.2024")
    codex_contaminant_source = registry.get_source_catalog_record("codex.cxs_193_1995.current_2025")
    china_source = registry.get_source_catalog_record("cn.nhc.gb2763.2026.announcement")
    us_authority = registry.get_legal_authority_record("us.epa.pesticides.40cfr_part_180.govinfo_2024")
    codex_authority = registry.get_legal_authority_record("codex.cccf.cxs_193_1995.current_2025.cadmium")
    china_authority = registry.get_legal_authority_record("cn.nhc.pesticides.gb_2763_2026")
    codex_reference = registry.get_reference_value_record("jmpr.imidacloprid.adi.2001")
    china_reference = registry.get_reference_value_record("cn.nhc.acetamiprid.adi.2026")
    us_mrl = registry.get_mrl_record("imidacloprid", "grapes", "us")
    codex_mrl = registry.get_mrl_record("acetamiprid", "grapes", "codex_global")
    china_mrl = registry.get_mrl_record("acetamiprid", "grapes", "cn")

    assert us_source["originTag"] == "official_regulatory"
    assert codex_source["documentStatus"] == "final_current"
    assert codex_contaminant_source["effectiveDate"] == "2025-11-10"
    assert china_source["effectiveDate"] == "2026-02-26"
    assert us_authority["sourceId"] == "us.govinfo.cfr.40_180.part.2024"
    assert codex_authority["sourceId"] == "codex.cxs_193_1995.current_2025"
    assert china_authority["sourceId"] == "cn.nhc.gb2763.2026.announcement"
    assert codex_reference["jurisdiction"] == "codex_global"
    assert china_reference["effectiveDate"] == "2026-03-01"
    assert us_mrl is not None and us_mrl["recordId"] == "us.epa.imidacloprid.grapes.mrl"
    assert codex_mrl is not None and codex_mrl["recordId"] == "codex.acetamiprid.grapes.mrl"
    assert china_mrl is not None and china_mrl["recordId"] == "cn.gb.acetamiprid.grapes.mrl"


def test_wave1_jurisdiction_coverage_registry_is_available() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])

    us_glyphosate = registry.get_jurisdiction_coverage_record("us.pesticide_residue.glyphosate.wave1")
    codex_cadmium = registry.get_jurisdiction_coverage_record("codex_global.cadmium_food_contaminants.cadmium.wave1")
    china_lead = registry.get_jurisdiction_coverage_record("cn.lead_food_contaminants.lead.wave1")
    us_lead_limit = registry.get_contaminant_legal_limit_record("us.fda.lead.processed_foods.general_baby_foods.ml.2025")
    china_arsenic_limit = registry.get_contaminant_legal_limit_record("cn.nhc.inorganic_arsenic.rice.ml.2025")

    assert us_glyphosate["coverageLevel"] == "deep_curated"
    assert "us.epa.glyphosate.rice.mrl" in us_glyphosate["enforcementRecordIds"]
    assert codex_cadmium["coverageLevel"] == "deep_curated"
    assert codex_cadmium["legalAuthorityIds"] == ["codex.cccf.cxs_193_1995.current_2025.cadmium"]
    assert codex_cadmium["officialSourceIds"] == ["codex.cxs_193_1995.current_2025"]
    assert codex_cadmium["legalLimitRecordIds"] == ["codex.cxs_193_1995.cadmium.wheat.ml.2025"]
    assert china_lead["coverageLevel"] == "deep_curated"
    assert china_lead["officialSourceIds"] == ["cn.nhc.gb2762.2025.announcement", "cn.cfsa.gb2762.2025.standard_text"]
    assert "cn.nhc.lead.infant_formula.ml.2025" in china_lead["legalLimitRecordIds"]
    assert us_lead_limit["limitValue"] == 0.01
    assert us_lead_limit["commodityCodes"] == ["purees"]
    assert china_arsenic_limit["effectiveDate"] == "2026-09-02"
    assert china_arsenic_limit["commodityCodes"] == ["rice"]


def test_duplicate_model_governance_entries_fail(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "model_governance.json").read_text())
    payload["families"].append(payload["families"][0])
    (tmp_path / "defaults" / "v1" / "model_governance.json").write_text(json.dumps(payload, indent=2) + "\n")

    with pytest.raises(DietaryRegistryError):
        DefaultsRegistry(tmp_path)


def test_unknown_reference_value_source_fails(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "reference_values.json").read_text())
    payload["records"][0]["sourceIds"].append("missing.source.record")
    (tmp_path / "defaults" / "v1" / "reference_values.json").write_text(json.dumps(payload, indent=2) + "\n")

    with pytest.raises(DietaryRegistryError):
        DefaultsRegistry(tmp_path)


def test_wave1_source_pack_rejects_non_official_origin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "source_catalog_jurisdiction_wave1.json").read_text())
    payload["sources"][0]["originTag"] = "curated_derived"
    (tmp_path / "defaults" / "v1" / "source_catalog_jurisdiction_wave1.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    monkeypatch.setenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", "1")
    with pytest.raises(DietaryRegistryError) as exc_info:
        DefaultsRegistry(tmp_path)
    assert exc_info.value.payload.code == "invalid_wave1_source_origin"


def test_wave1_reference_value_pack_requires_effective_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "reference_values_jurisdiction_wave1.json").read_text())
    payload["records"][0].pop("effectiveDate", None)
    (tmp_path / "defaults" / "v1" / "reference_values_jurisdiction_wave1.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    monkeypatch.setenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", "1")
    with pytest.raises(DietaryRegistryError) as exc_info:
        DefaultsRegistry(tmp_path)
    assert exc_info.value.payload.code == "missing_wave1_reference_value_effective_date"


def test_wave1_legal_authority_pack_requires_official_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "legal_authorities_jurisdiction_wave1.json").read_text())
    payload["authorities"][0]["sourceId"] = "dietary.profile.eu_adult_general"
    (tmp_path / "defaults" / "v1" / "legal_authorities_jurisdiction_wave1.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    monkeypatch.setenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", "1")
    with pytest.raises(DietaryRegistryError) as exc_info:
        DefaultsRegistry(tmp_path)
    assert exc_info.value.payload.code == "invalid_wave1_legal_authority_source"


def test_wave1_mrl_pack_requires_effective_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "mrl_enforcement_jurisdiction_wave1.json").read_text())
    payload["records"][0].pop("effectiveDate", None)
    (tmp_path / "defaults" / "v1" / "mrl_enforcement_jurisdiction_wave1.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    monkeypatch.setenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", "1")
    with pytest.raises(DietaryRegistryError) as exc_info:
        DefaultsRegistry(tmp_path)
    assert exc_info.value.payload.code == "missing_wave1_mrl_effective_date"


def test_wave1_mrl_pack_requires_official_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "mrl_enforcement_jurisdiction_wave1.json").read_text())
    payload["records"][0]["sourceIds"] = ["dietary.profile.eu_adult_general"]
    (tmp_path / "defaults" / "v1" / "mrl_enforcement_jurisdiction_wave1.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    monkeypatch.setenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", "1")
    with pytest.raises(DietaryRegistryError) as exc_info:
        DefaultsRegistry(tmp_path)
    assert exc_info.value.payload.code == "invalid_wave1_mrl_source"


def test_jurisdiction_coverage_pack_rejects_unknown_legal_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "jurisdiction_coverage_wave1.json").read_text())
    payload["records"][0]["legalAuthorityIds"] = ["missing.legal.authority"]
    (tmp_path / "defaults" / "v1" / "jurisdiction_coverage_wave1.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    monkeypatch.setenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", "1")
    with pytest.raises(DietaryRegistryError) as exc_info:
        DefaultsRegistry(tmp_path)
    assert exc_info.value.payload.code == "unknown_jurisdiction_coverage_legal_authority"


def test_jurisdiction_coverage_pack_rejects_unknown_legal_limit_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "jurisdiction_coverage_wave1.json").read_text())
    payload["records"][0]["legalLimitRecordIds"] = ["missing.legal.limit"]
    (tmp_path / "defaults" / "v1" / "jurisdiction_coverage_wave1.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    monkeypatch.setenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", "1")
    with pytest.raises(DietaryRegistryError) as exc_info:
        DefaultsRegistry(tmp_path)
    assert exc_info.value.payload.code == "unknown_jurisdiction_coverage_legal_limit_record"


def test_wave2_contaminant_legal_limit_pack_requires_effective_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "contaminant_legal_limits_wave2.json").read_text())
    payload["records"][0].pop("effectiveDate", None)
    (tmp_path / "defaults" / "v1" / "contaminant_legal_limits_wave2.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    monkeypatch.setenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", "1")
    with pytest.raises(DietaryRegistryError) as exc_info:
        DefaultsRegistry(tmp_path)
    assert exc_info.value.payload.code == "missing_official_primary_contaminant_legal_limit_effective_date"


def test_duplicate_active_wave1_mrl_records_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "mrl_enforcement_jurisdiction_wave1.json").read_text())
    duplicate = dict(payload["records"][0])
    duplicate["recordId"] = "us.epa.imidacloprid.apples.duplicate.mrl"
    payload["records"].append(duplicate)
    (tmp_path / "defaults" / "v1" / "mrl_enforcement_jurisdiction_wave1.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    monkeypatch.setenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", "1")
    with pytest.raises(DietaryRegistryError) as exc_info:
        DefaultsRegistry(tmp_path)
    assert exc_info.value.payload.code == "duplicate_active_mrl_enforcement_record"


def test_unknown_metals_occurrence_method_fails(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "metals_occurrence_registry.json").read_text())
    payload["records"][0]["methodIds"].append("missing.metals.method")
    (tmp_path / "defaults" / "v1" / "metals_occurrence_registry.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    with pytest.raises(DietaryRegistryError):
        DefaultsRegistry(tmp_path)


def test_unknown_metals_occurrence_reference_value_fails(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "metals_occurrence_registry.json").read_text())
    payload["records"][0]["referenceValueRecordIds"].append("missing.reference.value")
    (tmp_path / "defaults" / "v1" / "metals_occurrence_registry.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    with pytest.raises(DietaryRegistryError):
        DefaultsRegistry(tmp_path)


def test_unknown_metals_review_focus_occurrence_record_fails(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "metals_review_focus_registry.json").read_text())
    payload["records"][0]["linkedOccurrenceRecordIds"].append("missing.metals.occurrence")
    (tmp_path / "defaults" / "v1" / "metals_review_focus_registry.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    with pytest.raises(DietaryRegistryError):
        DefaultsRegistry(tmp_path)


def test_unknown_occurrence_evidence_review_focus_fails(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "occurrence_evidence_registry.json").read_text())
    payload["records"][0]["linkedReviewFocusIds"].append("missing.review.focus")
    (tmp_path / "defaults" / "v1" / "occurrence_evidence_registry.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    with pytest.raises(DietaryRegistryError):
        DefaultsRegistry(tmp_path)


def test_unknown_analytical_method_evidence_method_fails(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    payload = json.loads((tmp_path / "defaults" / "v1" / "analytical_method_evidence_registry.json").read_text())
    payload["records"][0]["methodIds"].append("missing.method.evidence")
    (tmp_path / "defaults" / "v1" / "analytical_method_evidence_registry.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    with pytest.raises(DietaryRegistryError):
        DefaultsRegistry(tmp_path)


def test_manifest_verification_passes_for_intact_defaults(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    # Should not raise
    registry = DefaultsRegistry(tmp_path)
    assert registry.core_defaults


def test_manifest_verification_fails_on_hash_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", raising=False)
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    core_path = tmp_path / "defaults" / "v1" / "core_defaults.json"
    payload = json.loads(core_path.read_text())
    payload["projectName"] = "tampered"
    core_path.write_text(json.dumps(payload, indent=2) + "\n")

    with pytest.raises(DietaryRegistryError) as exc_info:
        DefaultsRegistry(tmp_path)
    assert exc_info.value.payload.code == "defaults_integrity_mismatch"


def test_manifest_verification_can_be_skipped_via_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")
    core_path = tmp_path / "defaults" / "v1" / "core_defaults.json"
    payload = json.loads(core_path.read_text())
    payload["projectName"] = "tampered"
    core_path.write_text(json.dumps(payload, indent=2) + "\n")

    monkeypatch.setenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", "1")
    # Should not raise despite the hash mismatch
    registry = DefaultsRegistry(tmp_path)
    assert registry.core_defaults["projectName"] == "tampered"
