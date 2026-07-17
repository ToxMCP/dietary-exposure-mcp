"""Deterministic Dietary -> WoE round-trip fixture builder."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from dietary_mcp.integrations import (
    export_pbpk_oral_input,
    export_toxclaw_dietary_evidence_bundle,
)
from dietary_mcp.models import (
    BuildBoundedIntakeSummaryRequest,
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    DietaryCommodityResidueInput,
    ExportPbpkOralInputRequest,
    ExportToxclawDietaryEvidenceBundleRequest,
    IntakeWindowSemantic,
    ResidueSourceType,
    ScenarioClass,
    SelectConsumptionProfileRequest,
)
from dietary_mcp.runtime import DietaryRuntime

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
WOE_ROUNDTRIP_FIXTURE_PATH = (
    WORKSPACE_ROOT
    / "tests"
    / "fixtures"
    / "cross_suite"
    / "woe_ngra"
    / "dietary_exposure_handoff.v1.1.0.json"
)
WOE_SYNC_TARGET_PATH = (
    WORKSPACE_ROOT.parent
    / "WoE_NGRA_Synthesis_MCP"
    / "src"
    / "integration"
    / "__fixtures__"
    / "dietary-exposure-woe-roundtrip.bundle.json"
)
IVIVE_SYNC_TARGET_PATH = (
    WORKSPACE_ROOT.parent
    / "IVIVE_BER_MCP"
    / "tests"
    / "fixtures"
    / "cross_suite"
    / "upstream"
    / "dietary_exposure_handoff.v1.1.0.json"
)

DETERMINISTIC_GENERATED_AT = "2026-04-21T12:00:00.000Z"
SOURCE_VERSION = "1.1.0"
SCHEMA_VERSION = "1.1.0"
BUNDLE_ID = "dietary-exposure-handoff-001"
CREATED_BY = "dietary-cross-suite-fixture-builder"
PRODUCER_MODULE = "dietary_exposure"

CASE_CONFIGS = (
    {
        "case_id": "dietary_food_mediated_chronic_screening",
        "population_group": "adult_general",
        "intake_window": IntakeWindowSemantic.CHRONIC,
        "scenario_class": ScenarioClass.POINT_ESTIMATE,
        "suffix": "chronic",
        "evidence_id": "dietary-exposure-chronic-001",
        "claim_id": "dietary-exposure-chronic-claim-001",
        "link_id": "dietary-exposure-chronic-link-001",
        "applicability_id": "dietary-exposure-chronic-app-001",
        "uncertainty_id": "dietary-exposure-chronic-unc-001",
        "scenario_id": "dietary-scenario-chronic-001",
        "summary_id": "dietary-summary-chronic-001",
        "route_dose_id": "route-dose-dietary-chronic-001",
        "pbpk_bundle_id": "pbpk-bundle-dietary-chronic-001",
        "toxclaw_bundle_id": "toxclaw-bundle-dietary-chronic-001",
        "residue_profile_id": "dietary-residue-profile-chronic-001",
        "line_of_evidence_id": "loe-dietary-chronic",
    },
    {
        "case_id": "dietary_food_mediated_acute_screening",
        "population_group": "child_1_6",
        "intake_window": IntakeWindowSemantic.ACUTE,
        "scenario_class": ScenarioClass.BOUNDED_ACUTE,
        "suffix": "acute",
        "evidence_id": "dietary-exposure-acute-001",
        "claim_id": "dietary-exposure-acute-claim-001",
        "link_id": "dietary-exposure-acute-link-001",
        "applicability_id": "dietary-exposure-acute-app-001",
        "uncertainty_id": "dietary-exposure-acute-unc-001",
        "scenario_id": "dietary-scenario-acute-001",
        "summary_id": "dietary-summary-acute-001",
        "route_dose_id": "route-dose-dietary-acute-001",
        "pbpk_bundle_id": "pbpk-bundle-dietary-acute-001",
        "toxclaw_bundle_id": "toxclaw-bundle-dietary-acute-001",
        "residue_profile_id": "dietary-residue-profile-acute-001",
        "line_of_evidence_id": "loe-dietary-acute",
    },
)


def _sorted_json(value: Any) -> Any:
    if isinstance(value, list):
        return [_sorted_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _sorted_json(item) for key, item in sorted(value.items())}
    return value


def _stable_json_dumps(value: Any) -> str:
    return json.dumps(_sorted_json(value), indent=2)


def _hash_value(value: Any) -> str:
    return sha256(_stable_json_dumps(value).encode("utf-8")).hexdigest()


def _replace_generated_at(value: Any) -> Any:
    if isinstance(value, list):
        return [_replace_generated_at(item) for item in value]
    if isinstance(value, dict):
        updated = {}
        for key, item in value.items():
            if key in {"generated_at", "executed_at"}:
                updated[key] = DETERMINISTIC_GENERATED_AT
            else:
                updated[key] = _replace_generated_at(item)
        return updated
    return value


def _with_generated_at(value: dict[str, Any]) -> dict[str, Any]:
    return _replace_generated_at(json.loads(json.dumps(value)))


def _freeze_residue_profile(snapshot: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    residue_profile = snapshot.get("residue_profile")
    if not isinstance(residue_profile, dict):
        return snapshot
    residue_profile["profile_id"] = config["residue_profile_id"]
    for index, record in enumerate(residue_profile.get("records", []), start=1):
        if not isinstance(record, dict):
            continue
        commodity = record.get("commodity")
        commodity_code = (
            commodity.get("commodity_code")
            if isinstance(commodity, dict)
            else f"record-{index:02d}"
        )
        record["record_id"] = f"dietary-residue-record-{config['suffix']}-{commodity_code}"
    return snapshot


def _freeze_scenario_snapshot(snapshot: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    updated = _with_generated_at(snapshot)
    updated["scenario_id"] = config["scenario_id"]
    return _freeze_residue_profile(updated, config)


def _freeze_summary_snapshot(snapshot: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    updated = _with_generated_at(snapshot)
    updated["summary_id"] = config["summary_id"]
    updated["scenario_id"] = config["scenario_id"]
    result_metadata = updated.get("result_metadata")
    if isinstance(result_metadata, dict):
        result_metadata["result_id"] = f"result-{config['scenario_id']}-0.1.0"
    return updated


def _freeze_pbpk_snapshot(snapshot: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    updated = _with_generated_at(snapshot)
    updated["bundle_id"] = config["pbpk_bundle_id"]
    route_dose = updated.get("route_dose_estimate")
    if isinstance(route_dose, dict):
        route_dose["estimate_id"] = config["route_dose_id"]
        route_dose["scenario_id"] = config["scenario_id"]
    return updated


def _freeze_toxclaw_snapshot(snapshot: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    updated = _with_generated_at(snapshot)
    updated["bundle_id"] = config["toxclaw_bundle_id"]
    scenario = updated.get("scenario")
    if isinstance(scenario, dict):
        scenario["scenario_id"] = config["scenario_id"]
        _freeze_residue_profile({"residue_profile": scenario.get("residue_profile")}, config)
    summary = updated.get("summary")
    if isinstance(summary, dict):
        summary["summary_id"] = config["summary_id"]
        summary["scenario_id"] = config["scenario_id"]
        result_metadata = summary.get("result_metadata")
        if isinstance(result_metadata, dict):
            result_metadata["result_id"] = f"result-{config['scenario_id']}-0.1.0"
    route_dose = updated.get("route_dose_estimate")
    if isinstance(route_dose, dict):
        route_dose["estimate_id"] = config["route_dose_id"]
        route_dose["scenario_id"] = config["scenario_id"]
    return updated


def _typed_ref(
    *,
    object_type_ref: str,
    artifact_id: str,
    cached_snapshot: dict[str, Any],
) -> dict[str, Any]:
    return {
        "objectType": "typedHandoffRef",
        "schemaVersion": "1.1.0",
        "objectTypeRef": object_type_ref,
        "cachedSnapshot": cached_snapshot,
        "artifactId": artifact_id,
        "producerModule": PRODUCER_MODULE,
        "producerVersion": "0.1.0",
        "integrityHash": f"sha256:{_hash_value(cached_snapshot)}",
    }


def _evidence_provenance(tool_run_id: str, source_snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "toolRunId": tool_run_id,
        "createdAt": DETERMINISTIC_GENERATED_AT,
        "createdBy": CREATED_BY,
        "sourceHashes": [
            {
                "algorithm": "sha256",
                "value": _hash_value(source_snapshot),
            }
        ],
    }


def _build_runtime() -> DietaryRuntime:
    return DietaryRuntime(WORKSPACE_ROOT)


def _build_residue_profile(runtime: DietaryRuntime):
    return runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Illustrative residue", "casrn": "100-00-0"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.15,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.20,
                    source_type=ResidueSourceType.MONITORING,
                    source_reference={
                        "source_id": "example.apple.monitoring",
                        "title": "Illustrative apple monitoring record",
                        "effective_date": "2026-04-08",
                    },
                ),
                DietaryCommodityResidueInput(
                    commodity_code="spinach",
                    residue_concentration_mg_per_kg=0.05,
                    lower_bound_mg_per_kg=0.03,
                    upper_bound_mg_per_kg=0.08,
                    processing_factor=0.85,
                    source_type=ResidueSourceType.MODELED,
                    source_reference={
                        "source_id": "example.spinach.modeled",
                        "title": "Illustrative spinach modeled record",
                        "effective_date": "2026-04-08",
                    },
                ),
                DietaryCommodityResidueInput(
                    commodity_code="rice",
                    residue_concentration_mg_per_kg=0.02,
                    source_type=ResidueSourceType.USER_SUPPLIED,
                    source_reference={
                        "source_id": "example.rice.user",
                        "title": "Illustrative rice residue input",
                        "effective_date": "2026-04-08",
                    },
                ),
            ],
        )
    )


def _route_metric_keys(summary_snapshot: dict[str, Any]) -> list[str]:
    keys = ["total_intake_mg_per_kg_bw_per_day"]
    if summary_snapshot.get("lower_bound_total_intake_mg_per_kg_bw_per_day") is not None:
        keys.append("lower_bound_total_intake_mg_per_kg_bw_per_day")
    if summary_snapshot.get("upper_bound_total_intake_mg_per_kg_bw_per_day") is not None:
        keys.append("upper_bound_total_intake_mg_per_kg_bw_per_day")
    return keys


def build_dietary_woe_roundtrip_bundle() -> dict[str, Any]:
    runtime = _build_runtime()
    residue_profile = _build_residue_profile(runtime)

    evidence_items: list[dict[str, Any]] = []
    claim_items: list[dict[str, Any]] = []
    link_items: list[dict[str, Any]] = []
    applicability_items: list[dict[str, Any]] = []
    uncertainty_items: list[dict[str, Any]] = []

    for config in CASE_CONFIGS:
        selection = runtime.select_consumption_profile(
            SelectConsumptionProfileRequest(
                population_group=config["population_group"],
                intake_window=config["intake_window"],
                required_commodity_codes=["apples", "spinach", "rice"],
            )
        )
        scenario = runtime.build_dietary_intake_scenario(
            BuildDietaryIntakeScenarioRequest(
                chemical_identity=residue_profile.chemical_identity,
                residue_profile=residue_profile,
                consumption_profile=selection.profile,
                scenario_class=config["scenario_class"],
                intake_window_semantic=config["intake_window"],
            )
        )
        summary = runtime.summarize_intake(BuildBoundedIntakeSummaryRequest(scenario=scenario))
        pbpk_bundle = export_pbpk_oral_input(
            ExportPbpkOralInputRequest(scenario=scenario, summary=summary),
            runtime.provenance,
        )
        toxclaw_bundle = export_toxclaw_dietary_evidence_bundle(
            ExportToxclawDietaryEvidenceBundleRequest(scenario=scenario, summary=summary),
            runtime.provenance,
        )

        scenario_snapshot = _freeze_scenario_snapshot(
            scenario.model_dump(mode="json", by_alias=True),
            config,
        )
        summary_snapshot = _freeze_summary_snapshot(
            summary.model_dump(mode="json", by_alias=True),
            config,
        )
        pbpk_snapshot = _freeze_pbpk_snapshot(
            pbpk_bundle.model_dump(mode="json", by_alias=True),
            config,
        )
        toxclaw_snapshot = _freeze_toxclaw_snapshot(
            toxclaw_bundle.model_dump(mode="json", by_alias=True),
            config,
        )

        dose_metric = pbpk_snapshot["route_dose_estimate"]["dose_metric"]
        dose_value = pbpk_snapshot["route_dose_estimate"]["value_mg_per_kg_bw_per_day"]
        dose_unit = "mg/kg/day"
        intake_window_value = summary_snapshot["intake_window_semantic"]
        scenario_class_value = summary_snapshot["scenario_class"]
        claim_text = (
            "Food-mediated dietary screening for "
            f"{summary_snapshot['population_group']} {intake_window_value} intake "
            f"yields {dose_value:.12f} {dose_unit}."
        )

        evidence_items.append(
            {
                "originalId": config["evidence_id"],
                "evidenceClass": "exposure",
                "sourceModule": "exposure_ingress_v1",
                "provenance": _evidence_provenance(
                    f"{config['evidence_id']}-run",
                    {
                        "scenarioId": config["scenario_id"],
                        "summaryId": config["summary_id"],
                        "doseValue": dose_value,
                        "populationGroup": summary_snapshot["population_group"],
                        "intakeWindow": intake_window_value,
                    },
                ),
                "endpointFamily": "dietary_oral_exposure",
                "biologicalLevel": "organism",
                "methodMaturity": "deterministic_screening",
                "methodDescription": (
                    "Food-mediated dietary intake screening derived from governed residue "
                    "and consumption profiles."
                ),
                "studyIdentifiers": [
                    {
                        "identifierType": "benchmark_case_id",
                        "identifierValue": config["case_id"],
                    },
                    {
                        "identifierType": "scenario_id",
                        "identifierValue": config["scenario_id"],
                    },
                    {
                        "identifierType": "summary_id",
                        "identifierValue": config["summary_id"],
                    },
                    {
                        "identifierType": "intake_window_semantic",
                        "identifierValue": intake_window_value,
                    },
                    {
                        "identifierType": "scenario_class",
                        "identifierValue": scenario_class_value,
                    },
                    {
                        "identifierType": "population_group",
                        "identifierValue": summary_snapshot["population_group"],
                    },
                    {
                        "identifierType": "route_mechanism",
                        "identifierValue": "food_mediated_oral_intake",
                    },
                ],
                "schemaVersion": SCHEMA_VERSION,
                "exposureMetric": dose_metric,
                "exposureScenario": "food_mediated_dietary_intake",
                "aggregateExposure": False,
                "sourceScenarioId": config["scenario_id"],
                "route": summary_snapshot["route"],
                "productName": (
                    f"{scenario_snapshot['chemical_identity']['preferredName']} "
                    f"dietary {intake_window_value} screening"
                ),
                "productCategory": "food_mediated_residue",
                "populationGroup": summary_snapshot["population_group"],
                "region": summary_snapshot["region_id"],
                "intendedUseFamily": "dietary",
                "oralExposureContext": "food_mediated",
                "doseValue": dose_value,
                "doseUnit": dose_unit,
                "routeMetricKeys": _route_metric_keys(summary_snapshot),
                "upstreamArtifactRefs": [
                    _typed_ref(
                        object_type_ref="DietaryIntakeScenarioDefinition",
                        artifact_id=config["scenario_id"],
                        cached_snapshot=scenario_snapshot,
                    ),
                    _typed_ref(
                        object_type_ref="DietaryIntakeSummary",
                        artifact_id=config["summary_id"],
                        cached_snapshot=summary_snapshot,
                    ),
                    _typed_ref(
                        object_type_ref="RouteDoseEstimate",
                        artifact_id=config["route_dose_id"],
                        cached_snapshot=pbpk_snapshot["route_dose_estimate"],
                    ),
                    _typed_ref(
                        object_type_ref="PbpkExternalImportBundle",
                        artifact_id=config["pbpk_bundle_id"],
                        cached_snapshot=pbpk_snapshot,
                    ),
                    _typed_ref(
                        object_type_ref="ToxclawDietaryEvidenceBundle",
                        artifact_id=config["toxclaw_bundle_id"],
                        cached_snapshot=toxclaw_snapshot,
                    ),
                ],
            }
        )

        claim_items.append(
            {
                "originalId": config["claim_id"],
                "claimText": claim_text,
                "claimType": "quantitative",
                "supportStatus": "supports",
                "confidence": "moderate",
                "evidenceObjectIds": [config["evidence_id"]],
                "lineOfEvidenceId": config["line_of_evidence_id"],
                "rationale": (
                    "Dietary MCP preserves food-mediated intake semantics while exporting a "
                    "bounded oral-dose estimate for downstream review."
                ),
                "provenance": _evidence_provenance(
                    f"{config['claim_id']}-run",
                    {
                        "routeDoseId": config["route_dose_id"],
                        "pbpkBundleId": config["pbpk_bundle_id"],
                        "doseValue": dose_value,
                    },
                ),
                "applicabilityRecordId": config["applicability_id"],
            }
        )

        link_items.append(
            {
                "originalId": config["link_id"],
                "sourceId": config["evidence_id"],
                "sourceType": "evidence",
                "targetId": config["claim_id"],
                "targetType": "claim",
                "relationType": "supports",
                "rationale": (
                    "The deterministic dietary exposure estimate directly supports the "
                    "food-mediated oral screening claim."
                ),
                "strength": "direct",
                "bidirectional": False,
                "provenance": _evidence_provenance(
                    f"{config['link_id']}-run",
                    {
                        "sourceId": config["evidence_id"],
                        "targetId": config["claim_id"],
                    },
                ),
            }
        )

        applicability_items.append(
            {
                "originalId": config["applicability_id"],
                "evidenceClass": "exposure",
                "intendedUse": "woe_ngra_dietary_exposure",
                "dimensionAssessments": [
                    {
                        "dimension": "route",
                        "status": "direct",
                        "rationale": "Dietary export remains oral and food-mediated.",
                        "evidenceValue": summary_snapshot["route"],
                        "targetValue": "oral",
                    },
                    {
                        "dimension": "method_domain",
                        "status": "direct",
                        "rationale": "Dietary MCP preserves the intake window and scenario class explicitly.",
                        "evidenceValue": intake_window_value,
                        "targetValue": intake_window_value,
                    },
                    {
                        "dimension": "matrix",
                        "status": "direct",
                        "rationale": "The bundle remains food-mediated residue intake rather than product-centric direct use.",
                        "evidenceValue": "food_mediated",
                        "targetValue": "food_mediated",
                    },
                ],
                "overallStatus": "direct",
                "materiality": "material",
                "affectedObjectIds": [config["evidence_id"]],
                "provenance": _evidence_provenance(
                    f"{config['applicability_id']}-run",
                    {
                        "scenarioId": config["scenario_id"],
                        "intakeWindow": intake_window_value,
                        "scenarioClass": scenario_class_value,
                        "oralExposureContext": "food_mediated",
                    },
                ),
            }
        )

        uncertainty_items.append(
            {
                "originalId": config["uncertainty_id"],
                "uncertaintyClass": "policy_default",
                "burdenLevel": "moderate",
                "affectedObjectIds": [config["evidence_id"]],
                "rationale": (
                    "Dietary screening remains bounded by residue, consumption-profile, and "
                    "processing-factor assumptions and should not be treated as a final intake conclusion."
                ),
                "reducibility": "partially_reducible",
                "directionality": "unknown",
                "mitigationPath": (
                    "Escalate to reviewed residue evidence, population-specific intake data, or "
                    "PBPK/BER analysis before drawing stronger interpretive conclusions."
                ),
                "provenance": _evidence_provenance(
                    f"{config['uncertainty_id']}-run",
                    {
                        "scenarioId": config["scenario_id"],
                        "summaryId": config["summary_id"],
                        "pbpkBundleId": config["pbpk_bundle_id"],
                    },
                ),
            }
        )

    return _sorted_json(
        {
            "sourceFormat": "structured_json_bundle",
            "sourceVersion": SOURCE_VERSION,
            "bundleId": BUNDLE_ID,
            "schemaVersion": SCHEMA_VERSION,
            "createdAt": DETERMINISTIC_GENERATED_AT,
            "createdBy": CREATED_BY,
            "targetConsumer": "woe_ngra",
            "evidenceItems": evidence_items,
            "claimItems": claim_items,
            "linkItems": link_items,
            "applicabilityItems": applicability_items,
            "uncertaintyItems": uncertainty_items,
        }
    )


def write_dietary_woe_roundtrip_bundle(path: Path = WOE_ROUNDTRIP_FIXTURE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{json.dumps(build_dietary_woe_roundtrip_bundle(), indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
