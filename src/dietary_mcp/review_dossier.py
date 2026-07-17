from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dietary_mcp.adapter_walkthroughs import build_adapter_walkthrough, build_adapter_walkthrough_manifest
from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.models import (
    BundleProfile,
    ConfidentialityAnnotation,
    ConfidentialityTag,
    ExportVersionPinnedAdapterReviewDossierRequest,
    LimitationNote,
    PinnedResourceFingerprint,
    ReleaseMetadataSnapshot,
    SanitisationState,
    VersionPinnedAdapterReviewDossier,
)
from dietary_mcp.readiness import collect_source_governance_snapshot, get_model_governance_snapshot
from dietary_mcp.template_assets import read_adapter_template, read_adapter_template_manifest


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_json(payload: dict) -> str:
    return _sha256_text(json.dumps(payload, sort_keys=True))


def export_version_pinned_adapter_review_dossier(
    repo_root: Path,
    request: ExportVersionPinnedAdapterReviewDossierRequest,
) -> VersionPinnedAdapterReviewDossier:
    review_bundle = request.review_bundle
    if not review_bundle.walkthrough_name:
        raise DietaryValidationError(
            code="review_dossier_missing_walkthrough",
            message="Version-pinned review dossiers require a named walkthrough baseline.",
            suggestion="Build the review bundle from a walkthrough comparison result before exporting a dossier.",
        )

    from dietary_mcp.release_artifacts import build_release_reports

    defaults = DefaultsRegistry(repo_root)
    metadata_report = build_release_reports(
        repo_root,
        skip_validation=False,
        skip_examples=True,
    )["metadata-report"]
    template_manifest = read_adapter_template_manifest(repo_root)
    template_text = read_adapter_template(repo_root, review_bundle.template_name)
    walkthrough_manifest = build_adapter_walkthrough_manifest(repo_root)
    walkthrough_payload = build_adapter_walkthrough(repo_root, review_bundle.walkthrough_name)
    source_catalog_manifest = defaults.source_catalog_manifest()
    model_governance_manifest = defaults.model_governance_manifest()
    model_governance_snapshot = get_model_governance_snapshot(defaults, review_bundle.model_family)
    source_governance_snapshot = collect_source_governance_snapshot(
        defaults,
        review_bundle.check_result.normalized_projection.source_ids + model_governance_snapshot.source_ids,
    )

    pinned_resources = [
        PinnedResourceFingerprint(
            role="release_metadata_report",
            uri="release://metadata-report",
            sha256=_sha256_json(metadata_report),
            description="Release metadata report used to pin versioned artifact hashes for this review dossier.",
            confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
            sanitisation_state=SanitisationState.RETAINED,
        ),
        PinnedResourceFingerprint(
            role="template_manifest",
            uri="adapter-input-templates://manifest",
            sha256=_sha256_json(template_manifest),
            description="Manifest fingerprint for the published adapter input templates available during review.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        PinnedResourceFingerprint(
            role="template_payload",
            uri=f"adapter-template://{review_bundle.template_name}",
            sha256=_sha256_text(template_text),
            description="Exact adapter template content fingerprint used for the reviewed import format.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        PinnedResourceFingerprint(
            role="walkthrough_manifest",
            uri="adapter-import-walkthroughs://manifest",
            sha256=_sha256_json(walkthrough_manifest),
            description="Manifest fingerprint for the governed adapter walkthroughs available during review.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        PinnedResourceFingerprint(
            role="walkthrough_payload",
            uri=f"adapter-walkthrough://{review_bundle.walkthrough_name}",
            sha256=_sha256_json(walkthrough_payload),
            description="Exact governed walkthrough payload fingerprint used as the review baseline.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        PinnedResourceFingerprint(
            role="source_catalog_manifest",
            uri="source-catalog://manifest",
            sha256=_sha256_json(source_catalog_manifest),
            description="Manifest fingerprint for the governed regulatory source catalog available during review.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        PinnedResourceFingerprint(
            role="model_governance_manifest",
            uri="model-governance://manifest",
            sha256=_sha256_json(model_governance_manifest),
            description="Manifest fingerprint for the governed model-governance records available during review.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
    ]
    notes = [
        "Version-pinned dossier captures the exact release metadata hashes and reviewed template and walkthrough fingerprints used during adapter review.",
        "Pinned resource hashes are computed from canonical JSON for manifests and walkthrough payloads, and from raw text for CSV template content.",
        "Use this dossier when downstream reviewers need a portable record of the exact Dietary MCP artifacts that informed a review decision.",
        "This dossier supports internal review or consultation-oriented exploration only and is not a submission-capable regulatory package in v0.1.",
    ]
    for disclaimer in model_governance_snapshot.required_disclaimers:
        if disclaimer not in notes:
            notes.append(disclaimer)

    return VersionPinnedAdapterReviewDossier(
        bundle_profile=BundleProfile.INTERNAL_REVIEW,
        dossier_status=review_bundle.review_status,
        review_bundle=review_bundle,
        release_metadata=ReleaseMetadataSnapshot(
            resource_uri="release://metadata-report",
            release_version=metadata_report["version"],
            defaults_version=metadata_report["defaultsVersion"],
            metadata_report_sha256=_sha256_json(metadata_report),
            artifact_hashes=metadata_report["artifactHashes"],
        ),
        source_governance_snapshot=source_governance_snapshot,
        model_governance_snapshot=model_governance_snapshot,
        pinned_resources=pinned_resources,
        confidentiality_annotations=review_bundle.confidentiality_annotations
        + [
            ConfidentialityAnnotation(
                target_path="release_metadata",
                target_kind="field",
                confidentiality_tag=ConfidentialityTag.PUBLIC,
                rationale="Release metadata snapshot is retained in public dossiers as provenance for retained fingerprints.",
            ),
            ConfidentialityAnnotation(
                target_path="pinned_resources.release_metadata_report",
                target_kind="resource",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                rationale="The full release metadata report reference is treated as internal review material and removed from public dossiers.",
            ),
        ],
        limitations=[
            LimitationNote(
                code="version_pinned_not_signed",
                message="This dossier is version-pinned through release and resource fingerprints but is not cryptographically signed in v0.1.",
            )
        ],
        notes=notes,
    )
