from __future__ import annotations

from copy import deepcopy

from dietary_mcp.models import ReferenceValueRecord
from scripts.openfoodtox3_candidates import (
    build_candidate_migration,
    collect_reference_point_candidates,
    collect_source_candidates,
)


def _dossier(
    uuid: str,
    *,
    year: int = 2020,
    group: str = "EFSA PPR",
    domain: str = "pesticides",
) -> dict:
    return {
        "link": {"dossierUuid": uuid},
        "record": {
            "Domain.ExpertGroup": group,
            "Domain.FoodDomain": domain,
            "LiteratureReference.DateOfEvaluation": f"{year}-04-02",
            "LiteratureReference.EFSAOutputTitle": f"Output {uuid}",
            "LiteratureReference.LinkToPersistentIdentifier": f"DOI: 10.1000/{uuid}",
        },
    }


def _record(
    suffix: str,
    name: str,
    sections: dict,
    *,
    dossiers: list[dict] | None = None,
    review_flags: list[str] | None = None,
) -> dict:
    return {
        "recordKey": f"tox-{suffix}#row-{suffix}",
        "sourceRowNumber": int(suffix),
        "toxReferenceDocumentUuid": f"tox-{suffix}",
        "substanceUuid": f"sub-{suffix}",
        "referenceSubstanceUuid": f"ref-{suffix}",
        "substance": {"ChemicalName": name},
        "referenceSubstance": {
            "ReferenceSubstanceName": name,
            "Inventory.CASNumber": f"1-{suffix}-0",
        },
        "dossiers": dossiers if dossiers is not None else [_dossier(f"d-{suffix}")],
        "referencedLiterature": None,
        "reviewFlags": review_flags or [],
        "valueSections": sections,
    }


def _extraction(records: list[dict]) -> dict:
    return {
        "source": {
            "version": "v7",
            "doi": "10.5281/zenodo.19388272",
            "publicationDate": "2026-04-30",
            "md5": "source-md5",
            "sha256": "source-sha256",
        },
        "workbookSchemaSha256": "schema-sha256",
        "records": records,
    }


def _synonyms() -> dict:
    return {"defaultsVersion": "v1", "kind": "substance_synonyms", "entries": []}


def _old_bulk() -> dict:
    return {"defaultsVersion": "v1", "kind": "reference_values", "records": []}


def test_collect_source_candidates_excludes_operator_and_nondietary_descriptors() -> None:
    record = _record(
        "1",
        "Example",
        {
            "acceptableDailyIntake": {
                "Adi.lowerValue": 0.1,
                "Adi.Unit": "mg/kg bw/day",
                "Population": "consumers",
            },
            "acceptableOperatorExposureLevel": {
                "Aoel.Value": 0.2,
                "Aoel.Unit": "mg/kg bw/day",
                "Population": "workers",
            },
            "otherReferenceValues": {
                "ReferenceValueDescriptor": "other:",
                "ReferenceValueDescriptor.Other": "MOE",
                "RefValue.lowerValue": 100,
                "RefValue.Unit": "other:",
                "RefValue.Unit.Other": "dimensionless",
                "Population": "consumers",
            },
        },
    )

    candidates = collect_source_candidates(_extraction([record]))

    assert [(item["referenceType"], item["value"]) for item in candidates] == [("adi", 0.1)]


def test_candidate_migration_preserves_bounds_and_multi_dossier_context() -> None:
    record = _record(
        "2",
        "Example substance",
        {
            "otherReferenceValues": {
                "ReferenceValueDescriptor": "UL",
                "RefValue.lowerValue": 2,
                "RefValue.upperQualifier": "<=",
                "RefValue.upperValue": 4,
                "RefValue.Unit": "mg/day",
                "Population": "children",
                "Population.Remarks": "4-6 years",
                "CriticalEndpoint": "endpoint-uuid",
                "OverallUncertainty": "100",
            }
        },
        dossiers=[_dossier("old", year=2020), _dossier("new", year=2021)],
    )

    result = build_candidate_migration(_extraction([record]), _synonyms(), _old_bulk(), [])
    records = result["defaults"]["records"]

    assert len(records) == 2
    assert len({item["recordId"] for item in records}) == 2
    assert {item["value"] for item in records} == {2.0, 4.0}
    assert {item["population"] for item in records} == {"children - 4-6 years"}
    assert {item["assessmentYear"] for item in records} == {None}
    assert {item["submissionUse"] for item in records} == {"review_required"}
    assert {item["documentStatus"] for item in records} == {"dataset_current"}
    assert {item["sourceOutputId"] for item in records} == {None}
    assert {item["conflictGroupId"] for item in records} == {
        "example_substance.ul.openfoodtox3_variation"
    }
    assert all(ReferenceValueRecord.model_validate(item) for item in records)

    provenance = result["provenance"]["records"]
    assert {item["openfoodtox3"]["bound"] for item in provenance} == {"lower", "upper"}
    assert {len(item["openfoodtox3"]["dossiers"]) for item in provenance} == {2}
    lower = next(item for item in provenance if item["openfoodtox3"]["bound"] == "lower")
    assert lower["openfoodtox3"]["qualifier"] is None
    assert lower["openfoodtox3"]["qualifierWasExplicit"] is False


def test_candidate_migration_repairs_display_mojibake_and_preserves_raw_text() -> None:
    record = _record(
        "20",
        "Example substance",
        {
            "otherReferenceValues": {
                "ReferenceValueDescriptor": "UL",
                "RefValue.upperValue": 40,
                "RefValue.Unit": "\u00c2\u00b5g/day",
                "Population": "children",
                "Population.Remarks": "4\u00e2\u20ac\u201c6 years",
            }
        },
    )

    result = build_candidate_migration(_extraction([record]), _synonyms(), _old_bulk(), [])

    emitted = result["defaults"]["records"][0]
    assert emitted["unit"] == "\u00b5g/day"
    assert emitted["population"] == "children - 4\u20136 years"

    source = result["provenance"]["records"][0]["openfoodtox3"]
    assert source["unit"] == "\u00b5g/day"
    assert source["rawUnit"] == "\u00c2\u00b5g/day"
    assert source["normalizedUnit"] == "ug/day"
    assert source["populationRemarks"] == "4\u20136 years"
    assert source["rawPopulationRemarks"] == "4\u00e2\u20ac\u201c6 years"


def test_candidate_gates_hold_unsafe_and_curated_values() -> None:
    records = [
        _record(
            "3",
            "Worker value",
            {
                "otherReferenceValues": {
                    "ReferenceValueDescriptor": "TDI",
                    "RefValue.lowerValue": 1,
                    "RefValue.Unit": "mg/day",
                    "Population": "workers",
                }
            },
        ),
        _record(
            "4",
            "External value",
            {
                "otherReferenceValues": {
                    "ReferenceValueDescriptor": "TDI",
                    "RefValue.lowerValue": 1,
                    "RefValue.Unit": "mg/day",
                    "Population": "consumers",
                    "AssessmentBody": "other:",
                    "AssessmentBody.Other": "HBGV not from EFSA committees/panels",
                }
            },
        ),
        _record(
            "5",
            "Missing unit",
            {
                "acceptableDailyIntake": {
                    "Adi.lowerValue": 1,
                    "Population": "consumers",
                }
            },
        ),
        _record(
            "6",
            "Negative value",
            {
                "acceptableDailyIntake": {
                    "Adi.lowerValue": -1,
                    "Adi.Unit": "mg/kg bw/day",
                    "Population": "consumers",
                }
            },
        ),
        _record(
            "7",
            "Glyphosate",
            {
                "acceptableDailyIntake": {
                    "Adi.lowerValue": 0.5,
                    "Adi.Unit": "mg/kg bw/day",
                    "Population": "consumers",
                }
            },
        ),
        _record(
            "8",
            "No dossier",
            {
                "acceptableDailyIntake": {
                    "Adi.lowerValue": 0.5,
                    "Adi.Unit": "mg/kg bw/day",
                    "Population": "consumers",
                }
            },
            dossiers=[],
            review_flags=["missing_dossier_link"],
        ),
    ]

    result = build_candidate_migration(_extraction(records), _synonyms(), _old_bulk(), [])

    assert result["defaults"]["records"] == []
    counts = result["summary"]["heldReasonCounts"]
    assert counts["non_human_population"] == 1
    assert counts["unresolved_assessment_authority"] == 2
    assert counts["missing_unit"] == 1
    assert counts["invalid_nonpositive_or_nonfinite_value"] == 1
    assert counts["curated_record_precedence"] == 1
    assert counts["missing_dossier_link"] == 1


def test_named_global_authority_is_preserved_without_efsa_attribution() -> None:
    record = _record(
        "9",
        "Group substance",
        {
            "otherReferenceValues": {
                "ReferenceValueDescriptor": "other:",
                "ReferenceValueDescriptor.Other": "Group ADI",
                "RefValue.lowerValue": 0.3,
                "RefValue.Unit": "mg/kg bw/day",
                "Population": "consumers",
                "AssessmentBody": "other:",
                "AssessmentBody.Other": "JMPR",
            }
        },
    )

    result = build_candidate_migration(_extraction([record]), _synonyms(), _old_bulk(), [])
    emitted = result["defaults"]["records"][0]

    assert emitted["authority"] == "JMPR"
    assert emitted["jurisdiction"] == "codex_global"


def test_generation_is_deterministic_and_classifies_legacy_context() -> None:
    record = _record(
        "10",
        "Legacy substance",
        {
            "acceptableDailyIntake": {
                "Adi.lowerValue": 0.1,
                "Adi.Unit": "µg/kg bw/day",
                "Population": "consumers",
            }
        },
    )
    old = _old_bulk()
    old["records"] = [
        {
            "substanceKey": "legacy_substance",
            "referenceType": "adi",
            "value": 0.1,
            "unit": "ug/kg bw/day",
            "population": "consumers",
            "assessmentYear": 2020,
        }
    ]

    first = build_candidate_migration(_extraction([record]), _synonyms(), old, [])
    second = build_candidate_migration(deepcopy(_extraction([record])), _synonyms(), old, [])

    assert first == second
    assert first["provenance"]["records"][0]["migrationClassification"] == (
        "legacy_runtime_context_exact"
    )


def test_high_impact_review_keeps_curated_record_as_release_gate() -> None:
    records = [
        _record(
            "11",
            "Glyphosate",
            {
                "acceptableDailyIntake": {
                    "Adi.lowerValue": 0.5,
                    "Adi.Unit": "mg/kg bw/day",
                    "Population": "consumers",
                }
            },
        ),
        _record(
            "12",
            "Glyphosate",
            {
                "acceptableDailyIntake": {
                    "Adi.lowerValue": 1.0,
                    "Adi.Unit": "mg/kg bw/day",
                    "Population": "consumers",
                }
            },
        ),
    ]
    curated = [
        {
            "recordId": "efsa.openfoodtox.glyphosate.adi",
            "substanceKey": "glyphosate",
            "referenceType": "adi",
            "value": 0.5,
            "unit": "mg/kg bw/day",
            "sourceIds": ["efsa.openfoodtox"],
        }
    ]

    result = build_candidate_migration(
        _extraction(records),
        _synonyms(),
        _old_bulk(),
        curated,
    )

    assert result["defaults"]["records"] == []
    review = result["highImpactReview"]
    assert review["releaseGate"] == "human_toxicologist_review_required"
    assert review["records"][0]["supportStatus"] == "exact_supported_structured"
    assert review["recordCount"] == len(review["records"]) == 1
    assert len(review["contentSha256"]) == 64


def test_arfd_unit_correction_preserves_raw_workbook_encoding() -> None:
    record = _record(
        "8153",
        "Acetamiprid",
        {
            "acuteReferenceDose": {
                "Arfd.lowerValue": 0.005,
                "Arfd.Unit": "mg/kg bw/day",
                "Population": "consumers",
            }
        },
    )
    record["recordKey"] = "7f0e3478-4184-4dd9-936d-40f82b32ee4d#row-8153"
    curated = [
        {
            "recordId": "efsa.openfoodtox.acetamiprid.arfd",
            "substanceKey": "acetamiprid",
            "referenceType": "arfd",
            "value": 0.005,
            "unit": "mg/kg bw",
            "sourceIds": [
                "efsa.openfoodtox",
                "efsa.acetamiprid.statement.2024",
            ],
            "primarySourceId": "efsa.acetamiprid.statement.2024",
        }
    ]

    result = build_candidate_migration(
        _extraction([record]),
        _synonyms(),
        _old_bulk(),
        curated,
    )
    candidate = result["highImpactReview"]["records"][0]["openfoodtox3Candidates"][0]

    assert candidate["rawUnit"] == "mg/kg bw/day"
    assert candidate["normalizedUnit"] == "mg/kg bw"
    assert candidate["relationshipToCurated"] == "primary_source_unit_correction"
    assert candidate["unitCorrection"]["authoritySourceId"] == ("efsa.acetamiprid.statement.2024")
    assert candidate["sourceQualifierFieldPath"] is None


def test_nonexistent_lower_arfd_qualifier_column_is_not_claimed() -> None:
    record = _record(
        "13",
        "Example",
        {
            "acuteReferenceDose": {
                "Arfd.lowerValue": 0.1,
                "Arfd.Unit": "mg/kg bw",
                "Population": "consumers",
            }
        },
    )

    candidate = collect_source_candidates(_extraction([record]))[0]

    assert candidate["sourceQualifierFieldPath"] is None
    assert candidate["qualifierWasExplicit"] is False


def test_reference_point_candidates_preserve_structured_and_narrative_fields() -> None:
    structured = {
        "recordKey": "d9c10174-6dd0-4f77-b4aa-8e0eaf40111c#row-20",
        "sourceSheet": "END_STUDY_REC.HumanHealth",
        "sourceRowNumber": 20,
        "documentUuid": "d9c10174-6dd0-4f77-b4aa-8e0eaf40111c",
        "substanceUuid": "sub-arsenic",
        "referenceSubstanceUuid": "ref-arsenic",
        "substance": {"ChemicalName": "Arsenic, inorganic derivates"},
        "referenceSubstance": {"ReferenceSubstanceName": "Arsenic, inorganic derivates"},
        "dossiers": [_dossier("arsenic", year=2023)],
        "referencedLiterature": {
            "Document UUID": "lit-arsenic",
            "GeneralInfo.Name": "Arsenic opinion",
            "GeneralInfo.ReferenceYear": 2023,
            "GeneralInfo.Source": "DOI:10.2903/j.efsa.2024.8488",
        },
        "rawFields": {
            "ResultsAndDiscussion.EffectLevels.BasisForEffectLevel": "histopathology: neoplastic",
            "ResultsAndDiscussion.EffectLevels.DoseDescriptor": "BMDL05",
            "ResultsAndDiscussion.EffectLevels.EffectLevel.lowerValue": 0.06,
            "ResultsAndDiscussion.EffectLevels.EffectLevel.Unit": "other:",
            "ResultsAndDiscussion.EffectLevels.EffectLevel.Unit.Other": "ug/kg bw/day",
        },
        "reviewFlags": [],
    }
    narrative = {
        "recordKey": "1bec633b-5378-4e44-ab13-a5c0ac756787#row-21",
        "sourceSheet": "END_STUDY_REC.HumanHealth",
        "sourceRowNumber": 21,
        "documentUuid": "1bec633b-5378-4e44-ab13-a5c0ac756787",
        "substanceUuid": "sub-lead",
        "referenceSubstanceUuid": "ref-lead",
        "substance": {"ChemicalName": "Lead (Pb)"},
        "referenceSubstance": {"ReferenceSubstanceName": "Lead (Pb)"},
        "dossiers": [_dossier("lead", year=2010)],
        "referencedLiterature": {
            "Document UUID": "lit-lead",
            "GeneralInfo.Name": "Lead opinion",
            "GeneralInfo.ReferenceYear": 2010,
            "GeneralInfo.Source": "doi:10.2903/j.efsa.2010.1570",
        },
        "rawFields": {
            "ResultsAndDiscussion.AnyOtherInformationOnResultsInclTables.OtherInformation": (
                "Endpoint: ^ BMDL01; Value: '= 0.5 ug/kg bw/day; Basis: ^ neurology; "
                "Toxicity: developmental; Target tissue: Brain"
            )
        },
        "reviewFlags": [],
    }
    extraction = _extraction([])
    extraction["humanHealthRecords"] = [structured, narrative]

    candidates = collect_reference_point_candidates(extraction)

    assert [item["referenceType"] for item in candidates] == [
        "bmdl01_developmental_neurotoxicity",
        "bmdl05_skin_cancer",
    ]
    by_type = {item["referenceType"]: item for item in candidates}
    assert by_type["bmdl05_skin_cancer"]["sourceEncoding"] == "structured"
    assert by_type["bmdl05_skin_cancer"]["sourceUnitFieldPath"].endswith("Unit.Other")
    assert by_type["bmdl01_developmental_neurotoxicity"]["sourceEncoding"] == "unstructured"
    assert by_type["bmdl01_developmental_neurotoxicity"]["qualifier"] == "="
