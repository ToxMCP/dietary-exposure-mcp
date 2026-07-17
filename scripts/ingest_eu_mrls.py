#!/usr/bin/env python3
"""
Ingest EU MRL data from the EU Pesticides DataLake API v3.0.

Streams the NDJSON endpoint and produces:
    defaults/v1/mrl_enforcement_eu.json
    defaults/extensions/v1/commodity_taxonomy/eu_mrl.json

Run from repo root:
    uv run python scripts/ingest_eu_mrls.py
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_MRL = REPO_ROOT / "defaults" / "v1" / "mrl_enforcement_eu.json"
COMMODITY_EXT_DIR = REPO_ROOT / "defaults" / "extensions" / "v1" / "commodity_taxonomy"
COMMODITY_EXT_FILE = COMMODITY_EXT_DIR / "eu_mrl.json"

SYNONYMS_PATH = REPO_ROOT / "defaults" / "v1" / "substance_synonyms.json"
SOURCE_CATALOG_PATH = REPO_ROOT / "defaults" / "v1" / "source_catalog.json"

API_URL = (
    "https://api.datalake.sante.service.ec.europa.eu/sante/pesticides/"
    "pesticide-residues-mrls-download?language_code=EN&format=json&api-version=v3.0"
)


def load_synonym_lookup() -> dict[str, str]:
    with SYNONYMS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    lookup: dict[str, str] = {}
    for entry in data.get("entries", []):
        key = entry["canonicalKey"]
        names = [key] + entry.get("synonyms", [])
        for name in names:
            norm = re.sub(r"[^a-z0-9]", "", name.lower())
            lookup[norm] = key
    return lookup


def parse_mrl_value(mrl_text: str) -> tuple[float | None, bool]:
    text = mrl_text.strip()
    if text.lower() in {"no mrl required", "-", "", "n/a"}:
        return None, False
    is_star = text.endswith("*")
    num_str = text.rstrip("*").strip()
    try:
        val = float(num_str)
    except ValueError:
        return None, False
    return val, is_star


def infer_food_group(code: str) -> str:
    prefix = code[:2]
    mapping = {
        "01": "fruits_and_tree_nuts",
        "02": "vegetables",
        "03": "pulses_and_oilseeds",
        "04": "cereals",
        "05": "tea_coffee_cocoa_spices",
        "06": "animal_products",
        "07": "animal_products",
        "08": "miscellaneous",
        "09": "sugar_plants",
        "10": "beverages",
        "11": "feed",
        "12": "feed",
        "13": "mushrooms",
        "14": "miscellaneous",
        "15": "miscellaneous",
    }
    return mapping.get(prefix, "miscellaneous")


def main() -> None:
    synonym_lookup = load_synonym_lookup()

    # Verify source catalog has eu.reg.396_2005
    with SOURCE_CATALOG_PATH.open(encoding="utf-8") as f:
        source_catalog = json.load(f)
    known_source_ids = {s["sourceId"] for s in source_catalog.get("sources", [])}
    if "eu.reg.396_2005" not in known_source_ids:
        raise RuntimeError("eu.reg.396_2005 not found in source catalog")

    COMMODITY_EXT_DIR.mkdir(parents=True, exist_ok=True)

    matched_substances: dict[str, str] = {}  # EU name -> canonicalKey
    commodity_entries: list[dict] = []
    seen_commodity_codes: set[str] = set()

    mrl_records: list[dict] = []
    seen_mrl_ids: set[str] = set()

    print("Streaming EU MRL data from DataLake API ...")

    with urllib.request.urlopen(API_URL) as response:
        for line in response:
            if not line.strip():
                continue
            record = json.loads(line)

            eu_name = record.get("pesticide_residue_name", "").strip()
            pest_id = record.get("pesticide_residue_id")
            pcode = record.get("product_code")

            if pest_id is None or pcode is None:
                continue

            pcode = str(pcode).strip()
            pname = record.get("product_name", "") or ""
            mrl_text = (record.get("mrl_value") or "").strip()

            # Skip group-level commodity codes (heuristic: ends with 000)
            if pcode.endswith("000"):
                continue

            # Match substance using the leading token before any parenthesis
            cleaned = eu_name.split("(")[0].strip()
            cleaned = re.sub(r"\s+", " ", cleaned)
            norm = re.sub(r"[^a-z0-9]", "", cleaned.lower())
            canonical_key = synonym_lookup.get(norm)
            if canonical_key is None:
                # Fallback: check if any individual word/token matches a synonym
                tokens = re.split(r"[^a-z0-9]+", cleaned.lower())
                for token in tokens:
                    token_norm = re.sub(r"[^a-z0-9]", "", token)
                    if token_norm in synonym_lookup:
                        canonical_key = synonym_lookup[token_norm]
                        break
                if canonical_key is None:
                    continue

            matched_substances[eu_name] = canonical_key

            val, is_star = parse_mrl_value(mrl_text)
            if val is None:
                continue

            # Build commodity taxonomy entry
            if pcode not in seen_commodity_codes:
                seen_commodity_codes.add(pcode)
                commodity_entries.append({
                    "commodityCode": pcode,
                    "canonicalName": pname,
                    "foodGroup": infer_food_group(pcode),
                    "mappingStatus": "auto_ingested_eu_mrl",
                    "sourceId": f"eu.mrl.taxonomy.{pcode}",
                })

            record_id = f"eu.efsa.{canonical_key}.{pcode}.mrl"
            if record_id in seen_mrl_ids:
                continue
            seen_mrl_ids.add(record_id)

            notes = [
                "Auto-ingested from EU Pesticides Database (DataLake API v3.0).",
                f"EU Pesticides Database PestResID={pest_id}, ProductCode={pcode}.",
            ]
            if is_star:
                notes.append("MRL value marked with * (default/limit of quantification).")

            mrl_records.append({
                "recordId": record_id,
                "substanceKey": canonical_key,
                "commodityCode": pcode,
                "authority": "EFSA",
                "jurisdiction": "eu",
                "mrlValueMgPerKg": val,
                "sourceIds": ["eu.reg.396_2005"],
                "notes": notes,
            })

    print(f"Matched substances: {len(matched_substances)}")
    print(f"Commodity entries: {len(commodity_entries)}")
    print(f"MRL records: {len(mrl_records)}")

    # Write commodity taxonomy extension
    COMMODITY_EXT_FILE.write_text(
        json.dumps({
            "defaultsVersion": "v1",
            "kind": "commodity_taxonomy",
            "commodities": commodity_entries,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote commodity taxonomy extension to {COMMODITY_EXT_FILE}")

    # Write MRL enforcement pack
    OUTPUT_MRL.write_text(
        json.dumps({
            "defaultsVersion": "v1",
            "kind": "mrl_enforcement",
            "records": mrl_records,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote MRL enforcement pack to {OUTPUT_MRL}")


if __name__ == "__main__":
    main()
