# Metals Monitoring Interpretation Bundle

Dietary MCP exposes a read-only `dietary_export_metals_monitoring_interpretation_bundle` workflow to package governed metals monitoring context into one review object.

## Purpose

The bundle is intended to keep reviewer context together for cadmium, lead, inorganic arsenic, and mercury:

- family-level occurrence and monitoring context
- commodity- and population-specific review-focus records
- linked source, method, legal-authority, dataset, and reference-value identifiers
- a structured `uncertaintyAndAssumptionLedger` covering review-only governance posture, governed monitoring-context assumptions, and unresolved linkage gaps
- reviewer prompts derived from governed occurrence and review-focus questions
- priority food groups, high-attention foods, sensitive populations, and trend signals

This bundle does not calculate exposure, margin of exposure, or final regulatory conclusions.

## Inputs

The export is additive on top of the existing governed lookup tools:

- `dietary_lookup_metals_occurrence`
- `dietary_lookup_metals_review_focus`

The request packages those two lookup results together, plus an optional bundle note.

## Validation behavior

The exporter rejects:

- mismatched contaminant families
- mismatched jurisdictions when both inputs are explicit
- mismatched authorities when both inputs are explicit

These checks are there to stop accidental mixing of review contexts across incompatible filters.

## Output posture

The bundle returns:

- `occurrenceRecords`
- `reviewFocusRecords`
- linked and unresolved occurrence-record identifiers
- covered source, method, legal-authority, dataset, and reference-value ids
- `reviewPrompts`
- `referencedResources`
- `recommendedSequence`

`overallSubmissionUse` is aggregated conservatively from the supplied lookup results. Current metals families remain `review_required`, and `submissionCandidateAllowed` remains `false`.

## Review use

The intended use is:

- reviewer triage
- occurrence-monitoring interpretation
- commodity-priority review
- population-priority review
- audit-ready handoff of governed monitoring context

The bundle should not be presented as a native metals exposure engine or as a submission-capable decision package.
