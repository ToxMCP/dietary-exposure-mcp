from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    AssessReviewDossierReadinessRequest,
    CheckContaminantMonitoringImportRequest,
    ContaminantFamily,
    ContaminantMonitoringSignoffDecisionInput,
    ExportContaminantMonitoringInterpretationBundleRequest,
    ExportContaminantMonitoringSignoffPacketRequest,
    ExportScientificFollowUpQueueBundleRequest,
    ExportScientificFollowUpReviewBoardRequest,
    ExportVersionPinnedContaminantMonitoringReviewDossierRequest,
    InteroperabilityActionDecisionStatus,
)
from dietary_mcp.readiness_validation import _build_example_dossier
from dietary_mcp.runtime import DietaryRuntime, get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def _build_mixed_mercury_contaminant_dossier(runtime: DietaryRuntime):
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
    signoff_packet = runtime.export_contaminant_monitoring_signoff_packet(
        ExportContaminantMonitoringSignoffPacketRequest(
            interpretation_bundle=interpretation_bundle,
            reviewer_id="validation.followup.board",
            reviewer_role="scientific_reviewer",
            decisions=[
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_scientific_ledger.row_level_lod_coverage",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="LOD coverage reviewed.",
                    supporting_uris=["docs://contaminant-monitoring-import"],
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id=(
                        "review_scientific_ledger.lower_bound_handling."
                        "eu.mercury.occurrence_evidence.official_monitoring_context"
                    ),
                    decision_status=InteroperabilityActionDecisionStatus.WAIVED,
                    rationale="Lower-bound handling retained as waiver.",
                    supporting_uris=["docs://contaminant-monitoring-signoff"],
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id=(
                        "review_scientific_ledger.storage_stability."
                        "eu.mercury.analytical_method_evidence.official_control"
                    ),
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Storage stability reviewed.",
                    supporting_uris=["docs://analytical-method-evidence-registry"],
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id=(
                        "review_scientific_ledger.sampling_plan."
                        "eu.mercury.analytical_method_evidence.official_control"
                    ),
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Sampling plan reviewed.",
                    supporting_uris=["docs://analytical-method-evidence-registry"],
                ),
            ],
        )
    )
    return runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=signoff_packet,
        )
    )


def _build_queue_bundle(runtime: DietaryRuntime, scenario: str, target_profile: str):
    if scenario == "mercury_contaminant_mixed":
        dossier = _build_mixed_mercury_contaminant_dossier(runtime)
    else:
        dossier = _build_example_dossier(runtime, scenario)
    assessment = runtime.assess_review_dossier_readiness(
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile=target_profile,
        )
    )
    queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
        ExportScientificFollowUpQueueBundleRequest(
            dossier=dossier,
            assessment=assessment,
        )
    )
    return queue_bundle


def run_scientific_follow_up_review_board_cases(repo_root: Path) -> dict:
    cases_payload = json.loads((_validation_root(repo_root) / "scientific_follow_up_review_board_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in cases_payload["cases"]:
        queue_bundle = _build_queue_bundle(runtime, case["scenario"], case["targetProfile"])
        board = runtime.export_scientific_follow_up_review_board(
            ExportScientificFollowUpReviewBoardRequest(
                queue_bundle=queue_bundle,
                board_note=case.get("boardNote"),
            )
        )
        observed_owner_lane_by_action = {
            item.action_id: item.owner_lane.value for item in board.action_items
        }
        observed_due_state_by_action = {
            item.action_id: item.due_state.value for item in board.action_items
        }
        observed_owner_lane_groups = {
            item.owner_lane.value: item.action_ids for item in board.owner_lanes
        }
        observed_due_state_groups = {
            item.due_state.value: item.action_ids for item in board.due_state_groups
        }
        status = (
            "ok"
            if board.overall_status.value == case["expectedOverallStatus"]
            and board.source_workflow == case["expectedSourceWorkflow"]
            and observed_owner_lane_by_action == case.get("expectedOwnerLaneByAction", {})
            and observed_due_state_by_action == case.get("expectedDueStateByAction", {})
            and observed_owner_lane_groups == case.get("expectedOwnerLaneGroups", {})
            and observed_due_state_groups == case.get("expectedDueStateGroups", {})
            and board.recommended_triage_sequence
            == case.get("expectedRecommendedTriageSequence", board.recommended_triage_sequence)
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedOverallStatus": case["expectedOverallStatus"],
                "observedOverallStatus": board.overall_status.value,
                "expectedSourceWorkflow": case["expectedSourceWorkflow"],
                "observedSourceWorkflow": board.source_workflow,
                "expectedOwnerLaneByAction": case.get("expectedOwnerLaneByAction", {}),
                "observedOwnerLaneByAction": observed_owner_lane_by_action,
                "expectedDueStateByAction": case.get("expectedDueStateByAction", {}),
                "observedDueStateByAction": observed_due_state_by_action,
                "expectedOwnerLaneGroups": case.get("expectedOwnerLaneGroups", {}),
                "observedOwnerLaneGroups": observed_owner_lane_groups,
                "expectedDueStateGroups": case.get("expectedDueStateGroups", {}),
                "observedDueStateGroups": observed_due_state_groups,
                "expectedRecommendedTriageSequence": case.get("expectedRecommendedTriageSequence", []),
                "observedRecommendedTriageSequence": board.recommended_triage_sequence,
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
