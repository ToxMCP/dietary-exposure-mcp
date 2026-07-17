import pytest

from pathlib import Path

from dietary_mcp.metals_monitoring_signoff_validation import run_metals_monitoring_signoff_cases


pytestmark = [pytest.mark.slow]


def test_metals_monitoring_signoff_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    results = run_metals_monitoring_signoff_cases(repo_root)

    assert results["status"] == "ok"
    assert len(results["cases"]) >= 3
    assert all(case["status"] == "ok" for case in results["cases"])
