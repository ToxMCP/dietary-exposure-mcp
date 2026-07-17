from __future__ import annotations

from dietary_mcp.models import (
    ExportScientificFollowUpOwnerRemediationPacketRequest,
    ReviewResourceReference,
    ScientificFollowUpDueState,
    ScientificFollowUpOwnerRemediationActionItem,
    ScientificFollowUpOwnerRemediationPacket,
    ScientificFollowUpRemediationClass,
    ScientificFollowUpRemediationClassGroup,
)


REMEDIATION_ORDER = [
    ScientificFollowUpRemediationClass.RESOLVE_NOW,
    ScientificFollowUpRemediationClass.REVIEW_THIS_CYCLE,
    ScientificFollowUpRemediationClass.TRACK_IN_PROGRESS,
    ScientificFollowUpRemediationClass.RECORD_CLOSURE,
]

DUE_STATE_ORDER = [
    ScientificFollowUpDueState.IMMEDIATE,
    ScientificFollowUpDueState.CURRENT_CYCLE,
    ScientificFollowUpDueState.IN_PROGRESS,
    ScientificFollowUpDueState.CLOSED_WITH_WAIVER,
    ScientificFollowUpDueState.CLOSED,
]


def _remediation_docs(source_workflow: str) -> tuple[list[tuple[str, str, str]], str]:
    common_resources = [
        (
            "scientific_follow_up_owner_handoff_docs",
            "docs://scientific-follow-up-owner-handoff",
            "Operator guide for owner-lane handoff packets derived from the scientific follow-up review board.",
        ),
        (
            "scientific_follow_up_owner_remediation_docs",
            "docs://scientific-follow-up-owner-remediation",
            "Operator guide for owner-lane remediation packets derived from scientific follow-up handoffs.",
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
            "docs://scientific-follow-up-owner-remediation",
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
            "docs://scientific-follow-up-owner-remediation",
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
        "docs://scientific-follow-up-owner-remediation",
    )


def _remediation_class(item) -> ScientificFollowUpRemediationClass:
    if item.due_state == ScientificFollowUpDueState.IMMEDIATE:
        return ScientificFollowUpRemediationClass.RESOLVE_NOW
    if item.due_state == ScientificFollowUpDueState.CURRENT_CYCLE:
        return ScientificFollowUpRemediationClass.REVIEW_THIS_CYCLE
    if item.due_state == ScientificFollowUpDueState.IN_PROGRESS:
        return ScientificFollowUpRemediationClass.TRACK_IN_PROGRESS
    return ScientificFollowUpRemediationClass.RECORD_CLOSURE


def _recommended_steps(item, remediation_class: ScientificFollowUpRemediationClass) -> list[str]:
    if remediation_class == ScientificFollowUpRemediationClass.RESOLVE_NOW:
        return [
            "Review linked records, supporting URIs, and current reviewer rationale immediately.",
            "Resolve or explicitly document the escalated scientific issue before the next review handoff.",
            "Regenerate readiness-side artifacts after reviewer action is recorded.",
        ]
    if remediation_class == ScientificFollowUpRemediationClass.REVIEW_THIS_CYCLE:
        return [
            "Review linked records and supporting URIs during the current review cycle.",
            "Document reviewer rationale or completion status on the underlying scientific action.",
            "Refresh readiness-side artifacts after reviewer action is recorded.",
        ]
    if remediation_class == ScientificFollowUpRemediationClass.TRACK_IN_PROGRESS:
        return [
            "Continue the acknowledged review task and preserve interim rationale.",
            "Track supporting evidence until the action is completed or explicitly waived.",
            "Refresh readiness-side artifacts after the in-progress action changes state.",
        ]
    return [
        "Verify that the closed or waived action remains documented with supporting rationale.",
        "Retain closure context in downstream review records for auditability.",
        "Refresh readiness-side artifacts only if closure state is reopened or revised.",
    ]


def export_scientific_follow_up_owner_remediation_packet(
    request: ExportScientificFollowUpOwnerRemediationPacketRequest,
) -> ScientificFollowUpOwnerRemediationPacket:
    handoff_packet = request.handoff_packet

    remediation_items: list[ScientificFollowUpOwnerRemediationActionItem] = []
    remediation_class_map: dict[ScientificFollowUpRemediationClass, list[ScientificFollowUpOwnerRemediationActionItem]] = {
        remediation_class: [] for remediation_class in REMEDIATION_ORDER
    }

    for item in handoff_packet.action_items:
        remediation_class = _remediation_class(item)
        remediation_item = ScientificFollowUpOwnerRemediationActionItem(
            action_id=item.action_id,
            category=item.category,
            title=item.title,
            priority=item.priority,
            blocking=item.blocking,
            summary=item.summary,
            decision_status=item.decision_status,
            linked_record_ids=item.linked_record_ids,
            rationale=item.rationale,
            supporting_uris=item.supporting_uris,
            escalated=item.escalated,
            escalation_type=item.escalation_type,
            follow_up_note=item.follow_up_note,
            due_state=item.due_state,
            remediation_class=remediation_class,
            recommended_steps=_recommended_steps(item, remediation_class),
        )
        remediation_items.append(remediation_item)
        remediation_class_map[remediation_class].append(remediation_item)

    remediation_class_groups = [
        ScientificFollowUpRemediationClassGroup(
            remediation_class=remediation_class,
            action_ids=[item.action_id for item in remediation_class_map[remediation_class]],
            due_states=sorted(
                {item.due_state for item in remediation_class_map[remediation_class]},
                key=DUE_STATE_ORDER.index,
            ),
            blocking_action_ids=[
                item.action_id for item in remediation_class_map[remediation_class] if item.blocking
            ],
            action_count=len(remediation_class_map[remediation_class]),
        )
        for remediation_class in REMEDIATION_ORDER
        if remediation_class_map[remediation_class]
    ]

    resource_specs, documentation_resource_uri = _remediation_docs(handoff_packet.source_workflow)
    referenced_resources: dict[tuple[str, str], ReviewResourceReference] = {
        (resource.role, resource.uri): resource for resource in handoff_packet.referenced_resources
    }
    for role, uri, description in resource_specs:
        referenced_resources.setdefault(
            (role, uri),
            ReviewResourceReference(role=role, uri=uri, description=description),
        )

    notes = [
        "Scientific follow-up owner remediation packet is derived from the owner handoff packet and does not mutate queue, board, signoff, or dossier state.",
        "Remediation classes are deterministic operational guidance layered on top of owner-lane routing.",
    ]
    if handoff_packet.legal_limit_reviews:
        notes.append(
            "Legal-limit support reviews are preserved on the remediation packet so owner actions stay anchored to the underlying exact, partial, anchor-only, or explicit-gap support posture."
        )
    if request.packet_note:
        notes.append(request.packet_note)
    if not remediation_items:
        notes.append("No scientific follow-up items were present on the selected owner handoff packet.")

    return ScientificFollowUpOwnerRemediationPacket(
        overall_status=handoff_packet.overall_status,
        target_profile=handoff_packet.target_profile,
        source_handoff_packet_id=handoff_packet.packet_id,
        source_board_id=handoff_packet.source_board_id,
        source_bundle_id=handoff_packet.source_bundle_id,
        source_dossier_id=handoff_packet.source_dossier_id,
        source_dossier_status=handoff_packet.source_dossier_status,
        source_workflow=handoff_packet.source_workflow,
        bundle_profile=handoff_packet.bundle_profile,
        owner_lane=handoff_packet.owner_lane,
        legal_limit_reviews=handoff_packet.legal_limit_reviews,
        due_state_filter=handoff_packet.due_state_filter,
        action_items=remediation_items,
        remediation_class_groups=remediation_class_groups,
        action_count=len(remediation_items),
        blocking_action_count=sum(1 for item in remediation_items if item.blocking),
        resolve_now_action_ids=[
            item.action_id
            for item in remediation_class_map[ScientificFollowUpRemediationClass.RESOLVE_NOW]
        ],
        review_this_cycle_action_ids=[
            item.action_id
            for item in remediation_class_map[ScientificFollowUpRemediationClass.REVIEW_THIS_CYCLE]
        ],
        track_in_progress_action_ids=[
            item.action_id
            for item in remediation_class_map[ScientificFollowUpRemediationClass.TRACK_IN_PROGRESS]
        ],
        record_closure_action_ids=[
            item.action_id
            for item in remediation_class_map[ScientificFollowUpRemediationClass.RECORD_CLOSURE]
        ],
        recommended_remediation_sequence=[
            action_id for action_id in handoff_packet.recommended_owner_sequence
        ],
        documentation_resource_uri=documentation_resource_uri,
        referenced_resources=list(referenced_resources.values()),
        notes=notes,
    )
