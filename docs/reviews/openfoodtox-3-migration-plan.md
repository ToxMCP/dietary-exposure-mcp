# OpenFoodTox 3.0 migration plan

Status: independent review remediated; revised human scientific signoff required

Owner attestation update: Ivo Djidrovski, PhD accepted the exact version 1.2
high-impact object for governed screening on 2026-07-22. The
[attestation](./openfoodtox-3-owner-attestation-2026-07-22.md) discloses direct
project involvement, so the independent scientific promotion gate remains
open.

## Objective

Replace the superseded 2023 OpenFoodTox 2.0 bulk snapshot with a deterministic,
review-required OpenFoodTox 3.0 candidate without changing the Dietary MCP v1
tool contract or silently selecting preferred toxicological values.

The official source is EFSA's OpenFoodTox 3.0 version v7, Zenodo DOI
`10.5281/zenodo.19388272`, published on 30 April 2026. The migration uses the
22,595,502-byte `OFT3.0 export repository.xlsx` file pinned by MD5
`445fc05a6a421634df822d14131a7d83`. Raw source files remain under ignored
`tmp/` storage and are not committed.

## Migration stages

1. Freeze the source identity, workbook schema, and UUID-join integrity.
2. Build a lossless intermediate representation for reference-value rows and
   their substance, reference-substance, dossier, and literature context.
3. Reconcile every 2023 runtime record against 3.0 as unchanged, changed,
   removed, added, duplicate, or ambiguous.
4. Validate qualifiers, units, populations, assessment bodies, dates,
   uncertainty factors, critical endpoints, and persistent identifiers.
5. Review PFAS, BPA, cadmium, lead, arsenic, mercury, acrylamide, glyphosate,
   acetamiprid, and imidacloprid against original EFSA scientific outputs.
6. Generate candidate defaults with `submissionUse=review_required` and retain
   curated original-output records when bulk evidence is ambiguous.
7. Switch only the bulk layer, regenerate packaged assets, and run the full
   scientific and release verifier.

## Non-negotiable rules

- Never infer a current value from row order, a larger value, or a newer date.
- Preserve one-to-many dossier links and historical or population-specific
  records instead of flattening them into a single authority value.
- A missing or ambiguous UUID join is a review item, not an invitation to infer.
- A discrepancy with OpenFoodTox must be resolved against the original EFSA
  scientific output, which remains authoritative for regulatory reuse.
- O-QT-derived results are corroborating evidence, not a replacement for the
  checksum-pinned EFSA export.

## O-QT and IUCLID boundary

The local O-QT MCP 0.2.0 bridge passes strict readiness against OECD QSAR
Toolbox 4.8.2 and WebAPI v6. Its live `get_iuclid_section_tree` route works.
The two IUCLID tools are currently omitted from the O-QT RBAC allowlist even
though they register successfully; a session-only permission override was used
to test them without modifying the dirty O-QT checkout.

Live IUCLID searches for Acetamiprid and benzene returned successful empty
results. The Toolbox separately lists `Open Food Tox Hazard EFSA` among its
search databases, but that database is not currently exposed as source-native
records by the IUCLID search route. The official OpenFoodTox 3.0 workbook is
therefore the primary migration source. O-QT remains useful for independent
chemical identity, endpoint-tree, metabolism, profiler, and mechanistic checks.

## Initial workbook findings

- 18 sheets are present, including 7,880 substance rows, 7,890 reference
  substance rows, and 19,747 `FLEX_SUM.ToxRefValues` rows.
- All non-null substance-to-reference-substance, toxicological-value-to-
  substance, dossier-document-to-dossier, and opinion-to-literature UUID joins
  resolve.
- Fifteen toxicological-reference documents have no `DOSSIER_DOCS` link and
  must remain ambiguous until reviewed.
- Four toxicological-reference document UUIDs occur more than once.
- 382 toxicological-reference documents link to multiple dossiers. These links
  must be preserved because they can represent genuine shared assessments.
- Acetamiprid alone has five toxicological-reference rows spanning the 2013,
  2016, 2021, 2022, and 2024 EFSA context. This demonstrates why row-level
  currency selection would be scientifically unsafe.

The deterministic source inventory is generated with
`scripts/openfoodtox3_inventory.py` and recorded in
`docs/reviews/openfoodtox-3-source-inventory.json`.

The lossless intermediate representation is generated under ignored `tmp/`
storage with `scripts/openfoodtox3_extract.py`. It covers both
`FLEX_SUM.ToxRefValues` and all 38,808 rows in `END_STUDY_REC.HumanHealth`,
including exact source fields, units, qualifiers, document UUIDs, dossier
relationships, and literature references. Its compact, tracked evidence is
recorded in `docs/reviews/openfoodtox-3-extraction-summary.json`; no candidate
runtime reference values are emitted by this stage.

The old-to-new comparison is generated with
`scripts/openfoodtox3_reconcile.py`. It first resolves exact or canonical names,
then checksum-pinned OpenFoodTox 2.0 CAS relationships, and finally requires an
exact reference type, numeric value, unit, qualifier, population, and assessment
year. A failed stage is reported as changed-or-missing; it is never silently
coerced into a match. The compact result is recorded in
`docs/reviews/openfoodtox-3-reconciliation-summary.json`.

## First conservative reconciliation baseline

The first complete pass reconciles all 2,274 records in the superseded runtime
snapshot and reports:

- 1,121 unique exact context matches;
- 145 multiple exact candidates that must not be deduplicated automatically;
- 144 ambiguous substance identities and 95 unresolved identities;
- 193 records with no candidate for the legacy reference-value type;
- 21 changed-or-missing values and 19 changed-or-missing units;
- 302 changed-or-missing populations; and
- 234 changed-or-missing assessment years.

These are triage classifications, not scientific conclusions. In particular,
`changed_or_missing_*` means that the exact staged comparison failed at that
field after all preceding fields matched. It does not claim that EFSA withdrew
or changed a value until the linked scientific output is reviewed.

## Implemented candidate and runtime layer

`scripts/openfoodtox3_candidates.py` applies an explicit human dietary
allowlist to the lossless intermediate representation. It emits ADI, ARfD, AI,
average requirement, PRI, TDI, TWI, UL, MTDI, RfD, and safe-maximum-intake
descriptors only when a positive numeric value, unit, named human population,
source dossier, and resolvable assessment authority are present. Operator,
worker, animal, ecological, TTC, MOE, margin-of-safety, incomplete-data, and
unnamed external-authority values cannot enter runtime defaults.

The deterministic pass found 2,734 value-bearing dietary candidates:

- 2,417 are emitted as current-dataset, `review_required` runtime records;
- 317 are held, including 272 with unresolved assessment authority, 49 covered
  by curated-record precedence, 13 with missing dossier links, two with missing
  populations, and two with non-human populations;
- all 622 AOEL and 194 AAOEL section records are excluded from dietary lookup;
- every emitted lower or upper bound has its own stable record ID and a
  one-to-one UUID provenance entry; and
- multi-dossier values retain every dossier link and receive no assessment year
  when the linked years disagree.

The compact machine evidence is recorded in
`openfoodtox-3-candidate-summary.json`, while full row decisions remain in
ignored `tmp/` storage. Runtime data now use `efsa.openfoodtox`; the superseded
`efsa.openfoodtox.2023_snapshot` remains only as historical source metadata and
reconciliation evidence.

## High-impact review gate

`openfoodtox-3-high-impact-review.json` compares the curated EFSA records with
matching records from both workbook layers before curated-precedence
exclusions. The version 1.2 review contains 16 complete records, validates
against `openfoodtox-3-high-impact-review.schema.json`, and carries a canonical
content hash. Its two independent axes distinguish dataset support from
temporal currency. The additional record is the 0.08 mg/kg bw imidacloprid ARfD
context retained in EFSA's 2019 MRL consumer risk assessment; it became a
separately reviewable current-context record after the independent review found
that it had been incorrectly treated as unconditionally superseded.

The review now reports:

- six exact structured matches, two exact unstructured matches, four matches
  after explicit unit normalization, three matches after authoritative
  primary-source unit correction, and one match whose source uses an anomalous
  upper-bound field encoding;
- exact HumanHealth support for the acrylamide BMDL10 values of 0.17 and
  0.43 mg/kg bw/day, inorganic-arsenic BMDL05 of 0.06 micrograms/kg bw/day,
  and lead BMDL01 values of 0.5 and 0.63 micrograms/kg bw/day;
- a current 2023 glyphosate ARfD of 1.5 mg/kg bw, with 0.5 mg/kg bw retained as
  the superseded 2015 value;
- acetamiprid ADI 0.005 mg/kg bw/day and ARfD 0.005 mg/kg bw identified as
  introduced by the 2024 EFSA scientific statement, with raw OpenFoodTox acute
  units retained separately and Regulation (EU) 2025/158 represented only as
  follow-up MRL risk-management context; and
- a 2013 imidacloprid ARfD recommendation of 0.06 mg/kg bw represented in
  parallel with the 0.08 mg/kg bw value retained in EFSA's 2019 MRL assessment.
  Neither assertion is represented as unconditionally superseding the other.

The verifier resolves every non-null provenance field path against the pinned
workbook header inventory and, when the source workbook is present, checks that
inventory directly against the checksum-pinned XLSX. All 564 lower-bound ARfD
records now carry a null qualifier path because the claimed
`Arfd.lowerQualifier` workbook column does not exist.

No high-impact record is left with an unresolved dataset-support status. The
first independent review nevertheless returned `not approved` and identified
the four blockers remediated above. See
`openfoodtox-3-independent-review-remediation.md`. The corrected report has a
new canonical hash and remains `review_required` until a qualified toxicologist
positively signs off the revised values, temporal interpretations, and
original-source readings.

The project owner's positive attestation is retained as review evidence, but
it cannot provide the independence required by this gate.
