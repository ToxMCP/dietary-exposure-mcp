# Scientific Hardening Tracker

This tracker converts the integrated scientific review into concrete remediation work with one disposition, one implementation task, one owner lane, one phase, and one acceptance check per item.

## Baseline lock

- Baseline scenarios frozen for regression: raw deterministic intake, processed deterministic intake, processed survey summary, probabilistic summary, contaminant signoff, metals signoff, PFAS monitoring interpretation, and trade risk across `eu`, `us`, and `cn`.
- Deep-review bundle profile `scientific_deep_review_v1` now prioritizes `composition_recipes`, `food_vocabulary_crosswalk`, `core_defaults`, `source_catalog`, `substance_synonyms`, and `tests/test_runtime.py` in addition to the scientific runtime and validation modules.

## Adjudication matrix

| ID | Review finding | Disposition | Implementation task | Owner | Phase | Acceptance evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `R1` | Survey and probabilistic exposure paths ignored processing factors | `confirmed` | Centralize adjusted-residue arithmetic and apply it to survey and probabilistic workflows | `runtime` | `1` | `tests/test_runtime.py` processed-food survey and probabilistic regressions | `implemented` |
| `R2` | Probabilistic workflow used pseudo-bootstrap instead of cohort bootstrap | `confirmed` | Replace single-draw loop with cohort resampling and shared percentile summaries | `runtime` | `1` | `tests/test_runtime.py` bootstrap consistency coverage | `implemented` |
| `R3` | Trade risk returned vacuous `pass` when no applicable limit existed | `confirmed` | Return explicit non-pass states and quality flags for missing limits or invalid chemical identity | `runtime` | `1` | `tests/test_runtime.py` trade-risk invalid/no-limit assertions | `implemented` |
| `R4` | Recipe validation accepted invalid proportions and incomplete totals | `confirmed` | Enforce finite `0..1` proportions, recipe total `== 1.0`, and fix seeded recipes | `defaults` | `1` | `tests/test_defaults.py` plus manifest regeneration | `implemented` |
| `R5` | PFAS occurrence linkage was empty so food-context review stayed thin | `confirmed` | Populate PFAS occurrence support records and review-focus linkage for eggs, fish, and offal | `defaults` | `3` | `tests/test_runtime.py` PFAS linkage assertions | `implemented` |
| `R6` | Missing occurrence evidence only warned instead of blocking review closure | `confirmed` | Promote missing occurrence evidence to blocking status in checks, signoff, and dossier export | `governance` | `2` | signoff/dossier validation suites and `tests/test_release_artifacts.py` | `implemented` |
| `R7` | `broad_food_supply` matched unconditionally and masked weak matrix specificity | `confirmed` | Replace unconditional matching with explicit fallback warnings | `defaults` | `3` | `tests/test_runtime.py` fallback warning coverage | `implemented` |
| `R8` | Survey ingestion silently dropped too much data and hid subject body-weight conflicts | `confirmed` | Add dropped-row counts, loss fraction, unmapped codes, and body-weight conflict quality flags | `runtime` | `1` | `tests/test_runtime.py` survey-ingestion data-loss coverage | `implemented` |
| `R9` | Readiness could be mistaken for scientific sufficiency | `confirmed but overstated` | Add `scientific_integrity_verified`, jurisdiction consistency, and deprecated-state blocking rules while preserving governance scope | `readiness` | `2` | `tests/test_readiness_validation.py` and release-artifact validation | `implemented` |
| `R10` | Signoff semantics could be mistaken for scientific correctness or regulator acceptance | `confirmed but overstated` | Block closure on unresolved scientific errors, require evidence URIs for closed blocking actions, and rewrite operator/docs language | `governance` | `2` | signoff validation suites, review-dossier validation, docs updates | `implemented` |
| `R11` | Deterministic kernel was described as broadly broken on processing factors | `confirmed but overstated` | Preserve deterministic reference arithmetic, fix only the `0.0` bound bug, and document the narrower failure scope | `runtime` | `1` | `tests/test_runtime.py` and `plugins/reference_intake.py` regression | `implemented` |
| `R12` | Method and contaminant registry maturity was overstated for PFAS and historical metals coverage | `confirmed` | Downgrade PFAS evidence maturity where appropriate, add structured method metadata fields, and keep historical currency explicit | `defaults` | `3` | `tests/test_defaults.py`, updated defaults payloads, release artifacts | `implemented` |

## Remaining operating rules

- `readiness`, `signoff`, and `submission_candidate` remain governed review states, not claims of automatic regulatory acceptance.
- Closed contaminant or metals dossiers cannot be exported when core scientific blockers remain unresolved.
- Broad matrix fallbacks and historical-data posture must remain machine-visible in outputs, not hidden in prose.
