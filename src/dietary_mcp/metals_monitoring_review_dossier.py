from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.guidance import read_doc
from dietary_mcp.models import (
    ConfidentialityAnnotation,
    ConfidentialityTag,
    EmergingContaminantRecord,
    ExportVersionPinnedMetalsMonitoringReviewDossierRequest,
    InteroperabilitySignoffStatus,
    LimitationNote,
    MetalsMonitoringEscalationActionItem,
    MetalsMonitoringEscalationType,
    PinnedResourceFingerprint,
    ReleaseMetadataSnapshot,
    SanitisationRecord,
    SanitisationState,
    VersionPinnedMetalsMonitoringReviewDossier,
)
from dietary_mcp.readiness import collect_source_governance_snapshot


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_json(payload: dict) -> str:
    return _sha256_text(json.dumps(payload, sort_keys=True))


def _build_family_payload(defaults: DefaultsRegistry, family_id: str) -> tuple[dict, dict]:
    occurrence_payload = {
        "familyId": family_id,
        "records": defaults.get_metals_occurrence_records_for_family(family_id),
    }
    review_focus_payload = {
        "familyId": family_id,
        "records": defaults.get_metals_review_focus_records_for_family(family_id),
    }
    return occurrence_payload, review_focus_payload


def _build_escalation_items(packet) -> list[MetalsMonitoringEscalationActionItem]:
    escalation_items: list[MetalsMonitoringEscalationActionItem] = []
    waived_ids = set(packet.waived_action_ids)
    unresolved_blocking_ids = set(packet.unresolved_blocking_action_ids)

    for action in packet.action_items:
        escalation_type = None
        follow_up_note = None
        if action.action_id in waived_ids:
            escalation_type = MetalsMonitoringEscalationType.WAIVER_REVIEW
            follow_up_note = (
                "Reviewer waiver remains explicit and should be re-checked before downstream reuse or escalation closure."
            )
        elif action.action_id in unresolved_blocking_ids:
            escalation_type = MetalsMonitoringEscalationType.BLOCKING_FOLLOW_UP
            follow_up_note = (
                "Blocking review action remains unresolved and requires follow-up or escalation before signoff can close."
            )

        if escalation_type is None:
            continue

        escalation_items.append(
            MetalsMonitoringEscalationActionItem(
                action_id=action.action_id,
                escalation_type=escalation_type,
                category=action.category,
                title=action.title,
                priority=action.priority,
                blocking=action.blocking,
                summary=action.summary,
                decision_status=action.decision_status,
                linked_record_ids=action.linked_record_ids,
                rationale=action.rationale,
                supporting_uris=action.supporting_uris,
                follow_up_note=follow_up_note,
            )
        )
    return escalation_items


def export_version_pinned_metals_monitoring_review_dossier(
    repo_root: Path,
    request: ExportVersionPinnedMetalsMonitoringReviewDossierRequest,
) -> VersionPinnedMetalsMonitoringReviewDossier:
    interpretation_bundle = request.interpretation_bundle
    signoff_packet = request.signoff_packet

    if signoff_packet.source_bundle_id != interpretation_bundle.bundle_id:
        raise DietaryValidationError(
            code="metals_monitoring_review_dossier_bundle_mismatch",
            message="Metals monitoring review dossier requires a signoff packet built from the supplied interpretation bundle.",
            suggestion="Export the signoff packet from the same metals monitoring interpretation bundle you pass into the dossier exporter.",
        )
    if signoff_packet.contaminant_family != interpretation_bundle.contaminant_family:
        raise DietaryValidationError(
            code="metals_monitoring_review_dossier_family_mismatch",
            message="Metals monitoring review dossier requires matching contaminant families.",
            suggestion="Use a signoff packet and interpretation bundle produced for the same metals family.",
        )
    if signoff_packet.jurisdiction != interpretation_bundle.jurisdiction:
        raise DietaryValidationError(
            code="metals_monitoring_review_dossier_jurisdiction_mismatch",
            message="Metals monitoring review dossier requires matching jurisdictions.",
            suggestion="Use a signoff packet and interpretation bundle produced for the same jurisdiction filter.",
        )
    if signoff_packet.authority != interpretation_bundle.authority:
        raise DietaryValidationError(
            code="metals_monitoring_review_dossier_authority_mismatch",
            message="Metals monitoring review dossier requires matching authorities.",
            suggestion="Use a signoff packet and interpretation bundle produced for the same authority filter.",
        )
    if (
        signoff_packet.overall_signoff_status != InteroperabilitySignoffStatus.OPEN
        and not interpretation_bundle.occurrence_records
    ):
        raise DietaryValidationError(
            code="metals_monitoring_review_dossier_missing_occurrence_context",
            message="Signed or waived metals monitoring dossiers require governed occurrence context.",
            suggestion="Resolve occurrence context before exporting a closed metals monitoring dossier.",
        )
    if (
        signoff_packet.overall_signoff_status != InteroperabilitySignoffStatus.OPEN
        and signoff_packet.unresolved_blocking_action_ids
    ):
        raise DietaryValidationError(
            code="metals_monitoring_review_dossier_unresolved_blocking_actions",
            message="Closed metals monitoring dossiers cannot retain unresolved blocking signoff actions.",
            suggestion="Resolve or explicitly reopen the blocking actions before exporting the dossier.",
        )

    from dietary_mcp.release_artifacts import build_release_reports

    defaults = DefaultsRegistry(repo_root)
    metadata_report = build_release_reports(
        repo_root,
        skip_validation=False,
        skip_examples=True,
    )["metadata-report"]
    source_catalog_manifest = defaults.source_catalog_manifest()
    reference_values_manifest = defaults.reference_values_manifest()
    contaminant_legal_limits_manifest = defaults.contaminant_legal_limits_manifest()
    consumption_datasets_manifest = defaults.consumption_datasets_manifest()
    method_registry_manifest = defaults.method_registry_manifest()
    legal_authorities_manifest = defaults.legal_authorities_manifest()
    metals_occurrence_manifest = defaults.metals_occurrence_manifest()
    metals_review_focus_manifest = defaults.metals_review_focus_manifest()
    emerging_contaminants_manifest = defaults.emerging_contaminants_manifest()
    jurisdiction_coverage_manifest = defaults.jurisdiction_coverage_manifest()
    contaminant_legal_limit_family_payload = {
        "familyId": interpretation_bundle.contaminant_family.value,
        "records": defaults.get_contaminant_legal_limit_records(
            contaminant_family=interpretation_bundle.contaminant_family.value
        ),
    }
    contaminant_legal_limit_jurisdiction_payload = (
        {
            "jurisdiction": interpretation_bundle.jurisdiction,
            "records": defaults.get_contaminant_legal_limit_records(
                jurisdiction=interpretation_bundle.jurisdiction
            ),
        }
        if interpretation_bundle.jurisdiction
        else None
    )
    jurisdiction_coverage_jurisdiction_payload = (
        {
            "jurisdiction": interpretation_bundle.jurisdiction,
            "records": defaults.get_jurisdiction_coverage_records(
                jurisdiction=interpretation_bundle.jurisdiction
            ),
        }
        if interpretation_bundle.jurisdiction
        else None
    )
    occurrence_family_payload, review_focus_family_payload = _build_family_payload(
        defaults,
        interpretation_bundle.contaminant_family.value,
    )
    emerging_contaminant_snapshot = EmergingContaminantRecord.model_validate(
        defaults.get_emerging_contaminant_record(interpretation_bundle.contaminant_family.value)
    )
    interpretation_doc = read_doc(repo_root, "metals-monitoring-interpretation")
    signoff_doc = read_doc(repo_root, "metals-monitoring-signoff")

    source_governance_snapshot = collect_source_governance_snapshot(
        defaults,
        interpretation_bundle.covered_source_ids + emerging_contaminant_snapshot.source_ids,
    )

    pinned_resources = [
        PinnedResourceFingerprint(
            role="release_metadata_report",
            uri="release://metadata-report",
            sha256=_sha256_json(metadata_report),
            description="Release metadata report used to pin versioned artifact hashes for this metals monitoring review dossier.",
            confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
            sanitisation_state=SanitisationState.RETAINED,
        ),
        PinnedResourceFingerprint(
            role="source_catalog_manifest",
            uri="source-catalog://manifest",
            sha256=_sha256_json(source_catalog_manifest),
            description="Manifest fingerprint for the governed source catalog available during metals monitoring review.",
        ),
        PinnedResourceFingerprint(
            role="reference_values_manifest",
            uri="reference-values://manifest",
            sha256=_sha256_json(reference_values_manifest),
            description="Manifest fingerprint for governed reference-value records available during metals monitoring review.",
        ),
        PinnedResourceFingerprint(
            role="contaminant_legal_limits_manifest",
            uri="contaminant-legal-limits://manifest",
            sha256=_sha256_json(contaminant_legal_limits_manifest),
            description="Manifest fingerprint for governed contaminant legal-limit records available during metals monitoring review.",
        ),
        PinnedResourceFingerprint(
            role="contaminant_legal_limits_family",
            uri=f"contaminant-legal-limits://family/{interpretation_bundle.contaminant_family.value}",
            sha256=_sha256_json(contaminant_legal_limit_family_payload),
            description="Family-scoped contaminant legal-limit payload fingerprint used to keep support depth explicit during metals monitoring review.",
        ),
        PinnedResourceFingerprint(
            role="consumption_datasets_manifest",
            uri="consumption-datasets://manifest",
            sha256=_sha256_json(consumption_datasets_manifest),
            description="Manifest fingerprint for governed consumption-dataset records available during metals monitoring review.",
        ),
        PinnedResourceFingerprint(
            role="method_registry_manifest",
            uri="method-registry://manifest",
            sha256=_sha256_json(method_registry_manifest),
            description="Manifest fingerprint for governed method-registry records available during metals monitoring review.",
        ),
        PinnedResourceFingerprint(
            role="legal_authorities_manifest",
            uri="legal-authorities://manifest",
            sha256=_sha256_json(legal_authorities_manifest),
            description="Manifest fingerprint for governed legal-authority records available during metals monitoring review.",
        ),
        PinnedResourceFingerprint(
            role="jurisdiction_coverage_manifest",
            uri="jurisdiction-coverage://manifest",
            sha256=_sha256_json(jurisdiction_coverage_manifest),
            description="Manifest fingerprint for machine-readable jurisdiction coverage posture available during metals monitoring review.",
        ),
        PinnedResourceFingerprint(
            role="metals_occurrence_manifest",
            uri="metals-occurrence://manifest",
            sha256=_sha256_json(metals_occurrence_manifest),
            description="Manifest fingerprint for governed metals-occurrence records available during metals monitoring review.",
        ),
        PinnedResourceFingerprint(
            role="metals_occurrence_family",
            uri=f"metals-occurrence://family/{interpretation_bundle.contaminant_family.value}",
            sha256=_sha256_json(occurrence_family_payload),
            description="Exact governed metals-occurrence family payload fingerprint used during review.",
        ),
        PinnedResourceFingerprint(
            role="metals_review_focus_manifest",
            uri="metals-review-focus://manifest",
            sha256=_sha256_json(metals_review_focus_manifest),
            description="Manifest fingerprint for governed metals review-focus records available during metals monitoring review.",
        ),
        PinnedResourceFingerprint(
            role="metals_review_focus_family",
            uri=f"metals-review-focus://family/{interpretation_bundle.contaminant_family.value}",
            sha256=_sha256_json(review_focus_family_payload),
            description="Exact governed metals review-focus family payload fingerprint used during review.",
        ),
        PinnedResourceFingerprint(
            role="emerging_contaminants_manifest",
            uri="emerging-contaminants://manifest",
            sha256=_sha256_json(emerging_contaminants_manifest),
            description="Manifest fingerprint for governed emerging-contaminant family records available during review.",
        ),
        PinnedResourceFingerprint(
            role="emerging_contaminant_family",
            uri=f"emerging-contaminants://family/{interpretation_bundle.contaminant_family.value}",
            sha256=_sha256_json(emerging_contaminant_snapshot.model_dump(mode="json", by_alias=True)),
            description="Exact governed emerging-contaminant family record fingerprint used during review.",
        ),
        PinnedResourceFingerprint(
            role="interpretation_documentation",
            uri="docs://metals-monitoring-interpretation",
            sha256=_sha256_text(interpretation_doc),
            description="Operator documentation fingerprint for the metals monitoring interpretation bundle workflow.",
        ),
        PinnedResourceFingerprint(
            role="signoff_documentation",
            uri="docs://metals-monitoring-signoff",
            sha256=_sha256_text(signoff_doc),
            description="Operator documentation fingerprint for the metals monitoring signoff packet workflow.",
        ),
    ]
    if contaminant_legal_limit_jurisdiction_payload is not None:
        pinned_resources.append(
            PinnedResourceFingerprint(
                role="contaminant_legal_limits_jurisdiction",
                uri=f"contaminant-legal-limits://jurisdiction/{interpretation_bundle.jurisdiction}",
                sha256=_sha256_json(contaminant_legal_limit_jurisdiction_payload),
                description="Jurisdiction-scoped contaminant legal-limit payload fingerprint used to keep support depth explicit during metals monitoring review.",
            )
        )
    if jurisdiction_coverage_jurisdiction_payload is not None:
        pinned_resources.append(
            PinnedResourceFingerprint(
                role="jurisdiction_coverage_jurisdiction",
                uri=f"jurisdiction-coverage://jurisdiction/{interpretation_bundle.jurisdiction}",
                sha256=_sha256_json(jurisdiction_coverage_jurisdiction_payload),
                description="Jurisdiction-scoped coverage posture fingerprint used to avoid overreading partial or missing legal-limit support.",
            )
        )
    escalation_items = _build_escalation_items(signoff_packet)
    escalation_required = bool(escalation_items)
    notes = [
        "Version-pinned dossier captures the exact release metadata hashes and governed metals manifests used during metals monitoring review.",
        "Escalation items are derived only from explicit waivers and unresolved blocking actions recorded in the signoff packet.",
        "This dossier captures a governed review state and escalation posture only; it does not certify scientific correctness, submission readiness, or a submission-capable metals decision package.",
    ]
    if interpretation_bundle.legal_limit_reviews:
        notes.append(
            "Family- and jurisdiction-scoped contaminant legal-limit payloads are pinned so partial or missing legal-limit support remains explicit in downstream metals review."
        )
    if escalation_required:
        notes.append(
            "At least one reviewer waiver or unresolved blocking action remains visible in the dossier escalation overlay."
        )

    return VersionPinnedMetalsMonitoringReviewDossier(
        bundle_profile=interpretation_bundle.bundle_profile,
        dossier_status=signoff_packet.overall_signoff_status,
        interpretation_bundle=interpretation_bundle,
        signoff_packet=signoff_packet,
        release_metadata=ReleaseMetadataSnapshot(
            resource_uri="release://metadata-report",
            release_version=metadata_report["version"],
            defaults_version=metadata_report["defaultsVersion"],
            metadata_report_sha256=_sha256_json(metadata_report),
            artifact_hashes=metadata_report["artifactHashes"],
        ),
        source_governance_snapshot=source_governance_snapshot,
        emerging_contaminant_snapshot=emerging_contaminant_snapshot,
        pinned_resources=pinned_resources,
        escalation_required=escalation_required,
        escalation_items=escalation_items,
        confidentiality_annotations=[
            ConfidentialityAnnotation(
                target_path="release_metadata",
                target_kind="field",
                confidentiality_tag=ConfidentialityTag.PUBLIC,
                rationale="Release metadata snapshot is retained in metals monitoring dossiers as provenance for retained fingerprints.",
            ),
            ConfidentialityAnnotation(
                target_path="pinned_resources.release_metadata_report",
                target_kind="resource",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                rationale="The full release metadata report reference is treated as internal review material for the metals monitoring dossier.",
            ),
        ],
        sanitisation_records=[
            SanitisationRecord(
                target_path="pinned_resources.release_metadata_report",
                target_kind="resource",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                sanitisation_state=SanitisationState.RETAINED,
                note="Confidential release metadata pin is retained on the internal-review metals dossier.",
            )
        ],
        limitations=[
            LimitationNote(
                code="version_pinned_not_signed",
                message="This dossier is version-pinned through release and resource fingerprints but is not cryptographically signed in v0.1.",
            ),
            LimitationNote(
                code="review_only_metals_dossier",
                message="This dossier records metals monitoring review and escalation posture only and does not represent a native exposure engine or final regulatory decision package.",
            ),
            *[
                limitation
                for limitation in interpretation_bundle.limitations
                if limitation.code.startswith("legal_limit_scope.")
            ],
        ],
        notes=notes,
    )
