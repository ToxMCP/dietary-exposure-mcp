from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    AssessInteroperabilityPreviewReadinessRequest,
    ExportInteroperabilityPreviewRequest,
    ExportInteroperabilityRemediationBundleRequest,
    ExportInteroperabilitySignoffPacketRequest,
    InteroperabilityActionDecisionStatus,
    InteroperabilitySignoffDecisionInput,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_interoperability_signoff_cases(repo_root: Path) -> dict:
    from dietary_mcp.readiness_validation import _build_example_dossier

    cases_payload = json.loads((_validation_root(repo_root) / "interoperability_signoff_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []
    for case in cases_payload["cases"]:
        dossier = _build_example_dossier(runtime, case["scenario"])
        preview = runtime.export_interoperability_preview(
            ExportInteroperabilityPreviewRequest(
                dossier=dossier,
                target_profile="oht_85_iuclid_json_preview",
            )
        )
        assessment = runtime.assess_interoperability_preview_readiness(
            AssessInteroperabilityPreviewReadinessRequest(
                dossier=dossier,
                preview=preview,
                target_profile=case["targetProfile"],
            )
        )
        remediation_bundle = runtime.export_interoperability_remediation_bundle(
            ExportInteroperabilityRemediationBundleRequest(
                dossier=dossier,
                preview=preview,
                assessment=assessment,
            )
        )
        signoff_packet = runtime.export_interoperability_signoff_packet(
            ExportInteroperabilitySignoffPacketRequest(
                remediation_bundle=remediation_bundle,
                reviewer_id="validation.reviewer",
                reviewer_role="validation_reviewer",
                decisions=[
                    InteroperabilitySignoffDecisionInput(
                        action_id=item["actionId"],
                        decision_status=InteroperabilityActionDecisionStatus(item["decisionStatus"]),
                        rationale=item.get("rationale"),
                        reviewed_at=item.get("reviewedAt"),
                        supporting_uris=item.get("supportingUris", []),
                    )
                    for item in case.get("decisions", [])
                ],
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
