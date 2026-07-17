from __future__ import annotations

from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.models import (
    AdapterReviewBundle,
    BundleProfile,
    CommodityContributionDelta,
    ConfidentialityAnnotation,
    ConfidentialityTag,
    CompareDietaryScenariosRequest,
    ContaminantLegalLimitLookupResult,
    ContaminantFamily,
    ContaminantMonitoringInterpretationBundle,
    ContaminantMonitoringReviewPrompt,
    DependencyDescriptor,
    DietaryScenarioComparisonRecord,
    ExportAdapterReviewBundleRequest,
    ExportContaminantMonitoringInterpretationBundleRequest,
    ExportMetalsMonitoringInterpretationBundleRequest,
    ExportPbpkOralInputRequest,
    ExportToxclawDietaryEvidenceBundleRequest,
    FitForPurpose,
    LimitationNote,
    LookupContaminantLegalLimitsRequest,
    MetalsMonitoringInterpretationBundle,
    MetalsMonitoringReviewPrompt,
    MetalsReviewFocusRecord,
    PbpkDosingRegimen,
    PbpkExternalImportBundle,
    SubmissionUse,
    RouteDoseEstimate,
    ToxclawDietaryEvidenceBundle,
    ToxclawEvidenceItem,
    ReviewResourceReference,
)
from dietary_mcp.package_metadata import VERSION
from dietary_mcp.provenance import ProvenanceBuilder
from dietary_mcp.scientific_ledger import (
    build_contaminant_monitoring_bundle_ledger,
    build_metals_monitoring_bundle_ledger,
)
from dietary_mcp.source_database import lookup_contaminant_legal_limits


def _aggregate_submission_use(values: list[SubmissionUse]) -> SubmissionUse:
    if not values:
        return SubmissionUse.REVIEW_REQUIRED
    if any(value == SubmissionUse.NOT_ALLOWED for value in values):
        return SubmissionUse.NOT_ALLOWED
    if any(value == SubmissionUse.REVIEW_REQUIRED for value in values):
        return SubmissionUse.REVIEW_REQUIRED
    return SubmissionUse.ALLOWED


def _historical_context_limitations(
    defaults_registry: DefaultsRegistry,
    *,
    records: list[object],
    record_kind_label: str,
) -> list[LimitationNote]:
    limitations: list[LimitationNote] = []
    for record in records:
        assessment = defaults_registry.assess_source_currency(
            source_ids=getattr(record, "source_ids"),
            data_period=getattr(record, "data_period", None),
        )
        if not assessment.review_required:
            continue
        if assessment.historical_data_period and assessment.data_period_end_year is not None:
            message = (
                f"{record_kind_label} {getattr(record, 'record_id')} depends on data period "
                f"`{assessment.data_period}` ending in {assessment.data_period_end_year}; treat it as historical relative to {assessment.reference_date.isoformat()}."
            )
        else:
            message = (
                f"{record_kind_label} {getattr(record, 'record_id')} depends on historical supporting sources "
                f"({', '.join(assessment.historical_source_ids)}) as of {assessment.reference_date.isoformat()}."
            )
        limitations.append(
            LimitationNote(
                code=f"historical_data_context.{getattr(record, 'record_id')}",
                message=message,
            )
        )
    return limitations


def _build_legal_limit_reviews(
    defaults_registry: DefaultsRegistry,
    *,
    contaminant_family: ContaminantFamily,
    jurisdiction: str | None,
    authority: str | None,
    matrix_groups: list[str] | None = None,
) -> list[ContaminantLegalLimitLookupResult]:
    normalized_matrix_groups = sorted({item for item in (matrix_groups or []) if item})
    requests = (
        [
            LookupContaminantLegalLimitsRequest(
                contaminant_family=contaminant_family,
                jurisdiction=jurisdiction,
                authority=authority,
                matrix_group=matrix_group,
            )
            for matrix_group in normalized_matrix_groups
        ]
        if normalized_matrix_groups
        else [
            LookupContaminantLegalLimitsRequest(
                contaminant_family=contaminant_family,
                jurisdiction=jurisdiction,
                authority=authority,
            )
        ]
    )
    return [
        lookup_contaminant_legal_limits(defaults_registry, request)
        for request in requests
    ]


def _legal_limit_lane_key(review: ContaminantLegalLimitLookupResult) -> str:
    return review.matrix_group or review.commodity_code or review.substance_key or "family"


def _legal_limit_lane_label(review: ContaminantLegalLimitLookupResult) -> str:
    if review.matrix_group:
        return f"matrix group `{review.matrix_group}`"
    if review.commodity_code:
        return f"commodity `{review.commodity_code}`"
    if review.substance_key:
        return f"substance `{review.substance_key}`"
    return "current family/jurisdiction lane"


def _legal_limit_scope_summary(review: ContaminantLegalLimitLookupResult) -> str | None:
    jurisdiction_label = (review.jurisdiction or "requested jurisdiction").upper()
    lane_label = _legal_limit_lane_label(review)
    status = review.requested_lane_status.value
    if status in {"exact_curated_match", "unscoped_lookup"}:
        return None
    if status == "family_curated_but_requested_lane_unmatched":
        return (
            f"{jurisdiction_label} retains curated contaminant legal-limit support for {lane_label}, "
            "but the current lane falls outside the exact shipped scope."
        )
    if status == "anchor_only_family":
        return (
            f"{jurisdiction_label} retains only an official family anchor for {lane_label}; "
            "exact jurisdiction-specific legal-limit records are not shipped for this lane."
        )
    if status == "explicit_gap":
        return (
            f"{jurisdiction_label} carries an explicit contaminant legal-limit coverage gap for {lane_label}."
        )
    if status == "no_curated_family_coverage":
        return (
            f"{jurisdiction_label} does not currently ship curated contaminant legal-limit coverage for {lane_label}."
        )
    return None


def _legal_limit_scope_prompt(review: ContaminantLegalLimitLookupResult) -> str | None:
    summary = _legal_limit_scope_summary(review)
    if summary is None:
        return None
    return (
        f"{summary} Confirm reviewers do not overread this bundle as jurisdiction-complete and do not "
        "borrow legal-limit support from another authority, matrix, or commodity lane."
    )


def _legal_limit_scope_limitation(review: ContaminantLegalLimitLookupResult) -> LimitationNote | None:
    summary = _legal_limit_scope_summary(review)
    if summary is None:
        return None
    return LimitationNote(
        code=f"legal_limit_scope.{_legal_limit_lane_key(review)}",
        message=summary + " No cross-jurisdiction or cross-matrix borrowing is implied.",
    )


def compare_dietary_scenarios(
    request: CompareDietaryScenariosRequest,
    provenance_builder: ProvenanceBuilder,
) -> DietaryScenarioComparisonRecord:
    base_by_code = {
        item.commodity.commodity_code: item for item in request.base_summary.commodity_contributions
    }
    candidate_by_code = {
        item.commodity.commodity_code: item for item in request.candidate_summary.commodity_contributions
    }

    deltas = []
    for commodity_code, base_item in base_by_code.items():
        candidate_item = candidate_by_code.get(commodity_code)
        if not candidate_item:
            continue
        absolute_delta = (
            candidate_item.contribution_mg_per_kg_bw_per_day - base_item.contribution_mg_per_kg_bw_per_day
        )
        relative_delta = None
        if base_item.contribution_mg_per_kg_bw_per_day:
            relative_delta = absolute_delta / base_item.contribution_mg_per_kg_bw_per_day
        deltas.append(
            CommodityContributionDelta(
                commodity=base_item.commodity,
                base_value=base_item.contribution_mg_per_kg_bw_per_day,
                candidate_value=candidate_item.contribution_mg_per_kg_bw_per_day,
                absolute_delta=absolute_delta,
                relative_delta=relative_delta,
            )
        )

    base_params = {f"{item.parameter}:{item.value}" for item in request.base_summary.assumptions_applied}
    candidate_params = {
        f"{item.parameter}:{item.value}" for item in request.candidate_summary.assumptions_applied
    }
    changed_assumptions = sorted(candidate_params.symmetric_difference(base_params))
    dominant_drivers = [
        f"{item.commodity.commodity_code} delta={item.absolute_delta:.6g} mg/kg-bw/day"
        for item in sorted(deltas, key=lambda item: abs(item.absolute_delta), reverse=True)[:3]
    ]

    lower_delta = None
    upper_delta = None
    if (
        request.base_summary.lower_bound_total_intake_mg_per_kg_bw_per_day is not None
        and request.candidate_summary.lower_bound_total_intake_mg_per_kg_bw_per_day is not None
    ):
        lower_delta = (
            request.candidate_summary.lower_bound_total_intake_mg_per_kg_bw_per_day
            - request.base_summary.lower_bound_total_intake_mg_per_kg_bw_per_day
        )
    if (
        request.base_summary.upper_bound_total_intake_mg_per_kg_bw_per_day is not None
        and request.candidate_summary.upper_bound_total_intake_mg_per_kg_bw_per_day is not None
    ):
        upper_delta = (
            request.candidate_summary.upper_bound_total_intake_mg_per_kg_bw_per_day
            - request.base_summary.upper_bound_total_intake_mg_per_kg_bw_per_day
        )

    return DietaryScenarioComparisonRecord(
        base_scenario_id=request.base_summary.scenario_id,
        candidate_scenario_id=request.candidate_summary.scenario_id,
        intake_window_semantic=request.base_summary.intake_window_semantic,
        base_total_intake_mg_per_kg_bw_per_day=request.base_summary.total_intake_mg_per_kg_bw_per_day,
        candidate_total_intake_mg_per_kg_bw_per_day=request.candidate_summary.total_intake_mg_per_kg_bw_per_day,
        intake_delta_mg_per_kg_bw_per_day=(
            request.candidate_summary.total_intake_mg_per_kg_bw_per_day
            - request.base_summary.total_intake_mg_per_kg_bw_per_day
        ),
        lower_bound_delta_mg_per_kg_bw_per_day=lower_delta,
        upper_bound_delta_mg_per_kg_bw_per_day=upper_delta,
        contribution_deltas=deltas,
        changed_assumptions=changed_assumptions,
        dominant_drivers=dominant_drivers,
        provenance=provenance_builder.bundle(),
    )


def export_pbpk_oral_input(
    request: ExportPbpkOralInputRequest,
    provenance_builder: ProvenanceBuilder,
) -> PbpkExternalImportBundle:
    summary = request.summary
    scenario = request.scenario
    route_dose_estimate = RouteDoseEstimate(
        scenario_id=summary.scenario_id,
        chemical_identity=scenario.chemical_identity,
        intake_window_semantic=summary.intake_window_semantic,
        value_mg_per_kg_bw_per_day=summary.total_intake_mg_per_kg_bw_per_day,
        lower_bound_mg_per_kg_bw_per_day=summary.lower_bound_total_intake_mg_per_kg_bw_per_day,
        upper_bound_mg_per_kg_bw_per_day=summary.upper_bound_total_intake_mg_per_kg_bw_per_day,
        fit_for_purpose=FitForPurpose.DOWNSTREAM_EXPORT,
        provenance=provenance_builder.bundle(summary.provenance.source_references),
        limitations=[
            LimitationNote(
                code="food_taxonomy_removed",
                message="PBPK export normalizes the dietary result to oral dose semantics and omits commodity-taxonomy detail.",
            )
        ],
    )
    regimen = PbpkDosingRegimen(
        schedule="single_day" if summary.intake_window_semantic.value == "acute" else "daily_repeat",
        dose_frequency_per_day=24.0 / request.dosing_interval_hours,
        duration_days=1.0 if summary.intake_window_semantic.value == "acute" else None,
    )
    return PbpkExternalImportBundle(
        route_dose_estimate=route_dose_estimate,
        dosing_regimen=regimen,
        dependencies=[
            DependencyDescriptor(name="dietary-mcp", version=VERSION, role="producer"),
            DependencyDescriptor(name=summary.scenario_class.value, version=VERSION, role="workflow"),
            DependencyDescriptor(name=scenario.model_family.value, version=VERSION, role="model_family"),
        ],
        exposurePlausibilityRecords=request.exposure_plausibility_records,
        provenance=provenance_builder.bundle(summary.provenance.source_references),
    )


def export_toxclaw_dietary_evidence_bundle(
    request: ExportToxclawDietaryEvidenceBundleRequest,
    provenance_builder: ProvenanceBuilder,
) -> ToxclawDietaryEvidenceBundle:
    route_dose_estimate = export_pbpk_oral_input(
        ExportPbpkOralInputRequest(
            scenario=request.scenario,
            summary=request.summary,
        ),
        provenance_builder,
    ).route_dose_estimate
    seen = set()
    evidence_items = []
    for source_reference in request.summary.provenance.source_references:
        if source_reference.source_id in seen:
            continue
        seen.add(source_reference.source_id)
        evidence_items.append(
            ToxclawEvidenceItem(
                label=source_reference.title,
                source_reference=source_reference,
            )
        )
    return ToxclawDietaryEvidenceBundle(
        scenario=request.scenario,
        summary=request.summary,
        route_dose_estimate=route_dose_estimate,
        assumptions=request.summary.assumptions_applied,
        evidence_items=evidence_items,
        provenance=provenance_builder.bundle(request.summary.provenance.source_references),
        limitations=[
            LimitationNote(
                code="screening_bundle",
                message="Evidence bundle is suitable for orchestration and review support, not final regulatory conclusions.",
            )
        ],
    )


def export_adapter_review_bundle(
    request: ExportAdapterReviewBundleRequest,
) -> AdapterReviewBundle:
    check_result = request.check_result
    comparison_result = request.comparison_result

    if check_result.model_family != comparison_result.model_family:
        raise DietaryValidationError(
            code="adapter_review_bundle_model_family_mismatch",
            message="Adapter review bundle requires matching model families.",
            suggestion="Build the review bundle from a check result and comparison result produced for the same adapter family.",
        )
    if check_result.template_name != comparison_result.template_name:
        raise DietaryValidationError(
            code="adapter_review_bundle_template_mismatch",
            message="Adapter review bundle requires matching template names.",
            suggestion="Ensure the walkthrough comparison was produced from the same checked adapter import result.",
        )
    if check_result.walkthrough_name and check_result.walkthrough_name != comparison_result.walkthrough_name:
        raise DietaryValidationError(
            code="adapter_review_bundle_walkthrough_mismatch",
            message="Adapter review bundle requires matching walkthrough names.",
            suggestion="Use a comparison result generated against the walkthrough linked to the adapter check result.",
        )

    referenced_resources = [
        ReviewResourceReference(
            role="template",
            uri=check_result.template_resource_uri,
            description="Packaged adapter input template used to prepare the reviewed CSV text.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="walkthrough",
            uri=comparison_result.walkthrough_resource_uri,
            description="Governed walkthrough baseline used for the focused adapter review diff.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="documentation",
            uri=check_result.documentation_resource_uri,
            description="Operator documentation describing the adapter check and walkthrough comparison workflow.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
    ]

    if check_result.walkthrough_name:
        referenced_resources.append(
            ReviewResourceReference(
                role="walkthrough_manifest_entry",
                uri="adapter-import-walkthroughs://manifest",
                description="Manifest listing the governed walkthroughs published by Dietary MCP.",
                confidentiality_tag=ConfidentialityTag.PUBLIC,
            )
        )

    return AdapterReviewBundle(
        bundle_profile=BundleProfile.INTERNAL_REVIEW,
        review_status="match" if comparison_result.status == "match" else "review_required",
        model_family=check_result.model_family,
        template_name=check_result.template_name,
        walkthrough_name=comparison_result.walkthrough_name,
        check_result=check_result,
        comparison_result=comparison_result,
        referenced_resources=referenced_resources,
        dependencies=[
            DependencyDescriptor(name="dietary-mcp", version=VERSION, role="producer"),
            DependencyDescriptor(name="dietary_check_adapter_import", version=VERSION, role="check_workflow"),
            DependencyDescriptor(
                name="dietary_compare_adapter_import_to_walkthrough",
                version=VERSION,
                role="comparison_workflow",
            ),
            DependencyDescriptor(
                name=check_result.model_family.value,
                version=VERSION,
                role="model_family",
            ),
        ],
        matched_field_count=len(comparison_result.matched_fields),
        mismatch_field_count=len(comparison_result.mismatch_fields),
        confidentiality_annotations=[
            ConfidentialityAnnotation(
                target_path="check_result.chemical_identity",
                target_kind="field",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                rationale="Chemical identity can remain non-public during internal review workflows.",
            ),
            ConfidentialityAnnotation(
                target_path="check_result.declared_totals",
                target_kind="field",
                confidentiality_tag=ConfidentialityTag.CONFIDENTIAL,
                rationale="Declared case totals can encode non-public review context and are redacted from public exports.",
            ),
        ],
        limitations=[
            LimitationNote(
                code="screening_review_bundle",
                message="Adapter review bundle supports compatibility review and audit handoff, not final regulatory conclusions.",
            )
        ],
        notes=[
            "Bundle packages the adapter check result, governed walkthrough diff, and referenced review resources into a single auditable handoff object.",
            "Comparison findings are limited to stable normalized fields and do not include runtime-generated IDs or timestamps.",
            "Review-required status indicates one or more focused diff fields diverged from the governed walkthrough baseline.",
        ],
    )


def export_contaminant_monitoring_interpretation_bundle(
    defaults_registry: DefaultsRegistry,
    request: ExportContaminantMonitoringInterpretationBundleRequest,
) -> ContaminantMonitoringInterpretationBundle:
    check_result = request.check_result
    reporting_profile_payloads = []
    linked_review_focus_records: list[MetalsReviewFocusRecord] = []
    unresolved_linked_review_focus_ids = []
    seen_focus_ids: set[str] = set()

    if check_result.reporting_profile_summary is not None:
        for profile_id in check_result.reporting_profile_summary.applicable_profile_ids:
            try:
                payload = defaults_registry.get_reporting_profile_record(profile_id)
            except Exception:
                continue
            if payload["contaminantFamily"] != check_result.contaminant_family.value:
                continue
            reporting_profile_payloads.append(payload)

    for focus_id in check_result.normalized_projection.linked_review_focus_ids:
        if focus_id in seen_focus_ids:
            continue
        try:
            payload = defaults_registry.get_metals_review_focus_record(focus_id)
        except Exception:
            unresolved_linked_review_focus_ids.append(focus_id)
            continue
        if payload["contaminantFamily"] != check_result.contaminant_family.value:
            continue
        linked_review_focus_records.append(MetalsReviewFocusRecord.model_validate(payload))
        seen_focus_ids.add(focus_id)

    linked_review_focus_records = sorted(
        linked_review_focus_records,
        key=lambda record: (record.authority.lower(), record.focus_id),
    )
    occurrence_payloads = []
    seen_occurrence_ids: set[str] = set()
    for record in check_result.occurrence_evidence_records:
        for occurrence_id in record.occurrence_record_ids:
            if occurrence_id in seen_occurrence_ids:
                continue
            try:
                payload = defaults_registry.get_metals_occurrence_record(occurrence_id)
            except Exception:
                continue
            occurrence_payloads.append(payload)
            seen_occurrence_ids.add(occurrence_id)

    legal_limit_reviews = _build_legal_limit_reviews(
        defaults_registry,
        contaminant_family=check_result.contaminant_family,
        jurisdiction=check_result.jurisdiction,
        authority=check_result.authority,
        matrix_groups=sorted(
            {
                matrix_group
                for record in check_result.occurrence_evidence_records
                for matrix_group in record.matrix_groups
            }
            | {
                matrix_group
                for record in check_result.analytical_method_evidence_records
                for matrix_group in record.matrix_groups
            }
            | {
                matrix_group
                for payload in reporting_profile_payloads
                for matrix_group in payload.get("matrixGroups", [])
            }
        ),
    )

    review_prompts = [
        ContaminantMonitoringReviewPrompt(
            prompt_id=f"{occurrence['recordId']}.review_question_{index + 1}",
            category="occurrence_context",
            prompt=question,
            linked_record_id=occurrence["recordId"],
            linked_record_kind="occurrence_record",
        )
        for occurrence in occurrence_payloads
        for index, question in enumerate(occurrence.get("reviewQuestions", []))
    ] + [
        ContaminantMonitoringReviewPrompt(
            prompt_id=f"{focus.focus_id}.review_question_{index + 1}",
            category="review_focus",
            prompt=question,
            linked_record_id=focus.focus_id,
            linked_record_kind="review_focus_record",
        )
        for focus in linked_review_focus_records
        for index, question in enumerate(focus.review_questions)
    ] + [
        ContaminantMonitoringReviewPrompt(
            prompt_id=f"{record.record_id}.{field_name}",
            category="analytical_method_context",
            prompt=summary,
            linked_record_id=record.record_id,
            linked_record_kind="analytical_method_evidence_record",
        )
        for record in check_result.analytical_method_evidence_records
        for field_name, summary in [
            ("loq_summary", record.loq_summary),
            ("recovery_summary", record.recovery_summary),
            ("measurement_uncertainty_summary", record.measurement_uncertainty_summary),
            ("sampling_plan_summary", record.sampling_plan_summary),
            ("storage_stability_summary", record.storage_stability_summary),
        ]
        if summary
    ] + [
        ContaminantMonitoringReviewPrompt(
            prompt_id=f"quality_flag.{flag.code}",
            category="quality_flag",
            prompt=flag.message,
            linked_record_id=flag.code,
            linked_record_kind="quality_flag",
        )
        for flag in check_result.quality_flags
    ] + [
        ContaminantMonitoringReviewPrompt(
            prompt_id=f"legal_limit_scope.{_legal_limit_lane_key(review)}",
            category="legal_limit_scope",
            prompt=prompt,
            linked_record_id=_legal_limit_lane_key(review),
            linked_record_kind="contaminant_legal_limit_lane",
        )
        for review in legal_limit_reviews
        for prompt in [_legal_limit_scope_prompt(review)]
        if prompt is not None
    ]
    if check_result.reporting_profile_summary is not None:
        if check_result.reporting_profile_summary.recommended_primary_profile_ids:
            review_prompts.append(
                ContaminantMonitoringReviewPrompt(
                    prompt_id="reporting_profile.primary_selection",
                    category="reporting_convention",
                    prompt=(
                        "Confirm that the primary EU reporting profile remains the lead convention for this review and that any optional advisory profiles are carried only as supplementary outputs."
                    ),
                    linked_record_id=check_result.reporting_profile_summary.recommended_primary_profile_ids[0],
                    linked_record_kind="reporting_profile",
                )
            )
        for link in check_result.reporting_profile_summary.non_substitution_links:
            review_prompts.append(
                ContaminantMonitoringReviewPrompt(
                    prompt_id=f"reporting_profile.non_substitution.{link.profile_id}",
                    category="reporting_convention",
                    prompt=(
                        f"Do not substitute {link.profile_id} for {', '.join(link.not_substitutable_for_profile_ids)} in the current reporting package."
                    ),
                    linked_record_id=link.profile_id,
                    linked_record_kind="reporting_profile",
                )
            )

    referenced_resources = [
        ReviewResourceReference(
            role="documentation",
            uri="docs://contaminant-monitoring-interpretation",
            description="Operator documentation describing the contaminant monitoring interpretation bundle workflow.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="check_workflow_documentation",
            uri="docs://contaminant-monitoring-import",
            description="Operator documentation for contaminant monitoring import checks.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="occurrence_evidence_manifest",
            uri="occurrence-evidence://manifest",
            description="Governed occurrence-evidence manifest used to anchor contaminant monitoring review context.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="occurrence_evidence_family",
            uri=f"occurrence-evidence://family/{check_result.contaminant_family.value}",
            description="Family-specific occurrence-evidence records used in this monitoring interpretation bundle.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="analytical_method_evidence_manifest",
            uri="analytical-method-evidence://manifest",
            description="Governed analytical-method-evidence manifest used to anchor method-review context.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="analytical_method_evidence_family",
            uri=f"analytical-method-evidence://family/{check_result.contaminant_family.value}",
            description="Family-specific analytical-method-evidence records used in this monitoring interpretation bundle.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="occurrence_documentation",
            uri="docs://occurrence-evidence-registry",
            description="Operator documentation for governed occurrence-evidence records.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="analytical_method_documentation",
            uri="docs://analytical-method-evidence-registry",
            description="Operator documentation for governed analytical-method-evidence records.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="reporting_profiles_manifest",
            uri="reporting-profiles://manifest",
            description="Governed reporting-profile manifest covering primary EU and optional advisory reporting conventions.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="reporting_profiles_family",
            uri=f"reporting-profiles://family/{check_result.contaminant_family.value}",
            description="Family-specific governed reporting profiles considered during monitoring interpretation.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="reporting_profiles_documentation",
            uri="docs://reporting-profiles-registry",
            description="Operator guidance for governed reporting-profile usage and non-substitution posture.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="contaminant_legal_limits_manifest",
            uri="contaminant-legal-limits://manifest",
            description="Governed contaminant legal-limit manifest used to keep jurisdiction-specific legal-limit support explicit during monitoring review.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="contaminant_legal_limits_family",
            uri=f"contaminant-legal-limits://family/{check_result.contaminant_family.value}",
            description="Family-specific governed contaminant legal-limit records considered alongside the monitoring interpretation bundle.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="jurisdiction_coverage_manifest",
            uri="jurisdiction-coverage://manifest",
            description="Machine-readable jurisdiction-coverage manifest used to keep support depth explicit during monitoring review.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="jurisdiction_coverage_jurisdiction",
            uri=f"jurisdiction-coverage://jurisdiction/{check_result.jurisdiction}",
            description="Jurisdiction-scoped coverage posture used to avoid overreading partial or missing legal-limit support.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
    ]
    if check_result.jurisdiction:
        referenced_resources.append(
            ReviewResourceReference(
                role="contaminant_legal_limits_jurisdiction",
                uri=f"contaminant-legal-limits://jurisdiction/{check_result.jurisdiction}",
                description="Jurisdiction-scoped contaminant legal-limit records used to keep the monitoring review lane explicit.",
                confidentiality_tag=ConfidentialityTag.PUBLIC,
            )
        )
    if linked_review_focus_records:
        referenced_resources.extend(
            [
                ReviewResourceReference(
                    role="metals_review_focus_manifest",
                    uri="metals-review-focus://manifest",
                    description="Governed metals review-focus registry used to surface linked commodity and population follow-up context.",
                    confidentiality_tag=ConfidentialityTag.PUBLIC,
                ),
                ReviewResourceReference(
                    role="metals_review_focus_family",
                    uri=f"metals-review-focus://family/{check_result.contaminant_family.value}",
                    description="Family-specific review-focus records linked from the contaminant monitoring check result.",
                    confidentiality_tag=ConfidentialityTag.PUBLIC,
                ),
            ]
        )
    if check_result.contaminant_family != ContaminantFamily.PESTICIDE_RESIDUE:
        referenced_resources.append(
            ReviewResourceReference(
                role="emerging_family_governance",
                uri=f"emerging-contaminants://family/{check_result.contaminant_family.value}",
                description="Family-level evidence-maturity and submission-governance posture for this contaminant family.",
                confidentiality_tag=ConfidentialityTag.PUBLIC,
            )
        )

    notes = list(check_result.notes)
    if check_result.reporting_profile_summary is not None:
        notes.extend(check_result.reporting_profile_summary.notes)
    notes.append(
        "Interpretation bundle packages the contaminant monitoring check, governed evidence records, and reviewer prompts into one audit-ready object."
    )
    notes.append(
        "Bundle remains review-oriented and does not convert contaminant monitoring context into a native exposure or final decision engine."
    )
    if legal_limit_reviews:
        notes.append(
            "Attached legal-limit review snapshots make exact, partial, anchor-only, or missing jurisdiction support explicit instead of implying a complete legal-limit layer."
        )
    notes.extend(
        summary
        for summary in (_legal_limit_scope_summary(review) for review in legal_limit_reviews)
        if summary is not None
    )
    if unresolved_linked_review_focus_ids:
        notes.append(
            "Some linked review-focus ids could not be resolved from the governed defaults pack and should be reviewed before downstream interpretation."
        )
    if request.bundle_note:
        notes.append(request.bundle_note)

    uncertainty_and_assumption_ledger = build_contaminant_monitoring_bundle_ledger(
        check_ledger=check_result.uncertainty_and_assumption_ledger,
        unresolved_linked_review_focus_ids=sorted(unresolved_linked_review_focus_ids),
    )

    limitations = [
        LimitationNote(
            code="monitoring_interpretation_bundle_only",
            message="Bundle packages governed monitoring review context only and does not calculate contaminant exposure or risk.",
        )
    ]
    limitations.extend(
        _historical_context_limitations(
            defaults_registry,
            records=check_result.occurrence_evidence_records,
            record_kind_label="Occurrence-evidence record",
        )
    )
    limitations.extend(
        _historical_context_limitations(
            defaults_registry,
            records=check_result.analytical_method_evidence_records,
            record_kind_label="Analytical-method-evidence record",
        )
    )
    limitations.extend(
        limitation
        for limitation in (_legal_limit_scope_limitation(review) for review in legal_limit_reviews)
        if limitation is not None
    )

    return ContaminantMonitoringInterpretationBundle(
        bundle_profile=BundleProfile.INTERNAL_REVIEW,
        contaminant_family=check_result.contaminant_family,
        jurisdiction=check_result.jurisdiction,
        authority=check_result.authority,
        dataset_id=check_result.dataset_id,
        check_status=check_result.check_status,
        overall_submission_use=check_result.overall_submission_use,
        submission_candidate_allowed=check_result.submission_candidate_allowed,
        check_result=check_result,
        reporting_profile_summary=check_result.reporting_profile_summary,
        linked_review_focus_records=linked_review_focus_records,
        unresolved_linked_review_focus_ids=sorted(unresolved_linked_review_focus_ids),
        covered_source_ids=sorted(
            {source_id for record in check_result.occurrence_evidence_records for source_id in record.source_ids}
            | {source_id for record in check_result.analytical_method_evidence_records for source_id in record.source_ids}
            | {source_id for record in linked_review_focus_records for source_id in record.source_ids}
            | {source_id for payload in reporting_profile_payloads for source_id in payload.get("sourceIds", [])}
        ),
        covered_method_ids=sorted(
            {method_id for record in check_result.analytical_method_evidence_records for method_id in record.method_ids}
            | {method_id for record in linked_review_focus_records for method_id in record.method_ids}
        ),
        covered_legal_authority_ids=sorted(
            {
                authority_id
                for record in check_result.occurrence_evidence_records
                for authority_id in record.legal_authority_ids
            }
            | {
                authority_id
                for record in check_result.analytical_method_evidence_records
                for authority_id in record.legal_authority_ids
            }
            | {
                authority_id
                for record in linked_review_focus_records
                for authority_id in record.legal_authority_ids
            }
            | {
                authority_id
                for payload in reporting_profile_payloads
                for authority_id in payload.get("legalAuthorityIds", [])
            }
        ),
        covered_dataset_ids=sorted(
            {dataset_id for record in check_result.occurrence_evidence_records for dataset_id in record.dataset_ids}
            | {dataset_id for record in linked_review_focus_records for dataset_id in record.dataset_ids}
        ),
        covered_reference_value_record_ids=sorted(
            {
                record_id
                for record in check_result.occurrence_evidence_records
                for record_id in record.reference_value_record_ids
            }
            | {
                record_id
                for record in linked_review_focus_records
                for record_id in record.reference_value_record_ids
            }
            | {
                record_id
                for payload in reporting_profile_payloads
                for record_id in payload.get("referenceValueRecordIds", [])
            }
        ),
        legal_limit_reviews=legal_limit_reviews,
        uncertainty_and_assumption_ledger=uncertainty_and_assumption_ledger,
        review_prompts=review_prompts,
        recommended_sequence=[
            "review_header_resolution_and_quality_flags",
            "review_occurrence_evidence_context",
            "review_analytical_method_context",
            "review_linked_focus_records",
            "record_unresolved_limitations_before_downstream_use",
        ],
        referenced_resources=referenced_resources,
        dependencies=[
            DependencyDescriptor(name="dietary-mcp", version=VERSION, role="producer"),
            DependencyDescriptor(
                name="dietary_check_contaminant_monitoring_import",
                version=VERSION,
                role="check_workflow",
            ),
            DependencyDescriptor(
                name="dietary_lookup_occurrence_evidence",
                version=VERSION,
                role="occurrence_evidence_workflow",
            ),
            DependencyDescriptor(
                name="dietary_lookup_analytical_method_evidence",
                version=VERSION,
                role="analytical_method_evidence_workflow",
            ),
            DependencyDescriptor(
                name=check_result.contaminant_family.value,
                version=VERSION,
                role="contaminant_family",
            ),
        ],
        limitations=limitations,
        notes=notes,
    )


def export_metals_monitoring_interpretation_bundle(
    defaults_registry: DefaultsRegistry,
    request: ExportMetalsMonitoringInterpretationBundleRequest,
) -> MetalsMonitoringInterpretationBundle:
    occurrence_result = request.occurrence_result
    review_focus_result = request.review_focus_result

    if occurrence_result.contaminant_family != review_focus_result.contaminant_family:
        raise DietaryValidationError(
            code="metals_monitoring_bundle_family_mismatch",
            message="Metals monitoring interpretation bundle requires matching contaminant families.",
            suggestion="Build the bundle from occurrence and review-focus lookup results produced for the same metals family.",
        )
    if (
        occurrence_result.jurisdiction is not None
        and review_focus_result.jurisdiction is not None
        and occurrence_result.jurisdiction != review_focus_result.jurisdiction
    ):
        raise DietaryValidationError(
            code="metals_monitoring_bundle_jurisdiction_mismatch",
            message="Metals monitoring interpretation bundle requires matching jurisdictions when both inputs are specified.",
            suggestion="Use occurrence and review-focus lookup results derived from the same jurisdiction filter.",
        )
    if (
        occurrence_result.authority is not None
        and review_focus_result.authority is not None
        and occurrence_result.authority != review_focus_result.authority
    ):
        raise DietaryValidationError(
            code="metals_monitoring_bundle_authority_mismatch",
            message="Metals monitoring interpretation bundle requires matching authorities when both inputs are specified.",
            suggestion="Use occurrence and review-focus lookup results derived from the same authority filter.",
        )

    occurrence_records = sorted(
        occurrence_result.records,
        key=lambda record: (record.authority.lower(), record.record_id),
    )
    review_focus_records = sorted(
        review_focus_result.records,
        key=lambda record: (record.authority.lower(), record.focus_id),
    )

    occurrence_record_ids = {record.record_id for record in occurrence_records}
    linked_occurrence_record_ids = sorted(
        {
            occurrence_id
            for record in review_focus_records
            for occurrence_id in record.linked_occurrence_record_ids
        }
    )
    unresolved_linked_occurrence_record_ids = sorted(
        occurrence_id for occurrence_id in linked_occurrence_record_ids if occurrence_id not in occurrence_record_ids
    )
    legal_limit_reviews = _build_legal_limit_reviews(
        defaults_registry,
        contaminant_family=occurrence_result.contaminant_family,
        jurisdiction=occurrence_result.jurisdiction or review_focus_result.jurisdiction,
        authority=occurrence_result.authority or review_focus_result.authority,
    )

    review_prompts = [
        MetalsMonitoringReviewPrompt(
            prompt_id=f"{record.record_id}.review_question_{index + 1}",
            category="occurrence_context",
            prompt=question,
            linked_record_id=record.record_id,
            linked_record_kind="occurrence_record",
        )
        for record in occurrence_records
        for index, question in enumerate(record.review_questions)
    ] + [
        MetalsMonitoringReviewPrompt(
            prompt_id=f"{record.focus_id}.review_question_{index + 1}",
            category="commodity_focus",
            prompt=question,
            linked_record_id=record.focus_id,
            linked_record_kind="review_focus_record",
        )
        for record in review_focus_records
        for index, question in enumerate(record.review_questions)
    ] + [
        MetalsMonitoringReviewPrompt(
            prompt_id=f"legal_limit_scope.{_legal_limit_lane_key(review)}",
            category="legal_limit_scope",
            prompt=prompt,
            linked_record_id=_legal_limit_lane_key(review),
            linked_record_kind="contaminant_legal_limit_lane",
        )
        for review in legal_limit_reviews
        for prompt in [_legal_limit_scope_prompt(review)]
        if prompt is not None
    ]

    referenced_resources = [
        ReviewResourceReference(
            role="metals_occurrence_manifest",
            uri="metals-occurrence://manifest",
            description="Governed metals-occurrence registry used to provide monitoring and occurrence context.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="metals_occurrence_family",
            uri=f"metals-occurrence://family/{occurrence_result.contaminant_family.value}",
            description="Family-specific metals-occurrence records used in the interpretation bundle.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="metals_review_focus_manifest",
            uri="metals-review-focus://manifest",
            description="Governed metals review-focus registry used to provide commodity and population review prompts.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="metals_review_focus_family",
            uri=f"metals-review-focus://family/{review_focus_result.contaminant_family.value}",
            description="Family-specific metals review-focus records used in the interpretation bundle.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="documentation",
            uri="docs://metals-monitoring-interpretation",
            description="Operator documentation describing the metals monitoring interpretation bundle workflow.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="occurrence_documentation",
            uri="docs://metals-occurrence-registry",
            description="Operator documentation for governed metals-occurrence records.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="review_focus_documentation",
            uri="docs://metals-review-focus-registry",
            description="Operator documentation for governed metals review-focus records.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="contaminant_legal_limits_manifest",
            uri="contaminant-legal-limits://manifest",
            description="Governed contaminant legal-limit manifest used to keep legal-limit support depth explicit during metals monitoring review.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="contaminant_legal_limits_family",
            uri=f"contaminant-legal-limits://family/{occurrence_result.contaminant_family.value}",
            description="Family-specific governed contaminant legal-limit records reviewed alongside the metals monitoring bundle.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
        ReviewResourceReference(
            role="jurisdiction_coverage_manifest",
            uri="jurisdiction-coverage://manifest",
            description="Machine-readable jurisdiction coverage manifest used to keep coverage depth explicit during metals monitoring review.",
            confidentiality_tag=ConfidentialityTag.PUBLIC,
        ),
    ]
    jurisdiction_for_resources = occurrence_result.jurisdiction or review_focus_result.jurisdiction
    if jurisdiction_for_resources:
        referenced_resources.extend(
            [
                ReviewResourceReference(
                    role="contaminant_legal_limits_jurisdiction",
                    uri=f"contaminant-legal-limits://jurisdiction/{jurisdiction_for_resources}",
                    description="Jurisdiction-scoped contaminant legal-limit records considered during metals monitoring review.",
                    confidentiality_tag=ConfidentialityTag.PUBLIC,
                ),
                ReviewResourceReference(
                    role="jurisdiction_coverage_jurisdiction",
                    uri=f"jurisdiction-coverage://jurisdiction/{jurisdiction_for_resources}",
                    description="Jurisdiction-scoped coverage posture used to keep legal-limit support limits explicit during review.",
                    confidentiality_tag=ConfidentialityTag.PUBLIC,
                ),
            ]
        )
    if occurrence_result.contaminant_family != ContaminantFamily.PESTICIDE_RESIDUE:
        referenced_resources.append(
            ReviewResourceReference(
                role="emerging_family_governance",
                uri=f"emerging-contaminants://family/{occurrence_result.contaminant_family.value}",
                description="Governed family-level readiness and evidence-maturity posture for this metals family.",
                confidentiality_tag=ConfidentialityTag.PUBLIC,
            )
        )

    notes = []
    notes.extend(occurrence_result.notes)
    notes.extend(review_focus_result.notes)
    notes.append(
        "Interpretation bundle combines governed occurrence context and commodity-focus review prompts without implying a native quantitative metals exposure engine."
    )
    notes.append(
        "Bundle is suitable for reviewer triage, monitoring interpretation, and audit support only; final regulatory conclusions remain expert decisions."
    )
    if legal_limit_reviews:
        notes.append(
            "Attached legal-limit review snapshots keep family-level jurisdiction support explicit so missing or partial legal-limit coverage is not mistaken for a complete decision layer."
        )
    notes.extend(
        summary
        for summary in (_legal_limit_scope_summary(review) for review in legal_limit_reviews)
        if summary is not None
    )
    if unresolved_linked_occurrence_record_ids:
        notes.append(
            "Some review-focus records link to occurrence records that were not present in the supplied occurrence result; widen the occurrence filters if full linkage is required."
        )
    if request.bundle_note:
        notes.append(request.bundle_note)

    overall_submission_use = _aggregate_submission_use(
        [occurrence_result.overall_submission_use, review_focus_result.overall_submission_use]
    )
    uncertainty_and_assumption_ledger = build_metals_monitoring_bundle_ledger(
        contaminant_family=occurrence_result.contaminant_family,
        occurrence_records=occurrence_records,
        review_focus_records=review_focus_records,
        unresolved_linked_occurrence_record_ids=unresolved_linked_occurrence_record_ids,
        overall_submission_use=overall_submission_use,
        submission_candidate_allowed=(
            occurrence_result.submission_candidate_allowed and review_focus_result.submission_candidate_allowed
        ),
    )

    limitations = [
        LimitationNote(
            code="monitoring_interpretation_bundle_only",
            message="Bundle packages monitoring and review context only and does not calculate contaminant exposure or risk.",
        )
    ]
    limitations.extend(
        _historical_context_limitations(
            defaults_registry,
            records=occurrence_records,
            record_kind_label="Metals-occurrence record",
        )
    )
    limitations.extend(
        limitation
        for limitation in (_legal_limit_scope_limitation(review) for review in legal_limit_reviews)
        if limitation is not None
    )

    return MetalsMonitoringInterpretationBundle(
        bundle_profile=BundleProfile.INTERNAL_REVIEW,
        contaminant_family=occurrence_result.contaminant_family,
        jurisdiction=occurrence_result.jurisdiction or review_focus_result.jurisdiction,
        authority=occurrence_result.authority or review_focus_result.authority,
        overall_submission_use=overall_submission_use,
        submission_candidate_allowed=(
            occurrence_result.submission_candidate_allowed and review_focus_result.submission_candidate_allowed
        ),
        occurrence_records=occurrence_records,
        review_focus_records=review_focus_records,
        linked_occurrence_record_ids=linked_occurrence_record_ids,
        unresolved_linked_occurrence_record_ids=unresolved_linked_occurrence_record_ids,
        priority_food_groups=sorted(
            {food_group for record in occurrence_records for food_group in record.priority_food_groups}
        ),
        high_attention_foods=sorted(
            {food for record in occurrence_records for food in record.high_attention_foods}
        ),
        focus_foods=sorted({food for record in review_focus_records for food in record.focus_foods}),
        sensitive_population_groups=sorted(
            {
                group
                for record in occurrence_records
                for group in record.sensitive_population_groups
            }
            | {
                group
                for record in review_focus_records
                for group in record.sensitive_population_groups
            }
        ),
        trend_signals=sorted({signal for record in occurrence_records for signal in record.trend_signals}),
        covered_source_ids=sorted(
            {source_id for record in occurrence_records for source_id in record.source_ids}
            | {source_id for record in review_focus_records for source_id in record.source_ids}
        ),
        covered_method_ids=sorted(
            {method_id for record in occurrence_records for method_id in record.method_ids}
            | {method_id for record in review_focus_records for method_id in record.method_ids}
        ),
        covered_legal_authority_ids=sorted(
            {authority_id for record in occurrence_records for authority_id in record.legal_authority_ids}
            | {authority_id for record in review_focus_records for authority_id in record.legal_authority_ids}
        ),
        covered_dataset_ids=sorted(
            {dataset_id for record in occurrence_records for dataset_id in record.dataset_ids}
            | {dataset_id for record in review_focus_records for dataset_id in record.dataset_ids}
        ),
        covered_reference_value_record_ids=sorted(
            {
                record_id
                for record in occurrence_records
                for record_id in record.reference_value_record_ids
            }
            | {
                record_id
                for record in review_focus_records
                for record_id in record.reference_value_record_ids
            }
        ),
        legal_limit_reviews=legal_limit_reviews,
        uncertainty_and_assumption_ledger=uncertainty_and_assumption_ledger,
        review_prompts=review_prompts,
        recommended_sequence=[
            "review_occurrence_context",
            "review_priority_food_groups",
            "review_sensitive_populations",
            "review_commodity_focus_prompts",
            "review_governance_links",
        ],
        referenced_resources=referenced_resources,
        dependencies=[
            DependencyDescriptor(name="dietary-mcp", version=VERSION, role="producer"),
            DependencyDescriptor(
                name="dietary_lookup_metals_occurrence",
                version=VERSION,
                role="occurrence_workflow",
            ),
            DependencyDescriptor(
                name="dietary_lookup_metals_review_focus",
                version=VERSION,
                role="review_focus_workflow",
            ),
            DependencyDescriptor(
                name=occurrence_result.contaminant_family.value,
                version=VERSION,
                role="contaminant_family",
            ),
        ],
        limitations=limitations,
        notes=notes,
    )
