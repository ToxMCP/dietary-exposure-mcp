# Suite Integration Guide

Dietary MCP is a sibling service in the ToxMCP suite.

## Upstream

- curated residue evidence
- governed commodity taxonomy
- governed consumption profiles

## Downstream

- PBPK MCP consumes normalized oral dose bundles
- ToxClaw consumes dietary evidence bundles and scenario comparisons
- Direct-Use Exposure MCP remains the owner of direct-use oral workflows

## Herbal and supplement routing

- Medicinal TCM regimens and product-centric supplement dosing stay in Direct-Use Exposure MCP.
- Herbal teas, food-like botanicals, and nutrition-style supplement intake belong in Dietary MCP.
- Environmental-media oral intake from water or soil is still not routed into Dietary MCP by
  default unless the workflow becomes food-mediated residue plus consumption.

## Cross-MCP rule

Adapters should hand off shared contracts such as `route_dose_estimate` and `pbpk_external_import_bundle`, not model-native dietary payloads.

## Checked-in cross-suite fixtures

- `tests/fixtures/cross_suite/woe_ngra/dietary_exposure_handoff.v1.1.0.json`
  freezes the direct `Dietary -> WoE` handoff lane.
- The same source fixture is synced into IVIVE as the upstream anchor for the
  `Dietary -> IVIVE -> WoE` three-hop round-trip.

## Environmental-media oral seam

Environmental-media oral intake from water or soil is not routed into Dietary MCP by default.
That seam should start from Fate MCP `concentration_surface` outputs and only enter Dietary MCP
when the workflow becomes food-mediated residue plus consumption.
The new checked-in `Fate surface_water -> Exposure -> WoE` and
`Fate surface_water -> Exposure -> IVIVE -> WoE` bridges are intentionally
outside Dietary MCP and keep `environmental_media` oral screening distinct from
`food_mediated` intake.
The new checked-in `Fate agricultural_soil -> Exposure -> WoE` and
`Fate agricultural_soil -> Exposure -> IVIVE -> WoE` bridges are also
intentionally outside Dietary MCP and keep soil-contact environmental oral
screening distinct from both `food_mediated` intake and unresolved crop uptake.
