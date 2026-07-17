# Metals Monitoring Review Dossier

`dietary_export_version_pinned_metals_monitoring_review_dossier` packages a governed metals monitoring interpretation bundle and reviewer signoff packet into a version-pinned internal-review dossier.

The dossier is designed for auditability, not for new quantitative inference. It pins:
- `release://metadata-report`
- governed source, reference-value, dataset, method, and legal manifests
- `contaminant-legal-limits://manifest`
- `contaminant-legal-limits://family/{family_id}`
- `contaminant-legal-limits://jurisdiction/{jurisdiction}` when the reviewed bundle is jurisdiction-scoped
- `jurisdiction-coverage://manifest`
- `jurisdiction-coverage://jurisdiction/{jurisdiction}` when the reviewed bundle is jurisdiction-scoped
- family-specific `metals-occurrence://...` and `metals-review-focus://...` payloads
- family-specific `emerging-contaminants://...` governance
- workflow documentation fingerprints for interpretation and signoff

The escalation overlay is fixed and narrow:
- waived signoff actions become `waiver_review` escalation items
- unresolved blocking actions become `blocking_follow_up` escalation items

The dossier does not create submission readiness. It preserves the current review-only boundary for metals monitoring workflows and keeps unresolved reviewer decisions explicit.

The dossier also preserves the interpretation bundle's `uncertaintyAndAssumptionLedger`, so monitoring-context assumptions, trend-signal limits, and review-only governance posture remain visible in the pinned review object.
It also preserves the interpretation bundle's `legalLimitReviews`, so family-level legal-limit support remains explicit even when the bundle is built from occurrence and review-focus context rather than a native limit-matching workflow.
If a reviewer waives or leaves unresolved a ledger-derived signoff action, that scientific item also appears in the dossier escalation overlay.

Use this workflow when a reviewer needs one pinned object that captures:
- the governed occurrence context
- the governed review-focus prompts
- the reviewer decision state
- the exact manifest set used during the review
- the remaining waivers or follow-up actions

Current limitations:
- internal-review only
- version-pinned, not cryptographically signed
- no native metals exposure engine
- no final regulatory decision semantics
- closed dossiers require governed occurrence context and no unresolved blocking signoff actions

Use `dietary_assess_review_dossier_readiness` on this dossier when the reviewer needs a machine-readable governance status. Metals dossiers can be assessed against family-specific profiles such as `mercury_internal_review`, `mercury_consultation_exploratory`, or `mercury_submission_candidate` in addition to the generic EU profiles.
The readiness result also surfaces ledger-derived scientific follow-up action ids from the dossier signoff packet, so monitoring-context assumptions and trend-related follow-up stay aligned across signoff, readiness, and dossier escalation layers.
It also classifies those follow-up items into readiness-side queues for open, pending, acknowledged, completed, waived, and escalated actions.
Use `dietary_export_scientific_follow_up_queue_bundle` after readiness when those follow-up items need to be handed off into a downstream reviewer queue or case-management workflow without rebuilding queue state from raw readiness fields.
Use `dietary_export_scientific_follow_up_review_board` when the downstream reviewer workflow also needs deterministic owner-lane and due-state routing for those follow-up items.
Use `dietary_export_scientific_follow_up_owner_handoff_packet` when one owner lane needs a scoped reviewer handoff packet, optionally limited to specific due states.
Use `dietary_export_scientific_follow_up_owner_remediation_packet` when that owner lane also needs deterministic remediation classes for immediate resolution, current-cycle review, in-progress tracking, or closure recording.
Use `dietary_export_scientific_follow_up_owner_signoff_packet` when that owner lane also needs auditable acknowledgement, completion, or waiver state on the remediation items before downstream handoff.
Use `dietary_export_version_pinned_scientific_follow_up_owner_signoff_dossier` when that same owner lane needs a pinned audit overlay that freezes the exact owner signoff packet and this upstream metals-monitoring dossier together.
