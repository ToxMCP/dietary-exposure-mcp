import pytest

from pathlib import Path

from dietary_mcp.sanitisation_validation import run_sanitised_public_review_cases


pytestmark = [pytest.mark.slow]


def test_sanitised_public_review_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    results = run_sanitised_public_review_cases(repo_root)

    assert results["status"] == "ok"
    assert len(results["cases"]) >= 2
    assert all(case["status"] == "ok" for case in results["cases"])
