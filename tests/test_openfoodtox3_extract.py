from __future__ import annotations

import hashlib
from pathlib import Path

from openpyxl import Workbook

from scripts.openfoodtox3_extract import extract_openfoodtox3, summarize_extraction


def _write_sheet(workbook: Workbook, name: str, headers: list[str], rows: list[list[object]]) -> None:
    worksheet = workbook.create_sheet(name)
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)


def _source(path: Path) -> str:
    workbook = Workbook()
    workbook.remove(workbook.active)
    _write_sheet(
        workbook,
        "DOSSIER",
        [
            "Document UUID",
            "DossierSubject.Name",
            "LiteratureReference.DateOfEvaluation",
            "LiteratureReference.EFSAOutputTitle",
            "LiteratureReference.LinkToPersistentIdentifier",
        ],
        [
            ["dossier-1", "substance-1/dossier-1", "2024-03-27", "Opinion A", "doi:a"],
            ["dossier-2", "substance-1/dossier-2", "2016-10-17", "Opinion B", "doi:b"],
        ],
    )
    _write_sheet(
        workbook,
        "DOSSIER_DOCS",
        ["DOSSIER UUID", "DOCUMENT TYPE", "DOCUMENT SUBTYPE", "DOCUMENT UUID"],
        [
            ["dossier-1", "FLEXIBLE_SUMMARY", "ToxRefValues", "tox-1"],
            ["dossier-2", "FLEXIBLE_SUMMARY", "ToxRefValues", "tox-1"],
            [
                "dossier-1",
                "ENDPOINT_STUDY_RECORD",
                "EpidemiologicalData",
                "human-health-1",
            ],
        ],
    )
    _write_sheet(
        workbook,
        "REF_SUB",
        [
            "Document UUID",
            "Inventory.CASNumber",
            "MolecularStructuralInfo.InChIKey",
            "MolecularStructuralInfo.InChl",
            "MolecularStructuralInfo.SmilesNotation",
            "ReferenceSubstanceName",
        ],
        [["reference-1", "1-23-4", "KEY", "InChI=1S/test", "C", "Test substance"]],
    )
    _write_sheet(
        workbook,
        "SUB",
        ["Document UUID", "ChemicalName", "ReferenceSubstance.ReferenceSubstance"],
        [["substance-1", "Test substance", "reference-1"]],
    )
    _write_sheet(
        workbook,
        "LIT",
        ["Document UUID", "GeneralInfo.Name", "GeneralInfo.ReferenceYear", "GeneralInfo.Source"],
        [["literature-1", "Opinion A", 2024, "doi:a"]],
    )
    _write_sheet(
        workbook,
        "FLEX_SUM.ToxRefValues",
        [
            None,
            "Document UUID",
            "Definition",
            "Parent UUID",
            "Discussion.Discussion",
            "HumanHealthHazardCharacteristics.AcceptableDailyIntake.Adi.lowerValue",
            "HumanHealthHazardCharacteristics.AcceptableDailyIntake.Adi.Unit",
            "HumanHealthHazardCharacteristics.AcceptableDailyIntake.Population",
            "HumanHealthHazardCharacteristics.OtherReferenceValues.RefValue.lowerQualifier",
            "HumanHealthHazardCharacteristics.OtherReferenceValues.RefValue.lowerValue",
            "HumanHealthHazardCharacteristics.OtherReferenceValues.RefValue.Unit",
            "HumanHealthHazardCharacteristics.OtherReferenceValues.ReferenceToEFSAOpinion",
            "HumanHealthHazardCharacteristics.OtherReferenceValues.ReferenceValueDescriptor",
            "KeyInformation.KeyInformation",
        ],
        [
            [
                1,
                "tox-1",
                "FLEXIBLE_SUMMARY.ToxRefValues",
                "substance-1",
                "Discussion",
                0.005,
                "mg/kg bw/day",
                "consumers",
                ">=",
                1.5,
                "mg/day",
                "literature-1",
                "UL",
                "Key information",
            ]
        ],
    )
    _write_sheet(
        workbook,
        "END_STUDY_REC.HumanHealth",
        [
            None,
            "Document UUID",
            "Definition",
            "Parent UUID",
            "AdministrativeData.Endpoint",
            "DataSource.Reference",
            "ResultsAndDiscussion.EffectLevels.BasisForEffectLevel",
            "ResultsAndDiscussion.EffectLevels.DoseDescriptor",
            "ResultsAndDiscussion.EffectLevels.EffectLevel.lowerValue",
            "ResultsAndDiscussion.EffectLevels.EffectLevel.Unit",
        ],
        [
            [
                2,
                "human-health-1",
                "ENDPOINT_STUDY_RECORD.EpidemiologicalData",
                "substance-1",
                "epidemiological data",
                "literature-1",
                "histopathology: neoplastic",
                "BMDL05",
                0.06,
                "ug/kg bw/day",
            ]
        ],
    )
    workbook.save(path)
    return hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()  # noqa: S324


def test_extractor_preserves_sections_and_uuid_context(tmp_path: Path) -> None:
    path = tmp_path / "source.xlsx"
    expected_md5 = _source(path)

    extraction = extract_openfoodtox3(path, expected_md5=expected_md5)

    assert len(extraction["records"]) == 1
    assert len(extraction["humanHealthRecords"]) == 1
    assert len(extraction["substances"]) == 1
    assert extraction["substances"][0]["substanceUuid"] == "substance-1"
    record = extraction["records"][0]
    assert record["recordKey"] == "tox-1#row-2"
    assert record["substance"]["ChemicalName"] == "Test substance"
    assert record["referenceSubstance"]["Inventory.CASNumber"] == "1-23-4"
    assert [item["link"]["dossierUuid"] for item in record["dossiers"]] == [
        "dossier-1",
        "dossier-2",
    ]
    assert record["referencedLiterature"]["GeneralInfo.Source"] == "doi:a"
    assert record["valueSections"] == {
        "acceptableDailyIntake": {
            "Adi.lowerValue": 0.005,
            "Adi.Unit": "mg/kg bw/day",
            "Population": "consumers",
        },
        "otherReferenceValues": {
            "RefValue.lowerQualifier": ">=",
            "RefValue.lowerValue": 1.5,
            "RefValue.Unit": "mg/day",
            "ReferenceToEFSAOpinion": "literature-1",
            "ReferenceValueDescriptor": "UL",
        },
    }
    assert record["reviewFlags"] == ["multiple_dossier_links"]
    assert record["submissionUse"] == "review_required"
    human_health = extraction["humanHealthRecords"][0]
    assert human_health["recordKey"] == "human-health-1#row-2"
    assert human_health["sourceSheet"] == "END_STUDY_REC.HumanHealth"
    assert human_health["dataSourceReferenceUuid"] == "literature-1"
    assert human_health["referencedLiterature"]["GeneralInfo.Source"] == "doi:a"
    assert human_health["rawFields"][
        "ResultsAndDiscussion.EffectLevels.EffectLevel.lowerValue"
    ] == 0.06


def test_extraction_summary_counts_sections_and_review_flags(tmp_path: Path) -> None:
    path = tmp_path / "source.xlsx"
    expected_md5 = _source(path)

    summary = summarize_extraction(extract_openfoodtox3(path, expected_md5=expected_md5))

    assert summary["recordCount"] == 1
    assert summary["humanHealthRecordCount"] == 1
    assert summary["humanHealthStructuredEffectValueCount"] == 1
    assert summary["humanHealthNarrativeReferencePointCount"] == 0
    assert summary["humanHealthReviewFlagCounts"] == {}
    assert summary["substanceCount"] == 1
    assert summary["sectionRecordCounts"] == {
        "acceptableDailyIntake": 1,
        "otherReferenceValues": 1,
    }
    assert summary["reviewFlagCounts"] == {"multiple_dossier_links": 1}
    assert summary["otherReferenceValueDescriptorCounts"] == {"UL": 1}
    assert summary["status"] == "review_required"
