# Contaminant Monitoring Review Dossier

`dietary_export_version_pinned_contaminant_monitoring_review_dossier` packages a governed contaminant-monitoring interpretation bundle together with its reviewer signoff packet and the exact manifests and workflow documentation used during review.

## What it pins

- `release://metadata-report`
- `source-catalog://manifest`
- `reference-values://manifest`
- `contaminant-legal-limits://manifest`
- `contaminant-legal-limits://family/{family_id}`
- `contaminant-legal-limits://jurisdiction/{jurisdiction}` when the reviewed bundle is jurisdiction-scoped
- `consumption-datasets://manifest`
- `method-registry://manifest`
- `legal-authorities://manifest`
- `jurisdiction-coverage://manifest`
- `jurisdiction-coverage://jurisdiction/{jurisdiction}` when the reviewed bundle is jurisdiction-scoped
- `occurrence-evidence://manifest`
- `occurrence-evidence://family/{family_id}`
- `analytical-method-evidence://manifest`
- `analytical-method-evidence://family/{family_id}`
- `reporting-profiles://manifest`
- `reporting-profiles://profile/{profile_id}` for each applicable governed reporting profile
- `metals-review-focus://manifest`
- `metals-review-focus://family/{family_id}` when linked review-focus records exist for the monitored family
- `emerging-contaminants://manifest`
- `emerging-contaminants://family/{family_id}`
- `docs://contaminant-monitoring-interpretation`
- `docs://contaminant-monitoring-signoff`
- `docs://occurrence-evidence-registry`
- `docs://analytical-method-evidence-registry`
- `docs://reporting-profiles-registry`

## Escalation overlay

Escalation items are derived only from reviewer state already present in the contaminant-monitoring signoff packet:

- waived actions become `waiver_review`
- unresolved blocking actions become `blocking_follow_up`

The dossier does not add new scientific conclusions. It freezes the governed review context and makes remaining reviewer deviations or blockers explicit.

The dossier also preserves the interpretation bundle's `uncertaintyAndAssumptionLedger`, so analytical gaps, lower-bound handling assumptions, and review-only governance posture stay visible in the pinned handoff object.
It also carries forward the interpretation bundle's `legalLimitReviews`, so exact, partial, anchor-only, or missing jurisdiction legal-limit support remains explicit in the pinned handoff object instead of being inferred from prose.
When governed reporting profiles apply, the dossier also preserves the carried-forward `reportingProfileSummary` and an explicit snapshot of the exact reporting-profile records used during review.
If a reviewer waives or leaves unresolved a ledger-derived signoff action, that scientific item appears in the dossier escalation overlay just like any other reviewer action.

## Boundary

- This is an internal-review dossier, not a submission-capable decision package.
- It is version-pinned through release and resource fingerprints, but it is not cryptographically signed in v0.1.
- It does not create a native contaminant exposure engine or final regulatory decision output.
- Closed dossiers require occurrence evidence, resolved error-severity quality flags, and no unresolved blocking signoff actions.

## Readiness assessment

`dietary_assess_review_dossier_readiness` accepts this dossier shape directly. Use the family-specific readiness profiles, such as `mercury_internal_review`, `mercury_consultation_exploratory`, or `mercury_submission_candidate`, when the review must stay aligned to the governed emerging-contaminant family rather than the generic EU adapter profiles.
The readiness result also surfaces ledger-derived scientific follow-up action ids from the dossier signoff packet, so the same monitoring-specific follow-up items remain visible across signoff, readiness, and dossier escalation views.
It also classifies those follow-up items into readiness-side queues for open, pending, acknowledged, completed, waived, and escalated actions.
Use `dietary_export_scientific_follow_up_queue_bundle` after readiness when those follow-up items need to move into a downstream reviewer queue or case-management system without re-deriving queue state from the raw readiness payload.
Use `dietary_export_scientific_follow_up_review_board` when that downstream workflow also needs deterministic owner-lane and due-state routing for reviewer operations.
Use `dietary_export_scientific_follow_up_owner_handoff_packet` when one owner lane, such as `scientific_reviewer` or `review_lead`, needs a scoped handoff packet instead of the full board.
Use `dietary_export_scientific_follow_up_owner_remediation_packet` when that owner lane also needs deterministic next-step classes for remediation and closure handling instead of routing-only output.
Use `dietary_export_scientific_follow_up_owner_signoff_packet` when that owner lane also needs auditable acknowledgement, completion, or waiver state on the remediation items before downstream handoff.
Use `dietary_export_version_pinned_scientific_follow_up_owner_signoff_dossier` when that same owner lane needs a pinned audit overlay that freezes the exact owner signoff packet and this upstream contaminant-monitoring dossier together.
