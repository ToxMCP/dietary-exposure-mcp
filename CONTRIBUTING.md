# Contributing

Dietary Exposure MCP welcomes engineering review, scientific corrections, and
source-quality improvements. Every change should be suitable for audit through
the generated release artifacts.

Use the issue forms for reproducible software defects or scientific concerns.
Never attach confidential submissions, personal data, credentials, or
unpublished dossier material to a public issue.

## Working rules

- Preserve the published scope boundary: Dietary MCP is a food-mediated oral exposure support module, not a direct-use oral product engine and not a final regulatory decision engine.
- Prefer additive governed records over silent replacement when extending defaults, source databases, or validation packs.
- Preserve authority conflicts instead of flattening them.
- Use official or primary public sources for regulatory, methodological, and toxicological records.
- Keep review-only sources clearly marked as `review_required` or `not_allowed` where appropriate.
- Do not widen submission claims without updating readiness profiles, rules, and operator docs in the same change.

## Change workflow

1. Update code, governed defaults, validation packs, and docs together.
2. Regenerate packaged mirrors and public artifacts:

```bash
uv run dietary-mcp-generate-artifacts
uv run python -m dietary_mcp.release_artifacts
```

3. Run local quality gates:

```bash
./scripts/verify_release.sh
```

4. Review the generated outputs under `docs/releases/` before proposing a release.

## When adding scientific content

- Add the source to `defaults/v1/source_catalog.json`.
- Add governed records to the relevant registry rather than inventing ad hoc runtime logic.
- Add at least one executable validation case.
- State whether the source is redistributed, adapted, or linked only, and update `THIRD_PARTY_NOTICES.md` when required.
- Update the operator-facing docs if the new content changes scope, posture, or supported families.

## When changing contracts

- Regenerate schemas and examples.
- Keep request/result changes additive unless there is an explicit version bump.
- Check that packaged wheel parity is preserved through the artifact-generation path.

## Pull request expectations

- Explain the regulatory or scientific reason for the change.
- State whether the change affects scope, readiness posture, or only evidence depth.
- Link primary sources and identify any unresolved authority, unit, population, or currency conflict.
- Cite the updated generated counts from `docs/releases/` when the change materially expands registries or workflows.
- Confirm that `./scripts/verify_release.sh` passes and that generated artifacts are committed.
