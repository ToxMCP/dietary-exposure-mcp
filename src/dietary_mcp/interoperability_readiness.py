from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.errors import DietaryRegistryError
from dietary_mcp.models import (
    AssessInteroperabilityPreviewReadinessRequest,
    AssessReviewDossierReadinessRequest,
    InteroperabilityPreviewReadinessAssessment,
    InteroperabilityReadinessProfile,
    InteroperabilityRuleResult,
    InteroperabilitySupportLevel,
    ReadinessStatus,
)
from dietary_mcp.readiness import assess_review_dossier_readiness


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def read_interoperability_rules(repo_root: Path) -> dict:
    return json.loads((_validation_root(repo_root) / "interoperability_rules.json").read_text())


def read_interoperability_readiness_profiles(repo_root: Path) -> dict:
    return json.loads((_validation_root(repo_root) / "interoperability_readiness_profiles.json").read_text())


def get_interoperability_readiness_profile_record(repo_root: Path, profile_id: str) -> dict:
    payload = read_interoperability_readiness_profiles(repo_root)
    for item in payload["profiles"]:
        if item["profileId"] == profile_id:
            return item
    raise DietaryRegistryError(
        code="unknown_interoperability_readiness_profile",
        message=f"Unknown interoperability readiness profile: {profile_id}",
        suggestion="Use a profile listed in interoperability-readiness://manifest.",
    )


def _build_rule_result(
    rule_id: str,
    profile_id: str,
    status: ReadinessStatus,
    message: str,
    *,
    blocking: bool = False,
    note: str | None = None,
) -> InteroperabilityRuleResult:
    return InteroperabilityRuleResult(
        rule_id=rule_id,
        profile_id=profile_id,
        status=status,
        message=message,
        blocking=blocking,
        note=note,
    )


def assess_interoperability_preview_readiness(
    defaults_registry: DefaultsRegistry,
    repo_root: Path,
    request: AssessInteroperabilityPreviewReadinessRequest,
) -> InteroperabilityPreviewReadinessAssessment:
    profile = InteroperabilityReadinessProfile.model_validate(
        get_interoperability_readiness_profile_record(repo_root, request.target_profile)
    )
    rules_manifest = read_interoperability_rules(repo_root)
    published_rule_ids = {item["ruleId"] for item in rules_manifest["rules"]}

    preview = request.preview
    dossier = request.dossier
    unsupported_field_paths = sorted(item.local_path for item in preview.unsupported_fields)
    derived_mapping_paths = sorted(
        item.local_path for item in preview.mapped_fields if item.support_level == InteroperabilitySupportLevel.DERIVED
    )
    review_required_mapping_paths = sorted(
        item.local_path
        for item in preview.mapped_fields
        if item.support_level == InteroperabilitySupportLevel.REVIEW_REQUIRED
    )
    direct_mapping_count = sum(
        1 for item in preview.mapped_fields if item.support_level == InteroperabilitySupportLevel.DIRECT
    )
    derived_mapping_count = len(derived_mapping_paths)
    review_required_mapping_count = len(review_required_mapping_paths)

    linked_dossier_readiness = assess_review_dossier_readiness(
        defaults_registry,
        repo_root,
        AssessReviewDossierReadinessRequest(
            dossier=dossier,
            target_profile=profile.required_dossier_readiness_profile,
        ),
    )

    applied_rules: list[InteroperabilityRuleResult] = []

    def add_rule(
        rule_id: str,
        status: ReadinessStatus,
        message: str,
        *,
        blocking: bool = False,
        note: str | None = None,
    ) -> None:
        if rule_id not in published_rule_ids:
            raise ValueError(f"Unpublished interoperability rule referenced by implementation: {rule_id}")
        applied_rules.append(
            _build_rule_result(
                rule_id,
                profile.profile_id,
                status,
                message,
                blocking=blocking,
                note=note,
            )
        )

    if preview.target_profile.profile_id in profile.allowed_preview_profiles:
        add_rule(
            "preview_profile_allowed",
            ReadinessStatus.PASS,
            "Preview profile is allowed for the selected interoperability readiness profile.",
        )
    else:
        add_rule(
            "preview_profile_allowed",
            ReadinessStatus.FAIL,
            "Preview profile is not allowed for the selected interoperability readiness profile.",
            blocking=True,
            note=preview.target_profile.profile_id,
        )

    if preview.source_dossier_id == dossier.dossier_id:
        add_rule(
            "source_dossier_consistent",
            ReadinessStatus.PASS,
            "Preview source dossier matches the supplied version-pinned dossier.",
        )
    else:
        add_rule(
            "source_dossier_consistent",
            ReadinessStatus.FAIL,
            "Preview source dossier does not match the supplied version-pinned dossier.",
            blocking=True,
            note=f"preview={preview.source_dossier_id}, dossier={dossier.dossier_id}",
        )

    if not preview.missing_required_fields:
        add_rule(
            "preview_required_fields_complete",
            ReadinessStatus.PASS,
            "Preview contains all required mapped source fields.",
        )
    else:
        add_rule(
            "preview_required_fields_complete",
            ReadinessStatus.FAIL,
            "Preview is missing required source fields and cannot advance to the requested gate.",
            blocking=True,
            note=", ".join(preview.missing_required_fields),
        )

    if preview.target_document:
        add_rule(
            "preview_target_document_present",
            ReadinessStatus.PASS,
            "Preview produced a non-empty staged target document.",
        )
    else:
        add_rule(
            "preview_target_document_present",
            ReadinessStatus.FAIL,
            "Preview target document is empty.",
            blocking=True,
        )

    if linked_dossier_readiness.overall_status == ReadinessStatus.PASS:
        add_rule(
            "linked_dossier_readiness",
            ReadinessStatus.PASS,
            "Linked dossier readiness assessment satisfies the required dossier readiness profile.",
        )
    elif profile.profile_id == "eu_submission_xml_candidate":
        add_rule(
            "linked_dossier_readiness",
            ReadinessStatus.FAIL,
            "Linked dossier readiness assessment does not satisfy the required submission-oriented dossier profile.",
            blocking=True,
            note=linked_dossier_readiness.overall_status.value,
        )
    elif linked_dossier_readiness.overall_status == ReadinessStatus.FAIL:
        add_rule(
            "linked_dossier_readiness",
            ReadinessStatus.FAIL,
            "Linked dossier readiness assessment failed and blocks the requested interoperability gate.",
            blocking=True,
            note=linked_dossier_readiness.target_profile.profile_id,
        )
    else:
        add_rule(
            "linked_dossier_readiness",
            ReadinessStatus.REVIEW_REQUIRED,
            "Linked dossier readiness assessment requires human review before treating the preview as exchange-ready.",
            note=linked_dossier_readiness.target_profile.profile_id,
        )

    unsupported_status = (
        ReadinessStatus.FAIL if profile.profile_id == "eu_submission_xml_candidate" else ReadinessStatus.REVIEW_REQUIRED
    )
    if not unsupported_field_paths:
        add_rule(
            "preview_unsupported_fields_allowed",
            ReadinessStatus.PASS,
            "Preview does not carry unsupported local-only fields for the selected gate.",
        )
    else:
        add_rule(
            "preview_unsupported_fields_allowed",
            unsupported_status,
            "Preview still carries unsupported local-only fields that require review or block the selected gate.",
            blocking=unsupported_status == ReadinessStatus.FAIL,
            note=", ".join(unsupported_field_paths),
        )

    non_direct_status = (
        ReadinessStatus.FAIL if profile.profile_id == "eu_submission_xml_candidate" else ReadinessStatus.REVIEW_REQUIRED
    )
    non_direct_paths = derived_mapping_paths + review_required_mapping_paths
    if not non_direct_paths:
        add_rule(
            "preview_non_direct_mappings_allowed",
            ReadinessStatus.PASS,
            "Preview mappings are fully direct for the selected gate.",
        )
    else:
        add_rule(
            "preview_non_direct_mappings_allowed",
            non_direct_status,
            "Preview still depends on derived or review-required mappings that require review or block the selected gate.",
            blocking=non_direct_status == ReadinessStatus.FAIL,
            note=", ".join(sorted(non_direct_paths)),
        )

    blocking_rules = [item for item in applied_rules if item.status == ReadinessStatus.FAIL or item.blocking]
    warning_rules = [item for item in applied_rules if item.status == ReadinessStatus.REVIEW_REQUIRED]
    if blocking_rules:
        overall_status = ReadinessStatus.FAIL
    elif warning_rules:
        overall_status = ReadinessStatus.REVIEW_REQUIRED
    else:
        overall_status = ReadinessStatus.PASS

    notes = [
        "Interoperability readiness uses a fixed ruleset layered on top of the staged OHT/IUCLID-aligned JSON preview.",
        "This assessment does not imply XML conformance, dossier completeness, or final regulatory acceptance.",
        f"Linked dossier readiness profile: {profile.required_dossier_readiness_profile}.",
    ]
    notes.extend(profile.notes)

    return InteroperabilityPreviewReadinessAssessment(
        overall_status=overall_status,
        target_profile=profile,
        source_preview_profile_id=preview.target_profile.profile_id,
        linked_dossier_readiness_profile=profile.required_dossier_readiness_profile,
        linked_dossier_readiness_status=linked_dossier_readiness.overall_status,
        applied_rules=applied_rules,
        blocking_rules=blocking_rules,
        warning_rules=warning_rules,
        missing_required_fields=preview.missing_required_fields,
        unsupported_field_paths=unsupported_field_paths,
        derived_mapping_paths=derived_mapping_paths,
        review_required_mapping_paths=review_required_mapping_paths,
        direct_mapping_count=direct_mapping_count,
        derived_mapping_count=derived_mapping_count,
        review_required_mapping_count=review_required_mapping_count,
        notes=notes,
    )
