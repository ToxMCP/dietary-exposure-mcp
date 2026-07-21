# Public Release Process

Dietary Exposure MCP keeps two decisions separate:

- **software publication** decides whether a versioned package is technically
  reproducible, secure, documented, and suitable for its declared use
- **scientific promotion** decides whether review-gated records or evidence
  claims have received the qualified human approval required to move beyond
  screening and review use

`v0.1.0` is the first stable GitHub software release. It is an early `0.x`
baseline for screening and governed evidence handoff only. Stable software does
not mean scientific validation, regulator acceptance, or a safety conclusion.
The package is not published to PyPI as part of this release.

## Automated gates

Run the complete local release gate:

```bash
./scripts/verify_release.sh
```

Run the public-tree audit and the separate history audit:

```bash
uv run python scripts/public_release_audit.py
uv run python scripts/public_release_audit.py --history
```

The current-tree audit must pass. The history audit must either pass after a
coordinated rewrite or have an explicit owner decision accepting the exact
metadata already public. Never rewrite or force-push shared history as part of
routine release automation.

## Software release gate

Before publishing `v0.1.0`:

1. Confirm all automated scientific-invariant, contract, packaging, security,
   and reproducibility gates pass from the final merge commit.
2. Confirm README and release notes describe the software as screening only.
3. Confirm all 2,417 OpenFoodTox bulk records remain `review_required` and the
   pending high-impact signoff is visible.
4. Confirm no text implies legal, clinical, safety, market-access, or regulator
   approval.
5. Confirm `THIRD_PARTY_NOTICES.md`, `CITATION.cff`, `SECURITY.md`, limitations,
   and source-currency warnings are current.
6. Confirm repository visibility, branch rules, Actions permissions, private
   vulnerability reporting, and release attachments are appropriate.

## Publishing v0.1.0

1. Merge the reviewed release branch to `main`.
2. Run `./scripts/verify_release.sh` from the merge commit.
3. Create an annotated tag named `v0.1.0`.
4. Create a normal GitHub release from `docs/releases/v0.1.0.md`.
5. Attach the wheel, source distribution, `python-sbom.cdx.json`, and
   `SHA256SUMS` from `artifacts/releases/v0.1.0/`.
6. Download the public assets into a clean directory and verify them against
   the published `SHA256SUMS` file.

Do not publish a hosted HTTP endpoint as part of this release. The supported
path is local stdio operation. A hosted or multi-user deployment requires a
separate security review and authenticated gateway.

## Scientific promotion gate

The following remain required before promoting affected OpenFoodTox records or
making a stronger scientific-validation claim:

- positive independent toxicologist or dietary-risk-assessor signoff on the
  remediated OpenFoodTox 3.0 version 1.2 report and its canonical hash
- qualified human approval under ADR 0007
- current primary-source confirmation for decision-relevant values
- resolution of source conflicts, applicability questions, and review flags

Until those steps are complete, records and outputs keep their screening and
`review_required` semantics even though the software version is `v0.1.0`.

Third-party redistribution rights are a separate obligation. Publishing the
software does not grant permission to redistribute scientific source material
beyond its original terms.
