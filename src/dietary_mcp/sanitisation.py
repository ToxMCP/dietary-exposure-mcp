from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.models import (
    BundleProfile,
    ConfidentialityTag,
    ExportSanitisedPublicReviewDossierRequest,
    SanitisedPublicContaminantMonitoringReviewBundle,
    SanitisedPublicMetalsMonitoringReviewBundle,
    SanitisedPublicScientificFollowUpOwnerSignoffBundle,
    SanitisedPublicTradeJurisdictionRiskProfile,
    SanitisedPublicTradeRiskReport,
    SanitisedPublicTradeRiskReviewBundle,
    LimitationNote,
    SanitisationRecord,
    SanitisationState,
    SanitisedPublicAdapterReviewBundle,
    SanitisedPublicReviewDossier,
    VersionPinnedAdapterReviewDossier,
    VersionPinnedContaminantMonitoringReviewDossier,
    VersionPinnedMetalsMonitoringReviewDossier,
    VersionPinnedScientificFollowUpOwnerSignoffDossier,
    VersionPinnedTradeRiskReviewDossier,
)


def _resource_replacement_marker(resource_role: str) -> dict[str, str]:
    return {
        "type": "removed_resource",
        "reason": "confidential_resource",
        "resourceRole": resource_role,
    }


def _field_replacement_marker(field_path: str) -> dict[str, str]:
    return {
        "type": "redacted_field",
        "reason": "confidential_field",
        "fieldPath": field_path,
    }


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def read_sanitisation_rules(repo_root: Path) -> dict:
    return json.loads((_validation_root(repo_root) / "sanitisation_rules.json").read_text())


def _source_workflow_for_dossier(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
        | VersionPinnedScientificFollowUpOwnerSignoffDossier
        | VersionPinnedTradeRiskReviewDossier
    ),
) -> str:
    if isinstance(dossier, VersionPinnedAdapterReviewDossier):
        return "adapter_review_dossier"
    if isinstance(dossier, VersionPinnedContaminantMonitoringReviewDossier):
        return "contaminant_monitoring_review_dossier"
    if isinstance(dossier, VersionPinnedMetalsMonitoringReviewDossier):
        return "metals_monitoring_review_dossier"
    if isinstance(dossier, VersionPinnedScientificFollowUpOwnerSignoffDossier):
        return "scientific_follow_up_owner_signoff_dossier"
    return "trade_risk_review_dossier"


def _dossier_status_text(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
        | VersionPinnedScientificFollowUpOwnerSignoffDossier
        | VersionPinnedTradeRiskReviewDossier
    ),
) -> str:
    status = dossier.dossier_status
    return status.value if hasattr(status, "value") else str(status)


def _public_resources_and_records(resources) -> tuple[list, list[SanitisationRecord]]:
    public_resources = []
    sanitisation_records: list[SanitisationRecord] = []
    for resource in resources:
        if resource.confidentiality_tag == ConfidentialityTag.CONFIDENTIAL:
            sanitisation_records.append(
                SanitisationRecord(
                    target_path=f"public_review_bundle.referenced_resources.{resource.role}",
                    target_kind="resource",
                    confidentiality_tag=resource.confidentiality_tag,
                    sanitisation_state=SanitisationState.REMOVED,
                    replacement_marker=_resource_replacement_marker(resource.role),
                    note="Confidential review resources are omitted from sanitised public bundles.",
                )
            )
            continue
        public_resources.append(resource.model_copy(update={"sanitisation_state": SanitisationState.RETAINED}))
    return public_resources, sanitisation_records


def _public_pinned_resources_and_records(pinned_resources) -> tuple[list, list[SanitisationRecord]]:
    public_pinned_resources = []
    sanitisation_records: list[SanitisationRecord] = []
    for fingerprint in pinned_resources:
        if fingerprint.confidentiality_tag == ConfidentialityTag.CONFIDENTIAL:
            sanitisation_records.append(
                SanitisationRecord(
                    target_path=f"pinned_resources.{fingerprint.role}",
                    target_kind="resource",
                    confidentiality_tag=fingerprint.confidentiality_tag,
                    sanitisation_state=SanitisationState.REMOVED,
                    replacement_marker=_resource_replacement_marker(fingerprint.role),
                    note="Confidential pinned resources are omitted from sanitised public dossiers.",
                )
            )
            continue
        public_pinned_resources.append(
            fingerprint.model_copy(update={"sanitisation_state": SanitisationState.RETAINED})
        )
    return public_pinned_resources, sanitisation_records


def _field_redaction_records(confidentiality_annotations) -> list[SanitisationRecord]:
    sanitisation_records: list[SanitisationRecord] = []
    for annotation in confidentiality_annotations:
        if annotation.target_kind != "field" or annotation.confidentiality_tag != ConfidentialityTag.CONFIDENTIAL:
            continue
        sanitisation_records.append(
            SanitisationRecord(
                target_path=annotation.target_path,
                target_kind=annotation.target_kind,
                confidentiality_tag=annotation.confidentiality_tag,
                sanitisation_state=SanitisationState.REDACTED,
                replacement_marker=_field_replacement_marker(annotation.target_path),
                note=annotation.rationale,
            )
        )
    return sanitisation_records


def export_sanitised_public_review_dossier(
    request: ExportSanitisedPublicReviewDossierRequest,
) -> SanitisedPublicReviewDossier:
    dossier = request.dossier
    if dossier.bundle_profile == BundleProfile.SANITISED_PUBLIC:
        raise DietaryValidationError(
            code="review_dossier_already_sanitised",
            message="Sanitised-public review dossiers cannot be sanitised a second time.",
            suggestion="Provide an internal-review or submission-candidate dossier as the export source.",
        )

    if isinstance(dossier, VersionPinnedAdapterReviewDossier):
        public_resources, resource_records = _public_resources_and_records(
            dossier.review_bundle.referenced_resources
        )
        public_bundle = SanitisedPublicAdapterReviewBundle(
            review_status=dossier.review_bundle.review_status,
            model_family=dossier.review_bundle.model_family,
            template_name=dossier.review_bundle.template_name,
            walkthrough_name=dossier.review_bundle.walkthrough_name,
            comparison_status=dossier.review_bundle.comparison_result.status,
            matched_field_count=dossier.review_bundle.matched_field_count,
            mismatch_field_count=dossier.review_bundle.mismatch_field_count,
            mismatch_fields=dossier.review_bundle.comparison_result.mismatch_fields,
            referenced_resources=public_resources,
            dependencies=dossier.review_bundle.dependencies,
            notes=[
                "Sanitised public bundle retains review outcome, governed provenance, and non-confidential review resources only.",
                "Confidential fields and resources are represented in sanitisation_records rather than exposed directly.",
                *dossier.review_bundle.notes,
            ],
        )
        legal_limit_reviews = []
        emerging_contaminant_snapshot = None
        escalation_required = False
        escalation_action_ids: list[str] = []
        extra_notes: list[str] = []
    elif isinstance(dossier, VersionPinnedContaminantMonitoringReviewDossier):
        public_resources, resource_records = _public_resources_and_records(
            dossier.signoff_packet.referenced_resources
        )
        public_bundle = SanitisedPublicContaminantMonitoringReviewBundle(
            source_bundle_id=dossier.interpretation_bundle.bundle_id,
            source_packet_id=dossier.signoff_packet.packet_id,
            check_status=dossier.interpretation_bundle.check_status,
            overall_signoff_status=dossier.signoff_packet.overall_signoff_status,
            contaminant_family=dossier.interpretation_bundle.contaminant_family,
            jurisdiction=dossier.interpretation_bundle.jurisdiction,
            authority=dossier.interpretation_bundle.authority,
            dataset_id=dossier.interpretation_bundle.dataset_id,
            overall_submission_use=dossier.interpretation_bundle.overall_submission_use,
            submission_candidate_allowed=dossier.interpretation_bundle.submission_candidate_allowed,
            reporting_profile_summary=dossier.reporting_profile_summary,
            pending_action_ids=dossier.signoff_packet.pending_action_ids,
            acknowledged_action_ids=dossier.signoff_packet.acknowledged_action_ids,
            completed_action_ids=dossier.signoff_packet.completed_action_ids,
            waived_action_ids=dossier.signoff_packet.waived_action_ids,
            unresolved_blocking_action_ids=dossier.signoff_packet.unresolved_blocking_action_ids,
            referenced_resources=public_resources,
            notes=[
                "Sanitised public contaminant monitoring bundle retains governed signoff state, legal-limit posture, and non-confidential review resources only.",
                "Confidential fields and resources are represented in sanitisation_records rather than exposed directly.",
                *dossier.interpretation_bundle.notes,
                *dossier.signoff_packet.notes,
            ],
        )
        legal_limit_reviews = dossier.signoff_packet.legal_limit_reviews
        emerging_contaminant_snapshot = dossier.emerging_contaminant_snapshot
        escalation_required = dossier.escalation_required
        escalation_action_ids = [item.action_id for item in dossier.escalation_items]
        extra_notes = [
            "Sanitised public contaminant monitoring dossier preserves legal-limit review posture so partial, anchor-only, or missing jurisdiction support remains explicit in non-confidential exchange."
        ]
    elif isinstance(dossier, VersionPinnedMetalsMonitoringReviewDossier):
        public_resources, resource_records = _public_resources_and_records(
            dossier.signoff_packet.referenced_resources
        )
        public_bundle = SanitisedPublicMetalsMonitoringReviewBundle(
            source_bundle_id=dossier.interpretation_bundle.bundle_id,
            source_packet_id=dossier.signoff_packet.packet_id,
            overall_signoff_status=dossier.signoff_packet.overall_signoff_status,
            contaminant_family=dossier.interpretation_bundle.contaminant_family,
            jurisdiction=dossier.interpretation_bundle.jurisdiction,
            authority=dossier.interpretation_bundle.authority,
            overall_submission_use=dossier.interpretation_bundle.overall_submission_use,
            submission_candidate_allowed=dossier.interpretation_bundle.submission_candidate_allowed,
            priority_food_groups=dossier.interpretation_bundle.priority_food_groups,
            high_attention_foods=dossier.interpretation_bundle.high_attention_foods,
            focus_foods=dossier.interpretation_bundle.focus_foods,
            sensitive_population_groups=dossier.interpretation_bundle.sensitive_population_groups,
            trend_signals=dossier.interpretation_bundle.trend_signals,
            pending_action_ids=dossier.signoff_packet.pending_action_ids,
            acknowledged_action_ids=dossier.signoff_packet.acknowledged_action_ids,
            completed_action_ids=dossier.signoff_packet.completed_action_ids,
            waived_action_ids=dossier.signoff_packet.waived_action_ids,
            unresolved_blocking_action_ids=dossier.signoff_packet.unresolved_blocking_action_ids,
            referenced_resources=public_resources,
            notes=[
                "Sanitised public metals monitoring bundle retains governed signoff state, family-level legal-limit posture, and non-confidential review resources only.",
                "Confidential fields and resources are represented in sanitisation_records rather than exposed directly.",
                *dossier.interpretation_bundle.notes,
                *dossier.signoff_packet.notes,
            ],
        )
        legal_limit_reviews = dossier.signoff_packet.legal_limit_reviews
        emerging_contaminant_snapshot = dossier.emerging_contaminant_snapshot
        escalation_required = dossier.escalation_required
        escalation_action_ids = [item.action_id for item in dossier.escalation_items]
        extra_notes = [
            "Sanitised public metals monitoring dossier preserves legal-limit review posture so family-level partial or missing jurisdiction support remains explicit in non-confidential exchange."
        ]
    elif isinstance(dossier, VersionPinnedScientificFollowUpOwnerSignoffDossier):
        public_resources, resource_records = _public_resources_and_records(
            dossier.signoff_packet.referenced_resources
        )
        public_bundle = SanitisedPublicScientificFollowUpOwnerSignoffBundle(
            source_bundle_id=dossier.signoff_packet.source_bundle_id,
            source_packet_id=dossier.signoff_packet.packet_id,
            source_dossier_status=dossier.signoff_packet.source_dossier_status,
            overall_signoff_status=dossier.signoff_packet.overall_signoff_status,
            overall_status=dossier.signoff_packet.overall_status,
            target_profile=dossier.signoff_packet.target_profile,
            owner_lane=dossier.signoff_packet.owner_lane,
            due_state_filter=dossier.signoff_packet.due_state_filter,
            pending_action_ids=dossier.signoff_packet.pending_action_ids,
            acknowledged_action_ids=dossier.signoff_packet.acknowledged_action_ids,
            completed_action_ids=dossier.signoff_packet.completed_action_ids,
            waived_action_ids=dossier.signoff_packet.waived_action_ids,
            unresolved_blocking_action_ids=dossier.signoff_packet.unresolved_blocking_action_ids,
            resolve_now_action_ids=dossier.signoff_packet.resolve_now_action_ids,
            review_this_cycle_action_ids=dossier.signoff_packet.review_this_cycle_action_ids,
            track_in_progress_action_ids=dossier.signoff_packet.track_in_progress_action_ids,
            record_closure_action_ids=dossier.signoff_packet.record_closure_action_ids,
            recommended_signoff_sequence=dossier.signoff_packet.recommended_signoff_sequence,
            documentation_resource_uri=dossier.signoff_packet.documentation_resource_uri,
            referenced_resources=public_resources,
            notes=[
                "Sanitised public owner-lane signoff bundle retains lane status, legal-limit posture, and escalation context without exposing internal payload fingerprints.",
                "Confidential pinned payload resources are represented in sanitisation_records rather than exposed directly.",
                *dossier.signoff_packet.notes,
            ],
        )
        legal_limit_reviews = dossier.legal_limit_reviews
        emerging_contaminant_snapshot = dossier.emerging_contaminant_snapshot
        escalation_required = dossier.escalation_required
        escalation_action_ids = [item.action_id for item in dossier.escalation_items]
        extra_notes = [
            "Sanitised public owner-lane signoff dossier preserves owner-lane waiver and blocking escalation posture while removing the exact upstream dossier and owner-packet payload fingerprints."
        ]
    else:
        public_resources, resource_records = _public_resources_and_records(
            dossier.review_bundle.referenced_resources
        )
        public_bundle = SanitisedPublicTradeRiskReviewBundle(
            review_status=dossier.review_bundle.review_status,
            trade_report=SanitisedPublicTradeRiskReport(
                jurisdiction_profiles=[
                    SanitisedPublicTradeJurisdictionRiskProfile(
                        jurisdiction=profile.jurisdiction,
                        mrl_violations=profile.mrl_violations,
                        trade_status=profile.trade_status,
                        status_reason=profile.status_reason,
                        mrl_coverage_status=profile.mrl_coverage_status,
                        mrl_curated_support_types=profile.mrl_curated_support_types,
                        mrl_curated_scope_commodity_codes=profile.mrl_curated_scope_commodity_codes,
                        reference_value_jurisdiction_status=profile.reference_value_jurisdiction_status,
                        reference_value_curated_support_types=profile.reference_value_curated_support_types,
                        quality_flags=profile.quality_flags,
                        notes=profile.notes,
                    )
                    for profile in dossier.review_bundle.trade_report.jurisdiction_profiles
                ],
                quality_flags=dossier.review_bundle.trade_report.quality_flags,
                notes=dossier.review_bundle.trade_report.notes,
            ),
            review_prompts=dossier.review_bundle.review_prompts,
            documentation_resource_uri=dossier.review_bundle.documentation_resource_uri,
            referenced_resources=public_resources,
            dependencies=dossier.review_bundle.dependencies,
            limitations=dossier.review_bundle.limitations,
            notes=[
                "Sanitised public trade-risk bundle retains jurisdiction screening semantics, non-confidential review prompts, and no-borrowing posture only.",
                "Confidential fields and identity-bearing resources are represented in sanitisation_records rather than exposed directly.",
                *dossier.review_bundle.notes,
            ],
        )
        legal_limit_reviews = []
        emerging_contaminant_snapshot = None
        escalation_required = False
        escalation_action_ids = []
        extra_notes = [
            "Sanitised public trade-risk dossier preserves jurisdiction-level exact, partial, anchor-only, and explicit-gap screening posture without retaining the confidential substance identity layer."
        ]

    public_pinned_resources, pinned_resource_records = _public_pinned_resources_and_records(
        dossier.pinned_resources
    )
    sanitisation_records = (
        resource_records
        + pinned_resource_records
        + _field_redaction_records(dossier.confidentiality_annotations)
    )

    notes = [
        "Sanitised public dossier derived from a version-pinned internal review dossier.",
        "Retained provenance and pinned fingerprints remain machine-readable for public review of non-confidential content.",
        *extra_notes,
        *dossier.notes,
    ]
    limitations = dossier.limitations + [
        LimitationNote(
            code="sanitised_public_bundle",
            message="Sanitised public dossier omits confidential fields and resources and should not be treated as a complete internal review record.",
        )
    ]

    return SanitisedPublicReviewDossier(
        derived_from_dossier_id=dossier.dossier_id,
        dossier_status=_dossier_status_text(dossier),
        source_workflow=_source_workflow_for_dossier(dossier),
        public_review_bundle=public_bundle,
        release_metadata=dossier.release_metadata,
        source_governance_snapshot=dossier.source_governance_snapshot,
        model_governance_snapshot=(
            dossier.model_governance_snapshot
            if isinstance(
                dossier,
                (
                    VersionPinnedAdapterReviewDossier,
                    VersionPinnedScientificFollowUpOwnerSignoffDossier,
                ),
            )
            else None
        ),
        emerging_contaminant_snapshot=emerging_contaminant_snapshot,
        legal_limit_reviews=legal_limit_reviews,
        pinned_resources=public_pinned_resources,
        escalation_required=escalation_required,
        escalation_action_ids=escalation_action_ids,
        sanitisation_records=sanitisation_records,
        limitations=limitations,
        notes=notes,
    )
