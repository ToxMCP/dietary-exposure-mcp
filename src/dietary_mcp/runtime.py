from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from dietary_mcp.adapter_harness import (
    ExternalAdapterSummaryPayload,
    normalize_external_adapter_summary,
)
from dietary_mcp.adapter_checks import build_adapter_import_check_result
from dietary_mcp.contaminant_monitoring_checks import build_contaminant_monitoring_import_check_result
from dietary_mcp.contaminant_monitoring_review_dossier import (
    export_version_pinned_contaminant_monitoring_review_dossier,
)
from dietary_mcp.contaminant_monitoring_signoff import export_contaminant_monitoring_signoff_packet
from dietary_mcp.adapter_review import compare_adapter_import_to_walkthrough
from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.errors import DietaryRegistryError, DietaryValidationError
from dietary_mcp.integrations import (
    export_adapter_review_bundle,
    export_contaminant_monitoring_interpretation_bundle,
    export_metals_monitoring_interpretation_bundle,
)
from dietary_mcp.interoperability import export_interoperability_preview
from dietary_mcp.interoperability_readiness import assess_interoperability_preview_readiness
from dietary_mcp.interoperability_remediation import export_interoperability_remediation_bundle
from dietary_mcp.interoperability_signoff import export_interoperability_signoff_packet
from dietary_mcp.limits import (
    enforce_csv_byte_limit,
    enforce_probabilistic_draw_limit,
    enforce_probabilistic_iteration_limit,
    enforce_raw_survey_record_limit,
    enforce_residue_record_limit,
    enforce_target_jurisdiction_limit,
)
from dietary_mcp.metals_monitoring_review_dossier import (
    export_version_pinned_metals_monitoring_review_dossier,
)
from dietary_mcp.metals_monitoring_signoff import export_metals_monitoring_signoff_packet
from dietary_mcp.readiness import assess_review_dossier_readiness
from dietary_mcp.review_dossier import export_version_pinned_adapter_review_dossier
from dietary_mcp.scientific_follow_up_bundle import export_scientific_follow_up_queue_bundle
from dietary_mcp.scientific_follow_up_owner_handoff import export_scientific_follow_up_owner_handoff_packet
from dietary_mcp.scientific_follow_up_owner_remediation import (
    export_scientific_follow_up_owner_remediation_packet,
)
from dietary_mcp.scientific_follow_up_owner_signoff import (
    export_scientific_follow_up_owner_signoff_packet,
)
from dietary_mcp.scientific_follow_up_owner_signoff_dossier import (
    export_version_pinned_scientific_follow_up_owner_signoff_dossier,
)
from dietary_mcp.scientific_follow_up_review_board import export_scientific_follow_up_review_board
from dietary_mcp.trade_risk_review import (
    export_trade_risk_review_bundle,
    export_version_pinned_trade_risk_review_dossier,
)
from dietary_mcp.models import (
    AssessReviewDossierReadinessRequest,
    AssessInteroperabilityPreviewReadinessRequest,
    ApplyResidueEvidenceRequest,
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    BuildBoundedIntakeSummaryRequest,
    CheckAdapterImportRequest,
    CheckContaminantMonitoringImportRequest,
    CompareAdapterImportToWalkthroughRequest,
    CommodityConsumptionRecord,
    ConsumptionProfileSelectionResult,
    DietaryCommodityResidueRecord,
    DietaryConsumptionProfile,
    DietaryIntakeScenarioDefinition,
    DietaryResidueProfile,
    EvaluateGlobalTradeRiskRequest,
    GlobalTradeRiskReport,
    JurisdictionRiskProfile,
    ExportAdapterReviewBundleRequest,
    ExportTradeRiskReviewBundleRequest,
    ParseRawSurveyDatasetRequest,
    DietarySurveyDatasetRecord,
    SummarizeSurveyDistributionRequest,
    SurveyDistributionSummaryReport,
    BuildProbabilisticIntakeSummaryRequest,
    BuildUncertaintyIntakeAssessmentRequest,
    ProbabilisticIntakeSummary,
    ExportContaminantMonitoringInterpretationBundleRequest,
    ExportVersionPinnedContaminantMonitoringReviewDossierRequest,
    ExportVersionPinnedTradeRiskReviewDossierRequest,
    ExportContaminantMonitoringSignoffPacketRequest,
    ExportInteroperabilityPreviewRequest,
    ExportInteroperabilityRemediationBundleRequest,
    ExportInteroperabilitySignoffPacketRequest,
    ExportMetalsMonitoringInterpretationBundleRequest,
    ExportVersionPinnedMetalsMonitoringReviewDossierRequest,
    ExportMetalsMonitoringSignoffPacketRequest,
    ExportScientificFollowUpQueueBundleRequest,
    ExportScientificFollowUpOwnerHandoffPacketRequest,
    ExportScientificFollowUpOwnerRemediationPacketRequest,
    ExportScientificFollowUpOwnerSignoffPacketRequest,
    ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest,
    ExportScientificFollowUpReviewBoardRequest,
    ExportSanitisedPublicReviewDossierRequest,
    ExportVersionPinnedAdapterReviewDossierRequest,
    IntakeWindowSemantic,
    JurisdictionCoverageRecord,
    LookupContaminantLegalLimitsRequest,
    LookupConsumptionDatasetSupportRequest,
    LookupOccurrenceEvidenceRequest,
    LookupAnalyticalMethodEvidenceRequest,
    LookupReportingProfilesRequest,
    LookupMetalsOccurrenceRequest,
    LookupMetalsReviewFocusRequest,
    LookupMethodSupportRequest,
    LookupReferenceValuesRequest,
    LimitationNote,
    ModelFamily,
    PopulationContext,
    QualityFlag,
    ReferenceValueJurisdictionStatus,
    ReconcileResidueEvidenceRequest,
    ResidueEvidenceApplicationResult,
    ResidueEvidenceFitAssessment,
    ResidueEvidenceReconciliationResult,
    ResidueSourceType,
    ScenarioClass,
    SelectConsumptionProfileRequest,
    Severity,
    SourceClassification,
    SourceReference,
    TradeMrlCoverageStatus,
    UncertaintyIntakeAssessment,
)
from dietary_mcp.plugins import (
    AdapterStubDietaryPlugin,
    EfsaPrimoAdapterHarnessPlugin,
    EpaDeemAdapterHarnessPlugin,
    ReferenceDietaryPlugin,
)
from dietary_mcp.plugins.base import DietaryPlugin, PluginKey
from dietary_mcp.provenance import ProvenanceBuilder
from dietary_mcp.sanitisation import export_sanitised_public_review_dossier
from dietary_mcp.source_database import (
    lookup_consumption_dataset_support,
    lookup_contaminant_legal_limits,
    lookup_occurrence_evidence,
    lookup_analytical_method_evidence,
    lookup_reporting_profiles,
    lookup_metals_occurrence,
    lookup_metals_review_focus,
    lookup_method_support,
    lookup_reference_values,
)


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[PluginKey, DietaryPlugin] = {}

    def register(self, plugin: DietaryPlugin) -> None:
        if plugin.key in self._plugins:
            raise DietaryValidationError(
                code="duplicate_plugin_registration",
                message=f"Plugin already registered for {plugin.key}",
                suggestion="Register each workflow/model combination only once.",
            )
        self._plugins[plugin.key] = plugin

    def resolve(self, scenario_class: ScenarioClass, model_family: ModelFamily) -> DietaryPlugin:
        key = PluginKey(scenario_class=scenario_class, model_family=model_family)
        try:
            return self._plugins[key]
        except KeyError as exc:
            raise DietaryValidationError(
                code="unsupported_plugin_selection",
                message=f"No dietary plugin is registered for {scenario_class.value}/{model_family.value}.",
                suggestion="Choose a supported workflow or add a compatible adapter plugin.",
            ) from exc


_RUNTIME_CACHE: dict[Path, DietaryRuntime] = {}


def get_cached_dietary_runtime(repo_root: Path) -> DietaryRuntime:
    """Return a cached DietaryRuntime instance keyed by repo_root.

    This avoids repeated plugin registration and DefaultsRegistry construction
    across validation runners and test sessions.
    """
    key = repo_root.resolve()
    if key not in _RUNTIME_CACHE:
        _RUNTIME_CACHE[key] = DietaryRuntime(repo_root)
    return _RUNTIME_CACHE[key]


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    rank = (len(sorted_values) - 1) * (pct / 100.0)
    floor_index = int(rank)
    ceil_index = min(floor_index + 1, len(sorted_values) - 1)
    return sorted_values[floor_index] + (rank - floor_index) * (
        sorted_values[ceil_index] - sorted_values[floor_index]
    )


def _adjusted_residue_value(
    record: DietaryCommodityResidueRecord,
    *,
    bound: str = "point",
) -> float:
    if bound == "lower":
        concentration = (
            record.lower_bound_mg_per_kg
            if record.lower_bound_mg_per_kg is not None
            else record.residue_concentration_mg_per_kg
        )
    elif bound == "upper":
        concentration = (
            record.upper_bound_mg_per_kg
            if record.upper_bound_mg_per_kg is not None
            else record.residue_concentration_mg_per_kg
        )
    else:
        concentration = record.residue_concentration_mg_per_kg
    return concentration * record.processing_factor


def _summarize_exposure_distribution(exposures: list[float]) -> dict[str, float | int | None]:
    sorted_exposures = sorted(exposures)
    total_subjects = len(sorted_exposures)
    consumers = [value for value in sorted_exposures if value > 0.0]
    consumers_only_count = len(consumers)
    zero_intake_prevalence = (
        (total_subjects - consumers_only_count) / total_subjects if total_subjects > 0 else 0.0
    )

    summary: dict[str, float | int | None] = {
        "total_subjects": total_subjects,
        "consumers_only_count": consumers_only_count,
        "zero_intake_prevalence": zero_intake_prevalence,
        "mean": sum(sorted_exposures) / total_subjects if total_subjects > 0 else 0.0,
        "p95": _percentile(sorted_exposures, 95.0),
        "p99": _percentile(sorted_exposures, 99.0),
        "p999": _percentile(sorted_exposures, 99.9),
        "max": max(sorted_exposures) if sorted_exposures else 0.0,
        "consumers_only_mean": None,
        "consumers_only_p95": None,
        "consumers_only_p99": None,
        "consumers_only_p999": None,
    }
    if consumers:
        summary.update(
            {
                "consumers_only_mean": sum(consumers) / len(consumers),
                "consumers_only_p95": _percentile(consumers, 95.0),
                "consumers_only_p99": _percentile(consumers, 99.0),
                "consumers_only_p999": _percentile(consumers, 99.9),
            }
        )
    return summary


def _cohort_fingerprint(exposures: list[float]) -> str:
    payload = {
        "method": "cohort_bootstrap_v1",
        "subjectExposuresMgPerKgBwPerDay": exposures,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"cohort-{hashlib.sha256(encoded).hexdigest()[:12]}"


def _summarize_trade_mrl_support(
    defaults_registry: DefaultsRegistry,
    coverage_summaries: list[JurisdictionCoverageRecord],
) -> tuple[list[str], list[str]]:
    support_types: set[str] = set()
    commodity_codes: set[str] = set()
    for summary in coverage_summaries:
        if summary.enforcement_record_ids:
            support_types.add("enforcement_records")
        if summary.legal_authority_ids:
            support_types.add("legal_anchors")
        for record_id in summary.enforcement_record_ids:
            record = defaults_registry.get_mrl_enforcement_record(record_id)
            commodity_codes.add(record["commodityCode"])
    return sorted(support_types), sorted(commodity_codes)


def _determine_trade_mrl_coverage_status(
    requested_commodity_codes: set[str],
    coverage_summaries: list[JurisdictionCoverageRecord],
    curated_scope_commodity_codes: list[str],
) -> TradeMrlCoverageStatus:
    if not requested_commodity_codes:
        return TradeMrlCoverageStatus.UNSCOPED_LOOKUP
    if not coverage_summaries:
        return TradeMrlCoverageStatus.NO_CURATED_FAMILY_COVERAGE

    curated_scope = {code.lower() for code in curated_scope_commodity_codes}
    requested_scope = {code.lower() for code in requested_commodity_codes}
    if requested_scope.issubset(curated_scope):
        return TradeMrlCoverageStatus.ALL_REQUESTED_PAIRS_EXACTLY_CURATED
    if curated_scope:
        return TradeMrlCoverageStatus.REQUESTED_PAIR_OUTSIDE_CURATED_SCOPE
    if all(summary.coverage_level.value == "explicit_gap" for summary in coverage_summaries):
        return TradeMrlCoverageStatus.EXPLICIT_GAP
    if all(summary.coverage_level.value == "anchor_only" for summary in coverage_summaries):
        return TradeMrlCoverageStatus.ANCHOR_ONLY_FAMILY
    return TradeMrlCoverageStatus.FAMILY_CURATED_WITHOUT_MRL


def _build_trade_mrl_notes(
    *,
    jurisdiction: str,
    coverage_status: TradeMrlCoverageStatus,
    curated_support_types: list[str],
    curated_scope_commodity_codes: list[str],
) -> list[str]:
    notes: list[str] = []
    jurisdiction_label = jurisdiction.upper()
    if coverage_status == TradeMrlCoverageStatus.ALL_REQUESTED_PAIRS_EXACTLY_CURATED:
        notes.append(
            f"{jurisdiction_label} ships jurisdiction-specific MRL coverage for the full requested commodity pair set."
        )
    elif coverage_status == TradeMrlCoverageStatus.REQUESTED_PAIR_OUTSIDE_CURATED_SCOPE:
        scope_text = ", ".join(curated_scope_commodity_codes) if curated_scope_commodity_codes else "none"
        notes.append(
            f"{jurisdiction_label} ships curated MRLs for this substance, but the requested commodity set extends beyond the current shipped scope ({scope_text})."
        )
    elif coverage_status == TradeMrlCoverageStatus.FAMILY_CURATED_WITHOUT_MRL:
        notes.append(
            f"{jurisdiction_label} is curated for this substance/family, but the repo does not currently ship a jurisdiction-specific MRL layer for the requested pair set."
        )
    elif coverage_status == TradeMrlCoverageStatus.ANCHOR_ONLY_FAMILY:
        notes.append(
            f"{jurisdiction_label} currently exposes an official family anchor for this substance/family, but no curated jurisdiction-specific MRL layer."
        )
    elif coverage_status == TradeMrlCoverageStatus.EXPLICIT_GAP:
        notes.append(
            f"{jurisdiction_label} is tracked as an explicit MRL coverage gap for this substance/family."
        )
    elif coverage_status == TradeMrlCoverageStatus.NO_CURATED_FAMILY_COVERAGE:
        notes.append(
            f"No curated trade-risk MRL coverage record is currently shipped for this substance/family in {jurisdiction_label}."
        )

    if curated_support_types:
        notes.append(
            f"{jurisdiction_label} MRL support types attached to this lane: {', '.join(curated_support_types)}."
        )
    return notes


def _build_trade_reference_notes(
    *,
    jurisdiction: str,
    reference_status: ReferenceValueJurisdictionStatus,
    curated_support_types: list[str],
) -> list[str]:
    notes: list[str] = []
    jurisdiction_label = jurisdiction.upper()
    if reference_status == ReferenceValueJurisdictionStatus.EXACT_JURISDICTION_VALUE_PRESENT:
        notes.append(f"{jurisdiction_label} ships a jurisdiction-specific reference-value record for this lane.")
    elif reference_status == ReferenceValueJurisdictionStatus.JURISDICTION_VALUE_EXISTS_BUT_FILTER_UNMATCHED:
        notes.append(
            f"{jurisdiction_label} has jurisdiction-specific reference values for this lane, but the current filters did not select one."
        )
    elif reference_status == ReferenceValueJurisdictionStatus.FAMILY_CURATED_WITHOUT_REFERENCE_VALUE:
        notes.append(
            f"{jurisdiction_label} has governed curated support for this substance/family, but no jurisdiction-specific reference value is shipped."
        )
    elif reference_status == ReferenceValueJurisdictionStatus.ANCHOR_ONLY_FAMILY:
        notes.append(
            f"{jurisdiction_label} currently exposes only an official family anchor for the reference-value side of this lane."
        )
    elif reference_status == ReferenceValueJurisdictionStatus.EXPLICIT_GAP:
        notes.append(
            f"{jurisdiction_label} is tracked as an explicit reference-value coverage gap for this substance/family."
        )
    elif reference_status == ReferenceValueJurisdictionStatus.NO_CURATED_FAMILY_COVERAGE:
        notes.append(
            f"No curated reference-value coverage record is currently shipped for this substance/family in {jurisdiction_label}."
        )

    if curated_support_types:
        notes.append(
            f"{jurisdiction_label} reference-value support types attached to this lane: {', '.join(curated_support_types)}."
        )
    return notes


def _build_global_trade_report_notes(profiles: list[JurisdictionRiskProfile]) -> list[str]:
    notes = [
        "Trade-risk screening preserves jurisdiction separation and does not borrow MRLs or reference values across authorities.",
        "A pass status only means all applicable governed limits that were actually found were met for that jurisdiction; inspect MRL and reference-value coverage statuses before treating the lane as complete.",
    ]
    coverage_limited = [profile.jurisdiction.upper() for profile in profiles if profile.trade_status == "inconclusive_no_limit"]
    if coverage_limited:
        notes.append(
            "Inconclusive jurisdictions remain active review signals, not implicit passes: "
            + ", ".join(sorted(coverage_limited))
            + "."
        )
    return notes


class DietaryRuntime:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.defaults = DefaultsRegistry(repo_root)
        self.provenance = ProvenanceBuilder(self.defaults)
        self.plugins = PluginRegistry()
        for scenario_class in (
            ScenarioClass.POINT_ESTIMATE,
            ScenarioClass.BOUNDED_ACUTE,
            ScenarioClass.BOUNDED_CHRONIC,
        ):
            self.plugins.register(ReferenceDietaryPlugin(self.defaults, self.provenance, scenario_class))
            self.plugins.register(AdapterStubDietaryPlugin(self.defaults, self.provenance, scenario_class))
            self.plugins.register(EfsaPrimoAdapterHarnessPlugin(self.defaults, self.provenance, scenario_class))
            self.plugins.register(EpaDeemAdapterHarnessPlugin(self.defaults, self.provenance, scenario_class))

    def _subject_exposures_from_dataset(
        self,
        dataset: DietarySurveyDatasetRecord,
        residue_profile: DietaryResidueProfile,
    ) -> dict[str, float]:
        residue_map = {
            record.commodity.commodity_code: record
            for record in residue_profile.records
        }
        subject_weight_by_id: dict[str, float] = {}
        subject_mass_intake_by_id: dict[str, float] = {}

        for record in dataset.records:
            subject_weight_by_id.setdefault(record.subject_id, record.body_weight_kg)
            subject_mass_intake_by_id.setdefault(record.subject_id, 0.0)
            residue_record = residue_map.get(record.commodity_code)
            if residue_record is None:
                continue
            subject_mass_intake_by_id[record.subject_id] += (
                record.consumption_kg_per_day * _adjusted_residue_value(residue_record)
            )

        return {
            subject_id: (
                subject_mass_intake_by_id.get(subject_id, 0.0) / subject_weight
                if subject_weight > 0.0
                else 0.0
            )
            for subject_id, subject_weight in subject_weight_by_id.items()
        }

    def _resolve_trade_substance_key(self, chemical_identity: dict[str, str]) -> tuple[str | None, list[QualityFlag]]:
        preferred_name = chemical_identity.get("preferredName", "").strip().lower()
        if not preferred_name:
            return (
                None,
                [
                    QualityFlag(
                        code="invalid_trade_risk_request",
                        severity=Severity.ERROR,
                        message="Trade-risk evaluation requires a non-empty `preferredName` chemical identity.",
                    )
                ],
            )

        resolved = self.defaults.resolve_substance_key(preferred_name)
        if resolved is not None:
            return resolved, []

        has_reference_value = any(
            item["substanceKey"].strip().lower() == preferred_name
            for item in self.defaults.list_reference_value_records()
        )
        has_mrl = any(
            item["substanceKey"].strip().lower() == preferred_name
            for item in self.defaults.list_mrl_enforcement_records()
        )
        if has_reference_value or has_mrl:
            return preferred_name, []

        return (
            None,
            [
                QualityFlag(
                    code="unresolvable_trade_risk_chemical_identity",
                    severity=Severity.ERROR,
                    message=(
                        f"Trade-risk evaluation could not resolve governed substance identity for "
                        f"`{chemical_identity.get('preferredName', '')}`."
                    ),
                )
            ],
        )

    def build_residue_profile(self, request: BuildDietaryResidueProfileRequest) -> DietaryResidueProfile:
        enforce_residue_record_limit(len(request.residue_records))
        records = []
        quality_flags = []
        limitations = []
        source_references = []
        for item in request.residue_records:
            resolution = self.defaults.resolve_commodity(item.commodity_code)
            applied_processing_factor = item.processing_factor
            processing_factor_source_classification = SourceClassification.USER_INPUT
            processing_factor_source_reference = item.source_reference
            if applied_processing_factor is None:
                applied_processing_factor, processing_factor_source_reference = self.defaults.default_processing_factor(
                    item.commodity_code
                )
                processing_factor_source_classification = SourceClassification.CURATED_DEFAULT
                limitations.append(
                    LimitationNote(
                        code="default_processing_factor_applied",
                        message=f"Default processing factor was applied to {resolution.commodity.canonical_name}.",
                    )
                )

            quality_flags.extend(resolution.quality_flags)
            if item.source_reference:
                source_references.append(item.source_reference)
            if resolution.commodity.source_reference:
                source_references.append(resolution.commodity.source_reference)
            if processing_factor_source_reference:
                source_references.append(processing_factor_source_reference)

            substance_name = request.chemical_identity.get("preferredName", "").lower()
            resolved_substance = self.defaults.resolve_substance_key(substance_name) or substance_name
            adjusted_residue = item.residue_concentration_mg_per_kg * applied_processing_factor
            for mrl_record in self.defaults.list_mrl_records_by_substance_commodity(
                resolved_substance, resolution.commodity.commodity_code
            ):
                if adjusted_residue > mrl_record["mrlValueMgPerKg"]:
                    quality_flags.append(
                        QualityFlag(
                            code="mrl_violation",
                            severity=Severity.ERROR,
                            message=(
                                f"Effective residue concentration ({adjusted_residue} mg/kg) for "
                                f"{resolution.commodity.commodity_code} exceeds governed MRL "
                                f"({mrl_record['mrlValueMgPerKg']} mg/kg) from {mrl_record['authority']}."
                            ),
                        )
                    )

            records.append(
                DietaryCommodityResidueRecord(
                    commodity=resolution.commodity,
                    residue_concentration_mg_per_kg=item.residue_concentration_mg_per_kg,
                    lower_bound_mg_per_kg=item.lower_bound_mg_per_kg,
                    upper_bound_mg_per_kg=item.upper_bound_mg_per_kg,
                    residue_unit=item.residue_unit,
                    source_type=item.source_type,
                    processing_factor=applied_processing_factor,
                    processing_factor_source_classification=processing_factor_source_classification,
                    processing_factor_source_reference=processing_factor_source_reference,
                    region_id=item.region_id or request.region_id,
                    time_context=item.time_context,
                    review_status=item.review_status,
                    source_reference=item.source_reference,
                    provenance=self.provenance.bundle(
                        [ref for ref in [item.source_reference, resolution.commodity.source_reference] if ref]
                    ),
                    quality_flags=resolution.quality_flags,
                    limitations=[],
                )
            )

        return DietaryResidueProfile(
            chemical_identity=request.chemical_identity,
            region_id=request.region_id,
            records=records,
            provenance=self.provenance.bundle(source_references),
            quality_flags=quality_flags,
            limitations=limitations,
        )

    def parse_raw_survey_dataset(self, request: ParseRawSurveyDatasetRequest) -> DietarySurveyDatasetRecord:
        enforce_raw_survey_record_limit(len(request.raw_records))
        records = []
        quality_flags = []
        limitations = [
            LimitationNote(
                code="raw_survey_ingestion",
                message=(
                    "Raw survey datasets support governed distribution summaries and cohort-bootstrap review support, "
                    "but remain a reviewer-controlled population-exposure workflow in v0.1."
                ),
            )
        ]
        seen_commodities = set()
        dropped_record_count = 0
        unmapped_commodity_codes: set[str] = set()
        body_weight_by_subject: dict[str, float] = {}
        body_weight_conflict_subject_ids: set[str] = set()
        for raw_record in request.raw_records:
            try:
                resolution = self.defaults.resolve_commodity(raw_record.commodity_code)
                seen_commodities.add(resolution.commodity.commodity_code)
                first_body_weight = body_weight_by_subject.setdefault(raw_record.subject_id, raw_record.body_weight_kg)
                if abs(first_body_weight - raw_record.body_weight_kg) > 1e-9:
                    body_weight_conflict_subject_ids.add(raw_record.subject_id)
                record = raw_record.model_copy(update={"commodity_code": resolution.commodity.commodity_code})
                records.append(record)
            except DietaryRegistryError:
                dropped_record_count += 1
                unmapped_commodity_codes.add(raw_record.commodity_code)
                quality_flags.append(
                    QualityFlag(
                        code="unknown_survey_commodity",
                        severity=Severity.WARNING,
                        message=f"Survey record for {raw_record.subject_id} referenced unknown commodity {raw_record.commodity_code}.",
                    )
                )

        if not records:
            quality_flags.append(
                QualityFlag(
                    code="empty_survey_dataset",
                    severity=Severity.ERROR,
                    message="No valid commodity mappings were found in the raw survey dataset.",
                )
            )

        total_raw_records = len(request.raw_records)
        data_loss_fraction = dropped_record_count / total_raw_records if total_raw_records else 0.0
        if dropped_record_count:
            severity = Severity.ERROR if data_loss_fraction > 0.10 else Severity.WARNING
            quality_flags.append(
                QualityFlag(
                    code="survey_data_loss",
                    severity=severity,
                    message=(
                        f"{dropped_record_count} of {total_raw_records} survey rows were dropped during "
                        f"commodity normalization ({data_loss_fraction:.1%} data loss)."
                    ),
                )
            )
        if body_weight_conflict_subject_ids:
            quality_flags.append(
                QualityFlag(
                    code="subject_body_weight_conflict",
                    severity=Severity.WARNING,
                    message=(
                        "At least one subject carried conflicting body-weight values across survey rows: "
                        f"{sorted(body_weight_conflict_subject_ids)}."
                    ),
                )
            )
            limitations.append(
                LimitationNote(
                    code="subject_body_weight_conflict",
                    message=(
                        "Conflicting body-weight values were detected for one or more subjects; exposure summaries "
                        "use the first observed body weight per subject to avoid row-to-row denominator drift."
                    ),
                )
            )

        return DietarySurveyDatasetRecord(
            dataset_id=request.dataset_id,
            region_id=request.region_id,
            population_group=request.population_group,
            records=records,
            dropped_record_count=dropped_record_count,
            data_loss_fraction=data_loss_fraction,
            unmapped_commodity_codes=sorted(unmapped_commodity_codes),
            body_weight_conflict_subject_ids=sorted(body_weight_conflict_subject_ids),
            quality_flags=quality_flags,
            limitations=limitations,
        )

    def summarize_survey_distribution(
        self, request: SummarizeSurveyDistributionRequest
    ) -> SurveyDistributionSummaryReport:
        dataset = request.dataset
        residue_profile = request.residue_profile
        subject_exposures = self._subject_exposures_from_dataset(dataset, residue_profile)
        summary = _summarize_exposure_distribution(list(subject_exposures.values()))

        limitations = dataset.limitations + residue_profile.limitations + [
            LimitationNote(
                code="distribution_summary",
                message=(
                    "Distribution summary applies governed residue adjustment and percentile interpolation to "
                    "subject-level exposures, but is not a parametric Monte Carlo engine."
                ),
            )
        ]

        return SurveyDistributionSummaryReport(
            dataset_id=dataset.dataset_id,
            population_group=dataset.population_group,
            chemical_identity=residue_profile.chemical_identity,
            total_subjects=int(summary["total_subjects"]),
            consumers_only_count=int(summary["consumers_only_count"]),
            zero_intake_prevalence=float(summary["zero_intake_prevalence"]),
            mean_intake_mg_per_kg_bw_per_day=float(summary["mean"]),
            percentile_95_mg_per_kg_bw_per_day=float(summary["p95"]),
            percentile_99_mg_per_kg_bw_per_day=float(summary["p99"]),
            percentile_99_9_mg_per_kg_bw_per_day=float(summary["p999"]),
            max_mg_per_kg_bw_per_day=float(summary["max"]),
            consumers_only_mean_mg_per_kg_bw_per_day=summary["consumers_only_mean"],
            consumers_only_percentile_95_mg_per_kg_bw_per_day=summary["consumers_only_p95"],
            consumers_only_percentile_99_mg_per_kg_bw_per_day=summary["consumers_only_p99"],
            consumers_only_percentile_99_9_mg_per_kg_bw_per_day=summary["consumers_only_p999"],
            quality_flags=dataset.quality_flags + residue_profile.quality_flags,
            limitations=limitations,
        )

    def build_probabilistic_intake_summary(
        self, request: BuildProbabilisticIntakeSummaryRequest
    ) -> ProbabilisticIntakeSummary:
        enforce_probabilistic_iteration_limit(request.iteration_count)
        dataset = request.dataset
        residue_profile = request.residue_profile
        rng = random.Random(request.random_seed)

        subject_exposures = self._subject_exposures_from_dataset(dataset, residue_profile)
        exposures = sorted(subject_exposures.values())
        cohort_summary = _summarize_exposure_distribution(exposures)
        total_subjects = int(cohort_summary["total_subjects"])
        consumers_only_count = int(cohort_summary["consumers_only_count"])
        zero_intake_prevalence = float(cohort_summary["zero_intake_prevalence"])

        cohort_fingerprint = _cohort_fingerprint(exposures)
        
        simulated_exposures = []
        
        if total_subjects == 0:
            quality_flags = dataset.quality_flags + residue_profile.quality_flags + [
                QualityFlag(
                    code="empty_dataset",
                    severity=Severity.ERROR,
                    message="Cannot run probabilistic simulation on an empty dataset."
                )
            ]
            return ProbabilisticIntakeSummary(
                dataset_id=dataset.dataset_id,
                population_group=dataset.population_group,
                chemical_identity=residue_profile.chemical_identity,
                iteration_count=request.iteration_count,
                random_seed=request.random_seed,
                cohort_fingerprint=cohort_fingerprint,
                total_subjects=total_subjects,
                consumers_only_count=consumers_only_count,
                zero_intake_prevalence=zero_intake_prevalence,
                mean_intake_mg_per_kg_bw_per_day=0.0,
                percentile_95_mg_per_kg_bw_per_day=0.0,
                percentile_99_mg_per_kg_bw_per_day=0.0,
                percentile_99_9_mg_per_kg_bw_per_day=0.0,
                max_mg_per_kg_bw_per_day=0.0,
                quality_flags=quality_flags,
                limitations=dataset.limitations + residue_profile.limitations,
                provenance=self.provenance.bundle([])
            )

        enforce_probabilistic_draw_limit(request.iteration_count, total_subjects)

        # Cohort bootstrap resampling: each iteration samples a full cohort with replacement.
        for _ in range(request.iteration_count):
            simulated_exposures.extend(
                rng.choice(exposures)
                for _ in range(total_subjects)
            )

        simulated_exposures.sort()
        bootstrap_summary = _summarize_exposure_distribution(simulated_exposures)

        limitations = dataset.limitations + residue_profile.limitations + [
            LimitationNote(
                code="probabilistic_simulation_support",
                message=(
                    "Cohort bootstrap resampling re-draws the observed subject-exposure distribution with "
                    "replacement and reports pooled population and consumer-only summaries. This is review support, "
                    "not a parametric Monte Carlo engine or final regulatory acceptance path."
                ),
            )
        ]

        source_references = [
            SourceReference(
                source_id=f"dietary.dataset.{dataset.dataset_id}",
                title=f"Raw Survey Dataset: {dataset.dataset_id}",
                url=None,
            )
        ]
        if residue_profile.provenance and residue_profile.provenance.source_references:
            source_references.extend(residue_profile.provenance.source_references)

        return ProbabilisticIntakeSummary(
            dataset_id=dataset.dataset_id,
            population_group=dataset.population_group,
            chemical_identity=residue_profile.chemical_identity,
            iteration_count=request.iteration_count,
            random_seed=request.random_seed,
            cohort_fingerprint=cohort_fingerprint,
            total_subjects=total_subjects,
            consumers_only_count=consumers_only_count,
            zero_intake_prevalence=zero_intake_prevalence,
            mean_intake_mg_per_kg_bw_per_day=float(bootstrap_summary["mean"]),
            percentile_95_mg_per_kg_bw_per_day=float(bootstrap_summary["p95"]),
            percentile_99_mg_per_kg_bw_per_day=float(bootstrap_summary["p99"]),
            percentile_99_9_mg_per_kg_bw_per_day=float(bootstrap_summary["p999"]),
            max_mg_per_kg_bw_per_day=float(bootstrap_summary["max"]),
            consumers_only_mean_mg_per_kg_bw_per_day=bootstrap_summary["consumers_only_mean"],
            consumers_only_percentile_95_mg_per_kg_bw_per_day=bootstrap_summary["consumers_only_p95"],
            consumers_only_percentile_99_mg_per_kg_bw_per_day=bootstrap_summary["consumers_only_p99"],
            consumers_only_percentile_99_9_mg_per_kg_bw_per_day=bootstrap_summary["consumers_only_p999"],
            quality_flags=dataset.quality_flags + residue_profile.quality_flags,
            limitations=limitations,
            provenance=self.provenance.bundle(source_references)
        )

    def build_uncertainty_intake_assessment(
        self,
        request: BuildUncertaintyIntakeAssessmentRequest,
    ) -> UncertaintyIntakeAssessment:
        from dietary_mcp.uncertainty import build_uncertainty_intake_assessment

        return build_uncertainty_intake_assessment(self, request)

    def evaluate_global_trade_risk(
        self,
        request: EvaluateGlobalTradeRiskRequest,
    ) -> GlobalTradeRiskReport:
        enforce_residue_record_limit(len(request.residue_records))
        enforce_target_jurisdiction_limit(len(request.target_jurisdictions))
        resolved_substance, request_quality_flags = self._resolve_trade_substance_key(
            request.chemical_identity
        )
        profiles = []
        global_quality_flags = list(request_quality_flags)
        for jurisdiction in request.target_jurisdictions:
            mrl_violations = []
            profile_quality_flags: list[QualityFlag] = []
            applicable_limit_count = 0
            missing_limit_records: list[str] = []
            requested_commodity_codes: set[str] = set()

            if resolved_substance is None:
                profiles.append(
                    JurisdictionRiskProfile(
                        jurisdiction=jurisdiction,
                        mrl_violations=[],
                        applicable_reference_values=[],
                        trade_status="invalid_request",
                        status_reason=(
                            "Chemical identity is missing or could not be resolved to a governed substance key."
                        ),
                        quality_flags=request_quality_flags,
                        notes=[
                            "Trade-risk evaluation stopped before jurisdiction-specific screening because the request did not resolve to a governed substance key."
                        ],
                    )
                )
                continue

            for record in request.residue_records:
                try:
                    resolved_commodity_code = self.defaults.resolve_commodity(record.commodity_code).commodity.commodity_code
                except DietaryRegistryError:
                    resolved_commodity_code = record.commodity_code
                requested_commodity_codes.add(resolved_commodity_code.lower())
                try:
                    applied_processing_factor = (
                        record.processing_factor
                        if record.processing_factor is not None
                        else self.defaults.default_processing_factor(record.commodity_code)[0]
                    )
                except DietaryRegistryError:
                    applied_processing_factor = 1.0
                    profile_quality_flags.append(
                        QualityFlag(
                            code="trade_risk_unknown_commodity",
                            severity=Severity.WARNING,
                            message=(
                                f"Trade-risk evaluation could not resolve commodity `{record.commodity_code}` "
                                "for governed processing-factor lookup; using the submitted concentration as-is."
                            ),
                        )
                    )

                effective_residue = record.residue_concentration_mg_per_kg * applied_processing_factor
                mrl_record = self.defaults.get_mrl_record(resolved_substance, resolved_commodity_code, jurisdiction)
                if mrl_record is not None:
                    applicable_limit_count += 1
                    if effective_residue > mrl_record["mrlValueMgPerKg"]:
                        mrl_violations.append(
                            QualityFlag(
                                code="trade_mrl_violation",
                                severity=Severity.ERROR,
                                message=(
                                    f"Effective residue ({effective_residue} mg/kg) on {record.commodity_code} "
                                    f"violates {jurisdiction.upper()} MRL ({mrl_record['mrlValueMgPerKg']} mg/kg)."
                                ),
                            )
                        )
                else:
                    missing_limit_records.append(record.commodity_code)

            ref_result = self.lookup_reference_values(
                LookupReferenceValuesRequest(
                    substance_key=resolved_substance,
                    contaminant_family=request.contaminant_family,
                    jurisdiction=jurisdiction,
                )
            )
            profile_quality_flags.extend(ref_result.quality_flags)
            mrl_curated_support_types, mrl_curated_scope_commodity_codes = _summarize_trade_mrl_support(
                self.defaults,
                ref_result.coverage_summaries,
            )
            mrl_coverage_status = _determine_trade_mrl_coverage_status(
                requested_commodity_codes,
                ref_result.coverage_summaries,
                mrl_curated_scope_commodity_codes,
            )

            if mrl_violations:
                trade_status = "fail"
                status_reason = "At least one effective residue concentration exceeds an applicable governed limit."
            elif missing_limit_records:
                trade_status = "inconclusive_no_limit"
                if mrl_coverage_status == TradeMrlCoverageStatus.REQUESTED_PAIR_OUTSIDE_CURATED_SCOPE:
                    status_reason = (
                        "One or more requested residue commodities fall outside the curated jurisdiction-specific "
                        "MRL scope."
                    )
                elif mrl_coverage_status == TradeMrlCoverageStatus.FAMILY_CURATED_WITHOUT_MRL:
                    status_reason = (
                        "The jurisdiction is curated for this substance/family, but no jurisdiction-specific MRL "
                        "layer is shipped for the requested pair set."
                    )
                elif mrl_coverage_status == TradeMrlCoverageStatus.ANCHOR_ONLY_FAMILY:
                    status_reason = (
                        "Only an official family anchor is available for this jurisdiction; no curated "
                        "jurisdiction-specific MRL layer was shipped for the requested pair set."
                    )
                elif mrl_coverage_status == TradeMrlCoverageStatus.EXPLICIT_GAP:
                    status_reason = (
                        "The requested jurisdiction is tracked as an explicit trade-risk MRL coverage gap for "
                        "this substance/family."
                    )
                elif mrl_coverage_status == TradeMrlCoverageStatus.NO_CURATED_FAMILY_COVERAGE:
                    status_reason = (
                        "No curated trade-risk MRL coverage is currently shipped for this substance/family "
                        "in the requested jurisdiction."
                    )
                else:
                    status_reason = (
                        "One or more residue records do not have an applicable governed MRL in the requested "
                        "jurisdiction."
                    )
                profile_quality_flags.append(
                    QualityFlag(
                        code="missing_trade_limit",
                        severity=Severity.WARNING,
                        message=(
                            f"No applicable governed MRL was found for {sorted(set(missing_limit_records))} in "
                            f"{jurisdiction.upper()}."
                        ),
                    )
                )
                profile_quality_flags.append(
                    QualityFlag(
                        code="no_curated_mrl_for_requested_pair",
                        severity=Severity.WARNING,
                        message=(
                            "No curated jurisdiction-specific MRL was available for one or more requested "
                            f"substance/commodity pairs in {jurisdiction.upper()}."
                        ),
                    )
                )
                if mrl_coverage_status in {
                    TradeMrlCoverageStatus.EXPLICIT_GAP,
                    TradeMrlCoverageStatus.NO_CURATED_FAMILY_COVERAGE,
                }:
                    profile_quality_flags.append(
                        QualityFlag(
                            code="coverage_gap",
                            severity=Severity.WARNING,
                            message=(
                                f"Trade-risk coverage remains incomplete for at least one requested residue record in "
                                f"{jurisdiction.upper()}."
                            ),
                        )
                    )
                elif mrl_coverage_status == TradeMrlCoverageStatus.REQUESTED_PAIR_OUTSIDE_CURATED_SCOPE:
                    scope_text = ", ".join(mrl_curated_scope_commodity_codes) if mrl_curated_scope_commodity_codes else None
                    profile_quality_flags.append(
                        QualityFlag(
                            code="requested_trade_pair_outside_curated_scope",
                            severity=Severity.WARNING,
                            message=(
                                f"{jurisdiction.upper()} ships curated MRLs for `{resolved_substance}`, but one or more "
                                "requested commodities fall outside the shipped scope."
                                + (f" Curated scope includes: {scope_text}." if scope_text else "")
                            ),
                        )
                    )
                elif mrl_coverage_status == TradeMrlCoverageStatus.FAMILY_CURATED_WITHOUT_MRL:
                    profile_quality_flags.append(
                        QualityFlag(
                            code="family_curated_without_trade_mrl",
                            severity=Severity.WARNING,
                            message=(
                                f"{jurisdiction.upper()} has governed curated support for `{resolved_substance}`, but "
                                "the repo does not yet ship a jurisdiction-specific MRL layer for this pair set."
                            ),
                        )
                    )
                elif mrl_coverage_status == TradeMrlCoverageStatus.ANCHOR_ONLY_FAMILY:
                    profile_quality_flags.append(
                        QualityFlag(
                            code="anchor_only_family_without_trade_mrl",
                            severity=Severity.WARNING,
                            message=(
                                f"{jurisdiction.upper()} has an official family anchor for `{resolved_substance}`, "
                                "but no curated jurisdiction-specific MRL layer is shipped for this pair set."
                            ),
                        )
                    )
            elif applicable_limit_count == 0:
                trade_status = "inconclusive_no_limit"
                status_reason = "No applicable governed MRLs were available for the requested jurisdiction."
                profile_quality_flags.append(
                    QualityFlag(
                        code="missing_trade_limit",
                        severity=Severity.WARNING,
                        message=f"No applicable governed MRLs were found in {jurisdiction.upper()}.",
                    )
                )
                profile_quality_flags.append(
                    QualityFlag(
                        code="no_curated_mrl_for_requested_pair",
                        severity=Severity.WARNING,
                        message=(
                            f"No curated jurisdiction-specific MRLs were available for the requested pair set in "
                            f"{jurisdiction.upper()}."
                        ),
                    )
                )
                if mrl_coverage_status in {
                    TradeMrlCoverageStatus.EXPLICIT_GAP,
                    TradeMrlCoverageStatus.NO_CURATED_FAMILY_COVERAGE,
                }:
                    profile_quality_flags.append(
                        QualityFlag(
                            code="coverage_gap",
                            severity=Severity.WARNING,
                            message=(
                                f"Trade-risk evaluation for {jurisdiction.upper()} is coverage-limited because no curated "
                                "MRL matched the requested substance/commodity pairs."
                            ),
                        )
                    )
                elif mrl_coverage_status == TradeMrlCoverageStatus.FAMILY_CURATED_WITHOUT_MRL:
                    profile_quality_flags.append(
                        QualityFlag(
                            code="family_curated_without_trade_mrl",
                            severity=Severity.WARNING,
                            message=(
                                f"{jurisdiction.upper()} has governed curated support for `{resolved_substance}`, but "
                                "the repo does not yet ship a jurisdiction-specific MRL layer."
                            ),
                        )
                    )
                elif mrl_coverage_status == TradeMrlCoverageStatus.ANCHOR_ONLY_FAMILY:
                    profile_quality_flags.append(
                        QualityFlag(
                            code="anchor_only_family_without_trade_mrl",
                            severity=Severity.WARNING,
                            message=(
                                f"{jurisdiction.upper()} has an official family anchor for `{resolved_substance}`, "
                                "but no curated jurisdiction-specific MRL layer is shipped."
                            ),
                        )
                    )
            else:
                trade_status = "pass"
                status_reason = "All residue records were below the applicable governed limits that were found."

            profile_notes = _build_trade_mrl_notes(
                jurisdiction=jurisdiction,
                coverage_status=mrl_coverage_status,
                curated_support_types=mrl_curated_support_types,
                curated_scope_commodity_codes=mrl_curated_scope_commodity_codes,
            ) + _build_trade_reference_notes(
                jurisdiction=jurisdiction,
                reference_status=ref_result.requested_jurisdiction_status,
                curated_support_types=ref_result.curated_support_types,
            )

            profiles.append(
                JurisdictionRiskProfile(
                    jurisdiction=jurisdiction,
                    mrl_violations=mrl_violations,
                    applicable_reference_values=ref_result.matched_records,
                    trade_status=trade_status,
                    status_reason=status_reason,
                    mrl_coverage_status=mrl_coverage_status,
                    mrl_curated_support_types=mrl_curated_support_types,
                    mrl_curated_scope_commodity_codes=mrl_curated_scope_commodity_codes,
                    reference_value_jurisdiction_status=ref_result.requested_jurisdiction_status,
                    reference_value_curated_support_types=ref_result.curated_support_types,
                    coverage_summaries=ref_result.coverage_summaries,
                    quality_flags=profile_quality_flags,
                    notes=profile_notes,
                )
            )
            global_quality_flags.extend(profile_quality_flags)

        return GlobalTradeRiskReport(
            chemical_identity=request.chemical_identity,
            resolved_substance_key=resolved_substance,
            jurisdiction_profiles=profiles,
            quality_flags=global_quality_flags,
            notes=_build_global_trade_report_notes(profiles),
        )

    def select_consumption_profile(
        self,
        request: SelectConsumptionProfileRequest,
    ) -> ConsumptionProfileSelectionResult:
        profile_record = self.defaults.select_consumption_profile_record(
            region_id=request.region_id,
            population_group=request.population_group,
            intake_window=request.intake_window,
            preferred_profile_id=request.preferred_profile_id,
        )
        source_reference = self.defaults.profile_source_reference(profile_record)
        commodity_consumption = []
        matched = []
        missing = []
        
        # Expand recipes
        recipes_lookup = {
            r["compositeCommodityCode"]: r["components"]
            for r in self.defaults.list_composition_recipes_records()
        }

        expanded_items = []
        for item in profile_record["commodityConsumption"]:
            comp_code = item["commodityCode"]
            if comp_code in recipes_lookup:
                for comp in recipes_lookup[comp_code]:
                    expanded_items.append({
                        "commodityCode": comp["commodityCode"],
                        "acuteKgPerDay": (item.get("acuteKgPerDay") or 0.0) * comp["proportion"] if item.get("acuteKgPerDay") is not None else None,
                        "chronicKgPerDay": (item.get("chronicKgPerDay") or 0.0) * comp["proportion"] if item.get("chronicKgPerDay") is not None else None,
                    })
            else:
                expanded_items.append(item)

        for item in expanded_items:
            resolution = self.defaults.resolve_commodity(item["commodityCode"])
            commodity_consumption.append(
                CommodityConsumptionRecord(
                    commodity=resolution.commodity,
                    acute_kg_per_day=item.get("acuteKgPerDay"),
                    chronic_kg_per_day=item.get("chronicKgPerDay"),
                    source_reference=source_reference,
                )
            )

        available_codes = {item.commodity.commodity_code for item in commodity_consumption}
        for code in request.required_commodity_codes:
            canonical = self.defaults.resolve_commodity(code).commodity.commodity_code
            if canonical in available_codes:
                matched.append(canonical)
            else:
                missing.append(canonical)

        quality_flags = []
        limitations = [LimitationNote(code="profile_limitations", message=text) for text in profile_record["limitations"]]
        if missing:
            quality_flags.append(
                QualityFlag(
                    code="profile_coverage_gap",
                    severity=Severity.WARNING,
                    message="The selected consumption profile does not cover all requested commodities.",
                )
            )

        profile = DietaryConsumptionProfile(
            profile_id=profile_record["profileId"],
            display_name=profile_record["displayName"],
            population_group=profile_record["populationGroup"],
            profile_family=profile_record.get("profileFamily"),
            regulatory_basis=profile_record.get("regulatoryBasis"),
            review_status=profile_record.get("reviewStatus"),
            survey_profile_source=profile_record["surveySource"],
            region_id=profile_record["regionId"],
            body_weight_kg=float(profile_record["bodyWeightKg"]),
            applicable_windows=[IntakeWindowSemantic(item) for item in profile_record["applicableWindows"]],
            commodity_consumption=commodity_consumption,
            provenance=self.provenance.bundle([source_reference]),
            quality_flags=quality_flags
            + [
                QualityFlag(
                    code=item["code"],
                    severity=Severity(item["severity"]),
                    message=item["message"],
                )
                for item in profile_record.get("qualityFlags", [])
            ],
            limitations=limitations,
        )
        return ConsumptionProfileSelectionResult(
            profile=profile,
            matched_commodities=sorted(set(matched)),
            missing_commodities=sorted(set(missing)),
            quality_flags=quality_flags,
            limitations=limitations,
        )

    def build_dietary_intake_scenario(
        self,
        request: BuildDietaryIntakeScenarioRequest,
    ) -> DietaryIntakeScenarioDefinition:
        intake_window = request.intake_window_semantic
        if request.scenario_class == ScenarioClass.BOUNDED_ACUTE:
            intake_window = IntakeWindowSemantic.ACUTE
        elif request.scenario_class == ScenarioClass.BOUNDED_CHRONIC:
            intake_window = IntakeWindowSemantic.CHRONIC

        if request.residue_profile.region_id != request.consumption_profile.region_id:
            raise DietaryValidationError(
                code="region_mismatch",
                message="Residue profile region and consumption profile region must match.",
                suggestion="Align residue and consumption inputs to the same region pack.",
            )

        source_references = (
            request.residue_profile.provenance.source_references
            + request.consumption_profile.provenance.source_references
        )
        quality_flags = request.residue_profile.quality_flags + request.consumption_profile.quality_flags
        limitations = request.residue_profile.limitations + request.consumption_profile.limitations

        return DietaryIntakeScenarioDefinition(
            chemical_identity=request.chemical_identity,
            scenario_class=request.scenario_class,
            model_family=request.model_family,
            intake_window_semantic=intake_window,
            fit_for_purpose=request.fit_for_purpose,
            residue_profile=request.residue_profile,
            consumption_profile=request.consumption_profile,
            population_context=PopulationContext(
                population_group=request.consumption_profile.population_group,
                region_id=request.consumption_profile.region_id,
                body_weight_kg=request.consumption_profile.body_weight_kg,
                source_profile_id=request.consumption_profile.profile_id,
            ),
            provenance=self.provenance.bundle(source_references),
            quality_flags=quality_flags,
            limitations=limitations,
        )

    def summarize_intake(self, request: BuildBoundedIntakeSummaryRequest):
        plugin = self.plugins.resolve(
            scenario_class=request.scenario.scenario_class,
            model_family=request.scenario.model_family,
        )
        return plugin.run(request.scenario)

    def normalize_external_adapter_summary(
        self,
        payload: ExternalAdapterSummaryPayload,
        scenario: DietaryIntakeScenarioDefinition,
    ):
        return normalize_external_adapter_summary(
            payload,
            scenario,
            self.defaults,
            self.provenance,
        )

    def check_adapter_import(self, request: CheckAdapterImportRequest):
        enforce_residue_record_limit(len(request.residue_records))
        enforce_csv_byte_limit(request.csv_text)
        return build_adapter_import_check_result(self, request)

    def check_contaminant_monitoring_import(self, request: CheckContaminantMonitoringImportRequest):
        enforce_csv_byte_limit(request.csv_text)
        return build_contaminant_monitoring_import_check_result(self, request)

    def compare_adapter_import_to_walkthrough(
        self,
        request: CompareAdapterImportToWalkthroughRequest,
    ):
        return compare_adapter_import_to_walkthrough(self.repo_root, request)

    def export_adapter_review_bundle(
        self,
        request: ExportAdapterReviewBundleRequest,
    ):
        return export_adapter_review_bundle(request)

    def export_trade_risk_review_bundle(
        self,
        request: ExportTradeRiskReviewBundleRequest,
    ):
        return export_trade_risk_review_bundle(self.defaults, request)

    def export_version_pinned_trade_risk_review_dossier(
        self,
        request: ExportVersionPinnedTradeRiskReviewDossierRequest,
    ):
        return export_version_pinned_trade_risk_review_dossier(self.repo_root, request)

    def export_metals_monitoring_interpretation_bundle(
        self,
        request: ExportMetalsMonitoringInterpretationBundleRequest,
    ):
        return export_metals_monitoring_interpretation_bundle(self.defaults, request)

    def export_contaminant_monitoring_interpretation_bundle(
        self,
        request: ExportContaminantMonitoringInterpretationBundleRequest,
    ):
        return export_contaminant_monitoring_interpretation_bundle(self.defaults, request)

    def export_contaminant_monitoring_signoff_packet(
        self,
        request: ExportContaminantMonitoringSignoffPacketRequest,
    ):
        return export_contaminant_monitoring_signoff_packet(request)

    def export_version_pinned_contaminant_monitoring_review_dossier(
        self,
        request: ExportVersionPinnedContaminantMonitoringReviewDossierRequest,
    ):
        return export_version_pinned_contaminant_monitoring_review_dossier(self.repo_root, request)

    def export_metals_monitoring_signoff_packet(
        self,
        request: ExportMetalsMonitoringSignoffPacketRequest,
    ):
        return export_metals_monitoring_signoff_packet(request)

    def export_version_pinned_metals_monitoring_review_dossier(
        self,
        request: ExportVersionPinnedMetalsMonitoringReviewDossierRequest,
    ):
        return export_version_pinned_metals_monitoring_review_dossier(self.repo_root, request)

    def export_version_pinned_adapter_review_dossier(
        self,
        request: ExportVersionPinnedAdapterReviewDossierRequest,
    ):
        return export_version_pinned_adapter_review_dossier(self.repo_root, request)

    def export_sanitised_public_review_dossier(
        self,
        request: ExportSanitisedPublicReviewDossierRequest,
    ):
        return export_sanitised_public_review_dossier(request)

    def export_interoperability_preview(
        self,
        request: ExportInteroperabilityPreviewRequest,
    ):
        return export_interoperability_preview(self.repo_root, request)

    def assess_interoperability_preview_readiness(
        self,
        request: AssessInteroperabilityPreviewReadinessRequest,
    ):
        return assess_interoperability_preview_readiness(self.defaults, self.repo_root, request)

    def export_interoperability_remediation_bundle(
        self,
        request: ExportInteroperabilityRemediationBundleRequest,
    ):
        return export_interoperability_remediation_bundle(self.repo_root, request)

    def export_interoperability_signoff_packet(
        self,
        request: ExportInteroperabilitySignoffPacketRequest,
    ):
        return export_interoperability_signoff_packet(request)

    def assess_review_dossier_readiness(
        self,
        request: AssessReviewDossierReadinessRequest,
    ):
        return assess_review_dossier_readiness(self.defaults, self.repo_root, request)

    def export_scientific_follow_up_queue_bundle(
        self,
        request: ExportScientificFollowUpQueueBundleRequest,
    ):
        return export_scientific_follow_up_queue_bundle(request)

    def export_scientific_follow_up_review_board(
        self,
        request: ExportScientificFollowUpReviewBoardRequest,
    ):
        return export_scientific_follow_up_review_board(request)

    def export_scientific_follow_up_owner_handoff_packet(
        self,
        request: ExportScientificFollowUpOwnerHandoffPacketRequest,
    ):
        return export_scientific_follow_up_owner_handoff_packet(request)

    def export_scientific_follow_up_owner_remediation_packet(
        self,
        request: ExportScientificFollowUpOwnerRemediationPacketRequest,
    ):
        return export_scientific_follow_up_owner_remediation_packet(request)

    def export_scientific_follow_up_owner_signoff_packet(
        self,
        request: ExportScientificFollowUpOwnerSignoffPacketRequest,
    ):
        return export_scientific_follow_up_owner_signoff_packet(request)

    def export_version_pinned_scientific_follow_up_owner_signoff_dossier(
        self,
        request: ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest,
    ):
        return export_version_pinned_scientific_follow_up_owner_signoff_dossier(self.repo_root, request)

    def lookup_reference_values(
        self,
        request: LookupReferenceValuesRequest,
    ):
        return lookup_reference_values(self.defaults, request)

    def lookup_contaminant_legal_limits(
        self,
        request: LookupContaminantLegalLimitsRequest,
    ):
        return lookup_contaminant_legal_limits(self.defaults, request)

    def lookup_method_support(
        self,
        request: LookupMethodSupportRequest,
    ):
        return lookup_method_support(self.defaults, request)

    def lookup_consumption_dataset_support(
        self,
        request: LookupConsumptionDatasetSupportRequest,
    ):
        return lookup_consumption_dataset_support(self.defaults, request)

    def lookup_reporting_profiles(
        self,
        request: LookupReportingProfilesRequest,
    ):
        return lookup_reporting_profiles(self.defaults, request)

    def lookup_occurrence_evidence(
        self,
        request: LookupOccurrenceEvidenceRequest,
    ):
        return lookup_occurrence_evidence(self.defaults, request)

    def lookup_analytical_method_evidence(
        self,
        request: LookupAnalyticalMethodEvidenceRequest,
    ):
        return lookup_analytical_method_evidence(self.defaults, request)

    def lookup_metals_occurrence(
        self,
        request: LookupMetalsOccurrenceRequest,
    ):
        return lookup_metals_occurrence(self.defaults, request)

    def lookup_metals_review_focus(
        self,
        request: LookupMetalsReviewFocusRequest,
    ):
        return lookup_metals_review_focus(self.defaults, request)

    def assess_residue_evidence_fit(self, request) -> ResidueEvidenceFitAssessment:
        profile_codes = {record.commodity.commodity_code for record in request.residue_profile.records}
        consumption_codes = {item.commodity.commodity_code for item in request.consumption_profile.commodity_consumption}
        matched = profile_codes.intersection(consumption_codes)
        coverage_fraction = len(matched) / len(consumption_codes) if consumption_codes else 0.0
        score = coverage_fraction
        reasons = []
        quality_flags = []

        if coverage_fraction < 1.0:
            reasons.append("Residue profile does not cover every commodity in the selected consumption profile.")
        if request.scenario_class != ScenarioClass.POINT_ESTIMATE:
            missing_bounds = [
                record.commodity.commodity_code
                for record in request.residue_profile.records
                if record.lower_bound_mg_per_kg is None or record.upper_bound_mg_per_kg is None
            ]
            if missing_bounds:
                score -= 0.2
                reasons.append("Bounded workflow requested without explicit residue bounds for all commodities.")
                quality_flags.append(
                    QualityFlag(
                        code="missing_explicit_residue_bounds",
                        severity=Severity.WARNING,
                        message=(
                            "Bounded workflow requested without explicit residue bounds for "
                            f"{sorted(missing_bounds)}."
                        ),
                    )
                )
        heuristic_records = [
            record.commodity.commodity_code
            for record in request.residue_profile.records
            if record.commodity.mapping_status == "heuristic"
        ]
        if heuristic_records:
            score -= 0.1
            quality_flags.append(
                QualityFlag(
                    code="heuristic_mapping_present",
                    severity=Severity.WARNING,
                    message="At least one residue record relies on heuristic commodity mapping.",
                )
            )
            reasons.append("Heuristic commodity mappings reduce regulatory confidence.")

        score = max(min(score, 1.0), 0.0)
        if request.scenario_class != ScenarioClass.POINT_ESTIMATE and any(
            record.lower_bound_mg_per_kg is None or record.upper_bound_mg_per_kg is None
            for record in request.residue_profile.records
        ):
            score = min(score, 0.74)
            verdict = "review_needed"
        else:
            verdict = "good_fit" if score >= 0.75 else "review_needed"
        return ResidueEvidenceFitAssessment(
            fit_score=score,
            coverage_fraction=coverage_fraction,
            verdict=verdict,
            reasons=reasons,
            quality_flags=quality_flags,
        )

    def apply_residue_evidence(self, request: ApplyResidueEvidenceRequest) -> ResidueEvidenceApplicationResult:
        built = self.build_residue_profile(
            BuildDietaryResidueProfileRequest(
                chemical_identity=request.residue_profile.chemical_identity,
                region_id=request.residue_profile.region_id,
                residue_records=request.additional_records,
            )
        )
        merged_records = {record.commodity.commodity_code: record for record in request.residue_profile.records}
        applied_assumptions = []
        for record in built.records:
            key = record.commodity.commodity_code
            if key not in merged_records or request.override_existing:
                merged_records[key] = record
                applied_assumptions.append(
                    self.provenance.user_input(
                        parameter=f"residue_override:{key}",
                        value=record.residue_concentration_mg_per_kg,
                        unit=record.residue_unit,
                        rationale="Additional residue evidence was merged into the residue profile.",
                        source_reference=record.source_reference,
                    )
                )

        merged_profile = DietaryResidueProfile(
            chemical_identity=request.residue_profile.chemical_identity,
            region_id=request.residue_profile.region_id,
            records=sorted(merged_records.values(), key=lambda item: item.commodity.commodity_code),
            provenance=self.provenance.bundle(
                request.residue_profile.provenance.source_references + built.provenance.source_references
            ),
            quality_flags=request.residue_profile.quality_flags + built.quality_flags,
            limitations=request.residue_profile.limitations + built.limitations,
        )
        return ResidueEvidenceApplicationResult(
            residue_profile=merged_profile,
            applied_assumptions=applied_assumptions,
            notes=["Additional residue evidence was merged using commodity-code identity."],
        )

    def reconcile_residue_evidence(
        self,
        request: ReconcileResidueEvidenceRequest,
    ) -> ResidueEvidenceReconciliationResult:
        by_commodity: dict[str, list[DietaryCommodityResidueRecord]] = {}
        for profile in request.evidence_profiles:
            for record in profile.records:
                by_commodity.setdefault(record.commodity.commodity_code, []).append(record)

        reconciled_records = []
        conflicts = []
        source_references = []
        for commodity_code, records in sorted(by_commodity.items()):
            point_values = [record.residue_concentration_mg_per_kg for record in records]
            mean_value = sum(point_values) / len(point_values)
            lower = min(
                (
                    record.lower_bound_mg_per_kg
                    if record.lower_bound_mg_per_kg is not None
                    else record.residue_concentration_mg_per_kg
                )
                for record in records
            )
            upper = max(
                (
                    record.upper_bound_mg_per_kg
                    if record.upper_bound_mg_per_kg is not None
                    else record.residue_concentration_mg_per_kg
                )
                for record in records
            )
            spread = max(point_values) - min(point_values)
            conflict_threshold = max(0.25 * abs(mean_value), 1e-6)
            if spread > conflict_threshold:
                conflicts.append(f"{commodity_code} residue evidence differs by more than 25%.")
            template = records[0]
            if template.source_reference:
                source_references.append(template.source_reference)
            reconciled_records.append(
                template.model_copy(
                    update={
                        "residue_concentration_mg_per_kg": mean_value,
                        "lower_bound_mg_per_kg": lower,
                        "upper_bound_mg_per_kg": upper,
                        "source_type": ResidueSourceType.RECONCILED,
                        "review_status": "reconciled_screening",
                        "provenance": self.provenance.bundle(
                            [
                                ref
                                for record in records
                                for ref in record.provenance.source_references
                            ]
                        ),
                    }
                )
            )

        reconciled_profile = DietaryResidueProfile(
            chemical_identity=request.chemical_identity,
            region_id=request.region_id,
            records=reconciled_records,
            provenance=self.provenance.bundle(source_references),
            limitations=[
                LimitationNote(
                    code="reconciled_evidence",
                    message="Residue evidence was reconciled by averaging point estimates and retaining the observed bound range.",
                )
            ],
        )
        return ResidueEvidenceReconciliationResult(
            reconciled_profile=reconciled_profile,
            agreed_commodities=sorted(by_commodity.keys()),
            conflicts=conflicts,
            recommended_next_actions=(
                ["Review conflicting commodity residue evidence before higher-confidence use."]
                if conflicts
                else ["Residue evidence is internally consistent for screening use."]
            ),
        )
