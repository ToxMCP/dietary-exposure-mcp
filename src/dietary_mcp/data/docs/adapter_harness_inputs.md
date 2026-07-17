# Adapter Harness Inputs

Dietary MCP v0.1 includes an internal adapter normalizer for synthetic PRIMo- and DEEM-shaped outputs.

## Purpose

- prove that external dietary-engine-style results can be normalized into the public Dietary MCP contracts
- keep the public MCP surface free of raw model-native tools
- make adapter dry runs auditable before any official engine integration is attempted

## Internal payload expectations

- a declared `model_family` such as `efsa_primo_adapter` or `epa_deem_adapter`
- an external case identifier and engine version string
- a declared total intake in `mg/kg-bw/day`
- either normalized contribution objects or tabular rows that can be mapped into them
- commodity contribution rows with:
  - an external commodity code or alias
  - contribution value in `mg/kg-bw/day`
  - residue concentration in `mg/kg`
  - consumption amount in `kg_food/day`
  - processing factor
- optional lower and upper bounds
- optional assumption records, source references, and explanatory notes

## Supported tabular aliases

- commodity: `commodity_code`, `commodity`, `food`, `food_code`
- contribution: `contribution_mg_per_kg_bw_per_day`, `exposure_mg_per_kg_bw_per_day`, `exposure_mgkgbwday`, `iedi_mgkgbwday`, `iesti_mgkgbwday`
- residue: `residue_concentration_mg_per_kg`, `residue_mg_per_kg`, `residue_mgkg`, `hr_mgkg`, `stmr_mgkg`
- consumption: `consumption_kg_per_day`, `consumption_kgday`, `consumption_kg_day`, `food_consumption_kg_per_day`
- processing factor: `applied_processing_factor`, `processing_factor`, `pf`
- lower and upper contribution bounds: `lower_bound_intake_mg_per_kg_bw_per_day` / `upper_bound_intake_mg_per_kg_bw_per_day` plus shorthand aliases `lb_mgkgbwday` / `ub_mgkgbwday`

CSV imports use the same alias set through header matching.

## Validation rules

- the payload model family must match the scenario model family
- contribution totals must reconcile to the declared total within a tight tolerance
- external commodity codes are resolved through the governed Dietary MCP taxonomy and carry mapping flags forward
- normalized outputs must remain explicit about harness status and non-equivalence to official external engines
