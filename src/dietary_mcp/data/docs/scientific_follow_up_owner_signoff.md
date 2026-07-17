# Scientific Follow-Up Owner Signoff

`dietary_export_scientific_follow_up_owner_signoff_packet` derives an owner-scoped signoff packet from the scientific follow-up owner remediation packet.

Use this workflow when one owner lane needs an auditable reviewer overlay that records acknowledgement, completion, or waiver decisions on the routed remediation actions.

## Inputs

- `remediationPacket`
  - the owner-scoped packet exported from `dietary_export_scientific_follow_up_owner_remediation_packet`
- `reviewerId`
  - reviewer identifier for the owner lane recording decisions
- `reviewerRole`
  - reviewer role for the owner lane recording decisions
- `decisions`
  - additive decisions keyed by remediation `actionId`
- `packetNote` (optional)
  - additive reviewer note attached to the exported signoff packet

## Output semantics

The signoff packet preserves:

- the source dossier, bundle, board, handoff, and remediation identifiers
- the selected owner lane and any due-state filter already applied upstream
- any inherited `legalLimitReviews`, unchanged from readiness-side review semantics
- the routed remediation action items with decision state per action
- pending, acknowledged, completed, waived, and unresolved-blocking action lists
- the original remediation-class groupings and recommended signoff sequence
- linked documentation and workflow resources

The signoff packet does not:

- create new scientific findings
- change queue, board, handoff, or remediation content
- mutate readiness or dossier state
- imply submission readiness

## Recommended use

1. Assess the review dossier with `dietary_assess_review_dossier_readiness`
2. Export the scientific follow-up queue bundle
3. Export the scientific follow-up review board
4. Export one owner handoff packet per reviewer lane, optionally filtered by due state
5. Export an owner remediation packet when that lane needs deterministic operational next steps
6. Export an owner signoff packet when that lane needs auditable acknowledgement, completion, or waiver state
7. Export a version-pinned owner signoff dossier when that lane needs a pinned audit overlay on top of the signoff packet and source dossier

## Boundary

Owner signoff packets are reviewer overlays on top of routed remediation work. They preserve owner decisions and rationale, but they do not replace governed dossier signoff or version-pinned dossier export.
