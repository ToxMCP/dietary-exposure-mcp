#!/usr/bin/env python3
"""Regenerate the Track-B scientific-invariants gate corpus from the REAL producer.

The gate corpus under ``tests/governance_spine/corpus/`` is the set of FAITHFUL
real-producer emissions of every server-authored interpretive surface dietary
gates, captured exactly as the MCP server serializes a tool result
(``model_dump(mode="json", by_alias=True)``). It is NOT hand-authored and NOT the
stale ``schemas/examples/*`` fixtures (which fail their own released schemas).

Run ``uv run python scripts/generate_governance_corpus.py`` after any change to a
gated producer's emission shape; the committed corpus must round-trip byte-for-byte
(minus the non-deterministic ``result_metadata.executed_at`` / ``provenance.
generated_at`` timestamps, which the projection never reads and which this script
pins to a fixed value for reproducibility).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from dietary_mcp.integrations import export_adapter_review_bundle  # noqa: E402
from dietary_mcp.models import (  # noqa: E402
    AssessInteroperabilityPreviewReadinessRequest,
    AssessReviewDossierReadinessRequest,
    BuildBoundedIntakeSummaryRequest,
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    CheckAdapterImportRequest,
    CheckContaminantMonitoringImportRequest,
    CompareAdapterImportToWalkthroughRequest,
    ContaminantFamily,
    DietaryCommodityResidueInput,
    EvaluateGlobalTradeRiskRequest,
    ExportAdapterReviewBundleRequest,
    ExportContaminantMonitoringInterpretationBundleRequest,
    ExportContaminantMonitoringSignoffPacketRequest,
    ExportVersionPinnedContaminantMonitoringReviewDossierRequest,
    ExportInteroperabilityPreviewRequest,
    ExportInteroperabilityRemediationBundleRequest,
    ExportInteroperabilitySignoffPacketRequest,
    ExportMetalsMonitoringInterpretationBundleRequest,
    ExportMetalsMonitoringSignoffPacketRequest,
    ExportScientificFollowUpOwnerHandoffPacketRequest,
    ExportScientificFollowUpOwnerRemediationPacketRequest,
    ExportScientificFollowUpOwnerSignoffPacketRequest,
    ExportScientificFollowUpQueueBundleRequest,
    ExportScientificFollowUpReviewBoardRequest,
    ExportSanitisedPublicReviewDossierRequest,
    ExportTradeRiskReviewBundleRequest,
    ExportVersionPinnedAdapterReviewDossierRequest,
    IntakeWindowSemantic,
    LookupMetalsOccurrenceRequest,
    LookupMetalsReviewFocusRequest,
    ModelFamily,
    ResidueSourceType,
    ScenarioClass,
    SelectConsumptionProfileRequest,
)
from dietary_mcp.runtime import DietaryRuntime  # noqa: E402

CORPUS_DIR = REPO_ROOT / "tests" / "governance_spine" / "corpus"

# Deterministic stamps for the non-deterministic provenance/result-metadata fields
# (the projection never reads them; pinning keeps the corpus reproducible).
_FIXED_TS = "2026-01-01T00:00:00Z"


def _pin_timestamps(obj: dict) -> dict:
    rm = obj.get("result_metadata")
    if isinstance(rm, dict) and "executed_at" in rm:
        rm["executed_at"] = _FIXED_TS
    prov = obj.get("provenance")
    if isinstance(prov, dict) and "generated_at" in prov:
        prov["generated_at"] = _FIXED_TS
    return obj


def _dump(model) -> dict:
    return model.model_dump(mode="json", by_alias=True)


def main() -> int:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    rt = DietaryRuntime(REPO_ROOT)

    # --- dietaryIntakeSummary (external oral-dose intake estimate) -----------
    profile = rt.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.15,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
        )
    )
    consumption = rt.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            required_commodity_codes=["apples", "milk"],
        )
    ).profile
    scenario = rt.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=profile.chemical_identity,
            residue_profile=profile,
            consumption_profile=consumption,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            intake_window_semantic=IntakeWindowSemantic.ACUTE,
        )
    )
    summary = rt.summarize_intake(BuildBoundedIntakeSummaryRequest(scenario=scenario))

    # --- contaminant interpretation bundle + signoff packet ------------------
    ccr = rt.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,"
                "measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    bundle = rt.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=ccr)
    )
    packet = rt.export_contaminant_monitoring_signoff_packet(
        ExportContaminantMonitoringSignoffPacketRequest(
            interpretation_bundle=bundle,
            reviewer_id="runtime.contaminant",
            reviewer_role="scientific_reviewer",
        )
    )

    # --- adapter review bundle ----------------------------------------------
    check_result = rt.check_adapter_import(
        CheckAdapterImportRequest(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            population_group="child_1_6",
            intake_window=IntakeWindowSemantic.ACUTE,
            scenario_class=ScenarioClass.BOUNDED_ACUTE,
            chemical_identity={"preferredName": "Example"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.18,
                    lower_bound_mg_per_kg=0.12,
                    upper_bound_mg_per_kg=0.24,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.03,
                    source_type=ResidueSourceType.CURATED_DEFAULT,
                ),
            ],
            external_engine_version="3.1-harness",
            declared_total_intake_mg_per_kg_bw_per_day=0.00416,
            declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
            declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
            csv_text=(
                "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,"
                "lb_mgkgbwday,ub_mgkgbwday\n"
                "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
            ),
        )
    )
    comparison = rt.compare_adapter_import_to_walkthrough(
        CompareAdapterImportToWalkthroughRequest(
            check_result=check_result,
            walkthrough_name="efsa_primo_tabular_alias_case",
        )
    )
    adapter = export_adapter_review_bundle(
        ExportAdapterReviewBundleRequest(
            check_result=check_result, comparison_result=comparison
        )
    )

    # --- BC-6 exhaustive-sweep newly-gated surfaces --------------------------
    # metals monitoring interpretation bundle + signoff packet (the laundering
    # channel sibling of the contaminant signoff packet).
    metals_occurrence = rt.lookup_metals_occurrence(
        LookupMetalsOccurrenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )
    metals_review_focus = rt.lookup_metals_review_focus(
        LookupMetalsReviewFocusRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )
    metals_bundle = rt.export_metals_monitoring_interpretation_bundle(
        ExportMetalsMonitoringInterpretationBundleRequest(
            occurrence_result=metals_occurrence,
            review_focus_result=metals_review_focus,
        )
    )
    metals_signoff = rt.export_metals_monitoring_signoff_packet(
        ExportMetalsMonitoringSignoffPacketRequest(
            interpretation_bundle=metals_bundle,
            reviewer_id="runtime.metals",
            reviewer_role="scientific_reviewer",
        )
    )

    # trade-risk review bundle (embeds a GlobalTradeRiskReport with its own notes).
    trade_report = rt.evaluate_global_trade_risk(
        EvaluateGlobalTradeRiskRequest(
            chemical_identity={"preferredName": "glyphosate"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="grapes",
                    residue_concentration_mg_per_kg=0.2,
                    source_type="monitoring",
                )
            ],
            target_jurisdictions=["us", "codex_global"],
        )
    )
    trade_bundle = rt.export_trade_risk_review_bundle(
        ExportTradeRiskReviewBundleRequest(
            trade_report=trade_report,
            bundle_note="Illustrative review note for trade-risk bundle testing.",
        )
    )

    # interoperability signoff packet (adapter -> dossier -> preview -> assessment
    # -> remediation -> signoff).
    interop_dossier = rt.export_version_pinned_adapter_review_dossier(
        ExportVersionPinnedAdapterReviewDossierRequest(
            review_bundle=export_adapter_review_bundle(
                ExportAdapterReviewBundleRequest(
                    check_result=check_result, comparison_result=comparison
                )
            )
        )
    )
    interop_preview = rt.export_interoperability_preview(
        ExportInteroperabilityPreviewRequest(
            dossier=interop_dossier, target_profile="oht_85_iuclid_json_preview"
        )
    )
    interop_assessment = rt.assess_interoperability_preview_readiness(
        AssessInteroperabilityPreviewReadinessRequest(
            dossier=interop_dossier,
            preview=interop_preview,
            target_profile="eu_internal_exchange_preview",
        )
    )
    interop_remediation = rt.export_interoperability_remediation_bundle(
        ExportInteroperabilityRemediationBundleRequest(
            dossier=interop_dossier,
            preview=interop_preview,
            assessment=interop_assessment,
        )
    )
    interop_signoff = rt.export_interoperability_signoff_packet(
        ExportInteroperabilitySignoffPacketRequest(
            remediation_bundle=interop_remediation,
            reviewer_id="runtime.reviewer",
            reviewer_role="regulatory_reviewer",
        )
    )

    # scientific follow-up owner signoff packet (contaminant dossier -> readiness ->
    # queue -> board -> handoff -> remediation -> owner signoff) + the sanitised
    # public review dossier derived from the same contaminant dossier.
    contaminant_dossier = rt.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=bundle,
            signoff_packet=packet,
        )
    )
    sfu_readiness = rt.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=contaminant_dossier,
            target_profile="mercury_internal_review",
        )
    )
    sfu_queue = rt.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(
            dossier=contaminant_dossier, assessment=sfu_readiness
        )
    )
    sfu_board = rt.export_scientific_follow_up_review_board(
        ExportScientificFollowUpReviewBoardRequest(queue_bundle=sfu_queue)
    )
    sfu_handoff = rt.export_scientific_follow_up_owner_handoff_packet(
        ExportScientificFollowUpOwnerHandoffPacketRequest(
            board=sfu_board, owner_lane="scientific_reviewer"
        )
    )
    sfu_remediation = rt.export_scientific_follow_up_owner_remediation_packet(
        ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=sfu_handoff)
    )
    sfu_signoff = rt.export_scientific_follow_up_owner_signoff_packet(
        ExportScientificFollowUpOwnerSignoffPacketRequest(
            remediation_packet=sfu_remediation,
            reviewer_id="runtime.owner",
            reviewer_role="scientific_reviewer",
        )
    )
    sanitised_dossier = rt.export_sanitised_public_review_dossier(
        ExportSanitisedPublicReviewDossierRequest(dossier=contaminant_dossier)
    )

    written = {
        "dietary_intake_summary.json": _pin_timestamps(_dump(summary)),
        "contaminant_interpretation_bundle.json": _pin_timestamps(_dump(bundle)),
        "contaminant_signoff_packet.json": _pin_timestamps(_dump(packet)),
        "adapter_review_bundle.json": _pin_timestamps(_dump(adapter)),
        "metals_interpretation_bundle.json": _pin_timestamps(_dump(metals_bundle)),
        "metals_signoff_packet.json": _pin_timestamps(_dump(metals_signoff)),
        "trade_risk_review_bundle.json": _pin_timestamps(_dump(trade_bundle)),
        "interoperability_signoff_packet.json": _pin_timestamps(_dump(interop_signoff)),
        "scientific_follow_up_owner_signoff_packet.json": _pin_timestamps(
            _dump(sfu_signoff)
        ),
        "sanitised_public_review_dossier.json": _pin_timestamps(_dump(sanitised_dossier)),
    }
    for name, obj in written.items():
        (CORPUS_DIR / name).write_text(json.dumps(obj, indent=2) + "\n")
        print(f"[corpus] wrote {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
