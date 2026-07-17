from __future__ import annotations

from dietary_mcp.models import (
    ExportScientificFollowUpOwnerHandoffPacketRequest,
    ReviewResourceReference,
    ScientificFollowUpDueState,
    ScientificFollowUpDueStateGroup,
    ScientificFollowUpOwnerHandoffPacket,
    ScientificFollowUpOwnerLaneGroup,
)


DUE_STATE_ORDER = [
    ScientificFollowUpDueState.IMMEDIATE,
    ScientificFollowUpDueState.CURRENT_CYCLE,
    ScientificFollowUpDueState.IN_PROGRESS,
    ScientificFollowUpDueState.CLOSED_WITH_WAIVER,
    ScientificFollowUpDueState.CLOSED,
]


def _handoff_docs(source_workflow: str) -> tuple[list[tuple[str, str, str]], str]:
    common_resources = [
        (
            "scientific_follow_up_queue_docs",
            "docs://scientific-follow-up-queue-bundle",
            "Operator guide for the readiness-side queue bundle used as the source of truth for owner handoff packets.",
        ),
        (
            "scientific_follow_up_review_board_docs",
            "docs://scientific-follow-up-review-board",
            "Operator guide for reviewer-operable routing of scientific follow-up queues.",
        ),
        (
            "scientific_follow_up_owner_handoff_docs",
            "docs://scientific-follow-up-owner-handoff",
            "Operator guide for owner-lane handoff packets derived from the scientific follow-up review board.",
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
            "docs://scientific-follow-up-owner-handoff",
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
            "docs://scientific-follow-up-owner-handoff",
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
        "docs://scientific-follow-up-owner-handoff",
    )


def export_scientific_follow_up_owner_handoff_packet(
    request: ExportScientificFollowUpOwnerHandoffPacketRequest,
) -> ScientificFollowUpOwnerHandoffPacket:
    board = request.board
    due_state_filter = request.due_state_filter
    allowed_due_states = set(due_state_filter)

    action_items = [
        item
        for item in board.action_items
        if item.owner_lane == request.owner_lane
        and (not allowed_due_states or item.due_state in allowed_due_states)
    ]
    action_id_set = {item.action_id for item in action_items}
    due_state_groups = [
        ScientificFollowUpDueStateGroup(
            due_state=due_state_group.due_state,
            action_ids=[action_id for action_id in due_state_group.action_ids if action_id in action_id_set],
            blocking_action_ids=[
                action_id for action_id in due_state_group.blocking_action_ids if action_id in action_id_set
            ],
            owner_lanes=[request.owner_lane] if action_id_set else [],
            action_count=sum(1 for action_id in due_state_group.action_ids if action_id in action_id_set),
        )
        for due_state_group in board.due_state_groups
        if any(action_id in action_id_set for action_id in due_state_group.action_ids)
    ]

    owner_lane_group = ScientificFollowUpOwnerLaneGroup(
        owner_lane=request.owner_lane,
        action_ids=[item.action_id for item in action_items],
        blocking_action_ids=[item.action_id for item in action_items if item.blocking],
        due_states=sorted({item.due_state for item in action_items}, key=DUE_STATE_ORDER.index),
        action_count=len(action_items),
    )

    resource_specs, documentation_resource_uri = _handoff_docs(board.source_workflow)
    referenced_resources: dict[tuple[str, str], ReviewResourceReference] = {
        (resource.role, resource.uri): resource for resource in board.referenced_resources
    }
    for role, uri, description in resource_specs:
        referenced_resources.setdefault(
            (role, uri),
            ReviewResourceReference(role=role, uri=uri, description=description),
        )

    notes = [
        "Scientific follow-up owner handoff packet is derived from the review board and does not mutate queue, signoff, or dossier state.",
        "Owner lane and due-state filtering are deterministic routing controls for reviewer handoff only.",
    ]
    if board.legal_limit_reviews:
        notes.append(
            "Legal-limit support reviews remain visible on the handoff packet so owner routing does not overread partial, anchor-only, or explicit-gap jurisdiction support."
        )
    if due_state_filter:
        notes.append(
            "Due-state filter applied: " + ", ".join(due_state.value for due_state in due_state_filter) + "."
        )
    if not action_items:
        notes.append("No scientific follow-up items matched the selected owner lane and due-state filter.")
    if request.packet_note:
        notes.append(request.packet_note)

    return ScientificFollowUpOwnerHandoffPacket(
        overall_status=board.overall_status,
        target_profile=board.target_profile,
        source_board_id=board.board_id,
        source_bundle_id=board.source_bundle_id,
        source_dossier_id=board.source_dossier_id,
        source_dossier_status=board.source_dossier_status,
        source_workflow=board.source_workflow,
        bundle_profile=board.bundle_profile,
        owner_lane=request.owner_lane,
        legal_limit_reviews=board.legal_limit_reviews,
        owner_lane_group=owner_lane_group,
        due_state_filter=due_state_filter,
        action_items=action_items,
        due_state_groups=due_state_groups,
        action_count=len(action_items),
        blocking_action_ids=[item.action_id for item in action_items if item.blocking],
        immediate_action_ids=[item.action_id for item in action_items if item.due_state == ScientificFollowUpDueState.IMMEDIATE],
        current_cycle_action_ids=[
            item.action_id for item in action_items if item.due_state == ScientificFollowUpDueState.CURRENT_CYCLE
        ],
        in_progress_action_ids=[
            item.action_id for item in action_items if item.due_state == ScientificFollowUpDueState.IN_PROGRESS
        ],
        closed_action_ids=[
            item.action_id
            for item in action_items
            if item.due_state in (ScientificFollowUpDueState.CLOSED_WITH_WAIVER, ScientificFollowUpDueState.CLOSED)
        ],
        recommended_owner_sequence=[
            action_id for action_id in board.recommended_triage_sequence if action_id in action_id_set
        ],
        documentation_resource_uri=documentation_resource_uri,
        referenced_resources=list(referenced_resources.values()),
        notes=notes,
    )
