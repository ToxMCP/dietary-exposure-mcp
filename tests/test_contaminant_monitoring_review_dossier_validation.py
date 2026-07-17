import pytest

from pathlib import Path

from dietary_mcp.contaminant_monitoring_review_dossier_validation import (
    run_contaminant_monitoring_review_dossier_cases,
)


pytestmark = [pytest.mark.slow]


def test_contaminant_monitoring_review_dossier_validation_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    results = run_contaminant_monitoring_review_dossier_cases(repo_root)

    assert results["status"] == "ok"
    assert all(case["status"] == "ok" for case in results["cases"])
