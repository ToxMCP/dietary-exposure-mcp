import json
import sys

import pytest

from dietary_mcp import validation


def test_validation_cli_is_read_only_by_default_and_fails_non_ok(monkeypatch, capsys) -> None:
    called_generate = False
    summary = {
        "status": "review_required",
        "suiteCount": 1,
        "caseCount": 1,
        "failedCaseCount": 1,
        "suites": {
            "probabilistic_intake_summary": {
                "status": "review_required",
                "caseCount": 1,
                "failedCaseCount": 1,
            }
        },
        "failures": [
            {
                "suite": "probabilistic_intake_summary",
                "name": "injected_failure",
                "status": "review_required",
            }
        ],
    }

    def fake_generate_contract_artifacts(repo_root):
        nonlocal called_generate
        called_generate = True

    def fake_validate_generated_artifacts(repo_root):
        return {
            "probabilistic_intake_summary": [
                {"name": "injected_failure", "status": "review_required"}
            ],
            "status": "review_required",
            "suiteSummary": summary,
        }

    monkeypatch.setattr(sys, "argv", ["dietary-mcp-validate"])
    monkeypatch.setattr(validation, "generate_contract_artifacts", fake_generate_contract_artifacts)
    monkeypatch.setattr(validation, "validate_generated_artifacts", fake_validate_generated_artifacts)

    with pytest.raises(SystemExit) as exit_info:
        validation.main()

    assert exit_info.value.code == 1
    assert called_generate is False
    captured = capsys.readouterr()
    assert json.loads(captured.out)["status"] == "review_required"
    assert captured.err == ""


def test_validation_cli_can_generate_before_successful_validation(monkeypatch, capsys) -> None:
    called_generate = False
    summary = {
        "status": "ok",
        "suiteCount": 1,
        "caseCount": 1,
        "failedCaseCount": 0,
        "suites": {"schemas": {"status": "ok", "caseCount": 1, "failedCaseCount": 0}},
        "failures": [],
    }

    def fake_generate_contract_artifacts(repo_root):
        nonlocal called_generate
        called_generate = True

    def fake_validate_generated_artifacts(repo_root):
        return {
            "schemas": [{"name": "dietaryIntakeSummary.v1", "status": "ok"}],
            "status": "ok",
            "suiteSummary": summary,
        }

    monkeypatch.setattr(sys, "argv", ["dietary-mcp-validate", "--generate-artifacts"])
    monkeypatch.setattr(validation, "generate_contract_artifacts", fake_generate_contract_artifacts)
    monkeypatch.setattr(validation, "validate_generated_artifacts", fake_validate_generated_artifacts)

    validation.main()

    assert called_generate is True
    captured = capsys.readouterr()
    assert json.loads(captured.out)["status"] == "ok"
    assert captured.err == ""
