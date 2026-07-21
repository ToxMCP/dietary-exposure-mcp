# Release Artifacts

This directory contains the human-readable release notes and the generated
evidence used to review a Dietary Exposure MCP release.

## Start here

- [`v0.1.0-rc1.md`](./v0.1.0-rc1.md): public pre-release notes, install steps,
  scientific status, and known limitations
- [`../release_readiness.md`](../release_readiness.md): what `draft_ready` means
  and what still blocks stable release
- [`../applicability_limits.md`](../applicability_limits.md): plain-language
  intended use, limitations, and safe-use checklist
- [`../reviews/v0.1.0-scientific-source-review.md`](../reviews/v0.1.0-scientific-source-review.md):
  independent-review history and remediation posture

## Machine-readable evidence

- `v0.1.0.release_metadata.json`: package counts, supported workflows, artifact
  hashes, and distribution hashes
- `v0.1.0.validation_dossier.json`: validation-suite results
- `v0.1.0.readiness_report.json`: automated gate status and known limitations
- `v0.1.0.downstream_dry_runs.json`: downstream contract dry runs
- `v0.1.0.security_provenance_review.json`: security and provenance posture

These reports are also exposed through `release://` resources and can be
regenerated from a source checkout or release package. Generated status such as
`draft_ready` describes automated readiness for review; it is not independent
scientific signoff or regulator acceptance.
