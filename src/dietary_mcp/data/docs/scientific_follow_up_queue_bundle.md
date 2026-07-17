# Scientific Follow-Up Queue Bundle

`dietary_export_scientific_follow_up_queue_bundle` packages the scientific follow-up state already exposed by `dietary_assess_review_dossier_readiness` into one machine-readable handoff object.

## Purpose

- preserve readiness-side scientific follow-up items without forcing downstream systems to reconstruct queue state from raw readiness payloads
- keep queue semantics explicit for contaminant-monitoring and metals-monitoring dossiers
- export ordered follow-up items, queue labels, and referenced workflow documentation without mutating the underlying dossier or signoff packet

## Inputs

- a version-pinned review dossier
- a governed readiness assessment for that dossier
- an optional bundle note

## Output semantics

The bundle contains:

- the target readiness profile and overall readiness status
- any `legalLimitReviews` already attached to the readiness assessment, preserved without reinterpretation
- the source dossier id, dossier status, workflow kind, and bundle profile
- each scientific follow-up item with additive queue labels
- raw queue buckets and per-queue counts
- a recommended action sequence derived from queue priority
- referenced documentation and validation resources

Queue labels are additive. A follow-up item can appear in more than one queue, for example when a waiver is also escalated for explicit reviewer review.

If `legalLimitReviews` are present, they preserve the same exact-versus-partial-versus-anchor-versus-gap support semantics already surfaced by the governed monitoring workflows. The queue bundle does not flatten or reinterpret those support signals.

## Current scope

- adapter dossiers are supported, but normally export an empty follow-up bundle because they do not currently carry monitoring-ledger follow-up items
- contaminant-monitoring and metals-monitoring dossiers are the main consumers of this workflow
- this bundle is a review-support export only; it does not change readiness scoring or reviewer decisions
