from __future__ import annotations

from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.errors import DietaryRegistryError
from dietary_mcp.models import (
    CommodityConsumptionRecord,
    DietaryContributionRecord,
    DietaryIntakeScenarioDefinition,
    DietaryIntakeSummary,
    LimitationNote,
    ModelFamily,
    QualityFlag,
    ScenarioClass,
    Severity,
    SourceClassification,
)
from dietary_mcp.package_metadata import VERSION
from dietary_mcp.plugins.base import PluginKey
from dietary_mcp.provenance import ProvenanceBuilder
from dietary_mcp.result_meta import ResultMetadata


class ReferenceDietaryPlugin:
    limitations = [
        "Reference dietary plugin is deterministic and screening-oriented.",
        "Reference dietary plugin does not implement full probabilistic population variability.",
    ]

    def __init__(
        self,
        defaults_registry: DefaultsRegistry,
        provenance_builder: ProvenanceBuilder,
        scenario_class: ScenarioClass,
    ) -> None:
        self.defaults_registry = defaults_registry
        self.provenance_builder = provenance_builder
        self.key = PluginKey(
            scenario_class=scenario_class,
            model_family=ModelFamily.REFERENCE_DIETARY,
        )

    def _consumption_lookup(self, profile) -> dict[str, CommodityConsumptionRecord]:
        return {
            item.commodity.commodity_code: item
            for item in profile.commodity_consumption
        }

    def _source_classification_for_residue(self, source_type) -> SourceClassification:
        if source_type.value == "curated_default":
            return SourceClassification.CURATED_DEFAULT
        if source_type.value == "reconciled":
            return SourceClassification.DERIVED
        return SourceClassification.USER_INPUT

    def _build_contribution_records(self, scenario: DietaryIntakeScenarioDefinition):
        contributions = []
        assumptions = []
        quality_flags = []
        limitations = [LimitationNote(code="screening_model", message=text) for text in self.limitations]
        consumption_lookup = self._consumption_lookup(scenario.consumption_profile)
        body_weight = scenario.population_context.body_weight_kg

        for record in scenario.residue_profile.records:
            consumption_record = consumption_lookup.get(record.commodity.commodity_code)
            if not consumption_record:
                quality_flags.append(
                    QualityFlag(
                        code="missing_consumption_mapping",
                        severity=Severity.WARNING,
                        message=f"No consumption mapping was available for {record.commodity.commodity_code}.",
                    )
                )
                limitations.append(
                    LimitationNote(
                        code="missing_consumption_mapping",
                        message=f"{record.commodity.canonical_name} was excluded because the selected profile has no direct mapping.",
                    )
                )
                continue

            if scenario.intake_window_semantic.value == "acute":
                consumption_kg_per_day = consumption_record.acute_kg_per_day or 0.0
            else:
                consumption_kg_per_day = consumption_record.chronic_kg_per_day or 0.0

            adjusted_point = record.residue_concentration_mg_per_kg * record.processing_factor
            adjusted_lower = (
                (
                    record.lower_bound_mg_per_kg
                    if record.lower_bound_mg_per_kg is not None
                    else record.residue_concentration_mg_per_kg
                )
                * record.processing_factor
            )
            adjusted_upper = (
                (
                    record.upper_bound_mg_per_kg
                    if record.upper_bound_mg_per_kg is not None
                    else record.residue_concentration_mg_per_kg
                )
                * record.processing_factor
            )

            point_intake = adjusted_point * consumption_kg_per_day / body_weight
            lower_intake = adjusted_lower * consumption_kg_per_day / body_weight
            upper_intake = adjusted_upper * consumption_kg_per_day / body_weight

            if record.lower_bound_mg_per_kg is None or record.upper_bound_mg_per_kg is None:
                limitations.append(
                    LimitationNote(
                        code="bounded_input_missing",
                        message=f"{record.commodity.canonical_name} does not carry explicit residue bounds; bounded outputs collapse to the point estimate for this commodity.",
                    )
                )

            contributions.append(
                DietaryContributionRecord(
                    commodity=record.commodity,
                    intake_window_semantic=scenario.intake_window_semantic,
                    residue_concentration_mg_per_kg=record.residue_concentration_mg_per_kg,
                    consumption_kg_per_day=consumption_kg_per_day,
                    applied_processing_factor=record.processing_factor,
                    contribution_mg_per_kg_bw_per_day=point_intake,
                    fraction_of_total=0.0,
                    lower_bound_intake_mg_per_kg_bw_per_day=lower_intake,
                    upper_bound_intake_mg_per_kg_bw_per_day=upper_intake,
                    quality_flags=record.quality_flags,
                    limitations=record.limitations,
                )
            )

            assumptions.append(
                self.provenance_builder.user_input(
                    parameter=f"residue:{record.commodity.commodity_code}",
                    value=record.residue_concentration_mg_per_kg,
                    unit=record.residue_unit,
                    rationale=f"Residue concentration used for {record.commodity.canonical_name}.",
                    source_reference=record.source_reference,
                ).model_copy(
                    update={
                        "source_classification": self._source_classification_for_residue(record.source_type),
                    }
                )
            )
            assumptions.append(
                self.provenance_builder.curated_default(
                    parameter="default_processing_factor",
                    rationale=f"Base processing-factor governance path checked for {record.commodity.canonical_name}.",
                ).model_copy(
                    update={
                        "parameter": f"processing_factor:{record.commodity.commodity_code}",
                        "value": record.processing_factor,
                        "unit": "ratio",
                        "source_classification": record.processing_factor_source_classification,
                        "source_reference": record.processing_factor_source_reference,
                        "rationale": f"Processing factor applied to {record.commodity.canonical_name}.",
                    }
                )
            )
            assumptions.append(
                self.provenance_builder.curated_default(
                    parameter="max_dominant_contributors",
                    rationale=f"Contribution ranking used the governed cutoff while summarizing {record.commodity.canonical_name}.",
                ).model_copy(
                    update={
                        "parameter": f"consumption:{scenario.consumption_profile.profile_id}:{record.commodity.commodity_code}",
                        "value": consumption_kg_per_day,
                        "unit": "kg_food/day",
                        "source_reference": consumption_record.source_reference,
                        "rationale": f"{scenario.intake_window_semantic.value.capitalize()} consumption amount selected from the governed profile.",
                    }
                )
            )

        total = sum(item.contribution_mg_per_kg_bw_per_day for item in contributions)
        lower_total = sum(item.lower_bound_intake_mg_per_kg_bw_per_day or 0.0 for item in contributions)
        upper_total = sum(item.upper_bound_intake_mg_per_kg_bw_per_day or 0.0 for item in contributions)

        normalized_contributions = []
        for item in contributions:
            fraction = item.contribution_mg_per_kg_bw_per_day / total if total else 0.0
            normalized_contributions.append(item.model_copy(update={"fraction_of_total": fraction}))

        dominant_count = int(self.defaults_registry.parameter_value("max_dominant_contributors"))
        dominant = sorted(
            normalized_contributions,
            key=lambda item: item.contribution_mg_per_kg_bw_per_day,
            reverse=True,
        )[:dominant_count]

        return normalized_contributions, dominant, assumptions, quality_flags, limitations, total, lower_total, upper_total

    def run(self, scenario: DietaryIntakeScenarioDefinition) -> DietaryIntakeSummary:
        (
            contributions,
            dominant,
            assumptions,
            quality_flags,
            limitations,
            total,
            lower_total,
            upper_total,
        ) = self._build_contribution_records(scenario)

        if scenario.scenario_class == ScenarioClass.POINT_ESTIMATE:
            lower_bound = None
            upper_bound = None
        else:
            lower_bound = lower_total
            upper_bound = upper_total

        summary = DietaryIntakeSummary(
            scenario_id=scenario.scenario_id,
            scenario_class=scenario.scenario_class,
            intake_window_semantic=scenario.intake_window_semantic,
            total_intake_mg_per_kg_bw_per_day=total,
            lower_bound_total_intake_mg_per_kg_bw_per_day=lower_bound,
            upper_bound_total_intake_mg_per_kg_bw_per_day=upper_bound,
            population_group=scenario.population_context.population_group,
            region_id=scenario.population_context.region_id,
            body_weight_kg=scenario.population_context.body_weight_kg,
            fit_for_purpose=scenario.fit_for_purpose,
            commodity_contributions=contributions,
            dominant_commodity_contributors=dominant,
            assumptions_applied=assumptions,
            provenance=self.provenance_builder.bundle(scenario.provenance.source_references),
            quality_flags=quality_flags + scenario.quality_flags,
            limitations=limitations + scenario.limitations,
            result_metadata=ResultMetadata.completed(result_id=f"result-{scenario.scenario_id}-{VERSION}"),
        )
        return summary


class AdapterStubDietaryPlugin(ReferenceDietaryPlugin):
    limitations = [
        "Adapter stub reuses the reference dietary kernel in v0.1.",
        "External PRIMo- or DEEM-aligned adapters should replace this stub without changing public contracts.",
    ]

    def __init__(
        self,
        defaults_registry: DefaultsRegistry,
        provenance_builder: ProvenanceBuilder,
        scenario_class: ScenarioClass,
    ) -> None:
        super().__init__(defaults_registry, provenance_builder, scenario_class)
        self.key = PluginKey(
            scenario_class=scenario_class,
            model_family=ModelFamily.ADAPTER_STUB,
        )


class ExternalAdapterHarnessPlugin(ReferenceDietaryPlugin):
    adapter_source_ids: list[str] = []
    adapter_quality_flag_code = "adapter_harness"
    adapter_label = "External adapter harness"
    adapter_limitations = [
        "External adapter harness reuses the native deterministic kernel in v0.1.",
        "This harness proves contract normalization only and is not equivalent to the named external engine.",
    ]

    def __init__(
        self,
        defaults_registry: DefaultsRegistry,
        provenance_builder: ProvenanceBuilder,
        scenario_class: ScenarioClass,
        model_family: ModelFamily,
    ) -> None:
        super().__init__(defaults_registry, provenance_builder, scenario_class)
        self.key = PluginKey(scenario_class=scenario_class, model_family=model_family)

    def _adapter_source_references(self):
        refs = []
        for source_id in self.adapter_source_ids:
            try:
                refs.append(self.defaults_registry.source_catalog_reference(source_id))
            except DietaryRegistryError:
                continue
        return refs

    def run(self, scenario: DietaryIntakeScenarioDefinition) -> DietaryIntakeSummary:
        summary = super().run(scenario)
        adapter_refs = self._adapter_source_references()
        return summary.model_copy(
            update={
                "provenance": self.provenance_builder.bundle(
                    summary.provenance.source_references + adapter_refs
                ),
                "quality_flags": summary.quality_flags
                + [
                    QualityFlag(
                        code=self.adapter_quality_flag_code,
                        severity=Severity.INFO,
                        message=(
                            f"{self.adapter_label} currently normalizes through the native deterministic kernel "
                            "for contract-compatibility testing."
                        ),
                    )
                ],
                "limitations": summary.limitations
                + [LimitationNote(code="adapter_harness", message=text) for text in self.adapter_limitations],
            }
        )


class EfsaPrimoAdapterHarnessPlugin(ExternalAdapterHarnessPlugin):
    adapter_source_ids = ["efsa.primo", "efsa.default_body_weights.2012"]
    adapter_quality_flag_code = "efsa_primo_adapter_harness"
    adapter_label = "EFSA PRIMo-aligned harness"
    adapter_limitations = [
        "EFSA PRIMo-aligned harness currently reuses the native deterministic kernel in v0.1.",
        "No claim of official PRIMo engine equivalence, proprietary dataset reproduction, or regulatory endorsement is implied.",
    ]

    def __init__(
        self,
        defaults_registry: DefaultsRegistry,
        provenance_builder: ProvenanceBuilder,
        scenario_class: ScenarioClass,
    ) -> None:
        super().__init__(
            defaults_registry,
            provenance_builder,
            scenario_class,
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
        )


class EpaDeemAdapterHarnessPlugin(ExternalAdapterHarnessPlugin):
    adapter_source_ids = ["epa.deem.fcid.4_02"]
    adapter_quality_flag_code = "epa_deem_adapter_harness"
    adapter_label = "EPA DEEM-aligned harness"
    adapter_limitations = [
        "EPA DEEM-aligned harness currently reuses the native deterministic kernel in v0.1.",
        "No claim of official DEEM engine equivalence, proprietary dataset reproduction, or regulatory endorsement is implied.",
    ]

    def __init__(
        self,
        defaults_registry: DefaultsRegistry,
        provenance_builder: ProvenanceBuilder,
        scenario_class: ScenarioClass,
    ) -> None:
        super().__init__(
            defaults_registry,
            provenance_builder,
            scenario_class,
            model_family=ModelFamily.EPA_DEEM_ADAPTER,
        )
