from __future__ import annotations

import json
from pathlib import Path


WHO_GEMS_DATASET_URL = (
    "https://cdn.who.int/media/docs/default-source/food-safety/gems-food/"
    "gems-food-cluster-diets-2012-consumption.xls?sfvrsn=fc263737_6"
)
WHO_GEMS_OVERVIEW_URL = (
    "https://www.who.int/teams/nutrition-and-food-safety/databases/"
    "global-environment-monitoring-system-food-contamination"
)
EFSA_PRIMO_URL = "https://www.efsa.europa.eu/en/applications/pesticides/tools"
EFSA_PRIMO_REPORT_URL = "https://www.efsa.europa.eu/en/supporting/pub/en-8990"
EFSA_DEFAULTS_URL = "https://www.efsa.europa.eu/en/press/news/120307a"
EPA_DEEM_URL = (
    "https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/"
    "deem-fcidcalendex-software-installer"
)
EPA_DEEM_ERRATA_URL = (
    "https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/"
    "dietary-exposure-evaluation-model-deem-errata-list"
)

WHO_MAPPING = {
    "apples": {
        "lev2_name": "Pome fruits, fresh",
        "notes": [
            "Mapped from the WHO GEMS/Food pome-fruit category as a representative apples proxy.",
            "Category is broader than apples alone and should be treated as a chronic seed profile rather than a commodity-specific survey result.",
        ],
    },
    "spinach": {
        "lev2_name": "Leafy vegetables (including Brassica leafy vegetables and seaweed)",
        "notes": [
            "Mapped from the WHO GEMS/Food leafy-vegetable category as a representative spinach proxy.",
            "Category is broader than spinach alone and requires refinement before commodity-specific regulatory use.",
        ],
    },
    "rice": {
        "lev2_name": "Cereal grains & flours",
        "notes": [
            "Mapped from the WHO GEMS/Food cereal-grains-and-flours category as a broad rice proxy.",
            "Category is substantially broader than rice and should be treated as a heuristic chronic seed only.",
        ],
    },
    "milk": {
        "lev2_name": "Milks (no other ingredients)",
        "notes": [
            "Mapped directly from the WHO GEMS/Food milks-without-other-ingredients category.",
        ],
    },
}


def _load_xls_sheet(workbook_path: Path):
    try:
        import xlrd
    except ImportError as exc:
        raise RuntimeError(
            "xlrd is required to generate WHO GEMS/Food seed profiles. "
            "Run with `uv run --with xlrd dietary-mcp-generate-public-seeds --workbook <path>`."
        ) from exc
    book = xlrd.open_workbook(workbook_path)
    return book.sheet_by_name("GEMSFood Diets 2012")


def _coerce_numeric_cell(value: object) -> float:
    if value in ("", None):
        return 0.0
    return float(value)


def generate_who_gems_profiles(workbook_path: Path) -> dict:
    sheet = _load_xls_sheet(workbook_path)
    headers = sheet.row_values(0)
    cluster_codes = headers[3:]
    category_rows: dict[str, list[float]] = {}
    for r in range(2, sheet.nrows):
        lev2_name = sheet.cell_value(r, 2)
        if not lev2_name:
            continue
        category_rows[lev2_name] = [_coerce_numeric_cell(value) for value in sheet.row_values(r)[3:]]

    profiles = []
    for idx, cluster_code in enumerate(cluster_codes):
        commodity_consumption = []
        limitations = [
            "WHO GEMS/Food cluster diets are chronic model diets expressed in grams/person/day, not person-level survey records.",
            "This public seed profile uses a standard 60 kg adult body weight to normalize intake on a mg/kg-bw/day basis.",
            "Country composition for each cluster is maintained by WHO and should be confirmed against the official dashboard when needed.",
        ]
        quality_flags = [
            {
                "code": "public_seed_profile",
                "severity": "info",
                "message": "This profile is a public official seed derived from WHO GEMS/Food cluster diets and is intended for transparent chronic screening workflows.",
            }
        ]
        for commodity_code, mapping in WHO_MAPPING.items():
            try:
                grams_per_day = category_rows[mapping["lev2_name"]][idx]
            except KeyError as exc:
                raise RuntimeError(
                    f"WHO workbook is missing the mapped category {mapping['lev2_name']!r}."
                ) from exc
            commodity_consumption.append(
                {
                    "commodityCode": commodity_code,
                    "acuteKgPerDay": None,
                    "chronicKgPerDay": grams_per_day / 1000.0,
                }
            )
            limitations.extend(mapping["notes"])
            if commodity_code != "milk":
                quality_flags.append(
                    {
                        "code": f"broad_category_proxy_{commodity_code}",
                        "severity": "warning",
                        "message": mapping["notes"][0],
                    }
                )

        profiles.append(
            {
                "profileId": f"who_gems_{cluster_code.lower()}_chronic_general_v1",
                "displayName": f"WHO GEMS/Food {cluster_code} chronic general-population seed profile",
                "regionId": f"who_gems_cluster_{cluster_code.lower()}",
                "populationGroup": "adult_general",
                "profileFamily": "who_gems_cluster_diets_2012",
                "regulatoryBasis": "WHO GEMS/Food Cluster Diets 2012 chronic model diet",
                "reviewStatus": "public_official_seed",
                "surveySource": "WHO GEMS/Food Cluster Diets 2012 public dataset",
                "bodyWeightKg": 60.0,
                "applicableWindows": ["chronic"],
                "limitations": limitations,
                "qualityFlags": quality_flags,
                "sourceId": "who.gems.food.cluster_diets.2012",
                "sourceTitle": "WHO GEMS/Food Cluster Diets 2012 public dataset",
                "sourceUrl": WHO_GEMS_DATASET_URL,
                "commodityConsumption": commodity_consumption,
            }
        )

    return {
        "defaultsVersion": "v1",
        "kind": "consumption_profiles",
        "metadata": {
            "sourceId": "who.gems.food.cluster_diets.2012",
            "sourceTitle": "WHO GEMS/Food Cluster Diets 2012 public dataset",
            "sourceUrl": WHO_GEMS_DATASET_URL,
            "overviewUrl": WHO_GEMS_OVERVIEW_URL,
            "bodyWeightBasis": {
                "valueKg": 60.0,
                "justification": (
                    "WHO/JECFA chronic dietary exposure assessments commonly use a standard 60 kg adult body weight; "
                    "EFSA also notes that 60 kg has commonly been used for worldwide adult populations."
                ),
                "sourceUrls": [WHO_GEMS_OVERVIEW_URL, EFSA_DEFAULTS_URL],
            },
        },
        "profiles": profiles,
    }


def generate_source_catalog() -> dict:
    return {
        "defaultsVersion": "v1",
        "kind": "source_catalog",
        "sources": [
            {
                "sourceId": "who.gems.food.cluster_diets.2012",
                "title": "WHO GEMS/Food Cluster Diets 2012 public dataset",
                "organization": "WHO",
                "kind": "official_public_dataset",
                "jurisdiction": "global",
                "documentStatus": "dataset_current",
                "regulatoryRole": "dataset",
                "effectiveDate": None,
                "url": WHO_GEMS_DATASET_URL,
                "submissionUse": "review_required",
                "normativeFor": ["reference_dietary"],
                "supersedes": [],
                "supersededBy": [],
                "notes": [
                    "Public chronic model-diet dataset with 17 supra-national clusters.",
                    "Used in Dietary MCP as a public seed source for chronic general-population profiles.",
                ],
            },
            {
                "sourceId": "efsa.primo",
                "title": "EFSA PRIMo pesticide residue intake model tools page",
                "organization": "EFSA",
                "kind": "official_model_metadata",
                "jurisdiction": "eu",
                "documentStatus": "tool_metadata",
                "regulatoryRole": "software_metadata",
                "effectiveDate": None,
                "url": EFSA_PRIMO_URL,
                "submissionUse": "not_allowed",
                "normativeFor": ["efsa_primo_adapter"],
                "supersedes": [],
                "supersededBy": [],
                "notes": [
                    "Used as model-family metadata for future PRIMo-aligned adapter boundaries.",
                    "EFSA notes that PRIMo revision 3.1 remains the current version for MRL applications until formal endorsement of revision 4 in 2026.",
                ],
            },
            {
                "sourceId": "efsa.primo.rev4.report.2024",
                "title": "EFSA PRIMo revision 4 technical report",
                "organization": "EFSA",
                "kind": "official_supporting_publication",
                "jurisdiction": "eu",
                "documentStatus": "final_current",
                "regulatoryRole": "technical_report",
                "effectiveDate": "2024-08-09",
                "url": EFSA_PRIMO_REPORT_URL,
                "submissionUse": "review_required",
                "normativeFor": ["efsa_primo_adapter"],
                "supersedes": [],
                "supersededBy": [],
                "notes": [
                    "Technical report describing PRIMo revision 4 public rollout and migration context.",
                    "Useful for governance and consultation-only review, but not itself the submission engine.",
                ],
            },
            {
                "sourceId": "efsa.default_body_weights.2012",
                "title": "EFSA harmonised default values for risk assessment",
                "organization": "EFSA",
                "kind": "official_guidance_metadata",
                "jurisdiction": "eu",
                "documentStatus": "final_current",
                "regulatoryRole": "guidance",
                "effectiveDate": "2012-03-07",
                "url": EFSA_DEFAULTS_URL,
                "submissionUse": "review_required",
                "normativeFor": ["reference_dietary", "efsa_primo_adapter"],
                "supersedes": [],
                "supersededBy": [],
                "notes": [
                    "Provides public default body-weight guidance.",
                    "Notes that 60 kg has commonly been used for worldwide adult populations, while 70 kg is more realistic for EU adults when actual EU data are absent.",
                ],
            },
            {
                "sourceId": "epa.deem.fcid.4_02",
                "title": "EPA DEEM-FCID/Calendex software installer page",
                "organization": "US EPA",
                "kind": "official_model_metadata",
                "jurisdiction": "us",
                "documentStatus": "tool_metadata",
                "regulatoryRole": "software_metadata",
                "effectiveDate": None,
                "url": EPA_DEEM_URL,
                "submissionUse": "not_allowed",
                "normativeFor": ["epa_deem_adapter"],
                "supersedes": [],
                "supersededBy": [],
                "notes": [
                    "Documents that DEEM-FCID Version 4.02 is based on 2005-2010 NHANES/WWEIA data.",
                    "Used in Dietary MCP as metadata for future DEEM-aligned adapter boundaries rather than as a native public contract.",
                ],
            },
            {
                "sourceId": "epa.deem.errata",
                "title": "EPA Dietary Exposure Evaluation Model (DEEM) errata list",
                "organization": "US EPA",
                "kind": "official_model_metadata",
                "jurisdiction": "us",
                "documentStatus": "tool_metadata",
                "regulatoryRole": "software_metadata",
                "effectiveDate": None,
                "url": EPA_DEEM_ERRATA_URL,
                "submissionUse": "review_required",
                "normativeFor": ["epa_deem_adapter"],
                "supersedes": [],
                "supersededBy": [],
                "notes": [
                    "EPA publishes DEEM errata separately from the installer page.",
                    "Dietary MCP uses this record to surface official errata awareness in adapter governance.",
                ],
            },
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate public regulatory seed files for Dietary MCP.")
    parser.add_argument("--workbook", required=True, help="Path to the WHO GEMS/Food cluster diets XLS workbook.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    target_profiles = repo_root / "defaults" / "v1" / "consumption_profiles_who_gems_public.json"
    target_sources = repo_root / "defaults" / "v1" / "source_catalog.json"

    target_profiles.write_text(
        json.dumps(generate_who_gems_profiles(Path(args.workbook)), indent=2) + "\n"
    )
    target_sources.write_text(json.dumps(generate_source_catalog(), indent=2) + "\n")


if __name__ == "__main__":
    main()
