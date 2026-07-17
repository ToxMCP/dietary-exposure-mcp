from __future__ import annotations

import csv
import io
import re
from typing import Iterable
from typing import TYPE_CHECKING

from dietary_mcp.models import (
    AnalyticalMethodEvidenceRecord,
    CheckContaminantMonitoringImportRequest,
    ContaminantMonitoringHeaderResolution,
    ContaminantMonitoringImportCheckResult,
    ContaminantMonitoringNormalizedProjection,
    OccurrenceEvidenceRecord,
    QualityFlag,
    ReadinessStatus,
    ReportingProfileApplicabilitySummary,
    ReportingProfileNonSubstitutionLink,
    ReportingProfileRecord,
    ReportingProfileRole,
    ReviewResourceReference,
    Severity,
    SubmissionUse,
)
from dietary_mcp.scientific_ledger import build_contaminant_monitoring_check_ledger

if TYPE_CHECKING:
    from dietary_mcp.runtime import DietaryRuntime


HEADER_ALIASES = {
    "commodity": {"commodity", "food", "matrix", "product", "food_item", "fooditem"},
    "analyte": {"analyte", "substance", "contaminant", "compound"},
    "result_value": {"result", "concentration", "result_value", "measured_value", "level"},
    "unit": {"unit", "result_unit", "concentration_unit"},
    "sample_id": {"sample_id", "sample", "sample_code"},
    "lod": {"lod", "lod_value"},
    "loq": {"loq", "loq_value"},
    "recovery_percent": {"recovery", "recovery_percent"},
    "measurement_uncertainty_percent": {
        "measurement_uncertainty",
        "measurement_uncertainty_percent",
        "uncertainty_percent",
    },
    "sampling_year": {"sampling_year", "year"},
}

REQUIRED_CANONICAL_FIELDS = {"commodity", "analyte", "result_value", "unit"}


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _parse_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    return float(value.strip())


def _parse_int(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    return int(float(value.strip()))


def _canonicalize_headers(headers: Iterable[str]) -> tuple[dict[str, str], list[ContaminantMonitoringHeaderResolution]]:
    mapping: dict[str, str] = {}
    resolutions: list[ContaminantMonitoringHeaderResolution] = []
    for header in headers:
        normalized = _normalize_text(header)
        canonical_field = None
        for candidate, aliases in HEADER_ALIASES.items():
            if normalized == candidate or normalized in aliases:
                canonical_field = candidate
                break
        if canonical_field is not None and canonical_field not in mapping.values():
            mapping[header] = canonical_field
        resolutions.append(
            ContaminantMonitoringHeaderResolution(
                header=header,
                canonical_field=canonical_field,
                recognized=canonical_field is not None,
            )
        )
    return mapping, resolutions


def _matches_any(values: Iterable[str], target: str) -> bool:
    normalized_target = _normalize_text(target)
    return any(_normalize_text(value) == normalized_target or _normalize_text(value) in normalized_target for value in values)


def _matches_reporting_profile_matrix_groups(matrix_groups: Iterable[str], commodity: str) -> bool:
    if _matches_any(matrix_groups, commodity):
        return True
    normalized_commodity = _normalize_text(commodity)
    normalized_groups = {_normalize_text(group) for group in matrix_groups}
    if any(token in normalized_commodity for token in ("fish", "seafood")):
        return "fish_and_seafood" in normalized_groups
    if any(token in normalized_commodity for token in ("egg", "eggs")):
        return "eggs" in normalized_groups
    if any(token in normalized_commodity for token in ("offal", "liver", "kidney", "giblet", "giblets")):
        return "offal" in normalized_groups
    return False


def _match_evidence_matrix_groups(matrix_groups: Iterable[str], commodity: str) -> tuple[bool, bool]:
    normalized_groups = {_normalize_text(group) for group in matrix_groups}
    if _matches_reporting_profile_matrix_groups(matrix_groups, commodity):
        return True, False
    if "broad_food_supply" in normalized_groups:
        return True, True
    return False, False


def _aggregate_submission_use(values: list[SubmissionUse]) -> SubmissionUse:
    if not values:
        return SubmissionUse.REVIEW_REQUIRED
    if any(value == SubmissionUse.NOT_ALLOWED for value in values):
        return SubmissionUse.NOT_ALLOWED
    if any(value == SubmissionUse.REVIEW_REQUIRED for value in values):
        return SubmissionUse.REVIEW_REQUIRED
    return SubmissionUse.ALLOWED


def _append_currency_context(
    runtime: DietaryRuntime,
    *,
    records: list[OccurrenceEvidenceRecord] | list[AnalyticalMethodEvidenceRecord],
    record_kind_label: str,
    quality_flag_prefix: str,
    notes: list[str],
    quality_flags: list[QualityFlag],
) -> None:
    historical_record_ids: list[str] = []
    for record in records:
        assessment = runtime.defaults.assess_source_currency(
            source_ids=record.source_ids,
            data_period=getattr(record, "data_period", None),
        )
        for note in assessment.notes:
            notes.append(f"{record_kind_label} {record.record_id}: {note}")
        if assessment.historical_data_period:
            historical_record_ids.append(record.record_id)
            quality_flags.append(
                QualityFlag(
                    code=f"{quality_flag_prefix}_historical_data_period.{record.record_id}",
                    severity=Severity.WARNING,
                    message=(
                        f"{record_kind_label} {record.record_id} uses data period `{assessment.data_period}` ending in "
                        f"{assessment.data_period_end_year}, which is historical relative to {assessment.reference_date.isoformat()}."
                    ),
                )
            )
        elif assessment.review_required:
            historical_record_ids.append(record.record_id)
            quality_flags.append(
                QualityFlag(
                    code=f"{quality_flag_prefix}_historical_context.{record.record_id}",
                    severity=Severity.WARNING,
                    message=(
                        f"{record_kind_label} {record.record_id} relies on historical supporting sources "
                        f"({', '.join(assessment.historical_source_ids)}) as of {assessment.reference_date.isoformat()}."
                    ),
                )
            )
        elif assessment.historical_source_ids:
            notes.append(
                f"{record_kind_label} {record.record_id} still depends on older supporting sources ({', '.join(assessment.historical_source_ids)}) even though newer context records are also linked."
            )
    if historical_record_ids:
        notes.append(
            f"Historical data context was detected in the matched {record_kind_label.lower()} set ({', '.join(sorted(historical_record_ids))}); keep the interpretation review-oriented until currency is explicitly accepted."
        )


def _linked_metals_occurrence_payloads(
    runtime: DietaryRuntime,
    records: list[OccurrenceEvidenceRecord],
) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for record in records:
        for occurrence_id in record.occurrence_record_ids:
            if occurrence_id in seen_ids:
                continue
            payload = runtime.defaults.get_metals_occurrence_record(occurrence_id)
            if payload is None:
                continue
            seen_ids.add(occurrence_id)
            payloads.append(payload)
    return payloads


def _filter_occurrence_records(
    runtime: DietaryRuntime,
    request: CheckContaminantMonitoringImportRequest,
    analytes: set[str],
    commodities: set[str],
) -> tuple[list[OccurrenceEvidenceRecord], list[str], list[str]]:
    notes: list[str] = []
    records = []
    broad_fallback_record_ids: set[str] = set()
    available = runtime.defaults.list_occurrence_evidence_records()
    if request.occurrence_evidence_record_ids:
        selected_ids = set(request.occurrence_evidence_record_ids)
        for item in available:
            if item["recordId"] in selected_ids:
                records.append(OccurrenceEvidenceRecord.model_validate(item))
        missing = sorted(selected_ids.difference({record.record_id for record in records}))
        if missing:
            notes.append(f"Requested occurrence-evidence ids were not resolved: {missing}.")
    else:
        for item in available:
            if item["contaminantFamily"] != request.contaminant_family.value:
                continue
            if item["jurisdiction"].strip().lower() != request.jurisdiction.strip().lower():
                continue
            if request.authority and item["authority"].strip().lower() != request.authority.strip().lower():
                continue
            if analytes and not any(_normalize_text(analyte) in analytes for analyte in item["analytes"]):
                continue
            broad_used = False
            commodity_match = False
            for commodity in commodities:
                matched, used_broad_fallback = _match_evidence_matrix_groups(item["matrixGroups"], commodity)
                broad_used = broad_used or used_broad_fallback
                commodity_match = commodity_match or matched
            if commodities and not commodity_match:
                continue
            if broad_used:
                broad_fallback_record_ids.add(item["recordId"])
            records.append(OccurrenceEvidenceRecord.model_validate(item))
    if request.dataset_id is not None:
        dataset_records = [record for record in records if request.dataset_id in record.dataset_ids]
        if dataset_records:
            records = dataset_records
        else:
            notes.append(f"Declared dataset id {request.dataset_id} was not linked by the matched occurrence evidence.")
    records.sort(key=lambda record: (record.authority.lower(), record.record_id))
    return records, notes, sorted(broad_fallback_record_ids)


def _filter_analytical_method_records(
    runtime: DietaryRuntime,
    request: CheckContaminantMonitoringImportRequest,
    analytes: set[str],
    commodities: set[str],
) -> tuple[list[AnalyticalMethodEvidenceRecord], list[str], list[str]]:
    notes: list[str] = []
    records = []
    broad_fallback_record_ids: set[str] = set()
    available = runtime.defaults.list_analytical_method_evidence_records()
    if request.analytical_method_evidence_record_ids:
        selected_ids = set(request.analytical_method_evidence_record_ids)
        for item in available:
            if item["recordId"] in selected_ids:
                records.append(AnalyticalMethodEvidenceRecord.model_validate(item))
        missing = sorted(selected_ids.difference({record.record_id for record in records}))
        if missing:
            notes.append(f"Requested analytical-method-evidence ids were not resolved: {missing}.")
    else:
        for item in available:
            if item["contaminantFamily"] != request.contaminant_family.value:
                continue
            if item["jurisdiction"].strip().lower() != request.jurisdiction.strip().lower():
                continue
            if request.authority and item["authority"].strip().lower() != request.authority.strip().lower():
                continue
            if analytes and not any(_normalize_text(analyte) in analytes for analyte in item["analytes"]):
                continue
            broad_used = False
            commodity_match = False
            for commodity in commodities:
                matched, used_broad_fallback = _match_evidence_matrix_groups(item["matrixGroups"], commodity)
                broad_used = broad_used or used_broad_fallback
                commodity_match = commodity_match or matched
            if commodities and not commodity_match:
                continue
            if broad_used:
                broad_fallback_record_ids.add(item["recordId"])
            records.append(AnalyticalMethodEvidenceRecord.model_validate(item))
    records.sort(key=lambda record: (record.authority.lower(), record.record_id))
    return records, notes, sorted(broad_fallback_record_ids)


def build_contaminant_monitoring_import_check_result(
    runtime: DietaryRuntime,
    request: CheckContaminantMonitoringImportRequest,
) -> ContaminantMonitoringImportCheckResult:
    reader = csv.DictReader(io.StringIO(request.csv_text))
    headers = reader.fieldnames or []
    header_mapping, header_resolution = _canonicalize_headers(headers)
    missing_fields = sorted(REQUIRED_CANONICAL_FIELDS.difference(header_mapping.values()))

    quality_flags: list[QualityFlag] = []
    notes = [
        "Contaminant monitoring import checks validate supplied CSV text against governed occurrence and analytical-method evidence objects.",
        "This workflow is review-oriented and does not create a native contaminant exposure engine or final regulatory decision.",
    ]

    if missing_fields:
        quality_flags.append(
            QualityFlag(
                code="missing_required_monitoring_headers",
                severity=Severity.ERROR,
                message=f"Required monitoring headers were not resolved: {missing_fields}.",
            )
        )
        return ContaminantMonitoringImportCheckResult(
            check_status=ReadinessStatus.FAIL,
            contaminant_family=request.contaminant_family,
            jurisdiction=request.jurisdiction,
            authority=request.authority,
            dataset_id=request.dataset_id,
            overall_submission_use=SubmissionUse.REVIEW_REQUIRED,
            submission_candidate_allowed=False,
            header_resolution=header_resolution,
            normalized_projection=ContaminantMonitoringNormalizedProjection(
                row_count=0,
                analytes=[],
                commodity_names=[],
                units=[],
                sampling_years=[],
                rows_with_lod=0,
                rows_with_loq=0,
                rows_with_recovery_percent=0,
                rows_with_measurement_uncertainty_percent=0,
                priority_food_group_hits=[],
                high_attention_food_hits=[],
                sensitive_population_groups=[],
                linked_occurrence_record_ids=[],
                linked_review_focus_ids=[],
            ),
            quality_flags=quality_flags,
            uncertainty_and_assumption_ledger=[],
            referenced_resources=[
                ReviewResourceReference(
                    role="documentation",
                    uri="docs://contaminant-monitoring-import",
                    description="Operator guidance for contaminant monitoring import review.",
                ),
            ],
            notes=notes,
        )

    valid_rows = []
    invalid_row_indexes: list[int] = []
    for index, row in enumerate(reader, start=1):
        if row is None or not any((value or "").strip() for value in row.values()):
            continue
        canonical_row = {canonical: row.get(header, "") for header, canonical in header_mapping.items()}
        try:
            commodity = (canonical_row.get("commodity") or "").strip()
            analyte = (canonical_row.get("analyte") or "").strip()
            unit = (canonical_row.get("unit") or "").strip()
            result_value = _parse_float(canonical_row.get("result_value"))
            if not commodity or not analyte or not unit or result_value is None:
                raise ValueError("missing required row values")
            valid_rows.append(
                {
                    "commodity": commodity,
                    "analyte": analyte,
                    "unit": unit,
                    "resultValue": result_value,
                    "lod": _parse_float(canonical_row.get("lod")),
                    "loq": _parse_float(canonical_row.get("loq")),
                    "recoveryPercent": _parse_float(canonical_row.get("recovery_percent")),
                    "measurementUncertaintyPercent": _parse_float(
                        canonical_row.get("measurement_uncertainty_percent")
                    ),
                    "samplingYear": _parse_int(canonical_row.get("sampling_year")),
                }
            )
        except ValueError:
            invalid_row_indexes.append(index)

    if invalid_row_indexes:
        quality_flags.append(
            QualityFlag(
                code="invalid_monitoring_rows",
                severity=Severity.WARNING,
                message=f"Some monitoring rows could not be normalized and were excluded: {invalid_row_indexes}.",
            )
        )
    if not valid_rows:
        quality_flags.append(
            QualityFlag(
                code="no_valid_monitoring_rows",
                severity=Severity.ERROR,
                message="No monitoring rows could be normalized from the supplied CSV text.",
            )
        )
        return ContaminantMonitoringImportCheckResult(
            check_status=ReadinessStatus.FAIL,
            contaminant_family=request.contaminant_family,
            jurisdiction=request.jurisdiction,
            authority=request.authority,
            dataset_id=request.dataset_id,
            overall_submission_use=SubmissionUse.REVIEW_REQUIRED,
            submission_candidate_allowed=False,
            header_resolution=header_resolution,
            normalized_projection=ContaminantMonitoringNormalizedProjection(
                row_count=0,
                analytes=[],
                commodity_names=[],
                units=[],
                sampling_years=[],
                rows_with_lod=0,
                rows_with_loq=0,
                rows_with_recovery_percent=0,
                rows_with_measurement_uncertainty_percent=0,
                priority_food_group_hits=[],
                high_attention_food_hits=[],
                sensitive_population_groups=[],
                linked_occurrence_record_ids=[],
                linked_review_focus_ids=[],
            ),
            quality_flags=quality_flags,
            referenced_resources=[
                ReviewResourceReference(
                    role="documentation",
                    uri="docs://contaminant-monitoring-import",
                    description="Operator guidance for contaminant monitoring import review.",
                ),
            ],
            notes=notes,
        )

    analytes = {_normalize_text(item["analyte"]) for item in valid_rows}
    units = sorted({item["unit"] for item in valid_rows})
    commodities = sorted({item["commodity"] for item in valid_rows})
    sampling_years = sorted({item["samplingYear"] for item in valid_rows if item["samplingYear"] is not None})

    commodity_set = {_normalize_text(item["commodity"]) for item in valid_rows}
    occurrence_records, occurrence_notes, occurrence_broad_fallback_ids = _filter_occurrence_records(
        runtime, request, analytes, commodity_set
    )
    method_records, method_notes, method_broad_fallback_ids = _filter_analytical_method_records(
        runtime, request, analytes, commodity_set
    )
    notes.extend(occurrence_notes)
    notes.extend(method_notes)
    _append_currency_context(
        runtime,
        records=occurrence_records,
        record_kind_label="Occurrence-evidence record",
        quality_flag_prefix="occurrence_evidence",
        notes=notes,
        quality_flags=quality_flags,
    )
    _append_currency_context(
        runtime,
        records=method_records,
        record_kind_label="Analytical-method-evidence record",
        quality_flag_prefix="analytical_method_evidence",
        notes=notes,
        quality_flags=quality_flags,
    )
    linked_occurrence_payloads = _linked_metals_occurrence_payloads(runtime, occurrence_records)

    rows_with_lod = sum(1 for item in valid_rows if item["lod"] is not None)
    rows_with_loq = sum(1 for item in valid_rows if item["loq"] is not None)
    rows_with_recovery = sum(1 for item in valid_rows if item["recoveryPercent"] is not None)
    rows_with_uncertainty = sum(1 for item in valid_rows if item["measurementUncertaintyPercent"] is not None)

    if len(units) > 1:
        quality_flags.append(
            QualityFlag(
                code="multiple_monitoring_units",
                severity=Severity.WARNING,
                message="Multiple result units were present in the monitoring import and require reviewer confirmation.",
            )
        )
    if rows_with_loq == 0:
        quality_flags.append(
            QualityFlag(
                code="missing_loq_context",
                severity=Severity.WARNING,
                message="No LOQ values were preserved in the normalized monitoring rows.",
            )
        )
    if rows_with_recovery == 0:
        quality_flags.append(
            QualityFlag(
                code="missing_recovery_context",
                severity=Severity.WARNING,
                message="No recovery values were preserved in the normalized monitoring rows.",
            )
        )
    if rows_with_uncertainty == 0:
        quality_flags.append(
            QualityFlag(
                code="missing_measurement_uncertainty_context",
                severity=Severity.WARNING,
                message="No measurement-uncertainty values were preserved in the normalized monitoring rows.",
            )
        )
    if not occurrence_records:
        quality_flags.append(
            QualityFlag(
                code="missing_occurrence_evidence_match",
                severity=Severity.ERROR,
                message="No governed occurrence-evidence records matched the declared contaminant family and analytes.",
            )
        )
    if not method_records:
        quality_flags.append(
            QualityFlag(
                code="missing_analytical_method_evidence_match",
                severity=Severity.WARNING,
                message="No governed analytical-method-evidence records matched the declared contaminant family and analytes.",
            )
        )
    broad_fallback_record_ids = sorted(set(occurrence_broad_fallback_ids + method_broad_fallback_ids))
    if broad_fallback_record_ids:
        quality_flags.append(
            QualityFlag(
                code="broad_food_supply_fallback",
                severity=Severity.WARNING,
                message=(
                    "At least one governed evidence record matched through a `broad_food_supply` fallback rather "
                    f"than a matrix-specific link: {broad_fallback_record_ids}."
                ),
            )
        )
        notes.append(
            "Broad-food-supply fallback matching was used for at least one evidence record; treat the matrix linkage "
            "as review support rather than a matrix-specific confirmation."
        )

    high_attention_food_hits = sorted(
        {
            food
            for occurrence in linked_occurrence_payloads
            for food in occurrence.get("highAttentionFoods", [])
            if any(_matches_any([food], commodity) for commodity in commodities)
        }
    )
    priority_food_group_hits = sorted(
        {
            group
            for occurrence in linked_occurrence_payloads
            for group in occurrence.get("priorityFoodGroups", [])
            if any(_normalize_text(group) in _normalize_text(commodity) for commodity in commodities)
            or group == "fish_and_seafood"
        }
    )
    linked_review_focus_ids = sorted(
        {
            focus_id
            for occurrence in occurrence_records
            for focus_id in occurrence.linked_review_focus_ids
            if any(
                _matches_any(runtime.defaults.get_metals_review_focus_record(focus_id).get("focusFoods", []), commodity)
                or _matches_any(
                    runtime.defaults.get_metals_review_focus_record(focus_id).get("commodityGroups", []),
                    commodity,
                )
                for commodity in commodities
            )
        }
    )
    sensitive_population_groups = sorted(
        {
            group
            for occurrence in linked_occurrence_payloads
            for group in occurrence.get("sensitivePopulationGroups", [])
        }
    )
    required_review_questions = sorted(
        {
            question
            for occurrence in linked_occurrence_payloads
            for question in occurrence.get("reviewQuestions", [])
        }
        | {
            question
            for occurrence in occurrence_records
            for focus_id in occurrence.linked_review_focus_ids
            for question in runtime.defaults.get_metals_review_focus_record(focus_id).get("reviewQuestions", [])
        }
    )
    applicable_reporting_profile_ids = sorted(
        {
            profile_id
            for record in occurrence_records
            for profile_id in record.reporting_profile_ids
        }
        | {
            profile_id
            for record in method_records
            for profile_id in record.reporting_profile_ids
        }
        | {
            item["profileId"]
            for item in runtime.defaults.list_reporting_profile_records()
            if item["contaminantFamily"] == request.contaminant_family.value
            and (
                "broad_food_supply" in item["matrixGroups"]
                or any(_matches_reporting_profile_matrix_groups(item["matrixGroups"], commodity) for commodity in commodities)
            )
        }
    )
    applicable_reporting_profiles = sorted(
        [
            ReportingProfileRecord.model_validate(item)
            for item in runtime.defaults.list_reporting_profile_records()
            if item["profileId"] in applicable_reporting_profile_ids
        ],
        key=lambda record: (
            record.profile_role.value,
            record.authority.lower(),
            record.jurisdiction.lower(),
            record.profile_id,
        ),
    )
    recommended_primary_profile_ids = [
        record.profile_id
        for record in applicable_reporting_profiles
        if record.profile_role == ReportingProfileRole.PRIMARY_REGULATORY
    ]
    optional_extension_profile_ids = [
        record.profile_id
        for record in applicable_reporting_profiles
        if record.profile_role == ReportingProfileRole.NATIONAL_ADVISORY_OPTIONAL
    ]
    compliance_variant_profile_ids = [
        record.profile_id
        for record in applicable_reporting_profiles
        if record.profile_role == ReportingProfileRole.REGULATORY_COMPLIANCE_VARIANT
    ]
    supporting_detail_profile_ids = [
        record.profile_id
        for record in applicable_reporting_profiles
        if record.profile_role == ReportingProfileRole.SUPPORTING_DETAIL
    ]
    non_substitution_links = [
        ReportingProfileNonSubstitutionLink(
            profile_id=record.profile_id,
            not_substitutable_for_profile_ids=[
                profile_id
                for profile_id in record.not_substitutable_for_profile_ids
                if profile_id in applicable_reporting_profile_ids
            ],
        )
        for record in applicable_reporting_profiles
        if any(
            profile_id in applicable_reporting_profile_ids
            for profile_id in record.not_substitutable_for_profile_ids
        )
    ]
    reporting_profile_summary_notes: list[str] = []
    if applicable_reporting_profile_ids:
        notes.append(
            "Matched evidence records expose governed reporting-profile conventions; use reporting-profile roles to distinguish primary EU reporting from optional national advisory metrics."
        )
        if recommended_primary_profile_ids and optional_extension_profile_ids:
            reporting_profile_summary_notes.append(
                "Primary EU reporting profiles remain the lead convention even when optional national advisory profiles are also applicable."
            )
        if non_substitution_links:
            reporting_profile_summary_notes.append(
                "Non-substitutable profile links remain active; optional advisory metrics must not replace the linked EU primary or compliance profiles."
        )
    reporting_profile_summary = (
        ReportingProfileApplicabilitySummary(
            applicable_profile_ids=applicable_reporting_profile_ids,
            recommended_primary_profile_ids=recommended_primary_profile_ids,
            optional_extension_profile_ids=optional_extension_profile_ids,
            compliance_variant_profile_ids=compliance_variant_profile_ids,
            supporting_detail_profile_ids=supporting_detail_profile_ids,
            non_substitution_links=non_substitution_links,
            notes=reporting_profile_summary_notes,
        )
        if applicable_reporting_profile_ids
        else None
    )
    if reporting_profile_summary is not None:
        for link in reporting_profile_summary.non_substitution_links:
            linked_profile = next(
                (record for record in applicable_reporting_profiles if record.profile_id == link.profile_id),
                None,
            )
            if linked_profile is None:
                continue
            if linked_profile.profile_role not in {
                ReportingProfileRole.SUPPORTING_DETAIL,
                ReportingProfileRole.NATIONAL_ADVISORY_OPTIONAL,
                ReportingProfileRole.REGULATORY_COMPLIANCE_VARIANT,
            }:
                continue
            if any(
                primary_profile_id in reporting_profile_summary.applicable_profile_ids
                for primary_profile_id in link.not_substitutable_for_profile_ids
            ):
                continue
            quality_flags.append(
                QualityFlag(
                    code="reporting_profile_non_substitution_violation",
                    severity=Severity.ERROR,
                    message=(
                        f"Reporting profile {link.profile_id} cannot stand in for required primary or compliance "
                        f"profiles {link.not_substitutable_for_profile_ids}."
                    ),
                )
            )
        if (
            reporting_profile_summary.supporting_detail_profile_ids
            and not reporting_profile_summary.recommended_primary_profile_ids
        ):
            quality_flags.append(
                QualityFlag(
                    code="missing_primary_reporting_profile",
                    severity=Severity.ERROR,
                    message=(
                        "Supporting-detail reporting profiles were matched without any primary regulatory profile; "
                        "supporting detail must not silently replace the primary reporting basis."
                    ),
                )
            )

    overall_submission_use = _aggregate_submission_use(
        [record.submission_use for record in occurrence_records] + [record.submission_use for record in method_records]
    )
    submission_candidate_allowed = overall_submission_use == SubmissionUse.ALLOWED
    check_status = ReadinessStatus.PASS
    if (
        not occurrence_records
        or not method_records
        or len(units) > 1
        or rows_with_loq == 0
        or rows_with_recovery == 0
        or overall_submission_use != SubmissionUse.ALLOWED
    ):
        check_status = ReadinessStatus.REVIEW_REQUIRED
    if any(flag.severity == Severity.ERROR for flag in quality_flags):
        check_status = ReadinessStatus.FAIL

    uncertainty_and_assumption_ledger = build_contaminant_monitoring_check_ledger(
        contaminant_family=request.contaminant_family,
        row_count=len(valid_rows),
        rows_with_lod=rows_with_lod,
        rows_with_loq=rows_with_loq,
        rows_with_recovery_percent=rows_with_recovery,
        rows_with_measurement_uncertainty_percent=rows_with_uncertainty,
        sampling_years=sampling_years,
        occurrence_records=occurrence_records,
        analytical_method_records=method_records,
        overall_submission_use=overall_submission_use,
        submission_candidate_allowed=submission_candidate_allowed,
        dataset_declared=request.dataset_id is not None,
        dataset_linked=(
            request.dataset_id is None
            or any(request.dataset_id in record.dataset_ids for record in occurrence_records)
        ),
    )

    return ContaminantMonitoringImportCheckResult(
        check_status=check_status,
        contaminant_family=request.contaminant_family,
        jurisdiction=request.jurisdiction,
        authority=request.authority,
        dataset_id=request.dataset_id,
        overall_submission_use=overall_submission_use,
        submission_candidate_allowed=submission_candidate_allowed,
        occurrence_evidence_records=occurrence_records,
        analytical_method_evidence_records=method_records,
        applicable_reporting_profile_ids=applicable_reporting_profile_ids,
        reporting_profile_summary=reporting_profile_summary,
        header_resolution=header_resolution,
        normalized_projection=ContaminantMonitoringNormalizedProjection(
            row_count=len(valid_rows),
            analytes=sorted({_normalize_text(item["analyte"]) for item in valid_rows}),
            commodity_names=sorted({_normalize_text(item["commodity"]) for item in valid_rows}),
            units=units,
            sampling_years=sampling_years,
            rows_with_lod=rows_with_lod,
            rows_with_loq=rows_with_loq,
            rows_with_recovery_percent=rows_with_recovery,
            rows_with_measurement_uncertainty_percent=rows_with_uncertainty,
            priority_food_group_hits=priority_food_group_hits,
            high_attention_food_hits=high_attention_food_hits,
            sensitive_population_groups=sensitive_population_groups,
            linked_occurrence_record_ids=sorted(
                {occurrence_id for record in occurrence_records for occurrence_id in record.occurrence_record_ids}
            ),
            linked_review_focus_ids=linked_review_focus_ids,
        ),
        quality_flags=quality_flags,
        uncertainty_and_assumption_ledger=uncertainty_and_assumption_ledger,
        required_review_questions=required_review_questions,
        referenced_resources=[
            ReviewResourceReference(
                role="documentation",
                uri="docs://contaminant-monitoring-import",
                description="Operator guidance for contaminant monitoring import review.",
            ),
            ReviewResourceReference(
                role="occurrence_evidence_manifest",
                uri="occurrence-evidence://manifest",
                description="Governed occurrence-evidence manifest for contaminant monitoring families.",
            ),
            ReviewResourceReference(
                role="analytical_method_evidence_manifest",
                uri="analytical-method-evidence://manifest",
                description="Governed analytical-method-evidence manifest for contaminant monitoring families.",
            ),
            ReviewResourceReference(
                role="reporting_profiles_manifest",
                uri="reporting-profiles://manifest",
                description="Governed reporting-profile manifest for primary EU and optional advisory reporting conventions.",
            ),
            ReviewResourceReference(
                role="documentation",
                uri="docs://reporting-profiles-registry",
                description="Operator guidance for reporting-profile registry usage and optional extensions.",
            ),
        ],
        notes=notes,
    )
