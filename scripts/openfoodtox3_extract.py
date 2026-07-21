#!/usr/bin/env python3
"""Build a lossless, review-only intermediate representation of OpenFoodTox 3.0."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.openfoodtox3_inventory import SOURCE_MD5, SourceIntegrityError, build_inventory

SOURCE_ID = "efsa.openfoodtox"

SHEETS = (
    "DOSSIER",
    "DOSSIER_DOCS",
    "REF_SUB",
    "SUB",
    "LIT",
    "FLEX_SUM.ToxRefValues",
    "END_STUDY_REC.HumanHealth",
)

SECTION_PREFIXES = {
    "acceptableDailyIntake": (
        "HumanHealthHazardCharacteristics.AcceptableDailyIntake."
    ),
    "acceptableOperatorExposureLevel": (
        "HumanHealthHazardCharacteristics.AcceptableOperatorExposureLevel."
    ),
    "acuteAcceptableOperatorExposureLevel": (
        "HumanHealthHazardCharacteristics.AcuteAcceptableOperatorExposureLevel."
    ),
    "acuteReferenceDose": "HumanHealthHazardCharacteristics.AcuteReferenceDose.",
    "otherReferenceValues": "HumanHealthHazardCharacteristics.OtherReferenceValues.",
}

ROW_INDEX_COLUMNS = {"Unnamed: 0"}
TOX_IDENTITY_COLUMNS = {"Document UUID", "Definition", "Parent UUID"}
TOX_CONTEXT_COLUMNS = {"Discussion.Discussion", "KeyInformation.KeyInformation"}
HUMAN_HEALTH_REQUIRED_COLUMNS = {
    "Document UUID",
    "Definition",
    "Parent UUID",
    "AdministrativeData.Endpoint",
    "DataSource.Reference",
}


class ExtractionError(RuntimeError):
    """Raised when a lossless OpenFoodTox extraction cannot be guaranteed."""


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp | datetime | date):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _non_null_payload(row: pd.Series, *, excluded: set[str] | None = None) -> dict[str, Any]:
    excluded = excluded or set()
    payload: dict[str, Any] = {}
    for column, value in row.items():
        if str(column) in excluded:
            continue
        normalized = _json_value(value)
        if normalized is not None:
            payload[str(column)] = normalized
    return payload


def _unique_index(frame: pd.DataFrame, sheet_name: str) -> dict[str, pd.Series]:
    uuids = frame["Document UUID"].dropna().astype(str)
    duplicates = sorted(uuids[uuids.duplicated(keep=False)].unique())
    if duplicates:
        raise ExtractionError(
            f"{sheet_name} contains duplicate Document UUIDs: {', '.join(duplicates[:5])}"
        )
    return {
        str(row["Document UUID"]): row
        for _, row in frame.iterrows()
        if _json_value(row["Document UUID"]) is not None
    }


def _section_payloads(row: pd.Series) -> dict[str, dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    captured_columns: set[str] = set()
    for section_name, prefix in SECTION_PREFIXES.items():
        payload: dict[str, Any] = {}
        for column, value in row.items():
            column_name = str(column)
            if not column_name.startswith(prefix):
                continue
            captured_columns.add(column_name)
            normalized = _json_value(value)
            if normalized is not None:
                payload[column_name.removeprefix(prefix)] = normalized
        if payload:
            sections[section_name] = payload

    expected_section_columns = {
        str(column)
        for column in row.index
        if str(column).startswith("HumanHealthHazardCharacteristics.")
    }
    if captured_columns != expected_section_columns:
        missing = sorted(expected_section_columns - captured_columns)
        raise ExtractionError(f"unmapped toxicological section columns: {missing}")
    return sections


def _validate_tox_columns(frame: pd.DataFrame) -> None:
    known_columns = ROW_INDEX_COLUMNS | TOX_IDENTITY_COLUMNS | TOX_CONTEXT_COLUMNS
    unknown_columns = sorted(
        str(column)
        for column in frame.columns
        if str(column) not in known_columns
        and not any(str(column).startswith(prefix) for prefix in SECTION_PREFIXES.values())
    )
    if unknown_columns:
        raise ExtractionError(f"unmapped FLEX_SUM.ToxRefValues columns: {unknown_columns}")


def _dossier_links(frame: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    links: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for _, row in frame.iterrows():
        document_uuid = _json_value(row["DOCUMENT UUID"])
        dossier_uuid = _json_value(row["DOSSIER UUID"])
        if document_uuid is None or dossier_uuid is None:
            continue
        links[str(document_uuid)].append(
            {
                "dossierUuid": str(dossier_uuid),
                "documentType": _json_value(row.get("DOCUMENT TYPE")),
                "documentSubtype": _json_value(row.get("DOCUMENT SUBTYPE")),
            }
        )
    return links


def _substance_registry(
    substances: dict[str, pd.Series],
    reference_substances: dict[str, pd.Series],
) -> list[dict[str, Any]]:
    registry: list[dict[str, Any]] = []
    for substance_uuid, substance in sorted(substances.items()):
        reference_substance_uuid = _json_value(
            substance.get("ReferenceSubstance.ReferenceSubstance")
        )
        reference_substance = (
            reference_substances.get(str(reference_substance_uuid))
            if reference_substance_uuid is not None
            else None
        )
        if reference_substance is None:
            raise ExtractionError(
                f"unresolved reference-substance UUID {reference_substance_uuid} "
                f"for substance {substance_uuid}"
            )
        registry.append(
            {
                "substanceUuid": substance_uuid,
                "referenceSubstanceUuid": str(reference_substance_uuid),
                "substance": _non_null_payload(substance, excluded=ROW_INDEX_COLUMNS),
                "referenceSubstance": _non_null_payload(
                    reference_substance,
                    excluded=ROW_INDEX_COLUMNS,
                ),
            }
        )
    return registry


def _joined_context(
    tox_row: pd.Series,
    *,
    substances: dict[str, pd.Series],
    reference_substances: dict[str, pd.Series],
    dossiers: dict[str, pd.Series],
    literature: dict[str, pd.Series],
    dossier_links: dict[str, list[dict[str, Any]]],
    duplicate_tox_document_uuids: set[str],
    source_row_number: int,
) -> dict[str, Any]:
    tox_document_uuid = str(tox_row["Document UUID"])
    substance_uuid = str(tox_row["Parent UUID"])
    substance = substances.get(substance_uuid)
    if substance is None:
        raise ExtractionError(
            f"row {source_row_number}: unresolved substance UUID {substance_uuid}"
        )

    reference_substance_uuid = _json_value(
        substance.get("ReferenceSubstance.ReferenceSubstance")
    )
    reference_substance = (
        reference_substances.get(str(reference_substance_uuid))
        if reference_substance_uuid is not None
        else None
    )
    if reference_substance is None:
        raise ExtractionError(
            f"row {source_row_number}: unresolved reference-substance UUID "
            f"{reference_substance_uuid}"
        )

    links = sorted(
        dossier_links.get(tox_document_uuid, []),
        key=lambda item: (item["dossierUuid"], item.get("documentType") or ""),
    )
    dossier_context: list[dict[str, Any]] = []
    for link in links:
        dossier = dossiers.get(link["dossierUuid"])
        if dossier is None:
            raise ExtractionError(
                f"row {source_row_number}: unresolved dossier UUID {link['dossierUuid']}"
            )
        dossier_context.append(
            {
                "link": link,
                "record": _non_null_payload(dossier, excluded=ROW_INDEX_COLUMNS),
            }
        )

    opinion_uuid = _json_value(
        tox_row.get(
            "HumanHealthHazardCharacteristics.OtherReferenceValues.ReferenceToEFSAOpinion"
        )
    )
    opinion = literature.get(str(opinion_uuid)) if opinion_uuid is not None else None
    if opinion_uuid is not None and opinion is None:
        raise ExtractionError(
            f"row {source_row_number}: unresolved literature UUID {opinion_uuid}"
        )

    sections = _section_payloads(tox_row)
    review_flags: list[str] = []
    if not links:
        review_flags.append("missing_dossier_link")
    if tox_document_uuid in duplicate_tox_document_uuids:
        review_flags.append("duplicate_tox_document_uuid")
    if len({link["dossierUuid"] for link in links}) > 1:
        review_flags.append("multiple_dossier_links")
    if not sections:
        review_flags.append("no_toxicological_value_section")

    return {
        "recordKey": f"{tox_document_uuid}#row-{source_row_number}",
        "sourceSheet": "FLEX_SUM.ToxRefValues",
        "sourceRowNumber": source_row_number,
        "sourceRowIndex": _json_value(tox_row.get("Unnamed: 0")),
        "toxReferenceDocumentUuid": tox_document_uuid,
        "definition": _json_value(tox_row.get("Definition")),
        "substanceUuid": substance_uuid,
        "referenceSubstanceUuid": str(reference_substance_uuid),
        "substance": _non_null_payload(substance, excluded=ROW_INDEX_COLUMNS),
        "referenceSubstance": _non_null_payload(
            reference_substance,
            excluded=ROW_INDEX_COLUMNS,
        ),
        "dossiers": dossier_context,
        "referencedLiterature": (
            _non_null_payload(opinion, excluded=ROW_INDEX_COLUMNS)
            if opinion is not None
            else None
        ),
        "discussion": _json_value(tox_row.get("Discussion.Discussion")),
        "keyInformation": _json_value(tox_row.get("KeyInformation.KeyInformation")),
        "valueSections": sections,
        "reviewFlags": review_flags,
        "documentStatus": "dataset_current",
        "submissionUse": "review_required",
        "sourceIds": [SOURCE_ID],
    }


def _joined_human_health_context(
    row: pd.Series,
    *,
    substances: dict[str, pd.Series],
    reference_substances: dict[str, pd.Series],
    dossiers: dict[str, pd.Series],
    literature: dict[str, pd.Series],
    dossier_links: dict[str, list[dict[str, Any]]],
    duplicate_document_uuids: set[str],
    source_row_number: int,
) -> dict[str, Any]:
    document_uuid = str(row["Document UUID"])
    substance_uuid = str(row["Parent UUID"])
    substance = substances.get(substance_uuid)
    if substance is None:
        raise ExtractionError(
            f"END_STUDY_REC.HumanHealth row {source_row_number}: unresolved "
            f"substance UUID {substance_uuid}"
        )

    reference_substance_uuid = _json_value(
        substance.get("ReferenceSubstance.ReferenceSubstance")
    )
    reference_substance = (
        reference_substances.get(str(reference_substance_uuid))
        if reference_substance_uuid is not None
        else None
    )
    if reference_substance is None:
        raise ExtractionError(
            f"END_STUDY_REC.HumanHealth row {source_row_number}: unresolved "
            f"reference-substance UUID {reference_substance_uuid}"
        )

    links = sorted(
        dossier_links.get(document_uuid, []),
        key=lambda item: (item["dossierUuid"], item.get("documentType") or ""),
    )
    dossier_context: list[dict[str, Any]] = []
    for link in links:
        dossier = dossiers.get(link["dossierUuid"])
        if dossier is None:
            raise ExtractionError(
                f"END_STUDY_REC.HumanHealth row {source_row_number}: unresolved "
                f"dossier UUID {link['dossierUuid']}"
            )
        dossier_context.append(
            {
                "link": link,
                "record": _non_null_payload(dossier, excluded=ROW_INDEX_COLUMNS),
            }
        )

    literature_uuid = _json_value(row.get("DataSource.Reference"))
    referenced_literature = (
        literature.get(str(literature_uuid)) if literature_uuid is not None else None
    )
    if literature_uuid is not None and referenced_literature is None:
        raise ExtractionError(
            f"END_STUDY_REC.HumanHealth row {source_row_number}: unresolved "
            f"literature UUID {literature_uuid}"
        )

    review_flags: list[str] = []
    if not links:
        review_flags.append("missing_dossier_link")
    if document_uuid in duplicate_document_uuids:
        review_flags.append("duplicate_human_health_document_uuid")
    if len({link["dossierUuid"] for link in links}) > 1:
        review_flags.append("multiple_dossier_links")

    return {
        "recordKey": f"{document_uuid}#row-{source_row_number}",
        "sourceSheet": "END_STUDY_REC.HumanHealth",
        "sourceRowNumber": source_row_number,
        "sourceRowIndex": _json_value(row.get("Unnamed: 0")),
        "documentUuid": document_uuid,
        "definition": _json_value(row.get("Definition")),
        "substanceUuid": substance_uuid,
        "referenceSubstanceUuid": str(reference_substance_uuid),
        "substance": _non_null_payload(substance, excluded=ROW_INDEX_COLUMNS),
        "referenceSubstance": _non_null_payload(
            reference_substance,
            excluded=ROW_INDEX_COLUMNS,
        ),
        "dossiers": dossier_context,
        "dataSourceReferenceUuid": (
            str(literature_uuid) if literature_uuid is not None else None
        ),
        "referencedLiterature": (
            _non_null_payload(referenced_literature, excluded=ROW_INDEX_COLUMNS)
            if referenced_literature is not None
            else None
        ),
        "rawFields": _non_null_payload(row, excluded=ROW_INDEX_COLUMNS),
        "reviewFlags": review_flags,
        "documentStatus": "dataset_current",
        "submissionUse": "review_required",
        "sourceIds": [SOURCE_ID],
    }


def extract_openfoodtox3(
    path: Path,
    *,
    expected_md5: str = SOURCE_MD5,
) -> dict[str, Any]:
    inventory = build_inventory(path, expected_md5=expected_md5)
    frames = pd.read_excel(path, sheet_name=list(SHEETS), dtype=object)

    substances = _unique_index(frames["SUB"], "SUB")
    reference_substances = _unique_index(frames["REF_SUB"], "REF_SUB")
    dossiers = _unique_index(frames["DOSSIER"], "DOSSIER")
    literature = _unique_index(frames["LIT"], "LIT")
    dossier_links = _dossier_links(frames["DOSSIER_DOCS"])
    tox_frame = frames["FLEX_SUM.ToxRefValues"]
    _validate_tox_columns(tox_frame)
    tox_uuid_counts = Counter(
        str(value) for value in tox_frame["Document UUID"].dropna().astype(str)
    )
    duplicate_tox_document_uuids = {
        value for value, count in tox_uuid_counts.items() if count > 1
    }

    records = [
        _joined_context(
            row,
            substances=substances,
            reference_substances=reference_substances,
            dossiers=dossiers,
            literature=literature,
            dossier_links=dossier_links,
            duplicate_tox_document_uuids=duplicate_tox_document_uuids,
            source_row_number=int(index) + 2,
        )
        for index, row in tox_frame.iterrows()
    ]

    human_health_frame = frames["END_STUDY_REC.HumanHealth"]
    missing_human_health_columns = sorted(
        HUMAN_HEALTH_REQUIRED_COLUMNS - set(human_health_frame.columns)
    )
    if missing_human_health_columns:
        raise ExtractionError(
            "END_STUDY_REC.HumanHealth lacks required columns: "
            f"{missing_human_health_columns}"
        )
    human_health_uuid_counts = Counter(
        str(value)
        for value in human_health_frame["Document UUID"].dropna().astype(str)
    )
    duplicate_human_health_document_uuids = {
        value for value, count in human_health_uuid_counts.items() if count > 1
    }
    human_health_records = [
        _joined_human_health_context(
            row,
            substances=substances,
            reference_substances=reference_substances,
            dossiers=dossiers,
            literature=literature,
            dossier_links=dossier_links,
            duplicate_document_uuids=duplicate_human_health_document_uuids,
            source_row_number=int(index) + 2,
        )
        for index, row in human_health_frame.iterrows()
    ]

    return {
        "intermediateRepresentationVersion": "1.1",
        "source": inventory["source"],
        "workbookSchemaSha256": inventory["workbook"]["schemaSha256"],
        "substances": _substance_registry(substances, reference_substances),
        "records": records,
        "humanHealthRecords": human_health_records,
    }


def summarize_extraction(extraction: dict[str, Any]) -> dict[str, Any]:
    records = extraction["records"]
    human_health_records = extraction.get("humanHealthRecords", [])
    section_counts: Counter[str] = Counter()
    section_field_counts: Counter[str] = Counter()
    review_flag_counts: Counter[str] = Counter()
    other_descriptor_counts: Counter[str] = Counter()
    human_health_review_flag_counts: Counter[str] = Counter()
    human_health_structured_effect_value_count = 0
    human_health_narrative_reference_point_count = 0

    for record in records:
        review_flag_counts.update(record["reviewFlags"])
        for section_name, payload in record["valueSections"].items():
            section_counts[section_name] += 1
            section_field_counts[section_name] += len(payload)
        other = record["valueSections"].get("otherReferenceValues", {})
        descriptor = other.get("ReferenceValueDescriptor")
        descriptor_other = other.get("ReferenceValueDescriptor.Other")
        if descriptor is not None:
            resolved = descriptor_other if descriptor == "other:" and descriptor_other else descriptor
            other_descriptor_counts[str(resolved)] += 1

    for record in human_health_records:
        human_health_review_flag_counts.update(record.get("reviewFlags", []))
        raw_fields = record.get("rawFields", {})
        human_health_structured_effect_value_count += sum(
            "EffectLevel" in field
            and (field.endswith(".lowerValue") or field.endswith(".upperValue"))
            for field in raw_fields
        )
        human_health_narrative_reference_point_count += any(
            isinstance(value, str) and "Endpoint:" in value and "Value:" in value
            for value in raw_fields.values()
        )

    return {
        "summaryVersion": "1.1",
        "source": extraction["source"],
        "workbookSchemaSha256": extraction["workbookSchemaSha256"],
        "substanceCount": len(extraction["substances"]),
        "recordCount": len(records),
        "humanHealthRecordCount": len(human_health_records),
        "extractedSheetRecordCounts": {
            "END_STUDY_REC.HumanHealth": len(human_health_records),
            "FLEX_SUM.ToxRefValues": len(records),
        },
        "sectionRecordCounts": dict(sorted(section_counts.items())),
        "sectionPopulatedFieldCounts": dict(sorted(section_field_counts.items())),
        "reviewFlagCounts": dict(sorted(review_flag_counts.items())),
        "otherReferenceValueDescriptorCounts": dict(
            sorted(other_descriptor_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "humanHealthStructuredEffectValueCount": (
            human_health_structured_effect_value_count
        ),
        "humanHealthNarrativeReferencePointCount": (
            human_health_narrative_reference_point_count
        ),
        "humanHealthReviewFlagCounts": dict(
            sorted(human_health_review_flag_counts.items())
        ),
        "status": "review_required",
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path, help="Path to the pinned OpenFoodTox 3.0 XLSX")
    parser.add_argument("--output", type=Path, help="Write the full intermediate JSON")
    parser.add_argument("--summary-output", type=Path, help="Write the compact extraction summary")
    return parser.parse_args()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    if args.output is None and args.summary_output is None:
        raise SystemExit("at least one of --output or --summary-output is required")
    try:
        extraction = extract_openfoodtox3(args.workbook)
    except (ExtractionError, SourceIntegrityError) as exc:
        raise SystemExit(str(exc)) from exc

    if args.output:
        _write_json(args.output, extraction)
    if args.summary_output:
        _write_json(args.summary_output, summarize_extraction(extraction))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
