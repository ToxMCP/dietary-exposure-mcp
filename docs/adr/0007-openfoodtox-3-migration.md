# ADR 0007: OpenFoodTox 3.0 Migration

Status: Implemented; high-impact scientific signoff pending

Date: 2026-07-17

Implementation plan: [`../reviews/openfoodtox-3-migration-plan.md`](../reviews/openfoodtox-3-migration-plan.md)

## Context

EFSA released OpenFoodTox 3.0 on 30 April 2026. It uses an IUCLID 6-aligned
workbook and contains data from EFSA outputs through December 2025. Before this
decision was implemented, Dietary MCP carried a smaller OpenFoodTox 2.0
version-6 snapshot published in 2023, with source coverage through September
2022.

The 3.0 workbook is not a drop-in replacement. Toxicological reference values
are represented across IUCLID-shaped tables and fields, with dossier, substance,
literature, population, qualifier, and unit relationships that must be joined
explicitly. A quick column mapping would create silent scientific errors.

## Decision

Keep the 2023 snapshot represented as a superseded source-catalog entry and use
it only as a checksum-pinned reconciliation baseline. Replace the runtime bulk
pack with OpenFoodTox 3.0 while preserving the stable v1 contract.

The migration must:

1. Pin DOI `10.5281/zenodo.19388272`, workbook checksum
   `md5:445fc05a6a421634df822d14131a7d83`, and acquisition metadata.
2. Join dossier, substance, reference-substance, literature,
   `FLEX_SUM.ToxRefValues`, and `END_STUDY_REC.HumanHealth` records using
   documented UUID relationships.
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
- Full technical validation and release verification pass.
- High-impact discrepancies are accepted or corrected by a qualified human
  reviewer against the original scientific outputs.

## Consequences

The runtime bulk pack now contains 2,417 deterministic OpenFoodTox 3.0 records.
All are `review_required`, carry UUID-based provenance, and preserve source
bounds and one-to-many dossier context. Another 317 candidates are held because
of curated-record precedence or unresolved source context. The old 2.0 source
remains visible as superseded but is no longer used by runtime bulk records.

The machine review now resolves dataset support for all 16 high-impact curated
records, including five benchmark-dose records stored in the HumanHealth sheet.
It separates support from temporal currency, preserves the superseded 2015
glyphosate ARfD, and represents the imidacloprid 0.06 mg/kg bw recommendation
in parallel with the 0.08 mg/kg bw context retained in EFSA's 2019 MRL review.
It also distinguishes authoritative acute-unit corrections from exact workbook
matches and identifies the 2024 acetamiprid values as an EFSA scientific
proposal rather than attributing them to the later EU MRL measure. One current
glyphosate record remains explicitly flagged for anomalous upper-field
encoding. The first independent review was not approved; its blockers are
remediated, but positive signoff of the revised hash remains open.
