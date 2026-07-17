from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    ExportScientificFollowUpOwnerHandoffPacketRequest,
    ExportScientificFollowUpOwnerRemediationPacketRequest,
    ExportScientificFollowUpReviewBoardRequest,
)
from dietary_mcp.runtime import get_cached_dietary_runtime
from dietary_mcp.scientific_follow_up_review_board_validation import _build_queue_bundle


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_scientific_follow_up_owner_remediation_cases(repo_root: Path) -> dict:
    cases_payload = json.loads(
        (_validation_root(repo_root) / "scientific_follow_up_owner_remediation_cases.json").read_text()
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
                packet_note=case.get("handoffNote"),
            )
        )
        packet = runtime.export_scientific_follow_up_owner_remediation_packet(
            ExportScientificFollowUpOwnerRemediationPacketRequest(
                handoff_packet=handoff_packet,
                packet_note=case.get("packetNote"),
            )
        )
        observed_action_ids = [item.action_id for item in packet.action_items]
        observed_remediation_class_by_action = {
            item.action_id: item.remediation_class.value for item in packet.action_items
        }
        observed_remediation_class_groups = {
            item.remediation_class.value: item.action_ids for item in packet.remediation_class_groups
        }
        status = (
            "ok"
            if packet.overall_status.value == case["expectedOverallStatus"]
            and packet.source_workflow == case["expectedSourceWorkflow"]
            and observed_action_ids == case.get("expectedActionIds", [])
            and observed_remediation_class_by_action == case.get("expectedRemediationClassByAction", {})
            and observed_remediation_class_groups == case.get("expectedRemediationClassGroups", {})
            and packet.recommended_remediation_sequence
            == case.get("expectedRecommendedRemediationSequence", packet.recommended_remediation_sequence)
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
                "expectedRemediationClassByAction": case.get("expectedRemediationClassByAction", {}),
                "observedRemediationClassByAction": observed_remediation_class_by_action,
                "expectedRemediationClassGroups": case.get("expectedRemediationClassGroups", {}),
                "observedRemediationClassGroups": observed_remediation_class_groups,
                "expectedRecommendedRemediationSequence": case.get(
                    "expectedRecommendedRemediationSequence",
                    [],
                ),
                "observedRecommendedRemediationSequence": packet.recommended_remediation_sequence,
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
