from __future__ import annotations

from dietary_mcp.models import (
    AnalyticalMethodEvidenceRecord,
    ContaminantFamily,
    MetalsOccurrenceRecord,
    MetalsReviewFocusRecord,
    OccurrenceEvidenceRecord,
    ReadinessStatus,
    ScientificLedgerEntry,
    ScientificLedgerEntryKind,
    Severity,
    SubmissionUse,
)


def _add_entry(
    entries: list[ScientificLedgerEntry],
    entry: ScientificLedgerEntry,
) -> None:
    if any(item.entry_id == entry.entry_id for item in entries):
        return
    entries.append(entry)


def _governance_summary(
    contaminant_family: ContaminantFamily,
    overall_submission_use: SubmissionUse,
    submission_candidate_allowed: bool,
) -> str:
    if submission_candidate_allowed and overall_submission_use == SubmissionUse.ALLOWED:
        return "Submission posture is governed as allowed."
    if overall_submission_use == SubmissionUse.NOT_ALLOWED:
        return (
            f"{contaminant_family.value} remains governed as not allowed for submission-oriented use and must stay "
            "in internal or exploratory review."
        )
    return (
        f"{contaminant_family.value} remains governed as review_required and should stay in reviewer-controlled "
        "internal workflows."
    )


def build_scientific_ledger_action_specs(
    *,
    ledger: list[ScientificLedgerEntry],
    skip_entry_ids: set[str] | None = None,
) -> list[dict]:
    skip = skip_entry_ids or set()
    specs: list[dict] = []

    for entry in ledger:
        if entry.entry_id in skip:
            continue
        priority = (
            ReadinessStatus.FAIL
            if entry.severity == Severity.ERROR
            else ReadinessStatus.REVIEW_REQUIRED
        )
        specs.append(
            {
                "actionId": f"review_scientific_ledger.{entry.entry_id}",
                "category": f"scientific_ledger_{entry.entry_kind.value}",
                "title": f"Review {entry.category.replace('_', ' ')} ledger entry",
                "priority": priority,
                "blocking": (
                    entry.entry_kind == ScientificLedgerEntryKind.DATA_GAP
                    and priority == ReadinessStatus.FAIL
                ),
                "summary": (
                    f"{entry.summary} Keep the governed scientific ledger rationale explicit in reviewer signoff."
                ),
                "linkedRecordIds": [entry.entry_id, *entry.linked_record_ids],
            }
        )

    return specs


def build_contaminant_monitoring_check_ledger(
    *,
    contaminant_family: ContaminantFamily,
    row_count: int,
    rows_with_lod: int,
    rows_with_loq: int,
    rows_with_recovery_percent: int,
    rows_with_measurement_uncertainty_percent: int,
    sampling_years: list[int],
    occurrence_records: list[OccurrenceEvidenceRecord],
    analytical_method_records: list[AnalyticalMethodEvidenceRecord],
    overall_submission_use: SubmissionUse,
    submission_candidate_allowed: bool,
    dataset_declared: bool,
    dataset_linked: bool,
) -> list[ScientificLedgerEntry]:
    entries: list[ScientificLedgerEntry] = []

    if overall_submission_use != SubmissionUse.ALLOWED or not submission_candidate_allowed:
        _add_entry(
            entries,
            ScientificLedgerEntry(
                entry_id="governance_submission_posture",
                entry_kind=ScientificLedgerEntryKind.GOVERNANCE_LIMIT,
                category="governance",
                severity=Severity.WARNING,
                summary="Governance posture remains below submission-capable use.",
                rationale=_governance_summary(
                    contaminant_family,
                    overall_submission_use,
                    submission_candidate_allowed,
                ),
                linked_record_ids=[
                    *(record.record_id for record in occurrence_records),
                    *(record.record_id for record in analytical_method_records),
                ],
                source_ids=sorted(
                    {
                        source_id
                        for record in occurrence_records
                        for source_id in record.source_ids
                    }
                    | {
                        source_id
                        for record in analytical_method_records
                        for source_id in record.source_ids
                    }
                ),
            ),
        )

    for field_name, observed_count, summary, rationale, severity in [
        (
            "lod",
            rows_with_lod,
            "Row-level LOD coverage is incomplete.",
            "Detection-limit context should be reviewed against the linked analytical-method evidence rather than "
            "assumed from the CSV alone.",
            Severity.WARNING,
        ),
        (
            "loq",
            rows_with_loq,
            "Row-level LOQ coverage is incomplete.",
            "Quantification-limit context should be reviewed against the linked analytical-method evidence rather than "
            "assumed from the CSV alone.",
            Severity.WARNING,
        ),
        (
            "recovery_percent",
            rows_with_recovery_percent,
            "Row-level recovery coverage is incomplete.",
            "Recovery values are not available for every row and analytical interpretation should remain tied to the "
            "governed method evidence.",
            Severity.INFO,
        ),
        (
            "measurement_uncertainty_percent",
            rows_with_measurement_uncertainty_percent,
            "Row-level measurement-uncertainty coverage is incomplete.",
            "Measurement uncertainty is missing for at least one row and should not be inferred beyond the linked "
            "method context.",
            Severity.INFO,
        ),
    ]:
        if row_count == 0 or observed_count >= row_count:
            continue
        entry_kind = (
            ScientificLedgerEntryKind.DATA_GAP
            if observed_count == 0
            else ScientificLedgerEntryKind.UNCERTAINTY
        )
        _add_entry(
            entries,
            ScientificLedgerEntry(
                entry_id=f"row_level_{field_name}_coverage",
                entry_kind=entry_kind,
                category="analytical_measurement",
                severity=severity,
                summary=summary,
                rationale=f"{observed_count} of {row_count} rows supplied `{field_name}` values. {rationale}",
                conservative=None,
                affected_fields=[field_name],
                linked_record_ids=[record.record_id for record in analytical_method_records],
                source_ids=sorted(
                    {
                        source_id
                        for record in analytical_method_records
                        for source_id in record.source_ids
                    }
                ),
            ),
        )

    if not sampling_years and row_count:
        _add_entry(
            entries,
            ScientificLedgerEntry(
                entry_id="sampling_years_missing",
                entry_kind=ScientificLedgerEntryKind.DATA_GAP,
                category="sampling_context",
                severity=Severity.INFO,
                summary="Sampling years were not supplied in the monitoring table.",
                rationale="Temporal interpretation should remain tied to the governed occurrence and method evidence "
                "instead of inferred from the CSV rows.",
                affected_fields=["sampling_year"],
                linked_record_ids=[record.record_id for record in occurrence_records],
                source_ids=sorted(
                    {
                        source_id
                        for record in occurrence_records
                        for source_id in record.source_ids
                    }
                ),
            ),
        )

    if dataset_declared and not dataset_linked:
        _add_entry(
            entries,
            ScientificLedgerEntry(
                entry_id="declared_dataset_not_linked",
                entry_kind=ScientificLedgerEntryKind.DATA_GAP,
                category="dataset_linkage",
                severity=Severity.WARNING,
                summary="Declared dataset id is not linked by the matched occurrence evidence.",
                rationale="Dataset alignment should be reviewed before downstream interpretation because the declared "
                "dataset could not be confirmed from the governed occurrence-evidence records.",
                affected_fields=["dataset_id"],
                linked_record_ids=[record.record_id for record in occurrence_records],
                source_ids=sorted(
                    {
                        source_id
                        for record in occurrence_records
                        for source_id in record.source_ids
                    }
                ),
            ),
        )

    for record in occurrence_records:
        if record.lower_bound_handling:
            _add_entry(
                entries,
                ScientificLedgerEntry(
                    entry_id=f"lower_bound_handling.{record.record_id}",
                    entry_kind=ScientificLedgerEntryKind.ASSUMPTION,
                    category="occurrence_data",
                    severity=Severity.INFO,
                    summary="Lower-bound handling is governed by linked occurrence evidence.",
                    rationale=record.lower_bound_handling,
                    conservative=True,
                    affected_fields=["result_value", "lod", "loq"],
                    linked_record_ids=[record.record_id],
                    source_ids=record.source_ids,
                ),
            )

    for record in analytical_method_records:
        if record.storage_stability_summary:
            _add_entry(
                entries,
                ScientificLedgerEntry(
                    entry_id=f"storage_stability.{record.record_id}",
                    entry_kind=ScientificLedgerEntryKind.UNCERTAINTY,
                    category="analytical_method",
                    severity=Severity.INFO,
                    summary="Storage-stability interpretation relies on governed analytical-method context.",
                    rationale=record.storage_stability_summary,
                    linked_record_ids=[record.record_id],
                    source_ids=record.source_ids,
                ),
            )
        if record.sampling_plan_summary:
            _add_entry(
                entries,
                ScientificLedgerEntry(
                    entry_id=f"sampling_plan.{record.record_id}",
                    entry_kind=ScientificLedgerEntryKind.ASSUMPTION,
                    category="sampling_context",
                    severity=Severity.INFO,
                    summary="Sampling-plan interpretation relies on governed analytical-method context.",
                    rationale=record.sampling_plan_summary,
                    linked_record_ids=[record.record_id],
                    source_ids=record.source_ids,
                ),
            )

    return entries


def build_contaminant_monitoring_bundle_ledger(
    *,
    check_ledger: list[ScientificLedgerEntry],
    unresolved_linked_review_focus_ids: list[str],
) -> list[ScientificLedgerEntry]:
    entries = [item.model_copy(deep=True) for item in check_ledger]
    if unresolved_linked_review_focus_ids:
        _add_entry(
            entries,
            ScientificLedgerEntry(
                entry_id="unresolved_review_focus_linkage",
                entry_kind=ScientificLedgerEntryKind.DATA_GAP,
                category="review_focus",
                severity=Severity.WARNING,
                summary="Some linked review-focus records were not resolved.",
                rationale="The interpretation bundle keeps unresolved linked review-focus ids explicit so downstream "
                "review does not assume the commodity- or population-focus context is complete.",
                affected_fields=["linked_review_focus_ids"],
                linked_record_ids=unresolved_linked_review_focus_ids,
            ),
        )
    return entries


def build_metals_monitoring_bundle_ledger(
    *,
    contaminant_family: ContaminantFamily,
    occurrence_records: list[MetalsOccurrenceRecord],
    review_focus_records: list[MetalsReviewFocusRecord],
    unresolved_linked_occurrence_record_ids: list[str],
    overall_submission_use: SubmissionUse,
    submission_candidate_allowed: bool,
) -> list[ScientificLedgerEntry]:
    entries: list[ScientificLedgerEntry] = []

    if overall_submission_use != SubmissionUse.ALLOWED or not submission_candidate_allowed:
        _add_entry(
            entries,
            ScientificLedgerEntry(
                entry_id="governance_submission_posture",
                entry_kind=ScientificLedgerEntryKind.GOVERNANCE_LIMIT,
                category="governance",
                severity=Severity.WARNING,
                summary="Metals monitoring governance remains below submission-capable use.",
                rationale=_governance_summary(
                    contaminant_family,
                    overall_submission_use,
                    submission_candidate_allowed,
                ),
                linked_record_ids=[
                    *(record.record_id for record in occurrence_records),
                    *(record.focus_id for record in review_focus_records),
                ],
                source_ids=sorted(
                    {
                        source_id
                        for record in occurrence_records
                        for source_id in record.source_ids
                    }
                    | {
                        source_id
                        for record in review_focus_records
                        for source_id in record.source_ids
                    }
                ),
            ),
        )

    for record in occurrence_records:
        rationale_parts = [f"Occurrence kind: {record.occurrence_kind}."]
        if record.priority_food_groups:
            rationale_parts.append(
                "Priority food groups: " + ", ".join(record.priority_food_groups[:3]) + "."
            )
        if record.notes:
            rationale_parts.append(record.notes[0])
        _add_entry(
            entries,
            ScientificLedgerEntry(
                entry_id=f"monitoring_context.{record.record_id}",
                entry_kind=ScientificLedgerEntryKind.ASSUMPTION,
                category="occurrence_data",
                severity=Severity.INFO,
                summary="Occurrence interpretation relies on governed monitoring-support context.",
                rationale=" ".join(part for part in rationale_parts if part),
                linked_record_ids=[record.record_id],
                source_ids=record.source_ids,
            ),
        )

    if any(record.sensitive_population_groups for record in review_focus_records):
        _add_entry(
            entries,
            ScientificLedgerEntry(
                entry_id="sensitive_population_prompt_context",
                entry_kind=ScientificLedgerEntryKind.ASSUMPTION,
                category="sensitive_population_context",
                severity=Severity.INFO,
                summary="Sensitive-population focus remains prompt-based review context.",
                rationale="Sensitive-population groups in the metals bundle surface reviewer follow-up priorities and "
                "do not create subgroup-specific exposure calculations inside Dietary MCP.",
                linked_record_ids=[record.focus_id for record in review_focus_records],
                source_ids=sorted(
                    {
                        source_id
                        for record in review_focus_records
                        for source_id in record.source_ids
                    }
                ),
            ),
        )

    if any(record.trend_signals for record in occurrence_records):
        _add_entry(
            entries,
            ScientificLedgerEntry(
                entry_id="trend_signal_context",
                entry_kind=ScientificLedgerEntryKind.UNCERTAINTY,
                category="trend_signal",
                severity=Severity.INFO,
                summary="Trend signals remain qualitative review cues.",
                rationale="Trend signals in the governed metals occurrence records support reviewer attention but do "
                "not create a time-series inference or automated trend model.",
                linked_record_ids=[record.record_id for record in occurrence_records],
                source_ids=sorted(
                    {
                        source_id
                        for record in occurrence_records
                        for source_id in record.source_ids
                    }
                ),
            ),
        )

    if unresolved_linked_occurrence_record_ids:
        _add_entry(
            entries,
            ScientificLedgerEntry(
                entry_id="unresolved_occurrence_linkage",
                entry_kind=ScientificLedgerEntryKind.DATA_GAP,
                category="review_focus",
                severity=Severity.WARNING,
                summary="Some review-focus records link to occurrence records outside the supplied occurrence result.",
                rationale="Occurrence filters may be too narrow for complete linkage and should be widened before "
                "treating the metals monitoring context as fully covered.",
                linked_record_ids=unresolved_linked_occurrence_record_ids,
            ),
        )

    return entries
