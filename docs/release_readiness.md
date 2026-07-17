# Release Readiness

The generated `v0.1.0` dossier currently has `draft_ready` status. That means
the automated scientific, contract, packaging, and security evidence is ready
for review; it does not mean final regulatory or public-stable approval.

The automated release gate requires:

1. acute vs chronic semantics are explicit in contracts and examples
2. schemas and examples validate
3. benchmark cases pass within declared tolerances
4. defaults, taxonomy, and profile versions are published
5. contributor outputs and assumption ledgers are auditable
6. PBPK export objects validate directly
7. limitation notes prevent misuse as a final regulatory decision

A public release candidate additionally requires the current-tree privacy
audit, attribution and citation files, security reporting, reviewed release
notes, and a deliberate repository-visibility decision.

Stable `v0.1.0` additionally requires independent scientific signoff,
OpenFoodTox 3.0 reconciliation under ADR 0007, and resolution of third-party
data terms for the intended distribution. See
[`docs/public_release.md`](./public_release.md).
