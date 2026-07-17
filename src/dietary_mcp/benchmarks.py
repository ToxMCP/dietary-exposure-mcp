from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    BuildBoundedIntakeSummaryRequest,
    DietaryCommodityResidueInput,
    IntakeWindowSemantic,
    ResidueSourceType,
    ScenarioClass,
    SelectConsumptionProfileRequest,
    SourceReference,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


def _load_cases(repo_root: Path) -> list[dict]:
    candidate = repo_root / "validation" / "v1" / "benchmark_cases.json"
    path = candidate if candidate.exists() else runtime_asset_root() / "validation" / "v1" / "benchmark_cases.json"
    return json.loads(path.read_text())["cases"]


def run_benchmarks(repo_root: Path) -> dict:
    runtime = get_cached_dietary_runtime(repo_root)
    cases = []

    for case in _load_cases(repo_root):
        intake_window = IntakeWindowSemantic(case["intakeWindow"])
        scenario_class = ScenarioClass(case["scenarioClass"])
        consumption_profile = runtime.select_consumption_profile(
            SelectConsumptionProfileRequest(
                population_group=case["populationGroup"],
                intake_window=intake_window,
                required_commodity_codes=[item["commodityCode"] for item in case["residueRecords"]],
            )
        ).profile
        residue_profile = runtime.build_residue_profile(
            BuildDietaryResidueProfileRequest(
                chemical_identity=case["chemicalIdentity"],
                residue_records=[
                    DietaryCommodityResidueInput(
                        commodity_code=item["commodityCode"],
                        residue_concentration_mg_per_kg=item["residueConcentrationMgPerKg"],
                        lower_bound_mg_per_kg=item.get("lowerBoundMgPerKg"),
                        upper_bound_mg_per_kg=item.get("upperBoundMgPerKg"),
                        source_type=ResidueSourceType(item["sourceType"]),
                        source_reference=SourceReference(
                            source_id=f"benchmark.{case['name']}.{item['commodityCode']}",
                            title=f"Benchmark residue record for {case['name']}",
                            effective_date="2026-04-08",
                        ),
                    )
                    for item in case["residueRecords"]
                ],
            )
        )
        summary = runtime.summarize_intake(
            BuildBoundedIntakeSummaryRequest(
                scenario=runtime.build_dietary_intake_scenario(
                    BuildDietaryIntakeScenarioRequest(
                        chemical_identity=residue_profile.chemical_identity,
                        residue_profile=residue_profile,
                        consumption_profile=consumption_profile,
                        scenario_class=scenario_class,
                        intake_window_semantic=intake_window,
                    )
                )
            )
        )
        cases.append(
            {
                "name": case["name"],
                "expected": case["expectedTotalIntakeMgPerKgBwPerDay"],
                "observed": summary.total_intake_mg_per_kg_bw_per_day,
                "tolerance": case["tolerance"],
            }
        )
        if "expectedLowerBoundMgPerKgBwPerDay" in case:
            cases.append(
                {
                    "name": f"{case['name']}_lower_bound",
                    "expected": case["expectedLowerBoundMgPerKgBwPerDay"],
                    "observed": summary.lower_bound_total_intake_mg_per_kg_bw_per_day,
                    "tolerance": case["tolerance"],
                }
            )
        if "expectedUpperBoundMgPerKgBwPerDay" in case:
            cases.append(
                {
                    "name": f"{case['name']}_upper_bound",
                    "expected": case["expectedUpperBoundMgPerKgBwPerDay"],
                    "observed": summary.upper_bound_total_intake_mg_per_kg_bw_per_day,
                    "tolerance": case["tolerance"],
                }
            )

    for case in cases:
        case["status"] = "ok" if abs(case["observed"] - case["expected"]) <= case["tolerance"] else "failed"

    return {
        "status": "ok" if all(case["status"] == "ok" for case in cases) else "failed",
        "cases": cases,
    }
