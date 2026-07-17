from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    CheckContaminantMonitoringImportRequest,
    ContaminantFamily,
    ContaminantMonitoringSignoffDecisionInput,
    DietaryCommodityResidueInput,
    AssessReviewDossierReadinessRequest,
    ExportContaminantMonitoringInterpretationBundleRequest,
    ExportContaminantMonitoringSignoffPacketRequest,
    ExportScientificFollowUpOwnerHandoffPacketRequest,
    ExportScientificFollowUpOwnerRemediationPacketRequest,
    ExportScientificFollowUpOwnerSignoffPacketRequest,
    ExportScientificFollowUpQueueBundleRequest,
    ExportScientificFollowUpReviewBoardRequest,
    ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest,
    ExportVersionPinnedContaminantMonitoringReviewDossierRequest,
    EvaluateGlobalTradeRiskRequest,
    InteroperabilityActionDecisionStatus,
    ExportSanitisedPublicReviewDossierRequest,
    ExportTradeRiskReviewBundleRequest,
    ExportVersionPinnedTradeRiskReviewDossierRequest,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_sanitised_public_review_cases(repo_root: Path) -> dict:
    from dietary_mcp.readiness_validation import _build_example_dossier

    cases_payload = json.loads((_validation_root(repo_root) / "sanitised_public_review_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    def build_example_dossier(case: dict):
        if case["scenario"] == "trade_risk_glyphosate":
            trade_report = runtime.evaluate_global_trade_risk(
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
            review_bundle = runtime.export_trade_risk_review_bundle(
                ExportTradeRiskReviewBundleRequest(trade_report=trade_report)
            )
            return runtime.export_version_pinned_trade_risk_review_dossier(
                ExportVersionPinnedTradeRiskReviewDossierRequest(review_bundle=review_bundle)
            )
        if case["scenario"] == "scientific_follow_up_owner_signoff_mercury_waiver":
            check_result = runtime.check_contaminant_monitoring_import(
                CheckContaminantMonitoringImportRequest(
                    contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
                    jurisdiction="eu",
                    dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
                    csv_text=(
                        "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                        "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                        "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
                    ),
                )
            )
            interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
                ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
            )
            source_dossier = runtime.export_version_pinned_contaminant_monitoring_review_dossier(
                ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
                    interpretation_bundle=interpretation_bundle,
                    signoff_packet=runtime.export_contaminant_monitoring_signoff_packet(
                        ExportContaminantMonitoringSignoffPacketRequest(
                            interpretation_bundle=interpretation_bundle,
                            reviewer_id="validation.owner.source",
                            reviewer_role="scientific_reviewer",
                            decisions=[
                                ContaminantMonitoringSignoffDecisionInput(
                                    action_id="review_scientific_ledger.row_level_lod_coverage",
                                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                                    rationale="LOD coverage reviewed.",
                                ),
                                ContaminantMonitoringSignoffDecisionInput(
                                    action_id="review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                                    decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                                    rationale="Lower-bound handling retained as waiver.",
                                    supporting_uris=["docs://contaminant-monitoring-signoff"],
                                ),
                                ContaminantMonitoringSignoffDecisionInput(
                                    action_id="review_scientific_ledger.storage_stability.eu.mercury.analytical_method_evidence.official_control",
                                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                                    rationale="Storage stability reviewed.",
                                ),
                                ContaminantMonitoringSignoffDecisionInput(
                                    action_id="review_scientific_ledger.sampling_plan.eu.mercury.analytical_method_evidence.official_control",
                                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                                    rationale="Sampling plan reviewed.",
                                ),
                            ],
                        )
                    ),
                )
            )
            readiness = runtime.assess_review_dossier_readiness(
                AssessReviewDossierReadinessRequest(
                    dossier=source_dossier,
                    target_profile="mercury_internal_review",
                )
            )
            queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
                ExportScientificFollowUpQueueBundleRequest(dossier=source_dossier, assessment=readiness)
            )
            board = runtime.export_scientific_follow_up_review_board(
                ExportScientificFollowUpReviewBoardRequest(queue_bundle=queue_bundle)
            )
            handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
                ExportScientificFollowUpOwnerHandoffPacketRequest(
                    board=board,
                    owner_lane="review_lead",
                    due_state_filter=["immediate"],
                )
            )
            remediation_packet = runtime.export_scientific_follow_up_owner_remediation_packet(
                ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=handoff_packet)
            )
            signoff_packet = runtime.export_scientific_follow_up_owner_signoff_packet(
                ExportScientificFollowUpOwnerSignoffPacketRequest(
                    remediation_packet=remediation_packet,
                    reviewer_id="validation.owner.signoff.public",
                    reviewer_role="review_lead",
                    decisions=[
                        {
                            "actionId": "review_scientific_ledger.lower_bound_handling.eu.mercury.occurrence_evidence.official_monitoring_context",
                            "decisionStatus": InteroperabilityActionDecisionStatus.WAIVED,
                            "rationale": "Lower-bound handling retained with explicit public waiver trace.",
                            "reviewedAt": "2026-04-12",
                        }
                    ],
                )
            )
            return runtime.export_version_pinned_scientific_follow_up_owner_signoff_dossier(
                ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest(
                    source_dossier=source_dossier,
                    signoff_packet=signoff_packet,
                )
            )
        return _build_example_dossier(runtime, case["scenario"])

    for case in cases_payload["cases"]:
        dossier = build_example_dossier(case)
        sanitised = runtime.export_sanitised_public_review_dossier(
            ExportSanitisedPublicReviewDossierRequest(dossier=dossier)
        )
        removed_roles = sorted(
            {
                item.target_path.split(".")[-1]
                for item in sanitised.sanitisation_records
                if item.target_kind == "resource" and item.sanitisation_state.value == "removed"
            }
        )
        redacted_fields = sorted(
            item.target_path
            for item in sanitised.sanitisation_records
            if item.target_kind == "field" and item.sanitisation_state.value == "redacted"
        )
        retained_confidential_resources = [
            item.role
            for item in sanitised.pinned_resources
            if item.confidentiality_tag.value == "confidential"
        ] + [
            item.role
            for item in sanitised.public_review_bundle.referenced_resources
            if item.confidentiality_tag.value == "confidential"
        ]
        status = (
            "ok"
            if sanitised.bundle_profile.value == case["expectedBundleProfile"]
            and sanitised.source_workflow == case.get("expectedSourceWorkflow", sanitised.source_workflow)
            and removed_roles == sorted(case["expectedRemovedResourceRoles"])
            and redacted_fields == sorted(case["expectedRedactedFieldPaths"])
            and len(sanitised.legal_limit_reviews)
            == case.get("expectedLegalLimitReviewCount", len(sanitised.legal_limit_reviews))
            and sanitised.escalation_required
            == case.get("expectedEscalationRequired", sanitised.escalation_required)
            and not retained_confidential_resources
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedBundleProfile": case["expectedBundleProfile"],
                "observedBundleProfile": sanitised.bundle_profile.value,
                "expectedSourceWorkflow": case.get("expectedSourceWorkflow"),
                "observedSourceWorkflow": sanitised.source_workflow,
                "expectedRemovedResourceRoles": sorted(case["expectedRemovedResourceRoles"]),
                "observedRemovedResourceRoles": removed_roles,
                "expectedRedactedFieldPaths": sorted(case["expectedRedactedFieldPaths"]),
                "observedRedactedFieldPaths": redacted_fields,
                "expectedLegalLimitReviewCount": case.get("expectedLegalLimitReviewCount"),
                "observedLegalLimitReviewCount": len(sanitised.legal_limit_reviews),
                "expectedEscalationRequired": case.get("expectedEscalationRequired"),
                "observedEscalationRequired": sanitised.escalation_required,
                "retainedConfidentialResources": retained_confidential_resources,
            }
        )
    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
