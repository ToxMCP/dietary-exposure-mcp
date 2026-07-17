# Confidentiality-Aware Review Bundles

Dietary MCP v0.1 adds a Phase 2 packaging layer for confidentiality-aware review bundles and dossiers.

## Bundle profiles

The review export flow now distinguishes three bundle profiles:

- `internal_review`
- `submission_candidate`
- `sanitised_public`

Current built-in exports default to `internal_review`. No current model family becomes submission-capable because of this packaging layer.

## Confidentiality metadata

Review resources and pinned resources publish:

- `confidentialityTag`
- `sanitisationState`

Version-pinned dossiers also publish:

- `confidentialityAnnotations` for governed field-level sensitivity
- `sanitisationRecords` for removed resources and redacted fields

## Sanitised public export

Use `dietary_export_sanitised_public_review_dossier` to derive a public-facing dossier from an internal review dossier.

The export:

- retains non-confidential review resources
- retains release metadata and governed source/model snapshots
- supports adapter, contaminant-monitoring, metals-monitoring, scientific-follow-up owner-signoff, and trade-risk review dossiers
- preserves `legalLimitReviews` for monitoring-derived dossiers and owner-lane signoff overlays so exact, partial, anchor-only, or explicit-gap legal-limit posture remains machine-readable in public exchange
- preserves owner-lane escalation visibility for scientific-follow-up owner-signoff dossiers while removing the internal source-dossier and owner-packet payload fingerprints
- preserves jurisdiction-level trade-screening semantics for trade-risk dossiers while redacting identity-bearing substance fields and removing substance-scoped resource URIs
- removes confidential resources from the public output
- emits machine-readable redaction markers for confidential fields

## Current v0.1 defaults

The built-in sanitised export currently redacts:

- `check_result.chemical_identity`
- `check_result.declared_totals`

It currently removes the pinned `release_metadata_report` resource from the public bundle while retaining the reduced `release_metadata` snapshot for provenance. Owner-lane scientific follow-up public exports also remove the exact upstream source-dossier and owner-signoff payload fingerprint resources.

## Boundary

Sanitised public dossiers are packaging artifacts for public-facing review exchange. They are not complete internal review records and they are not submission dossiers.
