from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.errors import DietaryRegistryError
from dietary_mcp.models import (
    AssessReviewDossierReadinessRequest,
    ContaminantLegalLimitLookupResult,
    EmergingContaminantRecord,
    GovernanceStatus,
    InteroperabilityActionDecisionStatus,
    MetalsMonitoringEscalationType,
    ModelGovernanceRecord,
    ModelFamily,
    ReadinessStatus,
    RegulatoryReadinessProfile,
    RegulatoryRuleResult,
    RegulatorySourceRecord,
    ReviewDossierReadinessAssessment,
    RequestedLaneStatus,
    ScientificFollowUpItem,
    ScientificFollowUpQueues,
    SubmissionUse,
    VersionPinnedAdapterReviewDossier,
    VersionPinnedContaminantMonitoringReviewDossier,
    VersionPinnedMetalsMonitoringReviewDossier,
)


ADAPTER_REQUIRED_DOSSIER_FINGERPRINT_ROLES = {
    "release_metadata_report",
    "template_manifest",
    "template_payload",
    "walkthrough_manifest",
    "walkthrough_payload",
    "source_catalog_manifest",
    "model_governance_manifest",
}
CONTAMINANT_MONITORING_REQUIRED_DOSSIER_FINGERPRINT_ROLES = {
    "release_metadata_report",
    "source_catalog_manifest",
    "reference_values_manifest",
    "consumption_datasets_manifest",
    "method_registry_manifest",
    "legal_authorities_manifest",
    "occurrence_evidence_manifest",
    "occurrence_evidence_family",
    "analytical_method_evidence_manifest",
    "analytical_method_evidence_family",
    "metals_review_focus_manifest",
    "metals_review_focus_family",
    "emerging_contaminants_manifest",
    "emerging_contaminant_family",
}
METALS_MONITORING_REQUIRED_DOSSIER_FINGERPRINT_ROLES = {
    "release_metadata_report",
    "source_catalog_manifest",
    "reference_values_manifest",
    "consumption_datasets_manifest",
    "method_registry_manifest",
    "legal_authorities_manifest",
    "metals_occurrence_manifest",
    "metals_occurrence_family",
    "metals_review_focus_manifest",
    "metals_review_focus_family",
    "emerging_contaminants_manifest",
    "emerging_contaminant_family",
}


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def read_regulatory_rules(repo_root: Path) -> dict:
    return json.loads((_validation_root(repo_root) / "regulatory_rules.json").read_text())


def get_model_governance_snapshot(
    defaults_registry: DefaultsRegistry,
    model_family: ModelFamily | str,
) -> ModelGovernanceRecord:
    family_value = model_family.value if isinstance(model_family, ModelFamily) else model_family
    return ModelGovernanceRecord.model_validate(defaults_registry.get_model_governance_record(family_value))


def collect_source_governance_snapshot(
    defaults_registry: DefaultsRegistry,
    source_ids: list[str],
) -> list[RegulatorySourceRecord]:
    unique_source_ids = sorted(set(source_ids))
    snapshot = []
    for source_id in unique_source_ids:
        try:
            snapshot.append(
                RegulatorySourceRecord.model_validate(defaults_registry.get_source_catalog_record(source_id))
            )
        except DietaryRegistryError:
            continue
    return snapshot


def _profile_kind(defaults_registry: DefaultsRegistry, profile_id: str) -> str:
    known_profile_ids = {
        item["profileId"] for item in defaults_registry.regulatory_readiness_profiles["profiles"]
    }
    if profile_id not in known_profile_ids:
        raise ValueError(f"Unsupported readiness profile id: {profile_id}")
    if profile_id == "eu_internal_review" or profile_id.endswith("_internal_review"):
        return "internal_review"
    if profile_id == "eu_submission_candidate" or profile_id.endswith("_submission_candidate"):
        return "submission_candidate"
    if profile_id == "eu_consultation_exploratory" or profile_id.endswith("_consultation_exploratory"):
        return "consultation_exploratory"
    raise ValueError(f"Unsupported readiness profile id: {profile_id}")


def _scientific_integrity_status(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
    target_profile_kind: str,
) -> tuple[ReadinessStatus, str, str | None]:
    blockers: list[str] = []

    if isinstance(dossier, VersionPinnedAdapterReviewDossier):
        if dossier.review_bundle.comparison_result.status != "match":
            blockers.append("adapter walkthrough comparison still contains mismatches")
        if dossier.review_bundle.mismatch_field_count > 0:
            blockers.append("adapter review bundle still reports mismatched fields")
    elif isinstance(dossier, VersionPinnedContaminantMonitoringReviewDossier):
        error_quality_flag_codes = [
            item.code
            for item in dossier.interpretation_bundle.check_result.quality_flags
            if item.severity.value == "error"
        ]
        if dossier.interpretation_bundle.check_result.check_status == ReadinessStatus.FAIL:
            blockers.append("contaminant monitoring check result is failed")
        if error_quality_flag_codes:
            blockers.append(f"error-quality flags remain unresolved: {sorted(error_quality_flag_codes)}")
        if not dossier.interpretation_bundle.check_result.occurrence_evidence_records:
            blockers.append("occurrence evidence context is missing")
        if dossier.signoff_packet.unresolved_blocking_action_ids:
            blockers.append(
                "blocking signoff actions remain unresolved: "
                f"{sorted(dossier.signoff_packet.unresolved_blocking_action_ids)}"
            )
    else:
        if not dossier.interpretation_bundle.occurrence_records:
            blockers.append("metals occurrence context is missing")
        if dossier.signoff_packet.unresolved_blocking_action_ids:
            blockers.append(
                "blocking signoff actions remain unresolved: "
                f"{sorted(dossier.signoff_packet.unresolved_blocking_action_ids)}"
            )

    if not blockers:
        return (
            ReadinessStatus.PASS,
            "Scientific-integrity checks do not show unresolved critical scientific blockers.",
            None,
        )

    status = (
        ReadinessStatus.FAIL
        if target_profile_kind == "submission_candidate"
        else ReadinessStatus.REVIEW_REQUIRED
    )
    return (
        status,
        "Scientific-integrity checks found unresolved scientific blockers on the dossier.",
        "; ".join(blockers),
    )


def _jurisdiction_consistency_status(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
    target_profile: RegulatoryReadinessProfile,
    model_governance: ModelGovernanceRecord | None,
    emerging_contaminant: EmergingContaminantRecord | None,
    target_profile_kind: str,
) -> tuple[ReadinessStatus, str, str | None]:
    target_jurisdiction = target_profile.jurisdiction.strip().lower()
    dossier_jurisdictions: set[str] = set()

    if model_governance is not None:
        dossier_jurisdictions.update(item.strip().lower() for item in model_governance.jurisdictions)
    if emerging_contaminant is not None:
        dossier_jurisdictions.update(item.strip().lower() for item in emerging_contaminant.jurisdictions)
    if isinstance(dossier, VersionPinnedContaminantMonitoringReviewDossier):
        if dossier.interpretation_bundle.jurisdiction:
            dossier_jurisdictions.add(dossier.interpretation_bundle.jurisdiction.strip().lower())
    if isinstance(dossier, VersionPinnedMetalsMonitoringReviewDossier):
        if dossier.interpretation_bundle.jurisdiction:
            dossier_jurisdictions.add(dossier.interpretation_bundle.jurisdiction.strip().lower())

    if not dossier_jurisdictions or target_jurisdiction in dossier_jurisdictions:
        return (
            ReadinessStatus.PASS,
            "Target readiness jurisdiction is consistent with the dossier governance context.",
            None,
        )

    status = (
        ReadinessStatus.FAIL
        if target_profile_kind == "submission_candidate"
        else ReadinessStatus.REVIEW_REQUIRED
    )
    return (
        status,
        "Target readiness jurisdiction does not align with the dossier governance context.",
        ", ".join(sorted(dossier_jurisdictions)),
    )


def _historical_data_currency_status(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
    target_profile_kind: str,
) -> tuple[ReadinessStatus, str, str | None]:
    limitations = list(dossier.limitations)
    if isinstance(dossier, VersionPinnedContaminantMonitoringReviewDossier):
        limitations.extend(dossier.interpretation_bundle.limitations)
    if isinstance(dossier, VersionPinnedMetalsMonitoringReviewDossier):
        limitations.extend(dossier.interpretation_bundle.limitations)

    historical_limitations = [
        item for item in limitations if item.code == "historical_data_context" or item.code.startswith("historical_data_context.")
    ]
    if not historical_limitations:
        return (
            ReadinessStatus.PASS,
            "No unresolved historical data-currency limitations remain on the dossier.",
            None,
        )

    status = (
        ReadinessStatus.FAIL
        if target_profile_kind == "submission_candidate"
        else ReadinessStatus.REVIEW_REQUIRED
    )
    return (
        status,
        "Historical data-currency limitations remain unresolved on the dossier.",
        ", ".join(sorted(item.code for item in historical_limitations)),
    )


def _get_legal_limit_reviews(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
) -> list[ContaminantLegalLimitLookupResult]:
    if isinstance(dossier, VersionPinnedAdapterReviewDossier):
        return []
    return list(dossier.interpretation_bundle.legal_limit_reviews)


def _legal_limit_review_label(review: ContaminantLegalLimitLookupResult) -> str:
    parts: list[str] = []
    if review.jurisdiction:
        parts.append(review.jurisdiction)
    parts.append(review.contaminant_family.value)
    if review.substance_key:
        parts.append(review.substance_key)
    if review.commodity_code:
        parts.append(review.commodity_code)
    elif review.matrix_group:
        parts.append(review.matrix_group)
    return "/".join(parts)


def _legal_limit_support_status(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
    target_profile_kind: str,
) -> tuple[ReadinessStatus, str, str | None]:
    legal_limit_reviews = _get_legal_limit_reviews(dossier)
    if not legal_limit_reviews:
        if isinstance(dossier, VersionPinnedAdapterReviewDossier):
            return (
                ReadinessStatus.PASS,
                "No dossier-carried legal-limit support reviews apply to this workflow.",
                None,
            )
        status = (
            ReadinessStatus.REVIEW_REQUIRED
            if target_profile_kind == "submission_candidate"
            else ReadinessStatus.PASS
        )
        return (
            status,
            "No dossier-carried legal-limit support reviews were present for this governed monitoring dossier.",
            None,
        )

    non_exact_reviews = [
        review
        for review in legal_limit_reviews
        if review.requested_lane_status != RequestedLaneStatus.EXACT_CURATED_MATCH
    ]
    if not non_exact_reviews:
        return (
            ReadinessStatus.PASS,
            "Dossier-carried legal-limit support reviews show exact curated support for the reviewed lanes.",
            None,
        )

    note = "; ".join(
        f"{_legal_limit_review_label(review)}={review.requested_lane_status.value}"
        for review in non_exact_reviews
    )
    if target_profile_kind == "submission_candidate":
        return (
            ReadinessStatus.REVIEW_REQUIRED,
            "Dossier-carried legal-limit support is partial or missing for one or more reviewed lanes and requires human review before submission-candidate packaging.",
            note,
        )
    return (
        ReadinessStatus.PASS,
        "Legal-limit support posture remains explicit on the dossier for downstream review and does not borrow support from other jurisdictions or matrices.",
        note,
    )


def _get_required_fingerprint_roles(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
) -> set[str]:
    if isinstance(dossier, VersionPinnedAdapterReviewDossier):
        return ADAPTER_REQUIRED_DOSSIER_FINGERPRINT_ROLES
    if isinstance(dossier, VersionPinnedContaminantMonitoringReviewDossier):
        return CONTAMINANT_MONITORING_REQUIRED_DOSSIER_FINGERPRINT_ROLES
    return METALS_MONITORING_REQUIRED_DOSSIER_FINGERPRINT_ROLES


def _get_model_governance_snapshot(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
) -> ModelGovernanceRecord | None:
    if not isinstance(dossier, VersionPinnedAdapterReviewDossier):
        return None
    if dossier.model_governance_snapshot is None:
        return None
    return ModelGovernanceRecord.model_validate(dossier.model_governance_snapshot)


def _get_emerging_contaminant_snapshot(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
) -> EmergingContaminantRecord | None:
    if isinstance(dossier, VersionPinnedAdapterReviewDossier):
        return None
    if dossier.emerging_contaminant_snapshot is None:
        return None
    return EmergingContaminantRecord.model_validate(dossier.emerging_contaminant_snapshot)


def _get_source_governance_snapshot(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
) -> list[RegulatorySourceRecord]:
    return [RegulatorySourceRecord.model_validate(item) for item in dossier.source_governance_snapshot]


def _get_referenced_source_ids(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
    model_governance: ModelGovernanceRecord | None,
    emerging_contaminant: EmergingContaminantRecord | None,
) -> set[str]:
    if isinstance(dossier, VersionPinnedAdapterReviewDossier):
        referenced_source_ids = set(dossier.review_bundle.check_result.normalized_projection.source_ids)
    else:
        referenced_source_ids = set(dossier.interpretation_bundle.covered_source_ids)

    if model_governance is not None:
        referenced_source_ids.update(model_governance.source_ids)
    if emerging_contaminant is not None:
        referenced_source_ids.update(emerging_contaminant.source_ids)
    return referenced_source_ids


def _get_normative_sources(
    source_governance: list[RegulatorySourceRecord],
    model_governance: ModelGovernanceRecord | None,
    emerging_contaminant: EmergingContaminantRecord | None,
) -> list[RegulatorySourceRecord]:
    if model_governance is not None:
        return [item for item in source_governance if model_governance.model_family.value in item.normative_for]
    if emerging_contaminant is not None:
        family_source_ids = set(emerging_contaminant.source_ids)
        return [item for item in source_governance if item.source_id in family_source_ids]
    return []


def _combined_disclaimer_text(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
) -> str:
    parts = []
    parts.extend(dossier.notes)
    parts.extend(item.message for item in dossier.limitations)
    if isinstance(dossier, VersionPinnedAdapterReviewDossier):
        parts.extend(dossier.review_bundle.notes)
        parts.extend(item.message for item in dossier.review_bundle.limitations)
    else:
        parts.extend(dossier.interpretation_bundle.notes)
        parts.extend(dossier.signoff_packet.notes)
        parts.extend(item.message for item in dossier.interpretation_bundle.limitations)
        if hasattr(dossier.interpretation_bundle, "check_result"):
            parts.extend(dossier.interpretation_bundle.check_result.notes)
    return "\n".join(parts).lower()


def _governance_snapshots_complete(
    source_governance: list[RegulatorySourceRecord],
    model_governance: ModelGovernanceRecord | None,
    emerging_contaminant: EmergingContaminantRecord | None,
) -> bool:
    return bool(source_governance) and (model_governance is not None or emerging_contaminant is not None)


def _governance_disclaimers(
    model_governance: ModelGovernanceRecord | None,
    emerging_contaminant: EmergingContaminantRecord | None,
) -> list[str]:
    if model_governance is not None:
        return model_governance.required_disclaimers
    if emerging_contaminant is not None and emerging_contaminant.submission_use != SubmissionUse.ALLOWED:
        return []
    return []


def _internal_review_governance_status(
    model_governance: ModelGovernanceRecord | None,
    emerging_contaminant: EmergingContaminantRecord | None,
) -> tuple[ReadinessStatus, str]:
    if model_governance is not None and not model_governance.submission_allowed:
        return (
            ReadinessStatus.REVIEW_REQUIRED,
            "Current model family is not submission-capable and remains internal-review-only or harness-only.",
        )
    if emerging_contaminant is not None and emerging_contaminant.submission_use != SubmissionUse.ALLOWED:
        return (
            ReadinessStatus.REVIEW_REQUIRED,
            "Current governed contaminant family is not submission-capable and remains review-only or exploratory-only.",
        )
    return (
        ReadinessStatus.PASS,
        "Governance posture does not block internal review.",
    )


def _submission_candidate_governance_status(
    target_profile: RegulatoryReadinessProfile,
    model_governance: ModelGovernanceRecord | None,
    emerging_contaminant: EmergingContaminantRecord | None,
) -> tuple[ReadinessStatus, str]:
    if model_governance is not None and not model_governance.submission_allowed:
        return (
            ReadinessStatus.FAIL,
            "Current model family is not designated as a submission-capable engine.",
        )
    if emerging_contaminant is not None:
        if target_profile.profile_id in emerging_contaminant.hard_failure_profiles:
            return (
                ReadinessStatus.FAIL,
                "Current contaminant-family profile is explicitly hard-failed for submission-oriented use.",
            )
        if emerging_contaminant.submission_use != SubmissionUse.ALLOWED:
            return (
                ReadinessStatus.FAIL,
                "Current governed contaminant family is not designated as submission-capable.",
            )
    return (
        ReadinessStatus.PASS,
        "Governance posture allows submission-candidate evaluation.",
    )


def _collect_scientific_follow_up_items(
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ),
) -> list[ScientificFollowUpItem]:
    if isinstance(dossier, VersionPinnedAdapterReviewDossier):
        return []

    escalation_by_action_id = {
        item.action_id: item
        for item in dossier.escalation_items
    }
    follow_up_items: list[ScientificFollowUpItem] = []

    for action in dossier.signoff_packet.action_items:
        if not action.action_id.startswith("review_scientific_ledger."):
            continue
        escalation = escalation_by_action_id.get(action.action_id)
        follow_up_items.append(
            ScientificFollowUpItem(
                action_id=action.action_id,
                category=action.category,
                title=action.title,
                priority=action.priority,
                blocking=action.blocking,
                summary=action.summary,
                decision_status=action.decision_status,
                linked_record_ids=action.linked_record_ids,
                rationale=action.rationale,
                supporting_uris=action.supporting_uris,
                escalated=escalation is not None,
                escalation_type=(
                    MetalsMonitoringEscalationType(escalation.escalation_type)
                    if escalation is not None
                    else None
                ),
                follow_up_note=escalation.follow_up_note if escalation is not None else None,
            )
        )
    return follow_up_items


def _build_scientific_follow_up_queues(
    scientific_follow_up_items: list[ScientificFollowUpItem],
) -> ScientificFollowUpQueues:
    open_action_ids: list[str] = []
    pending_action_ids: list[str] = []
    acknowledged_action_ids: list[str] = []
    completed_action_ids: list[str] = []
    waived_action_ids: list[str] = []
    escalated_action_ids: list[str] = []

    for item in scientific_follow_up_items:
        if item.decision_status == InteroperabilityActionDecisionStatus.PENDING:
            pending_action_ids.append(item.action_id)
            open_action_ids.append(item.action_id)
        elif item.decision_status == InteroperabilityActionDecisionStatus.ACKNOWLEDGED:
            acknowledged_action_ids.append(item.action_id)
            open_action_ids.append(item.action_id)
        elif item.decision_status == InteroperabilityActionDecisionStatus.COMPLETED:
            completed_action_ids.append(item.action_id)
        elif item.decision_status == InteroperabilityActionDecisionStatus.WAIVED:
            waived_action_ids.append(item.action_id)

        if item.escalated:
            escalated_action_ids.append(item.action_id)

    return ScientificFollowUpQueues(
        open_action_ids=open_action_ids,
        pending_action_ids=pending_action_ids,
        acknowledged_action_ids=acknowledged_action_ids,
        completed_action_ids=completed_action_ids,
        waived_action_ids=waived_action_ids,
        escalated_action_ids=escalated_action_ids,
    )


def _build_rule_result(
    rule_id: str,
    profile_id: str,
    status: ReadinessStatus,
    message: str,
    *,
    blocking: bool = False,
    note: str | None = None,
) -> RegulatoryRuleResult:
    return RegulatoryRuleResult(
        rule_id=rule_id,
        profile_id=profile_id,
        status=status,
        message=message,
        blocking=blocking,
        note=note,
    )


def assess_review_dossier_readiness(
    defaults_registry: DefaultsRegistry,
    repo_root: Path,
    request: AssessReviewDossierReadinessRequest,
) -> ReviewDossierReadinessAssessment:
    target_profile = RegulatoryReadinessProfile.model_validate(
        defaults_registry.get_regulatory_readiness_profile_record(request.target_profile)
    )
    target_profile_kind = _profile_kind(defaults_registry, target_profile.profile_id)
    rules_manifest = read_regulatory_rules(repo_root)
    published_rule_ids = {item["ruleId"] for item in rules_manifest["rules"]}

    dossier = request.dossier
    legal_limit_reviews = _get_legal_limit_reviews(dossier)
    model_governance = _get_model_governance_snapshot(dossier)
    emerging_contaminant = _get_emerging_contaminant_snapshot(dossier)
    source_governance = _get_source_governance_snapshot(dossier)

    referenced_source_ids = _get_referenced_source_ids(dossier, model_governance, emerging_contaminant)
    resolved_source_ids = {item.source_id for item in source_governance}
    missing_source_ids = sorted(referenced_source_ids - resolved_source_ids)
    normative_sources = _get_normative_sources(source_governance, model_governance, emerging_contaminant)
    technical_report_sources = [item for item in source_governance if item.regulatory_role.value == "technical_report"]
    active_errata = [
        item for item in (model_governance.errata if model_governance is not None else []) if item.active
    ]
    combined_disclaimer_text = _combined_disclaimer_text(dossier)
    required_disclaimers = _governance_disclaimers(model_governance, emerging_contaminant)
    missing_disclaimers = [
        item for item in required_disclaimers if item.lower() not in combined_disclaimer_text
    ]
    missing_fingerprint_roles = sorted(
        _get_required_fingerprint_roles(dossier) - {item.role for item in dossier.pinned_resources}
    )
    governance_snapshots_complete = _governance_snapshots_complete(
        source_governance,
        model_governance,
        emerging_contaminant,
    )
    consultation_disclaimer_present = "consultation" in combined_disclaimer_text

    applied_rules: list[RegulatoryRuleResult] = []

    def add_rule(
        rule_id: str,
        status: ReadinessStatus,
        message: str,
        *,
        blocking: bool = False,
        note: str | None = None,
    ) -> None:
        if rule_id not in published_rule_ids:
            raise ValueError(f"Unpublished regulatory rule referenced by implementation: {rule_id}")
        applied_rules.append(
            _build_rule_result(
                rule_id,
                target_profile.profile_id,
                status,
                message,
                blocking=blocking,
                note=note,
            )
        )

    if governance_snapshots_complete:
        add_rule(
            "governance_snapshots_complete",
            ReadinessStatus.PASS,
            "Applicable governance snapshots are present on the dossier.",
        )
    else:
        status = (
            ReadinessStatus.FAIL
            if target_profile_kind == "submission_candidate"
            else ReadinessStatus.REVIEW_REQUIRED
        )
        add_rule(
            "governance_snapshots_complete",
            status,
            "Required model-family or contaminant-family governance snapshots are missing from the dossier.",
            blocking=status == ReadinessStatus.FAIL,
        )

    if not missing_source_ids:
        add_rule(
            "source_resolution_complete",
            ReadinessStatus.PASS,
            "All source ids referenced by the dossier resolve to governed source records.",
        )
    else:
        status = (
            ReadinessStatus.FAIL
            if target_profile_kind == "submission_candidate"
            else ReadinessStatus.REVIEW_REQUIRED
        )
        add_rule(
            "source_resolution_complete",
            status,
            f"Dossier references unresolved governed source ids: {missing_source_ids}.",
            blocking=status == ReadinessStatus.FAIL,
        )

    if not missing_fingerprint_roles:
        add_rule(
            "required_fingerprints_present",
            ReadinessStatus.PASS,
            "All required dossier fingerprints are present.",
        )
    else:
        status = (
            ReadinessStatus.FAIL
            if target_profile_kind == "submission_candidate"
            else ReadinessStatus.REVIEW_REQUIRED
        )
        add_rule(
            "required_fingerprints_present",
            status,
            f"Dossier is missing required pinned resource fingerprints: {missing_fingerprint_roles}.",
            blocking=status == ReadinessStatus.FAIL,
        )

    if not missing_disclaimers:
        add_rule(
            "required_disclaimers_present",
            ReadinessStatus.PASS,
            "All required governance disclaimers are present in dossier-facing notes or limitations.",
        )
    else:
        status = (
            ReadinessStatus.FAIL
            if target_profile_kind == "submission_candidate"
            else ReadinessStatus.REVIEW_REQUIRED
        )
        add_rule(
            "required_disclaimers_present",
            status,
            f"Dossier is missing required governance disclaimers: {missing_disclaimers}.",
            blocking=status == ReadinessStatus.FAIL,
        )

    scientific_integrity_status, scientific_integrity_message, scientific_integrity_note = (
        _scientific_integrity_status(dossier, target_profile_kind)
    )
    add_rule(
        "scientific_integrity_verified",
        scientific_integrity_status,
        scientific_integrity_message,
        blocking=scientific_integrity_status == ReadinessStatus.FAIL,
        note=scientific_integrity_note,
    )

    jurisdiction_status, jurisdiction_message, jurisdiction_note = _jurisdiction_consistency_status(
        dossier,
        target_profile,
        model_governance,
        emerging_contaminant,
        target_profile_kind,
    )
    add_rule(
        "jurisdiction_consistency",
        jurisdiction_status,
        jurisdiction_message,
        blocking=jurisdiction_status == ReadinessStatus.FAIL,
        note=jurisdiction_note,
    )

    data_currency_status, data_currency_message, data_currency_note = _historical_data_currency_status(
        dossier,
        target_profile_kind,
    )
    add_rule(
        "data_currency_reviewed",
        data_currency_status,
        data_currency_message,
        blocking=data_currency_status == ReadinessStatus.FAIL,
        note=data_currency_note,
    )

    legal_limit_support_status, legal_limit_support_message, legal_limit_support_note = (
        _legal_limit_support_status(dossier, target_profile_kind)
    )
    add_rule(
        "legal_limit_support_explicit",
        legal_limit_support_status,
        legal_limit_support_message,
        note=legal_limit_support_note,
    )

    if model_governance is not None and model_governance.governance_status == GovernanceStatus.DEPRECATED:
        deprecated_status = (
            ReadinessStatus.FAIL
            if target_profile_kind == "submission_candidate"
            else ReadinessStatus.REVIEW_REQUIRED
        )
        add_rule(
            "deprecated_governance_status_allowed",
            deprecated_status,
            "Model governance is marked as deprecated and requires explicit review before this readiness profile can be used.",
            blocking=deprecated_status == ReadinessStatus.FAIL,
            note=model_governance.model_family.value,
        )
    else:
        add_rule(
            "deprecated_governance_status_allowed",
            ReadinessStatus.PASS,
            "No deprecated governance state blocks the selected readiness profile.",
        )

    if target_profile_kind == "internal_review":
        internal_status, internal_message = _internal_review_governance_status(
            model_governance,
            emerging_contaminant,
        )
        add_rule(
            "model_submission_not_allowed",
            internal_status,
            internal_message,
        )

        flagged_sources = [
            item
            for item in normative_sources
            if item.document_status.value in {"draft", "consultation", "tool_metadata"}
        ]
        if flagged_sources:
            add_rule(
                "normative_source_status_allowed",
                ReadinessStatus.REVIEW_REQUIRED,
                "Normative sources include draft, consultation, or tool-metadata records that require explicit human review.",
                note=", ".join(sorted(item.source_id for item in flagged_sources)),
            )
        else:
            add_rule(
                "normative_source_status_allowed",
                ReadinessStatus.PASS,
                "Normative source statuses are acceptable for internal review.",
            )

        if active_errata:
            add_rule(
                "active_errata_status",
                ReadinessStatus.REVIEW_REQUIRED,
                "Active model errata require explicit human review before relying on the dossier.",
                note=", ".join(sorted(item.erratum_id for item in active_errata)),
            )
        else:
            add_rule(
                "active_errata_status",
                ReadinessStatus.PASS,
                "No active errata require additional internal-review handling.",
            )

    elif target_profile_kind == "submission_candidate":
        submission_status, submission_message = _submission_candidate_governance_status(
            target_profile,
            model_governance,
            emerging_contaminant,
        )
        add_rule(
            "model_submission_not_allowed",
            submission_status,
            submission_message,
            blocking=submission_status == ReadinessStatus.FAIL,
        )

        blocked_sources = [
            item
            for item in normative_sources
            if item.document_status.value in {"draft", "consultation", "superseded"}
        ]
        if blocked_sources:
            add_rule(
                "normative_source_status_allowed",
                ReadinessStatus.FAIL,
                "Normative sources include draft, consultation, or superseded records that block submission-candidate status.",
                blocking=True,
                note=", ".join(sorted(item.source_id for item in blocked_sources)),
            )
        else:
            add_rule(
                "normative_source_status_allowed",
                ReadinessStatus.PASS,
                "Normative source statuses do not block submission-candidate review.",
            )

        disallowed_sources = [
            item for item in normative_sources if item.submission_use.value == "not_allowed"
        ]
        if disallowed_sources:
            add_rule(
                "normative_source_submission_use",
                ReadinessStatus.FAIL,
                "Normative sources include records explicitly marked as not allowed for submission use.",
                blocking=True,
                note=", ".join(sorted(item.source_id for item in disallowed_sources)),
            )
        else:
            add_rule(
                "normative_source_submission_use",
                ReadinessStatus.PASS,
                "Normative sources are not explicitly blocked from submission use.",
            )

        if technical_report_sources:
            add_rule(
                "technical_report_dependencies",
                ReadinessStatus.REVIEW_REQUIRED,
                "Technical-report dependencies remain in the dossier and require human review before packaging as a submission candidate.",
                note=", ".join(sorted(item.source_id for item in technical_report_sources)),
            )
        else:
            add_rule(
                "technical_report_dependencies",
                ReadinessStatus.PASS,
                "No technical-report dependencies remain on the dossier.",
            )

        if any(item.blocking for item in active_errata):
            add_rule(
                "active_errata_status",
                ReadinessStatus.FAIL,
                "Blocking errata are active for the selected model family.",
                blocking=True,
                note=", ".join(sorted(item.erratum_id for item in active_errata if item.blocking)),
            )
        elif active_errata:
            add_rule(
                "active_errata_status",
                ReadinessStatus.REVIEW_REQUIRED,
                "Active non-blocking errata require review before submission-candidate packaging.",
                note=", ".join(sorted(item.erratum_id for item in active_errata)),
            )
        else:
            add_rule(
                "active_errata_status",
                ReadinessStatus.PASS,
                "No active errata affect submission-candidate review.",
            )

    elif target_profile_kind == "consultation_exploratory":
        if model_governance is not None and model_governance.governance_status not in {
            GovernanceStatus.COMPATIBILITY_HARNESS_ONLY,
            GovernanceStatus.INTERNAL_REFERENCE_ONLY,
        }:
            add_rule(
                "consultation_model_status_allowed",
                ReadinessStatus.REVIEW_REQUIRED,
                "Model governance status is outside the expected consultation-oriented families.",
            )
        else:
            add_rule(
                "consultation_model_status_allowed",
                ReadinessStatus.PASS,
                "Governance status is acceptable for consultation-oriented exploration.",
            )

        if consultation_disclaimer_present:
            add_rule(
                "consultation_watermark_present",
                ReadinessStatus.PASS,
                "Consultation-oriented disclaimer text is present on the dossier.",
            )
        else:
            add_rule(
                "consultation_watermark_present",
                ReadinessStatus.REVIEW_REQUIRED,
                "Consultation-oriented disclaimer text is missing from dossier-facing notes or limitations.",
            )

        if missing_source_ids:
            add_rule(
                "source_resolution_for_consultation",
                ReadinessStatus.REVIEW_REQUIRED,
                "Exploratory dossier has unresolved source governance records.",
                note=", ".join(missing_source_ids),
            )
        else:
            add_rule(
                "source_resolution_for_consultation",
                ReadinessStatus.PASS,
                "Source governance resolution is complete for exploratory review.",
            )

    blocking_rules = [item for item in applied_rules if item.status == ReadinessStatus.FAIL or item.blocking]
    warning_rules = [item for item in applied_rules if item.status == ReadinessStatus.REVIEW_REQUIRED]
    scientific_follow_up_items = _collect_scientific_follow_up_items(dossier)
    scientific_follow_up_queues = _build_scientific_follow_up_queues(scientific_follow_up_items)
    if blocking_rules:
        overall_status = ReadinessStatus.FAIL
    elif warning_rules:
        overall_status = ReadinessStatus.REVIEW_REQUIRED
    else:
        overall_status = ReadinessStatus.PASS

    notes = [
        "Readiness evaluation uses a fixed Phase 1 ruleset rather than a generic policy DSL.",
        "Assessment combines governance checks with explicit scientific-integrity gates and does not imply final regulatory acceptance.",
    ]
    if legal_limit_reviews:
        notes.append(
            "Legal-limit support reviews remain attached to this assessment so downstream workflows can distinguish exact curated support from partial, anchor-only, or explicit-gap posture without borrowing across jurisdictions or matrices."
        )
    if target_profile_kind == "submission_candidate" and model_governance is not None:
        notes.append(
            f"Model family {model_governance.model_family.value} is currently governed as {model_governance.governance_status.value}."
        )
    if target_profile_kind == "submission_candidate" and emerging_contaminant is not None:
        notes.append(
            f"Contaminant family {emerging_contaminant.family_id.value} currently remains {emerging_contaminant.submission_use.value} for submission-oriented use."
        )
    if scientific_follow_up_items:
        notes.append(
            "Scientific follow-up items are derived from ledger-backed reviewer actions already present on the dossier signoff packet."
        )

    return ReviewDossierReadinessAssessment(
        overall_status=overall_status,
        target_profile=target_profile,
        model_governance=model_governance,
        emerging_contaminant=emerging_contaminant,
        source_governance=source_governance,
        applied_rules=applied_rules,
        blocking_rules=blocking_rules,
        warning_rules=warning_rules,
        legal_limit_reviews=legal_limit_reviews,
        scientific_follow_up_items=scientific_follow_up_items,
        scientific_follow_up_queues=scientific_follow_up_queues,
        required_disclaimers=required_disclaimers,
        notes=notes,
    )
