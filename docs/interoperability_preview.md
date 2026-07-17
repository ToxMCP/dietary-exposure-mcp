# Interoperability Preview

Dietary MCP publishes a staged interoperability preview for review and mapping validation. This feature does not generate OECD Harmonised Template XML, IUCLID XML, or a submission-ready dossier.

## Surface

- tool: `dietary_export_interoperability_preview`
- tool: `dietary_assess_interoperability_preview_readiness`
- manifest resource: `interoperability://manifest`
- profile resource: `interoperability://profile/{profile_id}`
- validation resource: `validation://interoperability-profiles`
- documentation resource: `docs://interoperability-preview`

## Current profile

Phase 4 currently publishes one governed preview profile:

- `oht_85_iuclid_json_preview`

That profile projects selected fields from a `VersionPinnedAdapterReviewDossier` into a validation-only JSON structure aligned to:

- OECD OHT `85-1`
- OECD OHT `85-8`
- OECD OHT `85-10`

## Output semantics

The preview result includes:

- `targetDocument`: the staged JSON projection
- `mappedFields`: every governed field mapping and whether a value was present
- `missingRequiredFields`: required source paths that were not available in the dossier
- `unsupportedFields`: local MCP fields that are intentionally outside the current staged profile

Preview status is computed conservatively:

- `pass`: all required mapped fields are present and every applied mapping is `direct`
- `review_required`: required fields are present, but derived mappings or unsupported local fields remain
- `fail`: one or more required mapped fields are missing

## Current boundary

This preview is intentionally limited:

- no XML serialization
- no claim of IUCLID schema conformance
- no claim of OECD OHT dossier completeness
- no submission-readiness claim

Unsupported fields are surfaced explicitly so downstream teams can review what remains MCP-internal before any future interoperability work.

When a team needs an explicit exchange gate on top of the staged preview, use `dietary_assess_interoperability_preview_readiness` with one of the governed interoperability-readiness profiles.
