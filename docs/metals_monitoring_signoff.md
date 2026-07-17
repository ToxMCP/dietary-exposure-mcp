# Metals Monitoring Signoff Packet

Dietary MCP exposes a read-only `dietary_export_metals_monitoring_signoff_packet` workflow to layer explicit reviewer decisions on top of a governed metals monitoring interpretation bundle.

## Purpose

The signoff packet is intended to capture reviewer disposition, not to change the underlying monitoring bundle:

- pending, acknowledged, completed, or waived action decisions
- reviewer identity and role
- supporting resource references cited during review
- unresolved blocking actions that still require escalation
- explicit confirmation that current metals workflows remain review-oriented

The packet is an audit overlay. It does not convert a metals monitoring bundle into a submission-capable engine or a final regulatory decision object.

## Inputs

The workflow builds on:

- `dietary_export_metals_monitoring_interpretation_bundle`

The request packages:

- the governed interpretation bundle
- reviewer id and reviewer role
- optional action decisions with rationale, review timestamp, and supporting URIs
- an optional packet note

## Action model

The exporter derives a fixed action list from the interpretation bundle. Typical actions include:

- review occurrence context
- review priority food groups
- review sensitive populations
- review commodity-focus prompts
- review scientific-ledger entries for governed monitoring-context assumptions, sensitive-population prompt context, and trend-signal limits
- review governance links

If review-focus records are not linked back to the supplied occurrence context, the packet also emits a blocking linkage-resolution action.

## Output posture

The packet returns:

- `legalLimitReviews`
- `actionItems`
- `pendingActionIds`
- `acknowledgedActionIds`
- `completedActionIds`
- `waivedActionIds`
- `unresolvedBlockingActionIds`
- `referencedResources`
- `overallSignoffStatus`

`overallSignoffStatus` stays `open` whenever blocking actions are unresolved or actions remain only acknowledged. `signed_off_with_waivers` is explicit when the review is closed with at least one waiver. `signed_off` only appears when all actions are completed with no waivers.
`legalLimitReviews` keeps family-level exact-versus-partial-versus-anchor-versus-gap legal-limit support visible during signoff instead of letting reviewers infer support depth from occurrence context alone.

## Review boundary

The intended use is:

- reviewer acknowledgement and escalation tracking
- auditable waiver recording
- preservation of supporting evidence and guidance links
- explicit visibility of unresolved blocking review items

The signoff packet should not be presented as:

- a native metals exposure or risk engine
- a substitute for human regulatory review
- evidence that submission-candidate use is allowed for current metals families

Blocking actions marked `completed` or `waived` require supporting URIs, and unresolved blocking actions keep the packet `open`.
