from __future__ import annotations

from dietary_mcp.models import (
    ExportScientificFollowUpReviewBoardRequest,
    ReviewResourceReference,
    ScientificFollowUpDueState,
    ScientificFollowUpDueStateGroup,
    ScientificFollowUpOwnerLane,
    ScientificFollowUpOwnerLaneGroup,
    ScientificFollowUpQueueLabel,
    ScientificFollowUpReviewBoard,
    ScientificFollowUpReviewBoardItem,
)


OWNER_ORDER = [
    ScientificFollowUpOwnerLane.REVIEW_LEAD,
    ScientificFollowUpOwnerLane.REGULATORY_REVIEWER,
    ScientificFollowUpOwnerLane.SCIENTIFIC_REVIEWER,
]
DUE_STATE_ORDER = [
    ScientificFollowUpDueState.IMMEDIATE,
    ScientificFollowUpDueState.CURRENT_CYCLE,
    ScientificFollowUpDueState.IN_PROGRESS,
    ScientificFollowUpDueState.CLOSED_WITH_WAIVER,
    ScientificFollowUpDueState.CLOSED,
]
REGULATORY_CATEGORIES = {
    "scientific_ledger_governance",
}


def _owner_lane(item) -> ScientificFollowUpOwnerLane:
    queue_labels = set(item.queue_labels)
    if ScientificFollowUpQueueLabel.ESCALATED in queue_labels:
        return ScientificFollowUpOwnerLane.REVIEW_LEAD
    if item.category in REGULATORY_CATEGORIES:
        return ScientificFollowUpOwnerLane.REGULATORY_REVIEWER
    return ScientificFollowUpOwnerLane.SCIENTIFIC_REVIEWER


def _due_state(item) -> ScientificFollowUpDueState:
    queue_labels = set(item.queue_labels)
    if ScientificFollowUpQueueLabel.ESCALATED in queue_labels:
        return ScientificFollowUpDueState.IMMEDIATE
    if item.blocking and ScientificFollowUpQueueLabel.OPEN in queue_labels:
        return ScientificFollowUpDueState.IMMEDIATE
    if ScientificFollowUpQueueLabel.OPEN in queue_labels or ScientificFollowUpQueueLabel.PENDING in queue_labels:
        return ScientificFollowUpDueState.CURRENT_CYCLE
    if ScientificFollowUpQueueLabel.ACKNOWLEDGED in queue_labels:
        return ScientificFollowUpDueState.IN_PROGRESS
    if ScientificFollowUpQueueLabel.WAIVED in queue_labels:
        return ScientificFollowUpDueState.CLOSED_WITH_WAIVER
    return ScientificFollowUpDueState.CLOSED


def _recommended_triage_sequence(action_items: list[ScientificFollowUpReviewBoardItem]) -> list[str]:
    sorted_items = sorted(
        action_items,
        key=lambda item: (
            DUE_STATE_ORDER.index(item.due_state),
            OWNER_ORDER.index(item.owner_lane),
            item.triage_rank,
        ),
    )
    return [item.action_id for item in sorted_items]


def _board_docs(source_workflow: str) -> tuple[list[tuple[str, str, str]], str]:
    common_resources = [
        (
            "scientific_follow_up_queue_docs",
            "docs://scientific-follow-up-queue-bundle",
            "Operator guide for the readiness-side queue bundle used as the source of truth for this board.",
        ),
        (
            "scientific_follow_up_review_board_docs",
            "docs://scientific-follow-up-review-board",
            "Operator guide for reviewer-operable routing of scientific follow-up queues.",
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
            "docs://scientific-follow-up-review-board",
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
            "docs://scientific-follow-up-review-board",
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
        "docs://scientific-follow-up-review-board",
    )


def export_scientific_follow_up_review_board(
    request: ExportScientificFollowUpReviewBoardRequest,
) -> ScientificFollowUpReviewBoard:
    queue_bundle = request.queue_bundle
    action_items: list[ScientificFollowUpReviewBoardItem] = []
    owner_lane_map: dict[ScientificFollowUpOwnerLane, list[ScientificFollowUpReviewBoardItem]] = {
        lane: [] for lane in OWNER_ORDER
    }
    due_state_map: dict[ScientificFollowUpDueState, list[ScientificFollowUpReviewBoardItem]] = {
        due_state: [] for due_state in DUE_STATE_ORDER
    }

    queue_rank_lookup = {
        action_id: index + 1 for index, action_id in enumerate(queue_bundle.recommended_sequence)
    }
    for item in queue_bundle.action_items:
        board_item = ScientificFollowUpReviewBoardItem(
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
            queue_labels=item.queue_labels,
            owner_lane=_owner_lane(item),
            due_state=_due_state(item),
            triage_rank=queue_rank_lookup.get(item.action_id, len(queue_rank_lookup) + 1),
        )
        action_items.append(board_item)
        owner_lane_map[board_item.owner_lane].append(board_item)
        due_state_map[board_item.due_state].append(board_item)

    owner_lanes = [
        ScientificFollowUpOwnerLaneGroup(
            owner_lane=lane,
            action_ids=[item.action_id for item in owner_lane_map[lane]],
            blocking_action_ids=[item.action_id for item in owner_lane_map[lane] if item.blocking],
            due_states=sorted({item.due_state for item in owner_lane_map[lane]}, key=DUE_STATE_ORDER.index),
            action_count=len(owner_lane_map[lane]),
        )
        for lane in OWNER_ORDER
        if owner_lane_map[lane]
    ]
    due_state_groups = [
        ScientificFollowUpDueStateGroup(
            due_state=due_state,
            action_ids=[item.action_id for item in due_state_map[due_state]],
            blocking_action_ids=[item.action_id for item in due_state_map[due_state] if item.blocking],
            owner_lanes=sorted({item.owner_lane for item in due_state_map[due_state]}, key=OWNER_ORDER.index),
            action_count=len(due_state_map[due_state]),
        )
        for due_state in DUE_STATE_ORDER
        if due_state_map[due_state]
    ]

    resource_specs, documentation_resource_uri = _board_docs(queue_bundle.source_workflow)
    referenced_resources: dict[tuple[str, str], ReviewResourceReference] = {
        (resource.role, resource.uri): resource for resource in queue_bundle.referenced_resources
    }
    for role, uri, description in resource_specs:
        referenced_resources.setdefault(
            (role, uri),
            ReviewResourceReference(role=role, uri=uri, description=description),
        )

    notes = [
        "Scientific follow-up review board is derived from the queue bundle and does not mutate readiness, signoff, or dossier state.",
        "Owner lanes and due states are deterministic routing metadata for reviewer operations, not new regulatory rules.",
    ]
    if queue_bundle.legal_limit_reviews:
        notes.append(
            "Legal-limit support reviews are carried forward unchanged from the queue bundle so routing decisions cannot overread partial or missing jurisdiction support."
        )
    if not action_items:
        notes.append("No scientific follow-up items were present on the source queue bundle.")
    if request.board_note:
        notes.append(request.board_note)

    return ScientificFollowUpReviewBoard(
        overall_status=queue_bundle.overall_status,
        target_profile=queue_bundle.target_profile,
        source_bundle_id=queue_bundle.bundle_id,
        source_dossier_id=queue_bundle.source_dossier_id,
        source_dossier_status=queue_bundle.source_dossier_status,
        source_workflow=queue_bundle.source_workflow,
        bundle_profile=queue_bundle.bundle_profile,
        legal_limit_reviews=queue_bundle.legal_limit_reviews,
        action_items=action_items,
        owner_lanes=owner_lanes,
        due_state_groups=due_state_groups,
        immediate_action_ids=[item.action_id for item in due_state_map[ScientificFollowUpDueState.IMMEDIATE]],
        current_cycle_action_ids=[
            item.action_id for item in due_state_map[ScientificFollowUpDueState.CURRENT_CYCLE]
        ],
        in_progress_action_ids=[item.action_id for item in due_state_map[ScientificFollowUpDueState.IN_PROGRESS]],
        closed_action_ids=[
            item.action_id
            for due_state in (
                ScientificFollowUpDueState.CLOSED_WITH_WAIVER,
                ScientificFollowUpDueState.CLOSED,
            )
            for item in due_state_map[due_state]
        ],
        recommended_triage_sequence=_recommended_triage_sequence(action_items),
        documentation_resource_uri=documentation_resource_uri,
        referenced_resources=list(referenced_resources.values()),
        notes=notes,
    )
