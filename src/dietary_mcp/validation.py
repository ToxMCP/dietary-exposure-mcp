from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from dietary_mcp.adapter_validation import run_adapter_normalization_cases
from dietary_mcp.benchmarks import run_benchmarks
from dietary_mcp.contaminant_monitoring_bundle_validation import (
    run_contaminant_monitoring_bundle_cases,
)
from dietary_mcp.contaminant_monitoring_signoff_validation import (
    run_contaminant_monitoring_signoff_cases,
)
from dietary_mcp.contaminant_monitoring_review_dossier_validation import (
    run_contaminant_monitoring_review_dossier_cases,
)
from dietary_mcp.contaminant_monitoring_validation import run_contaminant_monitoring_check_cases
from dietary_mcp.contracts import SCHEMA_MODELS, generate_contract_artifacts
from dietary_mcp.food_vocabulary_validation import run_food_vocabulary_cases
from dietary_mcp.interoperability_validation import run_interoperability_preview_cases
from dietary_mcp.interoperability_readiness_validation import run_interoperability_readiness_cases
from dietary_mcp.interoperability_remediation_validation import run_interoperability_remediation_cases
from dietary_mcp.interoperability_signoff_validation import run_interoperability_signoff_cases
from dietary_mcp.metals_monitoring_validation import run_metals_monitoring_bundle_cases
from dietary_mcp.metals_monitoring_review_dossier_validation import (
    run_metals_monitoring_review_dossier_cases,
)
from dietary_mcp.metals_monitoring_signoff_validation import run_metals_monitoring_signoff_cases
from dietary_mcp.readiness_validation import run_review_dossier_readiness_cases
from dietary_mcp.reference_validation import run_dietary_reference_cases
from dietary_mcp.sanitisation_validation import run_sanitised_public_review_cases
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
from dietary_mcp.source_database_validation import run_source_database_cases
from dietary_mcp.survey_distribution_summary_validation import run_survey_distribution_summary_cases
from dietary_mcp.probabilistic_intake_summary_validation import run_probabilistic_intake_summary_cases
from dietary_mcp.tool_surface_validation import run_tool_surface_cases
from dietary_mcp.uncertainty_validation import (
    run_censored_residue_policy_cases,
    run_health_reference_exceedance_cases,
    run_uncertainty_intake_assessment_cases,
    run_uncertainty_reproducibility_cases,
    run_uncertainty_sensitivity_cases,
)


EXAMPLE_MODEL_ALIASES = {
    "dietaryIntakeSummary.pointEstimate.v1": "dietaryIntakeSummary.v1",
    "dietaryIntakeSummary.boundedAcute.v1": "dietaryIntakeSummary.v1",
}


def validate_generated_artifacts(repo_root: Path) -> dict:
    schema_dir = repo_root / "docs" / "contracts" / "schemas"
    example_dir = repo_root / "schemas" / "examples"
    results = {
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
        "source_databases": [],
        "metals_monitoring": [],
        "contaminant_monitoring": [],
        "contaminant_monitoring_bundle": [],
        "contaminant_monitoring_signoff": [],
        "contaminant_monitoring_review_dossier": [],
        "metals_monitoring_signoff": [],
        "metals_monitoring_review_dossier": [],
        "interoperability_preview": [],
        "interoperability_readiness": [],
        "interoperability_remediation": [],
        "interoperability_signoff": [],
        "review_dossier_readiness": [],
        "scientific_follow_up_queue_bundle": [],
        "scientific_follow_up_review_board": [],
        "scientific_follow_up_owner_handoff": [],
        "scientific_follow_up_owner_remediation": [],
        "scientific_follow_up_owner_signoff": [],
        "scientific_follow_up_owner_signoff_dossier": [],
        "sanitised_public_review": [],
    }

    if schema_dir.exists():
        for name in SCHEMA_MODELS:
            schema_path = schema_dir / f"{name}.json"
            results["schemas"].append({"name": name, "status": "ok" if schema_path.exists() else "missing"})
    else:
        for name in SCHEMA_MODELS:
            results["schemas"].append({"name": name, "status": "missing"})

    if example_dir.exists():
        for example_path in sorted(example_dir.glob("*.json")):
            if example_path.name == "manifest.json":
                continue
            name = example_path.stem
            model_name = EXAMPLE_MODEL_ALIASES.get(name, name)
            payload = json.loads(example_path.read_text())
            SCHEMA_MODELS[model_name].model_validate(payload)
            results["examples"].append({"name": example_path.name, "status": "ok"})
    else:
        results["examples"].append({"name": "schemas/examples", "status": "missing"})

    tool_surface_results = run_tool_surface_cases(repo_root)
    for case in tool_surface_results["cases"]:
        results["tool_surface"].append({"name": case["name"], "status": case["status"]})

    benchmark_results = run_benchmarks(repo_root)
    for case in benchmark_results["cases"]:
        results["benchmarks"].append({"name": case["name"], "status": case["status"]})

    reference_results = run_dietary_reference_cases(repo_root)
    for case in reference_results["cases"]:
        results["dietary_references"].append({"name": case["name"], "status": case["status"]})

    adapter_results = run_adapter_normalization_cases(repo_root)
    for case in adapter_results["cases"]:
        results["adapter_normalization"].append({"name": case["name"], "status": case["status"]})

    survey_distribution_results = run_survey_distribution_summary_cases(repo_root)
    for case in survey_distribution_results["cases"]:
        results["survey_distribution_summary"].append({"name": case["name"], "status": case["status"]})

    probabilistic_results = run_probabilistic_intake_summary_cases(repo_root)
    for case in probabilistic_results["cases"]:
        results["probabilistic_intake_summary"].append({"name": case["name"], "status": case["status"]})
    for comparison in probabilistic_results.get("fingerprintComparisons", []):
        results["probabilistic_intake_summary_fingerprints"].append(
            {"name": comparison["name"], "status": comparison["status"]}
        )

    uncertainty_results = run_uncertainty_intake_assessment_cases(repo_root)
    for case in uncertainty_results["cases"]:
        results["uncertainty_intake_assessment"].append({"name": case["name"], "status": case["status"]})

    censored_results = run_censored_residue_policy_cases(repo_root)
    for case in censored_results["cases"]:
        results["censored_residue_policy"].append({"name": case["name"], "status": case["status"]})

    sensitivity_results = run_uncertainty_sensitivity_cases(repo_root)
    for case in sensitivity_results["cases"]:
        results["uncertainty_sensitivity"].append({"name": case["name"], "status": case["status"]})

    health_reference_results = run_health_reference_exceedance_cases(repo_root)
    for case in health_reference_results["cases"]:
        results["health_reference_exceedance"].append({"name": case["name"], "status": case["status"]})

    reproducibility_results = run_uncertainty_reproducibility_cases(repo_root)
    for case in reproducibility_results["cases"]:
        results["uncertainty_reproducibility"].append({"name": case["name"], "status": case["status"]})

    food_vocabulary_results = run_food_vocabulary_cases(repo_root)
    for case in food_vocabulary_results["cases"]:
        results["food_vocabulary"].append({"name": case["name"], "status": case["status"]})

    source_database_results = run_source_database_cases(repo_root)
    for case in source_database_results["cases"]:
        results["source_databases"].append({"name": case["name"], "status": case["status"]})

    metals_monitoring_results = run_metals_monitoring_bundle_cases(repo_root)
    for case in metals_monitoring_results["cases"]:
        results["metals_monitoring"].append({"name": case["name"], "status": case["status"]})

    contaminant_monitoring_results = run_contaminant_monitoring_check_cases(repo_root)
    for case in contaminant_monitoring_results["cases"]:
        results["contaminant_monitoring"].append({"name": case["name"], "status": case["status"]})

    contaminant_monitoring_bundle_results = run_contaminant_monitoring_bundle_cases(repo_root)
    for case in contaminant_monitoring_bundle_results["cases"]:
        results["contaminant_monitoring_bundle"].append({"name": case["name"], "status": case["status"]})

    contaminant_monitoring_signoff_results = run_contaminant_monitoring_signoff_cases(repo_root)
    for case in contaminant_monitoring_signoff_results["cases"]:
        results["contaminant_monitoring_signoff"].append({"name": case["name"], "status": case["status"]})

    contaminant_monitoring_review_dossier_results = run_contaminant_monitoring_review_dossier_cases(repo_root)
    for case in contaminant_monitoring_review_dossier_results["cases"]:
        results["contaminant_monitoring_review_dossier"].append({"name": case["name"], "status": case["status"]})

    metals_monitoring_signoff_results = run_metals_monitoring_signoff_cases(repo_root)
    for case in metals_monitoring_signoff_results["cases"]:
        results["metals_monitoring_signoff"].append({"name": case["name"], "status": case["status"]})

    metals_monitoring_review_dossier_results = run_metals_monitoring_review_dossier_cases(repo_root)
    for case in metals_monitoring_review_dossier_results["cases"]:
        results["metals_monitoring_review_dossier"].append({"name": case["name"], "status": case["status"]})

    interoperability_results = run_interoperability_preview_cases(repo_root)
    for case in interoperability_results["cases"]:
        results["interoperability_preview"].append({"name": case["name"], "status": case["status"]})

    interoperability_readiness_results = run_interoperability_readiness_cases(repo_root)
    for case in interoperability_readiness_results["cases"]:
        results["interoperability_readiness"].append({"name": case["name"], "status": case["status"]})

    interoperability_remediation_results = run_interoperability_remediation_cases(repo_root)
    for case in interoperability_remediation_results["cases"]:
        results["interoperability_remediation"].append({"name": case["name"], "status": case["status"]})

    interoperability_signoff_results = run_interoperability_signoff_cases(repo_root)
    for case in interoperability_signoff_results["cases"]:
        results["interoperability_signoff"].append({"name": case["name"], "status": case["status"]})

    readiness_results = run_review_dossier_readiness_cases(repo_root)
    for case in readiness_results["cases"]:
        results["review_dossier_readiness"].append({"name": case["name"], "status": case["status"]})

    scientific_follow_up_bundle_results = run_scientific_follow_up_queue_bundle_cases(repo_root)
    for case in scientific_follow_up_bundle_results["cases"]:
        results["scientific_follow_up_queue_bundle"].append({"name": case["name"], "status": case["status"]})

    scientific_follow_up_review_board_results = run_scientific_follow_up_review_board_cases(repo_root)
    for case in scientific_follow_up_review_board_results["cases"]:
        results["scientific_follow_up_review_board"].append({"name": case["name"], "status": case["status"]})

    scientific_follow_up_owner_handoff_results = run_scientific_follow_up_owner_handoff_cases(repo_root)
    for case in scientific_follow_up_owner_handoff_results["cases"]:
        results["scientific_follow_up_owner_handoff"].append({"name": case["name"], "status": case["status"]})

    scientific_follow_up_owner_remediation_results = run_scientific_follow_up_owner_remediation_cases(repo_root)
    for case in scientific_follow_up_owner_remediation_results["cases"]:
        results["scientific_follow_up_owner_remediation"].append(
            {"name": case["name"], "status": case["status"]}
        )

    scientific_follow_up_owner_signoff_results = run_scientific_follow_up_owner_signoff_cases(repo_root)
    for case in scientific_follow_up_owner_signoff_results["cases"]:
        results["scientific_follow_up_owner_signoff"].append({"name": case["name"], "status": case["status"]})

    scientific_follow_up_owner_signoff_dossier_results = run_scientific_follow_up_owner_signoff_dossier_cases(
        repo_root
    )
    for case in scientific_follow_up_owner_signoff_dossier_results["cases"]:
        results["scientific_follow_up_owner_signoff_dossier"].append(
            {"name": case["name"], "status": case["status"]}
        )

    sanitised_results = run_sanitised_public_review_cases(repo_root)
    for case in sanitised_results["cases"]:
        results["sanitised_public_review"].append({"name": case["name"], "status": case["status"]})

    results["status"] = validation_results_status(results)
    results["suiteSummary"] = summarize_validation_results(results)
    return results


def validation_results_status(results: dict) -> str:
    for suite_name, cases in results.items():
        if suite_name in {"status", "suiteSummary"} or not isinstance(cases, list):
            continue
        for case in cases:
            if case.get("status") != "ok":
                return "review_required"
    return "ok"


def summarize_validation_results(results: dict) -> dict:
    suites = {}
    failures = []
    for suite_name, cases in results.items():
        if suite_name in {"status", "suiteSummary"} or not isinstance(cases, list):
            continue
        failed_cases = [
            {"name": case.get("name"), "status": case.get("status")}
            for case in cases
            if case.get("status") != "ok"
        ]
        suite_status = "ok" if not failed_cases else "review_required"
        suites[suite_name] = {
            "status": suite_status,
            "caseCount": len(cases),
            "failedCaseCount": len(failed_cases),
        }
        failures.extend({"suite": suite_name, **case} for case in failed_cases)
    return {
        "status": "ok" if not failures else "review_required",
        "suiteCount": len(suites),
        "caseCount": sum(suite["caseCount"] for suite in suites.values()),
        "failedCaseCount": len(failures),
        "suites": suites,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate generated Dietary MCP contract artifacts.")
    parser.add_argument(
        "--generate-artifacts",
        action="store_true",
        help="Regenerate contract artifacts before validation. Defaults to read-only validation.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    if args.generate_artifacts:
        generate_contract_artifacts(repo_root)
    results = validate_generated_artifacts(repo_root)
    summary = results.get("suiteSummary") or summarize_validation_results(results)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["status"] != "ok":
        sys.exit(1)


if __name__ == "__main__":
    main()
