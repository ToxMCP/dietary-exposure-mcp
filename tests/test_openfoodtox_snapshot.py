from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.models import LookupReferenceValuesRequest
from dietary_mcp.runtime import DietaryRuntime
from scripts.openfoodtox3_candidates import _repair_source_text


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return json.loads((REPO_ROOT / "defaults" / "v1" / name).read_text(encoding="utf-8"))


def test_openfoodtox_bulk_records_are_pinned_to_current_v3_dataset() -> None:
    sources = {item["sourceId"]: item for item in _load("source_catalog.json")["sources"]}
    records = _load("reference_values_openfoodtox.json")["records"]

    assert sources["efsa.openfoodtox"]["effectiveDate"] == "2026-04-30"
    assert sources["efsa.openfoodtox"]["documentStatus"] == "dataset_current"
    assert sources["efsa.openfoodtox.2023_snapshot"]["documentStatus"] == "superseded"
    assert sources["efsa.openfoodtox.2023_snapshot"]["supersededBy"] == ["efsa.openfoodtox"]
    assert len(records) == 2417
    assert all(item["sourceIds"] == ["efsa.openfoodtox"] for item in records)
    assert all(item["documentStatus"] == "dataset_current" for item in records)
    assert all(item["submissionUse"] == "review_required" for item in records)
    assert all(item["sourceOutputId"] is None for item in records)


def test_openfoodtox_runtime_records_preserve_structured_source_context() -> None:
    records = _load("reference_values_openfoodtox.json")["records"]
    provenance = {
        item["recordId"]: item["openfoodtox3"]
        for item in _load("openfoodtox_reference_value_provenance.json")["records"]
    }

    assert len(records) == len(provenance) == 2417
    unit_display_repairs = 0
    population_display_repairs = 0
    for record in records:
        source = provenance[record["recordId"]]
        assert record["assessmentLabel"] == source["descriptor"]
        assert record["value"] == source["value"]
        assert record["unit"] == source["unit"]
        assert source["recordKey"] in record["notes"][1]
        assert source["bound"] in {"lower", "upper"}
        assert source["sourceFile"] == "OFT3.0 export repository.xlsx"
        assert source["sourceSheet"] == "FLEX_SUM.ToxRefValues"
        assert source["sourceFieldPath"]
        assert source["rawValue"] == source["value"]
        assert _repair_source_text(source["rawUnit"]) == source["unit"]
        if source["rawUnit"] != source["unit"]:
            unit_display_repairs += 1
        if raw_remarks := source.get("rawPopulationRemarks"):
            assert _repair_source_text(raw_remarks) == source["populationRemarks"]
            population_display_repairs += 1
        assert source["dossiers"]
    assert unit_display_repairs == 10
    assert population_display_repairs == 40


def test_openfoodtox_candidate_gate_counts_and_curated_precedence_are_pinned() -> None:
    summary = json.loads(
        (REPO_ROOT / "docs" / "reviews" / "openfoodtox-3-candidate-summary.json").read_text(
            encoding="utf-8"
        )
    )
    records = _load("reference_values_openfoodtox.json")["records"]

    assert summary["sourceCandidateCount"] == 2734
    assert summary["referencePointCandidateCount"] == 171
    assert summary["referencePointSourceEncodingCounts"] == {
        "structured": 133,
        "unstructured": 38,
    }
    assert summary["emittedRuntimeRecordCount"] == len(records) == 2417
    assert summary["heldCandidateCount"] == 317
    assert summary["heldReasonCounts"]["unresolved_assessment_authority"] == 272
    assert summary["heldReasonCounts"]["curated_record_precedence"] == 49
    assert summary["excludedOperatorSectionRecordCounts"] == {
        "acceptableOperatorExposureLevel": 622,
        "acuteAcceptableOperatorExposureLevel": 194,
    }
    curated_keys = {
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
    assert not curated_keys & {record["substanceKey"] for record in records}


def test_openfoodtox_high_impact_differences_remain_a_human_release_gate() -> None:
    review = json.loads(
        (REPO_ROOT / "docs" / "reviews" / "openfoodtox-3-high-impact-review.json").read_text(
            encoding="utf-8"
        )
    )
    by_id = {item["curatedRecordId"]: item for item in review["records"]}

    assert review["releaseGate"] == "human_toxicologist_review_required"
    assert review["recordCount"] == len(review["records"]) == 16
    assert review["complete"] is True
    assert len(review["contentSha256"]) == 64
    assert by_id["efsa.openfoodtox.glyphosate.arfd"]["supportStatus"] == (
        "supported_after_primary_source_unit_correction"
    )
    assert by_id["efsa.openfoodtox.acetamiprid.adi"]["supportStatus"] == (
        "exact_supported_structured"
    )
    assert by_id["efsa.openfoodtox.imidacloprid.arfd"]["supportStatus"] == (
        "supported_after_primary_source_unit_correction"
    )
    assert (
        by_id["efsa.lead.developmental_neurotoxicity.bmdl01"]["supportStatus"]
        == "exact_supported_unstructured"
    )


def test_reference_lookup_can_filter_current_context_and_requires_source_review() -> None:
    runtime = DietaryRuntime(REPO_ROOT)

    result = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substanceKey="zinc",
            jurisdiction="eu",
            referenceType="pri",
            population="infants 7-11 months",
            assessmentYear=2014,
            sourceId="efsa.openfoodtox",
        )
    )

    assert len(result.matched_records) == 1
    assert result.matched_records[0].population == "infants - Consumers - Infants 7-11 months"
    assert result.matched_records[0].value == 2.9
    assert {item.code for item in result.quality_flags} == {
        "openfoodtox_original_output_review_required"
    }
    assert result.matched_records[0].submission_use.value == "review_required"


def test_reference_lookup_surfaces_unit_basis_variation() -> None:
    runtime = DietaryRuntime(REPO_ROOT)

    result = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(substanceKey="coumarin", jurisdiction="eu")
    )

    assert {item.unit for item in result.matched_records} == {"mg/kg bw", "mg/kg bw/day"}
    assert {item.qualifier for item in result.matched_records} == {"<"}
    assert {item.code for item in result.quality_flags} == {
        "openfoodtox_original_output_review_required",
        "reference_value_context_selection_required",
        "reference_value_unit_basis_review_required",
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
    assert records["arfd"].unit == "mg/kg bw"
    assert records["adi"].primary_source_id == "efsa.acetamiprid.statement.2024"
    assert "eu.reg.2025_158" not in records["adi"].source_ids


def test_glyphosate_history_and_imidacloprid_parallel_arfd_contexts() -> None:
    runtime = DietaryRuntime(REPO_ROOT)

    glyphosate = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substanceKey="glyphosate",
            jurisdiction="eu",
            referenceType="arfd",
        )
    ).matched_records
    assert {(item.value, item.unit, item.document_status.value) for item in glyphosate} == {
        (1.5, "mg/kg bw", "dataset_current"),
        (0.5, "mg/kg bw", "superseded"),
    }

    imidacloprid = runtime.lookup_reference_values(
        LookupReferenceValuesRequest(
            substanceKey="imidacloprid",
            jurisdiction="eu",
            referenceType="arfd",
        )
    ).matched_records
    assert {(item.value, item.unit, item.document_status.value) for item in imidacloprid} == {
        (0.06, "mg/kg bw", "dataset_current"),
        (0.08, "mg/kg bw", "final_current"),
    }
    assert {item.conflict_group_id for item in imidacloprid} == {"imidacloprid.arfd.efsa_context"}
