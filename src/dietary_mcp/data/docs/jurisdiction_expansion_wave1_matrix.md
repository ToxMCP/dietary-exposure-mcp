# Jurisdiction Expansion Wave 1 Coverage Matrix

Verified against live official primary sources on `2026-04-21`.

This matrix is the source-of-truth for the shipped `US + Codex + China` wave-1 expansion.

The same coverage posture is also published in the governed runtime as `jurisdiction_coverage_wave1.json` and exposed through MCP jurisdiction-coverage resources.
Contaminant rows below reflect the later wave-2 legal-limit hardening that added exact official contaminant ML/action-level records for selected `US` and `China` lanes.

Coverage semantics:

- `yes`: an official wave-1 pack is shipped for this column.
- `partial`: coverage is present, but only for selected current-taxonomy commodities or via normalized session/year metadata rather than a full jurisdiction data layer.
- `anchor-only`: an official source and legal anchor are shipped, but no jurisdiction-specific reference-value layer or exact ML extraction is shipped yet.
- `no`: no official wave-1 record is shipped for that column.
- `n/a`: not applicable to the current wave-1 layer design.

Compatibility rules:

- No EU or Codex value is silently borrowed to fill `US` or `China` gaps.
- No national value is silently borrowed to fill `Codex` gaps.
- Trade-risk coverage is curated for the shipped commodity taxonomy, not a claim of full database parity.

## United States

| Jurisdiction | Family | Substance | Official sources | Legal authority | Reference value | Exact MRL/ML coverage | Currency metadata | Gap reason or coverage note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `us` | `pesticide_residue` | `glyphosate` | yes | yes | no | partial | yes | `40 CFR 180.364` is curated for `rice`; no U.S. jurisdiction-specific dietary reference value is shipped. |
| `us` | `pesticide_residue` | `acetamiprid` | yes | yes | no | no | yes | `40 CFR 180.578` was verified, but no exact current-taxonomy commodity pair was curated in wave 1 and no U.S. jurisdiction-specific dietary reference value is shipped. |
| `us` | `pesticide_residue` | `imidacloprid` | yes | yes | no | partial | yes | Exact U.S. tolerances are curated for `apples`, `grapes`, and `rice`; no U.S. jurisdiction-specific dietary reference value is shipped. |
| `us` | `pesticide_residue` | `glufosinate` | yes | yes | no | partial | yes | Exact U.S. tolerance is curated for `rice`; no U.S. jurisdiction-specific dietary reference value is shipped. |
| `us` | `pesticide_residue` | `oxamyl` | yes | yes | no | partial | yes | Exact U.S. tolerance is curated for `tomatoes`; no U.S. jurisdiction-specific dietary reference value is shipped. |
| `us` | `pfas_food_contaminants` | `PFAS` | no | no | no | n/a | no | No final official U.S. food PFAS reference-value or binding food-law anchor is curated in wave 1. |
| `us` | `acrylamide_process_contaminants` | `acrylamide` | no | no | no | n/a | no | No final official U.S. acrylamide food reference-value or binding anchor is curated in wave 1. |
| `us` | `bisphenol_food_contact_migration` | `bisphenol_a` | no | no | no | n/a | no | No final official U.S. BPA food reference-value or binding anchor is curated in wave 1. |
| `us` | `cadmium_food_contaminants` | `cadmium` | no | no | no | n/a | no | No final official U.S. cadmium food reference-value or binding anchor is curated in wave 1. |
| `us` | `lead_food_contaminants` | `lead` | yes | yes | no | partial | yes | Exact final FDA action levels are now curated for processed baby foods, single-ingredient root vegetables, and dry infant cereals; no jurisdiction-specific dietary reference value is shipped. |
| `us` | `inorganic_arsenic_food_contaminants` | `inorganic_arsenic` | yes | yes | no | partial | yes | Exact final FDA action levels are now curated for infant rice cereals and apple juice; no jurisdiction-specific dietary reference value is shipped. |
| `us` | `mercury_food_contaminants` | `methylmercury` | yes | yes | no | partial | yes | Exact final FDA compliance-policy guidance is now curated for fish and other aquatic animals at the edible-portion scope; no jurisdiction-specific dietary reference value is shipped. |
| `us` | `mercury_food_contaminants` | `inorganic_mercury` | no | no | no | n/a | no | No final official U.S. inorganic mercury food reference-value or binding anchor is curated in wave 1. |

## Codex

| Jurisdiction | Family | Substance | Official sources | Legal authority | Reference value | Exact MRL/ML coverage | Currency metadata | Gap reason or coverage note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `codex_global` | `pesticide_residue` | `glyphosate` | yes | yes | yes | no | partial | The official Codex/JMPR ADI is shipped, but no exact wave-1 CXL for the current taxonomy was curated in this pass. |
| `codex_global` | `pesticide_residue` | `acetamiprid` | yes | yes | yes | partial | partial | Official Codex/JMPR ADI plus exact curated CXL coverage for `grapes`; broader commodity extraction is deferred. |
| `codex_global` | `pesticide_residue` | `imidacloprid` | yes | yes | yes | partial | partial | Official Codex/JMPR ADI plus exact curated CXL coverage for `apples`, `grapes`, and `tomatoes`; broader commodity extraction is deferred. |
| `codex_global` | `pesticide_residue` | `glufosinate` | yes | yes | yes | partial | partial | Official Codex/JMPR ADI and ARfD plus exact curated CXL coverage for `grapes`, `rice`, and `potatoes`; broader commodity extraction is deferred. |
| `codex_global` | `pesticide_residue` | `oxamyl` | yes | yes | yes | partial | partial | Official Codex/JMPR ADI and ARfD plus exact curated CXL coverage for `tomatoes` and `potatoes`; broader commodity extraction is deferred. |
| `codex_global` | `pfas_food_contaminants` | `PFAS` | no | no | no | n/a | no | No final official Codex PFAS food reference-value or contaminant anchor is curated in wave 1. |
| `codex_global` | `acrylamide_process_contaminants` | `acrylamide` | no | no | no | n/a | no | No final official Codex acrylamide reference-value or contaminant anchor is curated in wave 1. |
| `codex_global` | `bisphenol_food_contact_migration` | `bisphenol_a` | no | no | no | n/a | no | No final official Codex BPA food-contact reference-value or contaminant anchor is curated in wave 1. |
| `codex_global` | `cadmium_food_contaminants` | `cadmium` | yes | yes | no | partial | yes | The current official `CXS 193-1995` text is now curated with an exact Codex cadmium ML for `wheat`; no jurisdiction-specific dietary reference value is shipped and broader cadmium extraction remains deferred. |
| `codex_global` | `lead_food_contaminants` | `lead` | yes | yes | no | partial | yes | The current official `CXS 193-1995` text is now curated with exact Codex lead MLs for `apples`, `grapes`, `apple_juice`, `wheat`, `rice`, `milk`, `infant_formula`, and `salmon`; no jurisdiction-specific dietary reference value is shipped. |
| `codex_global` | `inorganic_arsenic_food_contaminants` | `inorganic_arsenic` | yes | yes | no | partial | yes | The current official `CXS 193-1995` text is now curated with an exact Codex inorganic-arsenic ML for `olive_oil`; the rice lane remains intentionally unresolved because the shipped taxonomy does not distinguish husked from polished rice. |
| `codex_global` | `mercury_food_contaminants` | `methylmercury` | yes | yes | no | no | yes | The current official `CXS 193-1995` text remains anchor-only for methylmercury because the Codex rows are species-specific and do not yet map exactly to the shipped fish taxonomy. |
| `codex_global` | `mercury_food_contaminants` | `inorganic_mercury` | yes | yes | no | no | yes | The current official `CXS 193-1995` text remains anchor-only for inorganic mercury because no inorganic-mercury-specific current-taxonomy food ML is curated; the standard instead provides total-mercury and species-specific methylmercury lanes. |

## China

| Jurisdiction | Family | Substance | Official sources | Legal authority | Reference value | Exact MRL/ML coverage | Currency metadata | Gap reason or coverage note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `cn` | `pesticide_residue` | `glyphosate` | yes | yes | yes | partial | yes | Official GB 2763-2026 ADI plus exact curated MRL coverage for `apples` and `rice`; broader commodity extraction is deferred. |
| `cn` | `pesticide_residue` | `acetamiprid` | yes | yes | yes | partial | yes | Official GB 2763-2026 ADI plus exact curated MRL coverage for `apples`, `grapes`, and `tomatoes`; broader commodity extraction is deferred. |
| `cn` | `pesticide_residue` | `imidacloprid` | yes | yes | yes | partial | yes | Official GB 2763-2026 ADI plus exact curated MRL coverage for `apples`, `grapes`, `rice`, `tomatoes`, and `potatoes`; broader commodity extraction is deferred. |
| `cn` | `pesticide_residue` | `glufosinate` | yes | yes | yes | partial | yes | Official GB 2763-2026 ADI plus exact curated MRL coverage for `grapes`, `rice`, `tomatoes`, and `potatoes`; broader commodity extraction is deferred. |
| `cn` | `pesticide_residue` | `oxamyl` | yes | yes | yes | partial | yes | Official GB 2763-2026 ADI plus exact curated MRL coverage for `tomatoes` and `potatoes`; broader commodity extraction is deferred. |
| `cn` | `pfas_food_contaminants` | `PFAS` | no | no | no | n/a | no | No final official China PFAS food reference-value or binding contaminant anchor is curated in wave 1. |
| `cn` | `acrylamide_process_contaminants` | `acrylamide` | no | no | no | n/a | no | No final official China acrylamide food reference-value or binding contaminant anchor is curated in wave 1. |
| `cn` | `bisphenol_food_contact_migration` | `bisphenol_a` | no | no | no | n/a | no | No final official China BPA food-contact reference-value or binding contaminant anchor is curated in wave 1. |
| `cn` | `cadmium_food_contaminants` | `cadmium` | yes | yes | no | partial | yes | Exact `GB 2762-2025` MLs are now curated for rice, fish, and infant auxiliary cereal foods; no jurisdiction-specific dietary reference value is shipped. |
| `cn` | `lead_food_contaminants` | `lead` | yes | yes | no | partial | yes | Exact `GB 2762-2025` MLs are now curated for grain/rice, fish, infant formula, and infant auxiliary foods; no jurisdiction-specific dietary reference value is shipped. |
| `cn` | `inorganic_arsenic_food_contaminants` | `inorganic_arsenic` | yes | yes | no | partial | yes | Exact `GB 2762-2025` MLs are now curated for rice, fish, and multiple infant auxiliary-food categories; no jurisdiction-specific dietary reference value is shipped. |
| `cn` | `mercury_food_contaminants` | `methylmercury` | yes | yes | no | partial | yes | Exact `GB 2762-2025` methylmercury MLs are now curated for aquatic animals and carnivorous fish; no jurisdiction-specific dietary reference value is shipped. |
| `cn` | `mercury_food_contaminants` | `inorganic_mercury` | yes | yes | no | no | yes | `GB 2762-2025` provides mercury anchors, but no inorganic-mercury-specific food ML is curated; the runtime keeps this lane as an explicit gap rather than substituting total-mercury or methylmercury limits. |
