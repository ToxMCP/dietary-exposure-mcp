from __future__ import annotations

from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.models import (
    ExportInteroperabilitySignoffPacketRequest,
    InteroperabilityActionDecisionStatus,
    InteroperabilitySignoffActionItem,
    InteroperabilitySignoffPacket,
    InteroperabilitySignoffStatus,
    ReviewResourceReference,
)


def export_interoperability_signoff_packet(
    request: ExportInteroperabilitySignoffPacketRequest,
) -> InteroperabilitySignoffPacket:
    remediation_bundle = request.remediation_bundle
    known_action_ids = {item.action_id for item in remediation_bundle.action_items}
    decisions_by_action = {}

    for decision in request.decisions:
        if decision.action_id in decisions_by_action:
            raise DietaryValidationError(
                code="duplicate_interoperability_signoff_decision",
                message=f"Duplicate signoff decision supplied for remediation action {decision.action_id}.",
                suggestion="Provide at most one signoff decision per remediation action.",
            )
        if decision.action_id not in known_action_ids:
            raise DietaryValidationError(
                code="unknown_interoperability_signoff_action",
                message=f"Unknown remediation action in signoff packet: {decision.action_id}.",
                suggestion="Use action ids listed in the remediation bundle actionItems array.",
            )
        decisions_by_action[decision.action_id] = decision

    referenced_resources: dict[tuple[str, str], ReviewResourceReference] = {}

    def add_resource(role: str, uri: str, description: str) -> None:
        key = (role, uri)
        if key in referenced_resources:
            return
        referenced_resources[key] = ReviewResourceReference(
            role=role,
            uri=uri,
            description=description,
        )

    for resource in remediation_bundle.referenced_resources:
        add_resource(resource.role, resource.uri, resource.description)
    add_resource(
        "interoperability_signoff_docs",
        "docs://interoperability-signoff",
        "Operator guide for reviewer-facing interoperability signoff packets.",
    )

    action_items: list[InteroperabilitySignoffActionItem] = []
    pending_action_ids: list[str] = []
    acknowledged_action_ids: list[str] = []
    completed_action_ids: list[str] = []
    waived_action_ids: list[str] = []
    unresolved_blocking_action_ids: list[str] = []

    for action in remediation_bundle.action_items:
        decision = decisions_by_action.get(action.action_id)
        if decision is None:
            decision_status = InteroperabilityActionDecisionStatus.PENDING
            rationale = None
            reviewed_at = None
            supporting_uris: list[str] = []
        else:
            decision_status = decision.decision_status
            rationale = decision.rationale
            reviewed_at = decision.reviewed_at
            supporting_uris = decision.supporting_uris

        resolved = decision_status in (
            InteroperabilityActionDecisionStatus.COMPLETED,
            InteroperabilityActionDecisionStatus.WAIVED,
        )
        if decision_status == InteroperabilityActionDecisionStatus.PENDING:
            pending_action_ids.append(action.action_id)
        elif decision_status == InteroperabilityActionDecisionStatus.ACKNOWLEDGED:
            acknowledged_action_ids.append(action.action_id)
        elif decision_status == InteroperabilityActionDecisionStatus.COMPLETED:
            completed_action_ids.append(action.action_id)
        else:
            waived_action_ids.append(action.action_id)

        if action.blocking and not resolved:
            unresolved_blocking_action_ids.append(action.action_id)

        for uri in supporting_uris:
            add_resource(
                "signoff_supporting_resource",
                uri,
                f"Supporting resource cited by reviewer signoff for action {action.action_id}.",
            )

        action_items.append(
            InteroperabilitySignoffActionItem(
                action_id=action.action_id,
                rule_id=action.rule_id,
                title=action.title,
                action_type=action.action_type,
                priority=action.priority,
                blocking=action.blocking,
                summary=action.summary,
                trigger_message=action.trigger_message,
                trigger_note=action.trigger_note,
                decision_status=decision_status,
                rationale=rationale,
                reviewed_at=reviewed_at,
                supporting_uris=supporting_uris,
                resolved=resolved,
            )
        )

    if pending_action_ids or acknowledged_action_ids or unresolved_blocking_action_ids:
        overall_signoff_status = InteroperabilitySignoffStatus.OPEN
    elif waived_action_ids:
        overall_signoff_status = InteroperabilitySignoffStatus.SIGNED_OFF_WITH_WAIVERS
    else:
        overall_signoff_status = InteroperabilitySignoffStatus.SIGNED_OFF

    notes = [
        "Signoff packet is a reviewer-facing overlay on top of the remediation bundle and does not alter the underlying readiness outcome.",
        "Waived actions remain explicitly visible so downstream reviewers can inspect the rationale for any accepted deviation.",
        "Signed-off status does not imply XML generation readiness, submission acceptance, or regulatory approval.",
    ]
    if unresolved_blocking_action_ids:
        notes.append("At least one blocking remediation action remains unresolved in the signoff packet.")
    if request.packet_note:
        notes.append(request.packet_note)

    return InteroperabilitySignoffPacket(
        overall_signoff_status=overall_signoff_status,
        reviewer_id=request.reviewer_id,
        reviewer_role=request.reviewer_role,
        source_remediation_bundle_id=remediation_bundle.bundle_id,
        source_dossier_id=remediation_bundle.source_dossier_id,
        source_preview_profile_id=remediation_bundle.source_preview_profile_id,
        target_profile=remediation_bundle.target_profile,
        linked_dossier_readiness_profile=remediation_bundle.linked_dossier_readiness_profile,
        linked_dossier_readiness_status=remediation_bundle.linked_dossier_readiness_status,
        action_items=action_items,
        pending_action_ids=pending_action_ids,
        acknowledged_action_ids=acknowledged_action_ids,
        completed_action_ids=completed_action_ids,
        waived_action_ids=waived_action_ids,
        unresolved_blocking_action_ids=unresolved_blocking_action_ids,
        referenced_resources=list(referenced_resources.values()),
        notes=notes,
    )
