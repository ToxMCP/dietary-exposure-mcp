from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from io import StringIO

from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.models import (
    DietaryAssumptionRecord,
    DietaryBaseModel,
    DietaryContributionRecord,
    DietaryIntakeScenarioDefinition,
    DietaryIntakeSummary,
    LimitationNote,
    ModelFamily,
    QualityFlag,
    ScenarioClass,
    Severity,
    SourceReference,
)
from dietary_mcp.package_metadata import VERSION
from dietary_mcp.provenance import ProvenanceBuilder
from dietary_mcp.result_meta import ResultMetadata
from pydantic import Field, model_validator


FAMILY_SOURCE_IDS = {
    ModelFamily.ADAPTER_STUB: [],
    ModelFamily.EFSA_PRIMO_ADAPTER: ["efsa.primo", "efsa.default_body_weights.2012"],
    ModelFamily.EPA_DEEM_ADAPTER: ["epa.deem.fcid.4_02"],
}

TABULAR_FIELD_ALIASES = {
    "commodity_code": ["commodity_code", "commodity", "food", "food_code", "commoditycode"],
    "contribution_mg_per_kg_bw_per_day": [
        "contribution_mg_per_kg_bw_per_day",
        "exposure_mg_per_kg_bw_per_day",
        "exposure_mgkgbwday",
        "iedi_mgkgbwday",
        "iesti_mgkgbwday",
    ],
    "residue_concentration_mg_per_kg": [
        "residue_concentration_mg_per_kg",
        "residue_mg_per_kg",
        "residue_mgkg",
        "hr_mgkg",
        "stmr_mgkg",
    ],
    "consumption_kg_per_day": [
        "consumption_kg_per_day",
        "consumption_kgday",
        "consumption_kg_day",
        "food_consumption_kg_per_day",
    ],
    "applied_processing_factor": [
        "applied_processing_factor",
        "processing_factor",
        "pf",
    ],
    "lower_bound_intake_mg_per_kg_bw_per_day": [
        "lower_bound_intake_mg_per_kg_bw_per_day",
        "lower_exposure_mg_per_kg_bw_per_day",
        "lb_mgkgbwday",
    ],
    "upper_bound_intake_mg_per_kg_bw_per_day": [
        "upper_bound_intake_mg_per_kg_bw_per_day",
        "upper_exposure_mg_per_kg_bw_per_day",
        "ub_mgkgbwday",
    ],
}


class ExternalAdapterContributionPayload(DietaryBaseModel):
    commodity_code: str = Field(min_length=1)
    contribution_mg_per_kg_bw_per_day: float = Field(ge=0.0)
    residue_concentration_mg_per_kg: float = Field(ge=0.0)
    consumption_kg_per_day: float = Field(ge=0.0)
    applied_processing_factor: float = Field(gt=0.0)
    lower_bound_intake_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    upper_bound_intake_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    source_reference: SourceReference | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> "ExternalAdapterContributionPayload":
        if (
            self.lower_bound_intake_mg_per_kg_bw_per_day is not None
            and self.lower_bound_intake_mg_per_kg_bw_per_day > self.contribution_mg_per_kg_bw_per_day
        ):
            raise ValueError("lower contribution bound cannot exceed the point contribution")
        if (
            self.upper_bound_intake_mg_per_kg_bw_per_day is not None
            and self.upper_bound_intake_mg_per_kg_bw_per_day < self.contribution_mg_per_kg_bw_per_day
        ):
            raise ValueError("upper contribution bound cannot be lower than the point contribution")
        return self


class ExternalAdapterSummaryPayload(DietaryBaseModel):
    model_family: ModelFamily
    external_case_id: str = Field(min_length=1)
    external_engine_version: str = Field(min_length=1)
    total_intake_mg_per_kg_bw_per_day: float = Field(ge=0.0)
    lower_bound_total_intake_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    upper_bound_total_intake_mg_per_kg_bw_per_day: float | None = Field(default=None, ge=0.0)
    contributions: list[ExternalAdapterContributionPayload]
    assumptions_applied: list[DietaryAssumptionRecord] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_payload(self) -> "ExternalAdapterSummaryPayload":
        if self.model_family == ModelFamily.REFERENCE_DIETARY:
            raise ValueError("external adapter payloads must use an adapter model family")
        if (
            self.lower_bound_total_intake_mg_per_kg_bw_per_day is not None
            and self.lower_bound_total_intake_mg_per_kg_bw_per_day > self.total_intake_mg_per_kg_bw_per_day
        ):
            raise ValueError("lower total intake bound cannot exceed the point estimate")
        if (
            self.upper_bound_total_intake_mg_per_kg_bw_per_day is not None
            and self.upper_bound_total_intake_mg_per_kg_bw_per_day < self.total_intake_mg_per_kg_bw_per_day
        ):
            raise ValueError("upper total intake bound cannot be lower than the point estimate")
        return self


def _normalize_header(header: str) -> str:
    return "".join(character for character in header.strip().lower() if character.isalnum() or character == "_")


def _coerce_float(value: object, field_name: str, row_index: int) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(str(value).strip())
    except ValueError as exc:
        raise DietaryValidationError(
            code="adapter_tabular_numeric_parse_error",
            message=f"Unable to parse numeric value for {field_name} in adapter row {row_index}.",
            suggestion="Provide numeric values for tabular adapter imports.",
            details={"field": field_name, "rowIndex": row_index, "rawValue": str(value)},
        ) from exc


def _extract_tabular_value(
    row: Mapping[str, object],
    canonical_field: str,
    row_index: int,
    required: bool,
) -> object | None:
    normalized = {_normalize_header(key): value for key, value in row.items()}
    for alias in TABULAR_FIELD_ALIASES[canonical_field]:
        value = normalized.get(_normalize_header(alias))
        if value not in ("", None):
            return value
    if required:
        raise DietaryValidationError(
            code="adapter_tabular_missing_field",
            message=f"Missing required adapter field {canonical_field} in row {row_index}.",
            suggestion="Provide the required column or one of its documented aliases.",
            details={"field": canonical_field, "rowIndex": row_index},
        )
    return None


def build_external_adapter_summary_from_rows(
    *,
    model_family: ModelFamily,
    external_case_id: str,
    external_engine_version: str,
    total_intake_mg_per_kg_bw_per_day: float,
    rows: Iterable[Mapping[str, object]],
    lower_bound_total_intake_mg_per_kg_bw_per_day: float | None = None,
    upper_bound_total_intake_mg_per_kg_bw_per_day: float | None = None,
    assumptions_applied: list[DietaryAssumptionRecord] | None = None,
    source_references: list[SourceReference] | None = None,
    notes: list[str] | None = None,
) -> ExternalAdapterSummaryPayload:
    contributions = []
    for row_index, row in enumerate(rows, start=1):
        contributions.append(
            ExternalAdapterContributionPayload(
                commodity_code=str(_extract_tabular_value(row, "commodity_code", row_index, required=True)).strip(),
                contribution_mg_per_kg_bw_per_day=_coerce_float(
                    _extract_tabular_value(
                        row,
                        "contribution_mg_per_kg_bw_per_day",
                        row_index,
                        required=True,
                    ),
                    "contribution_mg_per_kg_bw_per_day",
                    row_index,
                ),
                residue_concentration_mg_per_kg=_coerce_float(
                    _extract_tabular_value(
                        row,
                        "residue_concentration_mg_per_kg",
                        row_index,
                        required=True,
                    ),
                    "residue_concentration_mg_per_kg",
                    row_index,
                ),
                consumption_kg_per_day=_coerce_float(
                    _extract_tabular_value(row, "consumption_kg_per_day", row_index, required=True),
                    "consumption_kg_per_day",
                    row_index,
                ),
                applied_processing_factor=_coerce_float(
                    _extract_tabular_value(row, "applied_processing_factor", row_index, required=True),
                    "applied_processing_factor",
                    row_index,
                ),
                lower_bound_intake_mg_per_kg_bw_per_day=_coerce_float(
                    _extract_tabular_value(
                        row,
                        "lower_bound_intake_mg_per_kg_bw_per_day",
                        row_index,
                        required=False,
                    ),
                    "lower_bound_intake_mg_per_kg_bw_per_day",
                    row_index,
                ),
                upper_bound_intake_mg_per_kg_bw_per_day=_coerce_float(
                    _extract_tabular_value(
                        row,
                        "upper_bound_intake_mg_per_kg_bw_per_day",
                        row_index,
                        required=False,
                    ),
                    "upper_bound_intake_mg_per_kg_bw_per_day",
                    row_index,
                ),
            )
        )
    return ExternalAdapterSummaryPayload(
        model_family=model_family,
        external_case_id=external_case_id,
        external_engine_version=external_engine_version,
        total_intake_mg_per_kg_bw_per_day=total_intake_mg_per_kg_bw_per_day,
        lower_bound_total_intake_mg_per_kg_bw_per_day=lower_bound_total_intake_mg_per_kg_bw_per_day,
        upper_bound_total_intake_mg_per_kg_bw_per_day=upper_bound_total_intake_mg_per_kg_bw_per_day,
        contributions=contributions,
        assumptions_applied=assumptions_applied or [],
        source_references=source_references or [],
        notes=notes or [],
    )


def build_external_adapter_summary_from_csv(
    *,
    model_family: ModelFamily,
    external_case_id: str,
    external_engine_version: str,
    total_intake_mg_per_kg_bw_per_day: float,
    csv_text: str,
    lower_bound_total_intake_mg_per_kg_bw_per_day: float | None = None,
    upper_bound_total_intake_mg_per_kg_bw_per_day: float | None = None,
    assumptions_applied: list[DietaryAssumptionRecord] | None = None,
    source_references: list[SourceReference] | None = None,
    notes: list[str] | None = None,
) -> ExternalAdapterSummaryPayload:
    rows = list(csv.DictReader(StringIO(csv_text)))
    if not rows:
        raise DietaryValidationError(
            code="adapter_tabular_no_rows",
            message="No adapter rows were found in the supplied CSV text.",
            suggestion="Provide at least one contribution row in the CSV payload.",
        )
    return build_external_adapter_summary_from_rows(
        model_family=model_family,
        external_case_id=external_case_id,
        external_engine_version=external_engine_version,
        total_intake_mg_per_kg_bw_per_day=total_intake_mg_per_kg_bw_per_day,
        rows=rows,
        lower_bound_total_intake_mg_per_kg_bw_per_day=lower_bound_total_intake_mg_per_kg_bw_per_day,
        upper_bound_total_intake_mg_per_kg_bw_per_day=upper_bound_total_intake_mg_per_kg_bw_per_day,
        assumptions_applied=assumptions_applied,
        source_references=source_references,
        notes=notes,
    )


def _adapter_source_references(
    payload: ExternalAdapterSummaryPayload,
    defaults_registry: DefaultsRegistry,
) -> list[SourceReference]:
    refs = list(payload.source_references)
    for source_id in FAMILY_SOURCE_IDS.get(payload.model_family, []):
        refs.append(defaults_registry.source_catalog_reference(source_id))
    return refs


def normalize_external_adapter_summary(
    payload: ExternalAdapterSummaryPayload,
    scenario: DietaryIntakeScenarioDefinition,
    defaults_registry: DefaultsRegistry,
    provenance_builder: ProvenanceBuilder,
) -> DietaryIntakeSummary:
    if scenario.model_family != payload.model_family:
        raise DietaryValidationError(
            code="adapter_model_family_mismatch",
            message="External adapter payload model family does not match the scenario.",
            suggestion="Align the scenario model_family with the adapter payload before normalization.",
            details={
                "scenarioModelFamily": scenario.model_family.value,
                "payloadModelFamily": payload.model_family.value,
            },
        )

    source_references = _adapter_source_references(payload, defaults_registry)
    contributions = []
    quality_flags = list(scenario.quality_flags)
    limitations = list(scenario.limitations)

    for item in payload.contributions:
        resolution = defaults_registry.resolve_commodity(item.commodity_code)
        quality_flags.extend(resolution.quality_flags)
        if item.source_reference:
            source_references.append(item.source_reference)
        if resolution.commodity.source_reference:
            source_references.append(resolution.commodity.source_reference)

        contributions.append(
            DietaryContributionRecord(
                commodity=resolution.commodity,
                intake_window_semantic=scenario.intake_window_semantic,
                residue_concentration_mg_per_kg=item.residue_concentration_mg_per_kg,
                consumption_kg_per_day=item.consumption_kg_per_day,
                applied_processing_factor=item.applied_processing_factor,
                contribution_mg_per_kg_bw_per_day=item.contribution_mg_per_kg_bw_per_day,
                fraction_of_total=0.0,
                lower_bound_intake_mg_per_kg_bw_per_day=item.lower_bound_intake_mg_per_kg_bw_per_day,
                upper_bound_intake_mg_per_kg_bw_per_day=item.upper_bound_intake_mg_per_kg_bw_per_day,
                quality_flags=resolution.quality_flags,
                limitations=[
                    LimitationNote(
                        code="external_adapter_contribution",
                        message=(
                            f"{payload.model_family.value} contribution was normalized from an external adapter payload."
                        ),
                    )
                ],
            )
        )

    total_from_contributions = sum(item.contribution_mg_per_kg_bw_per_day for item in contributions)
    tolerance = max(1e-9, abs(payload.total_intake_mg_per_kg_bw_per_day) * 1e-6)
    if abs(total_from_contributions - payload.total_intake_mg_per_kg_bw_per_day) > tolerance:
        raise DietaryValidationError(
            code="adapter_total_mismatch",
            message="External adapter contribution totals do not match the declared summary total.",
            suggestion="Recompute the external contribution rows or correct the declared total before normalization.",
            details={
                "declaredTotal": payload.total_intake_mg_per_kg_bw_per_day,
                "contributionTotal": total_from_contributions,
            },
        )

    lower_from_contributions = sum(
        item.lower_bound_intake_mg_per_kg_bw_per_day or item.contribution_mg_per_kg_bw_per_day
        for item in contributions
    )
    upper_from_contributions = sum(
        item.upper_bound_intake_mg_per_kg_bw_per_day or item.contribution_mg_per_kg_bw_per_day
        for item in contributions
    )
    if scenario.scenario_class == ScenarioClass.POINT_ESTIMATE:
        lower_bound = None
        upper_bound = None
    else:
        lower_bound = payload.lower_bound_total_intake_mg_per_kg_bw_per_day or lower_from_contributions
        upper_bound = payload.upper_bound_total_intake_mg_per_kg_bw_per_day or upper_from_contributions
        if payload.lower_bound_total_intake_mg_per_kg_bw_per_day is None or payload.upper_bound_total_intake_mg_per_kg_bw_per_day is None:
            limitations.append(
                LimitationNote(
                    code="external_bounds_imputed",
                    message=(
                        "External adapter payload omitted explicit total bounds, so bounded totals were re-aggregated "
                        "from contribution rows."
                    ),
                )
            )

    normalized_contributions = []
    for item in contributions:
        fraction = (
            item.contribution_mg_per_kg_bw_per_day / payload.total_intake_mg_per_kg_bw_per_day
            if payload.total_intake_mg_per_kg_bw_per_day
            else 0.0
        )
        normalized_contributions.append(item.model_copy(update={"fraction_of_total": fraction}))

    assumptions = list(payload.assumptions_applied)
    assumptions.append(
        provenance_builder.derived(
            parameter=f"adapter_case:{payload.model_family.value}",
            value=payload.external_case_id,
            unit=None,
            rationale="External adapter case identifier preserved during normalization.",
        )
    )
    assumptions.append(
        provenance_builder.derived(
            parameter=f"adapter_engine_version:{payload.model_family.value}",
            value=payload.external_engine_version,
            unit=None,
            rationale="External adapter engine version preserved during normalization.",
        )
    )
    assumptions.append(
        provenance_builder.derived(
            parameter=f"adapter_contribution_count:{payload.model_family.value}",
            value=len(normalized_contributions),
            unit="count",
            rationale="Number of external contribution rows normalized into the dietary summary.",
        )
    )

    limitations.extend(
        LimitationNote(code="external_adapter_note", message=note)
        for note in payload.notes
    )
    limitations.append(
        LimitationNote(
            code="external_adapter_normalization",
            message=(
                f"{payload.model_family.value} summary was normalized from an external-style adapter payload and "
                "should be treated as a harnessed compatibility pathway, not an official engine execution."
            ),
        )
    )
    quality_flags.append(
        QualityFlag(
            code="external_adapter_normalized",
            severity=Severity.INFO,
            message=f"{payload.model_family.value} output was normalized through the adapter harness.",
        )
    )

    dominant_count = int(defaults_registry.parameter_value("max_dominant_contributors"))
    dominant = sorted(
        normalized_contributions,
        key=lambda item: item.contribution_mg_per_kg_bw_per_day,
        reverse=True,
    )[:dominant_count]

    return DietaryIntakeSummary(
        scenario_id=scenario.scenario_id,
        scenario_class=scenario.scenario_class,
        intake_window_semantic=scenario.intake_window_semantic,
        total_intake_mg_per_kg_bw_per_day=payload.total_intake_mg_per_kg_bw_per_day,
        lower_bound_total_intake_mg_per_kg_bw_per_day=lower_bound,
        upper_bound_total_intake_mg_per_kg_bw_per_day=upper_bound,
        population_group=scenario.population_context.population_group,
        region_id=scenario.population_context.region_id,
        body_weight_kg=scenario.population_context.body_weight_kg,
        fit_for_purpose=scenario.fit_for_purpose,
        commodity_contributions=normalized_contributions,
        dominant_commodity_contributors=dominant,
        assumptions_applied=assumptions,
        provenance=provenance_builder.bundle(scenario.provenance.source_references + source_references),
        quality_flags=quality_flags,
        limitations=limitations,
        result_metadata=ResultMetadata.completed(
            result_id=f"normalized-{scenario.scenario_id}-{payload.model_family.value}-{VERSION}"
        ),
    )
