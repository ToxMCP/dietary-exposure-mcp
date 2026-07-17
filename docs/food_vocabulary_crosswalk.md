# Food Vocabulary Crosswalk

Dietary MCP v0.1 publishes a provisional food-vocabulary crosswalk layer for workflow hardening.

## Scope

The pack adds optional fields to commodity-facing outputs:

- `foodex2_code`
- `rpc_code`
- `rpcd_code`
- `processed_status`
- `mapping_confidence`

It also publishes:

- base canonical commodity mappings
- raw-primary-commodity to processed-derivative mappings
- processing-factor applicability records for supported derivative pairs

## Important boundary

These mappings are illustrative and provisional in v0.1.

- They are not official EFSA FoodEx2 identifiers.
- They are not official RPC or RPCD identifiers.
- They are intended to harden field shapes, review workflows, and downstream integration planning.

## Resources

- `food-vocabulary://manifest`
- `food-vocabulary://commodity/{commodity_code}`
- `food-vocabulary://processed/{processed_commodity_code}`

## Current behavior

Canonical commodity codes remain the stable primary identifiers in Dietary MCP contracts.

When a processed derivative such as `apple_juice` is recognized:

- the canonical commodity code remains the raw-primary-commodity code
- the derivative mapping is retained through optional food-vocabulary fields
- the matched input code preserves the derivative text that was supplied
- supported derivative-specific default processing factors can be applied

## Mapping confidence

`mapping_confidence` is published separately from the older taxonomy `mapping_status`.

- `mapping_status` describes canonical/alias resolution quality inside the current taxonomy
- `mapping_confidence` describes confidence in the optional food-vocabulary linkage
