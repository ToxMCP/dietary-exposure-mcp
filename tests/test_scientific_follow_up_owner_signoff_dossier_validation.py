import pytest

from pathlib import Path

from dietary_mcp.scientific_follow_up_owner_signoff_dossier_validation import (
    run_scientific_follow_up_owner_signoff_dossier_cases,
)


pytestmark = [pytest.mark.slow]


def test_scientific_follow_up_owner_signoff_dossier_validation_cases_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = run_scientific_follow_up_owner_signoff_dossier_cases(repo_root)
    assert result["status"] == "ok"
