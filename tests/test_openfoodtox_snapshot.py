from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.models import LookupReferenceValuesRequest
from dietary_mcp.runtime import DietaryRuntime


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return json.loads((REPO_ROOT / "defaults" / "v1" / name).read_text(encoding="utf-8"))


def test_openfoodtox_bulk_records_are_pinned_to_superseded_snapshot() -> None:
    sources = {item["sourceId"]: item for item in _load("source_catalog.json")["sources"]}
    records = _load("reference_values_openfoodtox.json")["records"]

    assert sources["efsa.openfoodtox"]["effectiveDate"] == "2026-04-30"
    assert sources["efsa.openfoodtox"]["documentStatus"] == "dataset_current"
    assert sources["efsa.openfoodtox.2023_snapshot"]["documentStatus"] == "superseded"
    assert sources["efsa.openfoodtox.2023_snapshot"]["supersededBy"] == ["efsa.openfoodtox"]
    assert all(item["sourceIds"] == ["efsa.openfoodtox.2023_snapshot"] for item in records)
    assert all(item["documentStatus"] == "superseded" for item in records)


def test_openfoodtox_runtime_records_preserve_structured_source_context() -> None:
    records = _load("reference_values_openfoodtox.json")["records"]
    provenance = {
        item["recordId"]: item["openfoodtox"]
        for item in _load("openfoodtox_reference_value_provenance.json")["records"]
    }

    assert len(records) == len(provenance) == 2274
    for record in records:
        source = provenance[record["recordId"]]
        assert record["assessmentLabel"] == source["Assessment"]
        assert record["assessmentYear"] == source["Year"]
        assert record["population"] == source["Population"]
        assert record["qualifier"] == source["qualfier"]
        assert record["sourceOutputId"] == source["OutputID"]
        assert record["value"] == source["value"]
        assert record["unit"] == source["unit"]


def test_reference_lookup_can_filter_snapshot_context_and_warns_on_currency() -> None:
    runtime = DietaryRuntime(REPO_ROOT)

    result = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substanceKey="zinc",
            jurisdiction="eu",
            referenceType="pri",
            population="infants 7-11 months",
            assessmentYear=2014,
            sourceId="efsa.openfoodtox.2023_snapshot",
        )
    )

    assert len(result.matched_records) == 1
    assert result.matched_records[0].population == "Consumers - Infants 7-11 months"
    assert result.matched_records[0].value == 2.9
    assert {item.code for item in result.quality_flags} == {"superseded_source_snapshot"}


def test_reference_lookup_surfaces_unit_basis_variation() -> None:
    runtime = DietaryRuntime(REPO_ROOT)

    result = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(substanceKey="coumarin", jurisdiction="eu")
    )

    assert {item.unit for item in result.matched_records} == {"mg/kg bw", "mg/kg bw/day"}
    assert {item.qualifier for item in result.matched_records} == {"<"}
    assert {item.code for item in result.quality_flags} == {
        "reference_value_context_selection_required",
        "reference_value_unit_basis_review_required",
        "superseded_source_snapshot",
    }


def test_acetamiprid_uses_lower_efsa_reference_values_and_preserves_conflict() -> None:
    runtime = DietaryRuntime(REPO_ROOT)

    result = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(substanceKey="acetamiprid", jurisdiction="eu")
    )

    records = {item.reference_type: item for item in result.matched_records}
    assert records["adi"].value == 0.005
    assert records["adi"].unit == "mg/kg bw/day"
    assert records["arfd"].value == 0.005
    assert records["arfd"].unit == "mg/kg bw/day"
    assert records["adi"].primary_source_id == "efsa.acetamiprid.statement.2024"
    assert "eu.reg.2025_158" in records["adi"].source_ids
