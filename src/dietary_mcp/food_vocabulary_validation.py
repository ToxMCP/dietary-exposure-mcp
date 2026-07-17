from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.defaults import DefaultsRegistry


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_food_vocabulary_cases(repo_root: Path) -> dict:
    payload = json.loads((_validation_root(repo_root) / "food_vocabulary_cases.json").read_text())
    defaults = DefaultsRegistry(repo_root)
    results = []
    for case in payload["cases"]:
        resolved = defaults.resolve_commodity(case["inputCode"])
        observed_factor, _ = defaults.default_processing_factor(case["inputCode"])
        status = (
            "ok"
            if resolved.commodity.commodity_code == case["expectedCommodityCode"]
            and resolved.commodity.foodex2_code == case.get("expectedFoodex2Code")
            and (resolved.commodity.processed_status.value if resolved.commodity.processed_status else None)
            == case.get("expectedProcessedStatus")
            and abs(observed_factor - case["expectedProcessingFactor"]) <= 1e-12
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedCommodityCode": case["expectedCommodityCode"],
                "observedCommodityCode": resolved.commodity.commodity_code,
                "expectedFoodex2Code": case.get("expectedFoodex2Code"),
                "observedFoodex2Code": resolved.commodity.foodex2_code,
                "expectedProcessedStatus": case.get("expectedProcessedStatus"),
                "observedProcessedStatus": (
                    resolved.commodity.processed_status.value if resolved.commodity.processed_status else None
                ),
                "expectedProcessingFactor": case["expectedProcessingFactor"],
                "observedProcessingFactor": observed_factor,
            }
        )
    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
