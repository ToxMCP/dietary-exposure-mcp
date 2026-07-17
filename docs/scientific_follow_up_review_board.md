# Scientific Follow-Up Review Board

`dietary_export_scientific_follow_up_review_board` converts a readiness-side scientific follow-up queue bundle into a reviewer-operable routing board.

## Purpose

- group readiness follow-up items into deterministic owner lanes
- classify each item into an operational due state
- preserve the original readiness and queue-bundle semantics without inventing new scientific or regulatory conclusions

## Inputs

- a `scientificFollowUpQueueBundle`
- an optional board note

## Routing semantics

The review board is derived from the queue bundle only.

- `review_lead`
  - any escalated follow-up item
- `regulatory_reviewer`
  - governance-oriented ledger categories
- `scientific_reviewer`
  - all remaining scientific follow-up items

## Due-state semantics

- `immediate`
  - escalated items
  - open blocking items
- `current_cycle`
  - open or pending items that are not immediate
- `in_progress`
  - acknowledged items
- `closed_with_waiver`
  - waived items without an escalation overlay
- `closed`
  - completed items

## Boundary

- the board is routing metadata for reviewer operations
- any inherited `legalLimitReviews` remain contextual support snapshots only; they are not re-scored or collapsed during routing
- it does not alter dossier status, signoff status, or readiness scoring
- it does not create new regulatory requirements

Use `dietary_export_scientific_follow_up_owner_handoff_packet` when reviewer operations need one owner-lane packet, optionally constrained to specific due states, instead of the full routing board.
