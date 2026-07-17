from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.guidance import read_doc
from dietary_mcp.models import (
    BundleProfile,
    ConfidentialityAnnotation,
    ConfidentialityTag,
    DependencyDescriptor,
    ExportTradeRiskReviewBundleRequest,
    ExportVersionPinnedTradeRiskReviewDossierRequest,
    LimitationNote,
    PinnedResourceFingerprint,
    ReferenceValueJurisdictionStatus,
    RegulatorySourceRecord,
    ReleaseMetadataSnapshot,
    ReviewResourceReference,
    SanitisationState,
    TradeMrlCoverageStatus,
    TradeRiskReviewBundle,
    TradeRiskReviewPrompt,
    VersionPinnedTradeRiskReviewDossier,
)
from dietary_mcp.package_metadata import VERSION
from dietary_mcp.readiness import collect_source_governance_snapshot


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_json(payload: dict) -> str:
    return _sha256_text(json.dumps(payload, sort_keys=True))


def _trade_review_status(report) -> str:
    profiles = report.jurisdiction_profiles
    if not profiles:
        return "review_required"
    screening_clear = all(
        profile.trade_status == "pass"
        and profile.mrl_coverage_status == TradeMrlCoverageStatus.ALL_REQUESTED_PAIRS_EXACTLY_CURATED
        and profile.reference_value_jurisdiction_status
        == ReferenceValueJurisdictionStatus.EXACT_JURISDICTION_VALUE_PRESENT
        for profile in profiles
    )
    return "screening_clear" if screening_clear else "review_required"


def _collect_trade_source_ids(defaults: DefaultsRegistry, report) -> list[str]:
    source_ids: set[str] = set()
    for profile in report.jurisdiction_profiles:
        for record in profile.applicable_reference_values:
            source_ids.update(record.source_ids)
        for summary in profile.coverage_summaries:
            source_ids.update(summary.official_source_ids)
            for authority_id in summary.legal_authority_ids:
                source_ids.add(defaults.get_legal_authority_record(authority_id)["sourceId"])
            for record_id in summary.reference_value_record_ids:
                source_ids.update(defaults.get_reference_value_record(record_id).get("sourceIds", []))
            for record_id in summary.enforcement_record_ids:
                source_ids.update(defaults.get_mrl_enforcement_record(record_id).get("sourceIds", []))
    return sorted(source_ids)


def _build_trade_review_prompts(report) -> list[TradeRiskReviewPrompt]:
    prompts: list[TradeRiskReviewPrompt] = []
    for profile in report.jurisdiction_profiles:
        jurisdiction = profile.jurisdiction
        jurisdiction_label = jurisdiction.upper()
        if profile.trade_status == "invalid_request":
            prompts.append(
                TradeRiskReviewPrompt(
                    prompt_id=f"{jurisdiction}.identity_resolution",
                    jurisdiction=jurisdiction,
                    category="identity_resolution",
                    prompt=(
                        f"Resolve governed substance identity before using the {jurisdiction_label} trade-screening lane."
                    ),
                )
            )
            continue
        if profile.trade_status == "fail":
            prompts.append(
                TradeRiskReviewPrompt(
                    prompt_id=f"{jurisdiction}.mrl_exceedance_review",
                    jurisdiction=jurisdiction,
                    category="mrl_exceedance",
                    prompt=(
                        f"Review the {jurisdiction_label} MRL exceedance findings and do not treat this lane as commercially clear."
                    ),
                )
            )
        elif profile.trade_status == "inconclusive_no_limit":
            prompts.append(
                TradeRiskReviewPrompt(
                    prompt_id=f"{jurisdiction}.coverage_review",
                    jurisdiction=jurisdiction,
                    category="coverage_review",
                    prompt=(
                        f"Treat the {jurisdiction_label} lane as review-required until the missing or partial MRL coverage is explicitly accepted."
                    ),
                )
            )
        else:
            prompts.append(
                TradeRiskReviewPrompt(
                    prompt_id=f"{jurisdiction}.clearance_scope_check",
                    jurisdiction=jurisdiction,
                    category="scope_check",
                    prompt=(
                        f"Confirm that the {jurisdiction_label} pass status is interpreted only within the exact shipped MRL and reference-value scope."
                    ),
                )
            )

        if profile.mrl_coverage_status != TradeMrlCoverageStatus.ALL_REQUESTED_PAIRS_EXACTLY_CURATED:
            prompts.append(
                TradeRiskReviewPrompt(
                    prompt_id=f"{jurisdiction}.mrl_coverage_semantics",
                    jurisdiction=jurisdiction,
                    category="mrl_coverage_semantics",
                    prompt=(
                        f"Use `mrlCoverageStatus` for {jurisdiction_label} to distinguish partial curated scope, anchor-only posture, and explicit gaps instead of flattening them into a generic missing-limit state."
                    ),
                )
            )
        if (
            profile.reference_value_jurisdiction_status
            != ReferenceValueJurisdictionStatus.EXACT_JURISDICTION_VALUE_PRESENT
        ):
            prompts.append(
                TradeRiskReviewPrompt(
                    prompt_id=f"{jurisdiction}.reference_value_semantics",
                    jurisdiction=jurisdiction,
                    category="reference_value_semantics",
                    prompt=(
                        f"Use `referenceValueJurisdictionStatus` for {jurisdiction_label} to confirm whether the reference-value side is exact, anchor-only, family-curated-without-value, or an explicit gap."
                    ),
                )
            )
    return prompts


def export_trade_risk_review_bundle(
    defaults: DefaultsRegistry,
    request: ExportTradeRiskReviewBundleRequest,
) -> TradeRiskReviewBundle:
    report = request.trade_report
    covered_source_ids = _collect_trade_source_ids(defaults, report)
    review_status = _trade_review_status(report)
    resolved_substance_key = report.resolved_substance_key

    referenced_resources = [
        ReviewResourceReference(
            role="documentation",
            uri="docs://trade-risk-review",
            description="Operator documentation describing the trade-risk review bundle and dossier workflow.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="operator_guide",
            uri="docs://operator-guide",
            description="Operator guide covering trade-risk coverage semantics and no-borrowing posture.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="source_catalog_manifest",
            uri="source-catalog://manifest",
            description="Governed source-catalog manifest available during trade screening review.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="reference_values_manifest",
            uri="reference-values://manifest",
            description="Governed reference-values manifest available during trade screening review.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="mrl_enforcement_manifest",
            uri="mrl-enforcement://manifest",
            description="Governed MRL-enforcement manifest available during trade screening review.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="legal_authorities_manifest",
            uri="legal-authorities://manifest",
            description="Governed legal-authorities manifest available during trade screening review.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="jurisdiction_coverage_manifest",
            uri="jurisdiction-coverage://manifest",
            description="Governed jurisdiction-coverage manifest used to interpret exact, partial, anchor-only, and explicit-gap lanes.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
    ]
    seen_jurisdictions: set[str] = set()
    for profile in report.jurisdiction_profiles:
        if profile.jurisdiction in seen_jurisdictions:
            continue
        seen_jurisdictions.add(profile.jurisdiction)
        referenced_resources.append(
            ReviewResourceReference(
                role=f"{profile.jurisdiction}_coverage",
                uri=f"jurisdiction-coverage://jurisdiction/{profile.jurisdiction}",
                description=f"Jurisdiction-coverage records for {profile.jurisdiction.upper()} used during trade screening review.",
                confidentiality_tag=ConfidentialityTag.PUBLIC,
            )
        )
    if resolved_substance_key:
        referenced_resources.extend(
            [
                ReviewResourceReference(
                    role="reference_value_substance_lane",
                    uri=f"reference-values://substance/{resolved_substance_key}",
                    description="Substance-scoped reference-value records reviewed alongside the trade-screening result.",
                    confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                ),
                ReviewResourceReference(
                    role="mrl_enforcement_substance_lane",
                    uri=f"mrl-enforcement://substance/{resolved_substance_key}",
                    description="Substance-scoped MRL-enforcement records reviewed alongside the trade-screening result.",
                    confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                ),
            ]
        )

    notes = [
        "Bundle packages a governed trade-risk screening result with explicit coverage semantics, review prompts, and pinned review resources.",
        "No-borrowing semantics are preserved: missing jurisdiction coverage remains explicit and is not silently substituted from another authority.",
        "Use this bundle for internal trade-screening review and audit handoff, not as a market-clearance or regulator-acceptance packet.",
    ]
    notes.extend(report.notes)
    if review_status == "review_required":
        notes.append(
            "Review-required status means at least one jurisdiction remains failed, invalid, inconclusive, or coverage-limited under the shipped MRL/reference-value scope."
        )
    if request.bundle_note:
        notes.append(request.bundle_note)

    return TradeRiskReviewBundle(
        bundle_profile=BundleProfile.INTERNAL_REVIEW,
        review_status=review_status,
        trade_report=report,
        covered_source_ids=covered_source_ids,
        review_prompts=_build_trade_review_prompts(report),
        referenced_resources=referenced_resources,
        dependencies=[
            DependencyDescriptor(name="dietary-mcp", version=VERSION, role="producer"),
            DependencyDescriptor(name="dietary_evaluate_global_trade_risk", version=VERSION, role="screening_workflow"),
            DependencyDescriptor(
                name="dietary_export_trade_risk_review_bundle",
                version=VERSION,
                role="review_bundle_workflow",
            ),
        ],
        limitations=[
            LimitationNote(
                code="screening_review_bundle",
                message=(
                    "Trade-risk review bundle supports governed screening review and audit handoff only; it is not a final market-clearance or regulatory acceptance decision."
                ),
            )
        ],
        notes=notes,
    )


def export_version_pinned_trade_risk_review_dossier(
    repo_root: Path,
    request: ExportVersionPinnedTradeRiskReviewDossierRequest,
) -> VersionPinnedTradeRiskReviewDossier:
    review_bundle = request.review_bundle

    from dietary_mcp.release_artifacts import build_release_reports

    defaults = DefaultsRegistry(repo_root)
    metadata_report = build_release_reports(
        repo_root,
        skip_validation=False,
        skip_examples=True,
    )["metadata-report"]
    source_catalog_manifest = defaults.source_catalog_manifest()
    reference_values_manifest = defaults.reference_values_manifest()
    mrl_enforcement_manifest = defaults.mrl_enforcement_manifest()
    legal_authorities_manifest = defaults.legal_authorities_manifest()
    jurisdiction_coverage_manifest = defaults.jurisdiction_coverage_manifest()
    trade_risk_doc = read_doc(repo_root, "trade-risk-review")
    operator_guide_doc = read_doc(repo_root, "operator-guide")

    source_governance_snapshot: list[RegulatorySourceRecord] = collect_source_governance_snapshot(
        defaults,
        review_bundle.covered_source_ids,
    )

    pinned_resources = [
        PinnedResourceFingerprint(
            role="release_metadata_report",
            uri="release://metadata-report",
            sha256=_sha256_json(metadata_report),
            description="Release metadata report used to pin versioned artifact hashes for this trade-risk review dossier.",
            confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
            sanitisation_state=SanitisationState.RETAINED,
        ),
        PinnedResourceFingerprint(
            role="source_catalog_manifest",
            uri="source-catalog://manifest",
            sha256=_sha256_json(source_catalog_manifest),
            description="Manifest fingerprint for the governed source catalog available during trade-risk review.",
        ),
        PinnedResourceFingerprint(
            role="reference_values_manifest",
            uri="reference-values://manifest",
            sha256=_sha256_json(reference_values_manifest),
            description="Manifest fingerprint for governed reference-value records available during trade-risk review.",
        ),
        PinnedResourceFingerprint(
            role="mrl_enforcement_manifest",
            uri="mrl-enforcement://manifest",
            sha256=_sha256_json(mrl_enforcement_manifest),
            description="Manifest fingerprint for governed MRL-enforcement records available during trade-risk review.",
        ),
        PinnedResourceFingerprint(
            role="legal_authorities_manifest",
            uri="legal-authorities://manifest",
            sha256=_sha256_json(legal_authorities_manifest),
            description="Manifest fingerprint for governed legal-authority records available during trade-risk review.",
        ),
        PinnedResourceFingerprint(
            role="jurisdiction_coverage_manifest",
            uri="jurisdiction-coverage://manifest",
            sha256=_sha256_json(jurisdiction_coverage_manifest),
            description="Manifest fingerprint for governed jurisdiction-coverage records available during trade-risk review.",
        ),
        PinnedResourceFingerprint(
            role="trade_risk_review_documentation",
            uri="docs://trade-risk-review",
            sha256=_sha256_text(trade_risk_doc),
            description="Trade-risk review workflow documentation used during dossier export.",
        ),
        PinnedResourceFingerprint(
            role="operator_guide_documentation",
            uri="docs://operator-guide",
            sha256=_sha256_text(operator_guide_doc),
            description="Operator guide documentation used to interpret trade-risk coverage semantics during dossier export.",
        ),
    ]

    resolved_substance_key = review_bundle.trade_report.resolved_substance_key
    if resolved_substance_key:
        reference_value_payload = {
            "substanceKey": resolved_substance_key,
            "records": [
                item
                for item in defaults.list_reference_value_records()
                if item["substanceKey"].strip().lower() == resolved_substance_key.strip().lower()
            ],
        }
        mrl_payload = {
            "substanceKey": resolved_substance_key,
            "records": [
                item
                for item in defaults.list_mrl_enforcement_records()
                if item["substanceKey"].strip().lower() == resolved_substance_key.strip().lower()
            ],
        }
        pinned_resources.extend(
            [
                PinnedResourceFingerprint(
                    role="reference_value_substance_lane",
                    uri=f"reference-values://substance/{resolved_substance_key}",
                    sha256=_sha256_json(reference_value_payload),
                    description="Substance-scoped reference-value payload fingerprint used during trade-risk review.",
                    confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                    sanitisation_state=SanitisationState.RETAINED,
                ),
                PinnedResourceFingerprint(
                    role="mrl_enforcement_substance_lane",
                    uri=f"mrl-enforcement://substance/{resolved_substance_key}",
                    sha256=_sha256_json(mrl_payload),
                    description="Substance-scoped MRL-enforcement payload fingerprint used during trade-risk review.",
                    confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                    sanitisation_state=SanitisationState.RETAINED,
                ),
            ]
        )

    notes = [
        "Version-pinned trade-risk review dossier freezes the exact screening bundle, release metadata hashes, and review documentation fingerprints used during internal screening review.",
        "This dossier preserves explicit no-borrowing semantics and should be used when downstream reviewers need a portable record of why a lane was exact, partial, anchor-only, or an explicit gap.",
        "This dossier supports governed internal review only and is not a final market-clearance, shipment-release, or regulatory acceptance package.",
    ]
    notes.extend(review_bundle.notes)

    return VersionPinnedTradeRiskReviewDossier(
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
        pinned_resources=pinned_resources,
        confidentiality_annotations=[
            ConfidentialityAnnotation(
                target_path="review_bundle.trade_report.chemical_identity",
                target_kind="field",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                rationale="Trade-screening chemical identity can remain non-public during internal review workflows.",
            ),
            ConfidentialityAnnotation(
                target_path="review_bundle.trade_report.resolved_substance_key",
                target_kind="field",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                rationale="Resolved trade-screening substance keys can disclose the internal review substance identity.",
            ),
            ConfidentialityAnnotation(
                target_path="release_metadata",
                target_kind="field",
                confidentiality_tag=ConfidentialityTag.PUBLIC,
                rationale="Release metadata snapshot is retained as provenance for pinned internal-review dossiers.",
            ),
            ConfidentialityAnnotation(
                target_path="pinned_resources.release_metadata_report",
                target_kind="resource",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                rationale="The full release metadata report reference remains internal-review material.",
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
