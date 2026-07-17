from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.guidance import read_doc
from dietary_mcp.models import (
    BundleProfile,
    ConfidentialityAnnotation,
    ConfidentialityTag,
    EmergingContaminantRecord,
    ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest,
    LimitationNote,
    MetalsMonitoringEscalationType,
    ModelGovernanceRecord,
    PinnedResourceFingerprint,
    RegulatorySourceRecord,
    ReleaseMetadataSnapshot,
    SanitisationRecord,
    SanitisationState,
    ScientificFollowUpOwnerSignoffEscalationActionItem,
    VersionPinnedAdapterReviewDossier,
    VersionPinnedContaminantMonitoringReviewDossier,
    VersionPinnedMetalsMonitoringReviewDossier,
    VersionPinnedScientificFollowUpOwnerSignoffDossier,
)
from dietary_mcp.scientific_follow_up_owner_signoff import _signoff_docs


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_json(payload: dict) -> str:
    return _sha256_text(json.dumps(payload, sort_keys=True))


def _source_workflow_for_dossier(
    source_dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
) -> str:
    if isinstance(source_dossier, VersionPinnedAdapterReviewDossier):
        return "adapter_review_dossier"
    if isinstance(source_dossier, VersionPinnedContaminantMonitoringReviewDossier):
        return "contaminant_monitoring_review_dossier"
    return "metals_monitoring_review_dossier"


def _source_dossier_status_text(
    source_dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
) -> str:
    dossier_status = source_dossier.dossier_status
    return dossier_status.value if hasattr(dossier_status, "value") else str(dossier_status)


def _source_governance_snapshots(
    source_dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
) -> tuple[
    list[RegulatorySourceRecord],
    ModelGovernanceRecord | None,
    EmergingContaminantRecord | None,
]:
    if isinstance(source_dossier, VersionPinnedAdapterReviewDossier):
        return (
            source_dossier.source_governance_snapshot,
            source_dossier.model_governance_snapshot,
            None,
        )
    return (
        source_dossier.source_governance_snapshot,
        None,
        source_dossier.emerging_contaminant_snapshot,
    )


def _build_escalation_items(signoff_packet) -> list[ScientificFollowUpOwnerSignoffEscalationActionItem]:
    escalation_items: list[ScientificFollowUpOwnerSignoffEscalationActionItem] = []
    waived_ids = set(signoff_packet.waived_action_ids)
    unresolved_blocking_ids = set(signoff_packet.unresolved_blocking_action_ids)

    for action in signoff_packet.action_items:
        escalation_type = None
        follow_up_note = None
        if action.action_id in waived_ids:
            escalation_type = MetalsMonitoringEscalationType.WAIVER_REVIEW
            follow_up_note = (
                "Owner-lane waiver remains explicit and should be re-checked before downstream closure or audit completion."
            )
        elif action.action_id in unresolved_blocking_ids:
            escalation_type = MetalsMonitoringEscalationType.BLOCKING_FOLLOW_UP
            follow_up_note = (
                "Blocking owner-lane follow-up remains unresolved and requires completion or explicit escalation."
            )

        if escalation_type is None:
            continue

        escalation_items.append(
            ScientificFollowUpOwnerSignoffEscalationActionItem(
                action_id=action.action_id,
                escalation_type=escalation_type,
                category=action.category,
                title=action.title,
                priority=action.priority,
                blocking=action.blocking,
                summary=action.summary,
                decision_status=action.decision_status,
                linked_record_ids=action.linked_record_ids,
                remediation_class=action.remediation_class,
                rationale=action.rationale,
                supporting_uris=action.supporting_uris,
                follow_up_note=follow_up_note,
            )
        )
    return escalation_items


def export_version_pinned_scientific_follow_up_owner_signoff_dossier(
    repo_root: Path,
    request: ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest,
) -> VersionPinnedScientificFollowUpOwnerSignoffDossier:
    signoff_packet = request.signoff_packet
    source_dossier = request.source_dossier
    expected_source_workflow = _source_workflow_for_dossier(source_dossier)
    expected_source_dossier_status = _source_dossier_status_text(source_dossier)

    if signoff_packet.source_dossier_id != source_dossier.dossier_id:
        raise DietaryValidationError(
            code="scientific_follow_up_owner_signoff_dossier_id_mismatch",
            message="Owner signoff dossier requires a signoff packet built from the supplied source dossier.",
            suggestion="Use a source dossier whose dossierId matches the owner signoff packet sourceDossierId.",
        )
    if signoff_packet.source_workflow != expected_source_workflow:
        raise DietaryValidationError(
            code="scientific_follow_up_owner_signoff_dossier_workflow_mismatch",
            message="Owner signoff dossier requires matching source workflow semantics.",
            suggestion="Use a source dossier whose workflow matches the owner signoff packet sourceWorkflow.",
        )
    if signoff_packet.source_dossier_status != expected_source_dossier_status:
        raise DietaryValidationError(
            code="scientific_follow_up_owner_signoff_dossier_status_mismatch",
            message="Owner signoff dossier requires matching source dossier status.",
            suggestion="Use a source dossier whose dossier status matches the owner signoff packet sourceDossierStatus.",
        )
    if signoff_packet.bundle_profile != source_dossier.bundle_profile:
        raise DietaryValidationError(
            code="scientific_follow_up_owner_signoff_dossier_profile_mismatch",
            message="Owner signoff dossier requires matching bundle profiles.",
            suggestion="Use a source dossier and owner signoff packet produced for the same bundle profile.",
        )

    from dietary_mcp.release_artifacts import build_release_reports

    metadata_report = build_release_reports(
        repo_root,
        skip_validation=False,
        skip_examples=True,
    )["metadata-report"]
    source_governance_snapshot, model_governance_snapshot, emerging_contaminant_snapshot = (
        _source_governance_snapshots(source_dossier)
    )

    common_docs, _ = _signoff_docs(signoff_packet.source_workflow)
    signoff_dossier_doc = read_doc(repo_root, "scientific-follow-up-owner-signoff-dossier")

    pinned_resources = [
        PinnedResourceFingerprint(
            role="release_metadata_report",
            uri="release://metadata-report",
            sha256=_sha256_json(metadata_report),
            description="Release metadata report used to pin versioned artifact hashes for this owner-lane scientific follow-up signoff dossier.",
            confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
            sanitisation_state=SanitisationState.RETAINED,
        ),
        PinnedResourceFingerprint(
            role="source_dossier_payload",
            uri=f"internal://scientific-follow-up-source-dossier/{source_dossier.dossier_id}",
            sha256=_sha256_json(source_dossier.model_dump(mode="json", by_alias=True)),
            description="Exact upstream source dossier payload fingerprint referenced by this owner-lane signoff dossier.",
            confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
            sanitisation_state=SanitisationState.RETAINED,
        ),
        PinnedResourceFingerprint(
            role="owner_signoff_packet_payload",
            uri=f"internal://scientific-follow-up-owner-signoff-packet/{signoff_packet.packet_id}",
            sha256=_sha256_json(signoff_packet.model_dump(mode="json", by_alias=True)),
            description="Exact owner-lane signoff packet payload fingerprint captured by this dossier.",
            confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
            sanitisation_state=SanitisationState.RETAINED,
        ),
        PinnedResourceFingerprint(
            role="owner_signoff_dossier_documentation",
            uri="docs://scientific-follow-up-owner-signoff-dossier",
            sha256=_sha256_text(signoff_dossier_doc),
            description="Operator documentation fingerprint for the version-pinned owner-lane signoff dossier workflow.",
        ),
    ]
    for role, uri, description in common_docs:
        pinned_resources.append(
            PinnedResourceFingerprint(
                role=role,
                uri=uri,
                sha256=_sha256_text(read_doc(repo_root, uri.removeprefix("docs://"))),
                description=description,
            )
        )

    escalation_items = _build_escalation_items(signoff_packet)
    escalation_required = bool(escalation_items)
    notes = [
        "Version-pinned owner signoff dossier captures the exact owner-lane signoff packet, source dossier payload, and release metadata used for downstream audit.",
        "Escalation items are derived only from explicit waivers and unresolved blocking actions recorded in the owner signoff packet.",
        "This dossier is an owner-lane audit overlay and does not create a new readiness state, submission engine, or final regulatory decision package.",
    ]
    if signoff_packet.legal_limit_reviews:
        notes.append(
            "Legal-limit support reviews are pinned on the owner-lane dossier so downstream audit can distinguish exact curated support from partial, anchor-only, or explicit-gap posture without cross-jurisdiction borrowing."
        )
    if escalation_required:
        notes.append("At least one owner-lane waiver or unresolved blocking action remains visible in the dossier escalation overlay.")

    return VersionPinnedScientificFollowUpOwnerSignoffDossier(
        bundle_profile=BundleProfile(signoff_packet.bundle_profile),
        dossier_status=signoff_packet.overall_signoff_status,
        source_workflow=signoff_packet.source_workflow,
        source_dossier_id=signoff_packet.source_dossier_id,
        source_dossier_status=signoff_packet.source_dossier_status,
        source_bundle_id=signoff_packet.source_bundle_id,
        signoff_packet=signoff_packet,
        legal_limit_reviews=signoff_packet.legal_limit_reviews,
        release_metadata=ReleaseMetadataSnapshot(
            resource_uri="release://metadata-report",
            release_version=metadata_report["version"],
            defaults_version=metadata_report["defaultsVersion"],
            metadata_report_sha256=_sha256_json(metadata_report),
            artifact_hashes=metadata_report["artifactHashes"],
        ),
        source_governance_snapshot=source_governance_snapshot,
        model_governance_snapshot=model_governance_snapshot,
        emerging_contaminant_snapshot=emerging_contaminant_snapshot,
        pinned_resources=pinned_resources,
        escalation_required=escalation_required,
        escalation_items=escalation_items,
        confidentiality_annotations=[
            ConfidentialityAnnotation(
                target_path="releaseMetadata",
                target_kind="release_metadata_snapshot",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                rationale="Release metadata pin is retained on the owner-lane signoff dossier for internal auditability.",
            )
        ],
        sanitisation_records=[
            SanitisationRecord(
                target_path="releaseMetadata",
                target_kind="release_metadata_snapshot",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                sanitisation_state=SanitisationState.RETAINED,
                note="Release metadata remains retained on the internal-review owner-lane signoff dossier.",
            )
        ],
        limitations=[
            LimitationNote(
                code="version_pinned_not_signed",
                message="Owner-lane signoff dossier uses version-pinned hashes but is not cryptographically signed.",
            ),
            LimitationNote(
                code="owner_lane_review_only",
                message="Owner-lane signoff dossier records audit-ready follow-up, waiver, and escalation posture only.",
            ),
        ],
        notes=notes,
    )
