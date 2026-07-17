import pytest

from pathlib import Path

from dietary_mcp.readiness_validation import run_review_dossier_readiness_cases


pytestmark = [pytest.mark.slow]


def test_review_dossier_readiness_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    results = run_review_dossier_readiness_cases(repo_root)

    assert results["status"] == "ok"
    assert {item["name"] for item in results["cases"]} == {
        "efsa_primo_internal_review_current_model",
        "efsa_primo_consultation_exploratory_current_model",
        "efsa_primo_submission_candidate_current_model",
        "epa_deem_internal_review_errata",
        "mercury_contaminant_internal_review_current_family",
        "mercury_contaminant_consultation_exploratory_current_family",
        "mercury_metals_submission_candidate_current_family",
    }
