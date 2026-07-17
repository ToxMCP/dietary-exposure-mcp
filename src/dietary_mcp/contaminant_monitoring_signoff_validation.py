from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    CheckContaminantMonitoringImportRequest,
    ExportContaminantMonitoringInterpretationBundleRequest,
    ExportContaminantMonitoringSignoffPacketRequest,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_contaminant_monitoring_signoff_cases(repo_root: Path) -> dict:
    cases_payload = json.loads((_validation_root(repo_root) / "contaminant_monitoring_signoff_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in cases_payload["cases"]:
        check_result = runtime.check_contaminant_monitoring_import(
            CheckContaminantMonitoringImportRequest.model_validate(case["request"])
        )
        interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
            ExportContaminantMonitoringInterpretationBundleRequest(
                check_result=check_result,
                bundle_note=case.get("bundleNote"),
            )
        )
        packet = runtime.export_contaminant_monitoring_signoff_packet(
            ExportContaminantMonitoringSignoffPacketRequest(
                interpretation_bundle=interpretation_bundle,
                reviewer_id=case["reviewerId"],
                reviewer_role=case["reviewerRole"],
                decisions=case.get("decisions", []),
                packet_note=case.get("packetNote"),
            )
        )
        observed_action_ids = sorted(item.action_id for item in packet.action_items)
        status = (
            "ok"
            if packet.overall_signoff_status.value == case["expectedOverallSignoffStatus"]
            and observed_action_ids == sorted(case["expectedActionIds"])
            and sorted(packet.pending_action_ids) == sorted(case.get("expectedPendingActionIds", []))
            and sorted(packet.acknowledged_action_ids) == sorted(case.get("expectedAcknowledgedActionIds", []))
            and sorted(packet.completed_action_ids) == sorted(case.get("expectedCompletedActionIds", []))
            and sorted(packet.waived_action_ids) == sorted(case.get("expectedWaivedActionIds", []))
            and sorted(packet.unresolved_blocking_action_ids)
            == sorted(case.get("expectedUnresolvedBlockingActionIds", []))
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "observedOverallSignoffStatus": packet.overall_signoff_status.value,
                "observedActionIds": observed_action_ids,
                "observedPendingActionIds": packet.pending_action_ids,
                "observedAcknowledgedActionIds": packet.acknowledged_action_ids,
                "observedCompletedActionIds": packet.completed_action_ids,
                "observedWaivedActionIds": packet.waived_action_ids,
                "observedUnresolvedBlockingActionIds": packet.unresolved_blocking_action_ids,
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
