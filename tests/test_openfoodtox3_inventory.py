from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from openpyxl import Workbook

from scripts.openfoodtox3_inventory import SourceIntegrityError, build_inventory


def _write_sheet(workbook: Workbook, name: str, headers: list[str], rows: list[list[object]]) -> None:
    worksheet = workbook.create_sheet(name)
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)


def _synthetic_workbook(path: Path, *, include_unlinked_tox: bool = False) -> str:
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
        [["dossier-1", "substance-1/dossier-1", "2026-01-01", "Opinion", "doi:test"]],
    )
    _write_sheet(
        workbook,
        "DOSSIER_DOCS",
        ["DOSSIER UUID", "DOCUMENT UUID"],
        [["dossier-1", "tox-1"]],
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
        [["literature-1", "Opinion", 2026, "doi:test"]],
    )
    tox_rows = [["tox-1", "substance-1", "literature-1"]]
    if include_unlinked_tox:
        tox_rows.append(["tox-2", "substance-1", None])
    _write_sheet(
        workbook,
        "FLEX_SUM.ToxRefValues",
        [
            "Document UUID",
            "Parent UUID",
            "HumanHealthHazardCharacteristics.OtherReferenceValues.ReferenceToEFSAOpinion",
        ],
        tox_rows,
    )
    workbook.save(path)
    return hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()  # noqa: S324


def test_inventory_verifies_schema_and_uuid_joins(tmp_path: Path) -> None:
    path = tmp_path / "source.xlsx"
    expected_md5 = _synthetic_workbook(path)

    inventory = build_inventory(path, expected_md5=expected_md5)

    assert inventory["status"] == "ok"
    assert inventory["workbook"]["sheetCount"] == 6
    assert len(inventory["workbook"]["schemaSha256"]) == 64
    assert inventory["joinIntegrity"]["status"] == "ok"
    assert inventory["joinIntegrity"]["entityCounts"] == {
        "dossierDocumentUuids": 1,
        "literatureDocumentUuids": 1,
        "referenceSubstanceDocumentUuids": 1,
        "substanceDocumentUuids": 1,
        "toxReferenceValueRows": 1,
        "toxReferenceValueDocumentUuids": 1,
    }
    assert all(not values for values in inventory["joinIntegrity"]["unresolvedJoins"].values())


def test_inventory_marks_unlinked_tox_documents_for_review(tmp_path: Path) -> None:
    path = tmp_path / "source.xlsx"
    expected_md5 = _synthetic_workbook(path, include_unlinked_tox=True)

    inventory = build_inventory(path, expected_md5=expected_md5)

    assert inventory["status"] == "review_required"
    assert inventory["joinIntegrity"]["unlinkedToxReferenceValueDocumentUuids"] == ["tox-2"]
    assert inventory["joinIntegrity"]["errors"] == []


def test_inventory_rejects_unpinned_source(tmp_path: Path) -> None:
    path = tmp_path / "source.xlsx"
    _synthetic_workbook(path)

    with pytest.raises(SourceIntegrityError, match="checksum mismatch"):
        build_inventory(path, expected_md5="0" * 32)
