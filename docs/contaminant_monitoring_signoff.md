# Contaminant Monitoring Signoff Packet

The `dietary_export_contaminant_monitoring_signoff_packet` workflow adds reviewer decisions to a governed `contaminantMonitoringInterpretationBundle`.

## Inputs

- a `contaminantMonitoringInterpretationBundle`
- reviewer identity and role
- optional action decisions with rationale, review date, and supporting URIs
- an optional packet note

The workflow is intentionally downstream of `dietary_export_contaminant_monitoring_interpretation_bundle`. It does not parse raw CSV text directly.

## Output shape

The packet preserves:

- the source interpretation bundle identifier
- contaminant family, jurisdiction, authority, and dataset context
- the carried-forward `reportingProfileSummary` when the interpretation bundle matched governed reporting conventions
- the carried-forward `legalLimitReviews` so exact, partial, anchor-only, or missing jurisdiction legal-limit support remains explicit during reviewer signoff
- explicit reviewer action items for header-resolution review, occurrence-evidence review, analytical-method review, reporting-profile convention review, review-focus review, governance review, and critical quality-flag resolution when scientific errors remain
- explicit reviewer action items derived from `uncertaintyAndAssumptionLedger` entries, including analytical gaps, lower-bound handling assumptions, storage-stability context, and sampling-plan context
- decision-state tracking across pending, acknowledged, completed, waived, and unresolved blocking actions
- referenced supporting resources and operator documentation

## Current scope

In v0.1 this workflow is governed for the contaminants-monitoring families that already support interpretation bundles:

- pesticide residues
- PFAS
- acrylamide
- BPA food-contact dietary context
- cadmium
- lead
- inorganic arsenic
- mercury

## Boundary

This packet is a reviewer-facing overlay. It does not upgrade the underlying monitoring workflow into a submission-capable engine.

- `signed_off` means the configured reviewer actions were resolved for the current review packet.
- `signed_off_with_waivers` keeps approved deviations explicit.
- `open` means one or more actions remain pending, acknowledged, or unresolved.

Signed-off status does not imply final regulatory approval, native exposure modelling, or submission readiness.
The packet keeps legal-limit support semantics visible, but it does not upgrade partial or missing jurisdiction support into a blocker-resolved legal conclusion on its own.

Blocking actions cannot be closed on prose alone:

- blocking actions marked `completed` or `waived` require supporting URIs
- missing occurrence evidence or unresolved error-severity quality flags keep the packet open
