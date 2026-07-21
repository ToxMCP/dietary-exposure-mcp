#!/usr/bin/env python3
"""Conservatively reconcile OpenFoodTox 2.0 records against the 3.0 intermediate data."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import pandas as pd

OPENFOODTOX2_SUBSTANCE_MD5 = "ed0f19e97031b90af1d2311a47bc9d7f"

NAME_FIELDS = (
    "ChemicalName",
    "Description",
    "IupacName",
    "ReferenceSubstanceName",
    "RelatedSubstances.GroupCategoryInfo",
    "CAS name",
    "COM NAME [EFSA OFT2.0]",
    "Name",
    "PARAM NAME",
    "SUB NAME [EFSA OFT2.0]",
    "Trade name",
)
CAS_FIELDS = ("Inventory.CASNumber", "CAS number")


class ReconciliationError(RuntimeError):
    """Raised when reconciliation inputs cannot support deterministic comparison."""


def _decode_x_entities(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return re.sub(
        r"_x([0-9a-fA-F]{4})_",
        lambda match: chr(int(match.group(1), 16)),
        str(value),
    )


def _normalize_text(value: Any) -> str | None:
    decoded = _decode_x_entities(value)
    if decoded is None:
        return None
    normalized = unicodedata.normalize("NFKC", decoded).casefold().strip()
    return re.sub(r"\s+", " ", normalized) or None


def _canonical_name(value: Any) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    decomposed = unicodedata.normalize("NFKD", normalized)
    return "".join(character for character in decomposed if character.isalnum()) or None


def _normalize_cas(value: Any) -> str | None:
    decoded = _decode_x_entities(value)
    if decoded is None:
        return None
    digits = "".join(character for character in decoded if character.isdigit())
    return digits or None


def _normalize_unit(value: Any) -> str | None:
    normalized = _normalize_text(value)
    return normalized.replace("μ", "µ") if normalized else None


def _normalize_population(value: Any) -> str | None:
    normalized = _normalize_text(value)
    if normalized in {"consumer", "consumers"}:
        return "consumers"
    return normalized


def _normalize_reference_type(value: Any) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    if normalized.startswith("adi"):
        return "adi"
    if normalized.startswith("arfd"):
        return "arfd"
    return normalized


def _file_md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)  # noqa: S324 - pinned source identity
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _new_identity_indices(
    substances: list[dict[str, Any]],
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, set[str]]]:
    exact_names: dict[str, set[str]] = defaultdict(set)
    canonical_names: dict[str, set[str]] = defaultdict(set)
    cas_numbers: dict[str, set[str]] = defaultdict(set)
    for registry_entry in substances:
        substance_uuid = registry_entry["substanceUuid"]
        substance = registry_entry["substance"]
        reference_substance = registry_entry["referenceSubstance"]
        for field in NAME_FIELDS:
            value = substance.get(field, reference_substance.get(field))
            exact = _normalize_text(value)
            canonical = _canonical_name(value)
            if exact:
                exact_names[exact].add(substance_uuid)
            if canonical:
                canonical_names[canonical].add(substance_uuid)
        for field in CAS_FIELDS:
            cas_number = _normalize_cas(reference_substance.get(field))
            if cas_number:
                cas_numbers[cas_number].add(substance_uuid)
    return exact_names, canonical_names, cas_numbers


def _old_cas_index(frame: pd.DataFrame) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for _, row in frame.iterrows():
        substance_name = _normalize_text(row.get("Substance"))
        cas_number = _normalize_cas(row.get("CASNumber"))
        if substance_name and cas_number:
            index[substance_name].add(cas_number)
    return index


def _resolve_identity(
    substance_name: str,
    *,
    exact_names: dict[str, set[str]],
    canonical_names: dict[str, set[str]],
    new_cas_numbers: dict[str, set[str]],
    old_cas_numbers: dict[str, set[str]],
) -> tuple[str, set[str], list[str]]:
    exact_name = _normalize_text(substance_name)
    exact_hits = exact_names.get(exact_name or "", set())
    if exact_hits:
        return "exact_name", exact_hits, sorted(old_cas_numbers.get(exact_name or "", set()))

    canonical = _canonical_name(substance_name)
    canonical_hits = canonical_names.get(canonical or "", set())
    if canonical_hits:
        return (
            "canonical_name",
            canonical_hits,
            sorted(old_cas_numbers.get(exact_name or "", set())),
        )

    old_cas = sorted(old_cas_numbers.get(exact_name or "", set()))
    cas_hits: set[str] = set()
    for cas_number in old_cas:
        cas_hits.update(new_cas_numbers.get(cas_number, set()))
    return "cas", cas_hits, old_cas


def _assessment_years(record: dict[str, Any]) -> list[int]:
    years: set[int] = set()
    for dossier in record["dossiers"]:
        value = dossier["record"].get("LiteratureReference.DateOfEvaluation")
        match = re.match(r"^(\d{4})", str(value)) if value is not None else None
        if match:
            years.add(int(match.group(1)))
    return sorted(years)


def _persistent_identifiers(record: dict[str, Any]) -> list[str]:
    identifiers = {
        str(value)
        for dossier in record["dossiers"]
        if (
            value := dossier["record"].get(
                "LiteratureReference.LinkToPersistentIdentifier"
            )
        )
    }
    literature = record.get("referencedLiterature") or {}
    if literature.get("GeneralInfo.Source"):
        identifiers.add(str(literature["GeneralInfo.Source"]))
    return sorted(identifiers)


def _bound_candidates(
    *,
    record: dict[str, Any],
    section_name: str,
    payload: dict[str, Any],
    reference_type: str,
    value_prefix: str,
    unit_field: str,
    population_field: str,
    unit_other_field: str | None = None,
    population_other_field: str | None = None,
) -> list[dict[str, Any]]:
    unit_value = payload.get(unit_field)
    if unit_other_field and unit_value == "other:":
        unit_value = payload.get(unit_other_field)
    population_value = payload.get(population_field)
    if population_other_field and population_value == "other:":
        population_value = payload.get(population_other_field)

    candidates: list[dict[str, Any]] = []
    for bound in ("lower", "upper"):
        value_field = f"{value_prefix}.{bound}Value"
        if value_field not in payload:
            continue
        qualifier_field = f"{value_prefix}.{bound}Qualifier"
        candidates.append(
            {
                "recordKey": record["recordKey"],
                "toxReferenceDocumentUuid": record["toxReferenceDocumentUuid"],
                "section": section_name,
                "bound": bound,
                "referenceType": reference_type,
                "value": float(payload[value_field]),
                "qualifier": str(payload.get(qualifier_field, "=")),
                "unit": unit_value,
                "population": population_value,
                "assessmentYears": _assessment_years(record),
                "persistentIdentifiers": _persistent_identifiers(record),
                "reviewFlags": record["reviewFlags"],
            }
        )
    return candidates


def _candidate_index(records: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    candidates: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        substance_uuid = record["substanceUuid"]
        sections = record["valueSections"]
        adi = sections.get("acceptableDailyIntake")
        if adi:
            candidates[(substance_uuid, "adi")].extend(
                _bound_candidates(
                    record=record,
                    section_name="acceptableDailyIntake",
                    payload=adi,
                    reference_type="adi",
                    value_prefix="Adi",
                    unit_field="Adi.Unit",
                    population_field="Population",
                )
            )
        arfd = sections.get("acuteReferenceDose")
        if arfd:
            candidates[(substance_uuid, "arfd")].extend(
                _bound_candidates(
                    record=record,
                    section_name="acuteReferenceDose",
                    payload=arfd,
                    reference_type="arfd",
                    value_prefix="Arfd",
                    unit_field="Arfd.Unit",
                    population_field="Population",
                )
            )
        other = sections.get("otherReferenceValues")
        if other:
            descriptor = other.get("ReferenceValueDescriptor")
            if descriptor == "other:" and other.get("ReferenceValueDescriptor.Other"):
                descriptor = other["ReferenceValueDescriptor.Other"]
            reference_type = _normalize_reference_type(descriptor)
            if reference_type:
                candidates[(substance_uuid, reference_type)].extend(
                    _bound_candidates(
                        record=record,
                        section_name="otherReferenceValues",
                        payload=other,
                        reference_type=reference_type,
                        value_prefix="RefValue",
                        unit_field="RefValue.Unit",
                        unit_other_field="RefValue.Unit.Other",
                        population_field="Population",
                        population_other_field="Population.Other",
                    )
                )
    return candidates


def _numeric_equal(left: Any, right: Any) -> bool:
    return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-15)


def _filter_stage(
    candidates: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    return [candidate for candidate in candidates if predicate(candidate)]


def _reconcile_record(
    old_record: dict[str, Any],
    *,
    exact_names: dict[str, set[str]],
    canonical_names: dict[str, set[str]],
    new_cas_numbers: dict[str, set[str]],
    old_cas_numbers: dict[str, set[str]],
    candidates: dict[tuple[str, str], list[dict[str, Any]]],
) -> dict[str, Any]:
    old = old_record["openfoodtox"]
    identity_method, identity_hits, old_cas = _resolve_identity(
        old["Substance"],
        exact_names=exact_names,
        canonical_names=canonical_names,
        new_cas_numbers=new_cas_numbers,
        old_cas_numbers=old_cas_numbers,
    )
    result: dict[str, Any] = {
        "oldRecordId": old_record["recordId"],
        "old": old,
        "identityMethod": identity_method,
        "oldCasNumbers": old_cas,
        "candidateSubstanceUuids": sorted(identity_hits),
        "matchStageCounts": {},
        "candidateMatches": [],
    }
    if not identity_hits:
        result["classification"] = "unresolved_identity"
        return result
    if len(identity_hits) > 1:
        result["classification"] = "ambiguous_identity"
        return result

    substance_uuid = next(iter(identity_hits))
    reference_type = _normalize_reference_type(old["Assessment"])
    current = list(candidates.get((substance_uuid, reference_type or ""), []))
    result["matchStageCounts"]["referenceType"] = len(current)
    if not current:
        result["classification"] = "missing_reference_type_candidate"
        return result

    stages: tuple[
        tuple[str, str, Callable[[dict[str, Any]], bool]],
        ...,
    ] = (
        (
            "value",
            "changed_or_missing_value",
            lambda candidate: _numeric_equal(candidate["value"], old["value"]),
        ),
        (
            "unit",
            "changed_or_missing_unit",
            lambda candidate: _normalize_unit(candidate["unit"]) == _normalize_unit(old["unit"]),
        ),
        (
            "qualifier",
            "changed_or_missing_qualifier",
            lambda candidate: candidate["qualifier"] == old["qualfier"],
        ),
        (
            "population",
            "changed_or_missing_population",
            lambda candidate: _normalize_population(candidate["population"])
            == _normalize_population(old["Population"]),
        ),
        (
            "assessmentYear",
            "changed_or_missing_assessment_year",
            lambda candidate: int(old["Year"]) in candidate["assessmentYears"],
        ),
    )
    for stage_name, failure_classification, predicate in stages:
        previous = current
        current = _filter_stage(current, predicate)
        result["matchStageCounts"][stage_name] = len(current)
        if not current:
            result["classification"] = failure_classification
            result["candidateMatches"] = previous
            return result

    result["candidateMatches"] = current
    result["classification"] = (
        "unchanged_exact" if len(current) == 1 else "ambiguous_exact_duplicate"
    )
    return result


def build_reconciliation(
    old_provenance: dict[str, Any],
    old_substances: pd.DataFrame,
    extraction: dict[str, Any],
) -> dict[str, Any]:
    records = extraction.get("records")
    if not isinstance(records, list):
        raise ReconciliationError("OpenFoodTox 3.0 extraction has no records array")
    substances = extraction.get("substances")
    if not isinstance(substances, list):
        raise ReconciliationError("OpenFoodTox 3.0 extraction has no substances array")
    old_records = old_provenance.get("records")
    if not isinstance(old_records, list):
        raise ReconciliationError("OpenFoodTox 2.0 provenance has no records array")

    exact_names, canonical_names, new_cas_numbers = _new_identity_indices(substances)
    old_cas_numbers = _old_cas_index(old_substances)
    candidates = _candidate_index(records)
    reconciled = [
        _reconcile_record(
            old_record,
            exact_names=exact_names,
            canonical_names=canonical_names,
            new_cas_numbers=new_cas_numbers,
            old_cas_numbers=old_cas_numbers,
            candidates=candidates,
        )
        for old_record in old_records
    ]
    return {
        "reconciliationVersion": "1.0",
        "oldSource": {
            "sourceId": old_provenance.get("sourceId"),
            "sourceDoi": old_provenance.get("sourceDoi"),
            "sourceMd5": old_provenance.get("sourceMd5"),
            "sourceVersion": old_provenance.get("sourceVersion"),
        },
        "newSource": extraction.get("source"),
        "records": reconciled,
    }


def summarize_reconciliation(reconciliation: dict[str, Any]) -> dict[str, Any]:
    records = reconciliation["records"]
    classifications = Counter(record["classification"] for record in records)
    identity_methods = Counter(record["identityMethod"] for record in records)
    return {
        "summaryVersion": "1.0",
        "oldSource": reconciliation["oldSource"],
        "newSource": reconciliation["newSource"],
        "recordCount": len(records),
        "classificationCounts": dict(sorted(classifications.items())),
        "identityMethodCounts": dict(sorted(identity_methods.items())),
        "unchangedExactCount": classifications["unchanged_exact"],
        "reviewRequiredCount": len(records) - classifications["unchanged_exact"],
        "status": "review_required",
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old_provenance", type=Path)
    parser.add_argument("old_substances", type=Path)
    parser.add_argument("new_extraction", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ReconciliationError(f"expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    actual_md5 = _file_md5(args.old_substances)
    if actual_md5 != OPENFOODTOX2_SUBSTANCE_MD5:
        raise SystemExit(
            "OpenFoodTox 2.0 substance source checksum mismatch: "
            f"expected {OPENFOODTOX2_SUBSTANCE_MD5}, got {actual_md5}"
        )
    old_substances = pd.read_excel(
        args.old_substances,
        sheet_name="SUBSTANCECHARACTERISATION",
        dtype=object,
    )
    try:
        reconciliation = build_reconciliation(
            _load_json(args.old_provenance),
            old_substances,
            _load_json(args.new_extraction),
        )
    except ReconciliationError as exc:
        raise SystemExit(str(exc)) from exc
    _write_json(args.output, reconciliation)
    _write_json(args.summary_output, summarize_reconciliation(reconciliation))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
