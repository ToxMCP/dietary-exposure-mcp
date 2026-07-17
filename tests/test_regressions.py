import json
import shutil
from pathlib import Path

import pytest

from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.models import (
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    BuildBoundedIntakeSummaryRequest,
    DietaryCommodityResidueInput,
    IntakeWindowSemantic,
    ResidueSourceType,
    ScenarioClass,
    SelectConsumptionProfileRequest,
)
from dietary_mcp.runtime import DietaryRuntime


def test_dominant_contributors_and_assumption_ledger_are_explicit() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    runtime = DietaryRuntime(repo_root)
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest(
            chemical_identity={"preferredName": "Regression substance"},
            residue_records=[
                DietaryCommodityResidueInput(
                    commodity_code="apples",
                    residue_concentration_mg_per_kg=0.4,
                    source_type=ResidueSourceType.MONITORING,
                ),
                DietaryCommodityResidueInput(
                    commodity_code="spinach",
                    residue_concentration_mg_per_kg=0.1,
                    source_type=ResidueSourceType.MONITORING,
                ),
            ],
        )
    )
    profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            population_group="adult_general",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["apples", "spinach"],
        )
    ).profile
    summary = runtime.summarize_intake(
        BuildBoundedIntakeSummaryRequest(
            scenario=runtime.build_dietary_intake_scenario(
                BuildDietaryIntakeScenarioRequest(
                    chemical_identity=residue_profile.chemical_identity,
                    residue_profile=residue_profile,
                    consumption_profile=profile,
                    scenario_class=ScenarioClass.POINT_ESTIMATE,
                    intake_window_semantic=IntakeWindowSemantic.CHRONIC,
                )
            )
        )
    )
    assert summary.dominant_commodity_contributors
    parameters = {item.parameter for item in summary.assumptions_applied}
    assert "residue:apples" in parameters
    assert "processing_factor:apples" in parameters
    assert f"consumption:{profile.profile_id}:apples" in parameters


def test_defaults_manifest_hash_changes_when_defaults_file_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")

    baseline_manifest = DefaultsRegistry(tmp_path).build_manifest()
    core_defaults_path = tmp_path / "defaults" / "v1" / "core_defaults.json"
    payload = json.loads(core_defaults_path.read_text())
    payload["parameters"]["default_processing_factor"]["value"] = 1.1
    core_defaults_path.write_text(json.dumps(payload, indent=2) + "\n")

    monkeypatch.setenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", "1")
    changed_manifest = DefaultsRegistry(tmp_path).build_manifest()
    baseline_hash = next(
        item["sha256"] for item in baseline_manifest["files"] if item["path"].endswith("core_defaults.json")
    )
    changed_hash = next(
        item["sha256"] for item in changed_manifest["files"] if item["path"].endswith("core_defaults.json")
    )
    assert baseline_hash != changed_hash


def test_extension_packs_add_profiles_and_taxonomy_without_breaking_base_behavior(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "defaults", tmp_path / "defaults")

    taxonomy_extension_dir = tmp_path / "defaults" / "extensions" / "v1" / "commodity_taxonomy"
    taxonomy_extension_dir.mkdir(parents=True, exist_ok=True)
    (taxonomy_extension_dir / "berries.json").write_text(
        json.dumps(
            {
                "kind": "commodity_taxonomy",
                "commodities": [
                    {
                        "commodityCode": "berries",
                        "canonicalName": "Berries",
                        "foodGroup": "fruit",
                        "aliases": ["mixed_berries"],
                        "defaultProcessingFactor": 1.0,
                        "mappingStatus": "curated",
                        "sourceId": "dietary.extension.taxonomy.berries",
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    )

    profiles_extension_dir = tmp_path / "defaults" / "extensions" / "v1" / "consumption_profiles"
    profiles_extension_dir.mkdir(parents=True)
    (profiles_extension_dir / "senior_profile.json").write_text(
        json.dumps(
            {
                "kind": "consumption_profiles",
                "profiles": [
                    {
                        "profileId": "eu_senior_screening_v1",
                        "displayName": "EU senior screening profile",
                        "regionId": "eu_screening_default",
                        "populationGroup": "senior_general",
                        "surveySource": "Synthetic extension pack",
                        "bodyWeightKg": 68.0,
                        "applicableWindows": ["chronic"],
                        "limitations": ["Synthetic extension for compatibility testing"],
                        "sourceId": "dietary.extension.profile.senior",
                        "sourceTitle": "Synthetic senior profile",
                        "effectiveDate": "2026-04-08",
                        "commodityConsumption": [
                            {
                                "commodityCode": "berries",
                                "acuteKgPerDay": 0.0,
                                "chronicKgPerDay": 0.09
                            }
                        ]
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    )

    reporting_extension_dir = tmp_path / "defaults" / "extensions" / "v1" / "reporting_profiles"
    reporting_extension_dir.mkdir(parents=True, exist_ok=True)
    (reporting_extension_dir / "regional_reporting.json").write_text(
        json.dumps(
            {
                "kind": "reporting_profiles",
                "profiles": [
                    {
                        "profileId": "regional.synthetic.reporting_profile",
                        "displayName": "Regional synthetic reporting profile",
                        "authority": "Synthetic authority",
                        "jurisdiction": "regional_test",
                        "contaminantFamily": "pfas_food_contaminants",
                        "metricKind": "individual_analyte_panel",
                        "profileRole": "supporting_detail",
                        "submissionUse": "review_required",
                        "documentStatus": "final_current",
                        "reportedUnit": "ng/kg",
                        "matrixGroups": ["berries"],
                        "panelAnalytes": ["pfos", "pfoa"],
                        "aggregationBasis": "Synthetic additive reporting profile for extension regression coverage.",
                        "sourceIds": ["efsa.pfas.food.2020"],
                        "legalAuthorityIds": [],
                        "referenceValueRecordIds": [],
                        "notSubstitutableForProfileIds": ["eu.pfas.efsa4.food_risk"],
                        "notes": ["Synthetic reporting-profile extension for compatibility testing."]
                    }
                ]
            },
            indent=2,
        )
        + "\n"
    )

    monkeypatch.setenv("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION", "1")
    registry = DefaultsRegistry(tmp_path)
    berries = registry.resolve_commodity("mixed_berries")
    assert berries.commodity.commodity_code == "berries"

    profile = registry.select_consumption_profile_record(
        region_id="eu_screening_default",
        population_group="senior_general",
        intake_window=IntakeWindowSemantic.CHRONIC,
    )
    assert profile["profileId"] == "eu_senior_screening_v1"
    assert registry.get_reporting_profile_record("regional.synthetic.reporting_profile")["jurisdiction"] == "regional_test"

    base_profile = registry.select_consumption_profile_record(
        region_id="eu_screening_default",
        population_group="adult_general",
        intake_window=IntakeWindowSemantic.CHRONIC,
    )
    assert base_profile["profileId"] == "eu_adult_general_v1"


def test_public_seed_profile_pack_is_loaded_from_defaults_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    registry = DefaultsRegistry(repo_root)

    manifest_profiles = registry.consumption_profiles_manifest()["profiles"]
    public_seed_profile = next(
        profile for profile in manifest_profiles if profile["profileId"] == "who_gems_g01_chronic_general_v1"
    )
    assert public_seed_profile["profileFamily"] == "who_gems_cluster_diets_2012"
    assert public_seed_profile["reviewStatus"] == "public_official_seed"

    selected = registry.select_consumption_profile_record(
        region_id="who_gems_cluster_g01",
        population_group="adult_general",
        intake_window=IntakeWindowSemantic.CHRONIC,
        preferred_profile_id="who_gems_g01_chronic_general_v1",
    )
    assert selected["sourceId"] == "who.gems.food.cluster_diets.2012"
    assert selected["bodyWeightKg"] == 60.0


def test_runtime_surfaces_public_seed_profile_metadata_and_quality_flags() -> None:
    runtime = DietaryRuntime(Path(__file__).resolve().parents[1])
    selection = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(
            region_id="who_gems_cluster_g01",
            population_group="adult_general",
            intake_window=IntakeWindowSemantic.CHRONIC,
            required_commodity_codes=["apples", "milk"],
            preferred_profile_id="who_gems_g01_chronic_general_v1",
        )
    )

    assert selection.profile.profile_family == "who_gems_cluster_diets_2012"
    assert selection.profile.regulatory_basis == "WHO GEMS/Food Cluster Diets 2012 chronic model diet"
    assert selection.profile.review_status == "public_official_seed"
    assert any(flag.code == "broad_category_proxy_apples" for flag in selection.profile.quality_flags)
    assert any("60 kg adult body weight" in limitation.message for limitation in selection.profile.limitations)
