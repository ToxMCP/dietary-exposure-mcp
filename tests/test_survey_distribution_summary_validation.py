import pytest

from pathlib import Path

from dietary_mcp.survey_distribution_summary_validation import run_survey_distribution_summary_cases

pytestmark = [pytest.mark.slow]


def test_survey_distribution_summary_cases() -> None:
    results = run_survey_distribution_summary_cases(Path(__file__).resolve().parents[1])
    assert results["status"] == "ok"
