from pathlib import Path

import pytest

from dietary_mcp.uncertainty_validation import (
    run_censored_residue_policy_cases,
    run_health_reference_exceedance_cases,
    run_uncertainty_intake_assessment_cases,
    run_uncertainty_reproducibility_cases,
    run_uncertainty_sensitivity_cases,
)

pytestmark = [pytest.mark.slow]


def test_uncertainty_validation_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    suites = [
        (run_uncertainty_intake_assessment_cases(repo_root), 4),
        (run_censored_residue_policy_cases(repo_root), 1),
        (run_uncertainty_sensitivity_cases(repo_root), 1),
        (run_health_reference_exceedance_cases(repo_root), 3),
        (run_uncertainty_reproducibility_cases(repo_root), 1),
    ]

    for results, expected_count in suites:
        assert results["status"] == "ok"
        assert len(results["cases"]) == expected_count
        assert all(case["status"] == "ok" for case in results["cases"])
