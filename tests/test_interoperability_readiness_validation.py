import pytest

from pathlib import Path

from dietary_mcp.interoperability_readiness_validation import run_interoperability_readiness_cases


pytestmark = [pytest.mark.slow]


def test_interoperability_readiness_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    results = run_interoperability_readiness_cases(repo_root)

    assert results["status"] == "ok"
    assert {item["name"] for item in results["cases"]} == {
        "eu_internal_exchange_preview_current_model",
        "eu_consultation_exchange_preview_current_model",
        "eu_submission_xml_candidate_current_model",
        "eu_internal_exchange_preview_missing_required",
    }
