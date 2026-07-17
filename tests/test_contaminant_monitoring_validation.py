import pytest

from pathlib import Path

from dietary_mcp.contaminant_monitoring_validation import run_contaminant_monitoring_check_cases


pytestmark = [pytest.mark.slow]


def test_contaminant_monitoring_check_cases_pass() -> None:
    results = run_contaminant_monitoring_check_cases(Path(__file__).resolve().parents[1])

    assert results["status"] == "ok"
    assert {item["name"] for item in results["cases"]} == {
        "mercury_monitoring_import_check_links_occurrence_and_method_evidence",
        "inorganic_arsenic_monitoring_import_check_handles_rice_context",
        "lead_monitoring_import_check_fails_without_required_unit_header",
    }
