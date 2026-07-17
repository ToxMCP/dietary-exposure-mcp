from pathlib import Path

import pytest

from dietary_mcp.contracts import generate_contract_artifacts
from dietary_mcp.validation import validate_generated_artifacts


@pytest.mark.slow
@pytest.mark.contract
def test_contract_generation_and_validation() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    generate_contract_artifacts(repo_root)
    results = validate_generated_artifacts(repo_root)
    assert all(item["status"] == "ok" for item in results["schemas"])
    assert all(item["status"] == "ok" for item in results["examples"])
    assert all(item["status"] == "ok" for item in results["benchmarks"])
    schema_names = {item["name"] for item in results["schemas"]}
    example_names = {item["name"] for item in results["examples"]}
    assert {
        "parseRawSurveyDatasetRequest.v1",
        "dietaryErrorPayload.v1",
        "dietarySurveyDatasetRecord.v1",
        "summarizeSurveyDistributionRequest.v1",
        "surveyDistributionSummaryReport.v1",
        "buildProbabilisticIntakeSummaryRequest.v1",
        "probabilisticIntakeSummary.v1",
        "residueUncertaintyModel.v1",
        "uncertaintyAssumptionLedger.v1",
        "buildUncertaintyIntakeAssessmentRequest.v1",
        "uncertaintyIntakeAssessment.v1",
    } <= schema_names
    assert {
        "parseRawSurveyDatasetRequest.v1.json",
        "dietaryErrorPayload.v1.json",
        "dietarySurveyDatasetRecord.v1.json",
        "summarizeSurveyDistributionRequest.v1.json",
        "surveyDistributionSummaryReport.v1.json",
        "buildProbabilisticIntakeSummaryRequest.v1.json",
        "probabilisticIntakeSummary.v1.json",
        "residueUncertaintyModel.v1.json",
        "uncertaintyAssumptionLedger.v1.json",
        "buildUncertaintyIntakeAssessmentRequest.v1.json",
        "uncertaintyIntakeAssessment.v1.json",
    } <= example_names
