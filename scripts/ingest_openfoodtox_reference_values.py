#!/usr/bin/env python3
"""
Ingest EFSA OpenFoodTox 2.0 human reference values into Dietary MCP defaults.

This script reads:
    tmp/regulatory_sources/ReferenceValues_KJ_2023.xlsx
    tmp/regulatory_sources/SubstanceCharacterisation_KJ_2023.xlsx

And produces:
    defaults/v1/reference_values_openfoodtox.json
    defaults/v1/substance_synonyms.json (merged with existing)

Run from the repo root:
    uv run python scripts/ingest_openfoodtox_reference_values.py
"""

from __future__ import annotations

import json
import hashlib
import re
import unicodedata
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
OPENFOODTOX_REF = REPO_ROOT / "tmp" / "regulatory_sources" / "ReferenceValues_KJ_2023.xlsx"
OPENFOODTOX_SUB = REPO_ROOT / "tmp" / "regulatory_sources" / "SubstanceCharacterisation_KJ_2023.xlsx"
OUTPUT_REF = REPO_ROOT / "defaults" / "v1" / "reference_values_openfoodtox.json"
PROVENANCE_REF = REPO_ROOT / "defaults" / "v1" / "openfoodtox_reference_value_provenance.json"
SYNONYMS_PATH = REPO_ROOT / "defaults" / "v1" / "substance_synonyms.json"
OPENFOODTOX_SOURCE_ID = "efsa.openfoodtox.2023_snapshot"
OPENFOODTOX_SOURCE_VERSION = "6"
OPENFOODTOX_SOURCE_DOI = "10.5281/zenodo.8120114"
OPENFOODTOX_SOURCE_URL = "https://zenodo.org/records/8120114"
OPENFOODTOX_SOURCE_MD5 = "c3574a602191e9ef3c63f09c8263c7a7"
OPENFOODTOX_SOURCE_COVERAGE_THROUGH = "2022-09"

# Human dietary relevant assessment types from OpenFoodTox
HUMAN_ASSESSMENTS = {
    "ADI",
    "ADI (group)",
    "ADI (provisional)",
    "ARfD",
    "ARfD (group)",
    "TDI",
    "TDI (group)",
    "TDI (provisional)",
    "TWI",
    "TWI (provisional)",
    "UL",
    "UL (provisional)",
    "MTDI",
    "MTDI (provisional)",
    "AI",
    "PRI",
    "Safe maximum intake level",
}

# Mapping of OpenFoodTox assessment names to MCP referenceType values
ASSESSMENT_TO_REF_TYPE = {
    "ADI": "adi",
    "ADI (group)": "adi",
    "ADI (provisional)": "adi",
    "ARfD": "arfd",
    "ARfD (group)": "arfd",
    "TDI": "tdi",
    "TDI (group)": "tdi",
    "TDI (provisional)": "tdi",
    "TWI": "twi",
    "TWI (provisional)": "twi",
    "UL": "ul",
    "UL (provisional)": "ul",
    "MTDI": "mtdi",
    "MTDI (provisional)": "mtdi",
    "AI": "ai",
    "PRI": "pri",
    "Safe maximum intake level": "safe_maximum_intake_level",
}

# Authority normalization: EFSA panels -> EFSA
AUTHORITY_MAP = {
    "EFSA": "EFSA",
    "EFSA CONTAM": "EFSA",
    "EFSA ANS": "EFSA",
    "EFSA CEF": "EFSA",
    "EFSA FAF": "EFSA",
    "EFSA FEEDAP": "EFSA",
    "EFSA AFC": "EFSA",
    "EFSA PPR": "EFSA",
    "EFSA NDA": "EFSA",
    "SCF": "SCF",
    "EFSA CEF, EFSA CONTAM": "EFSA",
}

# Jurisdiction mapping
JURISDICTION_MAP = {
    "EFSA": "eu",
    "SCF": "eu",
    "JMPR": "codex_global",
}

# Substances with hardcoded test assertions that should be excluded from bulk ingestion
# and instead maintained in the curated base files.
TESTED_SUBSTANCE_KEYS: set[str] = {
    "glyphosate",
    "acetamiprid",
    "imidacloprid",
    "glufosinate",
    "oxamyl",
    "difenoconazole",
    "ethiprole",
    "tetraconazole",
    "tebuconazole",
    "cadmium",
    "lead",
    "inorganic_arsenic",
    "methylmercury",
    "inorganic_mercury",
}

# Manual overrides for substance keys to match existing MCP taxonomy
SUBSTANCE_KEY_OVERRIDES: dict[str, str] = {
    # Metals / contaminants
    "Cadmium (total)": "cadmium",
    "Lead (total)": "lead",
    "Arsenic, inorganic derivates": "inorganic_arsenic",
    "Methylmercury": "methylmercury",
    "Inorganic mercury": "inorganic_mercury",
    "Mercury (total)": "mercury_total",
    # Pesticides with different naming conventions
    "Glufosinate-ammonium": "glufosinate",
}

# Contaminant family heuristics based on substance key patterns
CONTAMINANT_FAMILY_OVERRIDES: dict[str, str] = {
    "cadmium": "cadmium_food_contaminants",
    "lead": "lead_food_contaminants",
    "inorganic_arsenic": "inorganic_arsenic_food_contaminants",
    "methylmercury": "mercury_food_contaminants",
    "inorganic_mercury": "mercury_food_contaminants",
    "mercury_total": "mercury_food_contaminants",
}


def decode_x_entities(text: str | float | None) -> str | None:
    """Decode Excel XML entity encoding (_xNNNN_ -> char)."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    text = str(text)

    def replace(m: re.Match[str]) -> str:
        try:
            return chr(int(m.group(1), 16))
        except ValueError:
            return m.group(0)

    text = re.sub(r"_x([0-9a-fA-F]{4})_", replace, text)
    return text


def to_snake_case_key(name: str) -> str:
    """Convert a substance display name to a lowercase snake_case key."""
    # Normalize unicode
    name = unicodedata.normalize("NFKD", name)
    # Replace common separators with spaces
    name = re.sub(r"[\-_\/]", " ", name)
    # Remove parentheses content for the key, but keep the word before it
    name = re.sub(r"\([^)]*\)", "", name)
    # Remove commas
    name = name.replace(",", "")
    # Lowercase
    name = name.lower().strip()
    # Replace spaces with underscores
    name = re.sub(r"\s+", "_", name)
    # Remove any remaining non-alphanumeric except underscore
    name = re.sub(r"[^a-z0-9_]", "", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def build_substance_key(openfoodtox_name: str) -> str:
    if openfoodtox_name in SUBSTANCE_KEY_OVERRIDES:
        return SUBSTANCE_KEY_OVERRIDES[openfoodtox_name]
    return to_snake_case_key(openfoodtox_name)


def infer_contaminant_family(substance_key: str, authority: str, assessment: str) -> str:
    if substance_key in CONTAMINANT_FAMILY_OVERRIDES:
        return CONTAMINANT_FAMILY_OVERRIDES[substance_key]
    # Heuristic based on assessment type: ADI/ARfD are typically pesticides
    if assessment in {"ADI", "ARfD", "ADI (group)", "ARfD (group)", "ADI (provisional)", "AOEL", "AOEL (provisional)"}:
        return "pesticide_residue"
    return "food_contaminant"


def sanitize_record_id(text: str) -> str:
    """Create a safe record id suffix from arbitrary text."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def load_openfoodtox() -> pd.DataFrame:
    if not OPENFOODTOX_REF.exists():
        raise SystemExit(
            f"Missing {OPENFOODTOX_REF}. Download ReferenceValues_KJ_2023.xlsx "
            f"from {OPENFOODTOX_SOURCE_URL}."
        )
    source_md5 = hashlib.md5(OPENFOODTOX_REF.read_bytes(), usedforsecurity=False).hexdigest()  # noqa: S324
    if source_md5 != OPENFOODTOX_SOURCE_MD5:
        raise SystemExit(
            f"OpenFoodTox source checksum mismatch: expected {OPENFOODTOX_SOURCE_MD5}, got {source_md5}."
        )
    df = pd.read_excel(OPENFOODTOX_REF, sheet_name="REFERENCEVALUES")
    for col in ["Substance", "Author", "Assessment", "qualfier", "value", "unit", "Population"]:
        df[col] = df[col].apply(decode_x_entities)
    return df


def main() -> None:  # noqa: C901, PLR0912, PLR0915
    df = load_openfoodtox()

    # Filter: consumer-related populations + relevant assessments
    consumer_mask = df["Population"].str.contains("Consumer", case=False, na=False)
    assessment_mask = df["Assessment"].isin(HUMAN_ASSESSMENTS)
    df = df[consumer_mask & assessment_mask].copy()

    # Drop rows with missing values
    df = df.dropna(subset=["value", "unit", "Substance", "Assessment"])

    # Exclude substances that have hardcoded test assertions in curated base files
    df["_substance_key"] = df["Substance"].apply(build_substance_key)
    df = df[~df["_substance_key"].isin(TESTED_SUBSTANCE_KEYS)].copy()
    df = df.drop(columns=["_substance_key"])

    print(f"OpenFoodTox human consumer reference values after exclusions: {len(df)} rows")

    # Build substance synonym map from substance characterisation if available
    substance_names: set[str] = set(df["Substance"].dropna().unique())

    # Load existing synonyms
    existing_synonyms: list[dict] = []
    if SYNONYMS_PATH.exists():
        existing_synonyms = json.loads(SYNONYMS_PATH.read_text(encoding="utf-8")).get("entries", [])

    existing_keys = {entry["canonicalKey"] for entry in existing_synonyms}

    # Generate new synonyms for all substances
    new_entries = []
    seen_keys = set(existing_keys)
    for name in sorted(substance_names):
        key = build_substance_key(name)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        entry = {
            "canonicalKey": key,
            "synonyms": [name],
            "sourceId": f"dietary.substance_synonyms.{key}",
        }
        new_entries.append(entry)

    # Merge synonyms: existing first, then new
    merged_entries = existing_synonyms + new_entries

    # Write synonyms
    SYNONYMS_PATH.write_text(
        json.dumps({
            "defaultsVersion": "v1",
            "kind": "substance_synonyms",
            "entries": merged_entries,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(merged_entries)} substance synonyms to {SYNONYMS_PATH}")

    # Build reference value records
    records: list[dict] = []
    seen_record_ids: set[str] = set()

    # Group by substance + assessment + authority + population to detect conflicts
    for _, row in df.iterrows():
        substance_name = str(row["Substance"]).strip()
        substance_key = build_substance_key(substance_name)
        assessment = str(row["Assessment"]).strip()
        ref_type = ASSESSMENT_TO_REF_TYPE[assessment]
        author_raw = str(row["Author"]).strip()
        authority = AUTHORITY_MAP.get(author_raw, author_raw)
        jurisdiction = JURISDICTION_MAP.get(authority, "eu")
        contaminant_family = infer_contaminant_family(substance_key, authority, assessment)
        value = float(row["value"])
        unit = str(row["unit"]).strip()
        population = str(row["Population"]).strip()
        year = int(row["Year"]) if pd.notna(row["Year"]) else None
        output_id = int(row["OutputID"]) if pd.notna(row["OutputID"]) else None

        # Build record id
        parts = ["efsa", "openfoodtox", substance_key, ref_type]
        if output_id is not None:
            parts.append(str(output_id))
        else:
            parts.append(str(len(records)))

        record_id = ".".join(parts)

        # Handle duplicates by appending an index
        base_record_id = record_id
        idx = 1
        while record_id in seen_record_ids:
            record_id = f"{base_record_id}_{idx}"
            idx += 1
        seen_record_ids.add(record_id)

        # Notes
        notes = [
            "Auto-ingested from EFSA OpenFoodTox 2.0 (ReferenceValues_KJ_2023).",
            f"OpenFoodTox OutputID={output_id}, Author={author_raw}, Assessment={assessment}, Population={population}.",
        ]
        if year:
            notes.append(f"Original assessment year: {year}.")
        if str(row.get("qualfier")).strip() not in ("", "None", "NaN", "=", "_x003D_"):
            notes.append(f"Qualifier: {row['qualfier']}.")

        record = {
            "recordId": record_id,
            "substanceKey": substance_key,
            "substanceName": substance_name,
            "referenceType": ref_type,
            "authority": authority,
            "jurisdiction": jurisdiction,
            "contaminantFamily": contaminant_family,
            "value": value,
            "unit": unit,
            "qualifier": str(row.get("qualfier")).strip(),
            "assessmentLabel": assessment,
            "assessmentYear": year,
            "population": population,
            "sourceOutputId": output_id,
            "sourceIds": [OPENFOODTOX_SOURCE_ID],
            "databaseSourceId": OPENFOODTOX_SOURCE_ID,
            "documentStatus": "superseded",
            "submissionUse": "review_required",
            "effectiveDate": None,
            "notes": notes,
            "_provenance": {
                "Substance": substance_name,
                "Author": author_raw,
                "Year": year,
                "OutputID": output_id,
                "Assessment": assessment,
                "qualfier": str(row.get("qualfier")) if pd.notna(row.get("qualfier")) else None,
                "value": value,
                "unit": unit,
                "Population": population,
            },
        }
        records.append(record)

    # Surface dataset variations without pretending they are all authority conflicts.
    conflict_groups: dict[tuple[str, str, str], list[dict]] = {}
    for rec in records:
        key = (rec["substanceKey"], rec["referenceType"], rec["jurisdiction"])
        conflict_groups.setdefault(key, []).append(rec)

    for (substance_key, ref_type, jurisdiction), group in conflict_groups.items():
        contexts = {
            (
                r["value"],
                r["unit"],
                r["qualifier"],
                r["population"],
                r["assessmentLabel"],
                r["assessmentYear"],
            )
            for r in group
        }
        if len(contexts) > 1:
            conflict_id = f"{substance_key}.{ref_type}.openfoodtox_2023_variation"
            for rec in group:
                rec["conflictGroupId"] = conflict_id

    # Write provenance sidecar for maximum auditability
    existing_ingestion_date = None
    if PROVENANCE_REF.exists():
        existing_ingestion_date = json.loads(PROVENANCE_REF.read_text(encoding="utf-8")).get("ingestionDate")
    provenance = {
        "defaultsVersion": "v1",
        "kind": "openfoodtox_provenance",
        "sourceId": OPENFOODTOX_SOURCE_ID,
        "sourceVersion": OPENFOODTOX_SOURCE_VERSION,
        "sourceDoi": OPENFOODTOX_SOURCE_DOI,
        "sourceUrl": OPENFOODTOX_SOURCE_URL,
        "sourceMd5": OPENFOODTOX_SOURCE_MD5,
        "sourceCoverageThrough": OPENFOODTOX_SOURCE_COVERAGE_THROUGH,
        "documentStatus": "superseded",
        "supersededBy": "efsa.openfoodtox",
        "sourceFile": "ReferenceValues_KJ_2023.xlsx",
        "sourceSheet": "REFERENCEVALUES",
        "ingestionDate": existing_ingestion_date or pd.Timestamp.now(tz="UTC").isoformat(),
        "records": [
            {
                "recordId": rec["recordId"],
                "openfoodtox": {
                    "Substance": rec["_provenance"]["Substance"],
                    "Author": rec["_provenance"]["Author"],
                    "Year": rec["_provenance"]["Year"],
                    "OutputID": rec["_provenance"]["OutputID"],
                    "Assessment": rec["_provenance"]["Assessment"],
                    "qualfier": rec["_provenance"]["qualfier"],
                    "value": rec["_provenance"]["value"],
                    "unit": rec["_provenance"]["unit"],
                    "Population": rec["_provenance"]["Population"],
                },
            }
            for rec in records
        ],
    }
    # Strip internal provenance key from runtime records
    for rec in records:
        rec.pop("_provenance", None)

    PROVENANCE_REF.write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(provenance['records'])} provenance entries to {PROVENANCE_REF}")

    OUTPUT_REF.write_text(
        json.dumps({
            "defaultsVersion": "v1",
            "kind": "reference_values",
            "records": records,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} reference value records to {OUTPUT_REF}")


if __name__ == "__main__":
    main()
