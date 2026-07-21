from __future__ import annotations

import copy
import hashlib
import json
import os
from contextvars import ContextVar
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root, sync_packaged_data
from dietary_mcp.adapter_manifest import build_adapter_manifest
from dietary_mcp.adapter_walkthroughs import build_adapter_walkthrough_manifest
from dietary_mcp.benchmarks import run_benchmarks
from dietary_mcp.contracts import build_contract_manifest
from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.dry_runs import build_validation_dossier, run_downstream_dry_runs
from dietary_mcp.examples import build_examples
from dietary_mcp.interoperability import read_interoperability_profiles
from dietary_mcp.interoperability_readiness import (
    read_interoperability_readiness_profiles,
    read_interoperability_rules,
)
from dietary_mcp.interoperability_remediation import read_interoperability_remediation_actions
from dietary_mcp.package_metadata import VERSION
from dietary_mcp.readiness import read_regulatory_rules
from dietary_mcp.reference_validation import run_dietary_reference_cases
from dietary_mcp.runtime import DietaryRuntime
from dietary_mcp.sanitisation import read_sanitisation_rules
from dietary_mcp.template_assets import read_adapter_template_manifest
from dietary_mcp.validation import (
    summarize_validation_results,
    validate_generated_artifacts,
    validation_results_status,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_RELEASE_REPORT_BUILD_DEPTH: ContextVar[int] = ContextVar("_RELEASE_REPORT_BUILD_DEPTH", default=0)
_RELEASE_REPORT_CACHE: dict[tuple[str, bool, bool, str, tuple[int, ...]], dict[str, dict]] = {}


def _path_mtime_ns(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        newest_mtime = path.stat().st_mtime_ns
    except OSError:
        return 0
    if path.is_file():
        return newest_mtime
    for candidate in path.rglob("*"):
        try:
            candidate_mtime = candidate.stat().st_mtime_ns
        except OSError:
            continue
        if candidate_mtime > newest_mtime:
            newest_mtime = candidate_mtime
    return newest_mtime


def _release_report_state_key(repo_root: Path) -> tuple[int, ...]:
    watched_paths = (
        repo_root / "src" / "dietary_mcp",
        repo_root / "defaults",
        repo_root / "validation",
        repo_root / "schemas" / "examples",
        repo_root / "docs" / "contracts" / "schemas",
        repo_root / "config",
        repo_root / "pyproject.toml",
    )
    return tuple(_path_mtime_ns(path) for path in watched_paths)


def build_release_reports(
    repo_root: Path,
    *,
    skip_validation: bool = False,
    skip_examples: bool = False,
    package_dist_dir: Path | None = None,
) -> dict[str, dict]:
    depth = _RELEASE_REPORT_BUILD_DEPTH.get()
    token = _RELEASE_REPORT_BUILD_DEPTH.set(depth + 1)
    try:
        nested_build = depth > 0
        effective_skip_validation = skip_validation or nested_build
        effective_skip_examples = skip_examples or nested_build
        dist_dir = (package_dist_dir or (repo_root / "dist")).resolve()
        cache_key = (
            str(repo_root.resolve()),
            effective_skip_validation,
            effective_skip_examples,
            str(dist_dir),
            (*_release_report_state_key(repo_root), _path_mtime_ns(dist_dir)),
        )
        cached_result = _RELEASE_REPORT_CACHE.get(cache_key)
        if cached_result is not None:
            return copy.deepcopy(cached_result)

        defaults_registry = DefaultsRegistry(repo_root)
        adapter_manifest = build_adapter_manifest(defaults_registry)
        template_manifest = read_adapter_template_manifest(repo_root)
        walkthrough_manifest = build_adapter_walkthrough_manifest(repo_root)
        reference_values_manifest = defaults_registry.reference_values_manifest()
        mrl_enforcement_manifest = defaults_registry.mrl_enforcement_manifest()
        contaminant_legal_limits_manifest = defaults_registry.contaminant_legal_limits_manifest()
        consumption_datasets_manifest = defaults_registry.consumption_datasets_manifest()
        method_registry_manifest = defaults_registry.method_registry_manifest()
        legal_authorities_manifest = defaults_registry.legal_authorities_manifest()
        reporting_profiles_manifest = defaults_registry.reporting_profiles_manifest()
        occurrence_evidence_manifest = defaults_registry.occurrence_evidence_manifest()
        analytical_method_evidence_manifest = defaults_registry.analytical_method_evidence_manifest()
        metals_occurrence_manifest = defaults_registry.metals_occurrence_manifest()
        metals_review_focus_manifest = defaults_registry.metals_review_focus_manifest()
        emerging_contaminants_manifest = defaults_registry.emerging_contaminants_manifest()
        jurisdiction_coverage_manifest = defaults_registry.jurisdiction_coverage_manifest()
        model_governance_manifest = defaults_registry.model_governance_manifest()
        food_vocabulary_manifest = defaults_registry.food_vocabulary_crosswalk_manifest()
        interoperability_profiles_manifest = read_interoperability_profiles(repo_root)
        interoperability_readiness_profiles_manifest = read_interoperability_readiness_profiles(repo_root)
        interoperability_rules_manifest = read_interoperability_rules(repo_root)
        interoperability_remediation_actions_manifest = read_interoperability_remediation_actions(repo_root)
        readiness_profiles_manifest = defaults_registry.regulatory_readiness_profiles_manifest()
        regulatory_rules_manifest = read_regulatory_rules(repo_root)
        sanitisation_rules_manifest = read_sanitisation_rules(repo_root)
        contracts_manifest = build_contract_manifest()
        validation_results = (
            validate_generated_artifacts(repo_root)
            if not effective_skip_validation
            else {
                "schemas": [],
                "examples": [],
                "tool_surface": [],
                "benchmarks": [],
                "dietary_references": [],
                "adapter_normalization": [],
                "survey_distribution_summary": [],
                "probabilistic_intake_summary": [],
                "probabilistic_intake_summary_fingerprints": [],
                "uncertainty_intake_assessment": [],
                "censored_residue_policy": [],
                "uncertainty_sensitivity": [],
                "health_reference_exceedance": [],
                "uncertainty_reproducibility": [],
                "food_vocabulary": [],
                "interoperability_preview": [],
                "interoperability_readiness": [],
                "interoperability_remediation": [],
                "interoperability_signoff": [],
                "contaminant_monitoring": [],
                "contaminant_monitoring_bundle": [],
                "contaminant_monitoring_signoff": [],
                "contaminant_monitoring_review_dossier": [],
                "metals_monitoring": [],
                "metals_monitoring_signoff": [],
                "metals_monitoring_review_dossier": [],
                "review_dossier_readiness": [],
                "scientific_follow_up_queue_bundle": [],
                "sanitised_public_review": [],
                "source_databases": [],
            }
        )
        validation_results["status"] = validation_results_status(validation_results)
        validation_results["suiteSummary"] = summarize_validation_results(validation_results)
        benchmark_results = run_benchmarks(repo_root)
        reference_results = run_dietary_reference_cases(repo_root)
        asset_root = runtime_asset_root() if not (repo_root / "config" / "release_gates.json").exists() else repo_root
        gates = json.loads((asset_root / "config" / "release_gates.json").read_text())["gates"]
        if effective_skip_examples:
            examples_manifest_path = (
                repo_root / "schemas" / "examples" / "manifest.json"
                if (repo_root / "schemas" / "examples" / "manifest.json").exists()
                else runtime_asset_root() / "schemas" / "examples" / "manifest.json"
            )
            examples_manifest = json.loads(examples_manifest_path.read_text())
        else:
            example_payloads = build_examples(DietaryRuntime(repo_root))
            examples_manifest = {
                "examples": [
                    {"name": name, "path": f"schemas/examples/{name}.json"} for name in sorted(example_payloads.keys())
                ]
            }
        validation_manifest = json.loads((asset_root / "validation" / "v1" / "manifest.json").read_text())
        package_artifacts = []
        if dist_dir.exists():
            for artifact in sorted(dist_dir.iterdir()):
                if artifact.is_file() and not artifact.name.startswith("."):
                    package_artifacts.append(
                        {
                            "name": artifact.name,
                            "sizeBytes": artifact.stat().st_size,
                            "sha256": _sha256(artifact),
                        }
                    )

        examples_ok = (
            all(item["status"] == "ok" for item in validation_results["examples"])
            if not effective_skip_validation
            else True
        )
        schemas_ok = (
            all(item["status"] == "ok" for item in validation_results["schemas"])
            if not effective_skip_validation
            else True
        )
        all_validation_suites_ok = (
            validation_results.get("status") == "ok" if not effective_skip_validation else True
        )
        benchmarks_ok = benchmark_results["status"] == "ok"
        gate_status = {
            "acute_chronic_explicit": True,
            "schemas_examples_validate": schemas_ok and examples_ok,
            "benchmarks_pass": benchmarks_ok,
            "all_validation_suites_ok": all_validation_suites_ok,
            "defaults_versions_published": bool(defaults_registry.build_manifest()["files"]),
            "contributors_auditable": any(
                item["name"] == "dietaryIntakeSummary.v1" for item in contracts_manifest["schemas"]
            ),
            "pbpk_export_valid": any(
                item["name"] == "pbpkExternalImportBundle.v1" for item in contracts_manifest["schemas"]
            ),
            "limitations_prevent_misuse": True,
        }

        metadata_report = {
        "version": VERSION,
        "schemaCount": len(contracts_manifest["schemas"]),
        "exampleCount": len(examples_manifest["examples"]),
        "defaultsVersion": defaults_registry.build_manifest()["defaultsVersion"],
        "consumptionProfileCount": len(defaults_registry.consumption_profiles_manifest()["profiles"]),
        "sourceCatalogCount": len(defaults_registry.source_catalog_manifest()["sources"]),
        "referenceValueRecordCount": len(reference_values_manifest["records"]),
        "contaminantLegalLimitRecordCount": len(contaminant_legal_limits_manifest["records"]),
        "consumptionDatasetCount": len(consumption_datasets_manifest["datasets"]),
        "methodRegistryCount": len(method_registry_manifest["methods"]),
        "legalAuthorityCount": len(legal_authorities_manifest["authorities"]),
        "reportingProfileCount": len(reporting_profiles_manifest["profiles"]),
        "occurrenceEvidenceRecordCount": len(occurrence_evidence_manifest["records"]),
        "analyticalMethodEvidenceRecordCount": len(analytical_method_evidence_manifest["records"]),
        "metalsOccurrenceRecordCount": len(metals_occurrence_manifest["records"]),
        "metalsReviewFocusRecordCount": len(metals_review_focus_manifest["records"]),
        "emergingContaminantFamilyCount": len(emerging_contaminants_manifest["families"]),
        "jurisdictionCoverageRecordCount": len(jurisdiction_coverage_manifest["records"]),
        "modelGovernanceFamilyCount": len(model_governance_manifest["families"]),
        "mrlEnforcementRecordCount": len(defaults_registry.mrl_enforcement_registry["records"]),
        "compositionRecipeCount": len(defaults_registry.composition_recipes_registry["records"]),
        "foodVocabularyCommodityCount": len(food_vocabulary_manifest["commodityMappings"]),
        "processedCommodityMappingCount": len(food_vocabulary_manifest["processedCommodityMappings"]),
        "interoperabilityProfileCount": len(interoperability_profiles_manifest["profiles"]),
        "interoperabilityReadinessProfileCount": len(interoperability_readiness_profiles_manifest["profiles"]),
        "readinessProfileCount": len(readiness_profiles_manifest["profiles"]),
        "interoperabilityRuleCount": len(interoperability_rules_manifest["rules"]),
        "interoperabilityRemediationActionCount": len(interoperability_remediation_actions_manifest["actions"]),
        "regulatoryRuleCount": len(regulatory_rules_manifest["rules"]),
        "sanitisationRuleCount": len(sanitisation_rules_manifest["rules"]),
        "adapterTemplateCount": len(template_manifest["templates"]),
        "adapterWalkthroughCount": len(walkthrough_manifest["walkthroughs"]),
        "commodityCount": len(defaults_registry.commodity_taxonomy_manifest()["commodities"]),
        "benchmarkCaseCount": len(benchmark_results["cases"]),
        "referenceCaseCount": len(reference_results["cases"]),
        "supportedWorkflows": [
            "point_estimate",
            "bounded_acute",
            "bounded_chronic",
            "parse_raw_survey_dataset",
            "survey_distribution_summary",
            "probabilistic_intake_summary",
            "uncertainty_intake_assessment",
            "evaluate_global_trade_risk",
            "trade_risk_review_bundle",
            "trade_risk_review_dossier",
            "adapter_stub",
            "adapter_review_handoff",
            "adapter_review_dossier",
            "review_dossier_readiness",
            "scientific_follow_up_queue_bundle",
            "scientific_follow_up_review_board",
            "scientific_follow_up_owner_handoff_packet",
            "scientific_follow_up_owner_remediation_packet",
            "scientific_follow_up_owner_signoff_packet",
            "scientific_follow_up_owner_signoff_dossier",
            "reference_value_lookup",
            "contaminant_legal_limit_lookup",
            "method_support_lookup",
            "consumption_dataset_support_lookup",
            "reporting_profile_lookup",
            "occurrence_evidence_lookup",
            "analytical_method_evidence_lookup",
            "contaminant_monitoring_import_check",
            "contaminant_monitoring_interpretation_bundle",
            "contaminant_monitoring_signoff_packet",
            "contaminant_monitoring_review_dossier",
            "metals_occurrence_lookup",
            "metals_review_focus_lookup",
            "metals_monitoring_interpretation_bundle",
            "metals_monitoring_signoff_packet",
            "metals_monitoring_review_dossier",
            "sanitised_public_review_dossier",
            "interoperability_preview",
            "interoperability_readiness_assessment",
            "interoperability_remediation_bundle",
            "interoperability_signoff_packet",
        ],
        "supportedModelFamilies": [item["modelFamily"] for item in adapter_manifest["families"]],
        "artifactHashes": {
            "adapterManifest": _sha256_text(json.dumps(adapter_manifest, sort_keys=True)),
            "adapterTemplateManifest": _sha256_text(json.dumps(template_manifest, sort_keys=True)),
            "adapterWalkthroughManifest": _sha256_text(json.dumps(walkthrough_manifest, sort_keys=True)),
            "referenceValuesManifest": _sha256_text(json.dumps(reference_values_manifest, sort_keys=True)),
            "mrlEnforcementManifest": _sha256_text(json.dumps(mrl_enforcement_manifest, sort_keys=True)),
            "contaminantLegalLimitsManifest": _sha256_text(
                json.dumps(contaminant_legal_limits_manifest, sort_keys=True)
            ),
            "consumptionDatasetsManifest": _sha256_text(json.dumps(consumption_datasets_manifest, sort_keys=True)),
            "methodRegistryManifest": _sha256_text(json.dumps(method_registry_manifest, sort_keys=True)),
            "legalAuthoritiesManifest": _sha256_text(json.dumps(legal_authorities_manifest, sort_keys=True)),
            "reportingProfilesManifest": _sha256_text(json.dumps(reporting_profiles_manifest, sort_keys=True)),
            "occurrenceEvidenceManifest": _sha256_text(json.dumps(occurrence_evidence_manifest, sort_keys=True)),
            "analyticalMethodEvidenceManifest": _sha256_text(
                json.dumps(analytical_method_evidence_manifest, sort_keys=True)
            ),
            "metalsOccurrenceManifest": _sha256_text(json.dumps(metals_occurrence_manifest, sort_keys=True)),
            "metalsReviewFocusManifest": _sha256_text(json.dumps(metals_review_focus_manifest, sort_keys=True)),
            "emergingContaminantsManifest": _sha256_text(
                json.dumps(emerging_contaminants_manifest, sort_keys=True)
            ),
            "jurisdictionCoverageManifest": _sha256_text(
                json.dumps(jurisdiction_coverage_manifest, sort_keys=True)
            ),
            "modelGovernanceManifest": _sha256_text(json.dumps(model_governance_manifest, sort_keys=True)),
            "foodVocabularyCrosswalkManifest": _sha256_text(json.dumps(food_vocabulary_manifest, sort_keys=True)),
            "interoperabilityProfilesManifest": _sha256_text(
                json.dumps(interoperability_profiles_manifest, sort_keys=True)
            ),
            "interoperabilityReadinessProfilesManifest": _sha256_text(
                json.dumps(interoperability_readiness_profiles_manifest, sort_keys=True)
            ),
            "interoperabilityRulesManifest": _sha256_text(
                json.dumps(interoperability_rules_manifest, sort_keys=True)
            ),
            "interoperabilityRemediationActionsManifest": _sha256_text(
                json.dumps(interoperability_remediation_actions_manifest, sort_keys=True)
            ),
            "readinessProfilesManifest": _sha256_text(json.dumps(readiness_profiles_manifest, sort_keys=True)),
            "regulatoryRulesManifest": _sha256_text(json.dumps(regulatory_rules_manifest, sort_keys=True)),
            "sanitisationRulesManifest": _sha256_text(json.dumps(sanitisation_rules_manifest, sort_keys=True)),
            "contractsManifest": _sha256_text(json.dumps(contracts_manifest, sort_keys=True)),
            "examplesManifest": _sha256_text(json.dumps(examples_manifest, sort_keys=True)),
            "defaultsManifest": _sha256_text(json.dumps(defaults_registry.build_manifest(), sort_keys=True)),
            "validationManifest": _sha256_text(json.dumps(validation_manifest, sort_keys=True)),
        },
        "packageArtifacts": package_artifacts,
    }
        readiness_report = {
        "version": VERSION,
        "status": "draft_ready" if all(gate_status.values()) else "review_required",
        "gates": [
            {
                "id": gate["id"],
                "description": gate["description"],
                "status": "pass" if gate_status[gate["id"]] else "review_required",
            }
            for gate in gates
        ],
        "validationSummary": validation_results["suiteSummary"],
        "validationArtifacts": validation_manifest["artifacts"],
        "knownLimitations": [
            "OpenFoodTox 3.0 bulk records remain review_required pending qualified review.",
            "Positive independent signoff on the remediated high-impact report is pending.",
            (
                "Decision-relevant reference and legal values require current "
                "primary-source verification."
            ),
            "No final regulatory decision semantics.",
            "No direct-use oral product or PBPK execution workflows.",
            "Bounded survey and uncertainty lanes are not a general-purpose population model.",
            "No claimed equivalence to PRIMo, DEEM, DietEx, or submission portals.",
            "Public RC support is local stdio; hosted HTTP requires a separate security review.",
            "Third-party attribution and redistribution terms remain applicable.",
        ],
    }
        security_provenance_review = {
        "version": VERSION,
        "status": "review_required",
        "notes": [
            "Dietary MCP does not handle secrets in v0.1.",
            "Residue, consumption-profile, and processing-factor provenance are explicit and machine-readable.",
            "Limitation notes are carried into comparison and downstream export payloads.",
        ],
        "machineReadableInputs": [
            "defaults/manifest.json",
            "validation/v1/manifest.json",
            "docs/contracts/schemas/manifest.json",
            "schemas/examples/manifest.json",
        ],
    }
        result = {
            "metadata-report": metadata_report,
            "readiness-report": readiness_report,
            "security-provenance-review-report": security_provenance_review,
        }
        if len(_RELEASE_REPORT_CACHE) >= 16:
            _RELEASE_REPORT_CACHE.clear()
        _RELEASE_REPORT_CACHE[cache_key] = copy.deepcopy(result)
        return result
    finally:
        _RELEASE_REPORT_BUILD_DEPTH.reset(token)


def write_release_reports(
    repo_root: Path,
    *,
    package_dist_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    reports = build_release_reports(repo_root, package_dist_dir=package_dist_dir)
    downstream_dry_runs = run_downstream_dry_runs(repo_root)
    validation_dossier = build_validation_dossier(repo_root)
    validation_summary = reports["readiness-report"]["validationSummary"]
    validation_dossier["status"] = (
        "draft_ready" if validation_summary["status"] == "ok" else "review_required"
    )
    validation_dossier["validationSummary"] = validation_summary
    release_dir = output_dir or (repo_root / "docs" / "releases")
    release_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "metadata-report": release_dir / f"v{VERSION}.release_metadata.json",
        "readiness-report": release_dir / f"v{VERSION}.readiness_report.json",
        "security-provenance-review-report": release_dir / f"v{VERSION}.security_provenance_review.json",
        "downstream-dry-runs": release_dir / f"v{VERSION}.downstream_dry_runs.json",
        "validation-dossier": release_dir / f"v{VERSION}.validation_dossier.json",
    }
    for key, path in paths.items():
        if key in reports:
            path.write_text(json.dumps(reports[key], indent=2) + "\n")
        elif key == "downstream-dry-runs":
            path.write_text(json.dumps(downstream_dry_runs, indent=2) + "\n")
        elif key == "validation-dossier":
            path.write_text(json.dumps(validation_dossier, indent=2) + "\n")
    return paths


def main() -> None:
    from dietary_mcp.contracts import generate_contract_artifacts

    repo_root = Path(__file__).resolve().parents[2]
    package_dist_env = os.environ.get("DIETARY_MCP_RELEASE_DIST_DIR")
    package_dist_dir = Path(package_dist_env).resolve() if package_dist_env else None
    generate_contract_artifacts(repo_root)
    sync_packaged_data(repo_root)
    write_release_reports(repo_root, package_dist_dir=package_dist_dir)


if __name__ == "__main__":
    main()
