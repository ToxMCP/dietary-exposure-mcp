# Release Readiness

## Current status

`v0.1.0` is ready for publication as the first stable GitHub software release.
It is an early `0.x` release for screening and governed evidence handoff only.
"Stable" describes the packaged software version and release channel; it does
not mean that every scientific record is curated, independently approved, or
accepted by a regulator.

The generated scientific-review dossier remains `draft_ready`. That status
means the automated scientific, contract, packaging, and security evidence is
internally consistent and ready for qualified human review. It is intentionally
independent from the decision to publish screening software.

The engineering release gates pass. Scientific promotion remains open:

- 2,417 bulk records remain `review_required`
- 16 high-impact records are included in review version `1.2`
- canonical content SHA-256:
  `0feb8e3e4f9852c2d102375dd89d814ed08407a602d699882cf48bdd7f3c8c90`
- the first independent review returned `not approved`; its blockers were
  remediated, but positive independent signoff has not yet been recorded
- the project owner accepted all 16 high-impact records for governed screening
  on 2026-07-22; the [owner attestation](./reviews/openfoodtox-3-owner-attestation-2026-07-22.md)
  discloses direct project involvement and does not close the independent gate

Until that signoff exists, affected records must remain screening and review
material. They must not be relabelled as curated, regulator-approved, or fit for
an unsupported final decision.

The automated release gate requires:

1. acute vs chronic semantics are explicit in contracts and examples
2. schemas and examples validate
3. benchmark cases pass within declared tolerances
4. defaults, taxonomy, and profile versions are published
5. contributor outputs and assumption ledgers are auditable
6. PBPK export objects validate directly
7. limitation notes prevent misuse as a final regulatory decision

The public `v0.1.0` software release additionally requires the current-tree
privacy audit, attribution and citation files, security reporting, reviewed
release notes, a clean complete verifier run, and explicit screening-only
language on the release surface.

Positive independent signoff is required before scientific promotion of the
OpenFoodTox high-impact report or any stronger validation claim. Third-party
redistribution terms and current primary-source checks still apply to every
downstream use. See the [limitations and safe-use guide](./applicability_limits.md)
and [public release process](./public_release.md).
