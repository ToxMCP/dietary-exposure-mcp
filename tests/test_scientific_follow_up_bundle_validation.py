import pytest

from pathlib import Path

from dietary_mcp.scientific_follow_up_bundle_validation import (
    run_scientific_follow_up_queue_bundle_cases,
)


pytestmark = [pytest.mark.slow]


def test_scientific_follow_up_queue_bundle_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    results = run_scientific_follow_up_queue_bundle_cases(repo_root)

    assert results["status"] == "ok"
    assert {item["name"] for item in results["cases"]} == {
        "efsa_primo_internal_review_empty_follow_up_bundle",
        "mercury_contaminant_internal_review_follow_up_bundle",
        "mercury_metals_submission_follow_up_bundle",
    }
