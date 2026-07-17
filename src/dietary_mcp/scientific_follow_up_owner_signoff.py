from __future__ import annotations

from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.models import (
    ExportScientificFollowUpOwnerSignoffPacketRequest,
    InteroperabilityActionDecisionStatus,
    InteroperabilitySignoffStatus,
    ReviewResourceReference,
    ScientificFollowUpOwnerSignoffActionItem,
    ScientificFollowUpOwnerSignoffPacket,
    ScientificFollowUpRemediationClass,
)


def _signoff_docs(source_workflow: str) -> tuple[list[tuple[str, str, str]], str]:
    common_resources = [
        (
            "scientific_follow_up_owner_remediation_docs",
            "docs://scientific-follow-up-owner-remediation",
            "Operator guide for owner-lane remediation packets derived from scientific follow-up handoffs.",
        ),
        (
            "scientific_follow_up_owner_signoff_docs",
            "docs://scientific-follow-up-owner-signoff",
            "Operator guide for owner-lane signoff packets derived from scientific follow-up remediation packets.",
        ),
    ]
    if source_workflow == "contaminant_monitoring_review_dossier":
        return (
            common_resources
            + [
                (
                    "contaminant_monitoring_review_docs",
                    "docs://contaminant-monitoring-review-dossier",
                    "Workflow guide for contaminant monitoring readiness, signoff, and dossier export.",
                ),
            ],
            "docs://scientific-follow-up-owner-signoff",
        )
    if source_workflow == "metals_monitoring_review_dossier":
        return (
            common_resources
            + [
                (
                    "metals_monitoring_review_docs",
                    "docs://metals-monitoring-review-dossier",
                    "Workflow guide for metals monitoring readiness, signoff, and dossier export.",
                ),
            ],
            "docs://scientific-follow-up-owner-signoff",
        )
    return (
        common_resources
        + [
            (
                "regulatory_governance_docs",
                "docs://regulatory-governance",
                "Governance semantics for adapter model families and EU-first readiness posture.",
            ),
        ],
        "docs://scientific-follow-up-owner-signoff",
    )


def export_scientific_follow_up_owner_signoff_packet(
    request: ExportScientificFollowUpOwnerSignoffPacketRequest,
) -> ScientificFollowUpOwnerSignoffPacket:
    remediation_packet = request.remediation_packet
    known_action_ids = {item.action_id for item in remediation_packet.action_items}
    decisions_by_action = {}

    for decision in request.decisions:
        if decision.action_id in decisions_by_action:
            raise DietaryValidationError(
                code="duplicate_scientific_follow_up_owner_signoff_decision",
                message=f"Duplicate signoff decision supplied for owner remediation action {decision.action_id}.",
                suggestion="Provide at most one signoff decision per owner remediation action.",
            )
        if decision.action_id not in known_action_ids:
            raise DietaryValidationError(
                code="unknown_scientific_follow_up_owner_signoff_action",
                message=f"Unknown owner remediation action in signoff packet: {decision.action_id}.",
                suggestion="Use action ids listed in the owner remediation packet actionItems array.",
            )
        decisions_by_action[decision.action_id] = decision

    referenced_resources: dict[tuple[str, str], ReviewResourceReference] = {}

    def add_resource(role: str, uri: str, description: str) -> None:
        key = (role, uri)
        if key in referenced_resources:
            return
        referenced_resources[key] = ReviewResourceReference(role=role, uri=uri, description=description)

    for resource in remediation_packet.referenced_resources:
        add_resource(resource.role, resource.uri, resource.description)
    resource_specs, documentation_resource_uri = _signoff_docs(remediation_packet.source_workflow)
    for role, uri, description in resource_specs:
        add_resource(role, uri, description)

    action_items: list[ScientificFollowUpOwnerSignoffActionItem] = []
    pending_action_ids: list[str] = []
    acknowledged_action_ids: list[str] = []
    completed_action_ids: list[str] = []
    waived_action_ids: list[str] = []
    unresolved_blocking_action_ids: list[str] = []
    resolve_now_action_ids: list[str] = []
    review_this_cycle_action_ids: list[str] = []
    track_in_progress_action_ids: list[str] = []
    record_closure_action_ids: list[str] = []

    for action in remediation_packet.action_items:
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

        if action.remediation_class == ScientificFollowUpRemediationClass.RESOLVE_NOW:
            resolve_now_action_ids.append(action.action_id)
        elif action.remediation_class == ScientificFollowUpRemediationClass.REVIEW_THIS_CYCLE:
            review_this_cycle_action_ids.append(action.action_id)
        elif action.remediation_class == ScientificFollowUpRemediationClass.TRACK_IN_PROGRESS:
            track_in_progress_action_ids.append(action.action_id)
        else:
            record_closure_action_ids.append(action.action_id)

        for uri in supporting_uris:
            add_resource(
                "signoff_supporting_resource",
                uri,
                f"Supporting resource cited by owner signoff for action {action.action_id}.",
            )

        action_items.append(
            ScientificFollowUpOwnerSignoffActionItem(
                action_id=action.action_id,
                category=action.category,
                title=action.title,
                priority=action.priority,
                blocking=action.blocking,
                summary=action.summary,
                linked_record_ids=action.linked_record_ids,
                due_state=action.due_state,
                remediation_class=action.remediation_class,
                recommended_steps=action.recommended_steps,
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
        "Owner signoff packet is a reviewer-facing overlay on top of the owner remediation packet and does not mutate readiness, queue, board, handoff, or dossier state.",
        "Waived actions remain explicitly visible so downstream reviewers can inspect accepted deviations from the default owner remediation sequence.",
        "Signed-off status does not imply submission readiness, regulatory approval, or closure of the underlying scientific issue outside the tracked owner lane.",
    ]
    if remediation_packet.legal_limit_reviews:
        notes.append(
            "Legal-limit support reviews remain attached to the owner signoff packet so signoff cannot be mistaken for exact jurisdiction coverage when support is partial, anchor-only, or absent."
        )
    if unresolved_blocking_action_ids:
        notes.append("At least one blocking owner remediation action remains unresolved in the signoff packet.")
    if request.packet_note:
        notes.append(request.packet_note)

    return ScientificFollowUpOwnerSignoffPacket(
        overall_signoff_status=overall_signoff_status,
        reviewer_id=request.reviewer_id,
        reviewer_role=request.reviewer_role,
        overall_status=remediation_packet.overall_status,
        target_profile=remediation_packet.target_profile,
        source_remediation_packet_id=remediation_packet.packet_id,
        source_handoff_packet_id=remediation_packet.source_handoff_packet_id,
        source_board_id=remediation_packet.source_board_id,
        source_bundle_id=remediation_packet.source_bundle_id,
        source_dossier_id=remediation_packet.source_dossier_id,
        source_dossier_status=remediation_packet.source_dossier_status,
        source_workflow=remediation_packet.source_workflow,
        bundle_profile=remediation_packet.bundle_profile,
        owner_lane=remediation_packet.owner_lane,
        legal_limit_reviews=remediation_packet.legal_limit_reviews,
        due_state_filter=remediation_packet.due_state_filter,
        action_items=action_items,
        action_count=len(action_items),
        pending_action_ids=pending_action_ids,
        acknowledged_action_ids=acknowledged_action_ids,
        completed_action_ids=completed_action_ids,
        waived_action_ids=waived_action_ids,
        unresolved_blocking_action_ids=unresolved_blocking_action_ids,
        resolve_now_action_ids=resolve_now_action_ids,
        review_this_cycle_action_ids=review_this_cycle_action_ids,
        track_in_progress_action_ids=track_in_progress_action_ids,
        record_closure_action_ids=record_closure_action_ids,
        recommended_signoff_sequence=remediation_packet.recommended_remediation_sequence,
        documentation_resource_uri=documentation_resource_uri,
        referenced_resources=list(referenced_resources.values()),
        notes=notes,
    )
