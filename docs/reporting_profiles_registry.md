# Reporting Profiles Registry

`reporting_profiles.json` publishes governed reporting conventions that can sit on top of occurrence-evidence and analytical-method-evidence records without changing the underlying evidence basis.

These profiles are intended to answer a narrower question than a reference value or method record:

- how should a monitored analyte panel be aggregated or preserved for reporting
- which profile is the primary regulatory basis for the current jurisdiction
- which profiles are optional advisory or supporting-detail extensions
- which profiles must not be substituted for each other

Current v0.1 scope:

- `eu.pfas.efsa4.food_risk` as the primary EU PFAS reporting profile
- `eu.pfas.efsa4.ml_lower_bound` as the EU compliance-oriented EFSA-4 lower-bound variant
- `eu.pfas.individual_panel_detail` as the supporting analyte-level detail profile
- `nl.pfas.rivm_peq.food_advisory` as an optional Dutch home-egg advisory extension profile
- `nl.pfas.rivm_peq.biota_fish_advisory` as an optional Dutch fish and biota advisory extension profile

Current policy:

- EU food-regulatory review should default to the primary EFSA-4 profile
- optional national advisory profiles do not replace the primary EU basis
- optional Dutch PEQ-style profiles should stay scoped to their own governed matrix use cases instead of being collapsed into one generic national metric
- `notSubstitutableForProfileIds` must be respected by downstream review tooling
- the registry is governance metadata only; it does not implement a PEQ calculator or any other quantitative aggregation engine

Current limitation:

- the shipped PFAS profiles are illustrative governed reporting conventions tied to the analytes already represented in Dietary MCP
- extension profiles can be surfaced during monitoring review without becoming built-in submission-ready defaults
