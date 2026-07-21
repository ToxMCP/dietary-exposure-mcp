from __future__ import annotations

from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.models import (
    AnalyticalMethodEvidenceLookupResult,
    AnalyticalMethodEvidenceRecord,
    AuthorityRecord,
    ContaminantLegalLimitLookupResult,
    ContaminantLegalLimitRecord,
    ConsumptionDatasetRecord,
    ConsumptionDatasetSupportLookupResult,
    ContaminantFamily,
    EmergingContaminantRecord,
    JurisdictionCoverageRecord,
    LegalAuthorityRecord,
    LookupConsumptionDatasetSupportRequest,
    LookupOccurrenceEvidenceRequest,
    LookupAnalyticalMethodEvidenceRequest,
    LookupMetalsOccurrenceRequest,
    LookupMetalsReviewFocusRequest,
    LookupMethodSupportRequest,
    LookupReferenceValuesRequest,
    MetalsOccurrenceLookupResult,
    MetalsOccurrenceRecord,
    MetalsReviewFocusLookupResult,
    MetalsReviewFocusRecord,
    MethodRegistryRecord,
    MethodSupportLookupResult,
    OccurrenceEvidenceLookupResult,
    OccurrenceEvidenceRecord,
    LookupReportingProfilesRequest,
    LookupContaminantLegalLimitsRequest,
    ReferenceValueLookupResult,
    ReferenceValueRecord,
    ReportingProfileLookupResult,
    ReportingProfileRecord,
    ReportingProfileRole,
    QualityFlag,
    ReferenceValueJurisdictionStatus,
    RequestedLaneStatus,
    Severity,
    SourceConflictGroup,
    SubmissionUse,
)


GLOBAL_JURISDICTIONS = {"global", "codex_global"}


def _normalize_text(value: str | None) -> str | None:
    return value.strip().lower() if value is not None else None


def _jurisdiction_matches(record_jurisdiction: str, requested_jurisdiction: str | None) -> bool:
    if requested_jurisdiction is None:
        return True
    normalized_requested = requested_jurisdiction.strip().lower()
    normalized_record = record_jurisdiction.strip().lower()
    return normalized_record == normalized_requested or normalized_record in GLOBAL_JURISDICTIONS


def _aggregate_submission_use(values: list[SubmissionUse]) -> SubmissionUse:
    if not values:
        return SubmissionUse.REVIEW_REQUIRED
    if any(value == SubmissionUse.NOT_ALLOWED for value in values):
        return SubmissionUse.NOT_ALLOWED
    if any(value == SubmissionUse.REVIEW_REQUIRED for value in values):
        return SubmissionUse.REVIEW_REQUIRED
    return SubmissionUse.ALLOWED


def _summarize_curated_legal_limit_scope(
    defaults_registry: DefaultsRegistry,
    coverage_summaries: list[JurisdictionCoverageRecord],
) -> tuple[list[str], list[str], bool]:
    commodity_codes: set[str] = set()
    matrix_groups: set[str] = set()
    has_exact_legal_limit_records = False
    for summary in coverage_summaries:
        for record_id in summary.legal_limit_record_ids:
            record = defaults_registry.get_contaminant_legal_limit_record(record_id)
            has_exact_legal_limit_records = True
            commodity_codes.update(record.get("commodityCodes", []))
            matrix_groups.update(record.get("matrixGroups", []))
    return sorted(commodity_codes), sorted(matrix_groups), has_exact_legal_limit_records


def _summarize_reference_support_types(
    coverage_summaries: list[JurisdictionCoverageRecord],
) -> tuple[list[str], bool]:
    support_types: set[str] = set()
    has_reference_value_records = False
    for summary in coverage_summaries:
        if summary.reference_value_record_ids:
            support_types.add("reference_values")
            has_reference_value_records = True
        if summary.enforcement_record_ids:
            support_types.add("enforcement_records")
        if summary.legal_limit_record_ids:
            support_types.add("legal_limits")
        if summary.legal_authority_ids:
            support_types.add("legal_anchors")
    return sorted(support_types), has_reference_value_records


def _family_specific_method_notes(contaminant_family: ContaminantFamily) -> list[str]:
    if contaminant_family == ContaminantFamily.MICROPLASTICS_EMERGING:
        return [
            "Microplastics remain isolated from pesticide method support and are not routed through PRIMo, DEEM, or OpenFoodTox logic."
        ]
    if contaminant_family == ContaminantFamily.PFAS_FOOD_CONTAMINANTS:
        return [
            "PFAS food-contaminant support is exposed as governed provenance and legal-context metadata, not as a native PFAS quantitative engine.",
            "PFAS records remain separate from pesticide-residue method support even when PFAS active substances can also appear in pesticide contexts.",
        ]
    if contaminant_family == ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS:
        return [
            "Acrylamide support is exposed as governed process-contaminant provenance, mitigation, and monitoring metadata rather than as a native acrylamide calculation engine.",
            "Acrylamide records remain separate from pesticide-residue method support and preserve the benchmark-dose and mitigation-oriented regulatory posture.",
        ]
    if contaminant_family == ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION:
        return [
            "Bisphenol support is exposed as governed dietary-exposure provenance for food-contact migration and foodstuffs review, not as a native food-contact migration engine.",
            "Bisphenol records remain separate from pesticide-residue method support and preserve EFSA and EU food-contact governance boundaries.",
        ]
    if contaminant_family == ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS:
        return [
            "Cadmium support is exposed as governed metals-contaminant provenance, dietary exposure, and legal-context metadata rather than as a native cadmium quantitative engine.",
            "Cadmium records remain separate from pesticide-residue method support and preserve EFSA metals-contaminant governance boundaries.",
            "Cadmium method support includes shared EU official-control sampling and analysis governance for contaminants in foodstuffs.",
        ]
    if contaminant_family == ContaminantFamily.LEAD_FOOD_CONTAMINANTS:
        return [
            "Lead support is exposed as governed metals-contaminant provenance, benchmark-dose reference-point context, and legal metadata rather than as a native lead quantitative engine.",
            "Lead records remain separate from pesticide-residue method support and preserve EFSA metals-contaminant governance boundaries.",
            "Lead method support includes shared EU official-control sampling and analysis governance for contaminants in foodstuffs.",
        ]
    if contaminant_family == ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS:
        return [
            "Inorganic arsenic support is exposed as governed metals-contaminant provenance, margin-of-exposure reference-point context, and legal metadata rather than as a native inorganic-arsenic quantitative engine.",
            "Inorganic arsenic records remain separate from pesticide-residue method support and preserve EFSA metals-contaminant governance boundaries.",
            "Inorganic arsenic method support includes shared EU official-control sampling and analysis governance for contaminants in foodstuffs.",
        ]
    if contaminant_family == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS:
        return [
            "Mercury support is exposed as governed metals-contaminant provenance, methylmercury and inorganic-mercury TWI context, and legal metadata rather than as a native mercury quantitative engine.",
            "Mercury records remain separate from pesticide-residue method support and preserve EFSA metals-contaminant governance boundaries.",
            "Mercury method support includes shared EU official-control sampling and analysis governance for contaminants in foodstuffs.",
        ]
    return []


def _family_specific_dataset_notes(contaminant_family: ContaminantFamily) -> list[str]:
    if contaminant_family == ContaminantFamily.MICROPLASTICS_EMERGING:
        return ["No governed microplastics-specific dietary consumption dataset is treated as submission-ready in v0.1."]
    if contaminant_family == ContaminantFamily.PFAS_FOOD_CONTAMINANTS:
        return [
            "PFAS dataset support uses EFSA food-consumption infrastructure and monitoring-programme metadata for review-oriented support only.",
            "No native PFAS submission engine is implied by these dataset registry records in v0.1.",
        ]
    if contaminant_family == ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS:
        return [
            "Acrylamide dataset support uses EFSA food-consumption infrastructure and EU monitoring metadata for review-oriented support only.",
            "No native acrylamide submission engine is implied by these dataset registry records in v0.1.",
        ]
    if contaminant_family == ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION:
        return [
            "Bisphenol dataset support uses EFSA food-consumption infrastructure as dietary context metadata for food-contact migration review.",
            "No native bisphenol migration or submission engine is implied by these dataset registry records in v0.1.",
        ]
    if contaminant_family == ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS:
        return [
            "Cadmium dataset support uses EFSA food-consumption infrastructure and dietary exposure reporting metadata for review-oriented support only.",
            "No native cadmium submission engine is implied by these dataset registry records in v0.1.",
        ]
    if contaminant_family == ContaminantFamily.LEAD_FOOD_CONTAMINANTS:
        return [
            "Lead dataset support uses EFSA food-consumption infrastructure and dietary exposure reporting metadata for review-oriented support only.",
            "No native lead submission engine is implied by these dataset registry records in v0.1.",
        ]
    if contaminant_family == ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS:
        return [
            "Inorganic arsenic dataset support uses EFSA food-consumption infrastructure and dietary exposure reporting metadata for review-oriented support only.",
            "No native inorganic-arsenic submission engine is implied by these dataset registry records in v0.1.",
        ]
    if contaminant_family == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS:
        return [
            "Mercury dataset support uses EFSA food-consumption infrastructure and dietary exposure context metadata for review-oriented support only.",
            "No native mercury submission engine is implied by these dataset registry records in v0.1.",
        ]
    return []


def _family_specific_metals_occurrence_notes(contaminant_family: ContaminantFamily) -> list[str]:
    if contaminant_family == ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS:
        return [
            "Cadmium occurrence support is exposed as governed EFSA exposure provenance linked to EU contaminants-law and official-control context.",
            "Records include priority food-group and review-question metadata so occurrence summaries can be interpreted without implying a native cadmium exposure engine.",
            "The metals-occurrence registry is not a live monitoring database or native cadmium exposure engine.",
        ]
    if contaminant_family == ContaminantFamily.LEAD_FOOD_CONTAMINANTS:
        return [
            "Lead occurrence support is exposed as governed EFSA exposure provenance linked to EU contaminants-law and official-control context.",
            "Records include priority food-group, high-attention food, and trend-signal metadata for review-oriented interpretation only.",
            "The metals-occurrence registry is not a live monitoring database or native lead exposure engine.",
        ]
    if contaminant_family == ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS:
        return [
            "Inorganic arsenic occurrence support is exposed as governed EFSA exposure provenance linked to EU contaminants-law and official-control context.",
            "Records include priority food-group and review-question metadata so rice-focused occurrence review remains explicit.",
            "The metals-occurrence registry is not a live monitoring database or native inorganic-arsenic exposure engine.",
        ]
    if contaminant_family == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS:
        return [
            "Mercury occurrence support is exposed as governed EFSA dietary context linked to EU contaminants-law and official-control context.",
            "Records include high-attention fish-species and sensitive-population metadata for review-oriented interpretation only.",
            "Mercury occurrence records preserve fish and seafood sensitivity notes without implying a native mercury exposure engine.",
        ]
    return []


def _family_specific_metals_review_focus_notes(contaminant_family: ContaminantFamily) -> list[str]:
    if contaminant_family == ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS:
        return [
            "Cadmium review-focus records prioritize staple plant foods and mollusc-specific follow-up for reviewer attention.",
            "The metals-review-focus registry is not a live occurrence database or native cadmium decision engine.",
        ]
    if contaminant_family == ContaminantFamily.LEAD_FOOD_CONTAMINANTS:
        return [
            "Lead review-focus records preserve explicit attention for game meat, offal, and other current contributor groups that should not be flattened into broad food buckets.",
            "The metals-review-focus registry is not a live occurrence database or native lead decision engine.",
        ]
    if contaminant_family == ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS:
        return [
            "Inorganic-arsenic review-focus records keep rice and rice-based foods explicit for margin-of-exposure style review.",
            "The metals-review-focus registry is not a live occurrence database or native inorganic-arsenic decision engine.",
        ]
    if contaminant_family == ContaminantFamily.MERCURY_FOOD_CONTAMINANTS:
        return [
            "Mercury review-focus records keep large predatory fish and sensitive-population advice explicit for reviewer follow-up.",
            "The metals-review-focus registry is not a live occurrence database or native mercury decision engine.",
        ]
    return []


def _family_specific_occurrence_evidence_notes(contaminant_family: ContaminantFamily) -> list[str]:
    if contaminant_family == ContaminantFamily.PESTICIDE_RESIDUE:
        return [
            "Pesticide-residue occurrence evidence is exposed as governed monitoring-context metadata linked to EFSA annual reporting, OpenFoodTox-backed reference values, and EU residue-law anchors.",
            "These records preserve review provenance and do not imply a native pesticide monitoring database or submission-capable residue engine.",
        ]
    if contaminant_family in {
        ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
        ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
        ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
        ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
    }:
        return [
            "Occurrence evidence is exposed as governed monitoring-context metadata linked to occurrence, dataset, method, and legal records.",
            "These records are review-oriented evidence objects and do not imply a native contaminant exposure engine.",
        ]
    if contaminant_family == ContaminantFamily.PFAS_FOOD_CONTAMINANTS:
        return [
            "PFAS occurrence evidence is exposed as governed dietary and monitoring-context metadata linked to EFSA review, EU monitoring, legal, and reference-value records.",
            "These records preserve review provenance and do not imply a native PFAS monitoring database or submission-capable exposure engine.",
        ]
    if contaminant_family == ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS:
        return [
            "Acrylamide occurrence evidence is exposed as governed process-contaminant monitoring and mitigation context linked to EFSA benchmark-dose provenance.",
            "These records preserve review provenance and do not imply a native acrylamide occurrence engine or final margin-of-exposure calculator.",
        ]
    if contaminant_family == ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION:
        return [
            "Bisphenol occurrence evidence is exposed as governed dietary and food-contact review context linked to EFSA TDI provenance and EU legal anchors.",
            "These records preserve review provenance and do not imply a native food-contact migration engine or compliance decision engine.",
        ]
    return []


def _family_specific_analytical_method_evidence_notes(contaminant_family: ContaminantFamily) -> list[str]:
    if contaminant_family == ContaminantFamily.PESTICIDE_RESIDUE:
        return [
            "Pesticide-residue analytical-method evidence is exposed as governed OECD residue-method and EFSA annual-report review context.",
            "These records preserve validation context and do not imply a native pesticide laboratory-method execution engine.",
        ]
    if contaminant_family in {
        ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
        ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
        ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
        ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
    }:
        return [
            "Analytical-method evidence is exposed as governed sampling, LOQ, recovery, uncertainty, and official-control context.",
            "These records preserve validation context and do not imply a native laboratory-method execution engine.",
        ]
    if contaminant_family == ContaminantFamily.PFAS_FOOD_CONTAMINANTS:
        return [
            "PFAS analytical-method evidence is exposed as governed monitoring-programme and analytical review context.",
            "These records preserve validation context and do not imply a native PFAS laboratory-method execution engine.",
        ]
    if contaminant_family == ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS:
        return [
            "Acrylamide analytical-method evidence is exposed as governed monitoring and mitigation review context.",
            "These records preserve validation context and do not imply a native acrylamide laboratory-method execution engine.",
        ]
    if contaminant_family == ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION:
        return [
            "Bisphenol analytical-method evidence is exposed as governed food-contact and dietary review context.",
            "These records preserve validation context and do not imply a native food-contact migration laboratory-method execution engine.",
        ]
    return []


def _family_specific_reporting_profile_notes(contaminant_family: ContaminantFamily) -> list[str]:
    if contaminant_family == ContaminantFamily.PFAS_FOOD_CONTAMINANTS:
        return [
            "PFAS reporting profiles keep EU EFSA-4 risk and compliance reporting distinct from optional national advisory metrics.",
            "Optional national advisory profiles do not replace the primary EU EFSA-4 reporting basis for food-regulatory review.",
        ]
    return [
        "Reporting profiles are exposed as governed reporting conventions and do not change the underlying evidence registry records."
    ]


def _currency_context_notes(
    defaults_registry: DefaultsRegistry,
    records: list[OccurrenceEvidenceRecord] | list[AnalyticalMethodEvidenceRecord] | list[MetalsOccurrenceRecord],
    *,
    record_kind_label: str,
) -> list[str]:
    notes: list[str] = []
    historical_record_ids: list[str] = []
    for record in records:
        assessment = defaults_registry.assess_source_currency(
            source_ids=record.source_ids,
            data_period=getattr(record, "data_period", None),
        )
        for note in assessment.notes:
            notes.append(f"{record_kind_label} {record.record_id}: {note}")
        if assessment.review_required:
            historical_record_ids.append(record.record_id)
    if historical_record_ids:
        notes.append(
            f"Historical data context remains on at least one {record_kind_label.lower()} ({', '.join(sorted(historical_record_ids))}); keep the result in review-oriented mode until the older evidence base is explicitly accepted."
        )
    return notes


def _matches_focus_text(values: list[str], query: str | None) -> bool:
    if query is None:
        return True
    normalized_query = query.strip().lower()
    if not normalized_query:
        return True
    return any(
        normalized_query == value.strip().lower() or normalized_query in value.strip().lower()
        for value in values
    )


def lookup_reference_values(
    defaults_registry: DefaultsRegistry,
    request: LookupReferenceValuesRequest,
) -> ReferenceValueLookupResult:
    substance_key = request.substance_key.strip().lower()
    authority_filter = _normalize_text(request.authority)
    jurisdiction_filter = _normalize_text(request.jurisdiction)
    family_filter = request.contaminant_family.value if request.contaminant_family is not None else None
    reference_type_filter = _normalize_text(request.reference_type)
    population_filter = _normalize_text(request.population)
    source_id_filter = _normalize_text(request.source_id)

    matched_records = []
    for item in defaults_registry.list_reference_value_records():
        if item["substanceKey"].strip().lower() != substance_key:
            continue
        if authority_filter and item["authority"].strip().lower() != authority_filter:
            continue
        if jurisdiction_filter and item["jurisdiction"].strip().lower() != jurisdiction_filter:
            continue
        if family_filter and item["contaminantFamily"] != family_filter:
            continue
        if reference_type_filter and item["referenceType"].strip().lower() != reference_type_filter:
            continue
        if population_filter and population_filter not in (item.get("population") or "").strip().lower():
            continue
        if request.assessment_year is not None and item.get("assessmentYear") != request.assessment_year:
            continue
        if source_id_filter and source_id_filter not in {source_id.lower() for source_id in item["sourceIds"]}:
            continue
        matched_records.append(ReferenceValueRecord.model_validate(item))

    matched_records.sort(
        key=lambda record: (
            record.reference_type,
            record.authority.lower(),
            record.jurisdiction.lower(),
            record.record_id,
        )
    )

    known_source_ids = {item["sourceId"] for item in defaults_registry.source_catalog_manifest()["sources"]}
    authorities = []
    seen_authority_keys: set[tuple[str, str, str]] = set()
    for record in matched_records:
        authority_key = (record.authority.lower(), record.jurisdiction.lower(), record.contaminant_family.value)
        if authority_key in seen_authority_keys:
            continue
        seen_authority_keys.add(authority_key)
        authority_sources = sorted(
            {
                source_id
                for source_id in record.source_ids
                if source_id in known_source_ids
            }
        )
        authorities.append(
            AuthorityRecord(
                authority_id=f"{record.authority.lower().replace(' ', '_')}.{record.jurisdiction}.{record.contaminant_family.value}",
                authority=record.authority,
                jurisdiction=record.jurisdiction,
                contaminant_family=record.contaminant_family,
                source_ids=authority_sources,
                notes=[
                    "Authority-specific records are preserved as published and are not flattened into one canonical value."
                ],
            )
        )

    conflict_groups = {}
    for record in matched_records:
        if not record.conflict_group_id:
            continue
        conflict_groups.setdefault(record.conflict_group_id, []).append(record)

    visible_conflicts = []
    for conflict_group_id, records in sorted(conflict_groups.items()):
        if len(records) < 2:
            continue
        authorities_in_group = sorted({record.authority for record in records})
        populations_in_group = {record.population for record in records if record.population}
        years_in_group = {record.assessment_year for record in records if record.assessment_year is not None}
        units_in_group = {record.unit for record in records if record.unit}
        if len(authorities_in_group) > 1:
            conflict_note = "Authority-specific values differ and require jurisdiction-aware selection."
        elif len(populations_in_group) > 1:
            conflict_note = "Population-specific source records differ; select the applicable population explicitly."
        elif len(units_in_group) > 1:
            conflict_note = "Source records use different unit bases; verify the original scientific outputs before use."
        elif len(years_in_group) > 1:
            conflict_note = "Historical source records differ by assessment year; no record is selected as canonical."
        else:
            conflict_note = "Multiple source records differ; review their structured context before selection."
        visible_conflicts.append(
            SourceConflictGroup(
                conflict_group_id=conflict_group_id,
                substance_key=records[0].substance_key,
                contaminant_family=records[0].contaminant_family,
                record_ids=[record.record_id for record in records],
                authorities=authorities_in_group,
                note=conflict_note,
            )
        )

    notes = []
    quality_flags = []
    coverage_summaries = []
    if jurisdiction_filter and family_filter:
        coverage_summaries = [
            JurisdictionCoverageRecord.model_validate(item)
            for item in defaults_registry.get_jurisdiction_coverage_records(
                jurisdiction=request.jurisdiction,
                contaminant_family=family_filter,
                substance_key=request.substance_key,
            )
        ]
        coverage_summaries.sort(key=lambda record: (record.jurisdiction.lower(), record.substance_key, record.coverage_id))
    curated_support_types, has_reference_value_records = _summarize_reference_support_types(coverage_summaries)

    if not jurisdiction_filter:
        requested_jurisdiction_status = ReferenceValueJurisdictionStatus.UNSCOPED_LOOKUP
    elif matched_records:
        requested_jurisdiction_status = ReferenceValueJurisdictionStatus.EXACT_JURISDICTION_VALUE_PRESENT
    elif coverage_summaries:
        if has_reference_value_records:
            requested_jurisdiction_status = ReferenceValueJurisdictionStatus.JURISDICTION_VALUE_EXISTS_BUT_FILTER_UNMATCHED
        elif all(item.coverage_level.value == "explicit_gap" for item in coverage_summaries):
            requested_jurisdiction_status = ReferenceValueJurisdictionStatus.EXPLICIT_GAP
        elif all(item.coverage_level.value == "anchor_only" for item in coverage_summaries):
            requested_jurisdiction_status = ReferenceValueJurisdictionStatus.ANCHOR_ONLY_FAMILY
        else:
            requested_jurisdiction_status = ReferenceValueJurisdictionStatus.FAMILY_CURATED_WITHOUT_REFERENCE_VALUE
    else:
        requested_jurisdiction_status = ReferenceValueJurisdictionStatus.NO_CURATED_FAMILY_COVERAGE

    if visible_conflicts:
        notes.append("Multiple reference-value contexts were preserved and exposed without selecting a canonical record.")
        quality_flags.append(
            QualityFlag(
                code="reference_value_context_selection_required",
                severity=Severity.WARNING,
                message="Multiple governed records matched; select the authority, population, assessment year, and unit basis explicitly.",
            )
        )
    if any("efsa.openfoodtox.2023_snapshot" in record.source_ids for record in matched_records):
        quality_flags.append(
            QualityFlag(
                code="superseded_source_snapshot",
                severity=Severity.WARNING,
                message=(
                    "At least one result comes from the superseded 2023 OpenFoodTox 2.0 snapshot. "
                    "OpenFoodTox 3.0 is current; verify the original EFSA output before regulatory use."
                ),
            )
        )
    if any("efsa.openfoodtox" in record.source_ids for record in matched_records):
        quality_flags.append(
            QualityFlag(
                code="openfoodtox_original_output_review_required",
                severity=Severity.WARNING,
                message=(
                    "At least one result comes from the current OpenFoodTox 3.0 bulk dataset. "
                    "Review the linked original EFSA scientific output before regulatory use."
                ),
            )
        )
    context_groups: dict[tuple[str, str, str], list[ReferenceValueRecord]] = {}
    for record in matched_records:
        context_groups.setdefault(
            (record.reference_type, record.authority.lower(), record.jurisdiction.lower()), []
        ).append(record)
    if any(len({record.unit for record in records if record.unit}) > 1 for records in context_groups.values()):
        quality_flags.append(
            QualityFlag(
                code="reference_value_unit_basis_review_required",
                severity=Severity.WARNING,
                message="Matched records for the same reference type and authority use different unit bases.",
            )
        )
    if coverage_summaries:
        coverage_levels = ", ".join(sorted({item.coverage_level.value for item in coverage_summaries}))
        notes.append(
            f"Machine-readable jurisdiction coverage summaries are attached for this lane ({coverage_levels})."
        )
    if not matched_records:
        notes.append("No governed reference-value records matched the requested filters.")
        if jurisdiction_filter:
            if requested_jurisdiction_status in {
                ReferenceValueJurisdictionStatus.EXPLICIT_GAP,
                ReferenceValueJurisdictionStatus.NO_CURATED_FAMILY_COVERAGE,
            }:
                quality_flags.append(
                    QualityFlag(
                        code="coverage_gap",
                        severity=Severity.WARNING,
                        message=(
                            f"No governed reference-value coverage is currently curated for `{request.substance_key}` "
                            f"in jurisdiction `{request.jurisdiction}`."
                        ),
                    )
                )
            quality_flags.append(
                QualityFlag(
                    code="no_jurisdiction_specific_reference_value",
                    severity=Severity.WARNING,
                    message=(
                        f"No jurisdiction-specific reference value matched `{request.substance_key}` "
                        f"for `{request.jurisdiction}`."
                    ),
                )
            )
            if requested_jurisdiction_status == ReferenceValueJurisdictionStatus.FAMILY_CURATED_WITHOUT_REFERENCE_VALUE:
                quality_flags.append(
                    QualityFlag(
                        code="family_curated_without_reference_value",
                        severity=Severity.WARNING,
                        message=(
                            f"Jurisdiction `{request.jurisdiction}` has governed curated support for "
                            f"`{request.substance_key}`, but the repo does not ship a jurisdiction-specific "
                            "reference value for this family."
                        ),
                    )
                )
                if curated_support_types:
                    notes.append(
                        "Jurisdiction support exists through "
                        + ", ".join(f"`{item}`" for item in curated_support_types)
                        + ", but not through a jurisdiction-specific reference-value record."
                    )
            elif requested_jurisdiction_status == ReferenceValueJurisdictionStatus.ANCHOR_ONLY_FAMILY:
                quality_flags.append(
                    QualityFlag(
                        code="anchor_only_family_without_reference_value",
                        severity=Severity.WARNING,
                        message=(
                            f"Jurisdiction `{request.jurisdiction}` has an official family anchor for "
                            f"`{request.substance_key}`, but no exact curated reference-value layer is shipped."
                        ),
                    )
                )
                notes.append(
                    "An official family anchor exists for this jurisdiction, but the repo does not yet ship a jurisdiction-specific reference-value record."
                )
            elif requested_jurisdiction_status == ReferenceValueJurisdictionStatus.JURISDICTION_VALUE_EXISTS_BUT_FILTER_UNMATCHED:
                quality_flags.append(
                    QualityFlag(
                        code="requested_authority_filter_unmatched",
                        severity=Severity.WARNING,
                        message=(
                            f"Jurisdiction `{request.jurisdiction}` has governed reference values for "
                            f"`{request.substance_key}`, but none matched the requested authority filter."
                        ),
                    )
                )
                notes.append(
                    "Jurisdiction-specific reference values exist for this lane, but the current authority filter excluded them."
                )
            notes.append(
                "Jurisdiction-specific coverage gaps are surfaced explicitly instead of borrowing values from other authorities."
            )

    return ReferenceValueLookupResult(
        substance_key=request.substance_key,
        contaminant_family=request.contaminant_family,
        requested_jurisdiction_status=requested_jurisdiction_status,
        curated_support_types=curated_support_types,
        authorities=authorities,
        matched_records=matched_records,
        visible_conflicts=visible_conflicts,
        coverage_summaries=coverage_summaries,
        quality_flags=quality_flags,
        notes=notes,
    )


def lookup_contaminant_legal_limits(
    defaults_registry: DefaultsRegistry,
    request: LookupContaminantLegalLimitsRequest,
) -> ContaminantLegalLimitLookupResult:
    authority_filter = _normalize_text(request.authority)
    jurisdiction_filter = _normalize_text(request.jurisdiction)
    substance_filter = _normalize_text(request.substance_key)
    matrix_group_filter = _normalize_text(request.matrix_group)
    normalized_commodity_code = None
    if request.commodity_code is not None:
        commodity_mapping = defaults_registry.get_food_vocabulary_mapping_record(request.commodity_code)
        normalized_commodity_code = commodity_mapping.get("processedCommodityCode")
        if normalized_commodity_code is None:
            normalized_commodity_code = commodity_mapping["commodityCode"]

    matched_records = []
    for item in defaults_registry.list_contaminant_legal_limit_records():
        if item["contaminantFamily"] != request.contaminant_family.value:
            continue
        if authority_filter and item["authority"].strip().lower() != authority_filter:
            continue
        if jurisdiction_filter and item["jurisdiction"].strip().lower() != jurisdiction_filter:
            continue
        if substance_filter and item["substanceKey"].strip().lower() != substance_filter:
            continue
        if normalized_commodity_code and normalized_commodity_code not in item["commodityCodes"]:
            continue
        if matrix_group_filter and matrix_group_filter not in {
            value.strip().lower() for value in item.get("matrixGroups", [])
        }:
            continue
        matched_records.append(ContaminantLegalLimitRecord.model_validate(item))

    matched_records.sort(
        key=lambda record: (
            record.jurisdiction.lower(),
            record.contaminant_family.value,
            record.substance_key,
            record.authority.lower(),
            record.limit_value,
            record.record_id,
        )
    )

    coverage_summaries = []
    if jurisdiction_filter:
        coverage_summaries = [
            JurisdictionCoverageRecord.model_validate(item)
            for item in defaults_registry.get_jurisdiction_coverage_records(
                jurisdiction=request.jurisdiction,
                contaminant_family=request.contaminant_family.value,
                substance_key=request.substance_key,
            )
        ]
        coverage_summaries.sort(key=lambda record: (record.jurisdiction.lower(), record.substance_key, record.coverage_id))
    curated_scope_commodity_codes, curated_scope_matrix_groups, has_exact_legal_limit_records = (
        _summarize_curated_legal_limit_scope(defaults_registry, coverage_summaries)
        if coverage_summaries
        else ([], [], False)
    )

    legal_authority_ids = {
        record.legal_authority_id
        for record in matched_records
    }
    for summary in coverage_summaries:
        legal_authority_ids.update(summary.legal_authority_ids)

    legal_authorities = [
        LegalAuthorityRecord.model_validate(defaults_registry.get_legal_authority_record(authority_id))
        for authority_id in sorted(legal_authority_ids)
    ]
    overall_submission_use = (
        _aggregate_submission_use([record.submission_use for record in matched_records])
        if matched_records
        else SubmissionUse.REVIEW_REQUIRED
    )

    if not jurisdiction_filter:
        requested_lane_status = RequestedLaneStatus.UNSCOPED_LOOKUP
    elif matched_records:
        requested_lane_status = RequestedLaneStatus.EXACT_CURATED_MATCH
    elif coverage_summaries:
        if has_exact_legal_limit_records:
            requested_lane_status = RequestedLaneStatus.FAMILY_CURATED_BUT_REQUESTED_LANE_UNMATCHED
        elif all(item.coverage_level.value == "explicit_gap" for item in coverage_summaries):
            requested_lane_status = RequestedLaneStatus.EXPLICIT_GAP
        else:
            requested_lane_status = RequestedLaneStatus.ANCHOR_ONLY_FAMILY
    else:
        requested_lane_status = RequestedLaneStatus.NO_CURATED_FAMILY_COVERAGE

    notes = []
    quality_flags = []
    if coverage_summaries:
        coverage_levels = ", ".join(sorted({item.coverage_level.value for item in coverage_summaries}))
        notes.append(
            f"Machine-readable jurisdiction coverage summaries are attached for this legal-limit lane ({coverage_levels})."
        )
    if matched_records:
        notes.append(
            "Jurisdiction-specific contaminant legal limits are preserved as published and are not borrowed across authorities."
        )
    else:
        notes.append("No governed contaminant legal-limit records matched the requested filters.")
        if jurisdiction_filter:
            if requested_lane_status in {
                RequestedLaneStatus.EXPLICIT_GAP,
                RequestedLaneStatus.NO_CURATED_FAMILY_COVERAGE,
            }:
                quality_flags.append(
                    QualityFlag(
                        code="coverage_gap",
                        severity=Severity.WARNING,
                        message=(
                            f"No governed contaminant legal-limit coverage is currently curated for family "
                            f"`{request.contaminant_family.value}` in jurisdiction `{request.jurisdiction}`."
                        ),
                    )
                )
            quality_flags.append(
                QualityFlag(
                    code="no_jurisdiction_specific_legal_limit",
                    severity=Severity.WARNING,
                    message=(
                        f"No jurisdiction-specific contaminant legal limit matched the requested lane for "
                        f"`{request.jurisdiction}`."
                    ),
                )
            )
            if requested_lane_status == RequestedLaneStatus.FAMILY_CURATED_BUT_REQUESTED_LANE_UNMATCHED:
                scope_bits = []
                if curated_scope_commodity_codes:
                    scope_bits.append(
                        "current exact commodity coverage includes "
                        + ", ".join(f"`{code}`" for code in curated_scope_commodity_codes[:8])
                    )
                if curated_scope_matrix_groups:
                    scope_bits.append(
                        "current matrix-group coverage includes "
                        + ", ".join(f"`{group}`" for group in curated_scope_matrix_groups[:8])
                    )
                scope_suffix = f"; {'; '.join(scope_bits)}" if scope_bits else ""
                quality_flags.append(
                    QualityFlag(
                        code="requested_lane_outside_curated_scope",
                        severity=Severity.WARNING,
                        message=(
                            f"Jurisdiction `{request.jurisdiction}` has curated contaminant legal-limit coverage for "
                            f"`{request.contaminant_family.value}`, but the requested lane did not match an exact curated "
                            f"record{scope_suffix}."
                        ),
                    )
                )
                notes.append(
                    "Family-level curated legal-limit coverage exists for this jurisdiction, but the requested commodity or matrix falls outside the exact curated scope."
                )
            elif requested_lane_status == RequestedLaneStatus.ANCHOR_ONLY_FAMILY:
                quality_flags.append(
                    QualityFlag(
                        code="anchor_only_family_without_exact_legal_limit",
                        severity=Severity.WARNING,
                        message=(
                            f"Jurisdiction `{request.jurisdiction}` has an official legal anchor for "
                            f"`{request.contaminant_family.value}`, but no exact curated legal-limit records are currently shipped for this family."
                        ),
                    )
                )
                notes.append(
                    "An official jurisdictional legal anchor exists for this family, but the repo does not yet ship exact curated legal-limit records for the requested lane."
                )
            if request.commodity_code or request.matrix_group or request.substance_key:
                lane_bits = [
                    bit
                    for bit in (
                        f"substance `{request.substance_key}`" if request.substance_key else None,
                        f"commodity `{request.commodity_code}`" if request.commodity_code else None,
                        f"matrix `{request.matrix_group}`" if request.matrix_group else None,
                    )
                    if bit is not None
                ]
                lane_text = ", ".join(lane_bits) if lane_bits else "requested lane"
                quality_flags.append(
                    QualityFlag(
                        code="no_curated_legal_limit_for_requested_lane",
                        severity=Severity.WARNING,
                        message=(
                            f"No curated contaminant legal-limit record matched {lane_text} in "
                            f"`{request.jurisdiction}`."
                        ),
                    )
                )
            notes.append(
                "Jurisdiction-specific contaminant legal-limit gaps are surfaced explicitly instead of borrowing values from another authority or matrix."
            )

    return ContaminantLegalLimitLookupResult(
        contaminant_family=request.contaminant_family,
        jurisdiction=request.jurisdiction,
        substance_key=request.substance_key,
        commodity_code=request.commodity_code,
        matrix_group=request.matrix_group,
        authority=request.authority,
        requested_lane_status=requested_lane_status,
        curated_scope_commodity_codes=curated_scope_commodity_codes,
        curated_scope_matrix_groups=curated_scope_matrix_groups,
        legal_authorities=legal_authorities,
        matched_records=matched_records,
        coverage_summaries=coverage_summaries,
        overall_submission_use=overall_submission_use,
        quality_flags=quality_flags,
        notes=notes,
    )


def lookup_method_support(
    defaults_registry: DefaultsRegistry,
    request: LookupMethodSupportRequest,
) -> MethodSupportLookupResult:
    authority_filter = _normalize_text(request.authority)
    jurisdiction_filter = _normalize_text(request.jurisdiction)
    methods = []
    for item in defaults_registry.list_method_registry_records():
        if item["contaminantFamily"] != request.contaminant_family.value:
            continue
        if authority_filter and item["authority"].strip().lower() != authority_filter:
            continue
        if not _jurisdiction_matches(item["jurisdiction"], request.jurisdiction):
            continue
        methods.append(MethodRegistryRecord.model_validate(item))
    methods.sort(key=lambda record: (record.authority.lower(), record.jurisdiction.lower(), record.method_id))

    legal_authorities = []
    for item in defaults_registry.list_legal_authority_records():
        if item["contaminantFamily"] != request.contaminant_family.value:
            continue
        if jurisdiction_filter:
            if item["jurisdiction"].strip().lower() != jurisdiction_filter:
                continue
        elif not _jurisdiction_matches(item["jurisdiction"], request.jurisdiction):
            continue
        legal_authorities.append(LegalAuthorityRecord.model_validate(item))
    legal_authorities.sort(key=lambda record: (record.jurisdiction.lower(), record.authority_id))

    emerging_contaminant = None
    notes = []
    submission_values = [record.submission_use for record in methods]
    if request.contaminant_family != ContaminantFamily.PESTICIDE_RESIDUE:
        emerging_contaminant = EmergingContaminantRecord.model_validate(
            defaults_registry.get_emerging_contaminant_record(request.contaminant_family.value)
        )
        submission_values.append(emerging_contaminant.submission_use)
        notes.extend(emerging_contaminant.notes)
        notes.extend(_family_specific_method_notes(request.contaminant_family))
    else:
        notes.append("EFSA is the first-class EU pesticide backbone for governed lookup outputs in this tranche.")
        if request.jurisdiction and request.jurisdiction.strip().lower() == "eu":
            notes.append(
                "The registry preserves the PRIMo 3.1 application boundary and keeps revision 4 as governed transition metadata."
            )

    overall_submission_use = _aggregate_submission_use(submission_values)
    submission_candidate_allowed = overall_submission_use == SubmissionUse.ALLOWED
    if emerging_contaminant is not None and emerging_contaminant.submission_use != SubmissionUse.ALLOWED:
        submission_candidate_allowed = False

    return MethodSupportLookupResult(
        contaminant_family=request.contaminant_family,
        jurisdiction=request.jurisdiction,
        authority=request.authority,
        methods=methods,
        legal_authorities=legal_authorities,
        emerging_contaminant=emerging_contaminant,
        overall_submission_use=overall_submission_use,
        submission_candidate_allowed=submission_candidate_allowed,
        notes=notes,
    )


def lookup_consumption_dataset_support(
    defaults_registry: DefaultsRegistry,
    request: LookupConsumptionDatasetSupportRequest,
) -> ConsumptionDatasetSupportLookupResult:
    family_filter = request.contaminant_family.value if request.contaminant_family is not None else None
    datasets = []
    for item in defaults_registry.list_consumption_dataset_records():
        if family_filter and item["contaminantFamily"] != family_filter:
            continue
        if request.dataset_id is not None and item["datasetId"] != request.dataset_id:
            continue
        if not _jurisdiction_matches(item["jurisdiction"], request.jurisdiction):
            continue
        datasets.append(ConsumptionDatasetRecord.model_validate(item))
    datasets.sort(key=lambda record: (record.authority.lower(), record.dataset_id))

    notes = []
    if family_filter == ContaminantFamily.PESTICIDE_RESIDUE.value and request.jurisdiction.strip().lower() == "eu":
        notes.append("EFSA food-consumption infrastructure and DietEx metadata are exposed as the primary EU pesticide dataset layer.")
    if family_filter is not None and family_filter != ContaminantFamily.PESTICIDE_RESIDUE.value:
        notes.extend(_family_specific_dataset_notes(ContaminantFamily(family_filter)))
    if not datasets:
        notes.append("No governed consumption-dataset records matched the requested filters.")

    return ConsumptionDatasetSupportLookupResult(
        jurisdiction=request.jurisdiction,
        dataset_id=request.dataset_id,
        contaminant_family=request.contaminant_family,
        datasets=datasets,
        overall_submission_use=_aggregate_submission_use([record.submission_use for record in datasets]),
        notes=notes,
    )


def lookup_reporting_profiles(
    defaults_registry: DefaultsRegistry,
    request: LookupReportingProfilesRequest,
) -> ReportingProfileLookupResult:
    authority_filter = _normalize_text(request.authority)
    matrix_group_filter = _normalize_text(request.matrix_group)
    profiles = []
    for item in defaults_registry.list_reporting_profile_records():
        if item["contaminantFamily"] != request.contaminant_family.value:
            continue
        if authority_filter and item["authority"].strip().lower() != authority_filter:
            continue
        if not _jurisdiction_matches(item["jurisdiction"], request.jurisdiction):
            continue
        if matrix_group_filter and not _matches_focus_text(item["matrixGroups"], request.matrix_group):
            continue
        profiles.append(ReportingProfileRecord.model_validate(item))
    profiles.sort(
        key=lambda record: (
            record.profile_role.value,
            record.authority.lower(),
            record.jurisdiction.lower(),
            record.profile_id,
        )
    )

    notes = _family_specific_reporting_profile_notes(request.contaminant_family)
    if request.matrix_group is not None:
        notes.append(f"Matrix-group filter applied: {request.matrix_group}.")
    if not profiles:
        notes.append("No governed reporting profiles matched the requested filters.")

    recommended_primary_profile_ids = [
        record.profile_id
        for record in profiles
        if record.profile_role == ReportingProfileRole.PRIMARY_REGULATORY
    ]

    return ReportingProfileLookupResult(
        contaminant_family=request.contaminant_family,
        jurisdiction=request.jurisdiction,
        authority=request.authority,
        matrix_group=request.matrix_group,
        profiles=profiles,
        recommended_primary_profile_ids=recommended_primary_profile_ids,
        notes=notes,
    )


def lookup_occurrence_evidence(
    defaults_registry: DefaultsRegistry,
    request: LookupOccurrenceEvidenceRequest,
) -> OccurrenceEvidenceLookupResult:
    authority_filter = _normalize_text(request.authority)
    analyte_filter = _normalize_text(request.analyte)
    matrix_group_filter = _normalize_text(request.matrix_group)
    records = []
    for item in defaults_registry.list_occurrence_evidence_records():
        if item["contaminantFamily"] != request.contaminant_family.value:
            continue
        if authority_filter and item["authority"].strip().lower() != authority_filter:
            continue
        if not _jurisdiction_matches(item["jurisdiction"], request.jurisdiction):
            continue
        if analyte_filter and not _matches_focus_text(item["analytes"], request.analyte):
            continue
        if matrix_group_filter and not _matches_focus_text(item["matrixGroups"], request.matrix_group):
            continue
        records.append(OccurrenceEvidenceRecord.model_validate(item))
    records.sort(key=lambda record: (record.authority.lower(), record.record_id))

    notes = _family_specific_occurrence_evidence_notes(request.contaminant_family)
    notes.extend(
        _currency_context_notes(
            defaults_registry,
            records,
            record_kind_label="Occurrence-evidence record",
        )
    )
    if request.analyte is not None:
        notes.append(f"Analyte filter applied: {request.analyte}.")
    if request.matrix_group is not None:
        notes.append(f"Matrix-group filter applied: {request.matrix_group}.")
    if not records:
        notes.append("No governed occurrence-evidence records matched the requested filters.")

    overall_submission_use = _aggregate_submission_use([record.submission_use for record in records])
    return OccurrenceEvidenceLookupResult(
        contaminant_family=request.contaminant_family,
        jurisdiction=request.jurisdiction,
        authority=request.authority,
        analyte=request.analyte,
        matrix_group=request.matrix_group,
        records=records,
        overall_submission_use=overall_submission_use,
        submission_candidate_allowed=overall_submission_use == SubmissionUse.ALLOWED,
        notes=notes,
    )


def lookup_analytical_method_evidence(
    defaults_registry: DefaultsRegistry,
    request: LookupAnalyticalMethodEvidenceRequest,
) -> AnalyticalMethodEvidenceLookupResult:
    authority_filter = _normalize_text(request.authority)
    analyte_filter = _normalize_text(request.analyte)
    matrix_group_filter = _normalize_text(request.matrix_group)
    records = []
    for item in defaults_registry.list_analytical_method_evidence_records():
        if item["contaminantFamily"] != request.contaminant_family.value:
            continue
        if authority_filter and item["authority"].strip().lower() != authority_filter:
            continue
        if not _jurisdiction_matches(item["jurisdiction"], request.jurisdiction):
            continue
        if analyte_filter and not _matches_focus_text(item["analytes"], request.analyte):
            continue
        if matrix_group_filter and not _matches_focus_text(item["matrixGroups"], request.matrix_group):
            continue
        records.append(AnalyticalMethodEvidenceRecord.model_validate(item))
    records.sort(key=lambda record: (record.authority.lower(), record.record_id))

    notes = _family_specific_analytical_method_evidence_notes(request.contaminant_family)
    notes.extend(
        _currency_context_notes(
            defaults_registry,
            records,
            record_kind_label="Analytical-method-evidence record",
        )
    )
    if request.analyte is not None:
        notes.append(f"Analyte filter applied: {request.analyte}.")
    if request.matrix_group is not None:
        notes.append(f"Matrix-group filter applied: {request.matrix_group}.")
    if not records:
        notes.append("No governed analytical-method-evidence records matched the requested filters.")

    overall_submission_use = _aggregate_submission_use([record.submission_use for record in records])
    return AnalyticalMethodEvidenceLookupResult(
        contaminant_family=request.contaminant_family,
        jurisdiction=request.jurisdiction,
        authority=request.authority,
        analyte=request.analyte,
        matrix_group=request.matrix_group,
        records=records,
        overall_submission_use=overall_submission_use,
        submission_candidate_allowed=overall_submission_use == SubmissionUse.ALLOWED,
        notes=notes,
    )


def lookup_metals_occurrence(
    defaults_registry: DefaultsRegistry,
    request: LookupMetalsOccurrenceRequest,
) -> MetalsOccurrenceLookupResult:
    authority_filter = _normalize_text(request.authority)
    records = []
    for item in defaults_registry.list_metals_occurrence_records():
        if item["contaminantFamily"] != request.contaminant_family.value:
            continue
        if authority_filter and item["authority"].strip().lower() != authority_filter:
            continue
        if not _jurisdiction_matches(item["jurisdiction"], request.jurisdiction):
            continue
        records.append(MetalsOccurrenceRecord.model_validate(item))
    records.sort(key=lambda record: (record.authority.lower(), record.record_id))

    notes = _family_specific_metals_occurrence_notes(request.contaminant_family)
    notes.extend(
        _currency_context_notes(
            defaults_registry,
            records,
            record_kind_label="Metals-occurrence record",
        )
    )
    if not records:
        notes.append("No governed metals-occurrence records matched the requested filters.")

    overall_submission_use = _aggregate_submission_use([record.submission_use for record in records])
    return MetalsOccurrenceLookupResult(
        contaminant_family=request.contaminant_family,
        jurisdiction=request.jurisdiction,
        authority=request.authority,
        records=records,
        overall_submission_use=overall_submission_use,
        submission_candidate_allowed=overall_submission_use == SubmissionUse.ALLOWED,
        notes=notes,
    )


def lookup_metals_review_focus(
    defaults_registry: DefaultsRegistry,
    request: LookupMetalsReviewFocusRequest,
) -> MetalsReviewFocusLookupResult:
    authority_filter = _normalize_text(request.authority)
    records = []
    for item in defaults_registry.list_metals_review_focus_records():
        if item["contaminantFamily"] != request.contaminant_family.value:
            continue
        if authority_filter and item["authority"].strip().lower() != authority_filter:
            continue
        if not _jurisdiction_matches(item["jurisdiction"], request.jurisdiction):
            continue
        if not _matches_focus_text(item["commodityGroups"], request.commodity_group):
            continue
        if not _matches_focus_text(item["focusFoods"], request.focus_food):
            continue
        records.append(MetalsReviewFocusRecord.model_validate(item))
    records.sort(key=lambda record: (record.authority.lower(), record.focus_id))

    notes = _family_specific_metals_review_focus_notes(request.contaminant_family)
    if request.commodity_group is not None:
        notes.append(f"Commodity-group filter applied: {request.commodity_group}.")
    if request.focus_food is not None:
        notes.append(f"Focus-food filter applied: {request.focus_food}.")
    if not records:
        notes.append("No governed metals-review-focus records matched the requested filters.")

    overall_submission_use = _aggregate_submission_use([record.submission_use for record in records])
    return MetalsReviewFocusLookupResult(
        contaminant_family=request.contaminant_family,
        jurisdiction=request.jurisdiction,
        authority=request.authority,
        commodity_group=request.commodity_group,
        focus_food=request.focus_food,
        records=records,
        overall_submission_use=overall_submission_use,
        submission_candidate_allowed=overall_submission_use == SubmissionUse.ALLOWED,
        notes=notes,
    )
