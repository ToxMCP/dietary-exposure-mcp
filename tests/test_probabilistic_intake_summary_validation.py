import pytest

from pathlib import Path

from dietary_mcp.probabilistic_intake_summary_validation import run_probabilistic_intake_summary_cases

pytestmark = [pytest.mark.slow]


def test_probabilistic_intake_summary_cases() -> None:
    results = run_probabilistic_intake_summary_cases(Path(__file__).resolve().parents[1])
    assert results["status"] == "ok"
    assert len(results["cases"]) == 4
    assert all(case["status"] == "ok" for case in results["cases"])
    assert len(results["fingerprintComparisons"]) == 2
    assert all(item["status"] == "ok" for item in results["fingerprintComparisons"])
