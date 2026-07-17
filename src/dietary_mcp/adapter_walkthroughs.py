from __future__ import annotations

from pathlib import Path

from dietary_mcp.adapter_checks import (
    build_header_resolution,
    build_normalized_projection,
    read_csv_headers,
    resolve_template_for_model_family,
)
from dietary_mcp.adapter_validation import load_adapter_normalization_cases, normalize_adapter_case
from dietary_mcp.errors import DietaryRegistryError


def _input_headers(case: dict) -> list[str]:
    if case["inputMode"] == "tabular_rows_v1":
        return list(case["rows"][0].keys())
    return read_csv_headers(case["csvText"])


def _projection_for_walkthrough(summary) -> dict:
    projection = build_normalized_projection(summary)
    return {
        "scenarioClass": projection.scenario_class.value,
        "intakeWindow": projection.intake_window.value,
        "populationGroup": projection.population_group,
        "regionId": projection.region_id,
        "bodyWeightKg": projection.body_weight_kg,
        "totalIntakeMgPerKgBwPerDay": projection.total_intake_mg_per_kg_bw_per_day,
        "lowerBoundMgPerKgBwPerDay": projection.lower_bound_mg_per_kg_bw_per_day,
        "upperBoundMgPerKgBwPerDay": projection.upper_bound_mg_per_kg_bw_per_day,
        "commodityCodes": projection.commodity_codes,
        "commodityContributions": [
            {
                "commodityCode": item.commodity_code,
                "canonicalName": item.canonical_name,
                "foodex2Code": item.foodex2_code,
                "rpcCode": item.rpc_code,
                "rpcdCode": item.rpcd_code,
                "processedStatus": item.processed_status.value if item.processed_status else None,
                "mappingConfidence": item.mapping_confidence.value if item.mapping_confidence else None,
                "contributionMgPerKgBwPerDay": item.contribution_mg_per_kg_bw_per_day,
                "fractionOfTotal": item.fraction_of_total,
                "residueConcentrationMgPerKg": item.residue_concentration_mg_per_kg,
                "consumptionKgPerDay": item.consumption_kg_per_day,
                "appliedProcessingFactor": item.applied_processing_factor,
                "lowerBoundMgPerKgBwPerDay": item.lower_bound_mg_per_kg_bw_per_day,
                "upperBoundMgPerKgBwPerDay": item.upper_bound_mg_per_kg_bw_per_day,
            }
            for item in projection.commodity_contributions
        ],
        "dominantCommodityCodes": projection.dominant_commodity_codes,
        "sourceIds": projection.source_ids,
        "qualityFlagCodes": projection.quality_flag_codes,
        "limitationCodes": projection.limitation_codes,
        "assumptionParameters": projection.assumption_parameters,
    }


def _build_validation_checks(case: dict, projection: dict) -> dict:
    tolerance = case["expected"].get("tolerance", 1e-12)
    checks = {
        "total": abs(projection["totalIntakeMgPerKgBwPerDay"] - case["expected"]["totalIntakeMgPerKgBwPerDay"])
        <= tolerance,
        "commodityCodes": projection["commodityCodes"] == case["expected"]["commodityCodes"],
        "sourceIds": set(case["expected"].get("requiredSourceIds", [])).issubset(set(projection["sourceIds"])),
        "qualityFlags": set(case["expected"].get("requiredQualityFlagCodes", [])).issubset(
            set(projection["qualityFlagCodes"])
        ),
    }
    if "lowerBoundMgPerKgBwPerDay" in case["expected"]:
        checks["lowerBound"] = projection["lowerBoundMgPerKgBwPerDay"] == case["expected"]["lowerBoundMgPerKgBwPerDay"]
    if "upperBoundMgPerKgBwPerDay" in case["expected"]:
        checks["upperBound"] = projection["upperBoundMgPerKgBwPerDay"] == case["expected"]["upperBoundMgPerKgBwPerDay"]
    return checks


def build_adapter_walkthrough_manifest(repo_root: Path) -> dict:
    walkthroughs = []
    for case in load_adapter_normalization_cases(repo_root):
        template = resolve_template_for_model_family(repo_root, case["modelFamily"])
        walkthroughs.append(
            {
                "name": case["name"],
                "modelFamily": case["modelFamily"],
                "inputMode": case["inputMode"],
                "templateName": template["name"],
                "templateResourceUri": f"adapter-template://{template['name']}",
                "resourceUri": f"adapter-walkthrough://{case['name']}",
                "description": (
                    f"Validated {case['modelFamily']} walkthrough pairing {template['name']} "
                    "with a normalized-summary projection."
                ),
            }
        )
    return {"version": "v1", "walkthroughs": walkthroughs}


def build_adapter_walkthrough(repo_root: Path, walkthrough_name: str) -> dict:
    for case in load_adapter_normalization_cases(repo_root):
        if case["name"] != walkthrough_name:
            continue
        template = resolve_template_for_model_family(repo_root, case["modelFamily"])
        normalized = normalize_adapter_case(repo_root, case)
        projection = _projection_for_walkthrough(normalized["summary"])
        headers = _input_headers(case)
        header_resolution = [
            {
                "header": item.header,
                "canonicalField": item.canonical_field,
                "recognized": item.recognized,
            }
            for item in build_header_resolution(headers)
        ]
        validation_checks = _build_validation_checks(case, projection)
        return {
            "name": case["name"],
            "modelFamily": case["modelFamily"],
            "inputMode": case["inputMode"],
            "templateName": template["name"],
            "templateResourceUri": f"adapter-template://{template['name']}",
            "documentationResourceUri": "docs://adapter-import-walkthroughs",
            "profileSelection": {
                "regionId": case["regionId"],
                "populationGroup": case["populationGroup"],
                "intakeWindow": case["intakeWindow"],
                "scenarioClass": case["scenarioClass"],
            },
            "chemicalIdentity": case["chemicalIdentity"],
            "declaredTotals": {
                "totalIntakeMgPerKgBwPerDay": case["declaredTotalIntakeMgPerKgBwPerDay"],
                "lowerBoundMgPerKgBwPerDay": case.get("declaredLowerBoundMgPerKgBwPerDay"),
                "upperBoundMgPerKgBwPerDay": case.get("declaredUpperBoundMgPerKgBwPerDay"),
            },
            "inputHeaders": headers,
            "headerResolution": header_resolution,
            "sampleInput": {"rows": case["rows"]} if case["inputMode"] == "tabular_rows_v1" else {"csvText": case["csvText"]},
            "validationExpectation": case["expected"],
            "validationStatus": "ok" if all(validation_checks.values()) else "failed",
            "validationChecks": validation_checks,
            "expectedNormalizedProjection": projection,
            "notes": [
                "Walkthroughs are derived from governed adapter normalization cases.",
                "The normalized projection excludes runtime-generated IDs and timestamps so downstream diffing stays stable.",
                "These examples validate the harnessed compatibility pathway only and are not official PRIMo or DEEM outputs.",
            ],
        }
    raise DietaryRegistryError(
        code="unknown_adapter_walkthrough",
        message=f"Unknown adapter walkthrough: {walkthrough_name}.",
        suggestion="Use a walkthrough listed in adapter-import-walkthroughs://manifest.",
    )
