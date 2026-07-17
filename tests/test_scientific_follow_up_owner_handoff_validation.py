import pytest

from pathlib import Path

from dietary_mcp.scientific_follow_up_owner_handoff_validation import (
    run_scientific_follow_up_owner_handoff_cases,
)


pytestmark = [pytest.mark.slow]


def test_scientific_follow_up_owner_handoff_validation_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = run_scientific_follow_up_owner_handoff_cases(repo_root)
    assert result["status"] == "ok"
    assert len(result["cases"]) >= 3
