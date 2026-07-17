import pytest

from pathlib import Path

from dietary_mcp.reference_validation import run_dietary_reference_cases


pytestmark = [pytest.mark.slow]


def test_dietary_reference_cases_pass() -> None:
    results = run_dietary_reference_cases(Path(__file__).resolve().parents[1])
    assert results["status"] == "ok"
