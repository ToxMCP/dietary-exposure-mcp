from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    ExportMetalsMonitoringInterpretationBundleRequest,
    ExportMetalsMonitoringSignoffPacketRequest,
    InteroperabilityActionDecisionStatus,
    LookupMetalsOccurrenceRequest,
    LookupMetalsReviewFocusRequest,
    MetalsMonitoringSignoffDecisionInput,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_metals_monitoring_signoff_cases(repo_root: Path) -> dict:
    cases_payload = json.loads((_validation_root(repo_root) / "metals_monitoring_signoff_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in cases_payload["cases"]:
        occurrence_result = runtime.lookup_metals_occurrence(
            LookupMetalsOccurrenceRequest.model_validate(case["occurrenceRequest"])
        )
        review_focus_result = runtime.lookup_metals_review_focus(
            LookupMetalsReviewFocusRequest.model_validate(case["reviewFocusRequest"])
        )
        interpretation_bundle = runtime.export_metals_monitoring_interpretation_bundle(
            ExportMetalsMonitoringInterpretationBundleRequest(
                occurrence_result=occurrence_result,
                review_focus_result=review_focus_result,
            )
        )
        signoff_packet = runtime.export_metals_monitoring_signoff_packet(
            ExportMetalsMonitoringSignoffPacketRequest(
                interpretation_bundle=interpretation_bundle,
                reviewer_id="validation.metals.reviewer",
                reviewer_role="validation_metals_reviewer",
                decisions=[
                    MetalsMonitoringSignoffDecisionInput(
                        action_id=item["actionId"],
                        decision_status=InteroperabilityActionDecisionStatus(item["decisionStatus"]),
                        rationale=item.get("rationale"),
                        reviewed_at=item.get("reviewedAt"),
                        supporting_uris=item.get("supportingUris", []),
                    )
                    for item in case.get("decisions", [])
                ],
                packet_note=case.get("packetNote"),
            )
        )
        status = (
            "ok"
            if signoff_packet.overall_signoff_status.value == case["expectedOverallSignoffStatus"]
            and signoff_packet.pending_action_ids == case["expectedPendingActionIds"]
            and signoff_packet.acknowledged_action_ids == case["expectedAcknowledgedActionIds"]
            and signoff_packet.completed_action_ids == case["expectedCompletedActionIds"]
            and signoff_packet.waived_action_ids == case["expectedWaivedActionIds"]
            and signoff_packet.unresolved_blocking_action_ids == case["expectedUnresolvedBlockingActionIds"]
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedOverallSignoffStatus": case["expectedOverallSignoffStatus"],
                "observedOverallSignoffStatus": signoff_packet.overall_signoff_status.value,
                "expectedPendingActionIds": case["expectedPendingActionIds"],
                "observedPendingActionIds": signoff_packet.pending_action_ids,
                "expectedAcknowledgedActionIds": case["expectedAcknowledgedActionIds"],
                "observedAcknowledgedActionIds": signoff_packet.acknowledged_action_ids,
                "expectedCompletedActionIds": case["expectedCompletedActionIds"],
                "observedCompletedActionIds": signoff_packet.completed_action_ids,
                "expectedWaivedActionIds": case["expectedWaivedActionIds"],
                "observedWaivedActionIds": signoff_packet.waived_action_ids,
                "expectedUnresolvedBlockingActionIds": case["expectedUnresolvedBlockingActionIds"],
                "observedUnresolvedBlockingActionIds": signoff_packet.unresolved_blocking_action_ids,
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
