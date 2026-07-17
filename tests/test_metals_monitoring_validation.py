import pytest

from pathlib import Path

from dietary_mcp.metals_monitoring_validation import run_metals_monitoring_bundle_cases


pytestmark = [pytest.mark.slow]


def test_metals_monitoring_bundle_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    results = run_metals_monitoring_bundle_cases(repo_root)

    assert results["status"] == "ok"
    assert {item["name"] for item in results["cases"]} == {
        "mercury_monitoring_interpretation_bundle",
        "inorganic_arsenic_monitoring_interpretation_bundle",
    }
