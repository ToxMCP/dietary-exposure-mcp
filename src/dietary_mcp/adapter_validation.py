from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from dietary_mcp.adapter_harness import (
    build_external_adapter_summary_from_csv,
    build_external_adapter_summary_from_rows,
    normalize_external_adapter_summary,
)
from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    DietaryCommodityResidueInput,
    IntakeWindowSemantic,
    ModelFamily,
    ResidueSourceType,
    ScenarioClass,
    SelectConsumptionProfileRequest,
    SourceReference,
)

if TYPE_CHECKING:
    from dietary_mcp.runtime import DietaryRuntime


def load_adapter_normalization_cases(repo_root: Path) -> list[dict]:
    candidate = repo_root / "validation" / "v1" / "adapter_normalization_cases.json"
    path = candidate if candidate.exists() else runtime_asset_root() / "validation" / "v1" / "adapter_normalization_cases.json"
    return json.loads(path.read_text())["cases"]


def _normalize_adapter_case(runtime: DietaryRuntime, case: dict) -> dict:
    intake_window = IntakeWindowSemantic(case["intakeWindow"])
    scenario_class = ScenarioClass(case["scenarioClass"])
    model_family = ModelFamily(case["modelFamily"])
    profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            region_id=case["regionId"],
            population_group=case["populationGroup"],
            intake_window=intake_window,
            required_commodity_codes=[item["commodityCode"] for item in case["residueRecords"]],
        )
    ).profile
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity=case["chemicalIdentity"],
            region_id=case["regionId"],
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code=item["commodityCode"],
                    residue_concentration_mg_per_kg=item["residueConcentrationMgPerKg"],
                    lower_bound_mg_per_kg=item.get("lowerBoundMgPerKg"),
                    upper_bound_mg_per_kg=item.get("upperBoundMgPerKg"),
                    source_type=ResidueSourceType(item["sourceType"]),
                    source_reference=SourceReference(
                        source_id=f"adapter-validation.{case['name']}.{item['commodityCode']}",
                        title=f"Adapter validation residue record for {case['name']}",
                        effective_date="2026-04-08",
                    ),
                )
                for item in case["residueRecords"]
            ],
        )
    )
    scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=residue_profile.chemical_identity,
            residue_profile=residue_profile,
            consumption_profile=profile,
            scenario_class=scenario_class,
            intake_window_semantic=intake_window,
            model_family=model_family,
        )
    )

    if case["inputMode"] == "tabular_rows_v1":
        payload = build_external_adapter_summary_from_rows(
            model_family=model_family,
            external_case_id=case["externalCaseId"],
            external_engine_version=case["externalEngineVersion"],
            total_intake_mg_per_kg_bw_per_day=case["declaredTotalIntakeMgPerKgBwPerDay"],
            lower_bound_total_intake_mg_per_kg_bw_per_day=case.get("declaredLowerBoundMgPerKgBwPerDay"),
            upper_bound_total_intake_mg_per_kg_bw_per_day=case.get("declaredUpperBoundMgPerKgBwPerDay"),
            rows=case["rows"],
        )
    else:
        payload = build_external_adapter_summary_from_csv(
            model_family=model_family,
            external_case_id=case["externalCaseId"],
            external_engine_version=case["externalEngineVersion"],
            total_intake_mg_per_kg_bw_per_day=case["declaredTotalIntakeMgPerKgBwPerDay"],
            lower_bound_total_intake_mg_per_kg_bw_per_day=case.get("declaredLowerBoundMgPerKgBwPerDay"),
            upper_bound_total_intake_mg_per_kg_bw_per_day=case.get("declaredUpperBoundMgPerKgBwPerDay"),
            csv_text=case["csvText"],
        )

    summary = normalize_external_adapter_summary(
        payload,
        scenario,
        runtime.defaults,
        runtime.provenance,
    )
    return {"scenario": scenario, "payload": payload, "summary": summary}


def normalize_adapter_case(repo_root: Path, case: dict) -> dict:
    from dietary_mcp.runtime import DietaryRuntime

    return _normalize_adapter_case(DietaryRuntime(repo_root), case)


def run_adapter_normalization_cases(repo_root: Path) -> dict:
    from dietary_mcp.runtime import get_cached_dietary_runtime

    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in load_adapter_normalization_cases(repo_root):
        summary = _normalize_adapter_case(runtime, case)["summary"]

        expected_codes = case["expected"]["commodityCodes"]
        observed_codes = [item.commodity.commodity_code for item in summary.commodity_contributions]
        expected_source_ids = set(case["expected"].get("requiredSourceIds", []))
        observed_source_ids = {item.source_id for item in summary.provenance.source_references}
        expected_quality_flag_codes = set(case["expected"].get("requiredQualityFlagCodes", []))
        observed_quality_flag_codes = {item.code for item in summary.quality_flags}
        tolerance = case["expected"].get("tolerance", 1e-12)

        checks = {
            "total": abs(summary.total_intake_mg_per_kg_bw_per_day - case["expected"]["totalIntakeMgPerKgBwPerDay"])
            <= tolerance,
            "commodityCodes": observed_codes == expected_codes,
            "sourceIds": expected_source_ids.issubset(observed_source_ids),
            "qualityFlags": expected_quality_flag_codes.issubset(observed_quality_flag_codes),
        }
        if "lowerBoundMgPerKgBwPerDay" in case["expected"]:
            checks["lowerBound"] = (
                summary.lower_bound_total_intake_mg_per_kg_bw_per_day
                == case["expected"]["lowerBoundMgPerKgBwPerDay"]
            )
        if "upperBoundMgPerKgBwPerDay" in case["expected"]:
            checks["upperBound"] = (
                summary.upper_bound_total_intake_mg_per_kg_bw_per_day
                == case["expected"]["upperBoundMgPerKgBwPerDay"]
            )

        results.append(
            {
                "name": case["name"],
                "status": "ok" if all(checks.values()) else "failed",
                "checks": checks,
                "observedTotal": summary.total_intake_mg_per_kg_bw_per_day,
            }
        )

    return {
        "status": "ok" if all(item["status"] == "ok" for item in results) else "failed",
        "cases": results,
    }
