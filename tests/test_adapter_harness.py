from pathlib import Path

import pytest

from dietary_mcp.adapter_harness import (
    ExternalAdapterContributionPayload,
    ExternalAdapterSummaryPayload,
    build_external_adapter_summary_from_csv,
    build_external_adapter_summary_from_rows,
    normalize_external_adapter_summary,
)
from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.models import (
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    DietaryCommodityResidueInput,
    IntakeWindowSemantic,
    ModelFamily,
    ResidueSourceType,
    ScenarioClass,
    SelectConsumptionProfileRequest,
)
from dietary_mcp.runtime import DietaryRuntime


def test_external_adapter_summary_normalizes_aliases_into_public_summary() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Adapter harness substance"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.2,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="milk",
                    residue_concentration_mg_per_kg=0.04,
                    source_type=ResidueSourceType.MONITORING,
                ),
            ],
        )
    )
    profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="adult_general",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["apples", "milk"],
        )
    ).profile
    scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=residue_profile.chemical_identity,
            residue_profile=residue_profile,
            consumption_profile=profile,
            scenario_class=ScenarioClass.POINT_ESTIMATE,
            intake_window_semantic=IntakeWindowSemantic.CHRONIC,
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
        )
    )
    payload = ExternalAdapterSummaryPayload(
        model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
        external_case_id="primo-case-001",
        external_engine_version="3.1-harness",
        total_intake_mg_per_kg_bw_per_day=0.00062,
        contributions=[
            ExternalAdapterContributionPayload(
                commodity_code="apple",
                contribution_mg_per_kg_bw_per_day=0.0005,
                residue_concentration_mg_per_kg=0.2,
                consumption_kg_per_day=0.18,
                applied_processing_factor=1.0,
            ),
            ExternalAdapterContributionPayload(
                commodity_code="whole_milk",
                contribution_mg_per_kg_bw_per_day=0.00012,
                residue_concentration_mg_per_kg=0.04,
                consumption_kg_per_day=0.22,
                applied_processing_factor=1.0,
            ),
        ],
        notes=["Synthetic PRIMo harness payload for normalization regression coverage."],
    )

    summary = normalize_external_adapter_summary(
        payload,
        scenario,
        runtime.defaults,
        runtime.provenance,
    )

    assert summary.total_intake_mg_per_kg_bw_per_day == pytest.approx(0.00062)
    assert {item.commodity.commodity_code for item in summary.commodity_contributions} == {"apples", "milk"}
    assert any(flag.code == "external_adapter_normalized" for flag in summary.quality_flags)
    assert any(ref.source_id == "efsa.primo" for ref in summary.provenance.source_references)


def test_external_adapter_summary_rejects_total_mismatch() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Adapter harness substance"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.2,
                    source_type=ResidueSourceType.MONITORING,
                )
            ],
        )
    )
    profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="adult_general",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["apples"],
        )
    ).profile
    scenario = runtime.build_dietary_intake_scenario(
        BuildDietaryIntakeScenarioRequest(
            chemical_identity=residue_profile.chemical_identity,
            residue_profile=residue_profile,
            consumption_profile=profile,
            scenario_class=ScenarioClass.POINT_ESTIMATE,
            intake_window_semantic=IntakeWindowSemantic.CHRONIC,
            model_family=ModelFamily.EPA_DEEM_ADAPTER,
        )
    )
    payload = ExternalAdapterSummaryPayload(
        model_family=ModelFamily.EPA_DEEM_ADAPTER,
        external_case_id="deem-case-001",
        external_engine_version="4.02-harness",
        total_intake_mg_per_kg_bw_per_day=0.0009,
        contributions=[
            ExternalAdapterContributionPayload(
                commodity_code="apples_raw",
                contribution_mg_per_kg_bw_per_day=0.0005,
                residue_concentration_mg_per_kg=0.2,
                consumption_kg_per_day=0.18,
                applied_processing_factor=1.0,
            )
        ],
    )

    with pytest.raises(DietaryValidationError) as exc:
        normalize_external_adapter_summary(
            payload,
            scenario,
            runtime.defaults,
            runtime.provenance,
        )
    assert exc.value.payload.code == "adapter_total_mismatch"


def test_tabular_row_builder_accepts_primo_style_aliases() -> None:
    payload = build_external_adapter_summary_from_rows(
        model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
        external_case_id="primo-tabular-001",
        external_engine_version="3.1-harness",
        total_intake_mg_per_kg_bw_per_day=0.00062,
        rows=[
            {
                "commodity": "apple",
                "iesti_mgkgbwday": "0.0005",
                "hr_mgkg": "0.2",
                "consumption_kg_day": "0.18",
                "pf": "1.0",
            },
            {
                "commodity": "whole_milk",
                "iesti_mgkgbwday": "0.00012",
                "hr_mgkg": "0.04",
                "consumption_kg_day": "0.22",
                "pf": "1.0",
            },
        ],
    )

    assert payload.model_family == ModelFamily.EFSA_PRIMO_ADAPTER
    assert [item.commodity_code for item in payload.contributions] == ["apple", "whole_milk"]
    assert payload.contributions[0].contribution_mg_per_kg_bw_per_day == pytest.approx(0.0005)


def test_csv_builder_accepts_deem_style_headers() -> None:
    payload = build_external_adapter_summary_from_csv(
        model_family=ModelFamily.EPA_DEEM_ADAPTER,
        external_case_id="deem-csv-001",
        external_engine_version="4.02-harness",
        total_intake_mg_per_kg_bw_per_day=0.00062,
        csv_text=(
            "food,exposure_mg_per_kg_bw_per_day,stmr_mgkg,food_consumption_kg_per_day,processing_factor\n"
            "apples_raw,0.0005,0.2,0.18,1.0\n"
            "cow_milk,0.00012,0.04,0.22,1.0\n"
        ),
    )

    assert payload.model_family == ModelFamily.EPA_DEEM_ADAPTER
    assert len(payload.contributions) == 2
    assert payload.contributions[1].commodity_code == "cow_milk"


def test_tabular_builder_rejects_missing_required_column() -> None:
    with pytest.raises(DietaryValidationError) as exc:
        build_external_adapter_summary_from_rows(
            model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
            external_case_id="primo-tabular-002",
            external_engine_version="3.1-harness",
            total_intake_mg_per_kg_bw_per_day=0.0005,
            rows=[
                {
                    "commodity": "apple",
                    "hr_mgkg": "0.2",
                    "consumption_kg_day": "0.18",
                    "pf": "1.0",
                }
            ],
        )
    assert exc.value.payload.code == "adapter_tabular_missing_field"
