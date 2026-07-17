# ADR 0007: OpenFoodTox 3.0 Migration

Status: Proposed

Date: 2026-07-17

## Context

EFSA released OpenFoodTox 3.0 on 30 April 2026. It uses an IUCLID 6-aligned
workbook and contains data from EFSA outputs through December 2025. Dietary MCP
currently carries a smaller OpenFoodTox 2.0 version-6 snapshot published in
2023, with source coverage through September 2022.

The 3.0 workbook is not a drop-in replacement. Toxicological reference values
are represented across IUCLID-shaped tables and fields, with dossier, substance,
literature, population, qualifier, and unit relationships that must be joined
explicitly. A quick column mapping would create silent scientific errors.

## Decision

Keep the 2023 snapshot available only as a superseded, checksum-pinned,
review-required source. Migrate to OpenFoodTox 3.0 on a separate branch after
the stable v0.1.0 contract is frozen.

The migration must:

1. Pin DOI `10.5281/zenodo.19388272`, workbook checksum
   `md5:445fc05a6a421634df822d14131a7d83`, and acquisition metadata.
2. Join dossier, substance, reference-substance, literature, and
   `FLEX_SUM.ToxRefValues` records using documented UUID relationships.
3. Preserve lower/upper qualifiers, units, populations, assessment bodies,
   uncertainty factors, critical endpoints, dates, and persistent identifiers.
4. Never infer “current” from row order or the largest numeric value.
5. Preserve historical and population-specific records without flattening them
   into authority conflicts.
6. Compare every currently curated high-impact record against both 3.0 and its
   original EFSA scientific output.
7. Produce deterministic source-to-runtime provenance and a machine-readable
   reconciliation report for added, removed, changed, and ambiguous records.
8. Keep all migrated records `review_required`; no bulk record becomes
   submission-allowed automatically.

## Acceptance gates

- Workbook checksum and schema fingerprint pass.
- Every emitted record resolves to a source dossier and substance UUID.
- No qualifier, population, unit, or assessment date is lost.
- Duplicate and conflict classifications pass adversarial fixtures.
- Curated PFAS, BPA, cadmium, lead, arsenic, mercury, acrylamide, glyphosate,
  acetamiprid, and imidacloprid records receive human review.
- v1 tool contracts remain backward-compatible or changes are versioned.
- Full scientific validation and release verification pass without warnings.

## Consequences

The stable release remains honest about its source currency while retaining a
reproducible historical corpus. OpenFoodTox 3.0 gains the dedicated validation
work it warrants instead of being rushed into the release candidate.
