# OpenFoodTox 3.0 independent review remediation

Review date: 2026-07-21

Original disposition: **Not approved; blocking scientific issues remain**

Remediation status: implementation complete; revised independent signoff pending

Owner attestation status: all 16 records and required conclusions were accepted
for governed screening by Ivo Djidrovski, PhD on 2026-07-22. The
[attestation](./openfoodtox-3-owner-attestation-2026-07-22.md) was made in a
disclosed project owner/maintainer capacity and does not satisfy the independent
signoff requirement.

## Review result preserved

The independent toxicologist accepted 12 of the 15 version 1.1 curated records,
marked three records `correction_required`, and confirmed that all 2,417 bulk
records must remain `review_required`. File integrity, workbook checksums,
JSON-schema validation, and canonical-content hashing passed. The prior review
is evidence of review activity, but its `not approved` disposition is not a
release approval.

## Blocking findings and corrections

| Finding | Remediation |
| --- | --- |
| Acetamiprid ARfD was represented as 0.005 mg/kg bw/day | The canonical ARfD is now 0.005 mg/kg bw. The raw OpenFoodTox unit remains in source provenance, and the candidate is classified as `primary_source_unit_correction` against the [2024 EFSA statement](https://www.efsa.europa.eu/en/efsajournal/pub/8759). |
| Imidacloprid 0.08 mg/kg bw was represented as unconditionally superseded by 0.06 | The 2013 value is explicitly a recommendation of 0.06 mg/kg bw. The 0.08 mg/kg bw value is retained as a parallel context used in EFSA's [2019 MRL review](https://www.efsa.europa.eu/en/efsajournal/pub/5570). Both records share a conflict group, remain review-required, and carry no false supersession edge. |
| Glyphosate ARfD was labelled `exact_match` despite a daily raw unit | The canonical 1.5 mg/kg bw value remains unchanged. Its raw mg/kg bw/day workbook encoding and upper-field anomaly remain visible, while the normalized unit is corrected against the [2023 EFSA peer review](https://www.efsa.europa.eu/en/efsajournal/pub/8164). |
| 564 lower-bound ARfD records cited a nonexistent `Arfd.lowerQualifier` column | All 564 paths are now null. The migration verifier requires every non-null value, unit, qualifier, and descriptor path to resolve to the pinned workbook header inventory and directly rechecks the inventory when the checksum-pinned XLSX is available. |

## Pre-signoff bulk quality audit

A final canonical-text audit on 22 July 2026 found source-workbook mojibake in
10 microgram unit labels and 40 age-range population remarks. The runtime layer
now repairs those labels for display and matching (`Âµg` to `µg`, malformed
dashes to an en dash, and malformed comparison symbols to `≥` or `≤`). Exact
workbook strings remain separately preserved as `rawUnit` or
`rawPopulationRemarks` provenance.

No numeric value, record identity, assessment context, or high-impact record
changed. The version 1.2 canonical high-impact hash therefore remains stable.
The migration verifier now rejects unresolved mojibake in canonical runtime or
normalized provenance fields; raw source fields are exempt because preserving
them is intentional.

## Revised review object

- Review version: `1.2`
- Schema version: `1.2`
- Record count: `16`
- Canonical content SHA-256: `0feb8e3e4f9852c2d102375dd89d814ed08407a602d699882cf48bdd7f3c8c90`
- Release gate: `human_toxicologist_review_required`

The record count is now 16 because the retained 0.08 mg/kg bw imidacloprid MRL
assessment context is no longer hidden as a superseded record. It is separately
reviewable in addition to the 0.06 mg/kg bw recommendation.

## Signoff requirement

The 12 prior accept decisions may be used as review history, but they do not
approve the revised canonical object. A qualified independent reviewer must
confirm the three corrected records, the newly explicit imidacloprid context,
the resolved field-path control, and the exact version 1.2 content hash before
the stable release gate can close.

The later owner attestation accepts all 16 revised records for governed
screening and is also retained as review history. Because the attestor is
directly involved in the project, it does not alter the independent gate.
