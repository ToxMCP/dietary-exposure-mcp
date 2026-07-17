from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    ExportMetalsMonitoringInterpretationBundleRequest,
    ExportMetalsMonitoringSignoffPacketRequest,
    ExportVersionPinnedMetalsMonitoringReviewDossierRequest,
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


def run_metals_monitoring_review_dossier_cases(repo_root: Path) -> dict:
    cases_payload = json.loads((_validation_root(repo_root) / "metals_monitoring_review_dossier_cases.json").read_text())
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
                reviewer_id="validation.metals.dossier.reviewer",
                reviewer_role="validation_metals_dossier_reviewer",
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
        dossier = runtime.export_version_pinned_metals_monitoring_review_dossier(
            ExportVersionPinnedMetalsMonitoringReviewDossierRequest(
                interpretation_bundle=interpretation_bundle,
                signoff_packet=signoff_packet,
            )
        )
        observed_action_ids = [item.action_id for item in dossier.escalation_items]
        observed_types_by_action = {
            item.action_id: item.escalation_type.value for item in dossier.escalation_items
        }
        status = (
            "ok"
            if dossier.dossier_status.value == case["expectedDossierStatus"]
            and dossier.escalation_required == case["expectedEscalationRequired"]
            and observed_action_ids == case["expectedEscalationActionIds"]
            and observed_types_by_action == case.get("expectedEscalationTypesByAction", observed_types_by_action)
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedDossierStatus": case["expectedDossierStatus"],
                "observedDossierStatus": dossier.dossier_status.value,
                "expectedEscalationRequired": case["expectedEscalationRequired"],
                "observedEscalationRequired": dossier.escalation_required,
                "expectedEscalationActionIds": case["expectedEscalationActionIds"],
                "observedEscalationActionIds": observed_action_ids,
                "expectedEscalationTypesByAction": case.get("expectedEscalationTypesByAction", {}),
                "observedEscalationTypesByAction": observed_types_by_action,
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
