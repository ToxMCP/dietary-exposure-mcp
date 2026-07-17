# Extension Hooks

Dietary MCP supports additive extension packs under `defaults/extensions/v1/`.

## Supported categories

- `defaults/extensions/v1/commodity_taxonomy/*.json`
- `defaults/extensions/v1/consumption_profiles/*.json`
- `defaults/extensions/v1/reporting_profiles/*.json`

## Rules

- extension packs must be additive
- extension packs must not override existing commodity codes or profile ids
- taxonomy packs must declare `kind: "commodity_taxonomy"`
- consumption-profile packs must declare `kind: "consumption_profiles"`
- reporting-profile packs must declare `kind: "reporting_profiles"`

## Reporting-profile rule

- reporting-profile extensions are additive metadata overlays, not replacements for built-in EU reporting bases
- optional national or advisory profiles must remain explicitly non-substitutable where the base EU profile is still the primary regulatory basis
- base defaults must not depend on extension-only profile ids; extensions may be surfaced downstream by family, jurisdiction, and matrix-group matching

These hooks preserve the public contracts while allowing future regional or taxonomy growth.
