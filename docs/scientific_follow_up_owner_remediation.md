# Scientific Follow-Up Owner Remediation

`dietary_export_scientific_follow_up_owner_remediation_packet` derives an owner-scoped remediation packet from the scientific follow-up owner handoff packet.

Use this workflow when one reviewer lane needs deterministic operational guidance for what to resolve now, review this cycle, keep tracking, or record as closed.

## Inputs

- `handoffPacket`
  - the owner-scoped packet exported from `dietary_export_scientific_follow_up_owner_handoff_packet`
- `packetNote` (optional)
  - additive reviewer note attached to the exported remediation packet

## Output semantics

The remediation packet preserves:

- the source dossier, bundle, board, and handoff identifiers
- the selected owner lane and any due-state filter already applied upstream
- any inherited `legalLimitReviews` so remediation stays anchored to the same jurisdiction-support posture
- the routed action items with one remediation class per action
- grouped action ids for `resolve_now`, `review_this_cycle`, `track_in_progress`, and `record_closure`
- the recommended remediation sequence derived from the owner handoff sequence
- linked documentation and workflow resources

The remediation packet does not:

- create new scientific findings
- change reviewer decision state
- mutate readiness, signoff, or dossier content
- imply submission readiness

## Recommended use

1. Assess the review dossier with `dietary_assess_review_dossier_readiness`
2. Export the scientific follow-up queue bundle
3. Export the scientific follow-up review board
4. Export one owner handoff packet per reviewer lane, optionally filtered by due state
5. Export an owner remediation packet when that lane needs deterministic operational next steps
6. Export an owner signoff packet when that lane needs auditable acknowledgement, completion, or waiver state

## Boundary

Owner remediation packets are operational review artifacts layered on top of routed scientific follow-up work. They classify existing action state into deterministic remediation classes, but they do not replace governed signoff or version-pinned dossier export.
