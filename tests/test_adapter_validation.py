import pytest

from pathlib import Path

from dietary_mcp.adapter_validation import run_adapter_normalization_cases


pytestmark = [pytest.mark.slow]


def test_adapter_normalization_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    results = run_adapter_normalization_cases(repo_root)

    assert results["status"] == "ok"
    assert len(results["cases"]) >= 2
    assert all(case["status"] == "ok" for case in results["cases"])
