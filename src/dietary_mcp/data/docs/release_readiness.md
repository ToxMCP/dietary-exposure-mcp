# Release Readiness

## Current status

`v0.1.0-rc1` is ready for publication as a GitHub pre-release. The generated
`v0.1.0` dossier has `draft_ready` status, which means the automated scientific,
contract, packaging, and security evidence is internally consistent and ready
for human review. It does not mean scientific approval, regulator acceptance,
or stable-release approval.

The engineering gates pass. The remaining stable-release blocker is positive
independent signoff on the remediated OpenFoodTox 3.0 high-impact report:

- 2,417 bulk records remain `review_required`
- 16 high-impact records are included in review version `1.2`
- canonical content SHA-256:
  `0feb8e3e4f9852c2d102375dd89d814ed08407a602d699882cf48bdd7f3c8c90`
- the first independent review returned `not approved`; its blockers were
  remediated, but that earlier disposition is not release approval

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

Stable `v0.1.0` additionally requires resolution of third-party data terms for
the intended distribution and a complete final source-currency review. See the
[limitations and safe-use guide](./applicability_limits.md) and
[public release process](./public_release.md).
