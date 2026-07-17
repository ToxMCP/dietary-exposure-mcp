# Public Release Process

Dietary Exposure MCP uses two distinct release decisions:

- a public GitHub release candidate for transparent engineering and scientific
  review
- a stable release after independent scientific signoff and completion of the
  declared source-reconciliation gates

The RC is a GitHub pre-release. The `0.1.0` wheel must not be uploaded to PyPI
as an RC because that version is reserved for the stable release.

## Automated Gates

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
metadata that will become public. Never rewrite or force-push shared history as
part of routine release automation.

## Repository Visibility Gate

Before changing visibility:

1. Review every issue, pull request, comment, release, and repository attachment
   for confidential information and local paths.
2. Resolve or explicitly accept historical personal email and workstation-path
   metadata.
3. Enable GitHub private vulnerability reporting.
4. Confirm the default branch, branch rules, Actions permissions, and repository
   secrets are suitable for a public repository.
5. Confirm `THIRD_PARTY_NOTICES.md`, `CITATION.cff`, `SECURITY.md`, and the RC
   release notes are current.

Changing repository visibility is a deliberate owner action, not part of a
build script.

## Publishing The RC

After the visibility gate:

1. Merge the reviewed RC branch to `main`.
2. Run `./scripts/verify_release.sh` from the merge commit.
3. Create an annotated tag named `v0.1.0-rc1`.
4. Create a GitHub pre-release from `docs/releases/v0.1.0-rc1.md`.
5. Attach the wheel, source distribution, `python-sbom.cdx.json`, and
   `SHA256SUMS` from `artifacts/releases/v0.1.0-rc1/`.
6. Verify the uploaded checksums against the local release directory.

Do not publish a public hosted HTTP endpoint as part of the RC. The supported
public evaluation path is local stdio operation.

## Stable Release Gates

Stable `v0.1.0` additionally requires:

- independent toxicologist or dietary-risk-assessor signoff
- OpenFoodTox 3.0 reconciliation under ADR 0007
- resolution of the WHO-derived profile redistribution posture for the intended
  release audience
- a final source-currency review and complete release-gate rerun
- a separate hosted-deployment security review if public HTTP is offered
