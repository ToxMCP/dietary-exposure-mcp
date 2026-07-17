from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    ExportScientificFollowUpOwnerHandoffPacketRequest,
    ExportScientificFollowUpOwnerRemediationPacketRequest,
    ExportScientificFollowUpOwnerSignoffPacketRequest,
    ExportScientificFollowUpReviewBoardRequest,
)
from dietary_mcp.runtime import get_cached_dietary_runtime
from dietary_mcp.scientific_follow_up_review_board_validation import _build_queue_bundle


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_scientific_follow_up_owner_signoff_cases(repo_root: Path) -> dict:
    cases_payload = json.loads(
        (_validation_root(repo_root) / "scientific_follow_up_owner_signoff_cases.json").read_text()
    )
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in cases_payload["cases"]:
        queue_bundle = _build_queue_bundle(runtime, case["scenario"], case["targetProfile"])
        board = runtime.export_scientific_follow_up_review_board(
            ExportScientificFollowUpReviewBoardRequest(queue_bundle=queue_bundle)
        )
        handoff_packet = runtime.export_scientific_follow_up_owner_handoff_packet(
            ExportScientificFollowUpOwnerHandoffPacketRequest(
                board=board,
                owner_lane=case["ownerLane"],
                due_state_filter=case.get("dueStateFilter", []),
            )
        )
        remediation_packet = runtime.export_scientific_follow_up_owner_remediation_packet(
            ExportScientificFollowUpOwnerRemediationPacketRequest(
                handoff_packet=handoff_packet,
            )
        )
        signoff_packet = runtime.export_scientific_follow_up_owner_signoff_packet(
            ExportScientificFollowUpOwnerSignoffPacketRequest(
                remediation_packet=remediation_packet,
                reviewer_id=case["reviewerId"],
                reviewer_role=case["reviewerRole"],
                decisions=case.get("decisions", []),
                packet_note=case.get("packetNote"),
            )
        )
        status = (
            "ok"
            if signoff_packet.overall_signoff_status.value == case["expectedOverallSignoffStatus"]
            and signoff_packet.source_workflow == case["expectedSourceWorkflow"]
            and signoff_packet.pending_action_ids == case.get("expectedPendingActionIds", [])
            and signoff_packet.acknowledged_action_ids == case.get("expectedAcknowledgedActionIds", [])
            and signoff_packet.completed_action_ids == case.get("expectedCompletedActionIds", [])
            and signoff_packet.waived_action_ids == case.get("expectedWaivedActionIds", [])
            and signoff_packet.recommended_signoff_sequence
            == case.get("expectedRecommendedSignoffSequence", signoff_packet.recommended_signoff_sequence)
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedOverallSignoffStatus": case["expectedOverallSignoffStatus"],
                "observedOverallSignoffStatus": signoff_packet.overall_signoff_status.value,
                "expectedSourceWorkflow": case["expectedSourceWorkflow"],
                "observedSourceWorkflow": signoff_packet.source_workflow,
                "expectedPendingActionIds": case.get("expectedPendingActionIds", []),
                "observedPendingActionIds": signoff_packet.pending_action_ids,
                "expectedAcknowledgedActionIds": case.get("expectedAcknowledgedActionIds", []),
                "observedAcknowledgedActionIds": signoff_packet.acknowledged_action_ids,
                "expectedCompletedActionIds": case.get("expectedCompletedActionIds", []),
                "observedCompletedActionIds": signoff_packet.completed_action_ids,
                "expectedWaivedActionIds": case.get("expectedWaivedActionIds", []),
                "observedWaivedActionIds": signoff_packet.waived_action_ids,
                "expectedRecommendedSignoffSequence": case.get("expectedRecommendedSignoffSequence", []),
                "observedRecommendedSignoffSequence": signoff_packet.recommended_signoff_sequence,
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
