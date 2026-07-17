from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import IntakeWindowSemantic, SelectConsumptionProfileRequest
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_dietary_reference_cases(repo_root: Path) -> dict:
    payload = json.loads((_validation_root(repo_root) / "dietary_reference_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in payload["cases"]:
        expected_matched = sorted(
            set(
                case.get("expectedMatchedCommodities")
                or [
                    runtime.defaults.resolve_commodity(code).commodity.commodity_code
                    for code in case["commodityCoverage"]
                ]
            )
        )
        expected_missing = sorted(set(case.get("expectedMissingCommodities", [])))
        window_results = []

        for window in case["applicableWindows"]:
            selection = runtime.select_consumption_profile(
                SelectConsumptionProfileRequest(
                    region_id=case["regionId"],
                    population_group=case["populationGroup"],
                    intake_window=IntakeWindowSemantic(window),
                    preferred_profile_id=case.get("preferredProfileId"),
                    required_commodity_codes=case["commodityCoverage"],
                )
            )
            observed_matched = sorted(set(selection.matched_commodities))
            observed_missing = sorted(set(selection.missing_commodities))
            observed_windows = sorted(item.value for item in selection.profile.applicable_windows)

            window_status = (
                "ok"
                if selection.profile.population_group == case["populationGroup"]
                and selection.profile.region_id == case["regionId"]
                and observed_matched == expected_matched
                and observed_missing == expected_missing
                and window in observed_windows
                and (
                    case.get("expectedProfileId") is None
                    or selection.profile.profile_id == case["expectedProfileId"]
                )
                and (
                    case.get("expectedBodyWeightKg") is None
                    or abs(selection.profile.body_weight_kg - case["expectedBodyWeightKg"]) <= 1e-12
                )
                else "mismatch"
            )
            window_results.append(
                {
                    "window": window,
                    "status": window_status,
                    "observedProfileId": selection.profile.profile_id,
                    "observedBodyWeightKg": selection.profile.body_weight_kg,
                    "observedMatchedCommodities": observed_matched,
                    "observedMissingCommodities": observed_missing,
                    "observedApplicableWindows": observed_windows,
                }
            )

        overall_status = "ok" if all(item["status"] == "ok" for item in window_results) else "mismatch"
        results.append(
            {
                "name": case["name"],
                "status": overall_status,
                "expectedProfileId": case.get("expectedProfileId"),
                "expectedBodyWeightKg": case.get("expectedBodyWeightKg"),
                "expectedMatchedCommodities": expected_matched,
                "expectedMissingCommodities": expected_missing,
                "windowResults": window_results,
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
