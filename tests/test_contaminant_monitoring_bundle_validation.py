import pytest

from pathlib import Path

from dietary_mcp.contaminant_monitoring_bundle_validation import (
    run_contaminant_monitoring_bundle_cases,
)


pytestmark = [pytest.mark.slow]


def test_contaminant_monitoring_bundle_cases_pass() -> None:
    results = run_contaminant_monitoring_bundle_cases(Path(__file__).resolve().parents[1])

    assert results["status"] == "ok"
    assert {item["name"] for item in results["cases"]} == {
        "mercury_contaminant_monitoring_interpretation_bundle",
        "inorganic_arsenic_contaminant_monitoring_interpretation_bundle",
    }
