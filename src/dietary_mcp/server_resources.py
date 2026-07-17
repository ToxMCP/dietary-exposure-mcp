from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from dietary_mcp.adapter_manifest import build_adapter_manifest
from dietary_mcp.adapter_walkthroughs import build_adapter_walkthrough, build_adapter_walkthrough_manifest
from dietary_mcp.contracts import SCHEMA_MODELS, build_contract_manifest
from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.examples import build_examples
from dietary_mcp.guidance import read_doc
from dietary_mcp.interoperability import get_interoperability_profile_record, read_interoperability_profiles
from dietary_mcp.interoperability_readiness import (
    get_interoperability_readiness_profile_record,
    read_interoperability_readiness_profiles,
    read_interoperability_rules,
)
from dietary_mcp.interoperability_remediation import (
    get_interoperability_remediation_action_record,
    read_interoperability_remediation_actions,
)
from dietary_mcp.readiness import read_regulatory_rules
from dietary_mcp.release_artifacts import build_release_reports
from dietary_mcp.runtime import DietaryRuntime
from dietary_mcp.sanitisation import read_sanitisation_rules
from dietary_mcp.template_assets import read_adapter_template, read_adapter_template_manifest


def register_resources(
    mcp: FastMCP,
    repo_root: Path,
    defaults: DefaultsRegistry,
    runtime: DietaryRuntime,
) -> None:
    @mcp.resource("contracts://manifest")
    def contracts_manifest() -> str:
        return json.dumps(build_contract_manifest(), indent=2)

    @mcp.resource("adapter-manifest://manifest")
    def adapter_manifest_resource() -> str:
        return json.dumps(build_adapter_manifest(defaults), indent=2)

    @mcp.resource("adapter-input-templates://manifest")
    def adapter_input_templates_manifest() -> str:
        return json.dumps(read_adapter_template_manifest(repo_root), indent=2)

    @mcp.resource("adapter-import-walkthroughs://manifest")
    def adapter_import_walkthroughs_manifest() -> str:
        return json.dumps(build_adapter_walkthrough_manifest(repo_root), indent=2)

    @mcp.resource("schemas://{schema_name}")
    def schema_resource(schema_name: str) -> str:
        return json.dumps(SCHEMA_MODELS[schema_name].model_json_schema(), indent=2)

    @mcp.resource("examples://{example_name}")
    def example_resource(example_name: str) -> str:
        return json.dumps(build_examples(runtime)[example_name], indent=2)

    @mcp.resource("defaults://manifest")
    def defaults_manifest() -> str:
        return json.dumps(defaults.build_manifest(), indent=2)

    @mcp.resource("source-catalog://manifest")
    def source_catalog_manifest() -> str:
        return json.dumps(defaults.source_catalog_manifest(), indent=2)

    @mcp.resource("reference-values://manifest")
    def reference_values_manifest() -> str:
        return json.dumps(defaults.reference_values_manifest(), indent=2)

    @mcp.resource("mrl-enforcement://manifest")
    def mrl_enforcement_manifest() -> str:
        return json.dumps(defaults.mrl_enforcement_manifest(), indent=2)

    @mcp.resource("contaminant-legal-limits://manifest")
    def contaminant_legal_limits_manifest() -> str:
        return json.dumps(defaults.contaminant_legal_limits_manifest(), indent=2)

    @mcp.resource("consumption-datasets://manifest")
    def consumption_datasets_manifest() -> str:
        return json.dumps(defaults.consumption_datasets_manifest(), indent=2)

    @mcp.resource("method-registry://manifest")
    def method_registry_manifest() -> str:
        return json.dumps(defaults.method_registry_manifest(), indent=2)

    @mcp.resource("legal-authorities://manifest")
    def legal_authorities_manifest() -> str:
        return json.dumps(defaults.legal_authorities_manifest(), indent=2)

    @mcp.resource("reporting-profiles://manifest")
    def reporting_profiles_manifest() -> str:
        return json.dumps(defaults.reporting_profiles_manifest(), indent=2)

    @mcp.resource("occurrence-evidence://manifest")
    def occurrence_evidence_manifest() -> str:
        return json.dumps(defaults.occurrence_evidence_manifest(), indent=2)

    @mcp.resource("analytical-method-evidence://manifest")
    def analytical_method_evidence_manifest() -> str:
        return json.dumps(defaults.analytical_method_evidence_manifest(), indent=2)

    @mcp.resource("metals-occurrence://manifest")
    def metals_occurrence_manifest() -> str:
        return json.dumps(defaults.metals_occurrence_manifest(), indent=2)

    @mcp.resource("metals-review-focus://manifest")
    def metals_review_focus_manifest() -> str:
        return json.dumps(defaults.metals_review_focus_manifest(), indent=2)

    @mcp.resource("emerging-contaminants://manifest")
    def emerging_contaminants_manifest() -> str:
        return json.dumps(defaults.emerging_contaminants_manifest(), indent=2)

    @mcp.resource("jurisdiction-coverage://manifest")
    def jurisdiction_coverage_manifest() -> str:
        return json.dumps(defaults.jurisdiction_coverage_manifest(), indent=2)

    @mcp.resource("model-governance://manifest")
    def model_governance_manifest() -> str:
        return json.dumps(defaults.model_governance_manifest(), indent=2)

    @mcp.resource("consumption-profiles://manifest")
    def consumption_profiles_manifest() -> str:
        return json.dumps(defaults.consumption_profiles_manifest(), indent=2)

    @mcp.resource("commodity-taxonomy://manifest")
    def commodity_taxonomy_manifest() -> str:
        return json.dumps(defaults.commodity_taxonomy_manifest(), indent=2)

    @mcp.resource("food-vocabulary://manifest")
    def food_vocabulary_manifest() -> str:
        return json.dumps(defaults.food_vocabulary_crosswalk_manifest(), indent=2)

    @mcp.resource("interoperability://manifest")
    def interoperability_manifest() -> str:
        return json.dumps(read_interoperability_profiles(repo_root), indent=2)

    @mcp.resource("interoperability-readiness://manifest")
    def interoperability_readiness_manifest() -> str:
        return json.dumps(read_interoperability_readiness_profiles(repo_root), indent=2)

    @mcp.resource("interoperability-remediation://catalog")
    def interoperability_remediation_catalog() -> str:
        return json.dumps(read_interoperability_remediation_actions(repo_root), indent=2)

    @mcp.resource("docs://{doc_name}")
    def docs_resource(doc_name: str) -> str:
        return read_doc(repo_root, doc_name)

    @mcp.resource("adapter-template://{template_name}")
    def adapter_template_resource(template_name: str) -> str:
        return read_adapter_template(repo_root, template_name)

    @mcp.resource("adapter-walkthrough://{walkthrough_name}")
    def adapter_walkthrough_resource(walkthrough_name: str) -> str:
        return json.dumps(build_adapter_walkthrough(repo_root, walkthrough_name), indent=2)

    @mcp.resource("release://{report_name}")
    def release_resource(report_name: str) -> str:
        return json.dumps(build_release_reports(repo_root)[report_name], indent=2)

    @mcp.resource("validation://manifest")
    def validation_manifest_resource() -> str:
        return (repo_root / "validation" / "v1" / "manifest.json").read_text()

    @mcp.resource("validation://regulatory-rules")
    def validation_regulatory_rules_resource() -> str:
        return json.dumps(read_regulatory_rules(repo_root), indent=2)

    @mcp.resource("validation://sanitisation-rules")
    def validation_sanitisation_rules_resource() -> str:
        return json.dumps(read_sanitisation_rules(repo_root), indent=2)

    @mcp.resource("validation://interoperability-profiles")
    def validation_interoperability_profiles_resource() -> str:
        return json.dumps(read_interoperability_profiles(repo_root), indent=2)

    @mcp.resource("validation://interoperability-rules")
    def validation_interoperability_rules_resource() -> str:
        return json.dumps(read_interoperability_rules(repo_root), indent=2)

    @mcp.resource("validation://interoperability-readiness-profiles")
    def validation_interoperability_readiness_profiles_resource() -> str:
        return json.dumps(read_interoperability_readiness_profiles(repo_root), indent=2)

    @mcp.resource("validation://interoperability-remediation-actions")
    def validation_interoperability_remediation_actions_resource() -> str:
        return json.dumps(read_interoperability_remediation_actions(repo_root), indent=2)

    @mcp.resource("validation://readiness-profiles")
    def validation_readiness_profiles_resource() -> str:
        return json.dumps(defaults.regulatory_readiness_profiles_manifest(), indent=2)

    @mcp.resource("validation://artifact/{artifact_name}")
    def validation_artifact_resource(artifact_name: str) -> str:
        return (repo_root / "validation" / "v1" / f"{artifact_name}.json").read_text()

    @mcp.resource("source-catalog://source/{source_id}")
    def source_catalog_record_resource(source_id: str) -> str:
        return json.dumps(defaults.get_source_catalog_record(source_id), indent=2)

    @mcp.resource("reference-values://substance/{substance_key}")
    def reference_values_record_resource(substance_key: str) -> str:
        records = [
            item
            for item in defaults.list_reference_value_records()
            if item["substanceKey"].strip().lower() == substance_key.strip().lower()
        ]
        return json.dumps(
            {
                "substanceKey": substance_key,
                "records": records,
            },
            indent=2,
        )

    @mcp.resource("mrl-enforcement://record/{record_id}")
    def mrl_enforcement_record_resource(record_id: str) -> str:
        return json.dumps(defaults.get_mrl_enforcement_record(record_id), indent=2)

    @mcp.resource("mrl-enforcement://substance/{substance_key}")
    def mrl_enforcement_substance_resource(substance_key: str) -> str:
        records = [
            item
            for item in defaults.list_mrl_enforcement_records()
            if item["substanceKey"].strip().lower() == substance_key.strip().lower()
        ]
        return json.dumps(
            {
                "substanceKey": substance_key,
                "records": records,
            },
            indent=2,
        )

    @mcp.resource("contaminant-legal-limits://record/{record_id}")
    def contaminant_legal_limit_record_resource(record_id: str) -> str:
        return json.dumps(defaults.get_contaminant_legal_limit_record(record_id), indent=2)

    @mcp.resource("contaminant-legal-limits://jurisdiction/{jurisdiction}")
    def contaminant_legal_limits_jurisdiction_resource(jurisdiction: str) -> str:
        return json.dumps(
            {
                "jurisdiction": jurisdiction,
                "records": defaults.get_contaminant_legal_limit_records(jurisdiction=jurisdiction),
            },
            indent=2,
        )

    @mcp.resource("contaminant-legal-limits://family/{family_id}")
    def contaminant_legal_limits_family_resource(family_id: str) -> str:
        return json.dumps(
            {
                "familyId": family_id,
                "records": defaults.get_contaminant_legal_limit_records(contaminant_family=family_id),
            },
            indent=2,
        )

    @mcp.resource("consumption-datasets://dataset/{dataset_id}")
    def consumption_dataset_record_resource(dataset_id: str) -> str:
        return json.dumps(defaults.get_consumption_dataset_record(dataset_id), indent=2)

    @mcp.resource("method-registry://method/{method_id}")
    def method_registry_record_resource(method_id: str) -> str:
        return json.dumps(defaults.get_method_registry_record(method_id), indent=2)

    @mcp.resource("legal-authorities://authority/{authority_id}")
    def legal_authority_record_resource(authority_id: str) -> str:
        return json.dumps(defaults.get_legal_authority_record(authority_id), indent=2)

    @mcp.resource("reporting-profiles://profile/{profile_id}")
    def reporting_profile_resource(profile_id: str) -> str:
        return json.dumps(defaults.get_reporting_profile_record(profile_id), indent=2)

    @mcp.resource("reporting-profiles://family/{family_id}")
    def reporting_profile_family_resource(family_id: str) -> str:
        return json.dumps(
            {
                "familyId": family_id,
                "profiles": defaults.get_reporting_profile_records_for_family(family_id),
            },
            indent=2,
        )

    @mcp.resource("occurrence-evidence://family/{family_id}")
    def occurrence_evidence_record_resource(family_id: str) -> str:
        return json.dumps(
            {
                "familyId": family_id,
                "records": defaults.get_occurrence_evidence_records_for_family(family_id),
            },
            indent=2,
        )

    @mcp.resource("analytical-method-evidence://family/{family_id}")
    def analytical_method_evidence_record_resource(family_id: str) -> str:
        return json.dumps(
            {
                "familyId": family_id,
                "records": defaults.get_analytical_method_evidence_records_for_family(family_id),
            },
            indent=2,
        )

    @mcp.resource("metals-occurrence://family/{family_id}")
    def metals_occurrence_record_resource(family_id: str) -> str:
        return json.dumps(
            {
                "familyId": family_id,
                "records": defaults.get_metals_occurrence_records_for_family(family_id),
            },
            indent=2,
        )

    @mcp.resource("metals-review-focus://family/{family_id}")
    def metals_review_focus_record_resource(family_id: str) -> str:
        return json.dumps(
            {
                "familyId": family_id,
                "records": defaults.get_metals_review_focus_records_for_family(family_id),
            },
            indent=2,
        )

    @mcp.resource("emerging-contaminants://family/{family_id}")
    def emerging_contaminant_record_resource(family_id: str) -> str:
        return json.dumps(defaults.get_emerging_contaminant_record(family_id), indent=2)

    @mcp.resource("jurisdiction-coverage://coverage/{coverage_id}")
    def jurisdiction_coverage_record_resource(coverage_id: str) -> str:
        return json.dumps(defaults.get_jurisdiction_coverage_record(coverage_id), indent=2)

    @mcp.resource("jurisdiction-coverage://jurisdiction/{jurisdiction}")
    def jurisdiction_coverage_jurisdiction_resource(jurisdiction: str) -> str:
        return json.dumps(
            {
                "jurisdiction": jurisdiction,
                "records": defaults.get_jurisdiction_coverage_records(jurisdiction=jurisdiction),
            },
            indent=2,
        )

    @mcp.resource("model-governance://family/{model_family}")
    def model_governance_family_resource(model_family: str) -> str:
        return json.dumps(defaults.get_model_governance_record(model_family), indent=2)

    @mcp.resource("food-vocabulary://commodity/{commodity_code}")
    def food_vocabulary_mapping_resource(commodity_code: str) -> str:
        return json.dumps(defaults.get_food_vocabulary_mapping_record(commodity_code), indent=2)

    @mcp.resource("food-vocabulary://processed/{processed_commodity_code}")
    def processed_commodity_mapping_resource(processed_commodity_code: str) -> str:
        return json.dumps(defaults.get_processed_commodity_mapping_record(processed_commodity_code), indent=2)

    @mcp.resource("interoperability://profile/{profile_id}")
    def interoperability_profile_resource(profile_id: str) -> str:
        return json.dumps(get_interoperability_profile_record(repo_root, profile_id), indent=2)

    @mcp.resource("interoperability-readiness://profile/{profile_id}")
    def interoperability_readiness_profile_resource(profile_id: str) -> str:
        return json.dumps(get_interoperability_readiness_profile_record(repo_root, profile_id), indent=2)

    @mcp.resource("interoperability-remediation://action/{action_id}")
    def interoperability_remediation_action_resource(action_id: str) -> str:
        return json.dumps(get_interoperability_remediation_action_record(repo_root, action_id), indent=2)
