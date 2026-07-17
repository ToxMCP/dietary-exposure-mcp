from __future__ import annotations

from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.models import (
    ExportMetalsMonitoringSignoffPacketRequest,
    InteroperabilityActionDecisionStatus,
    InteroperabilitySignoffStatus,
    MetalsMonitoringSignoffActionItem,
    MetalsMonitoringSignoffPacket,
    ReadinessStatus,
    ReviewResourceReference,
)
from dietary_mcp.scientific_ledger import build_scientific_ledger_action_specs


def _build_action_specs(bundle) -> list[dict]:
    occurrence_record_ids = [item.record_id for item in bundle.occurrence_records]
    review_focus_ids = [item.focus_id for item in bundle.review_focus_records]
    combined_record_ids = occurrence_record_ids + review_focus_ids

    specs = []
    if bundle.occurrence_records:
        specs.append(
            {
                "actionId": "review_occurrence_context",
                "category": "occurrence_context",
                "title": "Review occurrence context",
                "priority": ReadinessStatus.REVIEW_REQUIRED,
                "blocking": False,
                "summary": "Review monitored occurrence context, high-attention foods, and trend signals before interpreting this metals family.",
                "linkedRecordIds": occurrence_record_ids,
            }
        )
    else:
        specs.append(
            {
                "actionId": "resolve_occurrence_context",
                "category": "occurrence_context",
                "title": "Resolve occurrence context",
                "priority": ReadinessStatus.FAIL,
                "blocking": True,
                "summary": "Add governed occurrence context before metals monitoring signoff can close.",
                "linkedRecordIds": combined_record_ids,
            }
        )
    if bundle.priority_food_groups or bundle.high_attention_foods:
        specs.append(
            {
                "actionId": "review_priority_food_groups",
                "category": "priority_food_groups",
                "title": "Review priority food groups",
                "priority": ReadinessStatus.REVIEW_REQUIRED,
                "blocking": False,
                "summary": "Confirm that the highest-priority food groups and high-attention foods remain explicit in the review package.",
                "linkedRecordIds": combined_record_ids,
            }
        )
    if bundle.sensitive_population_groups:
        specs.append(
            {
                "actionId": "review_sensitive_populations",
                "category": "sensitive_populations",
                "title": "Review sensitive populations",
                "priority": ReadinessStatus.FAIL,
                "blocking": True,
                "summary": "Confirm that sensitive-population context is reviewed explicitly before reviewer signoff is recorded.",
                "linkedRecordIds": combined_record_ids,
            }
        )
    if bundle.review_focus_records:
        specs.append(
            {
                "actionId": "review_commodity_focus_prompts",
                "category": "commodity_focus",
                "title": "Review commodity-focus prompts",
                "priority": ReadinessStatus.REVIEW_REQUIRED,
                "blocking": False,
                "summary": "Work through the governed commodity- and population-focus prompts linked to this bundle.",
                "linkedRecordIds": review_focus_ids,
            }
        )
    specs.extend(
        build_scientific_ledger_action_specs(
            ledger=bundle.uncertainty_and_assumption_ledger,
        )
    )
    if (
        bundle.covered_source_ids
        or bundle.covered_method_ids
        or bundle.covered_legal_authority_ids
        or bundle.covered_reference_value_record_ids
    ):
        specs.append(
            {
                "actionId": "review_governance_links",
                "category": "governance_links",
                "title": "Review governance links",
                "priority": ReadinessStatus.FAIL,
                "blocking": True,
                "summary": "Confirm that source, method, legal, dataset, and reference-value links are sufficient for the intended review use.",
                "linkedRecordIds": combined_record_ids,
            }
        )
    if bundle.unresolved_linked_occurrence_record_ids:
        specs.append(
            {
                "actionId": "resolve_unlinked_review_focus_records",
                "category": "linkage_resolution",
                "title": "Resolve unlinked review-focus records",
                "priority": ReadinessStatus.FAIL,
                "blocking": True,
                "summary": "Resolve review-focus links that are not covered by the supplied occurrence context before signoff.",
                "linkedRecordIds": bundle.unresolved_linked_occurrence_record_ids,
            }
        )
    return specs


def export_metals_monitoring_signoff_packet(
    request: ExportMetalsMonitoringSignoffPacketRequest,
) -> MetalsMonitoringSignoffPacket:
    interpretation_bundle = request.interpretation_bundle
    action_specs = _build_action_specs(interpretation_bundle)
    known_action_ids = {item["actionId"] for item in action_specs}
    decisions_by_action = {}

    for decision in request.decisions:
        if decision.action_id in decisions_by_action:
            raise DietaryValidationError(
                code="duplicate_metals_monitoring_signoff_decision",
                message=f"Duplicate signoff decision supplied for metals monitoring action {decision.action_id}.",
                suggestion="Provide at most one signoff decision per metals monitoring action.",
            )
        if decision.action_id not in known_action_ids:
            raise DietaryValidationError(
                code="unknown_metals_monitoring_signoff_action",
                message=f"Unknown metals monitoring action in signoff packet: {decision.action_id}.",
                suggestion="Use action ids emitted by the metals monitoring interpretation bundle signoff workflow.",
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

    for resource in interpretation_bundle.referenced_resources:
        add_resource(resource.role, resource.uri, resource.description)
    add_resource(
        "metals_monitoring_signoff_docs",
        "docs://metals-monitoring-signoff",
        "Operator guide for reviewer-facing metals monitoring signoff packets.",
    )

    action_items: list[MetalsMonitoringSignoffActionItem] = []
    pending_action_ids: list[str] = []
    acknowledged_action_ids: list[str] = []
    completed_action_ids: list[str] = []
    waived_action_ids: list[str] = []
    unresolved_blocking_action_ids: list[str] = []

    for action in action_specs:
        decision = decisions_by_action.get(action["actionId"])
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

        if (
            action["blocking"]
            and decision_status in (
                InteroperabilityActionDecisionStatus.COMPLETED,
                InteroperabilityActionDecisionStatus.WAIVED,
            )
            and not supporting_uris
        ):
            raise DietaryValidationError(
                code="missing_metals_monitoring_blocking_support",
                message=(
                    f"Blocking metals monitoring action {action['actionId']} requires supporting URIs when marked "
                    f"{decision_status.value}."
                ),
                suggestion="Attach at least one supporting URI for completed or waived blocking actions.",
            )

        resolved = decision_status in (
            InteroperabilityActionDecisionStatus.COMPLETED,
            InteroperabilityActionDecisionStatus.WAIVED,
        )
        if decision_status == InteroperabilityActionDecisionStatus.PENDING:
            pending_action_ids.append(action["actionId"])
        elif decision_status == InteroperabilityActionDecisionStatus.ACKNOWLEDGED:
            acknowledged_action_ids.append(action["actionId"])
        elif decision_status == InteroperabilityActionDecisionStatus.COMPLETED:
            completed_action_ids.append(action["actionId"])
        else:
            waived_action_ids.append(action["actionId"])

        if action["blocking"] and not resolved:
            unresolved_blocking_action_ids.append(action["actionId"])

        for uri in supporting_uris:
            add_resource(
                "signoff_supporting_resource",
                uri,
                f"Supporting resource cited by reviewer signoff for action {action['actionId']}.",
            )

        action_items.append(
            MetalsMonitoringSignoffActionItem(
                action_id=action["actionId"],
                category=action["category"],
                title=action["title"],
                priority=action["priority"],
                blocking=action["blocking"],
                summary=action["summary"],
                linked_record_ids=action["linkedRecordIds"],
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
        "Signoff packet is a reviewer-facing overlay on top of the metals monitoring interpretation bundle and does not change the underlying bundle content.",
        "Waived actions remain explicitly visible so downstream reviewers can inspect accepted deviations from the default review sequence.",
        "Signed-off status records closure of the governed review workflow only; it does not certify scientific correctness, submission readiness, or regulatory approval.",
    ]
    if interpretation_bundle.legal_limit_reviews:
        notes.append(
            "Attached legal-limit review snapshots remain visible in signoff so family-level partial or missing jurisdiction support cannot be mistaken for a complete legal-limit layer."
        )
    if unresolved_blocking_action_ids:
        notes.append("At least one blocking metals monitoring action remains unresolved in the signoff packet.")
    if request.packet_note:
        notes.append(request.packet_note)

    return MetalsMonitoringSignoffPacket(
        overall_signoff_status=overall_signoff_status,
        reviewer_id=request.reviewer_id,
        reviewer_role=request.reviewer_role,
        source_bundle_id=interpretation_bundle.bundle_id,
        contaminant_family=interpretation_bundle.contaminant_family,
        jurisdiction=interpretation_bundle.jurisdiction,
        authority=interpretation_bundle.authority,
        overall_submission_use=interpretation_bundle.overall_submission_use,
        submission_candidate_allowed=interpretation_bundle.submission_candidate_allowed,
        legal_limit_reviews=interpretation_bundle.legal_limit_reviews,
        action_items=action_items,
        pending_action_ids=pending_action_ids,
        acknowledged_action_ids=acknowledged_action_ids,
        completed_action_ids=completed_action_ids,
        waived_action_ids=waived_action_ids,
        unresolved_blocking_action_ids=unresolved_blocking_action_ids,
        referenced_resources=list(referenced_resources.values()),
        notes=notes,
    )
