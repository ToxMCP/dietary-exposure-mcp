# Interoperability Readiness

Dietary MCP publishes a governed readiness gate on top of the staged interoperability preview. This layer does not create XML, and it does not upgrade the preview into a submission-ready dossier. It evaluates whether the staged JSON preview is suitable for a named exchange gate.

## Surface

- tool: `dietary_assess_interoperability_preview_readiness`
- follow-on tool: `dietary_export_interoperability_remediation_bundle`
- manifest resource: `interoperability-readiness://manifest`
- profile resource: `interoperability-readiness://profile/{profile_id}`
- remediation catalog resource: `interoperability-remediation://catalog`
- validation resources:
  - `validation://interoperability-rules`
  - `validation://interoperability-readiness-profiles`
  - `validation://interoperability-remediation-actions`

## Current profiles

- `eu_internal_exchange_preview`
- `eu_consultation_exchange_preview`
- `eu_submission_xml_candidate`

Each profile links to a required dossier-readiness profile and then applies a fixed interoperability ruleset over:

- preview/source dossier consistency
- required-field completeness
- presence of a staged target document
- unsupported-field handling
- derived or review-required mapping handling
- linked dossier readiness status

## Status semantics

- `pass`: the staged preview satisfies the selected exchange gate
- `review_required`: the preview can be reviewed at that gate, but unsupported fields, derived mappings, or linked dossier governance still require human review
- `fail`: the selected exchange gate is blocked

`eu_submission_xml_candidate` is intentionally strict. With current model families and mapping coverage, it is expected to fail.

## Boundary

This readiness layer:

- does not imply IUCLID schema conformance
- does not imply OECD OHT completeness
- does not imply XML-generation readiness by itself
- does not override the separate dossier-readiness assessment

It is a staging control for governed JSON previews only.

Use the remediation bundle when reviewers need an ordered action list instead of raw rule results.
