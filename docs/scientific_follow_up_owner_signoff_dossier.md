# Scientific Follow-Up Owner Signoff Dossier

`dietary_export_version_pinned_scientific_follow_up_owner_signoff_dossier` freezes an owner-lane scientific follow-up signoff packet together with the exact upstream review dossier and release metadata used during review.

Use this workflow when one reviewer lane needs a pinned, audit-ready handoff that preserves:

- the exact source dossier payload
- the exact owner-lane signoff packet payload
- the carried-forward source governance context
- any inherited `legalLimitReviews` already attached to the owner-lane signoff packet
- any model-governance or emerging-contaminant family snapshot already attached upstream
- explicit escalation items for waived or unresolved blocking owner actions

## Inputs

- `sourceDossier`
  - one version-pinned adapter, contaminant-monitoring, or metals-monitoring review dossier
- `signoffPacket`
  - the owner-lane signoff packet derived from readiness-side scientific follow-up routing for that same source dossier

## Output semantics

The dossier:

- pins the owner-lane signoff packet and upstream source dossier by content hash
- pins `release://metadata-report`
- pins the owner-signoff workflow documentation plus the source-workflow documentation already required for that lane
- preserves the upstream source-governance snapshot
- preserves `modelGovernanceSnapshot` for adapter-sourced dossiers
- preserves `emergingContaminantSnapshot` for contaminant- and metals-monitoring dossiers
- preserves `legalLimitReviews` so audit consumers can still see exact, partial, anchor-only, and explicit-gap legal-limit posture
- derives escalation items only from explicit waivers and unresolved blocking owner actions

The dossier does not:

- create a new readiness profile
- replace the upstream dossier
- change queue, board, handoff, remediation, or signoff state
- imply submission readiness or final regulatory approval

If a non-confidential handoff is needed, `dietary_export_sanitised_public_review_dossier` can derive a sanitised-public owner-lane signoff dossier that preserves retained governance snapshots, `legalLimitReviews`, and waiver/blocking escalation posture while removing the exact upstream dossier and owner-signoff payload fingerprints.

## Recommended use

1. Assess the source dossier with `dietary_assess_review_dossier_readiness`
2. Export the scientific follow-up queue bundle
3. Export the scientific follow-up review board
4. Export an owner handoff packet
5. Export an owner remediation packet
6. Export an owner signoff packet
7. Export this version-pinned owner signoff dossier when that lane needs an audit-ready pinned overlay for downstream review or inspection

## Boundary

This is an owner-lane audit overlay. It records the exact owner signoff state and escalations already present for that lane, but it does not create a new submission package, final decision artifact, or cryptographically signed dossier in v0.1.
