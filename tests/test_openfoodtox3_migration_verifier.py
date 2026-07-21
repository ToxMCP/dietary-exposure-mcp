from pathlib import Path

import pytest

from scripts.verify_openfoodtox3_migration import (
    MigrationVerificationError,
    _verify_field_path,
    verify_migration,
)


def test_tracked_openfoodtox3_migration_passes_release_invariants() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    result = verify_migration(repo_root)

    assert result == {
        "status": "ok",
        "sourceId": "efsa.openfoodtox",
        "sourceDoi": "10.5281/zenodo.19388272",
        "runtimeRecordCount": 2417,
        "provenanceRecordCount": 2417,
        "highImpactReviewRecordCount": 16,
        "releaseGate": "human_toxicologist_review_required",
    }


def test_verifier_rejects_nonexistent_workbook_field_path() -> None:
    headers = {"FLEX_SUM.ToxRefValues": {"actual.header"}}

    with pytest.raises(MigrationVerificationError, match="does not resolve"):
        _verify_field_path(
            headers,
            source_sheet="FLEX_SUM.ToxRefValues",
            field_path="invented.header",
            label="test provenance",
        )

    _verify_field_path(
        headers,
        source_sheet="FLEX_SUM.ToxRefValues",
        field_path=None,
        label="optional qualifier",
    )
