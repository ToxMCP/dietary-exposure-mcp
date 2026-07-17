import pytest

from pathlib import Path

from dietary_mcp.interoperability_remediation_validation import run_interoperability_remediation_cases


pytestmark = [pytest.mark.slow]


def test_interoperability_remediation_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    results = run_interoperability_remediation_cases(repo_root)

    assert results["status"] == "ok"
    assert {item["name"] for item in results["cases"]} == {
        "internal_exchange_preview_remediation_bundle",
        "submission_xml_candidate_remediation_bundle",
        "missing_required_preview_remediation_bundle",
    }
