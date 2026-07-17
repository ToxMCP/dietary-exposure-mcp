from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    ExportScientificFollowUpOwnerHandoffPacketRequest,
    ExportScientificFollowUpReviewBoardRequest,
)
from dietary_mcp.runtime import get_cached_dietary_runtime
from dietary_mcp.scientific_follow_up_review_board_validation import _build_queue_bundle


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_scientific_follow_up_owner_handoff_cases(repo_root: Path) -> dict:
    cases_payload = json.loads((_validation_root(repo_root) / "scientific_follow_up_owner_handoff_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in cases_payload["cases"]:
        queue_bundle = _build_queue_bundle(runtime, case["scenario"], case["targetProfile"])
        board = runtime.export_scientific_follow_up_review_board(
            ExportScientificFollowUpReviewBoardRequest(
                queue_bundle=queue_bundle,
            )
        )
        packet = runtime.export_scientific_follow_up_owner_handoff_packet(
            ExportScientificFollowUpOwnerHandoffPacketRequest(
                board=board,
                owner_lane=case["ownerLane"],
                due_state_filter=case.get("dueStateFilter", []),
                packet_note=case.get("packetNote"),
            )
        )
        observed_due_state_groups = {
            item.due_state.value: item.action_ids for item in packet.due_state_groups
        }
        observed_action_ids = [item.action_id for item in packet.action_items]
        status = (
            "ok"
            if packet.overall_status.value == case["expectedOverallStatus"]
            and packet.source_workflow == case["expectedSourceWorkflow"]
            and observed_action_ids == case.get("expectedActionIds", [])
            and packet.blocking_action_ids == case.get("expectedBlockingActionIds", [])
            and observed_due_state_groups == case.get("expectedDueStateGroups", {})
            and packet.recommended_owner_sequence
            == case.get("expectedRecommendedOwnerSequence", packet.recommended_owner_sequence)
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedOverallStatus": case["expectedOverallStatus"],
                "observedOverallStatus": packet.overall_status.value,
                "expectedSourceWorkflow": case["expectedSourceWorkflow"],
                "observedSourceWorkflow": packet.source_workflow,
                "expectedActionIds": case.get("expectedActionIds", []),
                "observedActionIds": observed_action_ids,
                "expectedBlockingActionIds": case.get("expectedBlockingActionIds", []),
                "observedBlockingActionIds": packet.blocking_action_ids,
                "expectedDueStateGroups": case.get("expectedDueStateGroups", {}),
                "observedDueStateGroups": observed_due_state_groups,
                "expectedRecommendedOwnerSequence": case.get("expectedRecommendedOwnerSequence", []),
                "observedRecommendedOwnerSequence": packet.recommended_owner_sequence,
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
