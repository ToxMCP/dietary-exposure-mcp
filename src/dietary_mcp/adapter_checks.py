from __future__ import annotations

import csv
from collections.abc import Iterable
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from dietary_mcp.adapter_harness import (
    TABULAR_FIELD_ALIASES,
    build_external_adapter_summary_from_csv,
)
from dietary_mcp.errors import DietaryRegistryError, DietaryValidationError
from dietary_mcp.models import (
    AdapterImportCheckProfileSelection,
    AdapterImportCheckResult,
    AdapterImportDeclaredTotals,
    AdapterImportHeaderResolution,
    AdapterNormalizedProjection,
    AdapterNormalizedProjectionContribution,
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    CheckAdapterImportRequest,
    SelectConsumptionProfileRequest,
)
from dietary_mcp.template_assets import read_adapter_template_manifest

if TYPE_CHECKING:
    from dietary_mcp.runtime import DietaryRuntime


def _normalize_header(header: str) -> str:
    return "".join(character for character in header.strip().lower() if character.isalnum() or character == "_")


def resolve_template_for_model_family(repo_root: Path, model_family: str) -> dict:
    manifest = read_adapter_template_manifest(repo_root)
    for item in manifest["templates"]:
        if item["modelFamily"] == model_family:
            return item
    raise DietaryRegistryError(
        code="missing_adapter_template",
        message=f"No adapter template is registered for model family {model_family}.",
        suggestion="Publish a matching adapter input template before exposing adapter validation tooling.",
    )


def read_csv_headers(csv_text: str) -> list[str]:
    rows = csv.reader(StringIO(csv_text))
    try:
        headers = next(rows)
    except StopIteration as exc:
        raise DietaryValidationError(
            code="adapter_tabular_missing_header",
            message="No CSV header row was found in the supplied adapter text.",
            suggestion="Provide a header row that matches one of the published adapter templates.",
        ) from exc
    if not headers:
        raise DietaryValidationError(
            code="adapter_tabular_empty_header",
            message="The supplied adapter CSV header row is empty.",
            suggestion="Provide at least one header column in the CSV payload.",
        )
    return headers


def build_header_resolution(headers: Iterable[str]) -> list[AdapterImportHeaderResolution]:
    resolutions = []
    alias_map = {
        _normalize_header(alias): canonical_field
        for canonical_field, aliases in TABULAR_FIELD_ALIASES.items()
        for alias in aliases
    }
    for header in headers:
        canonical_field = alias_map.get(_normalize_header(header))
        resolutions.append(
            AdapterImportHeaderResolution(
                header=header,
                canonical_field=canonical_field,
                recognized=canonical_field is not None,
            )
        )
    return resolutions


def build_normalized_projection(summary) -> AdapterNormalizedProjection:
    return AdapterNormalizedProjection(
        scenario_class=summary.scenario_class,
        intake_window=summary.intake_window_semantic,
        population_group=summary.population_group,
        region_id=summary.region_id,
        body_weight_kg=summary.body_weight_kg,
        total_intake_mg_per_kg_bw_per_day=summary.total_intake_mg_per_kg_bw_per_day,
        lower_bound_mg_per_kg_bw_per_day=summary.lower_bound_total_intake_mg_per_kg_bw_per_day,
        upper_bound_mg_per_kg_bw_per_day=summary.upper_bound_total_intake_mg_per_kg_bw_per_day,
        commodity_codes=[item.commodity.commodity_code for item in summary.commodity_contributions],
        commodity_contributions=[
            AdapterNormalizedProjectionContribution(
                commodity_code=item.commodity.commodity_code,
                canonical_name=item.commodity.canonical_name,
                foodex2_code=item.commodity.foodex2_code,
                rpc_code=item.commodity.rpc_code,
                rpcd_code=item.commodity.rpcd_code,
                processed_status=item.commodity.processed_status,
                mapping_confidence=item.commodity.mapping_confidence,
                contribution_mg_per_kg_bw_per_day=item.contribution_mg_per_kg_bw_per_day,
                fraction_of_total=item.fraction_of_total,
                residue_concentration_mg_per_kg=item.residue_concentration_mg_per_kg,
                consumption_kg_per_day=item.consumption_kg_per_day,
                applied_processing_factor=item.applied_processing_factor,
                lower_bound_mg_per_kg_bw_per_day=item.lower_bound_intake_mg_per_kg_bw_per_day,
                upper_bound_mg_per_kg_bw_per_day=item.upper_bound_intake_mg_per_kg_bw_per_day,
            )
            for item in summary.commodity_contributions
        ],
        dominant_commodity_codes=[item.commodity.commodity_code for item in summary.dominant_commodity_contributors],
        source_ids=sorted({item.source_id for item in summary.provenance.source_references}),
        quality_flag_codes=sorted({item.code for item in summary.quality_flags}),
        limitation_codes=sorted({item.code for item in summary.limitations}),
        assumption_parameters=sorted({item.parameter for item in summary.assumptions_applied}),
    )


def build_adapter_import_check_result(
    runtime: "DietaryRuntime",
    request: CheckAdapterImportRequest,
) -> AdapterImportCheckResult:
    headers = read_csv_headers(request.csv_text)
    header_resolution = build_header_resolution(headers)
    template = resolve_template_for_model_family(runtime.repo_root, request.model_family.value)

    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity=request.chemical_identity,
            region_id=request.region_id,
            residue_records=request.residue_records,
        )
    )
    consumption_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            region_id=request.region_id,
            population_group=request.population_group,
            intake_window=request.intake_window,
            required_commodity_codes=[item.commodity_code for item in request.residue_records],
        )
    ).profile
    scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=request.chemical_identity,
            residue_profile=residue_profile,
            consumption_profile=consumption_profile,
            scenario_class=request.scenario_class,
            intake_window_semantic=request.intake_window,
            fit_for_purpose=request.fit_for_purpose,
            model_family=request.model_family,
        )
    )
    payload = build_external_adapter_summary_from_csv(
        model_family=request.model_family,
        external_case_id=request.external_case_id,
        external_engine_version=request.external_engine_version,
        total_intake_mg_per_kg_bw_per_day=request.declared_total_intake_mg_per_kg_bw_per_day,
        lower_bound_total_intake_mg_per_kg_bw_per_day=request.declared_lower_bound_mg_per_kg_bw_per_day,
        upper_bound_total_intake_mg_per_kg_bw_per_day=request.declared_upper_bound_mg_per_kg_bw_per_day,
        csv_text=request.csv_text,
    )
    summary = runtime.normalize_external_adapter_summary(payload, scenario)

    return AdapterImportCheckResult(
        model_family=request.model_family,
        template_name=template["name"],
        walkthrough_name=template.get("walkthroughName"),
        template_resource_uri=f"adapter-template://{template['name']}",
        profile_selection=AdapterImportCheckProfileSelection(
            region_id=request.region_id,
            population_group=request.population_group,
            intake_window=request.intake_window,
            scenario_class=request.scenario_class,
        ),
        chemical_identity=request.chemical_identity,
        declared_totals=AdapterImportDeclaredTotals(
            total_intake_mg_per_kg_bw_per_day=request.declared_total_intake_mg_per_kg_bw_per_day,
            lower_bound_mg_per_kg_bw_per_day=request.declared_lower_bound_mg_per_kg_bw_per_day,
            upper_bound_mg_per_kg_bw_per_day=request.declared_upper_bound_mg_per_kg_bw_per_day,
        ),
        input_headers=headers,
        header_resolution=header_resolution,
        unmapped_headers=[item.header for item in header_resolution if not item.recognized],
        normalized_projection=build_normalized_projection(summary),
        notes=[
            "Adapter import checks normalize supplied CSV text through the adapter harness and return a stable projection without runtime-generated IDs or timestamps.",
            (
                "Successful results confirm CSV structure, numeric coercion, contribution-total "
                "reconciliation, commodity resolution, and profile selection for the declared scenario."
            ),
            "This tool validates a harnessed compatibility pathway only and does not execute an official PRIMo or DEEM engine.",
        ],
    )
