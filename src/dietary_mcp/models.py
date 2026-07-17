from __future__ import annotations

from datetime import date, datetime
from enum import Enum
import hashlib
import json
import math
from typing import Any, ClassVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from dietary_mcp.package_metadata import DEFAULTS_VERSION, SCHEMA_VERSION
from dietary_mcp.result_meta import ResultMetadata


# Execution-metadata fields that carry wall-clock timestamps. They are stripped
# (at any nesting depth) before hashing so derived identifiers depend only on the
# scientific content of a model, not on when the artifact happened to be built.
_VOLATILE_HASH_KEYS = frozenset({"generated_at", "generatedAt", "executed_at", "executedAt"})


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_volatile(item)
            for key, item in value.items()
            if key not in _VOLATILE_HASH_KEYS
        }
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


def _content_hash_id(prefix: str, payload: Any) -> str:
    """Return a deterministic ``<prefix>-<12hex>`` identifier for ``payload``.

    The suffix is the first 12 hex characters of the SHA-256 digest of the
    canonical JSON encoding of ``payload`` (with volatile timestamp fields
    removed). This keeps regenerated artifacts byte-for-byte stable across
    processes, platforms, and runs, replacing the former ``uuid4().hex[:12]``
    random suffixes that made committed artifacts and reproducibility
    fingerprints non-deterministic.
    """

    canonical = _strip_volatile(payload)
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()[:12]}"


def _assign_content_hash_id(model: BaseModel, field_name: str, prefix: str) -> None:
    """Replace ``model.<field_name>`` with a content-derived deterministic id.

    The identifier field itself is excluded from the hashed payload so the
    result is independent of whatever placeholder default factory produced.
    Nested models are already fully validated (and therefore carry their own
    deterministic ids) by the time an ``after`` validator runs, so the parent
    hash is stable too.
    """

    payload = model.model_dump(mode="json", by_alias=True, exclude={field_name})
    object.__setattr__(model, field_name, _content_hash_id(prefix, payload))


MAX_RAW_SURVEY_RECORDS = 100_000
MAX_RESIDUE_RECORDS = 2_000
MAX_REQUIRED_COMMODITY_CODES = 2_000
MAX_TARGET_JURISDICTIONS = 100
MAX_CSV_TEXT_LENGTH = 5_000_000
MAX_PROBABILISTIC_ITERATIONS = 1_000_000
MAX_UNCERTAINTY_OUTER_ITERATIONS = 50_000
MAX_UNCERTAINTY_INNER_ITERATIONS = 100_000


class DietaryBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ContentHashIdModel(DietaryBaseModel):
    """Base for models whose identifier is a deterministic content hash.

    Subclasses set ``_content_hash_id_field`` (the Python field name holding the
    identifier) and ``_content_hash_id_prefix`` (the ``<prefix>`` of the
    ``<prefix>-<12hex>`` value). The identifier's ``default_factory`` may still
    produce a random placeholder; this validator deterministically overwrites it
    from a SHA-256 of the model's content once every field (including nested
    models, which carry their own deterministic ids) has been validated.
    """

    _content_hash_id_field: ClassVar[str] = ""
    _content_hash_id_prefix: ClassVar[str] = ""

    @model_validator(mode="after")
    def _assign_deterministic_id(self) -> "ContentHashIdModel":
        field_name = type(self)._content_hash_id_field
        prefix = type(self)._content_hash_id_prefix
        if field_name and prefix:
            _assign_content_hash_id(self, field_name, prefix)
        return self


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ScientificLedgerEntryKind(str, Enum):
    ASSUMPTION = "assumption"
    UNCERTAINTY = "uncertainty"
    DATA_GAP = "data_gap"
    GOVERNANCE_LIMIT = "governance_limit"


class SourceClassification(str, Enum):
    USER_INPUT = "user_input"
    CURATED_DEFAULT = "curated_default"
    MAPPED = "mapped"
    DERIVED = "derived"
    HEURISTIC = "heuristic"


class SourceOriginTag(str, Enum):
    OFFICIAL_REGULATORY = "official_regulatory"
    CURATED_DERIVED = "curated_derived"
    ILLUSTRATIVE_PLACEHOLDER = "illustrative_placeholder"
    INTERNAL_OPERATIONAL = "internal_operational"


class DocumentStatus(str, Enum):
    FINAL_CURRENT = "final_current"
    SUPERSEDED = "superseded"
    DRAFT = "draft"
    CONSULTATION = "consultation"
    TOOL_METADATA = "tool_metadata"
    DATASET_CURRENT = "dataset_current"


class RegulatoryRole(str, Enum):
    BINDING = "binding"
    GUIDANCE = "guidance"
    TECHNICAL_REPORT = "technical_report"
    DATASET = "dataset"
    SOFTWARE_METADATA = "software_metadata"


class SubmissionUse(str, Enum):
    ALLOWED = "allowed"
    REVIEW_REQUIRED = "review_required"
    NOT_ALLOWED = "not_allowed"


class GovernanceStatus(str, Enum):
    INTERNAL_REFERENCE_ONLY = "internal_reference_only"
    COMPATIBILITY_HARNESS_ONLY = "compatibility_harness_only"
    OFFICIAL_SUBMISSION_ENGINE = "official_submission_engine"
    DEPRECATED = "deprecated"


class ReadinessStatus(str, Enum):
    PASS = "pass"
    REVIEW_REQUIRED = "review_required"
    FAIL = "fail"


class ScientificFollowUpQueueLabel(str, Enum):
    OPEN = "open"
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    WAIVED = "waived"
    ESCALATED = "escalated"


class ScientificFollowUpOwnerLane(str, Enum):
    SCIENTIFIC_REVIEWER = "scientific_reviewer"
    REGULATORY_REVIEWER = "regulatory_reviewer"
    REVIEW_LEAD = "review_lead"


class ScientificFollowUpDueState(str, Enum):
    IMMEDIATE = "immediate"
    CURRENT_CYCLE = "current_cycle"
    IN_PROGRESS = "in_progress"
    CLOSED_WITH_WAIVER = "closed_with_waiver"
    CLOSED = "closed"


class ScientificFollowUpRemediationClass(str, Enum):
    RESOLVE_NOW = "resolve_now"
    REVIEW_THIS_CYCLE = "review_this_cycle"
    TRACK_IN_PROGRESS = "track_in_progress"
    RECORD_CLOSURE = "record_closure"


class BundleProfile(str, Enum):
    INTERNAL_REVIEW = "internal_review"
    SUBMISSION_CANDIDATE = "submission_candidate"
    SANITISED_PUBLIC = "sanitised_public"


class ConfidentialityTag(str, Enum):
    PUBLIC = "public"
    CONFIDENTIAL = "confidential"


class SanitisationState(str, Enum):
    RETAINED = "retained"
    REDACTED = "redacted"
    REMOVED = "removed"


class ResidueSourceType(str, Enum):
    MONITORING = "monitoring"
    MODELED = "modeled"
    CURATED_DEFAULT = "curated_default"
    USER_SUPPLIED = "user_supplied"
    RECONCILED = "reconciled"


class UncertaintyAssessmentMode(str, Enum):
    TWO_DIMENSIONAL_MONTE_CARLO = "two_dimensional_monte_carlo"


class ResidueUncertaintyDistribution(str, Enum):
    POINT = "point"
    EMPIRICAL = "empirical"
    UNIFORM = "uniform"
    TRIANGULAR = "triangular"
    LOGNORMAL = "lognormal"
    CENSORED_LOGNORMAL = "censored_lognormal"


class CensoredDataPolicy(str, Enum):
    LOWER_BOUND_ZERO = "lower_bound_zero"
    MIDDLE_BOUND_HALF_LOD_LOQ = "middle_bound_half_lod_loq"
    UPPER_BOUND_LOD_LOQ = "upper_bound_lod_loq"
    THREE_BOUND_SENSITIVITY = "three_bound_sensitivity"


class HealthReferenceType(str, Enum):
    ADI = "ADI"
    ARFD = "ARfD"
    TDI = "TDI"
    BMDL = "BMDL"
    MOE_REFERENCE_POINT = "MOE_REFERENCE_POINT"


class IntakeWindowSemantic(str, Enum):
    ACUTE = "acute"
    CHRONIC = "chronic"


class ScenarioClass(str, Enum):
    POINT_ESTIMATE = "point_estimate"
    BOUNDED_ACUTE = "bounded_acute"
    BOUNDED_CHRONIC = "bounded_chronic"


class ModelFamily(str, Enum):
    REFERENCE_DIETARY = "reference_dietary"
    ADAPTER_STUB = "adapter_stub"
    EFSA_PRIMO_ADAPTER = "efsa_primo_adapter"
    EPA_DEEM_ADAPTER = "epa_deem_adapter"


class ContaminantFamily(str, Enum):
    PESTICIDE_RESIDUE = "pesticide_residue"
    MICROPLASTICS_EMERGING = "microplastics_emerging"
    PFAS_FOOD_CONTAMINANTS = "pfas_food_contaminants"
    ACRYLAMIDE_PROCESS_CONTAMINANTS = "acrylamide_process_contaminants"
    BISPHENOL_FOOD_CONTACT_MIGRATION = "bisphenol_food_contact_migration"
    CADMIUM_FOOD_CONTAMINANTS = "cadmium_food_contaminants"
    LEAD_FOOD_CONTAMINANTS = "lead_food_contaminants"
    INORGANIC_ARSENIC_FOOD_CONTAMINANTS = "inorganic_arsenic_food_contaminants"
    MERCURY_FOOD_CONTAMINANTS = "mercury_food_contaminants"
    FOOD_CONTAMINANT = "food_contaminant"


class FitForPurpose(str, Enum):
    SCREENING = "screening"
    DOWNSTREAM_EXPORT = "downstream_export"
    BENCHMARK = "benchmark"
    COMPARISON = "comparison"


class Route(str, Enum):
    ORAL = "oral"


class ProcessedStatus(str, Enum):
    RAW_PRIMARY_COMMODITY = "raw_primary_commodity"
    PROCESSED_DERIVATIVE = "processed_derivative"


class MappingConfidence(str, Enum):
    REVIEWED = "reviewed"
    PROVISIONAL = "provisional"
    HEURISTIC = "heuristic"


class MethodMaturityStatus(str, Enum):
    ESTABLISHED = "established"
    TRANSITIONAL = "transitional"
    EXPLORATORY = "exploratory"
    EMERGING = "emerging"


class EvidenceSupportStatus(str, Enum):
    ESTABLISHED = "established"
    LIMITED = "limited"
    EMERGING = "emerging"
    INSUFFICIENT = "insufficient"


class JurisdictionCoverageLevel(str, Enum):
    DEEP_CURATED = "deep_curated"
    ANCHOR_ONLY = "anchor_only"
    EXPLICIT_GAP = "explicit_gap"


class RequestedLaneStatus(str, Enum):
    EXACT_CURATED_MATCH = "exact_curated_match"
    FAMILY_CURATED_BUT_REQUESTED_LANE_UNMATCHED = "family_curated_but_requested_lane_unmatched"
    ANCHOR_ONLY_FAMILY = "anchor_only_family"
    EXPLICIT_GAP = "explicit_gap"
    NO_CURATED_FAMILY_COVERAGE = "no_curated_family_coverage"
    UNSCOPED_LOOKUP = "unscoped_lookup"


class ReferenceValueJurisdictionStatus(str, Enum):
    EXACT_JURISDICTION_VALUE_PRESENT = "exact_jurisdiction_value_present"
    JURISDICTION_VALUE_EXISTS_BUT_FILTER_UNMATCHED = "jurisdiction_value_exists_but_filter_unmatched"
    FAMILY_CURATED_WITHOUT_REFERENCE_VALUE = "family_curated_without_reference_value"
    ANCHOR_ONLY_FAMILY = "anchor_only_family"
    EXPLICIT_GAP = "explicit_gap"
    NO_CURATED_FAMILY_COVERAGE = "no_curated_family_coverage"
    UNSCOPED_LOOKUP = "unscoped_lookup"


class TradeMrlCoverageStatus(str, Enum):
    ALL_REQUESTED_PAIRS_EXACTLY_CURATED = "all_requested_pairs_exactly_curated"
    REQUESTED_PAIR_OUTSIDE_CURATED_SCOPE = "requested_pair_outside_curated_scope"
    FAMILY_CURATED_WITHOUT_MRL = "family_curated_without_mrl"
    ANCHOR_ONLY_FAMILY = "anchor_only_family"
    EXPLICIT_GAP = "explicit_gap"
    NO_CURATED_FAMILY_COVERAGE = "no_curated_family_coverage"
    UNSCOPED_LOOKUP = "unscoped_lookup"


class ContaminantLegalLimitType(str, Enum):
    ACTION_LEVEL = "action_level"
    MAXIMUM_LEVEL = "maximum_level"
    COMPLIANCE_POLICY_GUIDANCE = "compliance_policy_guidance"


class ReportingMetricKind(str, Enum):
    SUM_FIXED_PANEL = "sum_fixed_panel"
    RELATIVE_POTENCY_EQUIVALENT = "relative_potency_equivalent"
    INDIVIDUAL_ANALYTE_PANEL = "individual_analyte_panel"


class MrlEnforcementRecord(DietaryBaseModel):
    record_id: str = Field(alias="recordId")
    substance_key: str = Field(alias="substanceKey")
    commodity_code: str = Field(alias="commodityCode")
    authority: str
    jurisdiction: str
    mrl_value_mg_per_kg: float = Field(alias="mrlValueMgPerKg")
    effective_date: date | None = Field(default=None, alias="effectiveDate")
    superseded_by_record_id: str | None = Field(default=None, alias="supersededByRecordId")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    notes: list[str] = Field(default_factory=list)


class RecipeComponent(DietaryBaseModel):
    commodity_code: str = Field(alias="commodityCode")
    proportion: float

    @field_validator("proportion")
    @classmethod
    def validate_proportion(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Recipe component proportions must be finite.")
        if value < 0.0 or value > 1.0:
            raise ValueError("Recipe component proportions must be between 0.0 and 1.0.")
        return value


class CompositionRecipeRecord(DietaryBaseModel):
    recipe_id: str = Field(alias="recipeId")
    composite_commodity_code: str = Field(alias="compositeCommodityCode")
    components: list[RecipeComponent]
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_component_total(self) -> "CompositionRecipeRecord":
        total = sum(component.proportion for component in self.components)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError("Composition recipe component proportions must sum to 1.0.")
        return self


class ReportingProfileRole(str, Enum):
    PRIMARY_REGULATORY = "primary_regulatory"
    REGULATORY_COMPLIANCE_VARIANT = "regulatory_compliance_variant"
    NATIONAL_ADVISORY_OPTIONAL = "national_advisory_optional"
    SUPPORTING_DETAIL = "supporting_detail"


class InteroperabilitySupportLevel(str, Enum):
    DIRECT = "direct"
    DERIVED = "derived"
    REVIEW_REQUIRED = "review_required"


class InteroperabilityActionDecisionStatus(str, Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    WAIVED = "waived"


class InteroperabilitySignoffStatus(str, Enum):
    OPEN = "open"
    SIGNED_OFF = "signed_off"
    SIGNED_OFF_WITH_WAIVERS = "signed_off_with_waivers"


class MetalsMonitoringEscalationType(str, Enum):
    WAIVER_REVIEW = "waiver_review"
    BLOCKING_FOLLOW_UP = "blocking_follow_up"


class QualityFlag(DietaryBaseModel):
    code: str
    severity: Severity
    message: str


class LimitationNote(DietaryBaseModel):
    code: str
    message: str


class ScientificLedgerEntry(DietaryBaseModel):
    entry_id: str = Field(alias="entryId")
    entry_kind: ScientificLedgerEntryKind = Field(alias="entryKind")
    category: str
    severity: Severity
    summary: str
    rationale: str
    conservative: bool | None = None
    affected_fields: list[str] = Field(default_factory=list, alias="affectedFields")
    linked_record_ids: list[str] = Field(default_factory=list, alias="linkedRecordIds")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")


class SourceReference(DietaryBaseModel):
    source_id: str
    title: str
    effective_date: date | None = None
    url: str | None = None
    origin_tag: SourceOriginTag | None = Field(default=None, alias="originTag")


class RegulatorySourceRecord(DietaryBaseModel):
    source_id: str = Field(alias="sourceId")
    title: str
    organization: str
    kind: str
    jurisdiction: str
    document_status: DocumentStatus = Field(alias="documentStatus")
    regulatory_role: RegulatoryRole = Field(alias="regulatoryRole")
    effective_date: date | None = Field(default=None, alias="effectiveDate")
    url: str
    origin_tag: SourceOriginTag | None = Field(default=None, alias="originTag")
    submission_use: SubmissionUse = Field(alias="submissionUse")
    normative_for: list[str] = Field(default_factory=list, alias="normativeFor")
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: list[str] = Field(default_factory=list, alias="supersededBy")
    notes: list[str] = Field(default_factory=list)


class AuthorityRecord(DietaryBaseModel):
    authority_id: str = Field(alias="authorityId")
    authority: str
    jurisdiction: str
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    notes: list[str] = Field(default_factory=list)


class SourceConflictGroup(DietaryBaseModel):
    conflict_group_id: str = Field(alias="conflictGroupId")
    substance_key: str = Field(alias="substanceKey")
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    record_ids: list[str] = Field(default_factory=list, alias="recordIds")
    authorities: list[str] = Field(default_factory=list)
    note: str | None = None


class ReferenceValueRecord(DietaryBaseModel):
    record_id: str = Field(alias="recordId")
    substance_key: str = Field(alias="substanceKey")
    substance_name: str = Field(alias="substanceName")
    reference_type: str = Field(alias="referenceType")
    authority: str
    jurisdiction: str
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    value: float | None = None
    unit: str | None = None
    qualifier: str | None = None
    assessment_label: str | None = Field(default=None, alias="assessmentLabel")
    assessment_year: int | None = Field(default=None, ge=1900, le=2100, alias="assessmentYear")
    population: str | None = None
    source_output_id: int | None = Field(default=None, ge=0, alias="sourceOutputId")
    source_ids: list[str] = Field(alias="sourceIds")
    primary_source_id: str | None = Field(default=None, alias="primarySourceId")
    database_source_id: str | None = Field(default=None, alias="databaseSourceId")
    conflict_group_id: str | None = Field(default=None, alias="conflictGroupId")
    document_status: DocumentStatus = Field(alias="documentStatus")
    submission_use: SubmissionUse = Field(alias="submissionUse")
    effective_date: date | None = Field(default=None, alias="effectiveDate")
    notes: list[str] = Field(default_factory=list)


class ConsumptionDatasetRecord(DietaryBaseModel):
    dataset_id: str = Field(alias="datasetId")
    display_name: str = Field(alias="displayName")
    authority: str
    jurisdiction: str
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    dataset_kind: str = Field(alias="datasetKind")
    maturity_status: MethodMaturityStatus = Field(alias="maturityStatus")
    submission_use: SubmissionUse = Field(alias="submissionUse")
    document_status: DocumentStatus = Field(alias="documentStatus")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    method_ids: list[str] = Field(default_factory=list, alias="methodIds")
    compatible_model_families: list[ModelFamily] = Field(default_factory=list, alias="compatibleModelFamilies")
    notes: list[str] = Field(default_factory=list)


class MetalsOccurrenceRecord(DietaryBaseModel):
    record_id: str = Field(alias="recordId")
    display_name: str = Field(alias="displayName")
    authority: str
    jurisdiction: str
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    occurrence_kind: str = Field(alias="occurrenceKind")
    focus_substances: list[str] = Field(default_factory=list, alias="focusSubstances")
    matrix_scope: list[str] = Field(default_factory=list, alias="matrixScope")
    maturity_status: MethodMaturityStatus = Field(alias="maturityStatus")
    evidence_support_status: EvidenceSupportStatus = Field(alias="evidenceSupportStatus")
    submission_use: SubmissionUse = Field(alias="submissionUse")
    document_status: DocumentStatus = Field(alias="documentStatus")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    method_ids: list[str] = Field(default_factory=list, alias="methodIds")
    legal_authority_ids: list[str] = Field(default_factory=list, alias="legalAuthorityIds")
    dataset_ids: list[str] = Field(default_factory=list, alias="datasetIds")
    reference_value_record_ids: list[str] = Field(default_factory=list, alias="referenceValueRecordIds")
    priority_food_groups: list[str] = Field(default_factory=list, alias="priorityFoodGroups")
    high_attention_foods: list[str] = Field(default_factory=list, alias="highAttentionFoods")
    sensitive_population_groups: list[str] = Field(default_factory=list, alias="sensitivePopulationGroups")
    review_questions: list[str] = Field(default_factory=list, alias="reviewQuestions")
    trend_signals: list[str] = Field(default_factory=list, alias="trendSignals")
    notes: list[str] = Field(default_factory=list)


class MetalsReviewFocusRecord(DietaryBaseModel):
    focus_id: str = Field(alias="focusId")
    display_name: str = Field(alias="displayName")
    authority: str
    jurisdiction: str
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    focus_kind: str = Field(alias="focusKind")
    commodity_groups: list[str] = Field(default_factory=list, alias="commodityGroups")
    focus_foods: list[str] = Field(default_factory=list, alias="focusFoods")
    sensitive_population_groups: list[str] = Field(default_factory=list, alias="sensitivePopulationGroups")
    linked_occurrence_record_ids: list[str] = Field(default_factory=list, alias="linkedOccurrenceRecordIds")
    maturity_status: MethodMaturityStatus = Field(alias="maturityStatus")
    evidence_support_status: EvidenceSupportStatus = Field(alias="evidenceSupportStatus")
    submission_use: SubmissionUse = Field(alias="submissionUse")
    document_status: DocumentStatus = Field(alias="documentStatus")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    method_ids: list[str] = Field(default_factory=list, alias="methodIds")
    legal_authority_ids: list[str] = Field(default_factory=list, alias="legalAuthorityIds")
    dataset_ids: list[str] = Field(default_factory=list, alias="datasetIds")
    reference_value_record_ids: list[str] = Field(default_factory=list, alias="referenceValueRecordIds")
    review_questions: list[str] = Field(default_factory=list, alias="reviewQuestions")
    notes: list[str] = Field(default_factory=list)


class OccurrenceEvidenceRecord(DietaryBaseModel):
    record_id: str = Field(alias="recordId")
    display_name: str = Field(alias="displayName")
    authority: str
    jurisdiction: str
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    evidence_kind: str = Field(alias="evidenceKind")
    analytes: list[str] = Field(default_factory=list)
    matrix_groups: list[str] = Field(default_factory=list, alias="matrixGroups")
    sample_set_summary: str = Field(alias="sampleSetSummary")
    measured_unit: str = Field(alias="measuredUnit")
    data_period: str | None = Field(default=None, alias="dataPeriod")
    lower_bound_handling: str | None = Field(default=None, alias="lowerBoundHandling")
    maturity_status: MethodMaturityStatus = Field(alias="maturityStatus")
    evidence_support_status: EvidenceSupportStatus = Field(alias="evidenceSupportStatus")
    submission_use: SubmissionUse = Field(alias="submissionUse")
    document_status: DocumentStatus = Field(alias="documentStatus")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    occurrence_record_ids: list[str] = Field(default_factory=list, alias="occurrenceRecordIds")
    dataset_ids: list[str] = Field(default_factory=list, alias="datasetIds")
    method_evidence_record_ids: list[str] = Field(default_factory=list, alias="methodEvidenceRecordIds")
    legal_authority_ids: list[str] = Field(default_factory=list, alias="legalAuthorityIds")
    reference_value_record_ids: list[str] = Field(default_factory=list, alias="referenceValueRecordIds")
    linked_review_focus_ids: list[str] = Field(default_factory=list, alias="linkedReviewFocusIds")
    reporting_profile_ids: list[str] = Field(default_factory=list, alias="reportingProfileIds")
    notes: list[str] = Field(default_factory=list)


class AnalyticalMethodEvidenceRecord(DietaryBaseModel):
    record_id: str = Field(alias="recordId")
    display_name: str = Field(alias="displayName")
    authority: str
    jurisdiction: str
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    evidence_kind: str = Field(alias="evidenceKind")
    analytes: list[str] = Field(default_factory=list)
    matrix_groups: list[str] = Field(default_factory=list, alias="matrixGroups")
    technique_summary: str = Field(alias="techniqueSummary")
    method_code: str | None = Field(default=None, alias="methodCode")
    lod_summary: str | None = Field(default=None, alias="lodSummary")
    lod_value: float | None = Field(default=None, alias="lodValue")
    lod_unit: str | None = Field(default=None, alias="lodUnit")
    loq_summary: str | None = Field(default=None, alias="loqSummary")
    loq_value: float | None = Field(default=None, alias="loqValue")
    loq_unit: str | None = Field(default=None, alias="loqUnit")
    recovery_summary: str | None = Field(default=None, alias="recoverySummary")
    recovery_range_percent: list[float] | None = Field(default=None, alias="recoveryRangePercent")
    measurement_uncertainty_summary: str | None = Field(default=None, alias="measurementUncertaintySummary")
    measurement_uncertainty_percent: float | None = Field(default=None, alias="measurementUncertaintyPercent")
    storage_stability_summary: str | None = Field(default=None, alias="storageStabilitySummary")
    sampling_plan_summary: str | None = Field(default=None, alias="samplingPlanSummary")
    sampling_plan_reference: str | None = Field(default=None, alias="samplingPlanReference")
    maturity_status: MethodMaturityStatus = Field(alias="maturityStatus")
    evidence_support_status: EvidenceSupportStatus = Field(alias="evidenceSupportStatus")
    submission_use: SubmissionUse = Field(alias="submissionUse")
    document_status: DocumentStatus = Field(alias="documentStatus")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    method_ids: list[str] = Field(default_factory=list, alias="methodIds")
    legal_authority_ids: list[str] = Field(default_factory=list, alias="legalAuthorityIds")
    reporting_profile_ids: list[str] = Field(default_factory=list, alias="reportingProfileIds")
    notes: list[str] = Field(default_factory=list)


class ReportingProfileRecord(DietaryBaseModel):
    profile_id: str = Field(alias="profileId")
    display_name: str = Field(alias="displayName")
    authority: str
    jurisdiction: str
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    metric_kind: ReportingMetricKind = Field(alias="metricKind")
    profile_role: ReportingProfileRole = Field(alias="profileRole")
    submission_use: SubmissionUse = Field(alias="submissionUse")
    document_status: DocumentStatus = Field(alias="documentStatus")
    reported_unit: str = Field(alias="reportedUnit")
    matrix_groups: list[str] = Field(default_factory=list, alias="matrixGroups")
    panel_analytes: list[str] = Field(default_factory=list, alias="panelAnalytes")
    aggregation_basis: str = Field(alias="aggregationBasis")
    weighting_basis_summary: str | None = Field(default=None, alias="weightingBasisSummary")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    legal_authority_ids: list[str] = Field(default_factory=list, alias="legalAuthorityIds")
    reference_value_record_ids: list[str] = Field(default_factory=list, alias="referenceValueRecordIds")
    not_substitutable_for_profile_ids: list[str] = Field(
        default_factory=list,
        alias="notSubstitutableForProfileIds",
    )
    notes: list[str] = Field(default_factory=list)


class MethodRegistryRecord(DietaryBaseModel):
    method_id: str = Field(alias="methodId")
    display_name: str = Field(alias="displayName")
    authority: str
    jurisdiction: str
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    method_type: str = Field(alias="methodType")
    current_version_label: str = Field(alias="currentVersionLabel")
    maturity_status: MethodMaturityStatus = Field(alias="maturityStatus")
    evidence_support_status: EvidenceSupportStatus = Field(alias="evidenceSupportStatus")
    submission_use: SubmissionUse = Field(alias="submissionUse")
    document_status: DocumentStatus = Field(alias="documentStatus")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    model_family: ModelFamily | None = Field(default=None, alias="modelFamily")
    notes: list[str] = Field(default_factory=list)


class LegalAuthorityRecord(DietaryBaseModel):
    authority_id: str = Field(alias="authorityId")
    title: str
    citation: str
    jurisdiction: str
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    regulatory_role: RegulatoryRole = Field(alias="regulatoryRole")
    document_status: DocumentStatus = Field(alias="documentStatus")
    submission_use: SubmissionUse = Field(alias="submissionUse")
    source_id: str = Field(alias="sourceId")
    notes: list[str] = Field(default_factory=list)


class ContaminantLegalLimitRecord(DietaryBaseModel):
    record_id: str = Field(alias="recordId")
    jurisdiction: str
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    substance_key: str = Field(alias="substanceKey")
    authority: str
    legal_authority_id: str = Field(alias="legalAuthorityId")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    limit_type: ContaminantLegalLimitType = Field(alias="limitType")
    matrix_groups: list[str] = Field(default_factory=list, alias="matrixGroups")
    commodity_codes: list[str] = Field(default_factory=list, alias="commodityCodes")
    focus_food_description: str | None = Field(default=None, alias="focusFoodDescription")
    limit_value: float = Field(alias="limitValue", ge=0.0)
    unit: str
    expression_basis: str | None = Field(default=None, alias="expressionBasis")
    population_scope: str | None = Field(default=None, alias="populationScope")
    document_status: DocumentStatus = Field(alias="documentStatus")
    submission_use: SubmissionUse = Field(alias="submissionUse")
    effective_date: date | None = Field(default=None, alias="effectiveDate")
    notes: list[str] = Field(default_factory=list)


class JurisdictionCoverageRecord(DietaryBaseModel):
    coverage_id: str = Field(alias="coverageId")
    jurisdiction: str
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    substance_key: str = Field(alias="substanceKey")
    coverage_level: JurisdictionCoverageLevel = Field(alias="coverageLevel")
    official_source_ids: list[str] = Field(default_factory=list, alias="officialSourceIds")
    legal_authority_ids: list[str] = Field(default_factory=list, alias="legalAuthorityIds")
    reference_value_record_ids: list[str] = Field(default_factory=list, alias="referenceValueRecordIds")
    enforcement_record_ids: list[str] = Field(default_factory=list, alias="enforcementRecordIds")
    legal_limit_record_ids: list[str] = Field(default_factory=list, alias="legalLimitRecordIds")
    currency_metadata_complete: bool = Field(alias="currencyMetadataComplete")
    gap_reason: str | None = Field(default=None, alias="gapReason")
    notes: list[str] = Field(default_factory=list)


class EmergingContaminantRecord(DietaryBaseModel):
    family_id: ContaminantFamily = Field(alias="familyId")
    display_name: str = Field(alias="displayName")
    jurisdictions: list[str]
    method_maturity_status: MethodMaturityStatus = Field(alias="methodMaturityStatus")
    evidence_support_status: EvidenceSupportStatus = Field(alias="evidenceSupportStatus")
    submission_use: SubmissionUse = Field(alias="submissionUse")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    method_ids: list[str] = Field(default_factory=list, alias="methodIds")
    default_readiness_profile_ids: list[str] = Field(default_factory=list, alias="defaultReadinessProfileIds")
    hard_failure_profiles: list[str] = Field(default_factory=list, alias="hardFailureProfiles")
    notes: list[str] = Field(default_factory=list)


class ModelErratumRecord(DietaryBaseModel):
    erratum_id: str = Field(alias="erratumId")
    title: str
    description: str
    active: bool = True
    blocking: bool = False
    source_id: str | None = Field(default=None, alias="sourceId")
    url: str | None = None


class ModelGovernanceRecord(DietaryBaseModel):
    model_family: ModelFamily = Field(alias="modelFamily")
    jurisdictions: list[str]
    governance_status: GovernanceStatus = Field(alias="governanceStatus")
    submission_allowed: bool = Field(alias="submissionAllowed")
    current_version_label: str = Field(alias="currentVersionLabel")
    dataset_basis: str = Field(alias="datasetBasis")
    source_ids: list[str] = Field(alias="sourceIds")
    required_disclaimers: list[str] = Field(default_factory=list, alias="requiredDisclaimers")
    errata: list[ModelErratumRecord] = Field(default_factory=list)


class RegulatoryReadinessProfile(DietaryBaseModel):
    profile_id: str = Field(alias="profileId")
    display_name: str = Field(alias="displayName")
    jurisdiction: str
    intended_use: str = Field(alias="intendedUse")
    notes: list[str] = Field(default_factory=list)


class ProvenanceBundle(DietaryBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    defaults_version: str = Field(default=DEFAULTS_VERSION)
    algorithm_version: str
    generated_at: datetime
    source_references: list[SourceReference] = Field(default_factory=list)


class CommodityReference(DietaryBaseModel):
    taxonomy_id: str
    commodity_code: str
    canonical_name: str
    food_group: str
    mapping_status: str
    foodex2_code: str | None = None
    rpc_code: str | None = None
    rpcd_code: str | None = None
    processed_status: ProcessedStatus | None = None
    mapping_confidence: MappingConfidence | None = None
    matched_input_code: str | None = None
    source_reference: SourceReference | None = None


class FoodVocabularyCrosswalkRecord(DietaryBaseModel):
    commodity_code: str = Field(alias="commodityCode")
    foodex2_code: str | None = Field(default=None, alias="foodex2Code")
    rpc_code: str | None = Field(default=None, alias="rpcCode")
    rpcd_code: str | None = Field(default=None, alias="rpcdCode")
    processed_status: ProcessedStatus = Field(alias="processedStatus")
    mapping_confidence: MappingConfidence = Field(alias="mappingConfidence")
    source_id: str = Field(alias="sourceId")


class ProcessedCommodityMappingRecord(DietaryBaseModel):
    raw_commodity_code: str = Field(alias="rawCommodityCode")
    processed_commodity_code: str = Field(alias="processedCommodityCode")
    aliases: list[str] = Field(default_factory=list)
    canonical_name: str = Field(alias="canonicalName")
    food_group: str = Field(alias="foodGroup")
    foodex2_code: str | None = Field(default=None, alias="foodex2Code")
    rpc_code: str | None = Field(default=None, alias="rpcCode")
    rpcd_code: str | None = Field(default=None, alias="rpcdCode")
    processed_status: ProcessedStatus = Field(alias="processedStatus")
    mapping_confidence: MappingConfidence = Field(alias="mappingConfidence")
    default_processing_factor: float | None = Field(default=None, alias="defaultProcessingFactor")
    source_id: str = Field(alias="sourceId")


class ProcessingFactorApplicabilityRecord(DietaryBaseModel):
    raw_commodity_code: str = Field(alias="rawCommodityCode")
    processed_commodity_code: str = Field(alias="processedCommodityCode")
    applicability: str
    recommended_processing_factor: float | None = Field(
        default=None,
        alias="recommendedProcessingFactor",
    )
    source_id: str = Field(alias="sourceId")
    note: str | None = None


class PopulationContext(DietaryBaseModel):
    population_group: str
    region_id: str
    body_weight_kg: float = Field(gt=0.0)
    source_profile_id: str


class DietaryAssumptionRecord(DietaryBaseModel):
    parameter: str
    value: float | str
    unit: str | None = None
    source_classification: SourceClassification
    rationale: str
    source_reference: SourceReference | None = None
    quality_flags: list[QualityFlag] = Field(default_factory=list)


class DietaryCommodityResidueInput(DietaryBaseModel):
    commodity_code: str = Field(min_length=1)
    residue_concentration_mg_per_kg: float = Field(gt=0.0)
    lower_bound_mg_per_kg: float | None = Field(default=None, ge=0.0)
    upper_bound_mg_per_kg: float | None = Field(default=None, ge=0.0)
    residue_unit: str = Field(default="mg/kg")
    source_type: ResidueSourceType
    processing_factor: float | None = Field(default=None, gt=0.0)
    region_id: str | None = None
    time_context: str | None = None
    review_status: str = Field(default="reviewed")
    source_reference: SourceReference | None = None

    @field_validator("residue_unit")
    @classmethod
    def validate_residue_unit(cls, value: str) -> str:
        if value != "mg/kg":
            raise ValueError("Dietary MCP v0.1 supports residue inputs in mg/kg only")
        return value

    @model_validator(mode="after")
    def validate_bounds(self) -> "DietaryCommodityResidueInput":
        if self.lower_bound_mg_per_kg is not None and self.lower_bound_mg_per_kg > self.residue_concentration_mg_per_kg:
            raise ValueError("lower residue bound cannot exceed the point estimate")
        if self.upper_bound_mg_per_kg is not None and self.upper_bound_mg_per_kg < self.residue_concentration_mg_per_kg:
            raise ValueError("upper residue bound cannot be lower than the point estimate")
        return self


class DietaryCommodityResidueRecord(ContentHashIdModel):
    _content_hash_id_field = "record_id"
    _content_hash_id_prefix = "residue"
    schema_version: str = Field(default=SCHEMA_VERSION)
    record_id: str = Field(default_factory=lambda: f"residue-{uuid4().hex[:12]}")
    commodity: CommodityReference
    residue_concentration_mg_per_kg: float = Field(gt=0.0)
    lower_bound_mg_per_kg: float | None = Field(default=None, ge=0.0)
    upper_bound_mg_per_kg: float | None = Field(default=None, ge=0.0)
    residue_unit: str = Field(default="mg/kg")
    source_type: ResidueSourceType
    processing_factor: float = Field(gt=0.0)
    processing_factor_source_classification: SourceClassification
    processing_factor_source_reference: SourceReference | None = None
    region_id: str | None = None
    time_context: str | None = None
    review_status: str
    source_reference: SourceReference | None = None
    provenance: ProvenanceBundle
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)

    @field_validator("residue_unit")
    @classmethod
    def validate_residue_unit(cls, value: str) -> str:
        if value != "mg/kg":
            raise ValueError("Dietary MCP v0.1 supports residue records in mg/kg only")
        return value


class DietaryResidueProfile(ContentHashIdModel):
    _content_hash_id_field = "profile_id"
    _content_hash_id_prefix = "residue-profile"
    schema_version: str = Field(default=SCHEMA_VERSION)
    profile_id: str = Field(default_factory=lambda: f"residue-profile-{uuid4().hex[:12]}")
    chemical_identity: dict[str, str]
    region_id: str
    records: list[DietaryCommodityResidueRecord]
    provenance: ProvenanceBundle
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class CommodityConsumptionRecord(DietaryBaseModel):
    commodity: CommodityReference
    acute_kg_per_day: float | None = Field(default=None, ge=0.0)
    chronic_kg_per_day: float | None = Field(default=None, ge=0.0)
    source_reference: SourceReference | None = None

    @model_validator(mode="after")
    def validate_window_coverage(self) -> "CommodityConsumptionRecord":
        if self.acute_kg_per_day is None and self.chronic_kg_per_day is None:
            raise ValueError("consumption records must define at least one intake window")
        return self


class DietaryConsumptionProfile(DietaryBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    profile_id: str
    display_name: str
    population_group: str
    profile_family: str | None = None
    regulatory_basis: str | None = None
    review_status: str | None = None
    survey_profile_source: str
    region_id: str
    body_weight_kg: float = Field(gt=0.0)
    applicable_windows: list[IntakeWindowSemantic]
    intake_unit: str = Field(default="kg_food/day")
    commodity_consumption: list[CommodityConsumptionRecord]
    provenance: ProvenanceBundle
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class DietaryIntakeScenarioDefinition(ContentHashIdModel):
    _content_hash_id_field = "scenario_id"
    _content_hash_id_prefix = "dietary-scenario"
    schema_version: str = Field(default=SCHEMA_VERSION)
    scenario_id: str = Field(default_factory=lambda: f"dietary-scenario-{uuid4().hex[:12]}")
    chemical_identity: dict[str, str]
    scenario_class: ScenarioClass
    model_family: ModelFamily = Field(default=ModelFamily.REFERENCE_DIETARY)
    intake_window_semantic: IntakeWindowSemantic
    fit_for_purpose: FitForPurpose = Field(default=FitForPurpose.SCREENING)
    residue_profile: DietaryResidueProfile
    consumption_profile: DietaryConsumptionProfile
    population_context: PopulationContext
    provenance: ProvenanceBundle
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scenario_semantics(self) -> "DietaryIntakeScenarioDefinition":
        if self.scenario_class == ScenarioClass.BOUNDED_ACUTE and self.intake_window_semantic != IntakeWindowSemantic.ACUTE:
            raise ValueError("bounded_acute scenarios must declare acute semantics")
        if self.scenario_class == ScenarioClass.BOUNDED_CHRONIC and self.intake_window_semantic != IntakeWindowSemantic.CHRONIC:
            raise ValueError("bounded_chronic scenarios must declare chronic semantics")
        if self.intake_window_semantic not in self.consumption_profile.applicable_windows:
            raise ValueError("consumption profile does not support the requested intake window")
        return self


class DietaryContributionRecord(DietaryBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    commodity: CommodityReference
    intake_window_semantic: IntakeWindowSemantic
    residue_concentration_mg_per_kg: float = Field(ge=0.0)
    consumption_kg_per_day: float = Field(ge=0.0)
    applied_processing_factor: float = Field(gt=0.0)
    contribution_mg_per_kg_bw_per_day: float = Field(ge=0.0)
    fraction_of_total: float = Field(ge=0.0, le=1.0)
    lower_bound_intake_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    upper_bound_intake_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class DietaryIntakeSummary(ContentHashIdModel):
    _content_hash_id_field = "summary_id"
    _content_hash_id_prefix = "intake-summary"
    schema_version: str = Field(default=SCHEMA_VERSION)
    summary_id: str = Field(default_factory=lambda: f"intake-summary-{uuid4().hex[:12]}")
    scenario_id: str
    scenario_class: ScenarioClass
    intake_window_semantic: IntakeWindowSemantic
    route: Route = Field(default=Route.ORAL)
    total_intake_mg_per_kg_bw_per_day: float = Field(ge=0.0)
    lower_bound_total_intake_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    upper_bound_total_intake_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    metric_label: str = Field(default="external_oral_dose_mg_per_kg_bw_per_day")
    population_group: str
    region_id: str
    body_weight_kg: float = Field(gt=0.0)
    fit_for_purpose: FitForPurpose
    commodity_contributions: list[DietaryContributionRecord]
    dominant_commodity_contributors: list[DietaryContributionRecord]
    assumptions_applied: list[DietaryAssumptionRecord]
    provenance: ProvenanceBundle
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)
    result_metadata: ResultMetadata


class AdapterImportDeclaredTotals(DietaryBaseModel):
    total_intake_mg_per_kg_bw_per_day: float = Field(ge=0.0)
    lower_bound_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    upper_bound_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)


class AdapterImportHeaderResolution(DietaryBaseModel):
    header: str
    canonical_field: str | None = None
    recognized: bool


class AdapterNormalizedProjectionContribution(DietaryBaseModel):
    commodity_code: str
    canonical_name: str
    foodex2_code: str | None = None
    rpc_code: str | None = None
    rpcd_code: str | None = None
    processed_status: ProcessedStatus | None = None
    mapping_confidence: MappingConfidence | None = None
    contribution_mg_per_kg_bw_per_day: float = Field(ge=0.0)
    fraction_of_total: float = Field(ge=0.0, le=1.0)
    residue_concentration_mg_per_kg: float = Field(ge=0.0)
    consumption_kg_per_day: float = Field(ge=0.0)
    applied_processing_factor: float = Field(gt=0.0)
    lower_bound_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    upper_bound_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)


class AdapterNormalizedProjection(DietaryBaseModel):
    scenario_class: ScenarioClass
    intake_window: IntakeWindowSemantic
    population_group: str
    region_id: str
    body_weight_kg: float = Field(gt=0.0)
    total_intake_mg_per_kg_bw_per_day: float = Field(ge=0.0)
    lower_bound_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    upper_bound_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    commodity_codes: list[str]
    commodity_contributions: list[AdapterNormalizedProjectionContribution]
    dominant_commodity_codes: list[str]
    source_ids: list[str]
    quality_flag_codes: list[str]
    limitation_codes: list[str]
    assumption_parameters: list[str]


class CommodityContributionDelta(DietaryBaseModel):
    commodity: CommodityReference
    base_value: float
    candidate_value: float
    absolute_delta: float
    relative_delta: float | None = None


class DietaryScenarioComparisonRecord(ContentHashIdModel):
    _content_hash_id_field = "comparison_id"
    _content_hash_id_prefix = "comparison"
    schema_version: str = Field(default=SCHEMA_VERSION)
    comparison_id: str = Field(default_factory=lambda: f"comparison-{uuid4().hex[:12]}")
    base_scenario_id: str
    candidate_scenario_id: str
    intake_window_semantic: IntakeWindowSemantic
    base_total_intake_mg_per_kg_bw_per_day: float
    candidate_total_intake_mg_per_kg_bw_per_day: float
    intake_delta_mg_per_kg_bw_per_day: float
    lower_bound_delta_mg_per_kg_bw_per_day: float | None = None
    upper_bound_delta_mg_per_kg_bw_per_day: float | None = None
    contribution_deltas: list[CommodityContributionDelta]
    changed_assumptions: list[str]
    dominant_drivers: list[str]
    provenance: ProvenanceBundle
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class RouteDoseEstimate(ContentHashIdModel):
    _content_hash_id_field = "estimate_id"
    _content_hash_id_prefix = "route-dose"
    schema_version: str = Field(default=SCHEMA_VERSION)
    estimate_id: str = Field(default_factory=lambda: f"route-dose-{uuid4().hex[:12]}")
    scenario_id: str
    chemical_identity: dict[str, str]
    route: Route = Field(default=Route.ORAL)
    dose_metric: str = Field(default="external_oral_dose_mg_per_kg_bw_per_day")
    intake_window_semantic: IntakeWindowSemantic
    value_mg_per_kg_bw_per_day: float = Field(ge=0.0)
    lower_bound_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    upper_bound_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    fit_for_purpose: FitForPurpose
    provenance: ProvenanceBundle
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class ExposurePlausibilityRecord(DietaryBaseModel):
    schema_version: str = Field(default="exposurePlausibilityRecord.v1", alias="schemaVersion")
    record_id: str | None = Field(default=None, alias="recordId")
    chemical_id: str | None = Field(default=None, alias="chemicalId")
    chemical_name: str | None = Field(default=None, alias="chemicalName")
    classification: str
    decision_effect: str = Field(alias="decisionEffect")
    ratio_to_human_exposure: float | None = Field(default=None, alias="ratioToHumanExposure")
    rationale: str


class DependencyDescriptor(DietaryBaseModel):
    name: str
    version: str
    role: str


class PbpkDosingRegimen(DietaryBaseModel):
    schedule: str
    dose_frequency_per_day: float = Field(gt=0.0)
    duration_days: float | None = Field(default=None, gt=0.0)


class PbpkExternalImportBundle(ContentHashIdModel):
    _content_hash_id_field = "bundle_id"
    _content_hash_id_prefix = "pbpk-bundle"
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_id: str = Field(default_factory=lambda: f"pbpk-bundle-{uuid4().hex[:12]}")
    route_dose_estimate: RouteDoseEstimate
    dosing_regimen: PbpkDosingRegimen
    dependencies: list[DependencyDescriptor]
    exposure_plausibility_records: list[ExposurePlausibilityRecord] = Field(
        default_factory=list,
        alias="exposurePlausibilityRecords",
    )
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)
    quality_flags: list[QualityFlag] = Field(default_factory=list)


class ToxclawEvidenceItem(DietaryBaseModel):
    label: str
    source_reference: SourceReference


class ToxclawDietaryEvidenceBundle(ContentHashIdModel):
    _content_hash_id_field = "bundle_id"
    _content_hash_id_prefix = "toxclaw-bundle"
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_id: str = Field(default_factory=lambda: f"toxclaw-bundle-{uuid4().hex[:12]}")
    scenario: DietaryIntakeScenarioDefinition
    summary: DietaryIntakeSummary
    route_dose_estimate: RouteDoseEstimate
    assumptions: list[DietaryAssumptionRecord]
    evidence_items: list[ToxclawEvidenceItem]
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)
    quality_flags: list[QualityFlag] = Field(default_factory=list)


class EvaluateGlobalTradeRiskRequest(DietaryBaseModel):
    chemical_identity: dict[str, str]
    contaminant_family: ContaminantFamily = Field(default=ContaminantFamily.PESTICIDE_RESIDUE)
    residue_records: list[DietaryCommodityResidueInput] = Field(max_length=MAX_RESIDUE_RECORDS)
    target_jurisdictions: list[str] = Field(
        default_factory=lambda: ["eu", "us", "codex_global"],
        max_length=MAX_TARGET_JURISDICTIONS,
    )


class JurisdictionRiskProfile(DietaryBaseModel):
    jurisdiction: str
    mrl_violations: list[QualityFlag] = Field(default_factory=list)
    applicable_reference_values: list[ReferenceValueRecord] = Field(default_factory=list)
    trade_status: str
    status_reason: str | None = Field(default=None, alias="statusReason")
    mrl_coverage_status: TradeMrlCoverageStatus = Field(
        default=TradeMrlCoverageStatus.UNSCOPED_LOOKUP,
        alias="mrlCoverageStatus",
    )
    mrl_curated_support_types: list[str] = Field(default_factory=list, alias="mrlCuratedSupportTypes")
    mrl_curated_scope_commodity_codes: list[str] = Field(
        default_factory=list,
        alias="mrlCuratedScopeCommodityCodes",
    )
    reference_value_jurisdiction_status: ReferenceValueJurisdictionStatus = Field(
        default=ReferenceValueJurisdictionStatus.UNSCOPED_LOOKUP,
        alias="referenceValueJurisdictionStatus",
    )
    reference_value_curated_support_types: list[str] = Field(
        default_factory=list,
        alias="referenceValueCuratedSupportTypes",
    )
    coverage_summaries: list[JurisdictionCoverageRecord] = Field(default_factory=list, alias="coverageSummaries")
    quality_flags: list[QualityFlag] = Field(default_factory=list, alias="qualityFlags")
    notes: list[str] = Field(default_factory=list)


class GlobalTradeRiskReport(DietaryBaseModel):
    chemical_identity: dict[str, str]
    resolved_substance_key: str | None = Field(default=None, alias="resolvedSubstanceKey")
    jurisdiction_profiles: list[JurisdictionRiskProfile]
    quality_flags: list[QualityFlag] = Field(default_factory=list, alias="qualityFlags")
    notes: list[str] = Field(default_factory=list)


class TradeRiskReviewPrompt(DietaryBaseModel):
    prompt_id: str = Field(alias="promptId")
    jurisdiction: str
    category: str
    prompt: str
    linked_record_ids: list[str] = Field(default_factory=list, alias="linkedRecordIds")


class ExportTradeRiskReviewBundleRequest(DietaryBaseModel):
    trade_report: GlobalTradeRiskReport = Field(alias="tradeReport")
    bundle_note: str | None = Field(default=None, alias="bundleNote")


class TradeRiskReviewBundle(ContentHashIdModel):
    _content_hash_id_field = "bundle_id"
    _content_hash_id_prefix = "trade-risk-review-bundle"
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_id: str = Field(default_factory=lambda: f"trade-risk-review-bundle-{uuid4().hex[:12]}", alias="bundleId")
    bundle_profile: BundleProfile = Field(default=BundleProfile.INTERNAL_REVIEW, alias="bundleProfile")
    review_status: str = Field(alias="reviewStatus")
    trade_report: GlobalTradeRiskReport = Field(alias="tradeReport")
    covered_source_ids: list[str] = Field(default_factory=list, alias="coveredSourceIds")
    review_prompts: list[TradeRiskReviewPrompt] = Field(default_factory=list, alias="reviewPrompts")
    documentation_resource_uri: str = Field(default="docs://trade-risk-review", alias="documentationResourceUri")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    dependencies: list[DependencyDescriptor] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ExportVersionPinnedTradeRiskReviewDossierRequest(DietaryBaseModel):
    review_bundle: TradeRiskReviewBundle = Field(alias="reviewBundle")


class VersionPinnedTradeRiskReviewDossier(ContentHashIdModel):
    _content_hash_id_field = "dossier_id"
    _content_hash_id_prefix = "trade-risk-review-dossier"
    schema_version: str = Field(default=SCHEMA_VERSION)
    dossier_id: str = Field(default_factory=lambda: f"trade-risk-review-dossier-{uuid4().hex[:12]}", alias="dossierId")
    bundle_profile: BundleProfile = Field(default=BundleProfile.INTERNAL_REVIEW, alias="bundleProfile")
    dossier_status: str = Field(alias="dossierStatus")
    review_bundle: TradeRiskReviewBundle = Field(alias="reviewBundle")
    release_metadata: ReleaseMetadataSnapshot = Field(alias="releaseMetadata")
    source_governance_snapshot: list[RegulatorySourceRecord] = Field(
        default_factory=list,
        alias="sourceGovernanceSnapshot",
    )
    pinned_resources: list[PinnedResourceFingerprint] = Field(default_factory=list, alias="pinnedResources")
    confidentiality_annotations: list[ConfidentialityAnnotation] = Field(
        default_factory=list,
        alias="confidentialityAnnotations",
    )
    limitations: list[LimitationNote] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SanitisedPublicTradeJurisdictionRiskProfile(DietaryBaseModel):
    jurisdiction: str
    mrl_violations: list[QualityFlag] = Field(default_factory=list, alias="mrlViolations")
    trade_status: str = Field(alias="tradeStatus")
    status_reason: str | None = Field(default=None, alias="statusReason")
    mrl_coverage_status: TradeMrlCoverageStatus = Field(
        default=TradeMrlCoverageStatus.UNSCOPED_LOOKUP,
        alias="mrlCoverageStatus",
    )
    mrl_curated_support_types: list[str] = Field(default_factory=list, alias="mrlCuratedSupportTypes")
    mrl_curated_scope_commodity_codes: list[str] = Field(
        default_factory=list,
        alias="mrlCuratedScopeCommodityCodes",
    )
    reference_value_jurisdiction_status: ReferenceValueJurisdictionStatus = Field(
        default=ReferenceValueJurisdictionStatus.UNSCOPED_LOOKUP,
        alias="referenceValueJurisdictionStatus",
    )
    reference_value_curated_support_types: list[str] = Field(
        default_factory=list,
        alias="referenceValueCuratedSupportTypes",
    )
    quality_flags: list[QualityFlag] = Field(default_factory=list, alias="qualityFlags")
    notes: list[str] = Field(default_factory=list)


class SanitisedPublicTradeRiskReport(DietaryBaseModel):
    jurisdiction_profiles: list[SanitisedPublicTradeJurisdictionRiskProfile] = Field(
        default_factory=list,
        alias="jurisdictionProfiles",
    )
    quality_flags: list[QualityFlag] = Field(default_factory=list, alias="qualityFlags")
    notes: list[str] = Field(default_factory=list)


class BuildDietaryResidueProfileRequest(DietaryBaseModel):
    chemical_identity: dict[str, str]
    region_id: str = Field(default="eu_screening_default")
    residue_records: list[DietaryCommodityResidueInput] = Field(max_length=MAX_RESIDUE_RECORDS)


class SelectConsumptionProfileRequest(DietaryBaseModel):
    region_id: str = Field(default="eu_screening_default")
    population_group: str
    intake_window: IntakeWindowSemantic
    required_commodity_codes: list[str] = Field(
        default_factory=list,
        max_length=MAX_REQUIRED_COMMODITY_CODES,
    )
    preferred_profile_id: str | None = None


class RawSurveyRecordInput(DietaryBaseModel):
    subject_id: str = Field(alias="subjectId")
    body_weight_kg: float = Field(alias="bodyWeightKg", gt=0.0)
    days_in_survey: int = Field(alias="daysInSurvey", ge=1)
    commodity_code: str = Field(alias="commodityCode")
    consumption_kg_per_day: float = Field(alias="consumptionKgPerDay", ge=0.0)
    survey_weight: float | None = Field(default=None, alias="surveyWeight", gt=0.0)
    sampling_stratum: str | None = Field(default=None, alias="samplingStratum")
    sampling_cluster: str | None = Field(default=None, alias="samplingCluster")
    survey_day_id: str | None = Field(default=None, alias="surveyDayId")


class DietarySurveyDatasetRecord(DietaryBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    dataset_id: str = Field(alias="datasetId")
    region_id: str = Field(alias="regionId")
    population_group: str = Field(alias="populationGroup")
    records: list[RawSurveyRecordInput] = Field(max_length=MAX_RAW_SURVEY_RECORDS)
    dropped_record_count: int = Field(default=0, alias="droppedRecordCount", ge=0)
    data_loss_fraction: float = Field(default=0.0, alias="dataLossFraction", ge=0.0, le=1.0)
    unmapped_commodity_codes: list[str] = Field(default_factory=list, alias="unmappedCommodityCodes")
    body_weight_conflict_subject_ids: list[str] = Field(
        default_factory=list,
        alias="bodyWeightConflictSubjectIds",
    )
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class ParseRawSurveyDatasetRequest(DietaryBaseModel):
    dataset_id: str = Field(alias="datasetId")
    region_id: str = Field(alias="regionId")
    population_group: str = Field(alias="populationGroup")
    raw_records: list[RawSurveyRecordInput] = Field(alias="rawRecords", max_length=MAX_RAW_SURVEY_RECORDS)


class SummarizeSurveyDistributionRequest(DietaryBaseModel):
    dataset: DietarySurveyDatasetRecord
    residue_profile: DietaryResidueProfile


class SurveyDistributionSummaryReport(DietaryBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    dataset_id: str = Field(alias="datasetId")
    population_group: str = Field(alias="populationGroup")
    chemical_identity: dict[str, str] = Field(alias="chemicalIdentity")
    total_subjects: int = Field(alias="totalSubjects")
    consumers_only_count: int = Field(alias="consumersOnlyCount")
    zero_intake_prevalence: float = Field(alias="zeroIntakePrevalence")
    mean_intake_mg_per_kg_bw_per_day: float = Field(alias="meanIntakeMgPerKgBwPerDay")
    percentile_95_mg_per_kg_bw_per_day: float = Field(alias="percentile95MgPerKgBwPerDay")
    percentile_99_mg_per_kg_bw_per_day: float = Field(alias="percentile99MgPerKgBwPerDay")
    percentile_99_9_mg_per_kg_bw_per_day: float = Field(alias="percentile999MgPerKgBwPerDay")
    max_mg_per_kg_bw_per_day: float = Field(alias="maxMgPerKgBwPerDay")
    consumers_only_mean_mg_per_kg_bw_per_day: float | None = Field(
        default=None,
        alias="consumersOnlyMeanMgPerKgBwPerDay",
    )
    consumers_only_percentile_95_mg_per_kg_bw_per_day: float | None = Field(
        default=None,
        alias="consumersOnlyPercentile95MgPerKgBwPerDay",
    )
    consumers_only_percentile_99_mg_per_kg_bw_per_day: float | None = Field(
        default=None,
        alias="consumersOnlyPercentile99MgPerKgBwPerDay",
    )
    consumers_only_percentile_99_9_mg_per_kg_bw_per_day: float | None = Field(
        default=None,
        alias="consumersOnlyPercentile999MgPerKgBwPerDay",
    )
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class BuildProbabilisticIntakeSummaryRequest(DietaryBaseModel):
    dataset: DietarySurveyDatasetRecord
    residue_profile: DietaryResidueProfile
    iteration_count: int = Field(
        default=10000,
        alias="iterationCount",
        ge=100,
        le=MAX_PROBABILISTIC_ITERATIONS,
    )
    random_seed: int = Field(default=42, alias="randomSeed")


class ResidueUncertaintyModel(DietaryBaseModel):
    commodity_code: str = Field(alias="commodityCode")
    distribution: ResidueUncertaintyDistribution
    point_mg_per_kg: float | None = Field(default=None, alias="pointMgPerKg", ge=0.0)
    empirical_values_mg_per_kg: list[float] = Field(
        default_factory=list,
        alias="empiricalValuesMgPerKg",
        min_length=0,
        max_length=10_000,
    )
    min_mg_per_kg: float | None = Field(default=None, alias="minMgPerKg", ge=0.0)
    mode_mg_per_kg: float | None = Field(default=None, alias="modeMgPerKg", ge=0.0)
    max_mg_per_kg: float | None = Field(default=None, alias="maxMgPerKg", ge=0.0)
    geometric_mean_mg_per_kg: float | None = Field(default=None, alias="geometricMeanMgPerKg", gt=0.0)
    geometric_sd: float | None = Field(default=None, alias="geometricSd", gt=1.0)
    lod_mg_per_kg: float | None = Field(default=None, alias="lodMgPerKg", ge=0.0)
    loq_mg_per_kg: float | None = Field(default=None, alias="loqMgPerKg", ge=0.0)
    processing_factor_cv: float | None = Field(default=None, alias="processingFactorCv", ge=0.0)

    @field_validator("empirical_values_mg_per_kg")
    @classmethod
    def validate_empirical_values(cls, values: list[float]) -> list[float]:
        if any(value < 0.0 or not math.isfinite(value) for value in values):
            raise ValueError("empirical residue values must be finite non-negative numbers")
        return values

    @model_validator(mode="after")
    def validate_distribution_parameters(self) -> "ResidueUncertaintyModel":
        if self.distribution == ResidueUncertaintyDistribution.EMPIRICAL and not self.empirical_values_mg_per_kg:
            raise ValueError("empirical residue uncertainty models require empiricalValuesMgPerKg")
        if self.distribution == ResidueUncertaintyDistribution.UNIFORM:
            if self.min_mg_per_kg is None or self.max_mg_per_kg is None:
                raise ValueError("uniform residue uncertainty models require minMgPerKg and maxMgPerKg")
            if self.min_mg_per_kg > self.max_mg_per_kg:
                raise ValueError("uniform residue uncertainty minMgPerKg cannot exceed maxMgPerKg")
        if self.distribution == ResidueUncertaintyDistribution.TRIANGULAR:
            if self.min_mg_per_kg is None or self.mode_mg_per_kg is None or self.max_mg_per_kg is None:
                raise ValueError("triangular residue uncertainty models require min, mode, and max")
            if not self.min_mg_per_kg <= self.mode_mg_per_kg <= self.max_mg_per_kg:
                raise ValueError("triangular residue uncertainty requires min <= mode <= max")
        if self.distribution in {
            ResidueUncertaintyDistribution.LOGNORMAL,
            ResidueUncertaintyDistribution.CENSORED_LOGNORMAL,
        }:
            if self.geometric_mean_mg_per_kg is None or self.geometric_sd is None:
                raise ValueError("lognormal residue uncertainty models require geometric mean and sd")
        if self.distribution == ResidueUncertaintyDistribution.CENSORED_LOGNORMAL:
            if self.lod_mg_per_kg is None and self.loq_mg_per_kg is None:
                raise ValueError("censored lognormal models require lodMgPerKg or loqMgPerKg")
            if (
                self.lod_mg_per_kg is not None
                and self.loq_mg_per_kg is not None
                and self.lod_mg_per_kg > self.loq_mg_per_kg
            ):
                raise ValueError("lodMgPerKg cannot exceed loqMgPerKg")
        return self


class HealthReference(DietaryBaseModel):
    reference_type: HealthReferenceType = Field(alias="referenceType")
    value: float = Field(gt=0.0)
    unit: str = Field(default="mg/kg bw/day")
    source_id: str | None = Field(default=None, alias="sourceId")


class BuildUncertaintyIntakeAssessmentRequest(DietaryBaseModel):
    dataset: DietarySurveyDatasetRecord
    residue_profile: DietaryResidueProfile
    assessment_mode: UncertaintyAssessmentMode = Field(
        default=UncertaintyAssessmentMode.TWO_DIMENSIONAL_MONTE_CARLO,
        alias="assessmentMode",
    )
    random_seed: int = Field(alias="randomSeed")
    outer_iteration_count: int = Field(
        default=1000,
        alias="outerIterationCount",
        ge=10,
        le=MAX_UNCERTAINTY_OUTER_ITERATIONS,
    )
    inner_iteration_count: int = Field(
        default=1000,
        alias="innerIterationCount",
        ge=10,
        le=MAX_UNCERTAINTY_INNER_ITERATIONS,
    )
    residue_uncertainty_models: list[ResidueUncertaintyModel] = Field(
        alias="residueUncertaintyModels",
        min_length=1,
        max_length=MAX_RESIDUE_RECORDS,
    )
    censored_data_policy: CensoredDataPolicy = Field(
        default=CensoredDataPolicy.THREE_BOUND_SENSITIVITY,
        alias="censoredDataPolicy",
    )
    health_reference: HealthReference | None = Field(default=None, alias="healthReference")


class UncertaintyMetricInterval(DietaryBaseModel):
    median: float
    lower_95: float = Field(alias="lower95")
    upper_95: float = Field(alias="upper95")


class UncertaintyDistributionSummary(DietaryBaseModel):
    mean: UncertaintyMetricInterval
    percentile_95: UncertaintyMetricInterval = Field(alias="percentile95")
    percentile_99: UncertaintyMetricInterval = Field(alias="percentile99")
    percentile_99_9: UncertaintyMetricInterval = Field(alias="percentile999")
    max: UncertaintyMetricInterval
    consumers_only_mean: UncertaintyMetricInterval | None = Field(default=None, alias="consumersOnlyMean")
    consumers_only_percentile_95: UncertaintyMetricInterval | None = Field(
        default=None,
        alias="consumersOnlyPercentile95",
    )


class HealthReferenceExceedanceSummary(DietaryBaseModel):
    reference_type: HealthReferenceType = Field(alias="referenceType")
    reference_value: float = Field(alias="referenceValue")
    reference_unit: str = Field(alias="referenceUnit")
    exceedance_probability: UncertaintyMetricInterval = Field(alias="exceedanceProbability")
    percent_of_reference: UncertaintyMetricInterval | None = Field(default=None, alias="percentOfReference")
    high_percentile_metric: str | None = Field(default=None, alias="highPercentileMetric")
    high_percentile_exposure_ratio: UncertaintyMetricInterval | None = Field(
        default=None,
        alias="highPercentileExposureRatio",
    )
    margin_of_exposure: UncertaintyMetricInterval | None = Field(default=None, alias="marginOfExposure")


class SensitivityRankingRecord(DietaryBaseModel):
    input_name: str = Field(alias="inputName")
    metric: str
    rank_correlation: float = Field(alias="rankCorrelation")
    method: str = Field(default="spearman")


class UncertaintyAssumptionLedgerEntry(DietaryBaseModel):
    code: str
    severity: Severity
    category: str
    message: str
    conservative: bool | None = None


class UncertaintyAssumptionLedger(DietaryBaseModel):
    entries: list[UncertaintyAssumptionLedgerEntry] = Field(default_factory=list)


class UncertaintyReproducibilityRecord(DietaryBaseModel):
    random_seed: int = Field(alias="randomSeed")
    rng_algorithm: str = Field(alias="rngAlgorithm")
    model_fingerprint: str = Field(alias="modelFingerprint")
    input_fingerprint: str = Field(alias="inputFingerprint")
    simulation_fingerprint: str = Field(alias="simulationFingerprint")
    numpy_version: str = Field(alias="numpyVersion")
    scipy_version: str = Field(alias="scipyVersion")


class UncertaintyIntakeAssessment(ContentHashIdModel):
    _content_hash_id_field = "assessment_id"
    _content_hash_id_prefix = "uncertainty-assessment"
    schema_version: str = Field(default=SCHEMA_VERSION)
    assessment_id: str = Field(
        default_factory=lambda: f"uncertainty-assessment-{uuid4().hex[:12]}",
        alias="assessmentId",
    )
    dataset_id: str = Field(alias="datasetId")
    population_group: str = Field(alias="populationGroup")
    chemical_identity: dict[str, str] = Field(alias="chemicalIdentity")
    assessment_mode: UncertaintyAssessmentMode = Field(alias="assessmentMode")
    outer_iteration_count: int = Field(alias="outerIterationCount")
    inner_iteration_count: int = Field(alias="innerIterationCount")
    total_subjects: int = Field(alias="totalSubjects")
    weighted_sampling: bool = Field(alias="weightedSampling")
    censored_data_policy: CensoredDataPolicy = Field(alias="censoredDataPolicy")
    distribution_summary: UncertaintyDistributionSummary = Field(alias="distributionSummary")
    censored_policy_summaries: dict[str, UncertaintyDistributionSummary] = Field(
        default_factory=dict,
        alias="censoredPolicySummaries",
    )
    health_reference_exceedance: HealthReferenceExceedanceSummary | None = Field(
        default=None,
        alias="healthReferenceExceedance",
    )
    sensitivity_ranking: list[SensitivityRankingRecord] = Field(default_factory=list, alias="sensitivityRanking")
    uncertainty_assumption_ledger: UncertaintyAssumptionLedger = Field(alias="uncertaintyAssumptionLedger")
    reproducibility: UncertaintyReproducibilityRecord
    quality_flags: list[QualityFlag] = Field(default_factory=list, alias="qualityFlags")
    limitations: list[LimitationNote] = Field(default_factory=list)
    provenance: ProvenanceBundle


class ProbabilisticIntakeSummary(ContentHashIdModel):
    _content_hash_id_field = "summary_id"
    _content_hash_id_prefix = "probabilistic-summary"
    schema_version: str = Field(default=SCHEMA_VERSION)
    summary_id: str = Field(default_factory=lambda: f"probabilistic-summary-{uuid4().hex[:12]}", alias="summaryId")
    dataset_id: str = Field(alias="datasetId")
    population_group: str = Field(alias="populationGroup")
    chemical_identity: dict[str, str] = Field(alias="chemicalIdentity")
    iteration_count: int = Field(alias="iterationCount")
    random_seed: int = Field(alias="randomSeed")
    cohort_fingerprint: str = Field(alias="cohortFingerprint")
    total_subjects: int = Field(alias="totalSubjects")
    consumers_only_count: int = Field(alias="consumersOnlyCount")
    zero_intake_prevalence: float = Field(alias="zeroIntakePrevalence")
    mean_intake_mg_per_kg_bw_per_day: float = Field(alias="meanIntakeMgPerKgBwPerDay")
    percentile_95_mg_per_kg_bw_per_day: float = Field(alias="percentile95MgPerKgBwPerDay")
    percentile_99_mg_per_kg_bw_per_day: float = Field(alias="percentile99MgPerKgBwPerDay")
    percentile_99_9_mg_per_kg_bw_per_day: float = Field(alias="percentile999MgPerKgBwPerDay")
    max_mg_per_kg_bw_per_day: float = Field(alias="maxMgPerKgBwPerDay")
    consumers_only_mean_mg_per_kg_bw_per_day: float | None = Field(default=None, alias="consumersOnlyMeanMgPerKgBwPerDay")
    consumers_only_percentile_95_mg_per_kg_bw_per_day: float | None = Field(default=None, alias="consumersOnlyPercentile95MgPerKgBwPerDay")
    consumers_only_percentile_99_mg_per_kg_bw_per_day: float | None = Field(default=None, alias="consumersOnlyPercentile99MgPerKgBwPerDay")
    consumers_only_percentile_99_9_mg_per_kg_bw_per_day: float | None = Field(default=None, alias="consumersOnlyPercentile999MgPerKgBwPerDay")
    quality_flags: list[QualityFlag] = Field(default_factory=list, alias="qualityFlags")
    limitations: list[LimitationNote] = Field(default_factory=list)
    provenance: ProvenanceBundle


class ConsumptionProfileSelectionResult(DietaryBaseModel):
    profile: DietaryConsumptionProfile
    matched_commodities: list[str]
    missing_commodities: list[str]
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class BuildDietaryIntakeScenarioRequest(DietaryBaseModel):
    chemical_identity: dict[str, str]
    residue_profile: DietaryResidueProfile
    consumption_profile: DietaryConsumptionProfile
    scenario_class: ScenarioClass = Field(default=ScenarioClass.POINT_ESTIMATE)
    intake_window_semantic: IntakeWindowSemantic = Field(default=IntakeWindowSemantic.CHRONIC)
    fit_for_purpose: FitForPurpose = Field(default=FitForPurpose.SCREENING)
    model_family: ModelFamily = Field(default=ModelFamily.REFERENCE_DIETARY)


class BuildBoundedIntakeSummaryRequest(DietaryBaseModel):
    scenario: DietaryIntakeScenarioDefinition


class AssessResidueEvidenceFitRequest(DietaryBaseModel):
    residue_profile: DietaryResidueProfile
    consumption_profile: DietaryConsumptionProfile
    scenario_class: ScenarioClass = Field(default=ScenarioClass.POINT_ESTIMATE)


class ResidueEvidenceFitAssessment(DietaryBaseModel):
    fit_score: float = Field(ge=0.0, le=1.0)
    coverage_fraction: float = Field(ge=0.0, le=1.0)
    verdict: str
    reasons: list[str]
    quality_flags: list[QualityFlag] = Field(default_factory=list)


class ApplyResidueEvidenceRequest(DietaryBaseModel):
    residue_profile: DietaryResidueProfile
    additional_records: list[DietaryCommodityResidueInput] = Field(max_length=MAX_RESIDUE_RECORDS)
    override_existing: bool = Field(default=True)


class ResidueEvidenceApplicationResult(DietaryBaseModel):
    residue_profile: DietaryResidueProfile
    applied_assumptions: list[DietaryAssumptionRecord]
    notes: list[str]


class ReconcileResidueEvidenceRequest(DietaryBaseModel):
    chemical_identity: dict[str, str]
    region_id: str = Field(default="eu_screening_default")
    evidence_profiles: list[DietaryResidueProfile]
    strategy: str = Field(default="mean_with_range")


class ResidueEvidenceReconciliationResult(DietaryBaseModel):
    reconciled_profile: DietaryResidueProfile
    agreed_commodities: list[str]
    conflicts: list[str]
    recommended_next_actions: list[str]


class CompareDietaryScenariosRequest(DietaryBaseModel):
    base_summary: DietaryIntakeSummary
    candidate_summary: DietaryIntakeSummary


class CheckAdapterImportRequest(DietaryBaseModel):
    model_family: ModelFamily
    region_id: str = Field(default="eu_screening_default")
    population_group: str
    intake_window: IntakeWindowSemantic
    scenario_class: ScenarioClass
    chemical_identity: dict[str, str]
    residue_records: list[DietaryCommodityResidueInput] = Field(max_length=MAX_RESIDUE_RECORDS)
    external_engine_version: str = Field(min_length=1)
    external_case_id: str = Field(default="adapter-import-check", min_length=1)
    declared_total_intake_mg_per_kg_bw_per_day: float = Field(ge=0.0)
    declared_lower_bound_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    declared_upper_bound_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    csv_text: str = Field(min_length=1, max_length=MAX_CSV_TEXT_LENGTH)
    fit_for_purpose: FitForPurpose = Field(default=FitForPurpose.SCREENING)

    @model_validator(mode="after")
    def validate_model_family(self) -> "CheckAdapterImportRequest":
        if self.model_family == ModelFamily.REFERENCE_DIETARY:
            raise ValueError("adapter import checks require an adapter model family")
        return self


class AdapterImportCheckProfileSelection(DietaryBaseModel):
    region_id: str
    population_group: str
    intake_window: IntakeWindowSemantic
    scenario_class: ScenarioClass


class AdapterImportCheckResult(DietaryBaseModel):
    status: str = Field(default="ok")
    model_family: ModelFamily
    input_mode: str = Field(default="csv_v1")
    template_name: str
    walkthrough_name: str | None = None
    template_resource_uri: str
    documentation_resource_uri: str = Field(default="docs://adapter-import-walkthroughs")
    profile_selection: AdapterImportCheckProfileSelection
    chemical_identity: dict[str, str]
    declared_totals: AdapterImportDeclaredTotals
    input_headers: list[str]
    header_resolution: list[AdapterImportHeaderResolution]
    unmapped_headers: list[str] = Field(default_factory=list)
    normalized_projection: AdapterNormalizedProjection
    notes: list[str] = Field(default_factory=list)


class CompareAdapterImportToWalkthroughRequest(DietaryBaseModel):
    check_result: AdapterImportCheckResult
    walkthrough_name: str = Field(min_length=1)
    numeric_tolerance: float = Field(default=1e-12, ge=0.0)


class AdapterImportWalkthroughComparisonField(DietaryBaseModel):
    field: str
    matches: bool
    observed: dict | list[str] | float | str | bool | None = None
    expected: dict | list[str] | float | str | bool | None = None
    note: str | None = None


class CompareAdapterImportToWalkthroughResult(DietaryBaseModel):
    status: str
    walkthrough_name: str
    walkthrough_resource_uri: str
    template_name: str
    model_family: ModelFamily
    compared_fields: list[AdapterImportWalkthroughComparisonField]
    matched_fields: list[str]
    mismatch_fields: list[str]
    notes: list[str] = Field(default_factory=list)


class ExportAdapterReviewBundleRequest(DietaryBaseModel):
    check_result: AdapterImportCheckResult
    comparison_result: CompareAdapterImportToWalkthroughResult


class ConfidentialityAnnotation(DietaryBaseModel):
    target_path: str = Field(alias="targetPath")
    target_kind: str = Field(alias="targetKind")
    confidentiality_tag: ConfidentialityTag = Field(alias="confidentialityTag")
    rationale: str


class SanitisationRecord(DietaryBaseModel):
    target_path: str = Field(alias="targetPath")
    target_kind: str = Field(alias="targetKind")
    confidentiality_tag: ConfidentialityTag = Field(alias="confidentialityTag")
    sanitisation_state: SanitisationState = Field(alias="sanitisationState")
    replacement_marker: dict[str, str] | None = Field(default=None, alias="replacementMarker")
    note: str | None = None


class ReviewResourceReference(DietaryBaseModel):
    role: str
    uri: str
    description: str
    confidentiality_tag: ConfidentialityTag = Field(
        default=ConfidentialityTag.PUBLIC,
        alias="confidentialityTag",
    )
    sanitisation_state: SanitisationState = Field(
        default=SanitisationState.RETAINED,
        alias="sanitisationState",
    )


class AdapterReviewBundle(ContentHashIdModel):
    _content_hash_id_field = "bundle_id"
    _content_hash_id_prefix = "adapter-review-bundle"
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_id: str = Field(default_factory=lambda: f"adapter-review-bundle-{uuid4().hex[:12]}")
    bundle_profile: BundleProfile = Field(default=BundleProfile.INTERNAL_REVIEW, alias="bundleProfile")
    review_status: str
    model_family: ModelFamily
    template_name: str
    walkthrough_name: str
    check_result: AdapterImportCheckResult
    comparison_result: CompareAdapterImportToWalkthroughResult
    referenced_resources: list[ReviewResourceReference]
    dependencies: list[DependencyDescriptor]
    matched_field_count: int = Field(ge=0)
    mismatch_field_count: int = Field(ge=0)
    confidentiality_annotations: list[ConfidentialityAnnotation] = Field(
        default_factory=list,
        alias="confidentialityAnnotations",
    )
    limitations: list[LimitationNote] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ExportVersionPinnedAdapterReviewDossierRequest(DietaryBaseModel):
    review_bundle: AdapterReviewBundle


class PinnedResourceFingerprint(DietaryBaseModel):
    role: str
    uri: str
    sha256: str
    description: str
    confidentiality_tag: ConfidentialityTag = Field(
        default=ConfidentialityTag.PUBLIC,
        alias="confidentialityTag",
    )
    sanitisation_state: SanitisationState = Field(
        default=SanitisationState.RETAINED,
        alias="sanitisationState",
    )


class ReleaseMetadataSnapshot(DietaryBaseModel):
    resource_uri: str
    release_version: str
    defaults_version: str
    metadata_report_sha256: str
    artifact_hashes: dict[str, str]


class VersionPinnedAdapterReviewDossier(ContentHashIdModel):
    _content_hash_id_field = "dossier_id"
    _content_hash_id_prefix = "adapter-review-dossier"
    schema_version: str = Field(default=SCHEMA_VERSION)
    dossier_id: str = Field(default_factory=lambda: f"adapter-review-dossier-{uuid4().hex[:12]}")
    bundle_profile: BundleProfile = Field(default=BundleProfile.INTERNAL_REVIEW, alias="bundleProfile")
    dossier_status: str
    review_bundle: AdapterReviewBundle
    release_metadata: ReleaseMetadataSnapshot
    source_governance_snapshot: list[RegulatorySourceRecord] = Field(default_factory=list)
    model_governance_snapshot: ModelGovernanceRecord | None = None
    pinned_resources: list[PinnedResourceFingerprint]
    confidentiality_annotations: list[ConfidentialityAnnotation] = Field(
        default_factory=list,
        alias="confidentialityAnnotations",
    )
    sanitisation_records: list[SanitisationRecord] = Field(
        default_factory=list,
        alias="sanitisationRecords",
    )
    limitations: list[LimitationNote] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AssessReviewDossierReadinessRequest(DietaryBaseModel):
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    )
    target_profile: str = Field(alias="targetProfile", min_length=1)


class RegulatoryRuleResult(DietaryBaseModel):
    rule_id: str = Field(alias="ruleId")
    profile_id: str = Field(alias="profileId")
    status: ReadinessStatus
    message: str
    blocking: bool = False
    note: str | None = None


class ScientificFollowUpItem(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    category: str
    title: str
    priority: ReadinessStatus
    blocking: bool = False
    summary: str
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    linked_record_ids: list[str] = Field(default_factory=list, alias="linkedRecordIds")
    rationale: str | None = None
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")
    escalated: bool = False
    escalation_type: MetalsMonitoringEscalationType | None = Field(
        default=None,
        alias="escalationType",
    )
    follow_up_note: str | None = Field(default=None, alias="followUpNote")


class ScientificFollowUpQueues(DietaryBaseModel):
    open_action_ids: list[str] = Field(default_factory=list, alias="openActionIds")
    pending_action_ids: list[str] = Field(default_factory=list, alias="pendingActionIds")
    acknowledged_action_ids: list[str] = Field(default_factory=list, alias="acknowledgedActionIds")
    completed_action_ids: list[str] = Field(default_factory=list, alias="completedActionIds")
    waived_action_ids: list[str] = Field(default_factory=list, alias="waivedActionIds")
    escalated_action_ids: list[str] = Field(default_factory=list, alias="escalatedActionIds")


class ReviewDossierReadinessAssessment(DietaryBaseModel):
    overall_status: ReadinessStatus = Field(alias="overallStatus")
    target_profile: RegulatoryReadinessProfile = Field(alias="targetProfile")
    model_governance: ModelGovernanceRecord | None = Field(default=None, alias="modelGovernance")
    emerging_contaminant: EmergingContaminantRecord | None = Field(
        default=None,
        alias="emergingContaminant",
    )
    source_governance: list[RegulatorySourceRecord] = Field(default_factory=list, alias="sourceGovernance")
    applied_rules: list[RegulatoryRuleResult] = Field(default_factory=list, alias="appliedRules")
    blocking_rules: list[RegulatoryRuleResult] = Field(default_factory=list, alias="blockingRules")
    warning_rules: list[RegulatoryRuleResult] = Field(default_factory=list, alias="warningRules")
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult] = Field(
        default_factory=list,
        alias="legalLimitReviews",
    )
    scientific_follow_up_items: list[ScientificFollowUpItem] = Field(
        default_factory=list,
        alias="scientificFollowUpItems",
    )
    scientific_follow_up_queues: ScientificFollowUpQueues = Field(
        default_factory=ScientificFollowUpQueues,
        alias="scientificFollowUpQueues",
    )
    required_disclaimers: list[str] = Field(default_factory=list, alias="requiredDisclaimers")
    notes: list[str] = Field(default_factory=list)


class ScientificFollowUpQueueBundleItem(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    category: str
    title: str
    priority: ReadinessStatus
    blocking: bool = False
    summary: str
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    linked_record_ids: list[str] = Field(default_factory=list, alias="linkedRecordIds")
    rationale: str | None = None
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")
    escalated: bool = False
    escalation_type: MetalsMonitoringEscalationType | None = Field(
        default=None,
        alias="escalationType",
    )
    follow_up_note: str | None = Field(default=None, alias="followUpNote")
    queue_labels: list[ScientificFollowUpQueueLabel] = Field(default_factory=list, alias="queueLabels")


class ExportScientificFollowUpQueueBundleRequest(DietaryBaseModel):
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    )
    assessment: ReviewDossierReadinessAssessment
    bundle_note: str | None = Field(default=None, alias="bundleNote")


class ScientificFollowUpQueueBundle(ContentHashIdModel):
    _content_hash_id_field = "bundle_id"
    _content_hash_id_prefix = "scientific-follow-up"
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_id: str = Field(default_factory=lambda: f"scientific-follow-up-{uuid4().hex[:12]}")
    overall_status: ReadinessStatus = Field(alias="overallStatus")
    target_profile: RegulatoryReadinessProfile = Field(alias="targetProfile")
    source_dossier_id: str = Field(alias="sourceDossierId")
    source_dossier_status: str = Field(alias="sourceDossierStatus")
    source_workflow: str = Field(alias="sourceWorkflow")
    bundle_profile: BundleProfile = Field(alias="bundleProfile")
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult] = Field(
        default_factory=list,
        alias="legalLimitReviews",
    )
    action_items: list[ScientificFollowUpQueueBundleItem] = Field(default_factory=list, alias="actionItems")
    queues: ScientificFollowUpQueues
    open_action_count: int = Field(alias="openActionCount", ge=0)
    pending_action_count: int = Field(alias="pendingActionCount", ge=0)
    acknowledged_action_count: int = Field(alias="acknowledgedActionCount", ge=0)
    completed_action_count: int = Field(alias="completedActionCount", ge=0)
    waived_action_count: int = Field(alias="waivedActionCount", ge=0)
    escalated_action_count: int = Field(alias="escalatedActionCount", ge=0)
    recommended_sequence: list[str] = Field(default_factory=list, alias="recommendedSequence")
    documentation_resource_uri: str = Field(alias="documentationResourceUri")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class ScientificFollowUpReviewBoardItem(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    category: str
    title: str
    priority: ReadinessStatus
    blocking: bool = False
    summary: str
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    linked_record_ids: list[str] = Field(default_factory=list, alias="linkedRecordIds")
    rationale: str | None = None
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")
    escalated: bool = False
    escalation_type: MetalsMonitoringEscalationType | None = Field(
        default=None,
        alias="escalationType",
    )
    follow_up_note: str | None = Field(default=None, alias="followUpNote")
    queue_labels: list[ScientificFollowUpQueueLabel] = Field(default_factory=list, alias="queueLabels")
    owner_lane: ScientificFollowUpOwnerLane = Field(alias="ownerLane")
    due_state: ScientificFollowUpDueState = Field(alias="dueState")
    triage_rank: int = Field(alias="triageRank", ge=1)


class ScientificFollowUpOwnerLaneGroup(DietaryBaseModel):
    owner_lane: ScientificFollowUpOwnerLane = Field(alias="ownerLane")
    action_ids: list[str] = Field(default_factory=list, alias="actionIds")
    blocking_action_ids: list[str] = Field(default_factory=list, alias="blockingActionIds")
    due_states: list[ScientificFollowUpDueState] = Field(default_factory=list, alias="dueStates")
    action_count: int = Field(alias="actionCount", ge=0)


class ScientificFollowUpDueStateGroup(DietaryBaseModel):
    due_state: ScientificFollowUpDueState = Field(alias="dueState")
    action_ids: list[str] = Field(default_factory=list, alias="actionIds")
    blocking_action_ids: list[str] = Field(default_factory=list, alias="blockingActionIds")
    owner_lanes: list[ScientificFollowUpOwnerLane] = Field(default_factory=list, alias="ownerLanes")
    action_count: int = Field(alias="actionCount", ge=0)


class ExportScientificFollowUpReviewBoardRequest(DietaryBaseModel):
    queue_bundle: ScientificFollowUpQueueBundle = Field(alias="queueBundle")
    board_note: str | None = Field(default=None, alias="boardNote")


class ScientificFollowUpReviewBoard(ContentHashIdModel):
    _content_hash_id_field = "board_id"
    _content_hash_id_prefix = "scientific-follow-up-board"
    schema_version: str = Field(default=SCHEMA_VERSION)
    board_id: str = Field(default_factory=lambda: f"scientific-follow-up-board-{uuid4().hex[:12]}")
    overall_status: ReadinessStatus = Field(alias="overallStatus")
    target_profile: RegulatoryReadinessProfile = Field(alias="targetProfile")
    source_bundle_id: str = Field(alias="sourceBundleId")
    source_dossier_id: str = Field(alias="sourceDossierId")
    source_dossier_status: str = Field(alias="sourceDossierStatus")
    source_workflow: str = Field(alias="sourceWorkflow")
    bundle_profile: BundleProfile = Field(alias="bundleProfile")
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult] = Field(
        default_factory=list,
        alias="legalLimitReviews",
    )
    action_items: list[ScientificFollowUpReviewBoardItem] = Field(default_factory=list, alias="actionItems")
    owner_lanes: list[ScientificFollowUpOwnerLaneGroup] = Field(default_factory=list, alias="ownerLanes")
    due_state_groups: list[ScientificFollowUpDueStateGroup] = Field(default_factory=list, alias="dueStateGroups")
    immediate_action_ids: list[str] = Field(default_factory=list, alias="immediateActionIds")
    current_cycle_action_ids: list[str] = Field(default_factory=list, alias="currentCycleActionIds")
    in_progress_action_ids: list[str] = Field(default_factory=list, alias="inProgressActionIds")
    closed_action_ids: list[str] = Field(default_factory=list, alias="closedActionIds")
    recommended_triage_sequence: list[str] = Field(default_factory=list, alias="recommendedTriageSequence")
    documentation_resource_uri: str = Field(alias="documentationResourceUri")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class ExportScientificFollowUpOwnerHandoffPacketRequest(DietaryBaseModel):
    board: ScientificFollowUpReviewBoard
    owner_lane: ScientificFollowUpOwnerLane = Field(alias="ownerLane")
    due_state_filter: list[ScientificFollowUpDueState] = Field(default_factory=list, alias="dueStateFilter")
    packet_note: str | None = Field(default=None, alias="packetNote")


class ScientificFollowUpOwnerHandoffPacket(ContentHashIdModel):
    _content_hash_id_field = "packet_id"
    _content_hash_id_prefix = "scientific-follow-up-owner"
    schema_version: str = Field(default=SCHEMA_VERSION)
    packet_id: str = Field(default_factory=lambda: f"scientific-follow-up-owner-{uuid4().hex[:12]}")
    overall_status: ReadinessStatus = Field(alias="overallStatus")
    target_profile: RegulatoryReadinessProfile = Field(alias="targetProfile")
    source_board_id: str = Field(alias="sourceBoardId")
    source_bundle_id: str = Field(alias="sourceBundleId")
    source_dossier_id: str = Field(alias="sourceDossierId")
    source_dossier_status: str = Field(alias="sourceDossierStatus")
    source_workflow: str = Field(alias="sourceWorkflow")
    bundle_profile: BundleProfile = Field(alias="bundleProfile")
    owner_lane: ScientificFollowUpOwnerLane = Field(alias="ownerLane")
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult] = Field(
        default_factory=list,
        alias="legalLimitReviews",
    )
    owner_lane_group: ScientificFollowUpOwnerLaneGroup = Field(alias="ownerLaneGroup")
    due_state_filter: list[ScientificFollowUpDueState] = Field(default_factory=list, alias="dueStateFilter")
    action_items: list[ScientificFollowUpReviewBoardItem] = Field(default_factory=list, alias="actionItems")
    due_state_groups: list[ScientificFollowUpDueStateGroup] = Field(default_factory=list, alias="dueStateGroups")
    action_count: int = Field(alias="actionCount", ge=0)
    blocking_action_ids: list[str] = Field(default_factory=list, alias="blockingActionIds")
    immediate_action_ids: list[str] = Field(default_factory=list, alias="immediateActionIds")
    current_cycle_action_ids: list[str] = Field(default_factory=list, alias="currentCycleActionIds")
    in_progress_action_ids: list[str] = Field(default_factory=list, alias="inProgressActionIds")
    closed_action_ids: list[str] = Field(default_factory=list, alias="closedActionIds")
    recommended_owner_sequence: list[str] = Field(default_factory=list, alias="recommendedOwnerSequence")
    documentation_resource_uri: str = Field(alias="documentationResourceUri")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class ScientificFollowUpOwnerRemediationActionItem(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    category: str
    title: str
    priority: ReadinessStatus
    blocking: bool = False
    summary: str
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    linked_record_ids: list[str] = Field(default_factory=list, alias="linkedRecordIds")
    rationale: str | None = None
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")
    escalated: bool = False
    escalation_type: MetalsMonitoringEscalationType | None = Field(
        default=None,
        alias="escalationType",
    )
    follow_up_note: str | None = Field(default=None, alias="followUpNote")
    due_state: ScientificFollowUpDueState = Field(alias="dueState")
    remediation_class: ScientificFollowUpRemediationClass = Field(alias="remediationClass")
    recommended_steps: list[str] = Field(default_factory=list, alias="recommendedSteps")


class ScientificFollowUpRemediationClassGroup(DietaryBaseModel):
    remediation_class: ScientificFollowUpRemediationClass = Field(alias="remediationClass")
    action_ids: list[str] = Field(default_factory=list, alias="actionIds")
    due_states: list[ScientificFollowUpDueState] = Field(default_factory=list, alias="dueStates")
    blocking_action_ids: list[str] = Field(default_factory=list, alias="blockingActionIds")
    action_count: int = Field(alias="actionCount", ge=0)


class ExportScientificFollowUpOwnerRemediationPacketRequest(DietaryBaseModel):
    handoff_packet: ScientificFollowUpOwnerHandoffPacket = Field(alias="handoffPacket")
    packet_note: str | None = Field(default=None, alias="packetNote")


class ScientificFollowUpOwnerRemediationPacket(ContentHashIdModel):
    _content_hash_id_field = "packet_id"
    _content_hash_id_prefix = "scientific-follow-up-remediation"
    schema_version: str = Field(default=SCHEMA_VERSION)
    packet_id: str = Field(default_factory=lambda: f"scientific-follow-up-remediation-{uuid4().hex[:12]}")
    overall_status: ReadinessStatus = Field(alias="overallStatus")
    target_profile: RegulatoryReadinessProfile = Field(alias="targetProfile")
    source_handoff_packet_id: str = Field(alias="sourceHandoffPacketId")
    source_board_id: str = Field(alias="sourceBoardId")
    source_bundle_id: str = Field(alias="sourceBundleId")
    source_dossier_id: str = Field(alias="sourceDossierId")
    source_dossier_status: str = Field(alias="sourceDossierStatus")
    source_workflow: str = Field(alias="sourceWorkflow")
    bundle_profile: BundleProfile = Field(alias="bundleProfile")
    owner_lane: ScientificFollowUpOwnerLane = Field(alias="ownerLane")
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult] = Field(
        default_factory=list,
        alias="legalLimitReviews",
    )
    due_state_filter: list[ScientificFollowUpDueState] = Field(default_factory=list, alias="dueStateFilter")
    action_items: list[ScientificFollowUpOwnerRemediationActionItem] = Field(
        default_factory=list,
        alias="actionItems",
    )
    remediation_class_groups: list[ScientificFollowUpRemediationClassGroup] = Field(
        default_factory=list,
        alias="remediationClassGroups",
    )
    action_count: int = Field(alias="actionCount", ge=0)
    blocking_action_count: int = Field(alias="blockingActionCount", ge=0)
    resolve_now_action_ids: list[str] = Field(default_factory=list, alias="resolveNowActionIds")
    review_this_cycle_action_ids: list[str] = Field(default_factory=list, alias="reviewThisCycleActionIds")
    track_in_progress_action_ids: list[str] = Field(default_factory=list, alias="trackInProgressActionIds")
    record_closure_action_ids: list[str] = Field(default_factory=list, alias="recordClosureActionIds")
    recommended_remediation_sequence: list[str] = Field(default_factory=list, alias="recommendedRemediationSequence")
    documentation_resource_uri: str = Field(alias="documentationResourceUri")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class ScientificFollowUpOwnerSignoffDecisionInput(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    rationale: str | None = None
    reviewed_at: date | None = Field(default=None, alias="reviewedAt")
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")

    @model_validator(mode="after")
    def validate_rationale_for_decision(self) -> "ScientificFollowUpOwnerSignoffDecisionInput":
        if self.decision_status != InteroperabilityActionDecisionStatus.PENDING and not self.rationale:
            raise ValueError("A rationale is required for acknowledged, completed, or waived signoff decisions.")
        return self


class ScientificFollowUpOwnerSignoffActionItem(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    category: str
    title: str
    priority: ReadinessStatus
    blocking: bool = False
    summary: str
    linked_record_ids: list[str] = Field(default_factory=list, alias="linkedRecordIds")
    due_state: ScientificFollowUpDueState = Field(alias="dueState")
    remediation_class: ScientificFollowUpRemediationClass = Field(alias="remediationClass")
    recommended_steps: list[str] = Field(default_factory=list, alias="recommendedSteps")
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    rationale: str | None = None
    reviewed_at: date | None = Field(default=None, alias="reviewedAt")
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")
    resolved: bool = False


class ExportScientificFollowUpOwnerSignoffPacketRequest(DietaryBaseModel):
    remediation_packet: ScientificFollowUpOwnerRemediationPacket = Field(alias="remediationPacket")
    reviewer_id: str = Field(alias="reviewerId", min_length=1)
    reviewer_role: str = Field(alias="reviewerRole", min_length=1)
    decisions: list[ScientificFollowUpOwnerSignoffDecisionInput] = Field(default_factory=list)
    packet_note: str | None = Field(default=None, alias="packetNote")


class ScientificFollowUpOwnerSignoffPacket(ContentHashIdModel):
    _content_hash_id_field = "packet_id"
    _content_hash_id_prefix = "scientific-follow-up-owner-signoff"
    schema_version: str = Field(default=SCHEMA_VERSION)
    packet_id: str = Field(default_factory=lambda: f"scientific-follow-up-owner-signoff-{uuid4().hex[:12]}")
    overall_signoff_status: InteroperabilitySignoffStatus = Field(alias="overallSignoffStatus")
    reviewer_id: str = Field(alias="reviewerId")
    reviewer_role: str = Field(alias="reviewerRole")
    overall_status: ReadinessStatus = Field(alias="overallStatus")
    target_profile: RegulatoryReadinessProfile = Field(alias="targetProfile")
    source_remediation_packet_id: str = Field(alias="sourceRemediationPacketId")
    source_handoff_packet_id: str = Field(alias="sourceHandoffPacketId")
    source_board_id: str = Field(alias="sourceBoardId")
    source_bundle_id: str = Field(alias="sourceBundleId")
    source_dossier_id: str = Field(alias="sourceDossierId")
    source_dossier_status: str = Field(alias="sourceDossierStatus")
    source_workflow: str = Field(alias="sourceWorkflow")
    bundle_profile: BundleProfile = Field(alias="bundleProfile")
    owner_lane: ScientificFollowUpOwnerLane = Field(alias="ownerLane")
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult] = Field(
        default_factory=list,
        alias="legalLimitReviews",
    )
    due_state_filter: list[ScientificFollowUpDueState] = Field(default_factory=list, alias="dueStateFilter")
    action_items: list[ScientificFollowUpOwnerSignoffActionItem] = Field(default_factory=list, alias="actionItems")
    action_count: int = Field(alias="actionCount", ge=0)
    pending_action_ids: list[str] = Field(default_factory=list, alias="pendingActionIds")
    acknowledged_action_ids: list[str] = Field(default_factory=list, alias="acknowledgedActionIds")
    completed_action_ids: list[str] = Field(default_factory=list, alias="completedActionIds")
    waived_action_ids: list[str] = Field(default_factory=list, alias="waivedActionIds")
    unresolved_blocking_action_ids: list[str] = Field(default_factory=list, alias="unresolvedBlockingActionIds")
    resolve_now_action_ids: list[str] = Field(default_factory=list, alias="resolveNowActionIds")
    review_this_cycle_action_ids: list[str] = Field(default_factory=list, alias="reviewThisCycleActionIds")
    track_in_progress_action_ids: list[str] = Field(default_factory=list, alias="trackInProgressActionIds")
    record_closure_action_ids: list[str] = Field(default_factory=list, alias="recordClosureActionIds")
    recommended_signoff_sequence: list[str] = Field(default_factory=list, alias="recommendedSignoffSequence")
    documentation_resource_uri: str = Field(alias="documentationResourceUri")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class LookupReferenceValuesRequest(DietaryBaseModel):
    substance_key: str = Field(alias="substanceKey", min_length=1)
    authority: str | None = None
    jurisdiction: str | None = None
    contaminant_family: ContaminantFamily | None = Field(default=None, alias="contaminantFamily")
    reference_type: str | None = Field(default=None, alias="referenceType")
    population: str | None = None
    assessment_year: int | None = Field(default=None, ge=1900, le=2100, alias="assessmentYear")
    source_id: str | None = Field(default=None, alias="sourceId")


class ReferenceValueLookupResult(DietaryBaseModel):
    substance_key: str = Field(alias="substanceKey")
    contaminant_family: ContaminantFamily | None = Field(default=None, alias="contaminantFamily")
    requested_jurisdiction_status: ReferenceValueJurisdictionStatus = Field(
        default=ReferenceValueJurisdictionStatus.UNSCOPED_LOOKUP,
        alias="requestedJurisdictionStatus",
    )
    curated_support_types: list[str] = Field(default_factory=list, alias="curatedSupportTypes")
    authorities: list[AuthorityRecord] = Field(default_factory=list)
    matched_records: list[ReferenceValueRecord] = Field(default_factory=list, alias="matchedRecords")
    visible_conflicts: list[SourceConflictGroup] = Field(default_factory=list, alias="visibleConflicts")
    coverage_summaries: list[JurisdictionCoverageRecord] = Field(default_factory=list, alias="coverageSummaries")
    quality_flags: list[QualityFlag] = Field(default_factory=list, alias="qualityFlags")
    notes: list[str] = Field(default_factory=list)


class LookupContaminantLegalLimitsRequest(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    substance_key: str | None = Field(default=None, alias="substanceKey")
    commodity_code: str | None = Field(default=None, alias="commodityCode")
    matrix_group: str | None = Field(default=None, alias="matrixGroup")
    authority: str | None = None

    @field_validator("contaminant_family")
    @classmethod
    def validate_supported_family(cls, value: ContaminantFamily) -> ContaminantFamily:
        allowed = {
            ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS,
            ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION,
            ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
            ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
            ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
            ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        }
        if value not in allowed:
            raise ValueError(
                "contaminant legal-limit lookup supports PFAS, acrylamide, bisphenol A, cadmium, lead, inorganic arsenic, and mercury only"
            )
        return value


class ContaminantLegalLimitLookupResult(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    substance_key: str | None = Field(default=None, alias="substanceKey")
    commodity_code: str | None = Field(default=None, alias="commodityCode")
    matrix_group: str | None = Field(default=None, alias="matrixGroup")
    authority: str | None = None
    requested_lane_status: RequestedLaneStatus = Field(
        default=RequestedLaneStatus.UNSCOPED_LOOKUP,
        alias="requestedLaneStatus",
    )
    curated_scope_commodity_codes: list[str] = Field(default_factory=list, alias="curatedScopeCommodityCodes")
    curated_scope_matrix_groups: list[str] = Field(default_factory=list, alias="curatedScopeMatrixGroups")
    legal_authorities: list[LegalAuthorityRecord] = Field(default_factory=list, alias="legalAuthorities")
    matched_records: list[ContaminantLegalLimitRecord] = Field(default_factory=list, alias="matchedRecords")
    coverage_summaries: list[JurisdictionCoverageRecord] = Field(default_factory=list, alias="coverageSummaries")
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    quality_flags: list[QualityFlag] = Field(default_factory=list, alias="qualityFlags")
    notes: list[str] = Field(default_factory=list)


class LookupMethodSupportRequest(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None


class MethodSupportLookupResult(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    methods: list[MethodRegistryRecord] = Field(default_factory=list)
    legal_authorities: list[LegalAuthorityRecord] = Field(default_factory=list, alias="legalAuthorities")
    emerging_contaminant: EmergingContaminantRecord | None = Field(default=None, alias="emergingContaminant")
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    submission_candidate_allowed: bool = Field(alias="submissionCandidateAllowed")
    notes: list[str] = Field(default_factory=list)


class LookupConsumptionDatasetSupportRequest(DietaryBaseModel):
    jurisdiction: str = Field(min_length=1)
    dataset_id: str | None = Field(default=None, alias="datasetId")
    contaminant_family: ContaminantFamily | None = Field(default=None, alias="contaminantFamily")


class ConsumptionDatasetSupportLookupResult(DietaryBaseModel):
    jurisdiction: str
    dataset_id: str | None = Field(default=None, alias="datasetId")
    contaminant_family: ContaminantFamily | None = Field(default=None, alias="contaminantFamily")
    datasets: list[ConsumptionDatasetRecord] = Field(default_factory=list)
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    notes: list[str] = Field(default_factory=list)


class LookupMetalsOccurrenceRequest(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None

    @field_validator("contaminant_family")
    @classmethod
    def validate_metals_family(cls, value: ContaminantFamily) -> ContaminantFamily:
        allowed = {
            ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
            ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
            ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
            ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        }
        if value not in allowed:
            raise ValueError("metals occurrence lookup supports cadmium, lead, inorganic arsenic, and mercury only")
        return value


class MetalsOccurrenceLookupResult(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    records: list[MetalsOccurrenceRecord] = Field(default_factory=list)
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    submission_candidate_allowed: bool = Field(alias="submissionCandidateAllowed")
    notes: list[str] = Field(default_factory=list)


class LookupMetalsReviewFocusRequest(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    commodity_group: str | None = Field(default=None, alias="commodityGroup")
    focus_food: str | None = Field(default=None, alias="focusFood")

    @field_validator("contaminant_family")
    @classmethod
    def validate_metals_family(cls, value: ContaminantFamily) -> ContaminantFamily:
        allowed = {
            ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
            ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
            ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
            ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        }
        if value not in allowed:
            raise ValueError("metals review-focus lookup supports cadmium, lead, inorganic arsenic, and mercury only")
        return value


class MetalsReviewFocusLookupResult(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    commodity_group: str | None = Field(default=None, alias="commodityGroup")
    focus_food: str | None = Field(default=None, alias="focusFood")
    records: list[MetalsReviewFocusRecord] = Field(default_factory=list)
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    submission_candidate_allowed: bool = Field(alias="submissionCandidateAllowed")
    notes: list[str] = Field(default_factory=list)


class LookupOccurrenceEvidenceRequest(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    analyte: str | None = None
    matrix_group: str | None = Field(default=None, alias="matrixGroup")

    @field_validator("contaminant_family")
    @classmethod
    def validate_supported_family(cls, value: ContaminantFamily) -> ContaminantFamily:
        allowed = {
            ContaminantFamily.PESTICIDE_RESIDUE,
            ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS,
            ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION,
            ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
            ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
            ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
            ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        }
        if value not in allowed:
            raise ValueError(
                "occurrence evidence lookup supports pesticide residues, PFAS, acrylamide, bisphenol A, cadmium, lead, inorganic arsenic, and mercury only"
            )
        return value


class OccurrenceEvidenceLookupResult(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    analyte: str | None = None
    matrix_group: str | None = Field(default=None, alias="matrixGroup")
    records: list[OccurrenceEvidenceRecord] = Field(default_factory=list)
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    submission_candidate_allowed: bool = Field(alias="submissionCandidateAllowed")
    notes: list[str] = Field(default_factory=list)


class LookupAnalyticalMethodEvidenceRequest(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    analyte: str | None = None
    matrix_group: str | None = Field(default=None, alias="matrixGroup")

    @field_validator("contaminant_family")
    @classmethod
    def validate_supported_family(cls, value: ContaminantFamily) -> ContaminantFamily:
        allowed = {
            ContaminantFamily.PESTICIDE_RESIDUE,
            ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS,
            ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION,
            ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
            ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
            ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
            ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        }
        if value not in allowed:
            raise ValueError(
                "analytical method evidence lookup supports pesticide residues, PFAS, acrylamide, bisphenol A, cadmium, lead, inorganic arsenic, and mercury only"
            )
        return value


class AnalyticalMethodEvidenceLookupResult(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    analyte: str | None = None
    matrix_group: str | None = Field(default=None, alias="matrixGroup")
    records: list[AnalyticalMethodEvidenceRecord] = Field(default_factory=list)
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    submission_candidate_allowed: bool = Field(alias="submissionCandidateAllowed")
    notes: list[str] = Field(default_factory=list)


class LookupReportingProfilesRequest(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    matrix_group: str | None = Field(default=None, alias="matrixGroup")


class ReportingProfileLookupResult(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    matrix_group: str | None = Field(default=None, alias="matrixGroup")
    profiles: list[ReportingProfileRecord] = Field(default_factory=list)
    recommended_primary_profile_ids: list[str] = Field(
        default_factory=list,
        alias="recommendedPrimaryProfileIds",
    )
    notes: list[str] = Field(default_factory=list)


class ReportingProfileNonSubstitutionLink(DietaryBaseModel):
    profile_id: str = Field(alias="profileId")
    not_substitutable_for_profile_ids: list[str] = Field(
        default_factory=list,
        alias="notSubstitutableForProfileIds",
    )


class ReportingProfileApplicabilitySummary(DietaryBaseModel):
    applicable_profile_ids: list[str] = Field(default_factory=list, alias="applicableProfileIds")
    recommended_primary_profile_ids: list[str] = Field(
        default_factory=list,
        alias="recommendedPrimaryProfileIds",
    )
    optional_extension_profile_ids: list[str] = Field(
        default_factory=list,
        alias="optionalExtensionProfileIds",
    )
    compliance_variant_profile_ids: list[str] = Field(
        default_factory=list,
        alias="complianceVariantProfileIds",
    )
    supporting_detail_profile_ids: list[str] = Field(
        default_factory=list,
        alias="supportingDetailProfileIds",
    )
    non_substitution_links: list[ReportingProfileNonSubstitutionLink] = Field(
        default_factory=list,
        alias="nonSubstitutionLinks",
    )
    notes: list[str] = Field(default_factory=list)


class ContaminantMonitoringHeaderResolution(DietaryBaseModel):
    header: str
    canonical_field: str | None = Field(default=None, alias="canonicalField")
    recognized: bool


class ContaminantMonitoringNormalizedProjection(DietaryBaseModel):
    row_count: int = Field(alias="rowCount")
    analytes: list[str] = Field(default_factory=list)
    commodity_names: list[str] = Field(default_factory=list, alias="commodityNames")
    units: list[str] = Field(default_factory=list)
    sampling_years: list[int] = Field(default_factory=list, alias="samplingYears")
    rows_with_lod: int = Field(alias="rowsWithLod")
    rows_with_loq: int = Field(alias="rowsWithLoq")
    rows_with_recovery_percent: int = Field(alias="rowsWithRecoveryPercent")
    rows_with_measurement_uncertainty_percent: int = Field(alias="rowsWithMeasurementUncertaintyPercent")
    priority_food_group_hits: list[str] = Field(default_factory=list, alias="priorityFoodGroupHits")
    high_attention_food_hits: list[str] = Field(default_factory=list, alias="highAttentionFoodHits")
    sensitive_population_groups: list[str] = Field(default_factory=list, alias="sensitivePopulationGroups")
    linked_occurrence_record_ids: list[str] = Field(default_factory=list, alias="linkedOccurrenceRecordIds")
    linked_review_focus_ids: list[str] = Field(default_factory=list, alias="linkedReviewFocusIds")


class CheckContaminantMonitoringImportRequest(DietaryBaseModel):
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str = Field(min_length=1)
    csv_text: str = Field(alias="csvText", min_length=1, max_length=MAX_CSV_TEXT_LENGTH)
    authority: str | None = None
    dataset_id: str | None = Field(default=None, alias="datasetId")
    occurrence_evidence_record_ids: list[str] = Field(default_factory=list, alias="occurrenceEvidenceRecordIds")
    analytical_method_evidence_record_ids: list[str] = Field(
        default_factory=list,
        alias="analyticalMethodEvidenceRecordIds",
    )

    @field_validator("contaminant_family")
    @classmethod
    def validate_supported_family(cls, value: ContaminantFamily) -> ContaminantFamily:
        allowed = {
            ContaminantFamily.PESTICIDE_RESIDUE,
            ContaminantFamily.PFAS_FOOD_CONTAMINANTS,
            ContaminantFamily.ACRYLAMIDE_PROCESS_CONTAMINANTS,
            ContaminantFamily.BISPHENOL_FOOD_CONTACT_MIGRATION,
            ContaminantFamily.CADMIUM_FOOD_CONTAMINANTS,
            ContaminantFamily.LEAD_FOOD_CONTAMINANTS,
            ContaminantFamily.INORGANIC_ARSENIC_FOOD_CONTAMINANTS,
            ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        }
        if value not in allowed:
            raise ValueError(
                "contaminant monitoring import checks support pesticide residues, PFAS, acrylamide, bisphenol A, cadmium, lead, inorganic arsenic, and mercury only"
            )
        return value


class ContaminantMonitoringImportCheckResult(DietaryBaseModel):
    check_status: ReadinessStatus = Field(alias="checkStatus")
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str
    authority: str | None = None
    dataset_id: str | None = Field(default=None, alias="datasetId")
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    submission_candidate_allowed: bool = Field(alias="submissionCandidateAllowed")
    occurrence_evidence_records: list[OccurrenceEvidenceRecord] = Field(
        default_factory=list,
        alias="occurrenceEvidenceRecords",
    )
    analytical_method_evidence_records: list[AnalyticalMethodEvidenceRecord] = Field(
        default_factory=list,
        alias="analyticalMethodEvidenceRecords",
    )
    applicable_reporting_profile_ids: list[str] = Field(
        default_factory=list,
        alias="applicableReportingProfileIds",
    )
    reporting_profile_summary: ReportingProfileApplicabilitySummary | None = Field(
        default=None,
        alias="reportingProfileSummary",
    )
    header_resolution: list[ContaminantMonitoringHeaderResolution] = Field(
        default_factory=list,
        alias="headerResolution",
    )
    normalized_projection: ContaminantMonitoringNormalizedProjection = Field(alias="normalizedProjection")
    quality_flags: list[QualityFlag] = Field(default_factory=list, alias="qualityFlags")
    uncertainty_and_assumption_ledger: list[ScientificLedgerEntry] = Field(
        default_factory=list,
        alias="uncertaintyAndAssumptionLedger",
    )
    required_review_questions: list[str] = Field(default_factory=list, alias="requiredReviewQuestions")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class ContaminantMonitoringReviewPrompt(DietaryBaseModel):
    prompt_id: str = Field(alias="promptId")
    category: str
    prompt: str
    linked_record_id: str = Field(alias="linkedRecordId")
    linked_record_kind: str = Field(alias="linkedRecordKind")


class ExportContaminantMonitoringInterpretationBundleRequest(DietaryBaseModel):
    check_result: ContaminantMonitoringImportCheckResult = Field(alias="checkResult")
    bundle_note: str | None = Field(default=None, alias="bundleNote")


class ContaminantMonitoringInterpretationBundle(ContentHashIdModel):
    _content_hash_id_field = "bundle_id"
    _content_hash_id_prefix = "contaminant-monitoring-bundle"
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_id: str = Field(default_factory=lambda: f"contaminant-monitoring-bundle-{uuid4().hex[:12]}")
    bundle_profile: BundleProfile = Field(default=BundleProfile.INTERNAL_REVIEW, alias="bundleProfile")
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str
    authority: str | None = None
    dataset_id: str | None = Field(default=None, alias="datasetId")
    check_status: ReadinessStatus = Field(alias="checkStatus")
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    submission_candidate_allowed: bool = Field(alias="submissionCandidateAllowed")
    check_result: ContaminantMonitoringImportCheckResult = Field(alias="checkResult")
    reporting_profile_summary: ReportingProfileApplicabilitySummary | None = Field(
        default=None,
        alias="reportingProfileSummary",
    )
    linked_review_focus_records: list[MetalsReviewFocusRecord] = Field(
        default_factory=list,
        alias="linkedReviewFocusRecords",
    )
    unresolved_linked_review_focus_ids: list[str] = Field(
        default_factory=list,
        alias="unresolvedLinkedReviewFocusIds",
    )
    covered_source_ids: list[str] = Field(default_factory=list, alias="coveredSourceIds")
    covered_method_ids: list[str] = Field(default_factory=list, alias="coveredMethodIds")
    covered_legal_authority_ids: list[str] = Field(default_factory=list, alias="coveredLegalAuthorityIds")
    covered_dataset_ids: list[str] = Field(default_factory=list, alias="coveredDatasetIds")
    covered_reference_value_record_ids: list[str] = Field(
        default_factory=list,
        alias="coveredReferenceValueRecordIds",
    )
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult] = Field(
        default_factory=list,
        alias="legalLimitReviews",
    )
    uncertainty_and_assumption_ledger: list[ScientificLedgerEntry] = Field(
        default_factory=list,
        alias="uncertaintyAndAssumptionLedger",
    )
    review_prompts: list[ContaminantMonitoringReviewPrompt] = Field(default_factory=list, alias="reviewPrompts")
    recommended_sequence: list[str] = Field(default_factory=list, alias="recommendedSequence")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    dependencies: list[DependencyDescriptor] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ContaminantMonitoringSignoffDecisionInput(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    rationale: str | None = None
    reviewed_at: date | None = Field(default=None, alias="reviewedAt")
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")

    @model_validator(mode="after")
    def validate_rationale_for_decision(self) -> "ContaminantMonitoringSignoffDecisionInput":
        if self.decision_status != InteroperabilityActionDecisionStatus.PENDING and not self.rationale:
            raise ValueError("A rationale is required for acknowledged, completed, or waived signoff decisions.")
        return self


class ContaminantMonitoringSignoffActionItem(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    category: str
    title: str
    priority: ReadinessStatus
    blocking: bool = False
    summary: str
    linked_record_ids: list[str] = Field(default_factory=list, alias="linkedRecordIds")
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    rationale: str | None = None
    reviewed_at: date | None = Field(default=None, alias="reviewedAt")
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")
    resolved: bool = False


class ExportContaminantMonitoringSignoffPacketRequest(DietaryBaseModel):
    interpretation_bundle: ContaminantMonitoringInterpretationBundle = Field(alias="interpretationBundle")
    reviewer_id: str = Field(alias="reviewerId", min_length=1)
    reviewer_role: str = Field(alias="reviewerRole", min_length=1)
    decisions: list[ContaminantMonitoringSignoffDecisionInput] = Field(default_factory=list)
    packet_note: str | None = Field(default=None, alias="packetNote")


class ContaminantMonitoringSignoffPacket(ContentHashIdModel):
    _content_hash_id_field = "packet_id"
    _content_hash_id_prefix = "contaminant-monitoring-signoff"
    schema_version: str = Field(default=SCHEMA_VERSION)
    packet_id: str = Field(default_factory=lambda: f"contaminant-monitoring-signoff-{uuid4().hex[:12]}")
    overall_signoff_status: InteroperabilitySignoffStatus = Field(alias="overallSignoffStatus")
    reviewer_id: str = Field(alias="reviewerId")
    reviewer_role: str = Field(alias="reviewerRole")
    source_bundle_id: str = Field(alias="sourceBundleId")
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str
    authority: str | None = None
    dataset_id: str | None = Field(default=None, alias="datasetId")
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    submission_candidate_allowed: bool = Field(alias="submissionCandidateAllowed")
    reporting_profile_summary: ReportingProfileApplicabilitySummary | None = Field(
        default=None,
        alias="reportingProfileSummary",
    )
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult] = Field(
        default_factory=list,
        alias="legalLimitReviews",
    )
    action_items: list[ContaminantMonitoringSignoffActionItem] = Field(default_factory=list, alias="actionItems")
    pending_action_ids: list[str] = Field(default_factory=list, alias="pendingActionIds")
    acknowledged_action_ids: list[str] = Field(default_factory=list, alias="acknowledgedActionIds")
    completed_action_ids: list[str] = Field(default_factory=list, alias="completedActionIds")
    waived_action_ids: list[str] = Field(default_factory=list, alias="waivedActionIds")
    unresolved_blocking_action_ids: list[str] = Field(default_factory=list, alias="unresolvedBlockingActionIds")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class ContaminantMonitoringEscalationActionItem(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    escalation_type: MetalsMonitoringEscalationType = Field(alias="escalationType")
    category: str
    title: str
    priority: ReadinessStatus
    blocking: bool = False
    summary: str
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    linked_record_ids: list[str] = Field(default_factory=list, alias="linkedRecordIds")
    rationale: str | None = None
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")
    follow_up_note: str = Field(alias="followUpNote")


class ExportVersionPinnedContaminantMonitoringReviewDossierRequest(DietaryBaseModel):
    interpretation_bundle: ContaminantMonitoringInterpretationBundle = Field(alias="interpretationBundle")
    signoff_packet: ContaminantMonitoringSignoffPacket = Field(alias="signoffPacket")


class VersionPinnedContaminantMonitoringReviewDossier(ContentHashIdModel):
    _content_hash_id_field = "dossier_id"
    _content_hash_id_prefix = "contaminant-monitoring-review-dossier"
    schema_version: str = Field(default=SCHEMA_VERSION)
    dossier_id: str = Field(default_factory=lambda: f"contaminant-monitoring-review-dossier-{uuid4().hex[:12]}")
    bundle_profile: BundleProfile = Field(default=BundleProfile.INTERNAL_REVIEW, alias="bundleProfile")
    dossier_status: InteroperabilitySignoffStatus = Field(alias="dossierStatus")
    interpretation_bundle: ContaminantMonitoringInterpretationBundle = Field(alias="interpretationBundle")
    signoff_packet: ContaminantMonitoringSignoffPacket = Field(alias="signoffPacket")
    release_metadata: ReleaseMetadataSnapshot = Field(alias="releaseMetadata")
    source_governance_snapshot: list[RegulatorySourceRecord] = Field(
        default_factory=list,
        alias="sourceGovernanceSnapshot",
    )
    reporting_profile_summary: ReportingProfileApplicabilitySummary | None = Field(
        default=None,
        alias="reportingProfileSummary",
    )
    reporting_profile_snapshot: list[ReportingProfileRecord] = Field(
        default_factory=list,
        alias="reportingProfileSnapshot",
    )
    emerging_contaminant_snapshot: EmergingContaminantRecord | None = Field(
        default=None,
        alias="emergingContaminantSnapshot",
    )
    pinned_resources: list[PinnedResourceFingerprint] = Field(alias="pinnedResources")
    escalation_required: bool = Field(alias="escalationRequired")
    escalation_items: list[ContaminantMonitoringEscalationActionItem] = Field(
        default_factory=list,
        alias="escalationItems",
    )
    confidentiality_annotations: list[ConfidentialityAnnotation] = Field(
        default_factory=list,
        alias="confidentialityAnnotations",
    )
    sanitisation_records: list[SanitisationRecord] = Field(
        default_factory=list,
        alias="sanitisationRecords",
    )
    limitations: list[LimitationNote] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class MetalsMonitoringReviewPrompt(DietaryBaseModel):
    prompt_id: str = Field(alias="promptId")
    category: str
    prompt: str
    linked_record_id: str = Field(alias="linkedRecordId")
    linked_record_kind: str = Field(alias="linkedRecordKind")


class ExportMetalsMonitoringInterpretationBundleRequest(DietaryBaseModel):
    occurrence_result: MetalsOccurrenceLookupResult = Field(alias="occurrenceResult")
    review_focus_result: MetalsReviewFocusLookupResult = Field(alias="reviewFocusResult")
    bundle_note: str | None = Field(default=None, alias="bundleNote")


class MetalsMonitoringInterpretationBundle(ContentHashIdModel):
    _content_hash_id_field = "bundle_id"
    _content_hash_id_prefix = "metals-monitoring-bundle"
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_id: str = Field(default_factory=lambda: f"metals-monitoring-bundle-{uuid4().hex[:12]}")
    bundle_profile: BundleProfile = Field(default=BundleProfile.INTERNAL_REVIEW, alias="bundleProfile")
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    submission_candidate_allowed: bool = Field(alias="submissionCandidateAllowed")
    occurrence_records: list[MetalsOccurrenceRecord] = Field(default_factory=list, alias="occurrenceRecords")
    review_focus_records: list[MetalsReviewFocusRecord] = Field(default_factory=list, alias="reviewFocusRecords")
    linked_occurrence_record_ids: list[str] = Field(default_factory=list, alias="linkedOccurrenceRecordIds")
    unresolved_linked_occurrence_record_ids: list[str] = Field(
        default_factory=list,
        alias="unresolvedLinkedOccurrenceRecordIds",
    )
    priority_food_groups: list[str] = Field(default_factory=list, alias="priorityFoodGroups")
    high_attention_foods: list[str] = Field(default_factory=list, alias="highAttentionFoods")
    focus_foods: list[str] = Field(default_factory=list, alias="focusFoods")
    sensitive_population_groups: list[str] = Field(default_factory=list, alias="sensitivePopulationGroups")
    trend_signals: list[str] = Field(default_factory=list, alias="trendSignals")
    covered_source_ids: list[str] = Field(default_factory=list, alias="coveredSourceIds")
    covered_method_ids: list[str] = Field(default_factory=list, alias="coveredMethodIds")
    covered_legal_authority_ids: list[str] = Field(default_factory=list, alias="coveredLegalAuthorityIds")
    covered_dataset_ids: list[str] = Field(default_factory=list, alias="coveredDatasetIds")
    covered_reference_value_record_ids: list[str] = Field(
        default_factory=list,
        alias="coveredReferenceValueRecordIds",
    )
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult] = Field(
        default_factory=list,
        alias="legalLimitReviews",
    )
    uncertainty_and_assumption_ledger: list[ScientificLedgerEntry] = Field(
        default_factory=list,
        alias="uncertaintyAndAssumptionLedger",
    )
    review_prompts: list[MetalsMonitoringReviewPrompt] = Field(default_factory=list, alias="reviewPrompts")
    recommended_sequence: list[str] = Field(default_factory=list, alias="recommendedSequence")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    dependencies: list[DependencyDescriptor] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class MetalsMonitoringSignoffDecisionInput(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    rationale: str | None = None
    reviewed_at: date | None = Field(default=None, alias="reviewedAt")
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")

    @model_validator(mode="after")
    def validate_rationale_for_decision(self) -> "MetalsMonitoringSignoffDecisionInput":
        if self.decision_status != InteroperabilityActionDecisionStatus.PENDING and not self.rationale:
            raise ValueError("A rationale is required for acknowledged, completed, or waived signoff decisions.")
        return self


class MetalsMonitoringSignoffActionItem(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    category: str
    title: str
    priority: ReadinessStatus
    blocking: bool = False
    summary: str
    linked_record_ids: list[str] = Field(default_factory=list, alias="linkedRecordIds")
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    rationale: str | None = None
    reviewed_at: date | None = Field(default=None, alias="reviewedAt")
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")
    resolved: bool = False


class ExportMetalsMonitoringSignoffPacketRequest(DietaryBaseModel):
    interpretation_bundle: MetalsMonitoringInterpretationBundle = Field(alias="interpretationBundle")
    reviewer_id: str = Field(alias="reviewerId", min_length=1)
    reviewer_role: str = Field(alias="reviewerRole", min_length=1)
    decisions: list[MetalsMonitoringSignoffDecisionInput] = Field(default_factory=list)
    packet_note: str | None = Field(default=None, alias="packetNote")


class MetalsMonitoringSignoffPacket(ContentHashIdModel):
    _content_hash_id_field = "packet_id"
    _content_hash_id_prefix = "metals-monitoring-signoff"
    schema_version: str = Field(default=SCHEMA_VERSION)
    packet_id: str = Field(default_factory=lambda: f"metals-monitoring-signoff-{uuid4().hex[:12]}")
    overall_signoff_status: InteroperabilitySignoffStatus = Field(alias="overallSignoffStatus")
    reviewer_id: str = Field(alias="reviewerId")
    reviewer_role: str = Field(alias="reviewerRole")
    source_bundle_id: str = Field(alias="sourceBundleId")
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    submission_candidate_allowed: bool = Field(alias="submissionCandidateAllowed")
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult] = Field(
        default_factory=list,
        alias="legalLimitReviews",
    )
    action_items: list[MetalsMonitoringSignoffActionItem] = Field(default_factory=list, alias="actionItems")
    pending_action_ids: list[str] = Field(default_factory=list, alias="pendingActionIds")
    acknowledged_action_ids: list[str] = Field(default_factory=list, alias="acknowledgedActionIds")
    completed_action_ids: list[str] = Field(default_factory=list, alias="completedActionIds")
    waived_action_ids: list[str] = Field(default_factory=list, alias="waivedActionIds")
    unresolved_blocking_action_ids: list[str] = Field(default_factory=list, alias="unresolvedBlockingActionIds")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class MetalsMonitoringEscalationActionItem(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    escalation_type: MetalsMonitoringEscalationType = Field(alias="escalationType")
    category: str
    title: str
    priority: ReadinessStatus
    blocking: bool = False
    summary: str
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    linked_record_ids: list[str] = Field(default_factory=list, alias="linkedRecordIds")
    rationale: str | None = None
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")
    follow_up_note: str = Field(alias="followUpNote")


class ExportVersionPinnedMetalsMonitoringReviewDossierRequest(DietaryBaseModel):
    interpretation_bundle: MetalsMonitoringInterpretationBundle = Field(alias="interpretationBundle")
    signoff_packet: MetalsMonitoringSignoffPacket = Field(alias="signoffPacket")


class VersionPinnedMetalsMonitoringReviewDossier(ContentHashIdModel):
    _content_hash_id_field = "dossier_id"
    _content_hash_id_prefix = "metals-monitoring-review-dossier"
    schema_version: str = Field(default=SCHEMA_VERSION)
    dossier_id: str = Field(default_factory=lambda: f"metals-monitoring-review-dossier-{uuid4().hex[:12]}")
    bundle_profile: BundleProfile = Field(default=BundleProfile.INTERNAL_REVIEW, alias="bundleProfile")
    dossier_status: InteroperabilitySignoffStatus = Field(alias="dossierStatus")
    interpretation_bundle: MetalsMonitoringInterpretationBundle = Field(alias="interpretationBundle")
    signoff_packet: MetalsMonitoringSignoffPacket = Field(alias="signoffPacket")
    release_metadata: ReleaseMetadataSnapshot = Field(alias="releaseMetadata")
    source_governance_snapshot: list[RegulatorySourceRecord] = Field(
        default_factory=list,
        alias="sourceGovernanceSnapshot",
    )
    emerging_contaminant_snapshot: EmergingContaminantRecord | None = Field(
        default=None,
        alias="emergingContaminantSnapshot",
    )
    pinned_resources: list[PinnedResourceFingerprint] = Field(alias="pinnedResources")
    escalation_required: bool = Field(alias="escalationRequired")
    escalation_items: list[MetalsMonitoringEscalationActionItem] = Field(
        default_factory=list,
        alias="escalationItems",
    )
    confidentiality_annotations: list[ConfidentialityAnnotation] = Field(
        default_factory=list,
        alias="confidentialityAnnotations",
    )
    sanitisation_records: list[SanitisationRecord] = Field(
        default_factory=list,
        alias="sanitisationRecords",
    )
    limitations: list[LimitationNote] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ScientificFollowUpOwnerSignoffEscalationActionItem(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    escalation_type: MetalsMonitoringEscalationType = Field(alias="escalationType")
    category: str
    title: str
    priority: ReadinessStatus
    blocking: bool = False
    summary: str
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    linked_record_ids: list[str] = Field(default_factory=list, alias="linkedRecordIds")
    remediation_class: ScientificFollowUpRemediationClass = Field(alias="remediationClass")
    rationale: str | None = None
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")
    follow_up_note: str = Field(alias="followUpNote")


class ExportVersionPinnedScientificFollowUpOwnerSignoffDossierRequest(DietaryBaseModel):
    source_dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
    ) = Field(alias="sourceDossier")
    signoff_packet: ScientificFollowUpOwnerSignoffPacket = Field(alias="signoffPacket")


class VersionPinnedScientificFollowUpOwnerSignoffDossier(ContentHashIdModel):
    _content_hash_id_field = "dossier_id"
    _content_hash_id_prefix = "scientific-follow-up-owner-signoff-dossier"
    schema_version: str = Field(default=SCHEMA_VERSION)
    dossier_id: str = Field(default_factory=lambda: f"scientific-follow-up-owner-signoff-dossier-{uuid4().hex[:12]}")
    bundle_profile: BundleProfile = Field(default=BundleProfile.INTERNAL_REVIEW, alias="bundleProfile")
    dossier_status: InteroperabilitySignoffStatus = Field(alias="dossierStatus")
    source_workflow: str = Field(alias="sourceWorkflow")
    source_dossier_id: str = Field(alias="sourceDossierId")
    source_dossier_status: str = Field(alias="sourceDossierStatus")
    source_bundle_id: str = Field(alias="sourceBundleId")
    signoff_packet: ScientificFollowUpOwnerSignoffPacket = Field(alias="signoffPacket")
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult] = Field(
        default_factory=list,
        alias="legalLimitReviews",
    )
    release_metadata: ReleaseMetadataSnapshot = Field(alias="releaseMetadata")
    source_governance_snapshot: list[RegulatorySourceRecord] = Field(
        default_factory=list,
        alias="sourceGovernanceSnapshot",
    )
    model_governance_snapshot: ModelGovernanceRecord | None = Field(
        default=None,
        alias="modelGovernanceSnapshot",
    )
    emerging_contaminant_snapshot: EmergingContaminantRecord | None = Field(
        default=None,
        alias="emergingContaminantSnapshot",
    )
    pinned_resources: list[PinnedResourceFingerprint] = Field(default_factory=list, alias="pinnedResources")
    escalation_required: bool = Field(alias="escalationRequired")
    escalation_items: list[ScientificFollowUpOwnerSignoffEscalationActionItem] = Field(
        default_factory=list,
        alias="escalationItems",
    )
    confidentiality_annotations: list[ConfidentialityAnnotation] = Field(
        default_factory=list,
        alias="confidentialityAnnotations",
    )
    sanitisation_records: list[SanitisationRecord] = Field(
        default_factory=list,
        alias="sanitisationRecords",
    )
    limitations: list[LimitationNote] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class InteroperabilityProfile(DietaryBaseModel):
    profile_id: str = Field(alias="profileId")
    display_name: str = Field(alias="displayName")
    target_family: str = Field(alias="targetFamily")
    oht_templates: list[str] = Field(default_factory=list, alias="ohtTemplates")
    notes: list[str] = Field(default_factory=list)


class InteroperabilityReadinessProfile(DietaryBaseModel):
    profile_id: str = Field(alias="profileId")
    display_name: str = Field(alias="displayName")
    jurisdiction: str
    intended_use: str = Field(alias="intendedUse")
    allowed_preview_profiles: list[str] = Field(default_factory=list, alias="allowedPreviewProfiles")
    required_dossier_readiness_profile: str = Field(alias="requiredDossierReadinessProfile")
    notes: list[str] = Field(default_factory=list)


class InteroperabilityMappedField(DietaryBaseModel):
    local_path: str = Field(alias="localPath")
    target_path: str = Field(alias="targetPath")
    support_level: InteroperabilitySupportLevel = Field(alias="supportLevel")
    required: bool = False
    value_present: bool = Field(alias="valuePresent")
    value: dict | list | float | str | bool | None = None
    note: str | None = None


class InteroperabilityUnsupportedField(DietaryBaseModel):
    local_path: str = Field(alias="localPath")
    reason: str
    present: bool
    observed_value: dict | list | float | str | bool | None = Field(default=None, alias="observedValue")
    suggested_action: str | None = Field(default=None, alias="suggestedAction")


class ExportInteroperabilityPreviewRequest(DietaryBaseModel):
    dossier: VersionPinnedAdapterReviewDossier
    target_profile: str = Field(alias="targetProfile", min_length=1)


class InteroperabilityExportPreview(DietaryBaseModel):
    preview_status: ReadinessStatus = Field(alias="previewStatus")
    target_profile: InteroperabilityProfile = Field(alias="targetProfile")
    source_dossier_id: str = Field(alias="sourceDossierId")
    bundle_profile: BundleProfile = Field(alias="bundleProfile")
    profile_resource_uri: str = Field(alias="profileResourceUri")
    documentation_resource_uri: str = Field(alias="documentationResourceUri")
    target_document: dict = Field(alias="targetDocument")
    mapped_fields: list[InteroperabilityMappedField] = Field(default_factory=list, alias="mappedFields")
    unsupported_fields: list[InteroperabilityUnsupportedField] = Field(
        default_factory=list,
        alias="unsupportedFields",
    )
    missing_required_fields: list[str] = Field(default_factory=list, alias="missingRequiredFields")
    notes: list[str] = Field(default_factory=list)


class AssessInteroperabilityPreviewReadinessRequest(DietaryBaseModel):
    dossier: VersionPinnedAdapterReviewDossier
    preview: InteroperabilityExportPreview
    target_profile: str = Field(alias="targetProfile", min_length=1)


class InteroperabilityRuleResult(DietaryBaseModel):
    rule_id: str = Field(alias="ruleId")
    profile_id: str = Field(alias="profileId")
    status: ReadinessStatus
    message: str
    blocking: bool = False
    note: str | None = None


class InteroperabilityPreviewReadinessAssessment(DietaryBaseModel):
    overall_status: ReadinessStatus = Field(alias="overallStatus")
    target_profile: InteroperabilityReadinessProfile = Field(alias="targetProfile")
    source_preview_profile_id: str = Field(alias="sourcePreviewProfileId")
    linked_dossier_readiness_profile: str = Field(alias="linkedDossierReadinessProfile")
    linked_dossier_readiness_status: ReadinessStatus = Field(alias="linkedDossierReadinessStatus")
    applied_rules: list[InteroperabilityRuleResult] = Field(default_factory=list, alias="appliedRules")
    blocking_rules: list[InteroperabilityRuleResult] = Field(default_factory=list, alias="blockingRules")
    warning_rules: list[InteroperabilityRuleResult] = Field(default_factory=list, alias="warningRules")
    missing_required_fields: list[str] = Field(default_factory=list, alias="missingRequiredFields")
    unsupported_field_paths: list[str] = Field(default_factory=list, alias="unsupportedFieldPaths")
    derived_mapping_paths: list[str] = Field(default_factory=list, alias="derivedMappingPaths")
    review_required_mapping_paths: list[str] = Field(
        default_factory=list,
        alias="reviewRequiredMappingPaths",
    )
    direct_mapping_count: int = Field(alias="directMappingCount", ge=0)
    derived_mapping_count: int = Field(alias="derivedMappingCount", ge=0)
    review_required_mapping_count: int = Field(alias="reviewRequiredMappingCount", ge=0)
    notes: list[str] = Field(default_factory=list)


class InteroperabilityRemediationActionRecord(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    rule_id: str = Field(alias="ruleId")
    title: str
    action_type: str = Field(alias="actionType")
    summary: str
    recommended_steps: list[str] = Field(default_factory=list, alias="recommendedSteps")
    documentation_uris: list[str] = Field(default_factory=list, alias="documentationUris")
    resource_uris: list[str] = Field(default_factory=list, alias="resourceUris")


class InteroperabilityRemediationItem(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    rule_id: str = Field(alias="ruleId")
    title: str
    action_type: str = Field(alias="actionType")
    priority: ReadinessStatus
    blocking: bool = False
    summary: str
    recommended_steps: list[str] = Field(default_factory=list, alias="recommendedSteps")
    documentation_uris: list[str] = Field(default_factory=list, alias="documentationUris")
    resource_uris: list[str] = Field(default_factory=list, alias="resourceUris")
    trigger_message: str = Field(alias="triggerMessage")
    trigger_note: str | None = Field(default=None, alias="triggerNote")


class ExportInteroperabilityRemediationBundleRequest(DietaryBaseModel):
    dossier: VersionPinnedAdapterReviewDossier
    preview: InteroperabilityExportPreview
    assessment: InteroperabilityPreviewReadinessAssessment


class InteroperabilityRemediationBundle(ContentHashIdModel):
    _content_hash_id_field = "bundle_id"
    _content_hash_id_prefix = "interoperability-remediation"
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_id: str = Field(default_factory=lambda: f"interoperability-remediation-{uuid4().hex[:12]}")
    overall_status: ReadinessStatus = Field(alias="overallStatus")
    target_profile: InteroperabilityReadinessProfile = Field(alias="targetProfile")
    source_preview_profile_id: str = Field(alias="sourcePreviewProfileId")
    source_dossier_id: str = Field(alias="sourceDossierId")
    linked_dossier_readiness_profile: str = Field(alias="linkedDossierReadinessProfile")
    linked_dossier_readiness_status: ReadinessStatus = Field(alias="linkedDossierReadinessStatus")
    action_items: list[InteroperabilityRemediationItem] = Field(default_factory=list, alias="actionItems")
    blocking_action_count: int = Field(alias="blockingActionCount", ge=0)
    warning_action_count: int = Field(alias="warningActionCount", ge=0)
    recommended_sequence: list[str] = Field(default_factory=list, alias="recommendedSequence")
    catalog_resource_uri: str = Field(alias="catalogResourceUri")
    documentation_resource_uri: str = Field(alias="documentationResourceUri")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class InteroperabilitySignoffDecisionInput(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    rationale: str | None = None
    reviewed_at: date | None = Field(default=None, alias="reviewedAt")
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")

    @model_validator(mode="after")
    def validate_rationale_for_decision(self) -> "InteroperabilitySignoffDecisionInput":
        if self.decision_status != InteroperabilityActionDecisionStatus.PENDING and not self.rationale:
            raise ValueError("A rationale is required for acknowledged, completed, or waived signoff decisions.")
        return self


class InteroperabilitySignoffActionItem(DietaryBaseModel):
    action_id: str = Field(alias="actionId")
    rule_id: str = Field(alias="ruleId")
    title: str
    action_type: str = Field(alias="actionType")
    priority: ReadinessStatus
    blocking: bool = False
    summary: str
    trigger_message: str = Field(alias="triggerMessage")
    trigger_note: str | None = Field(default=None, alias="triggerNote")
    decision_status: InteroperabilityActionDecisionStatus = Field(alias="decisionStatus")
    rationale: str | None = None
    reviewed_at: date | None = Field(default=None, alias="reviewedAt")
    supporting_uris: list[str] = Field(default_factory=list, alias="supportingUris")
    resolved: bool = False


class ExportInteroperabilitySignoffPacketRequest(DietaryBaseModel):
    remediation_bundle: InteroperabilityRemediationBundle = Field(alias="remediationBundle")
    reviewer_id: str = Field(alias="reviewerId", min_length=1)
    reviewer_role: str = Field(alias="reviewerRole", min_length=1)
    decisions: list[InteroperabilitySignoffDecisionInput] = Field(default_factory=list)
    packet_note: str | None = Field(default=None, alias="packetNote")


class InteroperabilitySignoffPacket(ContentHashIdModel):
    _content_hash_id_field = "packet_id"
    _content_hash_id_prefix = "interoperability-signoff"
    schema_version: str = Field(default=SCHEMA_VERSION)
    packet_id: str = Field(default_factory=lambda: f"interoperability-signoff-{uuid4().hex[:12]}")
    overall_signoff_status: InteroperabilitySignoffStatus = Field(alias="overallSignoffStatus")
    reviewer_id: str = Field(alias="reviewerId")
    reviewer_role: str = Field(alias="reviewerRole")
    source_remediation_bundle_id: str = Field(alias="sourceRemediationBundleId")
    source_dossier_id: str = Field(alias="sourceDossierId")
    source_preview_profile_id: str = Field(alias="sourcePreviewProfileId")
    target_profile: InteroperabilityReadinessProfile = Field(alias="targetProfile")
    linked_dossier_readiness_profile: str = Field(alias="linkedDossierReadinessProfile")
    linked_dossier_readiness_status: ReadinessStatus = Field(alias="linkedDossierReadinessStatus")
    action_items: list[InteroperabilitySignoffActionItem] = Field(default_factory=list, alias="actionItems")
    pending_action_ids: list[str] = Field(default_factory=list, alias="pendingActionIds")
    acknowledged_action_ids: list[str] = Field(default_factory=list, alias="acknowledgedActionIds")
    completed_action_ids: list[str] = Field(default_factory=list, alias="completedActionIds")
    waived_action_ids: list[str] = Field(default_factory=list, alias="waivedActionIds")
    unresolved_blocking_action_ids: list[str] = Field(default_factory=list, alias="unresolvedBlockingActionIds")
    referenced_resources: list[ReviewResourceReference] = Field(default_factory=list, alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class ExportSanitisedPublicReviewDossierRequest(DietaryBaseModel):
    dossier: (
        VersionPinnedAdapterReviewDossier
        | VersionPinnedContaminantMonitoringReviewDossier
        | VersionPinnedMetalsMonitoringReviewDossier
        | VersionPinnedScientificFollowUpOwnerSignoffDossier
        | VersionPinnedTradeRiskReviewDossier
    )


class SanitisedPublicAdapterReviewBundle(DietaryBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_profile: BundleProfile = Field(default=BundleProfile.SANITISED_PUBLIC, alias="bundleProfile")
    review_status: str
    model_family: ModelFamily
    template_name: str
    walkthrough_name: str
    comparison_status: str = Field(alias="comparisonStatus")
    matched_field_count: int = Field(alias="matchedFieldCount", ge=0)
    mismatch_field_count: int = Field(alias="mismatchFieldCount", ge=0)
    mismatch_fields: list[str] = Field(default_factory=list, alias="mismatchFields")
    referenced_resources: list[ReviewResourceReference] = Field(alias="referencedResources")
    dependencies: list[DependencyDescriptor]
    notes: list[str] = Field(default_factory=list)


class SanitisedPublicContaminantMonitoringReviewBundle(DietaryBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_profile: BundleProfile = Field(default=BundleProfile.SANITISED_PUBLIC, alias="bundleProfile")
    source_bundle_id: str = Field(alias="sourceBundleId")
    source_packet_id: str = Field(alias="sourcePacketId")
    check_status: ReadinessStatus = Field(alias="checkStatus")
    overall_signoff_status: InteroperabilitySignoffStatus = Field(alias="overallSignoffStatus")
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str
    authority: str | None = None
    dataset_id: str | None = Field(default=None, alias="datasetId")
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    submission_candidate_allowed: bool = Field(alias="submissionCandidateAllowed")
    reporting_profile_summary: ReportingProfileApplicabilitySummary | None = Field(
        default=None,
        alias="reportingProfileSummary",
    )
    pending_action_ids: list[str] = Field(default_factory=list, alias="pendingActionIds")
    acknowledged_action_ids: list[str] = Field(default_factory=list, alias="acknowledgedActionIds")
    completed_action_ids: list[str] = Field(default_factory=list, alias="completedActionIds")
    waived_action_ids: list[str] = Field(default_factory=list, alias="waivedActionIds")
    unresolved_blocking_action_ids: list[str] = Field(default_factory=list, alias="unresolvedBlockingActionIds")
    referenced_resources: list[ReviewResourceReference] = Field(alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class SanitisedPublicMetalsMonitoringReviewBundle(DietaryBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_profile: BundleProfile = Field(default=BundleProfile.SANITISED_PUBLIC, alias="bundleProfile")
    source_bundle_id: str = Field(alias="sourceBundleId")
    source_packet_id: str = Field(alias="sourcePacketId")
    overall_signoff_status: InteroperabilitySignoffStatus = Field(alias="overallSignoffStatus")
    contaminant_family: ContaminantFamily = Field(alias="contaminantFamily")
    jurisdiction: str | None = None
    authority: str | None = None
    overall_submission_use: SubmissionUse = Field(alias="overallSubmissionUse")
    submission_candidate_allowed: bool = Field(alias="submissionCandidateAllowed")
    priority_food_groups: list[str] = Field(default_factory=list, alias="priorityFoodGroups")
    high_attention_foods: list[str] = Field(default_factory=list, alias="highAttentionFoods")
    focus_foods: list[str] = Field(default_factory=list, alias="focusFoods")
    sensitive_population_groups: list[str] = Field(default_factory=list, alias="sensitivePopulationGroups")
    trend_signals: list[str] = Field(default_factory=list, alias="trendSignals")
    pending_action_ids: list[str] = Field(default_factory=list, alias="pendingActionIds")
    acknowledged_action_ids: list[str] = Field(default_factory=list, alias="acknowledgedActionIds")
    completed_action_ids: list[str] = Field(default_factory=list, alias="completedActionIds")
    waived_action_ids: list[str] = Field(default_factory=list, alias="waivedActionIds")
    unresolved_blocking_action_ids: list[str] = Field(default_factory=list, alias="unresolvedBlockingActionIds")
    referenced_resources: list[ReviewResourceReference] = Field(alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class SanitisedPublicTradeRiskReviewBundle(DietaryBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_profile: BundleProfile = Field(default=BundleProfile.SANITISED_PUBLIC, alias="bundleProfile")
    review_status: str = Field(alias="reviewStatus")
    trade_report: SanitisedPublicTradeRiskReport = Field(alias="tradeReport")
    review_prompts: list[TradeRiskReviewPrompt] = Field(default_factory=list, alias="reviewPrompts")
    documentation_resource_uri: str = Field(default="docs://trade-risk-review", alias="documentationResourceUri")
    referenced_resources: list[ReviewResourceReference] = Field(alias="referencedResources")
    dependencies: list[DependencyDescriptor] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SanitisedPublicScientificFollowUpOwnerSignoffBundle(DietaryBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_profile: BundleProfile = Field(default=BundleProfile.SANITISED_PUBLIC, alias="bundleProfile")
    source_bundle_id: str = Field(alias="sourceBundleId")
    source_packet_id: str = Field(alias="sourcePacketId")
    source_dossier_status: str = Field(alias="sourceDossierStatus")
    overall_signoff_status: InteroperabilitySignoffStatus = Field(alias="overallSignoffStatus")
    overall_status: ReadinessStatus = Field(alias="overallStatus")
    target_profile: RegulatoryReadinessProfile = Field(alias="targetProfile")
    owner_lane: ScientificFollowUpOwnerLane = Field(alias="ownerLane")
    due_state_filter: list[ScientificFollowUpDueState] = Field(default_factory=list, alias="dueStateFilter")
    pending_action_ids: list[str] = Field(default_factory=list, alias="pendingActionIds")
    acknowledged_action_ids: list[str] = Field(default_factory=list, alias="acknowledgedActionIds")
    completed_action_ids: list[str] = Field(default_factory=list, alias="completedActionIds")
    waived_action_ids: list[str] = Field(default_factory=list, alias="waivedActionIds")
    unresolved_blocking_action_ids: list[str] = Field(default_factory=list, alias="unresolvedBlockingActionIds")
    resolve_now_action_ids: list[str] = Field(default_factory=list, alias="resolveNowActionIds")
    review_this_cycle_action_ids: list[str] = Field(default_factory=list, alias="reviewThisCycleActionIds")
    track_in_progress_action_ids: list[str] = Field(default_factory=list, alias="trackInProgressActionIds")
    record_closure_action_ids: list[str] = Field(default_factory=list, alias="recordClosureActionIds")
    recommended_signoff_sequence: list[str] = Field(default_factory=list, alias="recommendedSignoffSequence")
    documentation_resource_uri: str = Field(alias="documentationResourceUri")
    referenced_resources: list[ReviewResourceReference] = Field(alias="referencedResources")
    notes: list[str] = Field(default_factory=list)


class SanitisedPublicReviewDossier(ContentHashIdModel):
    _content_hash_id_field = "dossier_id"
    _content_hash_id_prefix = "sanitised-review-dossier"
    schema_version: str = Field(default=SCHEMA_VERSION)
    dossier_id: str = Field(default_factory=lambda: f"sanitised-review-dossier-{uuid4().hex[:12]}")
    derived_from_dossier_id: str = Field(alias="derivedFromDossierId")
    bundle_profile: BundleProfile = Field(default=BundleProfile.SANITISED_PUBLIC, alias="bundleProfile")
    dossier_status: str
    source_workflow: str | None = Field(default=None, alias="sourceWorkflow")
    public_review_bundle: (
        SanitisedPublicAdapterReviewBundle
        | SanitisedPublicContaminantMonitoringReviewBundle
        | SanitisedPublicMetalsMonitoringReviewBundle
        | SanitisedPublicScientificFollowUpOwnerSignoffBundle
        | SanitisedPublicTradeRiskReviewBundle
    ) = Field(alias="publicReviewBundle")
    release_metadata: ReleaseMetadataSnapshot
    source_governance_snapshot: list[RegulatorySourceRecord] = Field(
        default_factory=list,
        alias="sourceGovernanceSnapshot",
    )
    model_governance_snapshot: ModelGovernanceRecord | None = Field(
        default=None,
        alias="modelGovernanceSnapshot",
    )
    emerging_contaminant_snapshot: EmergingContaminantRecord | None = Field(
        default=None,
        alias="emergingContaminantSnapshot",
    )
    legal_limit_reviews: list[ContaminantLegalLimitLookupResult] = Field(
        default_factory=list,
        alias="legalLimitReviews",
    )
    pinned_resources: list[PinnedResourceFingerprint] = Field(alias="pinnedResources")
    escalation_required: bool = Field(default=False, alias="escalationRequired")
    escalation_action_ids: list[str] = Field(default_factory=list, alias="escalationActionIds")
    sanitisation_records: list[SanitisationRecord] = Field(alias="sanitisationRecords")
    limitations: list[LimitationNote] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ExportPbpkOralInputRequest(DietaryBaseModel):
    scenario: DietaryIntakeScenarioDefinition
    summary: DietaryIntakeSummary
    dosing_interval_hours: float = Field(default=24.0, gt=0.0)
    exposure_plausibility_records: list[ExposurePlausibilityRecord] = Field(
        default_factory=list,
        alias="exposurePlausibilityRecords",
    )


class ExportToxclawDietaryEvidenceBundleRequest(DietaryBaseModel):
    scenario: DietaryIntakeScenarioDefinition
    summary: DietaryIntakeSummary
