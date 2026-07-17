from __future__ import annotations

from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.models import (
    ContaminantMonitoringSignoffActionItem,
    ContaminantMonitoringSignoffPacket,
    ExportContaminantMonitoringSignoffPacketRequest,
    InteroperabilityActionDecisionStatus,
    InteroperabilitySignoffStatus,
    ReadinessStatus,
    ReviewResourceReference,
    Severity,
)
from dietary_mcp.scientific_ledger import build_scientific_ledger_action_specs


def _build_action_specs(bundle) -> list[dict]:
    occurrence_record_ids = [item.record_id for item in bundle.check_result.occurrence_evidence_records]
    analytical_method_record_ids = [item.record_id for item in bundle.check_result.analytical_method_evidence_records]
    review_focus_ids = [item.focus_id for item in bundle.linked_review_focus_records]
    quality_flag_codes = [flag.code for flag in bundle.check_result.quality_flags]
    error_quality_flag_codes = [
        flag.code for flag in bundle.check_result.quality_flags if flag.severity == Severity.ERROR
    ]
    combined_record_ids = occurrence_record_ids + analytical_method_record_ids + review_focus_ids

    specs = []
    if quality_flag_codes or bundle.check_result.header_resolution:
        specs.append(
            {
                "actionId": "review_header_resolution_and_quality_flags",
                "category": "header_resolution",
                "title": "Review header resolution and quality flags",
                "priority": ReadinessStatus.REVIEW_REQUIRED,
                "blocking": False,
                "summary": "Review header alias resolution, row normalization, and any quality flags before using the monitoring interpretation bundle.",
                "linkedRecordIds": quality_flag_codes,
            }
        )
    if error_quality_flag_codes:
        specs.append(
            {
                "actionId": "resolve_critical_quality_flags",
                "category": "quality_flags",
                "title": "Resolve critical quality flags",
                "priority": ReadinessStatus.FAIL,
                "blocking": True,
                "summary": "Resolve error-severity quality flags before contaminant monitoring signoff can close.",
                "linkedRecordIds": error_quality_flag_codes,
            }
        )
    if occurrence_record_ids:
        specs.append(
            {
                "actionId": "review_occurrence_evidence_context",
                "category": "occurrence_evidence",
                "title": "Review occurrence evidence context",
                "priority": ReadinessStatus.REVIEW_REQUIRED,
                "blocking": False,
                "summary": "Confirm that governed occurrence-evidence records match the monitoring matrix, analyte, and interpretation scope.",
                "linkedRecordIds": occurrence_record_ids,
            }
        )
    else:
        specs.append(
            {
                "actionId": "resolve_occurrence_evidence_context",
                "category": "occurrence_evidence",
                "title": "Resolve occurrence evidence context",
                "priority": ReadinessStatus.FAIL,
                "blocking": True,
                "summary": "Add or link governed occurrence-evidence context before contaminant monitoring signoff can close.",
                "linkedRecordIds": quality_flag_codes,
            }
        )
    if analytical_method_record_ids:
        specs.append(
            {
                "actionId": "review_analytical_method_context",
                "category": "analytical_method",
                "title": "Review analytical method context",
                "priority": ReadinessStatus.REVIEW_REQUIRED,
                "blocking": False,
                "summary": "Confirm that governed analytical-method evidence remains appropriate for LOQ, recovery, storage, and uncertainty interpretation.",
                "linkedRecordIds": analytical_method_record_ids,
            }
        )
    if (
        bundle.reporting_profile_summary is not None
        and bundle.reporting_profile_summary.applicable_profile_ids
    ):
        specs.append(
            {
                "actionId": "review_reporting_profile_conventions",
                "category": "reporting_profile",
                "title": "Review reporting-profile conventions",
                "priority": ReadinessStatus.REVIEW_REQUIRED,
                "blocking": False,
                "summary": (
                    "Confirm that the primary regulatory reporting profile remains the lead convention and that optional advisory or detail profiles are not substituted for the primary basis."
                ),
                "linkedRecordIds": bundle.reporting_profile_summary.applicable_profile_ids,
            }
        )
    if review_focus_ids:
        specs.append(
            {
                "actionId": "review_linked_focus_records",
                "category": "review_focus",
                "title": "Review linked focus records",
                "priority": ReadinessStatus.REVIEW_REQUIRED,
                "blocking": False,
                "summary": "Work through linked review-focus records for high-attention foods and sensitive populations referenced by the monitoring check.",
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
        or bundle.covered_dataset_ids
    ):
        specs.append(
            {
                "actionId": "review_governance_links",
                "category": "governance_links",
                "title": "Review governance links",
                "priority": ReadinessStatus.FAIL,
                "blocking": True,
                "summary": "Confirm that source, method, legal, dataset, and reference-value links are sufficient for the intended monitoring review use.",
                "linkedRecordIds": combined_record_ids,
            }
        )
    if bundle.unresolved_linked_review_focus_ids:
        specs.append(
            {
                "actionId": "resolve_unlinked_review_focus_records",
                "category": "linkage_resolution",
                "title": "Resolve unlinked review-focus records",
                "priority": ReadinessStatus.FAIL,
                "blocking": True,
                "summary": "Resolve linked review-focus identifiers that are not covered by the supplied governed defaults before signoff.",
                "linkedRecordIds": bundle.unresolved_linked_review_focus_ids,
            }
        )
    return specs


def export_contaminant_monitoring_signoff_packet(
    request: ExportContaminantMonitoringSignoffPacketRequest,
) -> ContaminantMonitoringSignoffPacket:
    interpretation_bundle = request.interpretation_bundle
    action_specs = _build_action_specs(interpretation_bundle)
    known_action_ids = {item["actionId"] for item in action_specs}
    decisions_by_action = {}

    for decision in request.decisions:
        if decision.action_id in decisions_by_action:
            raise DietaryValidationError(
                code="duplicate_contaminant_monitoring_signoff_decision",
                message=f"Duplicate signoff decision supplied for contaminant monitoring action {decision.action_id}.",
                suggestion="Provide at most one signoff decision per contaminant monitoring action.",
            )
        if decision.action_id not in known_action_ids:
            raise DietaryValidationError(
                code="unknown_contaminant_monitoring_signoff_action",
                message=f"Unknown contaminant monitoring action in signoff packet: {decision.action_id}.",
                suggestion="Use action ids emitted by the contaminant monitoring interpretation bundle signoff workflow.",
            )
        decisions_by_action[decision.action_id] = decision

    referenced_resources: dict[tuple[str, str], ReviewResourceReference] = {}

    def add_resource(role: str, uri: str, description: str) -> None:
        key = (role, uri)
        if key in referenced_resources:
            return
        referenced_resources[key] = ReviewResourceReference(role=role, uri=uri, description=description)

    for resource in interpretation_bundle.referenced_resources:
        add_resource(resource.role, resource.uri, resource.description)
    add_resource(
        "contaminant_monitoring_signoff_docs",
        "docs://contaminant-monitoring-signoff",
        "Operator guide for reviewer-facing contaminant monitoring signoff packets.",
    )

    action_items: list[ContaminantMonitoringSignoffActionItem] = []
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
                code="missing_contaminant_monitoring_blocking_support",
                message=(
                    f"Blocking contaminant monitoring action {action['actionId']} requires supporting URIs when "
                    f"marked {decision_status.value}."
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
            ContaminantMonitoringSignoffActionItem(
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
        "Signoff packet is a reviewer-facing overlay on top of the contaminant monitoring interpretation bundle and does not change the underlying bundle content.",
        "Waived actions remain explicitly visible so downstream reviewers can inspect accepted deviations from the default contaminant monitoring review sequence.",
        "Signed-off status records closure of the governed review workflow only; it does not certify scientific correctness, submission readiness, or regulatory approval.",
    ]
    if interpretation_bundle.legal_limit_reviews:
        notes.append(
            "Attached legal-limit review snapshots remain visible in signoff so partial, anchor-only, or missing jurisdiction support cannot be mistaken for a complete legal-limit layer."
        )
    if unresolved_blocking_action_ids:
        notes.append("At least one blocking contaminant monitoring action remains unresolved in the signoff packet.")
    if request.packet_note:
        notes.append(request.packet_note)

    return ContaminantMonitoringSignoffPacket(
        overall_signoff_status=overall_signoff_status,
        reviewer_id=request.reviewer_id,
        reviewer_role=request.reviewer_role,
        source_bundle_id=interpretation_bundle.bundle_id,
        contaminant_family=interpretation_bundle.contaminant_family,
        jurisdiction=interpretation_bundle.jurisdiction,
        authority=interpretation_bundle.authority,
        dataset_id=interpretation_bundle.dataset_id,
        overall_submission_use=interpretation_bundle.overall_submission_use,
        submission_candidate_allowed=interpretation_bundle.submission_candidate_allowed,
        reporting_profile_summary=interpretation_bundle.reporting_profile_summary,
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
