import pytest

from pathlib import Path

from dietary_mcp.interoperability_signoff_validation import run_interoperability_signoff_cases


pytestmark = [pytest.mark.slow]


def test_interoperability_signoff_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    results = run_interoperability_signoff_cases(repo_root)

    assert results["status"] == "ok"
    assert {item["name"] for item in results["cases"]} == {
        "internal_exchange_signoff_open_pending_actions",
        "internal_exchange_signoff_with_waiver",
        "submission_candidate_signoff_open_due_unresolved_blocking",
    }
