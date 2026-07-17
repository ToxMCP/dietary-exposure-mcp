# Trade Risk Review

The trade-risk review workflow packages jurisdiction-specific trade screening into an internal-review bundle or pinned dossier.

Use it when a residue-screening result needs to be handed to another reviewer, recorded for audit, or frozen with the exact manifests and documentation that were in force at review time.

Key interpretation rules:

- `pass` means all applicable governed limits that were actually found were met. It does not mean the jurisdiction is globally complete or commercially cleared.
- `inconclusive_no_limit` remains a live review signal. Use `mrlCoverageStatus` and `referenceValueJurisdictionStatus` to determine whether the gap is an explicit absence, anchor-only posture, family-curated-without-value layer, or a requested commodity pair outside the shipped curated scope.
- Trade screening preserves strict no-borrowing semantics across jurisdictions. Missing `US`, `Codex`, `China`, or `EU` support must remain explicit and must not be flattened by copying support from another authority.
- The bundle and dossier are review artifacts, not market-release authorisations, customs-clearance records, or regulator-acceptance packets.

Recommended reviewer checks:

- confirm the governed substance identity was resolved correctly
- inspect `tradeStatus`, `statusReason`, and `mrlViolations`
- inspect `mrlCoverageStatus`, `mrlCuratedSupportTypes`, and `mrlCuratedScopeCommodityCodes`
- inspect `referenceValueJurisdictionStatus` and `referenceValueCuratedSupportTypes`
- review top-level and per-jurisdiction `notes` before treating a lane as operationally usable

The version-pinned dossier extends the bundle by freezing release metadata, documentation fingerprints, and the exact manifest layer used during review.

If a non-confidential handoff is needed, `dietary_export_sanitised_public_review_dossier` can derive a sanitised-public trade-risk dossier that retains jurisdiction-level screening semantics, review prompts, and no-borrowing notes while redacting the internal substance identity layer and removing substance-scoped reference/MRL resource URIs.
