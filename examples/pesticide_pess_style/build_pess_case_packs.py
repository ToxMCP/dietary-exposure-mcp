"""Generate PESS-style dietary case packs for the PESS head-to-head.

Builds endosulfan and mancozeb public-source slices that mirror the accepted
``glyphosate_public_slice`` pack, then runs them through the real
``DietaryRuntime`` public contracts (no fabricated outputs).

Scientific-integrity posture (identical to the glyphosate slice):
  * Residue values are *illustrative regulatory-screening inputs* chosen within
    each active's observed EU MRL band, NOT row-level EFSA monitoring records.
  * Toxicological reference values (ADI / ARfD) are the REAL governed EFSA
    OpenFoodTox values already shipped in this repo (defaults/v1).
  * No EFSA PRIMo / DEEM / PESS engine execution is claimed.

Run:
    uv run --directory <repo> python examples/pesticide_pess_style/build_pess_case_packs.py
"""

from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.integrations import (
    export_pbpk_oral_input,
)
from dietary_mcp.models import (
    BuildBoundedIntakeSummaryRequest,
    BuildDietaryIntakeScenarioRequest,
    BuildDietaryResidueProfileRequest,
    BuildProbabilisticIntakeSummaryRequest,
    BuildUncertaintyIntakeAssessmentRequest,
    EvaluateGlobalTradeRiskRequest,
    ExportPbpkOralInputRequest,
    IntakeWindowSemantic,
    ParseRawSurveyDatasetRequest,
    ScenarioClass,
    SelectConsumptionProfileRequest,
    SummarizeSurveyDistributionRequest,
)
from dietary_mcp.runtime import DietaryRuntime

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = REPO_ROOT / "examples" / "pesticide_pess_style"
TARGET_JURISDICTIONS = ["eu", "us", "codex_global", "cn"]

# Chemical-agnostic synthetic survey fixture (mirrors the glyphosate slice).
SURVEY_RECORDS = [
    {"subjectId": "adult_001", "bodyWeightKg": 70.0, "commodityCode": "apple_juice", "consumptionKgPerDay": 0.2, "surveyWeight": 1.0},
    {"subjectId": "adult_001", "bodyWeightKg": 70.0, "commodityCode": "rice", "consumptionKgPerDay": 0.1, "surveyWeight": 1.0},
    {"subjectId": "adult_002", "bodyWeightKg": 62.0, "commodityCode": "apple_juice", "consumptionKgPerDay": 0.0, "surveyWeight": 1.2},
    {"subjectId": "adult_002", "bodyWeightKg": 62.0, "commodityCode": "rice", "consumptionKgPerDay": 0.25, "surveyWeight": 1.2},
    {"subjectId": "adult_003", "bodyWeightKg": 80.0, "commodityCode": "apple_juice", "consumptionKgPerDay": 0.15, "surveyWeight": 0.8},
    {"subjectId": "adult_003", "bodyWeightKg": 80.0, "commodityCode": "rice", "consumptionKgPerDay": 0.05, "surveyWeight": 0.8},
    {"subjectId": "adult_004", "bodyWeightKg": 68.0, "commodityCode": "apple_juice", "consumptionKgPerDay": 0.0, "surveyWeight": 1.0},
    {"subjectId": "adult_004", "bodyWeightKg": 68.0, "commodityCode": "rice", "consumptionKgPerDay": 0.0, "surveyWeight": 1.0},
]

CONFIGS = [
    {
        "slug": "endosulfan_public_slice",
        "casePackId": "endosulfan_public_slice_v1",
        "preferredName": "Endosulfan",
        "casrn": "115-29-7",
        "regulatoryContext": (
            "Endosulfan is an organochlorine insecticide whose EU approval lapsed; "
            "EU MRLs sit at or near the analytical LOQ band (~0.01-0.05 mg/kg)."
        ),
        # Illustrative screening residues within the observed EU LOQ band.
        "apple_residue": 0.01, "apple_bounds": [0.0, 0.05],
        "rice_residue": 0.01, "rice_bounds": [0.0, 0.03],
        # REAL governed EFSA OpenFoodTox reference values (defaults/v1).
        "adi": {"value": 0.006, "unit": "mg/kg bw/day", "sourceId": "efsa.openfoodtox.endosulfan.adi", "recordId": "efsa.openfoodtox.endosulfan.adi.65", "originalUnit": "6.0 ug/kg bw/day"},
        "arfd": {"value": 0.015, "unit": "mg/kg bw/day", "sourceId": "efsa.openfoodtox.endosulfan.arfd", "recordId": "efsa.openfoodtox.endosulfan.arfd.775"},
        "uncertainty_apple": {"geometricMeanMgPerKg": 0.01, "loqMgPerKg": 0.01},
        "uncertainty_rice_max": 0.03,
        "lockedFacts": [
            "PESS demonstrates endosulfan, mancozeb, and glyphosate dietary exposure.",
            "EFSA OpenFoodTox records an endosulfan ADI of 6.0 ug/kg bw/day (EFSA CONTAM, 2005) and an ARfD of 0.015 mg/kg bw/day (EFSA PPR, 2012).",
            "EU MRLs for endosulfan are set at or near the analytical limit of quantification.",
        ],
    },
    {
        "slug": "mancozeb_public_slice",
        "casePackId": "mancozeb_public_slice_v1",
        "preferredName": "Mancozeb",
        "casrn": "8018-01-7",
        "regulatoryContext": (
            "Mancozeb is a dithiocarbamate fungicide whose EU approval was not renewed; "
            "screening residues here sit within the observed EU MRL band."
        ),
        "apple_residue": 0.05, "apple_bounds": [0.0, 0.10],
        "rice_residue": 0.02, "rice_bounds": [0.0, 0.05],
        "adi": {"value": 0.023, "unit": "mg/kg bw/day", "sourceId": "efsa.openfoodtox.mancozeb.adi", "recordId": "efsa.openfoodtox.mancozeb.adi.3605", "originalUnit": "0.023 mg/kg bw/day"},
        "arfd": {"value": 0.15, "unit": "mg/kg bw/day", "sourceId": "efsa.openfoodtox.mancozeb.arfd", "recordId": "efsa.openfoodtox.mancozeb.arfd.3605"},
        "uncertainty_apple": {"geometricMeanMgPerKg": 0.05, "loqMgPerKg": 0.01},
        "uncertainty_rice_max": 0.05,
        "lockedFacts": [
            "PESS demonstrates endosulfan, mancozeb, and glyphosate dietary exposure.",
            "EFSA OpenFoodTox records a mancozeb ADI of 0.023 mg/kg bw/day and an ARfD of 0.15 mg/kg bw (EFSA, 2019).",
            "Mancozeb EU approval was not renewed; residue assumptions are screening-level.",
        ],
    },
]


def _residue_record(commodity: str, value: float, bounds: list[float], slug: str, chem: str) -> dict:
    return {
        "commodity_code": commodity,
        "residue_concentration_mg_per_kg": value,
        "lower_bound_mg_per_kg": bounds[0],
        "upper_bound_mg_per_kg": bounds[1],
        "residue_unit": "mg/kg",
        "source_type": "user_supplied",
        "review_status": "schema_reviewed_not_source_validated",
        "source_reference": {
            "source_id": f"casepack.{chem}.{commodity}.screening_residue",
            "title": f"{chem.title()} {commodity} regulatory-screening residue input (EU MRL band) for PESS-style public slice",
            "effective_date": "2026-06-01",
            "url": f"examples://pesticide_pess_style/{slug}/source_lock",
            "originTag": "illustrative_placeholder",
        },
    }


def build_input_payloads(cfg: dict) -> dict:
    chem = cfg["preferredName"].lower()
    residue_request = {
        "chemical_identity": {"preferredName": cfg["preferredName"], "casrn": cfg["casrn"]},
        "region_id": "eu_screening_default",
        "residue_records": [
            _residue_record("apple_juice", cfg["apple_residue"], cfg["apple_bounds"], cfg["slug"], chem),
            _residue_record("rice", cfg["rice_residue"], cfg["rice_bounds"], cfg["slug"], chem),
        ],
    }
    survey_request = {
        "datasetId": f"{cfg['slug']}_adult_survey",
        "regionId": "eu_screening_default",
        "populationGroup": "adult_general",
        "rawRecords": [
            {**rec, "daysInSurvey": 1, "samplingStratum": "public_slice", "surveyDayId": "d1"}
            for rec in SURVEY_RECORDS
        ],
    }
    probabilistic_overlay = {"iterationCount": 1000, "randomSeed": 20260601}
    uncertainty_overlay = {
        "assessmentMode": "two_dimensional_monte_carlo",
        "randomSeed": 20260601,
        "outerIterationCount": 40,
        "innerIterationCount": 80,
        "censoredDataPolicy": "three_bound_sensitivity",
        "residueUncertaintyModels": [
            {
                "commodityCode": "apples",
                "distribution": "censored_lognormal",
                "geometricMeanMgPerKg": cfg["uncertainty_apple"]["geometricMeanMgPerKg"],
                "geometricSd": 1.8,
                "lodMgPerKg": 0.005,
                "loqMgPerKg": cfg["uncertainty_apple"]["loqMgPerKg"],
                "processingFactorCv": 0.15,
            },
            {
                "commodityCode": "rice",
                "distribution": "uniform",
                "minMgPerKg": 0.0,
                "maxMgPerKg": cfg["uncertainty_rice_max"],
                "processingFactorCv": 0.05,
            },
        ],
        "healthReference": {
            "referenceType": "ADI",
            "value": cfg["adi"]["value"],
            "unit": cfg["adi"]["unit"],
            "sourceId": cfg["adi"]["sourceId"],
        },
    }
    return {
        "residue_profile_request": residue_request,
        "adult_raw_survey_request": survey_request,
        "probabilistic_request_overlay": probabilistic_overlay,
        "uncertainty_request_overlay": uncertainty_overlay,
    }


def build_source_lock(cfg: dict) -> dict:
    def anchor(sid, title, url, observed, facts=None):
        return {
            "sourceId": sid, "title": title, "url": url,
            "retrievedAt": "2026-06-01T00:00:00Z", "casePackReviewedAt": "2026-06-01T00:00:00Z",
            "publisherLastReviewed": None, "retrievalMethod": "manual_web_review",
            "observedUse": observed, "lockedFacts": facts or [],
        }
    return {
        "casePackId": cfg["casePackId"],
        "lockedOn": "2026-06-01",
        "purpose": f"PESS-style Dietary Exposure MCP demonstration for {cfg['preferredName']} using public source anchors, governed EFSA OpenFoodTox reference values, and illustrative screening residue inputs.",
        "sourceAnchors": [
            anchor("pess.2026.ecoenvsafety.120201",
                   "Modeling external exposure to pesticides in human populations: Developing an exposure scenario generator",
                   "https://doi.org/10.1016/j.ecoenv.2026.120201",
                   "PESS head-to-head comparison anchor for the dietary module.",
                   cfg["lockedFacts"]),
            anchor("efsa.openfoodtox.3", "EFSA Chemical Hazards Database - OpenFoodTox",
                   "https://www.efsa.europa.eu/en/data-report/chemical-hazards-database-openfoodtox",
                   "Governed toxicological reference values (ADI/ARfD) used for health-reference context.",
                   [f"OpenFoodTox record {cfg['adi']['recordId']} provides the ADI used here.",
                    f"OpenFoodTox record {cfg['arfd']['recordId']} provides the ARfD."]),
            anchor("ec.eu_mrl_legislation", "EU legislation on pesticide maximum residue levels",
                   "https://food.ec.europa.eu/plants/pesticides/maximum-residue-levels/eu-legislation-mrls_en",
                   "MRL-band context anchor for the illustrative screening residue inputs.",
                   [cfg["regulatoryContext"]]),
            anchor("ec.eu_pesticides_database", "EU Pesticides Database",
                   "https://food.ec.europa.eu/plants/pesticides/eu-pesticides-database_en",
                   "Public source anchor for EU active-substance and MRL lookup context."),
        ],
        "screeningInputPosture": {
            "residueValues": "Illustrative regulatory-screening inputs within the observed EU MRL band; not row-level EFSA monitoring records.",
            "referenceValues": f"REAL governed EFSA OpenFoodTox values (ADI {cfg['adi']['value']} {cfg['adi']['unit']}; ARfD {cfg['arfd']['value']} {cfg['arfd']['unit']}).",
            "matrixSemantics": {
                "submittedCommodityCode": "apple_juice",
                "canonicalCommodityCode": "apples",
                "residueMatrix": "raw_primary_commodity",
                "consumptionMatrix": "processed_derivative",
                "processingFactorDirection": "raw_residue_to_processed_food",
                "consumptionValueBasis": "governed_apples_profile_used_as_processed_derivative_proxy",
                "consumptionProxy": True,
            },
            "reviewStatus": "schema_reviewed_not_source_validated",
            "chemicalIdentityNote": "DTXSID not locked in this public slice; preferredName + CASRN provided.",
        },
        "nonClaims": [
            "No EFSA PRIMo, DEEM, or PESS engine execution is claimed.",
            "No official equivalence to EFSA monitoring datasets or dashboards is claimed.",
            "No legal clearance, final regulatory decision, trade clearance, or PBPK internal-dose simulation is claimed.",
        ],
    }


def run_pipeline(cfg: dict, payloads: dict, runtime: DietaryRuntime) -> dict:
    residue_profile = runtime.build_residue_profile(
        BuildDietaryResidueProfileRequest.model_validate(payloads["residue_profile_request"])
    )
    adult_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(population_group="adult_general", intake_window=IntakeWindowSemantic.CHRONIC,
                                        required_commodity_codes=["apple_juice", "rice"])
    ).profile
    child_profile = runtime.select_consumption_profile(
        SelectConsumptionProfileRequest(population_group="child_1_6", intake_window=IntakeWindowSemantic.ACUTE,
                                        required_commodity_codes=["apple_juice", "rice"])
    ).profile

    adult_scenario = runtime.build_dietary_intake_scenario(BuildDietaryIntakeScenarioRequest(
        chemical_identity=residue_profile.chemical_identity, residue_profile=residue_profile,
        consumption_profile=adult_profile, scenario_class=ScenarioClass.POINT_ESTIMATE,
        intake_window_semantic=IntakeWindowSemantic.CHRONIC))
    adult = runtime.summarize_intake(BuildBoundedIntakeSummaryRequest(scenario=adult_scenario))

    child_scenario = runtime.build_dietary_intake_scenario(BuildDietaryIntakeScenarioRequest(
        chemical_identity=residue_profile.chemical_identity, residue_profile=residue_profile,
        consumption_profile=child_profile, scenario_class=ScenarioClass.BOUNDED_ACUTE))
    child = runtime.summarize_intake(BuildBoundedIntakeSummaryRequest(scenario=child_scenario))

    dataset = runtime.parse_raw_survey_dataset(
        ParseRawSurveyDatasetRequest.model_validate(payloads["adult_raw_survey_request"]))
    survey = runtime.summarize_survey_distribution(
        SummarizeSurveyDistributionRequest(dataset=dataset, residue_profile=residue_profile))

    prob = runtime.build_probabilistic_intake_summary(BuildProbabilisticIntakeSummaryRequest(
        dataset=dataset, residue_profile=residue_profile, **payloads["probabilistic_request_overlay"]))

    unc_payload = {**payloads["uncertainty_request_overlay"],
                   "dataset": dataset.model_dump(mode="json", by_alias=True),
                   "residue_profile": residue_profile.model_dump(mode="json", by_alias=True)}
    unc = runtime.build_uncertainty_intake_assessment(
        BuildUncertaintyIntakeAssessmentRequest.model_validate(unc_payload))

    trade = runtime.evaluate_global_trade_risk(EvaluateGlobalTradeRiskRequest(
        chemical_identity=residue_profile.chemical_identity,
        residue_records=BuildDietaryResidueProfileRequest.model_validate(
            payloads["residue_profile_request"]).residue_records,
        target_jurisdictions=TARGET_JURISDICTIONS))

    pbpk = export_pbpk_oral_input(
        ExportPbpkOralInputRequest(scenario=child_scenario, summary=child), runtime.provenance)

    adult_contrib = {
        item.commodity.commodity_code: {
            "consumptionKgPerDay": item.consumption_kg_per_day,
            "appliedProcessingFactor": item.applied_processing_factor,
            "contributionMgPerKgBwPerDay": item.contribution_mg_per_kg_bw_per_day,
        } for item in adult.commodity_contributions
    }
    adi = cfg["adi"]["value"]
    arfd = cfg["arfd"]["value"]
    adult_total = adult.total_intake_mg_per_kg_bw_per_day
    child_total = child.total_intake_mg_per_kg_bw_per_day
    return {
        "casePackId": cfg["casePackId"],
        "generatedBy": "DietaryRuntime current public contracts via build_pess_case_packs.py",
        "chemicalIdentity": {"preferredName": cfg["preferredName"], "casrn": cfg["casrn"]},
        "healthReference": {"adi": cfg["adi"], "arfd": cfg["arfd"]},
        "processingFactorCheck": {
            "submittedCommodityCode": "apple_juice", "canonicalCommodityCode": "apples",
            "appliedProcessingFactor": adult_contrib.get("apples", {}).get("appliedProcessingFactor"),
            "contrastToPess": "PESS reported processing factor = 1 for all dietary calculations; this slice demonstrates governed processed-commodity handling.",
        },
        "deterministic": {
            "adultChronic": {
                "populationGroup": "adult_general", "scenarioClass": "point_estimate",
                "intakeWindowSemantic": "chronic",
                "totalIntakeMgPerKgBwPerDay": adult_total,
                "percentOfAdi": (adult_total / adi * 100.0) if adi else None,
                "commodityContributions": adult_contrib,
            },
            "childAcute": {
                "populationGroup": "child_1_6", "scenarioClass": "bounded_acute",
                "intakeWindowSemantic": "acute",
                "totalIntakeMgPerKgBwPerDay": child_total,
                "lowerBoundTotalIntakeMgPerKgBwPerDay": child.lower_bound_total_intake_mg_per_kg_bw_per_day,
                "upperBoundTotalIntakeMgPerKgBwPerDay": child.upper_bound_total_intake_mg_per_kg_bw_per_day,
                "percentOfArfd": (child_total / arfd * 100.0) if arfd else None,
            },
        },
        "surveyDistribution": {
            "totalSubjects": survey.total_subjects,
            "consumersOnlyCount": survey.consumers_only_count,
            "zeroIntakePrevalence": survey.zero_intake_prevalence,
            "meanIntakeMgPerKgBwPerDay": survey.mean_intake_mg_per_kg_bw_per_day,
            "percentile95MgPerKgBwPerDay": survey.percentile_95_mg_per_kg_bw_per_day,
        },
        "probabilistic": {
            "iterationCount": payloads["probabilistic_request_overlay"]["iterationCount"],
            "randomSeed": payloads["probabilistic_request_overlay"]["randomSeed"],
            "meanIntakeMgPerKgBwPerDay": prob.mean_intake_mg_per_kg_bw_per_day,
            "percentile95MgPerKgBwPerDay": prob.percentile_95_mg_per_kg_bw_per_day,
            "zeroIntakePrevalence": prob.zero_intake_prevalence,
        },
        "uncertainty": {
            "assessmentMode": unc.assessment_mode,
            "censoredDataPolicy": unc.censored_data_policy,
            "censoredPolicySummaryKeys": sorted(unc.censored_policy_summaries),
            "meanMedianMgPerKgBwPerDay": unc.distribution_summary.mean.median,
            "percentile95MedianMgPerKgBwPerDay": unc.distribution_summary.percentile_95.median,
            "adiExceedanceProbabilityMedian": unc.health_reference_exceedance.exceedance_probability.median,
        },
        "tradeRisk": {
            "targetJurisdictions": TARGET_JURISDICTIONS,
            "jurisdictionStatuses": {item.jurisdiction: item.trade_status for item in trade.jurisdiction_profiles},
            "jurisdictionMrlCoverageStatuses": {item.jurisdiction: item.mrl_coverage_status.value for item in trade.jurisdiction_profiles},
        },
        "pbpkHandoff": {
            "route": pbpk.route_dose_estimate.route,
            "intakeWindowSemantic": pbpk.route_dose_estimate.intake_window_semantic,
            "valueMgPerKgBwPerDay": pbpk.route_dose_estimate.value_mg_per_kg_bw_per_day,
            "schedule": pbpk.dosing_regimen.schedule,
        },
        "reviewPosture": {
            "residueInputPosture": "illustrative_screening_fixture_eu_mrl_band",
            "residueReviewStatus": "schema_reviewed_not_source_validated",
            "referenceValuePosture": "governed_efsa_openfoodtox",
        },
        "nonClaims": [
            "Not a row-level EFSA residue dataset reproduction.",
            "Not an EFSA PRIMo, DEEM, or PESS engine run.",
            "Not a final regulatory conclusion, legal clearance, or trade clearance.",
            "Not a PBPK internal-dose simulation.",
            "Not a biomonitoring validation.",
        ],
    }, pbpk


def write_docs(cfg: dict, case_dir: Path) -> None:
    (case_dir / "README.md").write_text(
        f"# {cfg['preferredName']} public slice (PESS-style)\n\n"
        f"PESS head-to-head dietary case pack for **{cfg['preferredName']}** (CAS {cfg['casrn']}), "
        f"mirroring `glyphosate_public_slice`.\n\n"
        f"- Toxicological reference values (ADI {cfg['adi']['value']} {cfg['adi']['unit']}, "
        f"ARfD {cfg['arfd']['value']} {cfg['arfd']['unit']}) are the **real governed EFSA OpenFoodTox** "
        f"values shipped in `defaults/v1`.\n"
        f"- Residue inputs are **illustrative regulatory-screening values** within the observed EU MRL band "
        f"(`schema_reviewed_not_source_validated`), not row-level EFSA monitoring data.\n\n"
        f"Regenerate with `build_pess_case_packs.py`. See `limitations.md` and `source_lock.json`.\n"
    )
    (case_dir / "limitations.md").write_text(
        f"# Limitations\n\n"
        f"This case pack is a public-source slice for demonstrating Dietary Exposure MCP governance for "
        f"{cfg['preferredName']}. It is not a full PESS reproduction.\n\n"
        f"## Explicit Non-Claims\n\n"
        f"- Residue values are illustrative regulatory-screening inputs within the EU MRL band, not row-level EFSA monitoring records.\n"
        f"- {cfg['regulatoryContext']}\n"
        f"- The apple-juice lane uses a raw-apple residue translated to apple-juice consumption with a processing factor.\n"
        f"- Consumption values come from governed Dietary MCP profiles; the raw survey is a compact synthetic fixture.\n"
        f"- Percentiles are regression-demo outputs from a tiny fixture, not population percentiles.\n"
        f"- ADI/ARfD are governed EFSA OpenFoodTox values; the health-reference exceedance is a chronic-context demonstration.\n"
        f"- DTXSID is not locked in this slice (preferredName + CASRN only).\n"
        f"- The PBPK handoff is an external oral dose packet only; biomonitoring comparison routes to a future Biomonitoring/Reverse-Exposure MCP.\n"
    )


def main() -> None:
    runtime = DietaryRuntime(REPO_ROOT)
    for cfg in CONFIGS:
        case_dir = BASE / cfg["slug"]
        (case_dir / "inputs").mkdir(parents=True, exist_ok=True)
        (case_dir / "outputs").mkdir(parents=True, exist_ok=True)
        payloads = build_input_payloads(cfg)
        for name, payload in payloads.items():
            (case_dir / "inputs" / f"{name}.json").write_text(json.dumps(payload, indent=2) + "\n")
        (case_dir / "source_lock.json").write_text(json.dumps(build_source_lock(cfg), indent=2) + "\n")
        write_docs(cfg, case_dir)

        summary, pbpk = run_pipeline(cfg, payloads, runtime)
        (case_dir / "outputs" / "output_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
        (case_dir / "outputs" / "pbpk_oral_handoff.json").write_text(
            pbpk.model_dump_json(indent=2, by_alias=True) + "\n")

        det = summary["deterministic"]
        print(f"\n=== {cfg['preferredName']} ({cfg['casePackId']}) ===")
        print(f"  adult chronic intake : {det['adultChronic']['totalIntakeMgPerKgBwPerDay']:.3e} mg/kg bw/day "
              f"({det['adultChronic']['percentOfAdi']:.4f}% ADI)")
        print(f"  child acute intake   : {det['childAcute']['totalIntakeMgPerKgBwPerDay']:.3e} mg/kg bw/day "
              f"(upper {det['childAcute']['upperBoundTotalIntakeMgPerKgBwPerDay']:.3e}; "
              f"{det['childAcute']['percentOfArfd']:.4f}% ARfD)")
        print(f"  uncertainty P95 med  : {summary['uncertainty']['percentile95MedianMgPerKgBwPerDay']:.3e}; "
              f"ADI exceedance prob median = {summary['uncertainty']['adiExceedanceProbabilityMedian']}")
        print(f"  trade-risk statuses  : {summary['tradeRisk']['jurisdictionStatuses']}")
        print(f"  written -> {case_dir.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
