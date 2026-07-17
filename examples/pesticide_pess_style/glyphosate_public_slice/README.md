# Glyphosate Public-Source Dietary Slice

This example is a PESS-style dietary case pack for Dietary Exposure MCP. It is intentionally small: it demonstrates the governed evidence workflow without claiming to reproduce EFSA raw monitoring rows, EFSA PRIMo, DEEM, or the full PESS paper.

## What It Shows

- Glyphosate food-mediated oral intake for a public-source regulatory-style screening demonstration.
- Apple juice as a processed apple derivative with an explicit raw-residue-to-processed-food processing factor.
- Rice as a second commodity with separate residue and trade-risk handling.
- Adult chronic deterministic intake.
- Child acute bounded intake for sensitive-population framing.
- Raw-survey distribution and cohort-bootstrap support.
- Three-bound censored-residue uncertainty handling.
- Cross-jurisdiction trade-risk statuses.
- PBPK-ready oral dose handoff.

## Source Position

The source lock cites public official sources for the workflow context:

- EFSA food consumption infrastructure.
- EFSA chemical monitoring and pesticide-residue annual-report context.
- EU Pesticides Database and MRL legislation context.
- EFSA OpenFoodTox reference-value infrastructure.
- EFSA glyphosate topic page.
- The PESS PDF supplied for comparison.

The residue values in this pack are deliberately labeled as regulatory-screening inputs. They are not row-level EFSA residue measurements and must not be presented as an EFSA/PESS reproduction.

For apple juice, the residue value is intentionally treated as a raw-primary-commodity apple residue assumption that is translated to apple-juice consumption with the governed processing factor. It is not a measured apple-juice residue. If a future case uses measured apple-juice residues directly, the processing factor should be 1.0 for that lane.

The apple-juice consumption lane is also an explicit proxy: the public slice uses the governed apples consumption amount as a compact processed-derivative fixture. It is not a row-level EFSA apple-juice survey estimate.

## Files

- `source_lock.json`: public source anchors and non-claim boundaries.
- `inputs/residue_profile_request.json`: residue profile request using public Dietary MCP contracts.
- `inputs/adult_raw_survey_request.json`: small governed survey dataset request.
- `inputs/probabilistic_request_overlay.json`: cohort-bootstrap settings.
- `inputs/uncertainty_request_overlay.json`: uncertainty and censored-residue settings.
- `outputs/output_summary.json`: stable numeric checkpoints, dual-unit conversions, and review posture.
- `outputs/pbpk_oral_handoff.json`: compact PBPK-ready child acute oral handoff object.
- Complete output bundles also include generated runtime artifacts named `00_output_summary.generated.json` through `15_toxclaw_dietary_evidence_bundle.json`, a reviewer-facing `16_toxclaw_evidence_index.json` supplement, plus `meta/manifest.json`, `meta/reviewer_patch_notes.json`, and `meta/SHA256SUMS.txt`.
- `limitations.md`: reviewer-facing limitations and backlog.

## How To Rebuild

Use the checked-in inputs with the current `DietaryRuntime`:

1. Build the residue profile from `inputs/residue_profile_request.json`.
2. Select `adult_general` chronic and `child_1_6` acute profiles for `apple_juice` and `rice`.
3. Build the adult `point_estimate` scenario and child `bounded_acute` scenario.
4. Parse `inputs/adult_raw_survey_request.json`.
5. Run survey summary, probabilistic summary, uncertainty assessment, trade-risk evaluation, PBPK export, and ToxClaw evidence export.

The repository regression test `tests/test_pess_glyphosate_case_pack.py` performs this rebuild and compares the main values against `outputs/output_summary.json`. Output-only zip bundles may not include the test file itself.
