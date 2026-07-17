from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    AssessReviewDossierReadinessRequest,
    ExportScientificFollowUpQueueBundleRequest,
    ExportScientificFollowUpOwnerHandoffPacketRequest,
    ExportScientificFollowUpOwnerRemediationPacketRequest,
    ExportScientificFollowUpOwnerSignoffPacketRequest,
    ExportScientificFollowUpReviewBoardRequest,
    ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest,
)
from dietary_mcp.readiness_validation import _build_example_dossier
from dietary_mcp.runtime import DietaryRuntime, get_cached_dietary_runtime
from dietary_mcp.scientific_follow_up_review_board_validation import _build_mixed_mercury_contaminant_dossier


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def _build_source_dossier(runtime: DietaryRuntime, scenario: str):
    if scenario == "mercury_contaminant_mixed":
        return _build_mixed_mercury_contaminant_dossier(runtime)
    return _build_example_dossier(runtime, scenario)


def run_scientific_follow_up_owner_signoff_dossier_cases(repo_root: Path) -> dict:
    cases_payload = json.loads(
        (_validation_root(repo_root) / "scientific_follow_up_owner_signoff_dossier_cases.json").read_text()
    )
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in cases_payload["cases"]:
        source_dossier = _build_source_dossier(runtime, case["scenario"])
        assessment = runtime.assess_review_dossier_readiness(
            AssessReviewDossierReadinessRequest(
                dossier=source_dossier,
                target_profile=case["targetProfile"],
            )
        )
        queue_bundle = runtime.export_scientific_follow_up_queue_bundle(
            ExportScientificFollowUpQueueBundleRequest(
                dossier=source_dossier,
                assessment=assessment,
            )
        )
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
            ExportScientificFollowUpOwnerRemediationPacketRequest(handoff_packet=handoff_packet)
        )
        signoff_packet = runtime.export_scientific_follow_up_owner_signoff_packet(
            ExportScientificFollowUpOwnerSignoffPacketRequest(
                remediation_packet=remediation_packet,
                reviewer_id=case["reviewerId"],
                reviewer_role=case["reviewerRole"],
                decisions=case.get("decisions", []),
            )
        )
        dossier = runtime.export_version_pinned_scientific_follow_up_owner_signoff_dossier(
            ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest(
                source_dossier=source_dossier,
                signoff_packet=signoff_packet,
            )
        )
        observed_escalation_action_ids = [item.action_id for item in dossier.escalation_items]
        observed_escalation_types = {
            item.action_id: item.escalation_type.value for item in dossier.escalation_items
        }
        expected_escalation_action_ids = case.get("expectedEscalationActionIds", observed_escalation_action_ids)
        expected_escalation_types = case.get("expectedEscalationTypes", observed_escalation_types)
        status = (
            "ok"
            if dossier.dossier_status.value == case["expectedDossierStatus"]
            and dossier.source_workflow == case["expectedSourceWorkflow"]
            and dossier.escalation_required == case["expectedEscalationRequired"]
            and observed_escalation_action_ids == expected_escalation_action_ids
            and observed_escalation_types == expected_escalation_types
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedDossierStatus": case["expectedDossierStatus"],
                "observedDossierStatus": dossier.dossier_status.value,
                "expectedSourceWorkflow": case["expectedSourceWorkflow"],
                "observedSourceWorkflow": dossier.source_workflow,
                "expectedEscalationRequired": case["expectedEscalationRequired"],
                "observedEscalationRequired": dossier.escalation_required,
                "expectedEscalationActionIds": expected_escalation_action_ids,
                "observedEscalationActionIds": observed_escalation_action_ids,
                "expectedEscalationTypes": expected_escalation_types,
                "observedEscalationTypes": observed_escalation_types,
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
