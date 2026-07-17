# Regulatory Seed Data

Dietary MCP v0.1 can publish public regulatory seed profiles that are suitable for transparent screening workflows but not final regulatory decisions.

## Current public seed sources

- Dietary MCP illustrative screening defaults: five transparent screening populations over thirteen canonical commodity codes for internal screening and review-support workflows.
- WHO GEMS/Food Cluster Diets 2012 public dataset: chronic model diets in grams/person/day across 17 supra-national clusters.
- EFSA PRIMo tools metadata: tracked as an official model-family reference for future adapter work, not exposed as a native public consumption-profile pack.
- EPA DEEM-FCID metadata: tracked as an official model-family reference for future adapter work, not exposed as a native public consumption-profile pack.
- EFSA OpenFoodTox, EFSA food-consumption infrastructure, and DietEx metadata are now exposed through governed source-database registries rather than direct seed-profile generation.
- Emerging microplastics records are published as a separate governed source family with explicit `not_allowed` submission posture.

## WHO GEMS/Food seed-pack rules

- Public WHO seed profiles are chronic-only.
- The seed pack uses a standard 60 kg adult body weight to normalize intake on a mg/kg-bw/day basis.
- Commodity coverage is intentionally narrow and uses explicit broad-category proxies where the WHO dataset is coarser than the Dietary MCP commodity taxonomy.
- Every proxy mapping emits quality flags and limitation notes so the result cannot be mistaken for a commodity-specific survey record.

## Review boundary

- `reviewStatus: public_official_seed` means the pack is derived from a public official source and has been structured for MCP use, but it is still a screening seed rather than a jurisdiction-approved final assessment pack.
- Jurisdiction-specific regulatory assessments should replace these seed packs with reviewed population data aligned to the target method, body-weight convention, and commodity definitions.
