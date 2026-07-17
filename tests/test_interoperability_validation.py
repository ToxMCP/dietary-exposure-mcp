import pytest

from pathlib import Path

from dietary_mcp.interoperability_validation import run_interoperability_preview_cases


pytestmark = [pytest.mark.slow]


def test_interoperability_preview_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    results = run_interoperability_preview_cases(repo_root)

    assert results["status"] == "ok"
    assert {item["name"] for item in results["cases"]} == {
        "efsa_primo_oht_preview_review_required",
        "efsa_primo_oht_preview_missing_governance_fail",
    }
