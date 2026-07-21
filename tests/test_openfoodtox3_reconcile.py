from __future__ import annotations

import pandas as pd

from scripts.openfoodtox3_reconcile import build_reconciliation, summarize_reconciliation


def _record(*, value: float = 0.005, population: str = "consumers") -> dict:
    return {
        "recordKey": "tox-1#row-2",
        "toxReferenceDocumentUuid": "tox-1",
        "substanceUuid": "substance-1",
        "substance": {"ChemicalName": "Acetamiprid"},
        "referenceSubstance": {
            "ReferenceSubstanceName": "Acetamiprid",
            "Inventory.CASNumber": "135410-20-7",
        },
        "dossiers": [
            {
                "link": {"dossierUuid": "dossier-1"},
                "record": {
                    "LiteratureReference.DateOfEvaluation": "2024-03-27",
                    "LiteratureReference.LinkToPersistentIdentifier": (
                        "doi:10.2903/j.efsa.2024.8759"
                    ),
                },
            }
        ],
        "referencedLiterature": None,
        "valueSections": {
            "acceptableDailyIntake": {
                "Adi.lowerValue": value,
                "Adi.Unit": "mg/kg bw/day",
                "Population": population,
            }
        },
        "reviewFlags": [],
    }


def _old_record(*, value: float = 0.005) -> dict:
    return {
        "recordId": "efsa.openfoodtox.acetamiprid.adi",
        "openfoodtox": {
            "Substance": "Acetamiprid",
            "Author": "EFSA",
            "Year": 2024,
            "OutputID": 1,
            "Assessment": "ADI",
            "qualfier": "=",
            "value": value,
            "unit": "mg/kg bw/day",
            "Population": "Consumers",
        },
    }


def _extraction(records: list[dict]) -> dict:
    substances = []
    seen: set[str] = set()
    for record in records:
        if record["substanceUuid"] in seen:
            continue
        seen.add(record["substanceUuid"])
        substances.append(
            {
                "substanceUuid": record["substanceUuid"],
                "referenceSubstanceUuid": f"reference-{record['substanceUuid']}",
                "substance": record["substance"],
                "referenceSubstance": record["referenceSubstance"],
            }
        )
    return {"source": {"doi": "new"}, "substances": substances, "records": records}


def test_reconciliation_finds_unique_exact_context_match() -> None:
    reconciliation = build_reconciliation(
        {"sourceId": "old", "records": [_old_record()]},
        pd.DataFrame(
            [
                {
                    "Substance": "Acetamiprid",
                    "CASNumber": "_x0031_35410-20-7",
                }
            ]
        ),
        _extraction([_record()]),
    )

    result = reconciliation["records"][0]
    assert result["classification"] == "unchanged_exact"
    assert result["identityMethod"] == "exact_name"
    assert result["matchStageCounts"] == {
        "referenceType": 1,
        "value": 1,
        "unit": 1,
        "qualifier": 1,
        "population": 1,
        "assessmentYear": 1,
    }
    assert result["candidateMatches"][0]["persistentIdentifiers"] == [
        "doi:10.2903/j.efsa.2024.8759"
    ]


def test_reconciliation_does_not_hide_changed_value() -> None:
    reconciliation = build_reconciliation(
        {"sourceId": "old", "records": [_old_record(value=0.025)]},
        pd.DataFrame(columns=["Substance", "CASNumber"]),
        _extraction([_record(value=0.005)]),
    )

    result = reconciliation["records"][0]
    assert result["classification"] == "changed_or_missing_value"
    assert result["matchStageCounts"]["value"] == 0
    assert result["candidateMatches"][0]["value"] == 0.005


def test_reconciliation_keeps_ambiguous_identity_for_review() -> None:
    second = _record()
    second["recordKey"] = "tox-2#row-3"
    second["substanceUuid"] = "substance-2"

    reconciliation = build_reconciliation(
        {"sourceId": "old", "records": [_old_record()]},
        pd.DataFrame(columns=["Substance", "CASNumber"]),
        _extraction([_record(), second]),
    )

    result = reconciliation["records"][0]
    assert result["classification"] == "ambiguous_identity"
    assert result["candidateSubstanceUuids"] == ["substance-1", "substance-2"]
    assert result["candidateMatches"] == []


def test_reconciliation_summary_separates_exact_from_review_queue() -> None:
    reconciliation = {
        "oldSource": {"sourceId": "old"},
        "newSource": {"doi": "new"},
        "records": [
            {"classification": "unchanged_exact", "identityMethod": "exact_name"},
            {"classification": "ambiguous_identity", "identityMethod": "cas"},
        ],
    }

    summary = summarize_reconciliation(reconciliation)

    assert summary["classificationCounts"] == {
        "ambiguous_identity": 1,
        "unchanged_exact": 1,
    }
    assert summary["unchangedExactCount"] == 1
    assert summary["reviewRequiredCount"] == 1
    assert summary["status"] == "review_required"
