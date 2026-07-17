from __future__ import annotations

import functools
import json
import logging
import time
import uuid

from mcp.types import CallToolResult, TextContent, ToolAnnotations
from mcp.server.fastmcp import FastMCP

from dietary_mcp import models as dm
from dietary_mcp.errors import DietaryError, DietaryErrorPayload
from dietary_mcp.integrations import (
    compare_dietary_scenarios,
    export_pbpk_oral_input,
    export_toxclaw_dietary_evidence_bundle,
)
from dietary_mcp.models import (
    AssessInteroperabilityPreviewReadinessRequest,
    AssessReviewDossierReadinessRequest,
    ApplyResidueEvidenceRequest,
    AssessResidueEvidenceFitRequest,
    CheckAdapterImportRequest,
    CheckContaminantMonitoringImportRequest,
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    BuildBoundedIntakeSummaryRequest,
    BuildUncertaintyIntakeAssessmentRequest,
    CompareAdapterImportToWalkthroughRequest,
    CompareDietaryScenariosRequest,
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
    ExportToxclawDietaryEvidenceBundleRequest,
    EvaluateGlobalTradeRiskRequest,
    ParseRawSurveyDatasetRequest,
    SummarizeSurveyDistributionRequest,
    BuildProbabilisticIntakeSummaryRequest,
    LookupContaminantLegalLimitsRequest,
    LookupConsumptionDatasetSupportRequest,
    LookupOccurrenceEvidenceRequest,
    LookupAnalyticalMethodEvidenceRequest,
    LookupReportingProfilesRequest,
    LookupMetalsOccurrenceRequest,
    LookupMetalsReviewFocusRequest,
    LookupMethodSupportRequest,
    LookupReferenceValuesRequest,
    ReconcileResidueEvidenceRequest,
    SelectConsumptionProfileRequest,
)
from dietary_mcp.runtime import DietaryRuntime

_LOGGER = logging.getLogger("dietary_mcp.tools")
_READ_ONLY_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
def _tool_title(tool_name: str) -> str:
    words = tool_name.removeprefix("dietary_").replace("_", " ").title()
    return f"Dietary {words}"


def _tool_annotations(tool_name: str) -> ToolAnnotations:
    # Every current MCP tool is a pure transformation that returns data to the
    # client. "Export" tools build payloads; they do not write or publish them.
    return _READ_ONLY_TOOL_ANNOTATIONS


def _dietary_tool(mcp: FastMCP):
    def decorator(func):
        return mcp.tool(
            title=_tool_title(func.__name__),
            annotations=_tool_annotations(func.__name__),
            structured_output=True,
        )(func)

    return decorator


def _error_result(exc: DietaryError, request_id: str) -> CallToolResult:
    payload = exc.payload.model_copy(
        update={
            "details": {
                **exc.payload.details,
                "requestId": request_id,
            }
        }
    )
    payload_dict = payload.model_dump(mode="json")
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps(payload_dict, indent=2, sort_keys=True),
            )
        ],
        structuredContent={"result": payload_dict},
        isError=True,
    )


def _trace_tool(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        request_id = str(uuid.uuid4())[:8]
        tool_name = func.__name__
        start = time.perf_counter()
        _LOGGER.info("Tool start: %s (request_id=%s)", tool_name, request_id)
        try:
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            _LOGGER.info("Tool end: %s (request_id=%s, elapsed_ms=%.2f)", tool_name, request_id, elapsed_ms)
            return result
        except DietaryError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            _LOGGER.warning(
                "Tool domain error: %s (request_id=%s, elapsed_ms=%.2f, error=%s)",
                tool_name, request_id, elapsed_ms, exc,
            )
            return _error_result(exc, request_id)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            _LOGGER.warning(
                "Tool error: %s (request_id=%s, elapsed_ms=%.2f, error=%s)",
                tool_name, request_id, elapsed_ms, exc,
            )
            raise

    return wrapper


def register_tools(mcp: FastMCP, runtime: DietaryRuntime) -> None:
    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_build_residue_profile(
        request: BuildDietaryResidueProfileRequest,
    ) -> dm.DietaryResidueProfile | DietaryErrorPayload:
        """Validate, normalize, and package commodity residue evidence into a dietary residue profile."""
        return runtime.build_residue_profile(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_select_consumption_profile(
        request: SelectConsumptionProfileRequest,
    ) -> dm.ConsumptionProfileSelectionResult | DietaryErrorPayload:
        """Select a governed dietary consumption profile for a declared population and intake window."""
        return runtime.select_consumption_profile(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_build_dietary_intake_scenario(
        request: BuildDietaryIntakeScenarioRequest,
    ) -> dm.DietaryIntakeScenarioDefinition | DietaryErrorPayload:
        """Build a dietary intake scenario with explicit acute/chronic semantics."""
        return runtime.build_dietary_intake_scenario(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_build_bounded_intake_summary(
        request: BuildBoundedIntakeSummaryRequest,
    ) -> dm.DietaryIntakeSummary | DietaryErrorPayload:
        """Compute a point-estimate or bounded intake summary for a validated dietary scenario."""
        return runtime.summarize_intake(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_compare_dietary_scenarios(
        request: CompareDietaryScenariosRequest,
    ) -> dm.DietaryScenarioComparisonRecord | DietaryErrorPayload:
        """Compare dietary scenario summaries and surface commodity-level drivers."""
        return compare_dietary_scenarios(request, runtime.provenance)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_assess_residue_evidence_fit(
        request: AssessResidueEvidenceFitRequest,
    ) -> dm.ResidueEvidenceFitAssessment | DietaryErrorPayload:
        """Assess residue-profile coverage and fitness for the selected dietary workflow."""
        return runtime.assess_residue_evidence_fit(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_apply_residue_evidence(
        request: ApplyResidueEvidenceRequest,
    ) -> dm.ResidueEvidenceApplicationResult | DietaryErrorPayload:
        """Merge additional residue evidence into an existing dietary residue profile."""
        return runtime.apply_residue_evidence(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_reconcile_residue_evidence(
        request: ReconcileResidueEvidenceRequest,
    ) -> dm.ResidueEvidenceReconciliationResult | DietaryErrorPayload:
        """Reconcile multiple residue profiles into a reviewable screening profile."""
        return runtime.reconcile_residue_evidence(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_evaluate_global_trade_risk(
        request: EvaluateGlobalTradeRiskRequest,
    ) -> dm.GlobalTradeRiskReport | DietaryErrorPayload:
        """Evaluate global trade risk across jurisdictions based on MRL violations and reference values."""
        return runtime.evaluate_global_trade_risk(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_parse_raw_survey_dataset(
        request: ParseRawSurveyDatasetRequest,
    ) -> dm.DietarySurveyDatasetRecord | DietaryErrorPayload:
        """Parse, validate, and normalize raw individual survey consumption records into a governed dataset."""
        return runtime.parse_raw_survey_dataset(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_summarize_survey_distribution(
        request: SummarizeSurveyDistributionRequest,
    ) -> dm.SurveyDistributionSummaryReport | DietaryErrorPayload:
        """Calculate governed intake distributions, percentiles, and zero-intake prevalence from a raw survey dataset without executing a full Monte Carlo simulation."""
        return runtime.summarize_survey_distribution(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_build_probabilistic_intake_summary(
        request: BuildProbabilisticIntakeSummaryRequest,
    ) -> dm.ProbabilisticIntakeSummary | DietaryErrorPayload:
        """Execute governed cohort-bootstrap review support over raw survey distributions."""
        return runtime.build_probabilistic_intake_summary(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_build_uncertainty_intake_assessment(
        request: BuildUncertaintyIntakeAssessmentRequest,
    ) -> dm.UncertaintyIntakeAssessment | DietaryErrorPayload:
        """Run a transparent two-dimensional uncertainty intake assessment with explicit assumptions."""
        return runtime.build_uncertainty_intake_assessment(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_check_adapter_import(
        request: CheckAdapterImportRequest,
    ) -> dm.AdapterImportCheckResult | DietaryErrorPayload:
        """Validate adapter-style CSV input and return a stable normalized projection for review."""
        return runtime.check_adapter_import(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_check_contaminant_monitoring_import(
        request: CheckContaminantMonitoringImportRequest,
    ) -> dm.ContaminantMonitoringImportCheckResult | DietaryErrorPayload:
        """Validate contaminant-monitoring CSV input against governed occurrence and analytical-method evidence records."""
        return runtime.check_contaminant_monitoring_import(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_compare_adapter_import_to_walkthrough(
        request: CompareAdapterImportToWalkthroughRequest,
    ) -> dm.CompareAdapterImportToWalkthroughResult | DietaryErrorPayload:
        """Compare a checked adapter import result to a governed walkthrough and emit a focused diff."""
        return runtime.compare_adapter_import_to_walkthrough(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_adapter_review_bundle(
        request: ExportAdapterReviewBundleRequest,
    ) -> dm.AdapterReviewBundle | DietaryErrorPayload:
        """Package adapter check and walkthrough-diff results into an auditable review handoff bundle."""
        return runtime.export_adapter_review_bundle(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_trade_risk_review_bundle(
        request: ExportTradeRiskReviewBundleRequest,
    ) -> dm.TradeRiskReviewBundle | DietaryErrorPayload:
        """Package a trade-risk screening result with explicit coverage semantics and reviewer prompts."""
        return runtime.export_trade_risk_review_bundle(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_contaminant_monitoring_interpretation_bundle(
        request: ExportContaminantMonitoringInterpretationBundleRequest,
    ) -> dm.ContaminantMonitoringInterpretationBundle | DietaryErrorPayload:
        """Package a contaminant monitoring check with governed evidence records and reviewer prompts."""
        return runtime.export_contaminant_monitoring_interpretation_bundle(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_contaminant_monitoring_signoff_packet(
        request: ExportContaminantMonitoringSignoffPacketRequest,
    ) -> dm.ContaminantMonitoringSignoffPacket | DietaryErrorPayload:
        """Export a reviewer-facing signoff packet for a governed contaminant monitoring interpretation bundle."""
        return runtime.export_contaminant_monitoring_signoff_packet(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_version_pinned_contaminant_monitoring_review_dossier(
        request: ExportVersionPinnedContaminantMonitoringReviewDossierRequest,
    ) -> dm.VersionPinnedContaminantMonitoringReviewDossier | DietaryErrorPayload:
        """Package contaminant monitoring interpretation and signoff outputs with pinned manifests and escalation overlays."""
        return runtime.export_version_pinned_contaminant_monitoring_review_dossier(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_version_pinned_adapter_review_dossier(
        request: ExportVersionPinnedAdapterReviewDossierRequest,
    ) -> dm.VersionPinnedAdapterReviewDossier | DietaryErrorPayload:
        """Package a review bundle with release hashes and pinned template and walkthrough fingerprints."""
        return runtime.export_version_pinned_adapter_review_dossier(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_version_pinned_trade_risk_review_dossier(
        request: ExportVersionPinnedTradeRiskReviewDossierRequest,
    ) -> dm.VersionPinnedTradeRiskReviewDossier | DietaryErrorPayload:
        """Package a trade-risk review bundle with pinned manifests, documentation, and release fingerprints."""
        return runtime.export_version_pinned_trade_risk_review_dossier(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_sanitised_public_review_dossier(
        request: ExportSanitisedPublicReviewDossierRequest,
    ) -> dm.SanitisedPublicReviewDossier | DietaryErrorPayload:
        """Derive a sanitised-public dossier with redaction records from an internal review dossier."""
        return runtime.export_sanitised_public_review_dossier(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_interoperability_preview(
        request: ExportInteroperabilityPreviewRequest,
    ) -> dm.InteroperabilityExportPreview | DietaryErrorPayload:
        """Build a validation-only OHT/IUCLID-aligned JSON export preview with unsupported-field reporting."""
        return runtime.export_interoperability_preview(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_assess_interoperability_preview_readiness(
        request: AssessInteroperabilityPreviewReadinessRequest,
    ) -> dm.InteroperabilityPreviewReadinessAssessment | DietaryErrorPayload:
        """Assess a staged interoperability preview against a governed export-readiness profile."""
        return runtime.assess_interoperability_preview_readiness(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_interoperability_remediation_bundle(
        request: ExportInteroperabilityRemediationBundleRequest,
    ) -> dm.InteroperabilityRemediationBundle | DietaryErrorPayload:
        """Export a machine-readable remediation bundle for a governed interoperability readiness outcome."""
        return runtime.export_interoperability_remediation_bundle(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_interoperability_signoff_packet(
        request: ExportInteroperabilitySignoffPacketRequest,
    ) -> dm.InteroperabilitySignoffPacket | DietaryErrorPayload:
        """Export a reviewer-facing signoff packet with action decisions and pinned rationale."""
        return runtime.export_interoperability_signoff_packet(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_assess_review_dossier_readiness(
        request: AssessReviewDossierReadinessRequest,
    ) -> dm.ReviewDossierReadinessAssessment | DietaryErrorPayload:
        """Assess a version-pinned review dossier against a governed regulatory readiness profile."""
        return runtime.assess_review_dossier_readiness(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_scientific_follow_up_queue_bundle(
        request: ExportScientificFollowUpQueueBundleRequest,
    ) -> dm.ScientificFollowUpQueueBundle | DietaryErrorPayload:
        """Export a machine-readable queue handoff for readiness-side scientific follow-up items."""
        return runtime.export_scientific_follow_up_queue_bundle(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_scientific_follow_up_review_board(
        request: ExportScientificFollowUpReviewBoardRequest,
    ) -> dm.ScientificFollowUpReviewBoard | DietaryErrorPayload:
        """Export a reviewer-operable routing board for readiness-side scientific follow-up items."""
        return runtime.export_scientific_follow_up_review_board(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_scientific_follow_up_owner_handoff_packet(
        request: ExportScientificFollowUpOwnerHandoffPacketRequest,
    ) -> dm.ScientificFollowUpOwnerHandoffPacket | DietaryErrorPayload:
        """Export an owner-scoped handoff packet for routed scientific follow-up items."""
        return runtime.export_scientific_follow_up_owner_handoff_packet(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_scientific_follow_up_owner_remediation_packet(
        request: ExportScientificFollowUpOwnerRemediationPacketRequest,
    ) -> dm.ScientificFollowUpOwnerRemediationPacket | DietaryErrorPayload:
        """Export an owner-scoped remediation packet for scientific follow-up handoff items."""
        return runtime.export_scientific_follow_up_owner_remediation_packet(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_scientific_follow_up_owner_signoff_packet(
        request: ExportScientificFollowUpOwnerSignoffPacketRequest,
    ) -> dm.ScientificFollowUpOwnerSignoffPacket | DietaryErrorPayload:
        """Export an owner-scoped signoff packet for scientific follow-up remediation items."""
        return runtime.export_scientific_follow_up_owner_signoff_packet(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_version_pinned_scientific_follow_up_owner_signoff_dossier(
        request: ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest,
    ) -> dm.VersionPinnedScientificFollowUpOwnerSignoffDossier | DietaryErrorPayload:
        """Export a version-pinned owner-lane signoff dossier for downstream audit and escalation tracking."""
        return runtime.export_version_pinned_scientific_follow_up_owner_signoff_dossier(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_lookup_reference_values(
        request: LookupReferenceValuesRequest,
    ) -> dm.ReferenceValueLookupResult | DietaryErrorPayload:
        """Return governed authority-specific reference-value records without flattening conflicts."""
        return runtime.lookup_reference_values(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_lookup_contaminant_legal_limits(
        request: LookupContaminantLegalLimitsRequest,
    ) -> dm.ContaminantLegalLimitLookupResult | DietaryErrorPayload:
        """Return governed jurisdiction-specific contaminant legal limits without borrowing from other authorities."""
        return runtime.lookup_contaminant_legal_limits(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_lookup_method_support(
        request: LookupMethodSupportRequest,
    ) -> dm.MethodSupportLookupResult | DietaryErrorPayload:
        """Return governed method-support posture for a contaminant family, jurisdiction, and authority."""
        return runtime.lookup_method_support(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_lookup_consumption_dataset_support(
        request: LookupConsumptionDatasetSupportRequest,
    ) -> dm.ConsumptionDatasetSupportLookupResult | DietaryErrorPayload:
        """Return governed dietary consumption-dataset support and allowed-use posture."""
        return runtime.lookup_consumption_dataset_support(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_lookup_reporting_profiles(
        request: LookupReportingProfilesRequest,
    ) -> dm.ReportingProfileLookupResult | DietaryErrorPayload:
        """Return governed reporting-profile conventions, including optional advisory extensions."""
        return runtime.lookup_reporting_profiles(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_lookup_occurrence_evidence(
        request: LookupOccurrenceEvidenceRequest,
    ) -> dm.OccurrenceEvidenceLookupResult | DietaryErrorPayload:
        """Return governed occurrence-evidence records for supported contaminant monitoring families."""
        return runtime.lookup_occurrence_evidence(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_lookup_analytical_method_evidence(
        request: LookupAnalyticalMethodEvidenceRequest,
    ) -> dm.AnalyticalMethodEvidenceLookupResult | DietaryErrorPayload:
        """Return governed analytical-method-evidence records for supported contaminant monitoring families."""
        return runtime.lookup_analytical_method_evidence(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_lookup_metals_occurrence(
        request: LookupMetalsOccurrenceRequest,
    ) -> dm.MetalsOccurrenceLookupResult | DietaryErrorPayload:
        """Return governed metals occurrence and monitoring support without implying a native exposure engine."""
        return runtime.lookup_metals_occurrence(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_lookup_metals_review_focus(
        request: LookupMetalsReviewFocusRequest,
    ) -> dm.MetalsReviewFocusLookupResult | DietaryErrorPayload:
        """Return governed metals commodity-focus review records without implying a native exposure engine."""
        return runtime.lookup_metals_review_focus(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_metals_monitoring_interpretation_bundle(
        request: ExportMetalsMonitoringInterpretationBundleRequest,
    ) -> dm.MetalsMonitoringInterpretationBundle | DietaryErrorPayload:
        """Package governed metals occurrence context and commodity-focus review prompts into one audit-ready bundle."""
        return runtime.export_metals_monitoring_interpretation_bundle(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_metals_monitoring_signoff_packet(
        request: ExportMetalsMonitoringSignoffPacketRequest,
    ) -> dm.MetalsMonitoringSignoffPacket | DietaryErrorPayload:
        """Export a reviewer-facing signoff packet for a governed metals monitoring interpretation bundle."""
        return runtime.export_metals_monitoring_signoff_packet(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_version_pinned_metals_monitoring_review_dossier(
        request: ExportVersionPinnedMetalsMonitoringReviewDossierRequest,
    ) -> dm.VersionPinnedMetalsMonitoringReviewDossier | DietaryErrorPayload:
        """Package a metals monitoring interpretation/signoff workflow with pinned manifests and escalation overlays."""
        return runtime.export_version_pinned_metals_monitoring_review_dossier(request)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_pbpk_oral_input(
        request: ExportPbpkOralInputRequest,
    ) -> dm.PbpkExternalImportBundle | DietaryErrorPayload:
        """Export a normalized oral dose bundle for PBPK consumers."""
        return export_pbpk_oral_input(request, runtime.provenance)

    @_dietary_tool(mcp)
    @_trace_tool
    def dietary_export_toxclaw_dietary_evidence_bundle(
        request: ExportToxclawDietaryEvidenceBundleRequest,
    ) -> dm.ToxclawDietaryEvidenceBundle | DietaryErrorPayload:
        """Export a ToxClaw-oriented dietary evidence bundle."""
        return export_toxclaw_dietary_evidence_bundle(request, runtime.provenance)
