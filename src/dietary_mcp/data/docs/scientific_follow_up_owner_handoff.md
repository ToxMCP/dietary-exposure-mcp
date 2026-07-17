# Scientific Follow-Up Owner Handoff

`dietary_export_scientific_follow_up_owner_handoff_packet` derives an owner-scoped handoff packet from the scientific follow-up review board.

Use this workflow when reviewer operations need a stable packet for one owner lane instead of the full routing board.

## Inputs

- `board`
  - the scientific follow-up review board exported from `dietary_export_scientific_follow_up_review_board`
- `ownerLane`
  - one of `review_lead`, `regulatory_reviewer`, or `scientific_reviewer`
- `dueStateFilter` (optional)
  - restricts the packet to one or more due states such as `immediate` or `current_cycle`
- `packetNote` (optional)
  - additive reviewer note attached to the exported packet

## Output semantics

The packet preserves:

- the source dossier, bundle, and board identifiers
- the selected owner lane
- the selected due-state filter
- any inherited `legalLimitReviews` from readiness-side review
- the filtered action items and due-state groups
- blocking, immediate, current-cycle, in-progress, and closed action lists
- the recommended owner sequence derived from the board triage order
- referenced documentation and workflow resources

The packet does not:

- change readiness state
- mutate signoff or dossier content
- create new regulatory rules
- imply submission readiness

## Recommended use

1. Assess the review dossier with `dietary_assess_review_dossier_readiness`
2. Export the scientific follow-up queue bundle
3. Export the scientific follow-up review board
4. Export one owner handoff packet per reviewer lane, optionally filtered by due state
5. Export an owner remediation packet when that lane needs deterministic next-step guidance instead of routing only

## Boundary

Owner handoff packets are operational review artifacts. They exist to route work, preserve traceability, and keep reviewer scope explicit. They are not a substitute for governed signoff or version-pinned dossier export.
