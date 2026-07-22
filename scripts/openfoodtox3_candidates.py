#!/usr/bin/env python3
"""Generate conservative Dietary MCP defaults from OpenFoodTox 3.0 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

SOURCE_ID = "efsa.openfoodtox"
SOURCE_VERSION = "v7"
SOURCE_DOI = "10.5281/zenodo.19388272"
SOURCE_PUBLICATION_DATE = "2026-04-30"
SOURCE_FILE = "OFT3.0 export repository.xlsx"
REVIEW_VERSION = "1.2"
REVIEW_SCHEMA_VERSION = "1.2"
REVIEW_GENERATED_AT = "2026-07-21T12:00:00Z"

SECTION_SOURCE_PREFIXES = {
    "acceptableDailyIntake": ("HumanHealthHazardCharacteristics.AcceptableDailyIntake."),
    "acuteReferenceDose": "HumanHealthHazardCharacteristics.AcuteReferenceDose.",
    "otherReferenceValues": ("HumanHealthHazardCharacteristics.OtherReferenceValues."),
}

# OpenFoodTox exports sparse row payloads. This list represents qualifier
# columns that actually exist in FLEX_SUM.ToxRefValues, including empty cells.
SECTION_QUALIFIER_FIELDS = {
    "acceptableDailyIntake": {"Adi.lowerQualifier", "Adi.upperQualifier"},
    "acuteReferenceDose": {"Arfd.upperQualifier"},
    "otherReferenceValues": {
        "RefValue.lowerQualifier",
        "RefValue.upperQualifier",
    },
}

AUTHORITATIVE_UNIT_CORRECTIONS = {
    (
        "6f1f0841-cc23-4389-875a-c1afe282638e#row-404",
        "arfd",
    ): {
        "authoritySourceId": "efsa.acetamiprid_imidacloprid.dnt.2013",
        "correctedUnit": "mg/kg bw",
        "reason": "The 2013 EFSA opinion expresses the ARfD without a per-day basis.",
    },
    (
        "8c5dd27d-d128-4735-822a-094f1746a837#row-7943",
        "arfd",
    ): {
        "authoritySourceId": "efsa.acetamiprid.peer_review.2016",
        "correctedUnit": "mg/kg bw",
        "reason": "The 2016 EFSA peer-review conclusion expresses the ARfD without a per-day basis.",
    },
    (
        "7f0e3478-4184-4dd9-936d-40f82b32ee4d#row-8153",
        "arfd",
    ): {
        "authoritySourceId": "efsa.acetamiprid.statement.2024",
        "correctedUnit": "mg/kg bw",
        "reason": "The 2024 EFSA statement expresses the ARfD without a per-day basis.",
    },
    (
        "d2727c60-cf21-4f54-a8c7-59b7ee1fc566#row-13510",
        "arfd",
    ): {
        "authoritySourceId": "efsa.glyphosate.peer_review.2023",
        "correctedUnit": "mg/kg bw",
        "reason": "The 2023 EFSA peer-review conclusion expresses the ARfD without a per-day basis.",
    },
    (
        "cb37ccd8-d85e-4f84-8f3b-7eb388f7f8ca#row-4951",
        "arfd",
    ): {
        "authoritySourceId": "efsa.acetamiprid_imidacloprid.dnt.2013",
        "correctedUnit": "mg/kg bw",
        "reason": "The 2013 EFSA opinion expresses the recommended ARfD without a per-day basis.",
    },
}

HIGH_IMPACT_REFERENCE_POINT_ADJUDICATIONS = {
    "0e049a9f-368c-40c0-b15c-6d2672fdc059": {
        "referenceType": "bmdl10_neoplastic",
        "assertionStatus": "selected_reference_point",
    },
    "3156ca56-59c3-46c9-8580-8379497cd7de": {
        "referenceType": "bmdl10_neurotoxicity",
        "assertionStatus": "selected_reference_point",
    },
    "d9c10174-6dd0-4f77-b4aa-8e0eaf40111c": {
        "referenceType": "bmdl05_skin_cancer",
        "assertionStatus": "selected_reference_point",
    },
    "1bec633b-5378-4e44-ab13-a5c0ac756787": {
        "referenceType": "bmdl01_developmental_neurotoxicity",
        "assertionStatus": "selected_reference_point",
    },
    "7fbbc975-942a-4dd6-9676-1c488cda33e4": {
        "referenceType": "bmdl10_nephrotoxicity",
        "assertionStatus": "selected_reference_point",
    },
}

DOI_SOURCE_IDS = {
    "10.2903/j.efsa.2008.148r": "efsa.imidacloprid.peer_review.2008",
    "10.2903/j.efsa.2010.1570": "efsa.lead.food.2010",
    "10.2903/j.efsa.2013.3471": "efsa.acetamiprid_imidacloprid.dnt.2013",
    "10.2903/j.efsa.2015.4104": "efsa.acrylamide.food.2015",
    "10.2903/j.efsa.2015.4302": "efsa.glyphosate.peer_review.2015",
    "10.2903/j.efsa.2016.4610": "efsa.acetamiprid.peer_review.2016",
    "10.2903/j.efsa.2019.5570": "efsa.imidacloprid.mrl_review.2019",
    "10.2903/j.efsa.2023.6857": "efsa.bpa.food.2023",
    "10.2903/j.efsa.2023.8164": "efsa.glyphosate.peer_review.2023",
    "10.2903/j.efsa.2024.8488": "efsa.inorganic_arsenic.food.2024",
    "10.2903/j.efsa.2024.8759": "efsa.acetamiprid.statement.2024",
}

ASSERTION_RELATION_OVERRIDES = {
    ("6f1f0841-cc23-4389-875a-c1afe282638e#row-404", "adi"): {
        "introducedByDoi": "10.2903/j.efsa.2013.3471",
        "assertionStatus": "recommended",
        "temporalStatus": "historical",
        "supersededByRecordKeys": ["7f0e3478-4184-4dd9-936d-40f82b32ee4d#row-8153"],
    },
    ("6f1f0841-cc23-4389-875a-c1afe282638e#row-404", "arfd"): {
        "introducedByDoi": "10.2903/j.efsa.2013.3471",
        "assertionStatus": "recommended",
        "temporalStatus": "historical",
        "supersededByRecordKeys": ["7f0e3478-4184-4dd9-936d-40f82b32ee4d#row-8153"],
    },
    ("7f0e3478-4184-4dd9-936d-40f82b32ee4d#row-8153", "adi"): {
        "introducedByDoi": "10.2903/j.efsa.2024.8759",
        "assertionStatus": "proposed",
        "temporalStatus": "current",
        "supersedesRecordKeys": [
            "6f1f0841-cc23-4389-875a-c1afe282638e#row-404",
            "8c5dd27d-d128-4735-822a-094f1746a837#row-7943",
        ],
    },
    ("7f0e3478-4184-4dd9-936d-40f82b32ee4d#row-8153", "arfd"): {
        "introducedByDoi": "10.2903/j.efsa.2024.8759",
        "assertionStatus": "proposed",
        "temporalStatus": "current",
        "supersedesRecordKeys": [
            "6f1f0841-cc23-4389-875a-c1afe282638e#row-404",
            "8c5dd27d-d128-4735-822a-094f1746a837#row-7943",
        ],
    },
    ("aff0ecb3-0bbe-4309-a9c8-3598568b387b#row-3733", "arfd"): {
        "introducedByDoi": "10.2903/j.efsa.2015.4302",
        "assertionStatus": "established",
        "temporalStatus": "historical",
        "supersededByRecordKeys": ["d2727c60-cf21-4f54-a8c7-59b7ee1fc566#row-13510"],
    },
    ("d2727c60-cf21-4f54-a8c7-59b7ee1fc566#row-13510", "arfd"): {
        "introducedByDoi": "10.2903/j.efsa.2023.8164",
        "assertionStatus": "established",
        "temporalStatus": "current",
        "supersedesRecordKeys": ["aff0ecb3-0bbe-4309-a9c8-3598568b387b#row-3733"],
    },
    ("c3e992fb-b762-46f2-943f-a697fbc81ad6#row-9487", "arfd"): {
        "introducedByDoi": "10.2903/j.efsa.2008.148r",
        "assertionStatus": "retained_in_mrl_assessment",
        "temporalStatus": "current",
    },
    ("cb37ccd8-d85e-4f84-8f3b-7eb388f7f8ca#row-4951", "arfd"): {
        "introducedByDoi": "10.2903/j.efsa.2013.3471",
        "assertionStatus": "recommended",
        "temporalStatus": "current",
    },
}

OTHER_DESCRIPTOR_TO_REFERENCE_TYPE = {
    "AI": "ai",
    "AR": "average_requirement",
    "Group ADI": "adi",
    "Group ARfD": "arfd",
    "MTDI": "mtdi",
    "MTDI (provisional)": "mtdi",
    "PRI": "pri",
    "RfD": "rfd",
    "Safe maximum intake level": "safe_maximum_intake_level",
    "TDI": "tdi",
    "TDI (group)": "tdi",
    "TDI (provisional)": "tdi",
    "TWI": "twi",
    "TWI (group)": "twi",
    "TWI (provisional)": "twi",
    "UL": "ul",
    "UL (provisional)": "ul",
    "safe maximum intake level (in food)": "safe_maximum_intake_level",
}

HUMAN_POPULATIONS = {
    "adolescents",
    "adult ('adolescents', 'adults', 'elderly' and 'very elderly')",
    "adults",
    "children",
    "consumers",
    "elderly",
    "infants",
    "lactating women",
    "other children",
    "pregnant women",
    "toddlers",
    "vegetarians",
    "very elderly",
    "young ('infants', 'toddlers' and 'other children')",
}

# These records are maintained against original EFSA outputs in curated packs.
# The bulk dataset remains corroborating evidence and cannot overwrite them.
CURATED_PRECEDENCE_KEYS = {
    "acetamiprid",
    "acrylamide",
    "bisphenol_a",
    "cadmium",
    "difenoconazole",
    "ethiprole",
    "glufosinate",
    "glyphosate",
    "imidacloprid",
    "inorganic_arsenic",
    "inorganic_mercury",
    "lead",
    "methylmercury",
    "oxamyl",
    "pfas_4_group",
    "tebuconazole",
    "tetraconazole",
}

HIGH_IMPACT_KEYS = {
    "acetamiprid",
    "acrylamide",
    "bisphenol_a",
    "cadmium",
    "glyphosate",
    "imidacloprid",
    "inorganic_arsenic",
    "inorganic_mercury",
    "lead",
    "methylmercury",
    "pfas_4_group",
}

SUBSTANCE_KEY_OVERRIDES = {
    "Acetamiprid": "acetamiprid",
    "Acrylamide": "acrylamide",
    "Arsenic, inorganic derivates": "inorganic_arsenic",
    "Bisphenol-A (Total)": "bisphenol_a",
    "Cadmium (Cd)": "cadmium",
    "Cadmium (total)": "cadmium",
    "Glufosinate-ammonium": "glufosinate",
    "Glyphosate": "glyphosate",
    "Imidacloprid": "imidacloprid",
    "Inorganic mercury": "inorganic_mercury",
    "Lead (Pb)": "lead",
    "Lead (total)": "lead",
    "Methylmercury": "methylmercury",
}

SPECIFIC_CONTAMINANT_FAMILIES = {
    "acrylamide": "acrylamide_process_contaminants",
    "bisphenol_a": "bisphenol_food_contact_migration",
    "cadmium": "cadmium_food_contaminants",
    "inorganic_arsenic": "inorganic_arsenic_food_contaminants",
    "inorganic_mercury": "mercury_food_contaminants",
    "lead": "lead_food_contaminants",
    "methylmercury": "mercury_food_contaminants",
    "pfas_4_group": "pfas_food_contaminants",
}


class CandidateGenerationError(RuntimeError):
    """Raised when candidate defaults cannot be generated deterministically."""


SOURCE_TEXT_REPAIRS = {
    "\u00c2\u00b5": "\u00b5",
    "\u00e2\u20ac\u00a2": "\u2022",
    "\u00e2\u20ac\u00a6": "\u2026",
    "\u00e2\u20ac\u0153": "\u201c",
    "\u00e2\u20ac\u02dc": "\u2018",
    "\u00e2\u20ac\u201c": "\u2013",
    "\u00e2\u2030\u00a4": "\u2264",
    "\u00e2\u2030\u00a5": "\u2265",
}


def _repair_source_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    repaired = value
    for encoded, decoded in SOURCE_TEXT_REPAIRS.items():
        repaired = repaired.replace(encoded, decoded)
    return repaired


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", str(_repair_source_text(value))).casefold().strip()
    normalized = normalized.replace("‘", "'").replace("’", "'")
    return re.sub(r"\s+", " ", normalized) or None


def _normalize_unit(value: Any) -> str | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None
    normalized = normalized.replace("μ", "u").replace("µ", "u")
    normalized = normalized.replace("body weight", "bw").replace("b.w.", "bw")
    return re.sub(r"\s+", " ", normalized)


def _units_equivalent(left: Any, right: Any) -> bool:
    return _normalize_unit(left) == _normalize_unit(right)


def _to_substance_key(name: str) -> str:
    if name in SUBSTANCE_KEY_OVERRIDES:
        return SUBSTANCE_KEY_OVERRIDES[name]
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_name = re.sub(r"[\-/,]", " ", ascii_name)
    ascii_name = re.sub(r"\([^)]*\)", "", ascii_name)
    key = re.sub(r"[^a-z0-9]+", "_", ascii_name.casefold()).strip("_")
    return key


def _display_name(record: dict[str, Any]) -> str | None:
    substance = record.get("substance") or {}
    reference_substance = record.get("referenceSubstance") or {}
    for value in (
        substance.get("ChemicalName"),
        reference_substance.get("ReferenceSubstanceName"),
        reference_substance.get("PARAM NAME"),
        reference_substance.get("Name"),
        reference_substance.get("IupacName"),
    ):
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _cas_number(record: dict[str, Any]) -> str | None:
    value = (record.get("referenceSubstance") or {}).get("Inventory.CASNumber")
    if value is None:
        return None
    normalized = re.sub(r"[^0-9]", "", str(value))
    return normalized or None


def _ec_number(record: dict[str, Any]) -> str | None:
    value = (record.get("referenceSubstance") or {}).get("Inventory.InventoryEntry")
    if value is None:
        return None
    match = re.search(r"\b\d{3}-\d{3}-\d\b", str(value))
    return match.group(0) if match else None


def _normalize_doi(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    normalized = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)", "", normalized, flags=re.I)
    normalized = normalized.strip().casefold()
    return normalized or None


def _existing_synonym_index(payload: dict[str, Any]) -> dict[str, str]:
    index: dict[str, str] = {}
    ambiguous: set[str] = set()
    for entry in payload.get("entries", []):
        key = str(entry["canonicalKey"])
        values = [key, *entry.get("synonyms", [])]
        for value in values:
            normalized = _normalize_text(value)
            if not normalized:
                continue
            if normalized in index and index[normalized] != key:
                ambiguous.add(normalized)
            else:
                index[normalized] = key
    for value in ambiguous:
        index.pop(value, None)
    return index


def _resolve_base_key(name: str, synonym_index: dict[str, str]) -> tuple[str, str]:
    if name in SUBSTANCE_KEY_OVERRIDES:
        return SUBSTANCE_KEY_OVERRIDES[name], "override"
    existing = synonym_index.get(_normalize_text(name) or "")
    if existing:
        return existing, "existing_synonym"
    generated = _to_substance_key(name)
    return generated, "generated"


def _resolve_substance_keys(
    records: list[dict[str, Any]],
    existing_synonyms: dict[str, Any],
) -> dict[str, str]:
    synonym_index = _existing_synonym_index(existing_synonyms)
    proposals: dict[str, tuple[str, str, str | None, str | None]] = {}
    groups: dict[str, list[str]] = defaultdict(list)
    for record in records:
        uuid = str(record["substanceUuid"])
        if uuid in proposals:
            continue
        name = _display_name(record)
        if not name:
            proposals[uuid] = (f"openfoodtox_{uuid[:8]}", "generated", None, _cas_number(record))
        else:
            base_key, origin = _resolve_base_key(name, synonym_index)
            if not base_key:
                base_key = f"openfoodtox_{uuid[:8]}"
            proposals[uuid] = (base_key, origin, _normalize_text(name), _cas_number(record))
        groups[proposals[uuid][0]].append(uuid)

    resolved: dict[str, str] = {}
    for base_key, uuids in sorted(groups.items()):
        identities = {(proposals[uuid][2], proposals[uuid][3]) for uuid in uuids}
        origins = {proposals[uuid][1] for uuid in uuids}
        if len(identities) <= 1 or origins & {"override", "existing_synonym"}:
            resolved.update({uuid: base_key for uuid in uuids})
            continue
        for uuid in sorted(uuids):
            cas = proposals[uuid][3]
            suffix = cas if cas else uuid.replace("-", "")[:12]
            resolved[uuid] = f"{base_key}_{suffix}"
    return resolved


def _resolved_other(payload: dict[str, Any], field: str, other_field: str) -> Any:
    value = payload.get(field)
    if value == "other:":
        return payload.get(other_field)
    return value


def _add_bounds(
    candidates: list[dict[str, Any]],
    *,
    record: dict[str, Any],
    payload: dict[str, Any],
    section: str,
    assessment_label: str,
    reference_type: str,
    value_prefix: str,
    unit_field: str,
    population_field: str,
    unit_other_field: str | None = None,
    population_other_field: str | None = None,
) -> None:
    raw_unit = payload.get(unit_field)
    unit = raw_unit
    resolved_unit_field = unit_field
    if unit_other_field:
        unit = _resolved_other(payload, unit_field, unit_other_field)
        if raw_unit == "other:" and payload.get(unit_other_field) is not None:
            resolved_unit_field = unit_other_field
    population = payload.get(population_field)
    if population_other_field:
        population = _resolved_other(payload, population_field, population_other_field)
    population_remarks = payload.get("Population.Remarks")
    for bound in ("lower", "upper"):
        value_field = f"{value_prefix}.{bound}Value"
        if payload.get(value_field) is None:
            continue
        qualifier_field = f"{value_prefix}.{bound}Qualifier"
        source_prefix = SECTION_SOURCE_PREFIXES[section]
        candidates.append(
            {
                "record": record,
                "payload": payload,
                "section": section,
                "assertionClass": "health_based_guidance_value",
                "sourceEncoding": "structured",
                "assessmentLabel": assessment_label,
                "referenceType": reference_type,
                "bound": bound,
                "value": payload[value_field],
                "unit": _repair_source_text(unit),
                "rawValue": payload[value_field],
                "rawUnit": unit,
                "rawUnitSelector": raw_unit,
                "normalizedUnit": _normalize_unit(unit),
                "sourceFieldPath": f"{source_prefix}{value_field}",
                "sourceUnitFieldPath": f"{source_prefix}{resolved_unit_field}",
                "sourceQualifierFieldPath": (
                    f"{source_prefix}{qualifier_field}"
                    if qualifier_field in SECTION_QUALIFIER_FIELDS[section]
                    else None
                ),
                "population": _repair_source_text(population),
                "rawPopulation": population,
                "populationRemarks": _repair_source_text(population_remarks),
                "rawPopulationRemarks": population_remarks,
                "qualifier": payload.get(qualifier_field),
                "qualifierWasExplicit": qualifier_field in payload,
            }
        )


def collect_source_candidates(extraction: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect value-bearing human dietary descriptors without applying runtime gates."""
    candidates: list[dict[str, Any]] = []
    records = extraction.get("records")
    if not isinstance(records, list):
        raise CandidateGenerationError("OpenFoodTox 3.0 extraction has no records array")
    for record in records:
        sections = record.get("valueSections") or {}
        if adi := sections.get("acceptableDailyIntake"):
            _add_bounds(
                candidates,
                record=record,
                payload=adi,
                section="acceptableDailyIntake",
                assessment_label="ADI",
                reference_type="adi",
                value_prefix="Adi",
                unit_field="Adi.Unit",
                population_field="Population",
            )
        if arfd := sections.get("acuteReferenceDose"):
            _add_bounds(
                candidates,
                record=record,
                payload=arfd,
                section="acuteReferenceDose",
                assessment_label="ARfD",
                reference_type="arfd",
                value_prefix="Arfd",
                unit_field="Arfd.Unit",
                population_field="Population",
            )
        if other := sections.get("otherReferenceValues"):
            descriptor = _resolved_other(
                other,
                "ReferenceValueDescriptor",
                "ReferenceValueDescriptor.Other",
            )
            reference_type = OTHER_DESCRIPTOR_TO_REFERENCE_TYPE.get(str(descriptor))
            if reference_type:
                _add_bounds(
                    candidates,
                    record=record,
                    payload=other,
                    section="otherReferenceValues",
                    assessment_label=str(descriptor),
                    reference_type=reference_type,
                    value_prefix="RefValue",
                    unit_field="RefValue.Unit",
                    unit_other_field="RefValue.Unit.Other",
                    population_field="Population",
                    population_other_field="Population.Other",
                )
    return candidates


_STRUCTURED_EFFECT_VALUE_RE = re.compile(
    r"^(?P<value_prefix>.+EffectLevel\.)(?P<bound>lower|upper)Value$"
)
_NARRATIVE_VALUE_RE = re.compile(
    r"^'?\s*(?P<qualifier><=|>=|=|<|>)?\s*"
    r"(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s+"
    r"(?P<unit>.+?)\s*$"
)


def _resolved_raw_field(
    raw_fields: dict[str, Any],
    field_path: str,
    other_field_path: str,
) -> tuple[Any, str, Any]:
    selector = raw_fields.get(field_path)
    if selector == "other:" and raw_fields.get(other_field_path) is not None:
        return raw_fields[other_field_path], other_field_path, selector
    return selector, field_path, selector


def _reference_point_type(document_uuid: str, descriptor: Any) -> str:
    adjudication = HIGH_IMPACT_REFERENCE_POINT_ADJUDICATIONS.get(document_uuid)
    if adjudication:
        return str(adjudication["referenceType"])
    normalized = re.sub(r"[^a-z0-9]+", "_", str(descriptor).casefold()).strip("_")
    return normalized or "reference_point"


def _structured_reference_point_candidates(record: dict[str, Any]) -> list[dict[str, Any]]:
    raw_fields = record.get("rawFields") or {}
    document_uuid = str(record.get("documentUuid") or "")
    candidates: list[dict[str, Any]] = []
    for field_path, raw_value in raw_fields.items():
        match = _STRUCTURED_EFFECT_VALUE_RE.match(str(field_path))
        if not match or raw_value is None:
            continue
        value_prefix = match.group("value_prefix")
        bound = match.group("bound")
        group_prefix = value_prefix.removesuffix("EffectLevel.")
        descriptor_field_path = f"{group_prefix}Endpoint"
        descriptor = raw_fields.get(descriptor_field_path)
        if descriptor is None:
            descriptor_field_path = f"{group_prefix}DoseDescriptor"
            descriptor = raw_fields.get(descriptor_field_path)
        if descriptor == "other:":
            other_path = f"{descriptor_field_path}.Other"
            if raw_fields.get(other_path) is not None:
                descriptor_field_path = other_path
                descriptor = raw_fields[other_path]
        if not (_normalize_text(descriptor) or "").startswith("bmdl"):
            continue

        unit_path = f"{value_prefix}Unit"
        unit, resolved_unit_path, unit_selector = _resolved_raw_field(
            raw_fields,
            unit_path,
            f"{unit_path}.Other",
        )
        qualifier_path = f"{value_prefix}{bound}Qualifier"
        context = {
            key: value
            for key, value in raw_fields.items()
            if str(key).startswith(group_prefix)
            and any(
                marker in str(key)
                for marker in (
                    "BasedOn",
                    "Basis",
                    "Endpoint",
                    "DoseDescriptor",
                    "RemarksOnResult",
                )
            )
        }
        adjudication = HIGH_IMPACT_REFERENCE_POINT_ADJUDICATIONS.get(
            document_uuid,
            {},
        )
        candidates.append(
            {
                "record": record,
                "payload": raw_fields,
                "section": "humanHealthEffectLevel",
                "assertionClass": "reference_point",
                "sourceEncoding": "structured",
                "assessmentLabel": str(descriptor),
                "referenceType": _reference_point_type(document_uuid, descriptor),
                "bound": bound,
                "value": raw_value,
                "rawValue": raw_value,
                "unit": _repair_source_text(unit),
                "rawUnit": unit,
                "rawUnitSelector": unit_selector,
                "normalizedUnit": _normalize_unit(unit),
                "qualifier": raw_fields.get(qualifier_path),
                "qualifierWasExplicit": qualifier_path in raw_fields,
                "sourceFieldPath": str(field_path),
                "sourceUnitFieldPath": resolved_unit_path,
                "sourceQualifierFieldPath": (
                    qualifier_path if qualifier_path in raw_fields else None
                ),
                "descriptorFieldPath": descriptor_field_path,
                "effectContext": context,
                "population": "humans",
                "populationRemarks": None,
                "assertionStatus": adjudication.get(
                    "assertionStatus",
                    "study_reference_point",
                ),
            }
        )
    return candidates


def _narrative_reference_point_candidates(record: dict[str, Any]) -> list[dict[str, Any]]:
    raw_fields = record.get("rawFields") or {}
    document_uuid = str(record.get("documentUuid") or "")
    candidates: list[dict[str, Any]] = []
    for field_path, raw_value in raw_fields.items():
        if (
            not isinstance(raw_value, str)
            or "Endpoint:" not in raw_value
            or "Value:" not in raw_value
        ):
            continue
        fields: dict[str, str] = {}
        for part in raw_value.split(";"):
            label, separator, value = part.partition(":")
            if not separator:
                continue
            fields[label.strip().casefold()] = value.strip().removeprefix("^").strip()
        descriptor = fields.get("endpoint")
        value_match = _NARRATIVE_VALUE_RE.fullmatch(fields.get("value", ""))
        if not (_normalize_text(descriptor) or "").startswith("bmdl") or value_match is None:
            continue
        adjudication = HIGH_IMPACT_REFERENCE_POINT_ADJUDICATIONS.get(
            document_uuid,
            {},
        )
        unit = value_match.group("unit")
        candidates.append(
            {
                "record": record,
                "payload": raw_fields,
                "section": "humanHealthNarrativeReferencePoint",
                "assertionClass": "reference_point",
                "sourceEncoding": "unstructured",
                "assessmentLabel": str(descriptor),
                "referenceType": _reference_point_type(document_uuid, descriptor),
                "bound": "narrative",
                "value": float(value_match.group("value")),
                "rawValue": value_match.group("value"),
                "unit": _repair_source_text(unit),
                "rawUnit": unit,
                "rawUnitSelector": unit,
                "normalizedUnit": _normalize_unit(unit),
                "qualifier": value_match.group("qualifier"),
                "qualifierWasExplicit": value_match.group("qualifier") is not None,
                "sourceFieldPath": str(field_path),
                "sourceUnitFieldPath": str(field_path),
                "sourceQualifierFieldPath": str(field_path),
                "descriptorFieldPath": str(field_path),
                "effectContext": {key: value for key, value in fields.items() if key != "value"},
                "rawNarrative": raw_value,
                "population": "humans",
                "populationRemarks": None,
                "assertionStatus": adjudication.get(
                    "assertionStatus",
                    "study_reference_point",
                ),
            }
        )
    return candidates


def collect_reference_point_candidates(extraction: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect explicit BMD reference points from human-health endpoint records."""
    records = extraction.get("humanHealthRecords")
    if not isinstance(records, list):
        return []
    candidates: list[dict[str, Any]] = []
    for record in records:
        candidates.extend(_structured_reference_point_candidates(record))
        candidates.extend(_narrative_reference_point_candidates(record))
    return sorted(
        candidates,
        key=lambda item: (
            str(item["record"]["recordKey"]),
            str(item["sourceFieldPath"]),
            str(item["bound"]),
        ),
    )


def _assessment_years(record: dict[str, Any]) -> list[int]:
    years: set[int] = set()
    for dossier in record.get("dossiers", []):
        value = dossier.get("record", {}).get("LiteratureReference.DateOfEvaluation")
        match = re.match(r"^(\d{4})", str(value)) if value is not None else None
        if match:
            years.add(int(match.group(1)))
    return sorted(years)


def _dossier_authorities(record: dict[str, Any]) -> set[str]:
    authorities: set[str] = set()
    for dossier in record.get("dossiers", []):
        group = _normalize_text(dossier.get("record", {}).get("Domain.ExpertGroup"))
        if not group:
            continue
        if group.startswith("efsa"):
            authorities.add("EFSA")
        elif group == "scf":
            authorities.add("SCF")
    return authorities


def _resolve_authority(candidate: dict[str, Any]) -> str | None:
    payload = candidate["payload"]
    body = _normalize_text(payload.get("AssessmentBody"))
    body_other = _normalize_text(payload.get("AssessmentBody.Other"))
    combined = " ".join(value for value in (body, body_other) if value)
    if "not from efsa" in combined:
        return None
    if "jmpr" in combined:
        return "JMPR"
    if "jecfa" in combined or "joint fao/who expert committee" in combined:
        return "JECFA"
    if "established by efsa" in combined or body == "efsa":
        return "EFSA"
    if body == "scf":
        return "SCF"
    authorities = _dossier_authorities(candidate["record"])
    return next(iter(authorities)) if len(authorities) == 1 else None


def _jurisdiction(authority: str) -> str:
    return "codex_global" if authority in {"JECFA", "JMPR"} else "eu"


def _contaminant_family(substance_key: str, record: dict[str, Any]) -> str:
    if substance_key in SPECIFIC_CONTAMINANT_FAMILIES:
        return SPECIFIC_CONTAMINANT_FAMILIES[substance_key]
    domains = {
        _normalize_text(dossier.get("record", {}).get("Domain.FoodDomain"))
        for dossier in record.get("dossiers", [])
    }
    return "pesticide_residue" if "pesticides" in domains else "food_contaminant"


def _population_label(candidate: dict[str, Any]) -> str | None:
    population = candidate.get("population")
    if population is None or not str(population).strip():
        return None
    label = str(population).strip()
    remarks = candidate.get("populationRemarks")
    if remarks is not None and str(remarks).strip():
        label = f"{label} - {str(remarks).strip()}"
    return label


def _persistent_identifiers(record: dict[str, Any]) -> list[str]:
    raw_identifiers = {
        str(value).strip()
        for dossier in record.get("dossiers", [])
        if (
            value := dossier.get("record", {}).get("LiteratureReference.LinkToPersistentIdentifier")
        )
    }
    literature = record.get("referencedLiterature") or {}
    if literature.get("GeneralInfo.Source"):
        raw_identifiers.add(str(literature["GeneralInfo.Source"]).strip())
    identifiers: set[str] = set()
    for value in raw_identifiers:
        doi_match = re.match(r"^doi\s*:\s*(.+)$", value, flags=re.IGNORECASE)
        identifiers.add(f"doi:{doi_match.group(1).strip().lower()}" if doi_match else value)
    return sorted(value for value in identifiers if value)


def _candidate_gate_reasons(candidate: dict[str, Any], substance_key: str) -> list[str]:
    reasons: list[str] = []
    record = candidate["record"]
    population = _normalize_text(candidate.get("population"))
    try:
        value = float(candidate["value"])
    except (TypeError, ValueError):
        value = math.nan
    if not math.isfinite(value) or value <= 0:
        reasons.append("invalid_nonpositive_or_nonfinite_value")
    if not candidate.get("unit") or not str(candidate["unit"]).strip():
        reasons.append("missing_unit")
    if not population:
        reasons.append("missing_population")
    elif population not in HUMAN_POPULATIONS:
        reasons.append("non_human_population")
    if "missing_dossier_link" in record.get("reviewFlags", []):
        reasons.append("missing_dossier_link")
    if _resolve_authority(candidate) is None:
        reasons.append("unresolved_assessment_authority")
    if substance_key in CURATED_PRECEDENCE_KEYS:
        reasons.append("curated_record_precedence")
    return reasons


def _record_id(candidate: dict[str, Any], substance_key: str) -> str:
    record = candidate["record"]
    material = "|".join(
        (
            str(record["recordKey"]),
            candidate["section"],
            candidate["bound"],
            candidate["referenceType"],
        )
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    return f"efsa.openfoodtox.v3.{substance_key}.{candidate['referenceType']}.{digest}"


def _runtime_notes(candidate: dict[str, Any]) -> list[str]:
    record = candidate["record"]
    years = _assessment_years(record)
    identifiers = _persistent_identifiers(record)
    notes = [
        "Review-only value extracted from checksum-pinned EFSA OpenFoodTox 3.0 v7.",
        (
            f"Source recordKey={record['recordKey']}, section={candidate['section']}, "
            f"bound={candidate['bound']}; no canonical or current value was selected."
        ),
    ]
    if years:
        notes.append(f"Structural dossier assessment years: {', '.join(map(str, years))}.")
    if identifiers:
        notes.append(
            "Structural dossier persistent identifiers (not assertion-level support): "
            f"{', '.join(identifiers)}."
        )
    if record.get("reviewFlags"):
        notes.append(f"Source review flags: {', '.join(sorted(record['reviewFlags']))}.")
    notes.append("The original EFSA scientific output remains authoritative for regulatory use.")
    return notes


def _build_runtime_record(
    candidate: dict[str, Any],
    substance_key: str,
) -> dict[str, Any]:
    record = candidate["record"]
    authority = _resolve_authority(candidate)
    if authority is None:
        raise CandidateGenerationError("runtime record requested for unresolved authority")
    years = _assessment_years(record)
    qualifier = candidate.get("qualifier")
    if qualifier is None or not str(qualifier).strip():
        qualifier = "="
    return {
        "recordId": _record_id(candidate, substance_key),
        "substanceKey": substance_key,
        "substanceName": _display_name(record) or substance_key,
        "referenceType": candidate["referenceType"],
        "authority": authority,
        "jurisdiction": _jurisdiction(authority),
        "contaminantFamily": _contaminant_family(substance_key, record),
        "value": float(candidate["value"]),
        "unit": str(candidate["unit"]).strip(),
        "qualifier": str(qualifier).strip(),
        "assessmentLabel": candidate["assessmentLabel"],
        "assessmentYear": years[0] if len(years) == 1 else None,
        "population": _population_label(candidate),
        "sourceOutputId": None,
        "sourceIds": [SOURCE_ID],
        "databaseSourceId": SOURCE_ID,
        "documentStatus": "dataset_current",
        "submissionUse": "review_required",
        "effectiveDate": None,
        "notes": _runtime_notes(candidate),
    }


def _dossier_provenance(record: dict[str, Any]) -> list[dict[str, Any]]:
    dossiers: list[dict[str, Any]] = []
    for dossier in record.get("dossiers", []):
        link = dossier.get("link") or {}
        source = dossier.get("record") or {}
        dossiers.append(
            {
                "dossierUuid": link.get("dossierUuid"),
                "expertGroup": source.get("Domain.ExpertGroup"),
                "foodDomain": source.get("Domain.FoodDomain"),
                "efsaQuestionNumber": source.get("DataSource.EFSAQuestionNumber"),
                "assessmentDate": source.get("LiteratureReference.DateOfEvaluation"),
                "outputTitle": source.get("LiteratureReference.EFSAOutputTitle"),
                "persistentIdentifier": source.get(
                    "LiteratureReference.LinkToPersistentIdentifier"
                ),
            }
        )
    return dossiers


def _build_provenance_record(
    candidate: dict[str, Any],
    runtime_record: dict[str, Any],
    migration_classification: str,
) -> dict[str, Any]:
    record = candidate["record"]
    payload = candidate["payload"]
    return {
        "recordId": runtime_record["recordId"],
        "migrationClassification": migration_classification,
        "openfoodtox3": {
            "recordKey": record["recordKey"],
            "sourceRowNumber": record.get("sourceRowNumber"),
            "toxReferenceDocumentUuid": record.get("toxReferenceDocumentUuid"),
            "substanceUuid": record.get("substanceUuid"),
            "referenceSubstanceUuid": record.get("referenceSubstanceUuid"),
            "substanceName": _display_name(record),
            "casNumber": (record.get("referenceSubstance") or {}).get("Inventory.CASNumber"),
            "ecNumber": _ec_number(record),
            "sourceFile": SOURCE_FILE,
            "sourceSheet": record.get("sourceSheet", "FLEX_SUM.ToxRefValues"),
            "section": candidate["section"],
            "assertionClass": candidate.get(
                "assertionClass",
                "health_based_guidance_value",
            ),
            "sourceEncoding": candidate.get("sourceEncoding", "structured"),
            "descriptor": candidate["assessmentLabel"],
            "bound": candidate["bound"],
            "value": candidate["value"],
            "unit": candidate.get("unit"),
            "rawValue": candidate.get("rawValue"),
            "rawUnit": candidate.get("rawUnit"),
            "rawUnitSelector": candidate.get("rawUnitSelector"),
            "normalizedUnit": candidate.get("normalizedUnit"),
            "qualifier": candidate.get("qualifier"),
            "qualifierWasExplicit": candidate["qualifierWasExplicit"],
            "sourceFieldPath": candidate.get("sourceFieldPath"),
            "sourceUnitFieldPath": candidate.get("sourceUnitFieldPath"),
            "sourceQualifierFieldPath": candidate.get("sourceQualifierFieldPath"),
            "population": candidate.get("population"),
            "populationRemarks": candidate.get("populationRemarks"),
            **(
                {"rawPopulation": candidate.get("rawPopulation")}
                if candidate.get("rawPopulation") != candidate.get("population")
                else {}
            ),
            **(
                {"rawPopulationRemarks": candidate.get("rawPopulationRemarks")}
                if candidate.get("rawPopulationRemarks") != candidate.get("populationRemarks")
                else {}
            ),
            "assessmentBody": payload.get("AssessmentBody"),
            "assessmentBodyOther": payload.get("AssessmentBody.Other"),
            "criticalEndpointUuid": payload.get("CriticalEndpoint"),
            "overallUncertainty": payload.get("OverallUncertainty"),
            "justificationOverallUncertainty": payload.get("JustificationOverallUf"),
            "dossiers": _dossier_provenance(record),
            "referencedLiterature": record.get("referencedLiterature"),
            "sourceReviewFlags": record.get("reviewFlags", []),
        },
    }


def _old_record_indices(
    old_records: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], set[str]]:
    by_key_type: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    keys: set[str] = set()
    for record in old_records:
        key = str(record.get("substanceKey", ""))
        reference_type = _normalize_text(record.get("referenceType")) or ""
        keys.add(key)
        by_key_type[(key, reference_type)].append(record)
    return by_key_type, keys


def _same_number(left: Any, right: Any) -> bool:
    try:
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-15)
    except (TypeError, ValueError):
        return False


def _migration_classification(
    record: dict[str, Any],
    old_by_key_type: dict[tuple[str, str], list[dict[str, Any]]],
    old_keys: set[str],
) -> str:
    key = record["substanceKey"]
    reference_type = _normalize_text(record["referenceType"]) or ""
    old_candidates = old_by_key_type.get((key, reference_type), [])
    if not old_candidates:
        return (
            "new_to_2023_runtime_reference_type_candidate"
            if key in old_keys
            else "new_to_2023_runtime_substance_candidate"
        )
    for old in old_candidates:
        if (
            _same_number(record["value"], old.get("value"))
            and _normalize_unit(record["unit"]) == _normalize_unit(old.get("unit"))
            and _normalize_text(record["population"]) == _normalize_text(old.get("population"))
            and record["assessmentYear"] == old.get("assessmentYear")
        ):
            return "legacy_runtime_context_exact"
    if any(
        _same_number(record["value"], old.get("value"))
        and _normalize_unit(record["unit"]) == _normalize_unit(old.get("unit"))
        for old in old_candidates
    ):
        return "legacy_runtime_value_with_changed_or_ambiguous_context"
    return "legacy_runtime_value_or_unit_changed_or_ambiguous"


def _apply_conflict_groups(records: list[dict[str, Any]]) -> None:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[
            (
                record["substanceKey"],
                record["referenceType"],
                record["authority"],
                record["jurisdiction"],
            )
        ].append(record)
    for (substance_key, reference_type, _, _), group in groups.items():
        if len(group) < 2:
            continue
        conflict_id = f"{substance_key}.{reference_type}.openfoodtox3_variation"
        for record in group:
            record["conflictGroupId"] = conflict_id


def _merge_synonyms(
    existing: dict[str, Any],
    source_records: list[dict[str, Any]],
    keys_by_uuid: dict[str, str],
) -> dict[str, Any]:
    entries = [dict(entry) for entry in existing.get("entries", [])]
    by_key = {str(entry["canonicalKey"]): entry for entry in entries}
    additions: dict[str, set[str]] = defaultdict(set)
    for record in source_records:
        name = _display_name(record)
        if name:
            additions[keys_by_uuid[str(record["substanceUuid"])]].add(name)
    for key, names in sorted(additions.items()):
        entry = by_key.get(key)
        if entry is None:
            entry = {
                "canonicalKey": key,
                "synonyms": [],
                "sourceId": f"dietary.substance_synonyms.{key}",
            }
            entries.append(entry)
            by_key[key] = entry
        existing_names = {_normalize_text(value) for value in entry.get("synonyms", [])}
        appended = [name for name in sorted(names) if _normalize_text(name) not in existing_names]
        entry["synonyms"] = [*entry.get("synonyms", []), *appended]
    return {
        "defaultsVersion": "v1",
        "kind": "substance_synonyms",
        "entries": entries,
    }


def _curated_efsa_records(curated_records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for record in curated_records:
        if record.get("substanceKey") not in HIGH_IMPACT_KEYS:
            continue
        if record.get("documentStatus") == "superseded":
            continue
        source_ids = set(record.get("sourceIds", []))
        if any(source_id.startswith("efsa.") for source_id in source_ids):
            selected.append(record)
    return selected


def _source_reference(
    *,
    doi: Any,
    dossier_uuid: str | None = None,
    literature_uuid: str | None = None,
    title: Any = None,
    assessment_date: Any = None,
) -> dict[str, Any]:
    normalized_doi = _normalize_doi(doi)
    return {
        "sourceId": DOI_SOURCE_IDS.get(normalized_doi or ""),
        "doi": normalized_doi,
        "dossierUuid": dossier_uuid,
        "literatureUuid": literature_uuid,
        "title": str(title) if title is not None else None,
        "assessmentDate": (str(assessment_date) if assessment_date is not None else None),
    }


def _dossier_membership(record: dict[str, Any]) -> list[dict[str, Any]]:
    memberships: list[dict[str, Any]] = []
    for dossier in record.get("dossiers", []):
        link = dossier.get("link") or {}
        source = dossier.get("record") or {}
        memberships.append(
            _source_reference(
                doi=source.get("LiteratureReference.LinkToPersistentIdentifier"),
                dossier_uuid=link.get("dossierUuid"),
                title=source.get("LiteratureReference.EFSAOutputTitle"),
                assessment_date=source.get("LiteratureReference.DateOfEvaluation"),
            )
        )
    return sorted(
        memberships,
        key=lambda item: (
            item.get("assessmentDate") or "",
            item.get("dossierUuid") or "",
        ),
    )


def _referenced_literature_source(record: dict[str, Any]) -> dict[str, Any] | None:
    literature = record.get("referencedLiterature") or {}
    doi = _normalize_doi(literature.get("GeneralInfo.Source"))
    if not doi:
        return None
    return _source_reference(
        doi=doi,
        literature_uuid=(literature.get("Document UUID") or record.get("dataSourceReferenceUuid")),
        title=literature.get("GeneralInfo.Name"),
        assessment_date=literature.get("GeneralInfo.ReferenceYear"),
    )


def _assertion_relationships(candidate: dict[str, Any]) -> dict[str, Any]:
    record = candidate["record"]
    memberships = _dossier_membership(record)
    override = ASSERTION_RELATION_OVERRIDES.get(
        (record["recordKey"], candidate["referenceType"]),
        {},
    )
    introduced_by_doi = _normalize_doi(override.get("introducedByDoi"))
    introduced_by: list[dict[str, Any]] = []
    if introduced_by_doi:
        introduced_by = [item for item in memberships if item.get("doi") == introduced_by_doi]
    else:
        literature_source = _referenced_literature_source(record)
        if literature_source is not None:
            matching_membership = next(
                (item for item in memberships if item.get("doi") == literature_source.get("doi")),
                None,
            )
            introduced_by = [matching_membership or literature_source]
        elif len(memberships) == 1:
            introduced_by = list(memberships)
    introduced_dois = {item.get("doi") for item in introduced_by}
    mentioned_in = [item for item in memberships if item.get("doi") not in introduced_dois]
    return {
        "introducedBy": introduced_by,
        "mentionedIn": mentioned_in,
        "dossierMembership": memberships,
        "supersedesRecordKeys": override.get("supersedesRecordKeys", []),
        "supersededByRecordKeys": override.get("supersededByRecordKeys", []),
        "assertionStatus": override.get(
            "assertionStatus",
            candidate.get("assertionStatus", "established"),
        ),
        "temporalStatus": override.get("temporalStatus"),
    }


def _candidate_temporal_status(
    candidate: dict[str, Any],
    *,
    exact: bool,
    latest_assessment_year: int | None,
) -> str:
    relationships = _assertion_relationships(candidate)
    if relationships["temporalStatus"]:
        return str(relationships["temporalStatus"])
    years = _assessment_years(candidate["record"])
    if not exact:
        return "historical"
    if latest_assessment_year is None or not years:
        return "currentness_uncertain"
    return "current" if max(years) == latest_assessment_year else "historical"


def _candidate_review_payload(
    candidate: dict[str, Any],
    curated: dict[str, Any],
    *,
    latest_assessment_year: int | None,
) -> dict[str, Any]:
    record = candidate["record"]
    unit_correction = AUTHORITATIVE_UNIT_CORRECTIONS.get(
        (str(record["recordKey"]), str(candidate["referenceType"]))
    )
    corrected_unit = (
        str(unit_correction["correctedUnit"])
        if unit_correction is not None
        else candidate.get("unit")
    )
    exact = _same_number(curated.get("value"), candidate["value"]) and _units_equivalent(
        curated.get("unit"), corrected_unit
    )
    relationships = _assertion_relationships(candidate)
    temporal_status = _candidate_temporal_status(
        candidate,
        exact=exact,
        latest_assessment_year=latest_assessment_year,
    )
    source_encoding_flags: list[str] = []
    if (
        candidate.get("assertionClass") == "health_based_guidance_value"
        and candidate.get("bound") == "upper"
    ):
        source_encoding_flags.append("hbgv_encoded_in_upper_value_field")
    if candidate.get("sourceEncoding") == "unstructured":
        source_encoding_flags.append("value_encoded_in_narrative_field")
    if unit_correction is not None:
        source_encoding_flags.append("primary_source_unit_correction_applied")
    relationship_to_curated = "exact_match"
    if unit_correction is not None and exact:
        relationship_to_curated = "primary_source_unit_correction"
    elif not exact:
        relationship_to_curated = (
            "different_current_value"
            if temporal_status == "current"
            else "different_historical_value"
        )
    return {
        "recordKey": record["recordKey"],
        "sourceFile": SOURCE_FILE,
        "sourceSheet": record.get("sourceSheet", "FLEX_SUM.ToxRefValues"),
        "sourceRowNumber": record.get("sourceRowNumber"),
        "documentUuid": (record.get("toxReferenceDocumentUuid") or record.get("documentUuid")),
        "substanceUuid": record.get("substanceUuid"),
        "referenceSubstanceUuid": record.get("referenceSubstanceUuid"),
        "casNumber": (record.get("referenceSubstance") or {}).get("Inventory.CASNumber"),
        "ecNumber": _ec_number(record),
        "assertionClass": candidate.get(
            "assertionClass",
            "health_based_guidance_value",
        ),
        "sourceEncoding": candidate.get("sourceEncoding", "structured"),
        "sourceEncodingFlags": source_encoding_flags,
        "descriptor": candidate.get("assessmentLabel"),
        "descriptorFieldPath": candidate.get("descriptorFieldPath"),
        "bound": candidate.get("bound"),
        "sourceFieldPath": candidate.get("sourceFieldPath"),
        "sourceUnitFieldPath": candidate.get("sourceUnitFieldPath"),
        "sourceQualifierFieldPath": candidate.get("sourceQualifierFieldPath"),
        "rawValue": candidate.get("rawValue", candidate.get("value")),
        "rawUnit": candidate.get("rawUnit", candidate.get("unit")),
        "rawUnitSelector": candidate.get("rawUnitSelector"),
        "rawQualifier": candidate.get("qualifier"),
        "normalizedValue": float(candidate["value"]),
        "normalizedUnit": _normalize_unit(corrected_unit),
        "unitCorrection": (
            {
                **unit_correction,
                "rawUnit": candidate.get("rawUnit", candidate.get("unit")),
            }
            if unit_correction is not None
            else None
        ),
        "population": candidate.get("population"),
        "assessmentYears": _assessment_years(record),
        "relationshipToCurated": relationship_to_curated,
        "temporalStatus": temporal_status,
        "assertionStatus": relationships["assertionStatus"],
        "introducedBy": relationships["introducedBy"],
        "mentionedIn": relationships["mentionedIn"],
        "dossierMembership": relationships["dossierMembership"],
        "supersedesRecordKeys": relationships["supersedesRecordKeys"],
        "supersededByRecordKeys": relationships["supersededByRecordKeys"],
        "effectContext": candidate.get("effectContext"),
        "rawNarrative": candidate.get("rawNarrative"),
    }


def _support_status(
    curated: dict[str, Any],
    candidates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
) -> str:
    supported = [
        (candidate, comparison)
        for candidate, comparison in zip(candidates, comparisons, strict=True)
        if comparison["relationshipToCurated"] in {"exact_match", "primary_source_unit_correction"}
    ]
    if not candidates:
        return "not_found_after_cross_sheet_search"
    if not supported:
        return "conflicting_values"
    current_supported = [
        pair for pair in supported if pair[1]["temporalStatus"] == "current"
    ] or supported
    if any(
        comparison["relationshipToCurated"] == "primary_source_unit_correction"
        for _, comparison in current_supported
    ):
        return "supported_after_primary_source_unit_correction"
    if any(
        "hbgv_encoded_in_upper_value_field" in comparison["sourceEncodingFlags"]
        for _, comparison in current_supported
    ):
        return "supported_but_source_encoding_anomalous"
    if any(candidate.get("sourceEncoding") == "unstructured" for candidate, _ in current_supported):
        return "exact_supported_unstructured"
    if any(
        str(curated.get("unit")) != str(candidate.get("unit")) for candidate, _ in current_supported
    ):
        return "supported_after_unit_normalization"
    return "exact_supported_structured"


def _curated_assertion_metadata(curated: dict[str, Any]) -> dict[str, Any]:
    record_id = str(curated["recordId"])
    reference_type = str(curated["referenceType"])
    assertion_class = (
        "reference_point" if reference_type.startswith("bmdl") else "health_based_guidance_value"
    )
    assertion_status = "established"
    regulatory_adoption_status = None
    regulatory_follow_up_source_ids: list[str] = []
    supersedes_record_ids: list[str] = []
    if record_id.startswith("efsa.openfoodtox.acetamiprid."):
        assertion_status = "proposed"
        regulatory_adoption_status = "used_in_binding_mrl_risk_management"
        regulatory_follow_up_source_ids = ["eu.reg.2025_158"]
    elif record_id == "efsa.openfoodtox.imidacloprid.arfd":
        assertion_status = "recommended"
        regulatory_adoption_status = "recommendation_not_unconditionally_adopted"
        regulatory_follow_up_source_ids = ["efsa.imidacloprid.mrl_review.2019"]
    elif record_id == "efsa.openfoodtox.imidacloprid.arfd.2008":
        assertion_status = "retained_in_mrl_assessment"
        regulatory_adoption_status = "retained_for_2019_mrl_consumer_risk_assessment"
        regulatory_follow_up_source_ids = ["efsa.imidacloprid.mrl_review.2019"]
    elif record_id == "efsa.openfoodtox.glyphosate.arfd":
        supersedes_record_ids = ["efsa.openfoodtox.glyphosate.arfd.2015"]
    elif assertion_class == "reference_point":
        assertion_status = "selected_reference_point"

    source_ids = list(curated.get("sourceIds", []))
    database_source_ids = [SOURCE_ID]
    primary_source_id = curated.get("primarySourceId")
    supporting_source_ids = [
        source_id
        for source_id in source_ids
        if source_id not in {*database_source_ids, *regulatory_follow_up_source_ids}
    ]
    introduced_by_source_ids = (
        ["efsa.imidacloprid.peer_review.2008"]
        if record_id == "efsa.openfoodtox.imidacloprid.arfd.2008"
        else ([primary_source_id] if primary_source_id is not None else supporting_source_ids)
    )
    return {
        "assertionClass": assertion_class,
        "assertionStatus": assertion_status,
        "regulatoryAdoptionStatus": regulatory_adoption_status,
        "temporalStatus": "current",
        "validFrom": curated.get("effectiveDate"),
        "assessmentYear": curated.get("assessmentYear"),
        "introducedBySourceIds": introduced_by_source_ids,
        "supportingSourceIds": supporting_source_ids,
        "databaseSourceIds": database_source_ids,
        "regulatoryFollowUpSourceIds": regulatory_follow_up_source_ids,
        "supersedesRecordIds": supersedes_record_ids,
    }


def _review_content_sha256(payload: dict[str, Any]) -> str:
    canonical = {key: value for key, value in payload.items() if key != "contentSha256"}
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_high_impact_review(
    source_candidates: list[dict[str, Any]],
    keys_by_uuid: dict[str, str],
    curated_records: list[dict[str, Any]],
    *,
    source: dict[str, Any] | None = None,
    workbook_schema_sha256: str | None = None,
) -> dict[str, Any]:
    by_key_type: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in source_candidates:
        key = keys_by_uuid[str(candidate["record"]["substanceUuid"])]
        by_key_type[(key, candidate["referenceType"])].append(candidate)

    reviews: list[dict[str, Any]] = []
    for curated in sorted(
        _curated_efsa_records(curated_records), key=lambda item: item["recordId"]
    ):
        key = curated["substanceKey"]
        candidates = by_key_type.get((key, curated["referenceType"]), [])
        all_years = [
            year for candidate in candidates for year in _assessment_years(candidate["record"])
        ]
        latest_assessment_year = max(all_years) if all_years else None
        comparisons = [
            _candidate_review_payload(
                candidate,
                curated,
                latest_assessment_year=latest_assessment_year,
            )
            for candidate in candidates
        ]
        support_status = _support_status(curated, candidates, comparisons)
        reviews.append(
            {
                "curatedRecordId": curated["recordId"],
                "substanceKey": key,
                "referenceType": curated["referenceType"],
                "curatedValue": curated.get("value"),
                "curatedUnit": curated.get("unit"),
                "curatedSourceIds": curated.get("sourceIds", []),
                **_curated_assertion_metadata(curated),
                "supportStatus": support_status,
                "openfoodtox3Candidates": comparisons,
            }
        )
    support_status_counts = Counter(item["supportStatus"] for item in reviews)
    temporal_status_counts = Counter(item["temporalStatus"] for item in reviews)
    source = source or {}
    review = {
        "reviewVersion": REVIEW_VERSION,
        "schemaVersion": REVIEW_SCHEMA_VERSION,
        "generatedAt": REVIEW_GENERATED_AT,
        "sourceId": SOURCE_ID,
        "sourceDoi": source.get("doi", SOURCE_DOI),
        "sourceVersion": source.get("version", SOURCE_VERSION),
        "sourcePublishedAt": source.get(
            "publicationDate",
            SOURCE_PUBLICATION_DATE,
        ),
        "sourceFile": source.get("fileName", SOURCE_FILE),
        "sourceFileSha256": source.get("sha256"),
        "workbookSchemaSha256": workbook_schema_sha256,
        "statusDefinitions": {
            "supportStatus": {
                "exact_supported_structured": "Exact value and unit are present in a structured source field.",
                "exact_supported_unstructured": "Exact value is present in a source narrative and was parsed with the strict narrative grammar.",
                "supported_after_unit_normalization": "Value is exact after a semantics-preserving unit normalization.",
                "supported_after_primary_source_unit_correction": "Value is supported after correcting a dataset unit against the authoritative scientific output while preserving the raw encoding.",
                "supported_but_source_encoding_anomalous": "Value is supported, but the source bound field is not the expected HBGV encoding.",
                "conflicting_values": "Cross-sheet candidates exist but none supports the curated assertion.",
                "not_found_after_cross_sheet_search": "No matching candidate was found across both reviewed sheets.",
                "original_output_overrides_dataset": "The original scientific output was adjudicated as authoritative over a dataset difference.",
            },
            "temporalStatus": {
                "current": "Current curated assertion.",
                "historical": "Earlier assertion retained as history.",
                "currentness_uncertain": "Currentness cannot be resolved from the dataset alone.",
            },
        },
        "recordCount": len(reviews),
        "supportStatusCounts": dict(sorted(support_status_counts.items())),
        "temporalStatusCounts": dict(sorted(temporal_status_counts.items())),
        "records": reviews,
        "releaseGate": "human_toxicologist_review_required",
        "complete": True,
    }
    review["contentSha256"] = _review_content_sha256(review)
    return review


def build_candidate_migration(
    extraction: dict[str, Any],
    existing_synonyms: dict[str, Any],
    old_bulk: dict[str, Any],
    curated_records: list[dict[str, Any]],
) -> dict[str, Any]:
    source_candidates = collect_source_candidates(extraction)
    reference_point_candidates = collect_reference_point_candidates(extraction)
    source_records = extraction.get("records", [])
    identity_source_records = list(
        {
            str(candidate["record"]["substanceUuid"]): candidate["record"]
            for candidate in [*source_candidates, *reference_point_candidates]
        }.values()
    )
    keys_by_uuid = _resolve_substance_keys(identity_source_records, existing_synonyms)
    old_records = old_bulk.get("records", [])
    old_by_key_type, old_keys = _old_record_indices(old_records)

    runtime_records: list[dict[str, Any]] = []
    provenance_records: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()
    reference_type_counts: Counter[str] = Counter()

    for candidate in source_candidates:
        record = candidate["record"]
        substance_key = keys_by_uuid[str(record["substanceUuid"])]
        reasons = _candidate_gate_reasons(candidate, substance_key)
        reason_counts.update(reasons)
        decision = {
            "recordKey": record["recordKey"],
            "substanceKey": substance_key,
            "referenceType": candidate["referenceType"],
            "section": candidate["section"],
            "bound": candidate["bound"],
            "value": candidate["value"],
            "unit": candidate.get("unit"),
            "population": candidate.get("population"),
            "decision": "held" if reasons else "emitted",
            "reasons": reasons,
        }
        if reasons:
            decisions.append(decision)
            continue
        runtime_record = _build_runtime_record(candidate, substance_key)
        classification = _migration_classification(
            runtime_record,
            old_by_key_type,
            old_keys,
        )
        decision["recordId"] = runtime_record["recordId"]
        decision["migrationClassification"] = classification
        decisions.append(decision)
        runtime_records.append(runtime_record)
        provenance_records.append(
            _build_provenance_record(candidate, runtime_record, classification)
        )
        classification_counts[classification] += 1
        reference_type_counts[runtime_record["referenceType"]] += 1

    runtime_records.sort(key=lambda item: item["recordId"])
    provenance_records.sort(key=lambda item: item["recordId"])
    decisions.sort(
        key=lambda item: (
            item["recordKey"],
            item["section"],
            item["bound"],
        )
    )
    _apply_conflict_groups(runtime_records)
    provenance_ids = {item["recordId"] for item in provenance_records}
    runtime_ids = {item["recordId"] for item in runtime_records}
    if runtime_ids != provenance_ids or len(runtime_ids) != len(runtime_records):
        raise CandidateGenerationError("runtime/provenance record identities are not one-to-one")

    source = extraction.get("source") or {}
    provenance = {
        "defaultsVersion": "v1",
        "kind": "openfoodtox_provenance",
        "sourceId": SOURCE_ID,
        "sourceVersion": source.get("version", SOURCE_VERSION),
        "sourceDoi": source.get("doi", SOURCE_DOI),
        "sourcePublicationDate": source.get("publicationDate", SOURCE_PUBLICATION_DATE),
        "sourceMd5": source.get("md5"),
        "sourceSha256": source.get("sha256"),
        "workbookSchemaSha256": extraction.get("workbookSchemaSha256"),
        "documentStatus": "dataset_current",
        "submissionUse": "review_required",
        "records": provenance_records,
    }
    summary = {
        "summaryVersion": "1.2",
        "source": source,
        "workbookSchemaSha256": extraction.get("workbookSchemaSha256"),
        "sourceCandidateCount": len(source_candidates),
        "referencePointCandidateCount": len(reference_point_candidates),
        "referencePointSourceEncodingCounts": dict(
            sorted(
                Counter(
                    str(candidate["sourceEncoding"]) for candidate in reference_point_candidates
                ).items()
            )
        ),
        "emittedRuntimeRecordCount": len(runtime_records),
        "heldCandidateCount": len(source_candidates) - len(runtime_records),
        "heldReasonCounts": dict(sorted(reason_counts.items())),
        "referenceTypeCounts": dict(sorted(reference_type_counts.items())),
        "migrationClassificationCounts": dict(sorted(classification_counts.items())),
        "excludedOperatorSectionRecordCounts": {
            "acceptableOperatorExposureLevel": sum(
                "acceptableOperatorExposureLevel" in record.get("valueSections", {})
                for record in source_records
            ),
            "acuteAcceptableOperatorExposureLevel": sum(
                "acuteAcceptableOperatorExposureLevel" in record.get("valueSections", {})
                for record in source_records
            ),
        },
        "submissionUse": "review_required",
        "status": "technical_migration_complete_human_review_required",
    }
    return {
        "defaults": {
            "defaultsVersion": "v1",
            "kind": "reference_values",
            "records": runtime_records,
        },
        "provenance": provenance,
        "synonyms": _merge_synonyms(
            existing_synonyms,
            identity_source_records,
            keys_by_uuid,
        ),
        "review": {
            "reviewVersion": REVIEW_VERSION,
            "sourceId": SOURCE_ID,
            "decisions": decisions,
        },
        "summary": summary,
        "highImpactReview": build_high_impact_review(
            [*source_candidates, *reference_point_candidates],
            keys_by_uuid,
            curated_records,
            source=source,
            workbook_schema_sha256=extraction.get("workbookSchemaSha256"),
        ),
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CandidateGenerationError(f"expected JSON object: {path}")
    return payload


def _load_curated_records(root: Path, output_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(root.glob("reference_values*.json")):
        if (
            path.resolve() == output_path.resolve()
            or path.name == "reference_values_openfoodtox.json"
        ):
            continue
        payload = _load_json(path)
        values = payload.get("records")
        if isinstance(values, list):
            records.extend(values)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extraction", type=Path)
    parser.add_argument("--old-bulk", type=Path, required=True)
    parser.add_argument("--existing-synonyms", type=Path, required=True)
    parser.add_argument("--curated-root", type=Path, required=True)
    parser.add_argument("--defaults-output", type=Path, required=True)
    parser.add_argument("--provenance-output", type=Path, required=True)
    parser.add_argument("--synonyms-output", type=Path, required=True)
    parser.add_argument("--review-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--high-impact-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = build_candidate_migration(
        _load_json(args.extraction),
        _load_json(args.existing_synonyms),
        _load_json(args.old_bulk),
        _load_curated_records(args.curated_root, args.defaults_output),
    )
    _write_json(args.defaults_output, result["defaults"])
    _write_json(args.provenance_output, result["provenance"])
    _write_json(args.synonyms_output, result["synonyms"])
    _write_json(args.review_output, result["review"])
    _write_json(args.summary_output, result["summary"])
    _write_json(args.high_impact_output, result["highImpactReview"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
