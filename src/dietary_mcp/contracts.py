from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import sync_packaged_data
from dietary_mcp.errors import DietaryErrorPayload
from dietary_mcp.examples import write_examples
from dietary_mcp.models import (
    AssessInteroperabilityPreviewReadinessRequest,
    AdapterImportCheckResult,
    AdapterReviewBundle,
    AnalyticalMethodEvidenceLookupResult,
    AssessReviewDossierReadinessRequest,
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    BuildBoundedIntakeSummaryRequest,
    BuildUncertaintyIntakeAssessmentRequest,
    CheckAdapterImportRequest,
    CheckContaminantMonitoringImportRequest,
    CompareAdapterImportToWalkthroughRequest,
    CompareAdapterImportToWalkthroughResult,
    ContaminantMonitoringSignoffPacket,
    ContaminantMonitoringInterpretationBundle,
    ContaminantMonitoringImportCheckResult,
    VersionPinnedContaminantMonitoringReviewDossier,
    ConsumptionProfileSelectionResult,
    DietaryAssumptionRecord,
    DietaryCommodityResidueRecord,
    DietaryConsumptionProfile,
    DietarySurveyDatasetRecord,
    DietaryContributionRecord,
    DietaryIntakeScenarioDefinition,
    DietaryIntakeSummary,
    DietaryResidueProfile,
    DietaryScenarioComparisonRecord,
    BuildProbabilisticIntakeSummaryRequest,
    ExportAdapterReviewBundleRequest,
    ExportTradeRiskReviewBundleRequest,
    ExportContaminantMonitoringInterpretationBundleRequest,
    ExportContaminantMonitoringSignoffPacketRequest,
    ExportVersionPinnedContaminantMonitoringReviewDossierRequest,
    ExportVersionPinnedTradeRiskReviewDossierRequest,
    ExportInteroperabilityPreviewRequest,
    ExportInteroperabilityRemediationBundleRequest,
    ExportInteroperabilitySignoffPacketRequest,
    ExportMetalsMonitoringInterpretationBundleRequest,
    ExportMetalsMonitoringSignoffPacketRequest,
    ExportScientificFollowUpQueueBundleRequest,
    ExportScientificFollowUpOwnerHandoffPacketRequest,
    ExportScientificFollowUpOwnerRemediationPacketRequest,
    ExportScientificFollowUpOwnerSignoffPacketRequest,
    ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest,
    ExportScientificFollowUpReviewBoardRequest,
    ExportVersionPinnedMetalsMonitoringReviewDossierRequest,
    ExportSanitisedPublicReviewDossierRequest,
    ExportVersionPinnedAdapterReviewDossierRequest,
    ExportPbpkOralInputRequest,
    InteroperabilityExportPreview,
    InteroperabilityRemediationBundle,
    InteroperabilitySignoffPacket,
    InteroperabilityPreviewReadinessAssessment,
    LookupAnalyticalMethodEvidenceRequest,
    LookupContaminantLegalLimitsRequest,
    LookupConsumptionDatasetSupportRequest,
    LookupOccurrenceEvidenceRequest,
    LookupReportingProfilesRequest,
    LookupMethodSupportRequest,
    LookupReferenceValuesRequest,
    LookupMetalsReviewFocusRequest,
    ParseRawSurveyDatasetRequest,
    PbpkExternalImportBundle,
    ProbabilisticIntakeSummary,
    ResidueUncertaintyModel,
    ConsumptionDatasetSupportLookupResult,
    MethodSupportLookupResult,
    LookupMetalsOccurrenceRequest,
    MetalsOccurrenceLookupResult,
    MetalsMonitoringInterpretationBundle,
    MetalsMonitoringSignoffPacket,
    OccurrenceEvidenceLookupResult,
    ReportingProfileLookupResult,
    ScientificFollowUpQueueBundle,
    ScientificFollowUpOwnerHandoffPacket,
    ScientificFollowUpOwnerRemediationPacket,
    ScientificFollowUpOwnerSignoffPacket,
    VersionPinnedScientificFollowUpOwnerSignoffDossier,
    ScientificFollowUpReviewBoard,
    VersionPinnedMetalsMonitoringReviewDossier,
    MetalsReviewFocusLookupResult,
    ContaminantLegalLimitLookupResult,
    ReferenceValueLookupResult,
    EvaluateGlobalTradeRiskRequest,
    GlobalTradeRiskReport,
    ReviewDossierReadinessAssessment,
    RouteDoseEstimate,
    SelectConsumptionProfileRequest,
    SanitisedPublicReviewDossier,
    SummarizeSurveyDistributionRequest,
    SurveyDistributionSummaryReport,
    ToxclawDietaryEvidenceBundle,
    TradeRiskReviewBundle,
    UncertaintyAssumptionLedger,
    UncertaintyIntakeAssessment,
    VersionPinnedAdapterReviewDossier,
    VersionPinnedTradeRiskReviewDossier,
)
from dietary_mcp.runtime import get_cached_dietary_runtime


SCHEMA_MODELS = {
    "buildDietaryResidueProfileRequest.v1": BuildDietaryResidueProfileRequest,
    "dietaryErrorPayload.v1": DietaryErrorPayload,
    "selectConsumptionProfileRequest.v1": SelectConsumptionProfileRequest,
    "consumptionProfileSelectionResult.v1": ConsumptionProfileSelectionResult,
    "buildDietaryIntakeScenarioRequest.v1": BuildDietaryIntakeScenarioRequest,
    "buildBoundedIntakeSummaryRequest.v1": BuildBoundedIntakeSummaryRequest,
    "parseRawSurveyDatasetRequest.v1": ParseRawSurveyDatasetRequest,
    "dietarySurveyDatasetRecord.v1": DietarySurveyDatasetRecord,
    "summarizeSurveyDistributionRequest.v1": SummarizeSurveyDistributionRequest,
    "surveyDistributionSummaryReport.v1": SurveyDistributionSummaryReport,
    "buildProbabilisticIntakeSummaryRequest.v1": BuildProbabilisticIntakeSummaryRequest,
    "probabilisticIntakeSummary.v1": ProbabilisticIntakeSummary,
    "residueUncertaintyModel.v1": ResidueUncertaintyModel,
    "uncertaintyAssumptionLedger.v1": UncertaintyAssumptionLedger,
    "buildUncertaintyIntakeAssessmentRequest.v1": BuildUncertaintyIntakeAssessmentRequest,
    "uncertaintyIntakeAssessment.v1": UncertaintyIntakeAssessment,
    "checkAdapterImportRequest.v1": CheckAdapterImportRequest,
    "checkContaminantMonitoringImportRequest.v1": CheckContaminantMonitoringImportRequest,
    "adapterImportCheckResult.v1": AdapterImportCheckResult,
    "contaminantMonitoringImportCheckResult.v1": ContaminantMonitoringImportCheckResult,
    "exportContaminantMonitoringInterpretationBundleRequest.v1": ExportContaminantMonitoringInterpretationBundleRequest,
    "contaminantMonitoringInterpretationBundle.v1": ContaminantMonitoringInterpretationBundle,
    "exportContaminantMonitoringSignoffPacketRequest.v1": ExportContaminantMonitoringSignoffPacketRequest,
    "contaminantMonitoringSignoffPacket.v1": ContaminantMonitoringSignoffPacket,
    "exportVersionPinnedContaminantMonitoringReviewDossierRequest.v1": (
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest
    ),
    "versionPinnedContaminantMonitoringReviewDossier.v1": VersionPinnedContaminantMonitoringReviewDossier,
    "compareAdapterImportToWalkthroughRequest.v1": CompareAdapterImportToWalkthroughRequest,
    "compareAdapterImportToWalkthroughResult.v1": CompareAdapterImportToWalkthroughResult,
    "exportAdapterReviewBundleRequest.v1": ExportAdapterReviewBundleRequest,
    "adapterReviewBundle.v1": AdapterReviewBundle,
    "exportVersionPinnedAdapterReviewDossierRequest.v1": ExportVersionPinnedAdapterReviewDossierRequest,
    "versionPinnedAdapterReviewDossier.v1": VersionPinnedAdapterReviewDossier,
    "exportSanitisedPublicReviewDossierRequest.v1": ExportSanitisedPublicReviewDossierRequest,
    "sanitisedPublicReviewDossier.v1": SanitisedPublicReviewDossier,
    "exportInteroperabilityPreviewRequest.v1": ExportInteroperabilityPreviewRequest,
    "interoperabilityExportPreview.v1": InteroperabilityExportPreview,
    "assessInteroperabilityPreviewReadinessRequest.v1": AssessInteroperabilityPreviewReadinessRequest,
    "interoperabilityPreviewReadinessAssessment.v1": InteroperabilityPreviewReadinessAssessment,
    "exportInteroperabilityRemediationBundleRequest.v1": ExportInteroperabilityRemediationBundleRequest,
    "interoperabilityRemediationBundle.v1": InteroperabilityRemediationBundle,
    "exportInteroperabilitySignoffPacketRequest.v1": ExportInteroperabilitySignoffPacketRequest,
    "interoperabilitySignoffPacket.v1": InteroperabilitySignoffPacket,
    "assessReviewDossierReadinessRequest.v1": AssessReviewDossierReadinessRequest,
    "reviewDossierReadinessAssessment.v1": ReviewDossierReadinessAssessment,
    "exportScientificFollowUpQueueBundleRequest.v1": ExportScientificFollowUpQueueBundleRequest,
    "scientificFollowUpQueueBundle.v1": ScientificFollowUpQueueBundle,
    "exportScientificFollowUpReviewBoardRequest.v1": ExportScientificFollowUpReviewBoardRequest,
    "scientificFollowUpReviewBoard.v1": ScientificFollowUpReviewBoard,
    "exportScientificFollowUpOwnerHandoffPacketRequest.v1": ExportScientificFollowUpOwnerHandoffPacketRequest,
    "scientificFollowUpOwnerHandoffPacket.v1": ScientificFollowUpOwnerHandoffPacket,
    "exportScientificFollowUpOwnerRemediationPacketRequest.v1": (
        ExportScientificFollowUpOwnerRemediationPacketRequest
    ),
    "scientificFollowUpOwnerRemediationPacket.v1": ScientificFollowUpOwnerRemediationPacket,
    "exportScientificFollowUpOwnerSignoffPacketRequest.v1": ExportScientificFollowUpOwnerSignoffPacketRequest,
    "scientificFollowUpOwnerSignoffPacket.v1": ScientificFollowUpOwnerSignoffPacket,
    "exportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest.v1": (
        ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest
    ),
    "versionPinnedScientificFollowUpOwnerSignoffDossier.v1": VersionPinnedScientificFollowUpOwnerSignoffDossier,
    "lookupReferenceValuesRequest.v1": LookupReferenceValuesRequest,
    "referenceValueLookupResult.v1": ReferenceValueLookupResult,
    "evaluateGlobalTradeRiskRequest.v1": EvaluateGlobalTradeRiskRequest,
    "globalTradeRiskReport.v1": GlobalTradeRiskReport,
    "exportTradeRiskReviewBundleRequest.v1": ExportTradeRiskReviewBundleRequest,
    "tradeRiskReviewBundle.v1": TradeRiskReviewBundle,
    "exportVersionPinnedTradeRiskReviewDossierRequest.v1": ExportVersionPinnedTradeRiskReviewDossierRequest,
    "versionPinnedTradeRiskReviewDossier.v1": VersionPinnedTradeRiskReviewDossier,
    "lookupContaminantLegalLimitsRequest.v1": LookupContaminantLegalLimitsRequest,
    "contaminantLegalLimitLookupResult.v1": ContaminantLegalLimitLookupResult,
    "lookupMethodSupportRequest.v1": LookupMethodSupportRequest,
    "methodSupportLookupResult.v1": MethodSupportLookupResult,
    "lookupConsumptionDatasetSupportRequest.v1": LookupConsumptionDatasetSupportRequest,
    "consumptionDatasetSupportLookupResult.v1": ConsumptionDatasetSupportLookupResult,
    "lookupReportingProfilesRequest.v1": LookupReportingProfilesRequest,
    "reportingProfileLookupResult.v1": ReportingProfileLookupResult,
    "lookupOccurrenceEvidenceRequest.v1": LookupOccurrenceEvidenceRequest,
    "occurrenceEvidenceLookupResult.v1": OccurrenceEvidenceLookupResult,
    "lookupAnalyticalMethodEvidenceRequest.v1": LookupAnalyticalMethodEvidenceRequest,
    "analyticalMethodEvidenceLookupResult.v1": AnalyticalMethodEvidenceLookupResult,
    "lookupMetalsOccurrenceRequest.v1": LookupMetalsOccurrenceRequest,
    "metalsOccurrenceLookupResult.v1": MetalsOccurrenceLookupResult,
    "lookupMetalsReviewFocusRequest.v1": LookupMetalsReviewFocusRequest,
    "metalsReviewFocusLookupResult.v1": MetalsReviewFocusLookupResult,
    "exportMetalsMonitoringInterpretationBundleRequest.v1": ExportMetalsMonitoringInterpretationBundleRequest,
    "metalsMonitoringInterpretationBundle.v1": MetalsMonitoringInterpretationBundle,
    "exportMetalsMonitoringSignoffPacketRequest.v1": ExportMetalsMonitoringSignoffPacketRequest,
    "metalsMonitoringSignoffPacket.v1": MetalsMonitoringSignoffPacket,
    "exportVersionPinnedMetalsMonitoringReviewDossierRequest.v1": ExportVersionPinnedMetalsMonitoringReviewDossierRequest,
    "versionPinnedMetalsMonitoringReviewDossier.v1": VersionPinnedMetalsMonitoringReviewDossier,
    "exportPbpkOralInputRequest.v1": ExportPbpkOralInputRequest,
    "dietaryCommodityResidueRecord.v1": DietaryCommodityResidueRecord,
    "dietaryResidueProfile.v1": DietaryResidueProfile,
    "dietaryConsumptionProfile.v1": DietaryConsumptionProfile,
    "dietaryIntakeScenarioDefinition.v1": DietaryIntakeScenarioDefinition,
    "dietaryContributionRecord.v1": DietaryContributionRecord,
    "dietaryAssumptionRecord.v1": DietaryAssumptionRecord,
    "dietaryIntakeSummary.v1": DietaryIntakeSummary,
    "dietaryScenarioComparisonRecord.v1": DietaryScenarioComparisonRecord,
    "routeDoseEstimate.v1": RouteDoseEstimate,
    "pbpkExternalImportBundle.v1": PbpkExternalImportBundle,
    "toxclawDietaryEvidenceBundle.v1": ToxclawDietaryEvidenceBundle,
}


def build_contract_manifest() -> dict:
    return {
        "schemas": [
            {
                "name": name,
                "path": f"docs/contracts/schemas/{name}.json",
            }
            for name in sorted(SCHEMA_MODELS.keys())
        ]
    }


def generate_contract_artifacts(repo_root: Path) -> None:
    schema_dir = repo_root / "docs" / "contracts" / "schemas"
    schema_dir.mkdir(parents=True, exist_ok=True)
    for name, model in SCHEMA_MODELS.items():
        (schema_dir / f"{name}.json").write_text(json.dumps(model.model_json_schema(), indent=2) + "\n")
    (schema_dir / "manifest.json").write_text(json.dumps(build_contract_manifest(), indent=2) + "\n")

    runtime = get_cached_dietary_runtime(repo_root)
    write_examples(repo_root, runtime)
    runtime.defaults.write_manifest()
    sync_packaged_data(repo_root)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    generate_contract_artifacts(repo_root)


if __name__ == "__main__":
    main()
