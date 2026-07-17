from __future__ import annotations

from dietary_mcp.models import (
    ContaminantLegalLimitLookupResult,
    ExportScientificFollowUpQueueBundleRequest,
    ReviewResourceReference,
    ScientificFollowUpItem,
    ScientificFollowUpQueueBundle,
    ScientificFollowUpQueueBundleItem,
    ScientificFollowUpQueueLabel,
    ScientificFollowUpQueues,
    VersionPinnedAdapterReviewDossier,
    VersionPinnedContaminantMonitoringReviewDossier,
    VersionPinnedMetalsMonitoringReviewDossier,
)


QUEUE_FIELD_MAP = {
    ScientificFollowUpQueueLabel.OPEN: "open_action_ids",
    ScientificFollowUpQueueLabel.PENDING: "pending_action_ids",
    ScientificFollowUpQueueLabel.ACKNOWLEDGED: "acknowledged_action_ids",
    ScientificFollowUpQueueLabel.COMPLETED: "completed_action_ids",
    ScientificFollowUpQueueLabel.WAIVED: "waived_action_ids",
    ScientificFollowUpQueueLabel.ESCALATED: "escalated_action_ids",
}
QUEUE_ORDER = [
    ScientificFollowUpQueueLabel.ESCALATED,
    ScientificFollowUpQueueLabel.OPEN,
    ScientificFollowUpQueueLabel.PENDING,
    ScientificFollowUpQueueLabel.ACKNOWLEDGED,
    ScientificFollowUpQueueLabel.WAIVED,
    ScientificFollowUpQueueLabel.COMPLETED,
]


def _legal_limit_review_resource_specs(
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult],
) -> list[tuple[str, str, str]]:
    if not legal_limit_reviews:
        return []

    resource_specs = [
        (
            "contaminant_legal_limits_manifest",
            "contaminant-legal-limits://manifest",
            "Manifest for governed contaminant legal-limit lookup records referenced by readiness-side legal-limit support reviews.",
        ),
        (
            "jurisdiction_coverage_manifest",
            "jurisdiction-coverage://manifest",
            "Manifest for jurisdiction coverage posture referenced by readiness-side legal-limit support reviews.",
        ),
    ]
    for family in sorted({review.contaminant_family.value for review in legal_limit_reviews}):
        resource_specs.append(
            (
                f"contaminant_legal_limits_family_{family}",
                f"contaminant-legal-limits://family/{family}",
                f"Governed contaminant legal-limit records for the {family} family referenced by readiness-side legal-limit support reviews.",
            )
        )
    for jurisdiction in sorted(
        {review.jurisdiction.strip().lower() for review in legal_limit_reviews if review.jurisdiction}
    ):
        resource_specs.extend(
            [
                (
                    f"contaminant_legal_limits_jurisdiction_{jurisdiction}",
                    f"contaminant-legal-limits://jurisdiction/{jurisdiction}",
                    f"Jurisdiction-scoped governed contaminant legal-limit records for {jurisdiction} referenced by readiness-side legal-limit support reviews.",
                ),
                (
                    f"jurisdiction_coverage_jurisdiction_{jurisdiction}",
                    f"jurisdiction-coverage://jurisdiction/{jurisdiction}",
                    f"Jurisdiction coverage posture for {jurisdiction} referenced by readiness-side legal-limit support reviews.",
                ),
            ]
        )
    return resource_specs


def _build_queue_label_lookup(queues: ScientificFollowUpQueues) -> dict[str, list[ScientificFollowUpQueueLabel]]:
    lookup: dict[str, list[ScientificFollowUpQueueLabel]] = {}
    for label in QUEUE_ORDER:
        action_ids = getattr(queues, QUEUE_FIELD_MAP[label])
        for action_id in action_ids:
            lookup.setdefault(action_id, []).append(label)
    return lookup


def _bundle_item(item: ScientificFollowUpItem, queue_labels: list[ScientificFollowUpQueueLabel]) -> ScientificFollowUpQueueBundleItem:
    return ScientificFollowUpQueueBundleItem(
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
        queue_labels=queue_labels,
    )


def _recommended_sequence(
    items: list[ScientificFollowUpItem],
    queues: ScientificFollowUpQueues,
) -> list[str]:
    action_ids = {item.action_id for item in items}
    sequence: list[str] = []
    seen: set[str] = set()

    for label in QUEUE_ORDER:
        for action_id in getattr(queues, QUEUE_FIELD_MAP[label]):
            if action_id in action_ids and action_id not in seen:
                sequence.append(action_id)
                seen.add(action_id)

    for item in items:
        if item.action_id not in seen:
            sequence.append(item.action_id)
            seen.add(item.action_id)

    return sequence


def _source_workflow_and_docs(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
) -> tuple[str, list[tuple[str, str, str]], str]:
    common_resources = [
        (
            "operator_guide",
            "docs://operator-guide",
            "Operator guide for governed dossier readiness and review workflows.",
        ),
        (
            "validation_framework",
            "docs://validation-framework",
            "Validation framework covering governed readiness and follow-up workflows.",
        ),
        (
            "readiness_rules",
            "validation://regulatory-rules",
            "Governed readiness rules applied to review dossier assessments.",
        ),
        (
            "readiness_profiles",
            "validation://readiness-profiles",
            "Governed readiness profiles for adapter and contaminant-family dossier review.",
        ),
    ]
    if isinstance(dossier, VersionPinnedAdapterReviewDossier):
        return (
            "adapter_review_dossier",
            common_resources
            + [
                (
                    "adapter_review_docs",
                    "docs://adapter-import-walkthroughs",
                    "Workflow guide for adapter review, walkthrough comparison, and dossier readiness.",
                ),
                (
                    "governance_docs",
                    "docs://regulatory-governance",
                    "Governance semantics for adapter model families and EU-first readiness posture.",
                ),
            ],
            "docs://regulatory-governance",
        )
    if isinstance(dossier, VersionPinnedContaminantMonitoringReviewDossier):
        return (
            "contaminant_monitoring_review_dossier",
            common_resources
            + [
                (
                    "contaminant_monitoring_review_docs",
                    "docs://contaminant-monitoring-review-dossier",
                    "Workflow guide for contaminant monitoring readiness, signoff, and dossier export.",
                ),
                (
                    "contaminant_monitoring_signoff_docs",
                    "docs://contaminant-monitoring-signoff",
                    "Reviewer signoff guidance for contaminant monitoring action items and waivers.",
                ),
                (
                    "source_database_docs",
                    "docs://regulatory-source-databases",
                    "Governed source database documentation for contaminant monitoring evidence and family posture.",
                ),
            ],
            "docs://contaminant-monitoring-review-dossier",
        )
    return (
        "metals_monitoring_review_dossier",
        common_resources
        + [
            (
                "metals_monitoring_review_docs",
                "docs://metals-monitoring-review-dossier",
                "Workflow guide for metals monitoring readiness, signoff, and dossier export.",
            ),
            (
                "metals_monitoring_signoff_docs",
                "docs://metals-monitoring-signoff",
                "Reviewer signoff guidance for metals monitoring action items and waivers.",
            ),
            (
                "source_database_docs",
                "docs://regulatory-source-databases",
                "Governed source database documentation for metals occurrence, focus, and family posture.",
            ),
        ],
        "docs://metals-monitoring-review-dossier",
    )


def export_scientific_follow_up_queue_bundle(
    request: ExportScientificFollowUpQueueBundleRequest,
) -> ScientificFollowUpQueueBundle:
    assessment = request.assessment
    queue_labels = _build_queue_label_lookup(assessment.scientific_follow_up_queues)
    action_items = [
        _bundle_item(item, queue_labels.get(item.action_id, []))
        for item in assessment.scientific_follow_up_items
    ]
    source_workflow, resource_specs, documentation_resource_uri = _source_workflow_and_docs(request.dossier)
    referenced_resources: dict[tuple[str, str], ReviewResourceReference] = {}
    for role, uri, description in (
        resource_specs + _legal_limit_review_resource_specs(assessment.legal_limit_reviews)
    ):
        referenced_resources.setdefault(
            (role, uri),
            ReviewResourceReference(role=role, uri=uri, description=description),
        )

    notes = [
        "Scientific follow-up queue bundle is derived from the readiness assessment and does not mutate the underlying dossier or signoff decisions.",
        "Queue labels are additive; a single follow-up item can appear in more than one queue when waiver or escalation overlays coexist.",
    ]
    if assessment.legal_limit_reviews:
        notes.append(
            "Legal-limit support reviews are inherited unchanged from readiness so downstream queues preserve exact, partial, anchor-only, and explicit-gap support semantics without borrowing across jurisdictions or matrices."
        )
    if not action_items:
        notes.append("No scientific follow-up items were present on the readiness assessment for the selected dossier and profile.")
    if request.bundle_note:
        notes.append(request.bundle_note)

    queues = assessment.scientific_follow_up_queues
    return ScientificFollowUpQueueBundle(
        overall_status=assessment.overall_status,
        target_profile=assessment.target_profile,
        source_dossier_id=request.dossier.dossier_id,
        source_dossier_status=(
            request.dossier.dossier_status
            if isinstance(request.dossier.dossier_status, str)
            else request.dossier.dossier_status.value
        ),
        source_workflow=source_workflow,
        bundle_profile=request.dossier.bundle_profile,
        legal_limit_reviews=assessment.legal_limit_reviews,
        action_items=action_items,
        queues=queues,
        open_action_count=len(queues.open_action_ids),
        pending_action_count=len(queues.pending_action_ids),
        acknowledged_action_count=len(queues.acknowledged_action_ids),
        completed_action_count=len(queues.completed_action_ids),
        waived_action_count=len(queues.waived_action_ids),
        escalated_action_count=len(queues.escalated_action_ids),
        recommended_sequence=_recommended_sequence(assessment.scientific_follow_up_items, queues),
        documentation_resource_uri=documentation_resource_uri,
        referenced_resources=list(referenced_resources.values()),
        notes=notes,
    )
