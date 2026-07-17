import json
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp import FastMCP

from dietary_mcp.server import create_server
from dietary_mcp.server_tools import register_tools


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.anyio
async def test_server_surface_exposes_expected_tools_and_resources() -> None:
    server = create_server()
    tools = await server.list_tools()
    resources = await server.list_resources()
    templates = await server.list_resource_templates()

    assert {tool.name for tool in tools} == {
        "dietary_build_residue_profile",
        "dietary_select_consumption_profile",
        "dietary_build_dietary_intake_scenario",
        "dietary_build_bounded_intake_summary",
        "dietary_compare_dietary_scenarios",
        "dietary_assess_residue_evidence_fit",
        "dietary_apply_residue_evidence",
        "dietary_reconcile_residue_evidence",
        "dietary_evaluate_global_trade_risk",
        "dietary_parse_raw_survey_dataset",
        "dietary_summarize_survey_distribution",
        "dietary_build_probabilistic_intake_summary",
        "dietary_build_uncertainty_intake_assessment",
        "dietary_check_adapter_import",
        "dietary_check_contaminant_monitoring_import",
        "dietary_compare_adapter_import_to_walkthrough",
        "dietary_export_adapter_review_bundle",
        "dietary_export_trade_risk_review_bundle",
        "dietary_export_contaminant_monitoring_interpretation_bundle",
        "dietary_export_contaminant_monitoring_signoff_packet",
        "dietary_export_version_pinned_contaminant_monitoring_review_dossier",
        "dietary_export_version_pinned_adapter_review_dossier",
        "dietary_export_version_pinned_trade_risk_review_dossier",
        "dietary_export_sanitised_public_review_dossier",
        "dietary_export_interoperability_preview",
        "dietary_assess_interoperability_preview_readiness",
        "dietary_export_interoperability_remediation_bundle",
        "dietary_export_interoperability_signoff_packet",
        "dietary_assess_review_dossier_readiness",
        "dietary_export_scientific_follow_up_queue_bundle",
        "dietary_export_scientific_follow_up_review_board",
        "dietary_export_scientific_follow_up_owner_handoff_packet",
        "dietary_export_scientific_follow_up_owner_remediation_packet",
        "dietary_export_scientific_follow_up_owner_signoff_packet",
        "dietary_export_version_pinned_scientific_follow_up_owner_signoff_dossier",
        "dietary_lookup_reference_values",
        "dietary_lookup_contaminant_legal_limits",
        "dietary_lookup_method_support",
        "dietary_lookup_consumption_dataset_support",
        "dietary_lookup_reporting_profiles",
        "dietary_lookup_occurrence_evidence",
        "dietary_lookup_analytical_method_evidence",
        "dietary_lookup_metals_occurrence",
        "dietary_lookup_metals_review_focus",
        "dietary_export_metals_monitoring_interpretation_bundle",
        "dietary_export_metals_monitoring_signoff_packet",
        "dietary_export_version_pinned_metals_monitoring_review_dossier",
        "dietary_export_pbpk_oral_input",
        "dietary_export_toxclaw_dietary_evidence_bundle",
    }
    assert len(tools) == 49
    assert all(tool.title for tool in tools)
    assert all(tool.outputSchema for tool in tools)
    assert all(tool.annotations is not None for tool in tools)
    assert all(tool.annotations.readOnlyHint is not None for tool in tools)
    assert all(tool.annotations.destructiveHint is False for tool in tools)
    assert all(tool.annotations.openWorldHint is False for tool in tools)
    # All current tools return deterministic data transformations. Even the
    # export tools build payloads in memory and do not write or publish them.
    assert all(tool.annotations.readOnlyHint is True for tool in tools)
    assert all(tool.annotations.idempotentHint is True for tool in tools)
    assert {str(resource.uri) for resource in resources} == {
        "adapter-manifest://manifest",
        "adapter-input-templates://manifest",
        "adapter-import-walkthroughs://manifest",
        "contracts://manifest",
        "defaults://manifest",
        "source-catalog://manifest",
        "reference-values://manifest",
        "mrl-enforcement://manifest",
        "contaminant-legal-limits://manifest",
        "consumption-datasets://manifest",
        "method-registry://manifest",
        "legal-authorities://manifest",
        "reporting-profiles://manifest",
        "occurrence-evidence://manifest",
        "analytical-method-evidence://manifest",
        "metals-occurrence://manifest",
        "metals-review-focus://manifest",
        "emerging-contaminants://manifest",
        "jurisdiction-coverage://manifest",
        "model-governance://manifest",
        "consumption-profiles://manifest",
        "commodity-taxonomy://manifest",
        "food-vocabulary://manifest",
        "interoperability://manifest",
        "interoperability-readiness://manifest",
        "interoperability-remediation://catalog",
        "validation://manifest",
        "validation://interoperability-rules",
        "validation://interoperability-readiness-profiles",
        "validation://interoperability-remediation-actions",
        "validation://regulatory-rules",
        "validation://sanitisation-rules",
        "validation://interoperability-profiles",
        "validation://readiness-profiles",
    }
    assert {str(template.uriTemplate) for template in templates} == {
        "schemas://{schema_name}",
        "examples://{example_name}",
        "docs://{doc_name}",
        "adapter-template://{template_name}",
        "adapter-walkthrough://{walkthrough_name}",
        "release://{report_name}",
        "validation://artifact/{artifact_name}",
        "source-catalog://source/{source_id}",
        "reference-values://substance/{substance_key}",
        "mrl-enforcement://record/{record_id}",
        "mrl-enforcement://substance/{substance_key}",
        "contaminant-legal-limits://record/{record_id}",
        "contaminant-legal-limits://jurisdiction/{jurisdiction}",
        "contaminant-legal-limits://family/{family_id}",
        "consumption-datasets://dataset/{dataset_id}",
        "method-registry://method/{method_id}",
        "legal-authorities://authority/{authority_id}",
        "reporting-profiles://profile/{profile_id}",
        "reporting-profiles://family/{family_id}",
        "occurrence-evidence://family/{family_id}",
        "analytical-method-evidence://family/{family_id}",
        "metals-occurrence://family/{family_id}",
        "metals-review-focus://family/{family_id}",
        "emerging-contaminants://family/{family_id}",
        "jurisdiction-coverage://coverage/{coverage_id}",
        "jurisdiction-coverage://jurisdiction/{jurisdiction}",
        "model-governance://family/{model_family}",
        "food-vocabulary://commodity/{commodity_code}",
        "food-vocabulary://processed/{processed_commodity_code}",
        "interoperability://profile/{profile_id}",
        "interoperability-readiness://profile/{profile_id}",
        "interoperability-remediation://action/{action_id}",
    }


def test_create_server_does_not_rewrite_generated_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    schema_manifest = repo_root / "docs" / "contracts" / "schemas" / "manifest.json"
    before_mtime = schema_manifest.stat().st_mtime_ns
    before_content = schema_manifest.read_bytes()

    create_server()

    assert schema_manifest.stat().st_mtime_ns == before_mtime
    assert schema_manifest.read_bytes() == before_content


@pytest.mark.anyio
async def test_tool_success_and_domain_error_use_structured_content() -> None:
    server = create_server()

    ok_content, ok_structured = await server.call_tool(
        "dietary_lookup_reference_values",
        {"request": {"substanceKey": "glyphosate"}},
    )
    assert ok_content
    assert ok_structured["result"]["substanceKey"] == "glyphosate"

    error = await server.call_tool(
        "dietary_select_consumption_profile",
        {"request": {"population_group": "not_a_population", "intake_window": "chronic"}},
    )
    assert error.isError is True
    assert error.structuredContent["result"]["code"] == "missing_consumption_profile"
    assert "requestId" in error.structuredContent["result"]["details"]


@pytest.mark.anyio
async def test_uncertainty_tool_success_and_domain_error_are_structured() -> None:
    from dietary_mcp.models import (
        BuildDietaryResidueProfileRequest,
        BuildUncertaintyIntakeAssessmentRequest,
        DietaryCommodityResidueInput,
        ParseRawSurveyDatasetRequest,
        RawSurveyRecordInput,
        ResidueSourceType,
        ResidueUncertaintyModel,
    )
    from dietary_mcp.runtime import DietaryRuntime

    repo_root = Path(__file__).resolve().parents[1]
    runtime = DietaryRuntime(repo_root)
    dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest(
            datasetId="server_uncertainty",
            regionId="eu",
            populationGroup="adult_general",
            rawRecords=[
                RawSurveyRecordInput(
                    subjectId="s1",
                    bodyWeightKg=70.0,
                    daysInSurvey=1,
                    commodityCode="apples",
                    consumptionKgPerDay=0.3,
                ),
                RawSurveyRecordInput(
                    subjectId="s2",
                    bodyWeightKg=70.0,
                    daysInSurvey=1,
                    commodityCode="apples",
                    consumptionKgPerDay=0.0,
                ),
            ],
        )
    )
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "ServerUncertainty"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.2,
                    source_type=ResidueSourceType.MONITORING,
                )
            ],
        )
    )

    server = create_server()
    ok_request = BuildUncertaintyIntakeAssessmentRequest(
        dataset=dataset,
        residue_profile=residue_profile,
        randomSeed=23,
        outerIterationCount=10,
        innerIterationCount=20,
        residueUncertaintyModels=[
            ResidueUncertaintyModel(
                commodityCode="apples",
                distribution="point",
                pointMgPerKg=0.2,
            )
        ],
    )
    ok_content, ok_structured = await server.call_tool(
        "dietary_build_uncertainty_intake_assessment",
        {"request": ok_request.model_dump(mode="json", by_alias=True)},
    )

    assert ok_content
    assert ok_structured["result"]["assessmentMode"] == "two_dimensional_monte_carlo"
    assert ok_structured["result"]["reproducibility"]["rngAlgorithm"] == "numpy.PCG64"

    bad_request = ok_request.model_copy(
        update={
            "residue_uncertainty_models": [
                ResidueUncertaintyModel(
                    commodityCode="rice",
                    distribution="point",
                    pointMgPerKg=0.1,
                )
            ]
        }
    )
    error = await server.call_tool(
        "dietary_build_uncertainty_intake_assessment",
        {"request": bad_request.model_dump(mode="json", by_alias=True)},
    )

    assert error.isError is True
    assert error.structuredContent["result"]["code"] == "uncertainty_model_without_residue_record"


@pytest.mark.anyio
async def test_unexpected_tool_exceptions_still_raise() -> None:
    class ExplodingRuntime:
        def lookup_reference_values(self, request):
            raise RuntimeError("boom")

    server = FastMCP("test-dietary-tools")
    register_tools(server, ExplodingRuntime())

    with pytest.raises(ToolError, match="boom"):
        await server.call_tool(
            "dietary_lookup_reference_values",
            {"request": {"substanceKey": "glyphosate"}},
        )


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.anyio
async def test_server_resources_are_readable() -> None:
    server = create_server()

    adapter_manifest = list(await server.read_resource("adapter-manifest://manifest"))
    adapter_templates = list(await server.read_resource("adapter-input-templates://manifest"))
    adapter_walkthroughs = list(await server.read_resource("adapter-import-walkthroughs://manifest"))
    contracts = list(await server.read_resource("contracts://manifest"))
    defaults = list(await server.read_resource("defaults://manifest"))
    source_catalog = list(await server.read_resource("source-catalog://manifest"))
    reference_values = list(await server.read_resource("reference-values://manifest"))
    contaminant_legal_limits = list(await server.read_resource("contaminant-legal-limits://manifest"))
    consumption_datasets = list(await server.read_resource("consumption-datasets://manifest"))
    method_registry = list(await server.read_resource("method-registry://manifest"))
    legal_authorities = list(await server.read_resource("legal-authorities://manifest"))
    reporting_profiles = list(await server.read_resource("reporting-profiles://manifest"))
    occurrence_evidence = list(await server.read_resource("occurrence-evidence://manifest"))
    analytical_method_evidence = list(await server.read_resource("analytical-method-evidence://manifest"))
    metals_occurrence = list(await server.read_resource("metals-occurrence://manifest"))
    metals_review_focus = list(await server.read_resource("metals-review-focus://manifest"))
    emerging_contaminants = list(await server.read_resource("emerging-contaminants://manifest"))
    jurisdiction_coverage = list(await server.read_resource("jurisdiction-coverage://manifest"))
    model_governance = list(await server.read_resource("model-governance://manifest"))
    food_vocabulary = list(await server.read_resource("food-vocabulary://manifest"))
    validation_manifest = list(await server.read_resource("validation://manifest"))
    interoperability_rules = list(await server.read_resource("validation://interoperability-rules"))
    interoperability_readiness_profiles = list(
        await server.read_resource("validation://interoperability-readiness-profiles")
    )
    interoperability_remediation_actions = list(
        await server.read_resource("validation://interoperability-remediation-actions")
    )
    regulatory_rules = list(await server.read_resource("validation://regulatory-rules"))
    sanitisation_rules = list(await server.read_resource("validation://sanitisation-rules"))
    interoperability_profiles = list(await server.read_resource("validation://interoperability-profiles"))
    readiness_profiles = list(await server.read_resource("validation://readiness-profiles"))
    source_database_cases = list(await server.read_resource("validation://artifact/source_database_cases"))
    contaminant_monitoring_cases = list(
        await server.read_resource("validation://artifact/contaminant_monitoring_check_cases")
    )
    contaminant_monitoring_bundle_cases = list(
        await server.read_resource("validation://artifact/contaminant_monitoring_bundle_cases")
    )
    contaminant_monitoring_signoff_cases = list(
        await server.read_resource("validation://artifact/contaminant_monitoring_signoff_cases")
    )
    contaminant_monitoring_review_dossier_cases = list(
        await server.read_resource("validation://artifact/contaminant_monitoring_review_dossier_cases")
    )
    mapping_gap_report = list(await server.read_resource("validation://artifact/commodity_mapping_gap_report"))
    primo_template = list(await server.read_resource("adapter-template://efsa_primo_tabular_template"))
    primo_walkthrough = list(await server.read_resource("adapter-walkthrough://efsa_primo_tabular_alias_case"))
    primo_source = list(await server.read_resource("source-catalog://source/efsa.primo"))
    metals_control_source = list(await server.read_resource("source-catalog://source/eu.reg.333_2007"))
    glyphosate_reference_values = list(await server.read_resource("reference-values://substance/glyphosate"))
    us_lead_legal_limit_record = list(
        await server.read_resource(
            "contaminant-legal-limits://record/us.fda.lead.processed_foods.general_baby_foods.ml.2025"
        )
    )
    china_legal_limits = list(await server.read_resource("contaminant-legal-limits://jurisdiction/cn"))
    arsenic_legal_limits = list(
        await server.read_resource("contaminant-legal-limits://family/inorganic_arsenic_food_contaminants")
    )
    acetamiprid_reference_values = list(await server.read_resource("reference-values://substance/acetamiprid"))
    pfas_reference_values = list(
        await server.read_resource("reference-values://substance/sum_pfoa_pfna_pfhxs_pfos")
    )
    eu_pfas_reporting_profile = list(
        await server.read_resource("reporting-profiles://profile/eu.pfas.efsa4.food_risk")
    )
    pfas_reporting_profiles = list(
        await server.read_resource("reporting-profiles://family/pfas_food_contaminants")
    )
    acrylamide_reference_values = list(await server.read_resource("reference-values://substance/acrylamide"))
    bpa_reference_values = list(await server.read_resource("reference-values://substance/bisphenol_a"))
    cadmium_reference_values = list(await server.read_resource("reference-values://substance/cadmium"))
    lead_reference_values = list(await server.read_resource("reference-values://substance/lead"))
    inorganic_arsenic_reference_values = list(
        await server.read_resource("reference-values://substance/inorganic_arsenic")
    )
    methylmercury_reference_values = list(await server.read_resource("reference-values://substance/methylmercury"))
    inorganic_mercury_reference_values = list(
        await server.read_resource("reference-values://substance/inorganic_mercury")
    )
    comprehensive_db = list(
        await server.read_resource("consumption-datasets://dataset/efsa.comprehensive_food_consumption_db")
    )
    pfas_dataset = list(
        await server.read_resource("consumption-datasets://dataset/efsa.comprehensive_food_consumption_db.pfas_support")
    )
    acrylamide_dataset = list(
        await server.read_resource("consumption-datasets://dataset/efsa.comprehensive_food_consumption_db.acrylamide_support")
    )
    bpa_dataset = list(
        await server.read_resource("consumption-datasets://dataset/efsa.comprehensive_food_consumption_db.bpa_support")
    )
    cadmium_dataset = list(
        await server.read_resource("consumption-datasets://dataset/efsa.comprehensive_food_consumption_db.cadmium_support")
    )
    lead_dataset = list(
        await server.read_resource("consumption-datasets://dataset/efsa.comprehensive_food_consumption_db.lead_support")
    )
    inorganic_arsenic_dataset = list(
        await server.read_resource(
            "consumption-datasets://dataset/efsa.comprehensive_food_consumption_db.inorganic_arsenic_support"
        )
    )
    mercury_dataset = list(
        await server.read_resource("consumption-datasets://dataset/efsa.comprehensive_food_consumption_db.mercury_support")
    )
    cadmium_metals_occurrence = list(
        await server.read_resource("metals-occurrence://family/cadmium_food_contaminants")
    )
    cadmium_occurrence_evidence = list(
        await server.read_resource("occurrence-evidence://family/cadmium_food_contaminants")
    )
    mercury_occurrence_evidence = list(
        await server.read_resource("occurrence-evidence://family/mercury_food_contaminants")
    )
    lead_analytical_method_evidence = list(
        await server.read_resource("analytical-method-evidence://family/lead_food_contaminants")
    )
    mercury_analytical_method_evidence = list(
        await server.read_resource("analytical-method-evidence://family/mercury_food_contaminants")
    )
    lead_metals_occurrence = list(await server.read_resource("metals-occurrence://family/lead_food_contaminants"))
    inorganic_arsenic_metals_occurrence = list(
        await server.read_resource("metals-occurrence://family/inorganic_arsenic_food_contaminants")
    )
    mercury_metals_occurrence = list(
        await server.read_resource("metals-occurrence://family/mercury_food_contaminants")
    )
    cadmium_metals_review_focus = list(
        await server.read_resource("metals-review-focus://family/cadmium_food_contaminants")
    )
    lead_metals_review_focus = list(
        await server.read_resource("metals-review-focus://family/lead_food_contaminants")
    )
    inorganic_arsenic_metals_review_focus = list(
        await server.read_resource("metals-review-focus://family/inorganic_arsenic_food_contaminants")
    )
    mercury_metals_review_focus = list(
        await server.read_resource("metals-review-focus://family/mercury_food_contaminants")
    )
    primo_method = list(await server.read_resource("method-registry://method/efsa.primo.3_1_application"))
    pfas_method = list(await server.read_resource("method-registry://method/efsa.pfas.food.2020_opinion"))
    acrylamide_method = list(await server.read_resource("method-registry://method/efsa.acrylamide.food.2015_opinion"))
    bpa_method = list(await server.read_resource("method-registry://method/efsa.bpa.food.2023_opinion"))
    cadmium_method = list(await server.read_resource("method-registry://method/efsa.cadmium.food.2009_opinion"))
    cadmium_control_method = list(await server.read_resource("method-registry://method/eu.cadmium.official_control.333_2007"))
    lead_method = list(await server.read_resource("method-registry://method/efsa.lead.food.2010_opinion"))
    lead_control_method = list(await server.read_resource("method-registry://method/eu.lead.official_control.333_2007"))
    inorganic_arsenic_method = list(
        await server.read_resource("method-registry://method/efsa.inorganic_arsenic.food.2024_opinion")
    )
    inorganic_arsenic_control_method = list(
        await server.read_resource("method-registry://method/eu.inorganic_arsenic.official_control.333_2007")
    )
    mercury_method = list(await server.read_resource("method-registry://method/efsa.mercury.food.2012_opinion"))
    mercury_control_method = list(
        await server.read_resource("method-registry://method/eu.mercury.official_control.333_2007")
    )
    mrl_law = list(
        await server.read_resource("legal-authorities://authority/eu.pesticide_residues.reg_396_2005")
    )
    pfas_law = list(await server.read_resource("legal-authorities://authority/eu.contaminants.reg_2023_915"))
    acrylamide_law = list(await server.read_resource("legal-authorities://authority/eu.acrylamide.reg_2017_2158"))
    bpa_law = list(await server.read_resource("legal-authorities://authority/eu.bpa.fcm.reg_2024_3190"))
    cadmium_law = list(await server.read_resource("legal-authorities://authority/eu.cadmium.contaminants.reg_2023_915"))
    cadmium_control_law = list(
        await server.read_resource("legal-authorities://authority/eu.cadmium.official_control.reg_333_2007")
    )
    lead_law = list(await server.read_resource("legal-authorities://authority/eu.lead.contaminants.reg_2023_915"))
    lead_control_law = list(
        await server.read_resource("legal-authorities://authority/eu.lead.official_control.reg_333_2007")
    )
    inorganic_arsenic_law = list(
        await server.read_resource("legal-authorities://authority/eu.inorganic_arsenic.contaminants.reg_2025_1891")
    )
    inorganic_arsenic_control_law = list(
        await server.read_resource("legal-authorities://authority/eu.inorganic_arsenic.official_control.reg_333_2007")
    )
    mercury_law = list(await server.read_resource("legal-authorities://authority/eu.mercury.contaminants.reg_2023_915"))
    mercury_control_law = list(
        await server.read_resource("legal-authorities://authority/eu.mercury.official_control.reg_333_2007")
    )
    microplastics_family = list(await server.read_resource("emerging-contaminants://family/microplastics_emerging"))
    pfas_family = list(await server.read_resource("emerging-contaminants://family/pfas_food_contaminants"))
    acrylamide_family = list(await server.read_resource("emerging-contaminants://family/acrylamide_process_contaminants"))
    bpa_family = list(await server.read_resource("emerging-contaminants://family/bisphenol_food_contact_migration"))
    cadmium_family = list(await server.read_resource("emerging-contaminants://family/cadmium_food_contaminants"))
    lead_family = list(await server.read_resource("emerging-contaminants://family/lead_food_contaminants"))
    inorganic_arsenic_family = list(
        await server.read_resource("emerging-contaminants://family/inorganic_arsenic_food_contaminants")
    )
    mercury_family = list(await server.read_resource("emerging-contaminants://family/mercury_food_contaminants"))
    us_coverage = list(await server.read_resource("jurisdiction-coverage://jurisdiction/us"))
    codex_cadmium_coverage = list(
        await server.read_resource("jurisdiction-coverage://coverage/codex_global.cadmium_food_contaminants.cadmium.wave1")
    )
    primo_governance = list(await server.read_resource("model-governance://family/efsa_primo_adapter"))
    apples_food_mapping = list(await server.read_resource("food-vocabulary://commodity/apples"))
    apple_juice_mapping = list(await server.read_resource("food-vocabulary://processed/apple_juice"))
    interoperability_manifest = list(await server.read_resource("interoperability://manifest"))
    interoperability_profile = list(await server.read_resource("interoperability://profile/oht_85_iuclid_json_preview"))
    interoperability_readiness_manifest = list(await server.read_resource("interoperability-readiness://manifest"))
    interoperability_readiness_profile = list(
        await server.read_resource("interoperability-readiness://profile/eu_internal_exchange_preview")
    )
    interoperability_remediation_catalog = list(await server.read_resource("interoperability-remediation://catalog"))
    interoperability_remediation_action = list(
        await server.read_resource("interoperability-remediation://action/upgrade_linked_dossier_readiness")
    )
    reporting_profiles_doc = list(await server.read_resource("docs://reporting-profiles-registry"))

    assert json.loads(adapter_manifest[0].content)["families"]
    assert json.loads(adapter_templates[0].content)["templates"]
    assert json.loads(adapter_walkthroughs[0].content)["walkthroughs"]
    assert json.loads(contracts[0].content)["schemas"]
    assert json.loads(defaults[0].content)["files"]
    assert json.loads(source_catalog[0].content)["sources"]
    assert json.loads(reference_values[0].content)["records"]
    assert json.loads(contaminant_legal_limits[0].content)["records"]
    assert json.loads(consumption_datasets[0].content)["datasets"]
    assert json.loads(method_registry[0].content)["methods"]
    assert json.loads(legal_authorities[0].content)["authorities"]
    assert json.loads(reporting_profiles[0].content)["profiles"]
    assert json.loads(occurrence_evidence[0].content)["records"]
    assert json.loads(analytical_method_evidence[0].content)["records"]
    assert json.loads(metals_occurrence[0].content)["records"]
    assert json.loads(metals_review_focus[0].content)["records"]
    assert json.loads(emerging_contaminants[0].content)["families"]
    assert json.loads(jurisdiction_coverage[0].content)["records"]
    assert json.loads(model_governance[0].content)["families"]
    assert json.loads(food_vocabulary[0].content)["commodityMappings"]
    assert json.loads(validation_manifest[0].content)["artifacts"]
    assert json.loads(interoperability_rules[0].content)["rules"]
    assert json.loads(interoperability_readiness_profiles[0].content)["profiles"]
    assert json.loads(interoperability_remediation_actions[0].content)["actions"]
    assert json.loads(regulatory_rules[0].content)["rules"]
    assert json.loads(sanitisation_rules[0].content)["rules"]
    assert json.loads(interoperability_profiles[0].content)["profiles"]
    assert json.loads(readiness_profiles[0].content)["profiles"]
    assert json.loads(source_database_cases[0].content)["cases"]
    assert json.loads(contaminant_monitoring_cases[0].content)["cases"]
    assert json.loads(contaminant_monitoring_bundle_cases[0].content)["cases"]
    assert json.loads(contaminant_monitoring_signoff_cases[0].content)["cases"]
    assert json.loads(contaminant_monitoring_review_dossier_cases[0].content)["cases"]
    assert json.loads(mapping_gap_report[0].content)["gaps"]
    assert json.loads(interoperability_manifest[0].content)["profiles"]
    assert json.loads(interoperability_profile[0].content)["mappedFields"]
    assert json.loads(interoperability_readiness_manifest[0].content)["profiles"]
    assert json.loads(interoperability_readiness_profile[0].content)["requiredDossierReadinessProfile"]
    assert json.loads(interoperability_remediation_catalog[0].content)["actions"]
    assert json.loads(interoperability_remediation_action[0].content)["ruleId"] == "linked_dossier_readiness"
    assert "rivm" in reporting_profiles_doc[0].content.lower()
    assert json.loads(primo_source[0].content)["documentStatus"] == "tool_metadata"
    assert json.loads(metals_control_source[0].content)["regulatoryRole"] == "binding"
    assert len(json.loads(glyphosate_reference_values[0].content)["records"]) >= 2
    assert json.loads(us_lead_legal_limit_record[0].content)["limitValue"] == 0.01
    assert json.loads(us_lead_legal_limit_record[0].content)["commodityCodes"] == ["purees"]
    assert {
        item["recordId"] for item in json.loads(china_legal_limits[0].content)["records"]
    } >= {
        "cn.nhc.cadmium.rice.ml.2025",
        "cn.nhc.lead.infant_formula.ml.2025",
        "cn.nhc.inorganic_arsenic.rice.ml.2025",
        "cn.nhc.methylmercury.aquatic_animals.general.ml.2025",
    }
    assert {
        item["recordId"] for item in json.loads(arsenic_legal_limits[0].content)["records"]
    } >= {
        "us.fda.inorganic_arsenic.rice_cereals.ml.2020",
        "us.fda.inorganic_arsenic.apple_juice.ml.2023",
        "cn.nhc.inorganic_arsenic.rice.ml.2025",
    }
    assert {item["recordId"] for item in json.loads(acetamiprid_reference_values[0].content)["records"]} >= {
        "efsa.openfoodtox.acetamiprid.adi",
        "efsa.openfoodtox.acetamiprid.arfd",
        "jmpr.acetamiprid.adi.2011",
        "cn.nhc.acetamiprid.adi.2026",
    }
    assert json.loads(pfas_reference_values[0].content)["records"][0]["referenceType"] == "twi"
    assert json.loads(eu_pfas_reporting_profile[0].content)["profileRole"] == "primary_regulatory"
    assert {item["profileId"] for item in json.loads(pfas_reporting_profiles[0].content)["profiles"]} == {
        "eu.pfas.efsa4.food_risk",
        "eu.pfas.efsa4.ml_lower_bound",
        "eu.pfas.individual_panel_detail",
        "nl.pfas.rivm_peq.biota_fish_advisory",
        "nl.pfas.rivm_peq.food_advisory",
    }
    assert len(json.loads(acrylamide_reference_values[0].content)["records"]) == 2
    assert json.loads(bpa_reference_values[0].content)["records"][0]["referenceType"] == "tdi"
    assert json.loads(cadmium_reference_values[0].content)["records"][0]["referenceType"] == "twi"
    assert len(json.loads(lead_reference_values[0].content)["records"]) == 2
    assert json.loads(inorganic_arsenic_reference_values[0].content)["records"][0]["referenceType"] == "bmdl05_skin_cancer"
    assert json.loads(methylmercury_reference_values[0].content)["records"][0]["referenceType"] == "twi"
    assert json.loads(inorganic_mercury_reference_values[0].content)["records"][0]["referenceType"] == "twi"
    assert json.loads(comprehensive_db[0].content)["datasetId"] == "efsa.comprehensive_food_consumption_db"
    assert json.loads(pfas_dataset[0].content)["contaminantFamily"] == "pfas_food_contaminants"
    assert json.loads(acrylamide_dataset[0].content)["contaminantFamily"] == "acrylamide_process_contaminants"
    assert json.loads(bpa_dataset[0].content)["contaminantFamily"] == "bisphenol_food_contact_migration"
    assert json.loads(cadmium_dataset[0].content)["contaminantFamily"] == "cadmium_food_contaminants"
    assert json.loads(lead_dataset[0].content)["contaminantFamily"] == "lead_food_contaminants"
    assert json.loads(inorganic_arsenic_dataset[0].content)["contaminantFamily"] == "inorganic_arsenic_food_contaminants"
    assert json.loads(mercury_dataset[0].content)["contaminantFamily"] == "mercury_food_contaminants"
    assert (
        json.loads(cadmium_occurrence_evidence[0].content)["records"][0]["recordId"]
        == "eu.cadmium.occurrence_evidence.official_monitoring_context"
    )
    assert (
        json.loads(mercury_occurrence_evidence[0].content)["records"][0]["recordId"]
        == "eu.mercury.occurrence_evidence.official_monitoring_context"
    )
    assert (
        json.loads(lead_analytical_method_evidence[0].content)["records"][0]["recordId"]
        == "eu.lead.analytical_method_evidence.official_control"
    )
    assert (
        json.loads(mercury_analytical_method_evidence[0].content)["records"][0]["recordId"]
        == "eu.mercury.analytical_method_evidence.official_control"
    )
    assert json.loads(cadmium_metals_occurrence[0].content)["records"][0]["recordId"] == "efsa.cadmium.occurrence_monitoring.support"
    assert json.loads(lead_metals_occurrence[0].content)["records"][0]["recordId"] == "efsa.lead.occurrence_monitoring.support"
    assert (
        json.loads(inorganic_arsenic_metals_occurrence[0].content)["records"][0]["recordId"]
        == "efsa.inorganic_arsenic.occurrence_monitoring.support"
    )
    assert json.loads(mercury_metals_occurrence[0].content)["records"][0]["recordId"] == "efsa.mercury.occurrence_monitoring.support"
    assert "game_meat" in json.loads(lead_metals_occurrence[0].content)["records"][0]["highAttentionFoods"]
    assert "rice_and_rice_based_products" in json.loads(inorganic_arsenic_metals_occurrence[0].content)["records"][0]["priorityFoodGroups"]
    assert "swordfish" in json.loads(mercury_metals_occurrence[0].content)["records"][0]["highAttentionFoods"]
    assert (
        "women_who_are_pregnant_or_planning_pregnancy"
        in json.loads(mercury_metals_occurrence[0].content)["records"][0]["sensitivePopulationGroups"]
    )
    assert (
        json.loads(cadmium_metals_review_focus[0].content)["records"][0]["focusId"]
        == "efsa.cadmium.staple_plant_foods.review_focus"
    )
    assert "game_meat" in {
        food for item in json.loads(lead_metals_review_focus[0].content)["records"] for food in item["focusFoods"]
    }
    assert "rice_based_infant_foods" in {
        food
        for item in json.loads(inorganic_arsenic_metals_review_focus[0].content)["records"]
        for food in item["focusFoods"]
    }
    assert "bigeye_tuna" in {
        food for item in json.loads(mercury_metals_review_focus[0].content)["records"] for food in item["focusFoods"]
    }
    assert json.loads(primo_method[0].content)["currentVersionLabel"] == "3.1"
    assert json.loads(pfas_method[0].content)["authority"] == "EFSA"
    assert json.loads(acrylamide_method[0].content)["authority"] == "EFSA"
    assert json.loads(bpa_method[0].content)["authority"] == "EFSA"
    assert json.loads(cadmium_method[0].content)["authority"] == "EFSA"
    assert json.loads(cadmium_control_method[0].content)["authority"] == "European Union"
    assert json.loads(lead_method[0].content)["authority"] == "EFSA"
    assert json.loads(lead_control_method[0].content)["authority"] == "European Union"
    assert json.loads(inorganic_arsenic_method[0].content)["authority"] == "EFSA"
    assert json.loads(inorganic_arsenic_control_method[0].content)["authority"] == "European Union"
    assert json.loads(mercury_method[0].content)["authority"] == "EFSA"
    assert json.loads(mercury_control_method[0].content)["authority"] == "European Union"
    assert json.loads(mrl_law[0].content)["submissionUse"] == "allowed"
    assert json.loads(pfas_law[0].content)["submissionUse"] == "allowed"
    assert json.loads(acrylamide_law[0].content)["submissionUse"] == "allowed"
    assert json.loads(bpa_law[0].content)["submissionUse"] == "allowed"
    assert json.loads(cadmium_law[0].content)["submissionUse"] == "allowed"
    assert json.loads(cadmium_control_law[0].content)["submissionUse"] == "allowed"
    assert json.loads(lead_law[0].content)["submissionUse"] == "allowed"
    assert json.loads(lead_control_law[0].content)["submissionUse"] == "allowed"
    assert json.loads(inorganic_arsenic_law[0].content)["submissionUse"] == "allowed"
    assert json.loads(inorganic_arsenic_control_law[0].content)["submissionUse"] == "allowed"
    assert json.loads(mercury_law[0].content)["submissionUse"] == "allowed"
    assert json.loads(mercury_control_law[0].content)["submissionUse"] == "allowed"
    assert json.loads(microplastics_family[0].content)["submissionUse"] == "not_allowed"
    assert json.loads(pfas_family[0].content)["submissionUse"] == "review_required"
    assert json.loads(acrylamide_family[0].content)["submissionUse"] == "allowed"
    assert json.loads(bpa_family[0].content)["submissionUse"] == "allowed"
    assert json.loads(cadmium_family[0].content)["submissionUse"] == "allowed"
    assert json.loads(lead_family[0].content)["submissionUse"] == "allowed"
    assert json.loads(inorganic_arsenic_family[0].content)["submissionUse"] == "allowed"
    assert json.loads(mercury_family[0].content)["submissionUse"] == "allowed"
    assert any(
        item["coverageId"] == "us.pesticide_residue.glyphosate.wave1"
        for item in json.loads(us_coverage[0].content)["records"]
    )
    assert json.loads(codex_cadmium_coverage[0].content)["coverageLevel"] == "deep_curated"
    assert json.loads(primo_governance[0].content)["governanceStatus"] == "compatibility_harness_only"
    assert json.loads(apples_food_mapping[0].content)["foodex2Code"] == "EXAMPLE_FDX2_APPLES_RAW"
    assert json.loads(apple_juice_mapping[0].content)["processedCommodityCode"] == "apple_juice"
    assert "commodity,iesti_mgkgbwday" in primo_template[0].content
    assert (
        json.loads(primo_walkthrough[0].content)["expectedNormalizedProjection"]["commodityCodes"]
        == ["apples", "milk"]
    )
