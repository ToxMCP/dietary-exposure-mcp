# ADR 0005 — Track-B scientific-invariants gate (vendored schema-spine engine)

Status: Accepted
Date: 2026-06-25
Supersedes: none (additive governance layer; complements ADR 0001 dietary boundary,
ADR 0004 provenance/quality governance, and the Track-A gates)

## Context

dietary-exposure-mcp emits a number of RELEASED objects. Some are FAITHFUL RELAYS
of curated / looked-up data; others are SERVER-AUTHORED CONCLUSIONS — the server
computes an interpretive qualification (an external oral-dose intake estimate, a
monitoring-submission-use verdict, a reviewer signoff status, an adapter-parity
review status). The cross-fleet ToxMCP schema-spine policy engine
(`ToxMCP/toxmcp-schema-spine`) encodes the anti-overclaim / review / uncertainty
invariants every server-authored conclusion must respect: a dietary or contaminant
exposure interpretation is **review context, never a risk or regulatory
conclusion** (ADR 0001 — the dietary boundary — restated machine-checkably).

This ADR adds a **Track-B scientific-invariants gate**: it projects each
server-authored interpretive surface onto its canonical spine shape and runs the
digest-pinned spine policy engine over the projection, blocking on any
public-release-blocking code. The repo already enforces these natively (it is
deterministic and zero-LLM), so the gate is a **regression tripwire** — GREEN on
the pristine corpus, RED if a future change lets an overclaim / unbounded-readiness
/ missing-uncertainty regression into a released object.

## Exhaustive candidacy sweep (every released object classified)

| Released object | Classification | Gated? | Spine shape |
|---|---|---|---|
| **dietaryIntakeSummary** (embeds dietaryContributionRecord[], dietaryAssumptionRecord[]) | SERVER-AUTHORED — computes an external oral-dose intake estimate + applied assumptions | **YES** | RouteDoseEstimate.v1 |
| **contaminantMonitoringInterpretationBundle** | SERVER-AUTHORED — authors checkStatus / overallSubmissionUse / submissionCandidateAllowed | **YES** | ToxMcpObject.v1 |
| **contaminantMonitoringSignoffPacket** | SERVER-AUTHORED — authors a reviewer signoff status (the review arm) | **YES** | ToxMcpObject.v1 (+ nested ReviewState) |
| **adapterReviewBundle** | SERVER-AUTHORED — authors a review_status parity verdict | **YES** | ToxMcpObject.v1 |
| **metalsMonitoringInterpretationBundle** | SERVER-AUTHORED — authors submission-use + a review narrative for a metals family | **YES (BC-6)** | ToxMcpObject.v1 |
| **metalsMonitoringSignoffPacket** | SERVER-AUTHORED reviewer signoff (the **proven laundering channel**: could emit `overallSignoffStatus=SIGNED_OFF` while `unresolvedBlockingActionIds` is non-empty + append an unchecked `packet_note`) | **YES (BC-6)** | ToxMcpObject.v1 (+ nested ReviewState) |
| **tradeRiskReviewBundle** (embeds GlobalTradeRiskReport) | SERVER-AUTHORED — authors a trade `review_status` + review narrative; the embedded report's EVERY narrative leaf (notes[], qualityFlags[].message, each jurisdiction_profiles[].notes[], jurisdiction_profiles[].quality_flags[]/mrl_violations[].message, status_reason) is deep-scanned recursively (BC-6 FINAL defect 2) | **YES (BC-6)** | ToxMcpObject.v1 |
| **interoperabilitySignoffPacket** | SERVER-AUTHORED reviewer signoff over a remediation bundle (signoff + blocking arm) | **YES (BC-6)** | ToxMcpObject.v1 (+ nested ReviewState) |
| **scientificFollowUpOwnerSignoffPacket** | SERVER-AUTHORED owner signoff (signoff + blocking arm) | **YES (BC-6)** | ToxMcpObject.v1 (+ nested ReviewState) |
| **sanitisedPublicReviewDossier** (embeds a SanitisedPublic* bundle) | SERVER-AUTHORED **PUBLIC-release** review disclosure; its `notes[]`/`limitations[]` and the embedded bundle's EVERY narrative leaf (deep-scanned recursively) are the highest-stakes overclaim surface | **YES (BC-6)** | ToxMcpObject.v1 |
| **scientificFollowUpQueueBundle** (operator `bundle_note` → `notes[]`) | SERVER-AUTHORED — appends an operator-controlled note verbatim into a producer `notes[]` that lands in this TOP-LEVEL tool result (an ungated operator-note SINK) | **YES (BC-6 FINAL)** | ToxMcpObject.v1 |
| **scientificFollowUpReviewBoard** (operator `board_note` → `notes[]`) | SERVER-AUTHORED operator-note SINK | **YES (BC-6 FINAL)** | ToxMcpObject.v1 |
| **scientificFollowUpOwnerHandoffPacket** (operator `packet_note` → `notes[]`) | SERVER-AUTHORED operator-note SINK | **YES (BC-6 FINAL)** | ToxMcpObject.v1 |
| **scientificFollowUpOwnerRemediationPacket** (operator `packet_note` → `notes[]`) | SERVER-AUTHORED operator-note SINK | **YES (BC-6 FINAL)** | ToxMcpObject.v1 |
| consumptionProfileSelectionResult | RELAY — selects a curated profile record + a deterministic matched/missing set operation | no | — |
| dietaryConsumptionProfile, dietaryResidueProfile, dietarySurveyDatasetRecord, dietaryIntakeScenarioDefinition, dietaryScenarioComparisonRecord, probabilisticIntakeSummary, uncertaintyIntakeAssessment, surveyDistributionSummaryReport | RELAY / structured echo of inputs + deterministic arithmetic (already carry native limitations + the dietary-boundary disclaimer; no `notes[]` free-text authoring arm) | no | — |
| *LookupResult family (referenceValue, contaminantLegalLimit, methodSupport, occurrenceEvidence, analyticalMethodEvidence, metalsOccurrence, metalsReviewFocus, consumptionDatasetSupport, reportingProfile) | RELAY of curated reference/occurrence records | no | — |
| adapterImportCheckResult, compareAdapterImportToWalkthroughResult, contaminantMonitoringImportCheckResult | RELAY / deterministic diff of a supplied import vs governed evidence | no | — |
| version-pinned review dossiers (adapter / contaminant / metals / tradeRisk / scientificFollowUpOwnerSignoff), interoperabilityRemediationBundle, interoperabilityExportPreview, toxclawDietaryEvidenceBundle, pbpkExternalImportBundle | SERVER-AUTHORED wrappers/overlays that RE-PACKAGE an already-gated core (a version-pinned dossier embeds the same interpretation bundle + signoff packet that ARE gated; an export wraps a gated summary). Their narrative payload is one of the gated cores; they add packaging/pins/redaction, not a NEW authored scientific conclusion. | not separately gated (the cores they embed ARE gated; the signoff/sanitised/public terminus IS gated) | — |
| *Request.v1 (all `export*Request` / `build*Request` / `lookup*Request` / `check*Request`) | TOOL INPUTS, not released conclusions | no | — |
| dietaryErrorPayload | error envelope | no | — |

**BC-6 exhaustive sweep.** v1 gated only four cores and claimed the metals /
signoff / sanitised / trade-risk / interoperability families were "wrappers" of
those cores. That was WRONG for the surfaces that author an INDEPENDENT conclusion:
the metals interpretation bundle + signoff packet, the trade-risk bundle, the
interoperability + scientific-follow-up-owner signoff packets, and the
sanitised-public review dossier are each derived from DIFFERENT producer inputs (a
metals occurrence/review-focus lookup, a global-trade-risk evaluation, an
adapter-interoperability remediation chain, a follow-up board), NOT from one of the
four gated cores — so a regression in their `notes[]` / signoff arm could NOT be
caught by gating only the four. In particular the metals **signoff packet** is a
PROVEN LAUNDERING CHANNEL: it shares the exact review/blocking invariants of the
contaminant signoff sibling yet was ungated. BC-6 gates EACH of these ten
independent server-authored-conclusion surfaces (4 original + 6 new), and proves the
laundering channel now bites the SAME `READY_WITH_BLOCKERS` (signed-off + unresolved
blockers) and `FREE_TEXT_OVERCLAIM` (unchecked note) as its sibling.

**BC-6 FINAL — the complete operator-note injection map.** The repo has ELEVEN
operator-controlled note inputs (`bundle_note` / `board_note` / `packet_note` request
fields) that flow VERBATIM into a producer `notes[]`. Tracing each to the TOP-LEVEL
MCP tool result it lands in:

| operator request-note field | producer notes[] sink (top-level tool result) | gated via |
|---|---|---|
| `ExportTradeRiskReviewBundleRequest.bundleNote` | tradeRiskReviewBundle | `_project_review_document` |
| `ExportContaminantMonitoringInterpretationBundleRequest.bundleNote` | contaminantMonitoringInterpretationBundle | review-doc |
| `ExportMetalsMonitoringInterpretationBundleRequest.bundleNote` | metalsMonitoringInterpretationBundle | review-doc |
| `ExportContaminantMonitoringSignoffPacketRequest.packetNote` | contaminantMonitoringSignoffPacket | signoff arm |
| `ExportMetalsMonitoringSignoffPacketRequest.packetNote` | metalsMonitoringSignoffPacket | signoff arm |
| `ExportInteroperabilitySignoffPacketRequest.packetNote` | interoperabilitySignoffPacket | signoff arm |
| `ExportScientificFollowUpOwnerSignoffPacketRequest.packetNote` | scientificFollowUpOwnerSignoffPacket | signoff arm |
| `ExportScientificFollowUpQueueBundleRequest.bundleNote` | **scientificFollowUpQueueBundle** | **review-doc (BC-6 FINAL)** |
| `ExportScientificFollowUpReviewBoardRequest.boardNote` | **scientificFollowUpReviewBoard** | **review-doc (BC-6 FINAL)** |
| `ExportScientificFollowUpOwnerHandoffPacketRequest.packetNote` | **scientificFollowUpOwnerHandoffPacket** | **review-doc (BC-6 FINAL)** |
| `ExportScientificFollowUpOwnerRemediationPacketRequest.packetNote` | **scientificFollowUpOwnerRemediationPacket** | **review-doc (BC-6 FINAL)** |

After BC-6 the first seven sinks landed on gated surfaces, but the last FOUR were
still UNGATED top-level results, letting an operator launder an overclaim that
traversed no gated surface. BC-6 FINAL gates each of those four (review documents —
their readiness signal is `overallStatus`, NOT a signoff status, so the
signoff/`READY_WITH_BLOCKERS` arm is unreachable and intentionally not projected),
routing every note through the same clause-level overclaim scan. The follow-up
SIGNOFF terminus (`scientificFollowUpOwnerSignoffPacket`) that DOES carry
`overallSignoffStatus` remains gated through the signoff arm and bites
`READY_WITH_BLOCKERS` on the SIGNED_OFF + unresolved-blockers laundering.

**BC-6 FINAL — recursive narrative-leaf deep-scan (defect 2).** Pre-fix,
`tradeRiskReviewBundle` deep-scanned ONLY `tradeReport.notes[]`. The real producer
also stamps server-authored free text into `tradeReport.qualityFlags[].message`, each
`jurisdiction_profiles[].notes[]`, `jurisdiction_profiles[].quality_flags[]` /
`mrl_violations[].message`, and a narrative `jurisdiction_profiles[].status_reason` —
all UNSCANNED (proven: an overclaim there → engine `valid=True`, no code). A generic
recursive narrative-leaf collector (`_collect_narrative_leaves`) now walks the WHOLE
released object and harvests EVERY substantive string under a narrative key at any
depth, so no narrative escapes the `FREE_TEXT_OVERCLAIM` scan. It harvests strings
ONLY under narrative keys, so ids / enums / numerics / booleans never mint scanned
content and the pristine real-producer corpus stays engine-clean.

**BC-6 FINAL ROUND-4 — close the operator-note class BY CONSTRUCTION.** Rounds 1–3
closed each differently-NAMED operator-note field one at a time because the collector
keyed off an EXACT-MATCH allowlist of narrative key names (`_NARRATIVE_LEAF_KEYS` =
notes/note/message/.../summary). Each round a new field escaped — last,
`actionItems[].followUpNote` (on all four follow-up surfaces) and
`interoperabilitySignoffPacket.actionItems[].triggerNote`: operator-supplied free
text nested in the `actionItems[]` array that no projector deep-scanned (independently
reproduced — the SAME overclaim string bit in top-level `notes[]` but passed
`valid=True` in `actionItems[].followUpNote`). The exact-match allowlist is replaced
by a **key-PATTERN matcher**: a string leaf is operator-narrative iff its KEY
(case-insensitive) CONTAINS any of note / message / reason / rationale / summary /
comment / justification / caveat / narrative / description / explanation / finding /
remark / annotation — a suffix/substring match, not an exact name. This catches
`followUpNote` / `triggerNote` / `packetNote` / `bundleNote` / `boardNote` /
`statusReason` / `qualityFlags[].message` / every `*Note` / `*Message` / `*Reason`
without enumerating one more field, and `_collect_narrative_leaves` is run over the
WHOLE released object on EVERY gated surface (not a curated per-surface embedded-source
list). It stays PRECISE — only string leaves DIRECTLY under a pattern-matched key are
harvested, so the faithful pristine corpus (verified: all 14 surfaces engine-clean)
never false-positives.

The remaining wrappers (version-pinned dossiers, remediation, exports) embed a
narrative payload that IS one of the fourteen gated surfaces, so their interpretive
content is covered transitively; the public/signoff TERMINUS of every chain is
gated. No false "only gated object" claim is made.

## Advertised codes (every one proven to bite on a producer-contract-valid fault)

RouteDoseEstimate (dietaryIntakeSummary), from DECLARED fields:
- `EXTERNAL_EXPOSURE_NOT_INTERNAL_DOSE` — the producer's declared `metric_label`
  asserts an internal-dose / Css / AUC / risk / regulatory metric (the projection
  passes the label through as the implied downstream use; an honest
  `external_oral_dose…` label is engine-clean).
- `EXPOSURE_UNCERTAINTY_AND_CEILING_REQUIRED` — the producer omits BOTH the intake
  bounds and the limitations narrative (both optional in the emission contract), so
  no uncertainty / confidence-ceiling reference is mintable.

ToxMcpObject (the three review / interpretation documents):
- `FREE_TEXT_OVERCLAIM` — a safety / regulatory overclaim in a declared narrative
  leaf (`notes[]` / `limitations[].message`, plus — for a surface that embeds a
  sub-report/bundle — EVERY narrative leaf of that embedded structure at any depth,
  collected by `_collect_narrative_leaves`: notes / message / reason / rationale /
  summary, e.g. the trade report's `qualityFlags[].message`, per-jurisdiction
  `notes[]` / `quality_flags[]`/`mrl_violations[].message` and `status_reason`, and
  the sanitised-dossier bundle's nested narrative). Standing
  non-claim DENIALS ("…does not certify … regulatory approval"; the verbless copular
  form "…is not a … regulatory acceptance decision") are routed to the
  NonClaimBoundary's requiredCaveats (negation-aware, not overclaim-scanned) to avoid
  false-positiving a faithful disclaimer; a genuine non-negated overclaim stays in
  the scanned `limitations` and bites.
  **BC-6 clause-bypass fix (defect 2):** narrative leaves are now split into
  CLAUSES/SENTENCES (`.!?;:` + contrastive conjunctions) and the denial-vs-overclaim
  classification runs PER CLAUSE. Pre-fix, a single global denial match routed the
  WHOLE leaf to caveats, so a non-negated overclaim clause sharing a string with a
  denial clause ("This does not certify regulatory approval; nonetheless it confirms
  the food is safe for regulatory submission.") laundered past the scanner with no
  bite. Now only the denial clause is exempted; the overclaim clause stays scanned
  and bites. (We deliberately do NOT split on bare coordinating "and"/"or", which
  would strip a negated phrase from its negation and false-positive a faithful
  disclaimer — verified against the real producer corpus.)
- `READY_WITH_BLOCKERS` — a `signed_off` signoff packet (contaminant / **metals** /
  interoperability / scientific-follow-up-owner) that still declares
  `unresolvedBlockingActionIds` (publication-ready ReviewState with blockers).

Meta fail-closed (synthesized; ALWAYS block): `SOURCE_CONTRACT_VIOLATION`,
`ENGINE_UNAVAILABLE`, `UNRECOGNIZED_SPINE_SCHEMA_ID`, `VENDOR_DIGEST_MISMATCH`,
`PROJECTION_INCOMPLETE`.

### Honest-dropped codes (documented N/A)

- **AI-provenance arm** (`AI_MODEL_IDENTITY_REQUIRED` / `HUMAN_REVIEW_*_AI` /
  `AI_USE_NONE_WITH_MODEL_TRACE` / `MODEL_IDENTITY_IS_NOT_VALIDATION` / …) —
  dietary-exposure-mcp is deterministic and zero-LLM. The strict emission contracts
  carry NO `aiUse` / model-use field, and `src/` has no LLM / model-inference lane.
  The gate therefore projects neither an `AssessmentRun` nor an `AiModelUseRecord`;
  advertising an AI code would be a dead arm. **Re-introduction path:** if a future
  release adds an LLM/narrative lane whose output enters a released object with a
  real declared AI-provenance field, plumb that field into an `AssessmentRun`
  projection and advertise the AI codes (each proven to bite on a real source
  AI-provenance gap).
- `READY_WITH_PENDING_HUMAN_REVIEW` / `READY_WITHOUT_HUMAN_REVIEW` — the signoff
  packet's only review-readiness signal is `overallSignoffStatus`; `signed_off`
  semantically IS completed human review, so there is no producer-emittable state
  yielding `publicationReadiness=ready` WITH `humanReview=required/not_required`.
  Unreachable on a contract-valid fault; `READY_WITH_BLOCKERS` covers the
  signed-off-but-not-actually-ready arm.

## Decision (the hardened Track-B template)

1. **Vendor** the digest-pinned spine engine under `vendor/schema-spine/`
   (`gitSha e0a6a0581efd8dfd5b10c2de14435d87769c5944`), byte-verified by
   `scripts/vendor_verify.py` (`fileDigests` SHA-256 map in `VENDORED_FROM.json`).
2. **Fail-closed Node bridge** (`src/dietary_mcp/governance/spine_bridge.py`):
   digest tamper / missing node / non-zero exit / unrecognized schemaId all BLOCK;
   `valid:true` is trusted only after every guard passes.
3. **Source-contract guard** (`src/dietary_mcp/governance/source_contract.py`): a
   dependency-free Draft-07 SUBSET validator enforcing each producer's STRICT
   `additionalProperties:false` emission contract (`schemas/spine-emission-contract/`),
   wired at the TOP of `run_gate`. A non-contract packet is a
   `SOURCE_CONTRACT_VIOLATION` block and is NEVER projected — this closes the
   producer-emission-contract dead-arm class. The strict contracts were tightened
   from the producer's FULL declared schema and VERIFIED by running the REAL
   producer seams (`DietaryRuntime` + the export builders, `model_dump(mode="json",
   by_alias=True)`) across optional-field-bearing AND optional-omitting variants —
   not the stale `schemas/examples/*` fixtures (which fail their own released
   schemas). No over-tighten: a faithful emission that omits an optional passes.
4. **Total projection from declared fields only**
   (`src/dietary_mcp/governance/project_to_spine.py`): positive structured /
   canonical evidence (a disguised / placeholder / homoglyph / zero-width string
   mints no narrative); NFKD identifier normalization; the producer's real
   `metric_label` / signoff status / blocking-action ids passed THROUGH (never a
   re-derived narrower allowlist); any unmapped field → `PROJECTION_INCOMPLETE`.
5. **Advertise only producer-contract-valid-reachable codes** — each proven to bite
   on an Ajv-valid fault through the real bridge (not a projected-object mutation),
   in `tests/governance_spine/test_scientific_invariants_adversarial.py`.

## Enforcement

`.github/workflows/scientific-invariants.yml` runs `vendor:verify` → the gate →
the governance self-tests. **ADVISORY** on the GitHub Free private repo (no
required-status-checks); the runtime bridge additionally fails closed, so a
tampered engine or non-contract packet blocks the gate even when CI is advisory.
PROMOTE-TO-BLOCKING when the repo gains branch protection (Team/Pro or public).

The pre-existing Track-A gates (`track-a-gates.yml`: mcp-conformance + schema-drift)
and `security.yml` are untouched and remain green (the gate adds files only under
`vendor/`, `schemas/spine-emission-contract/`, `src/dietary_mcp/governance/`,
`scripts/`, `tests/governance_spine/`, and a new workflow — none of which the
schema-drift `docs/contracts/schemas/` scan or the conformance tool-surface set
touch).

## Known limitation — operator-supplied secondary-prose residual (accepted)

The `FREE_TEXT_OVERCLAIM` scan harvests operator-controllable free text by a
**recursive key-substring match** (`_collect_narrative_leaves` /
`_NARRATIVE_KEY_PATTERN`) over the WHOLE released object on every gated surface:
any string leaf whose key contains one of
`note / message / reason / rationale / summary / comment / justification / caveat /
narrative / description / explanation / finding / remark / annotation` is scanned,
at any depth — including all 11 top-level operator-note sinks, nested
`actionItems[].followUpNote` / `actionItems[].triggerNote`, and the embedded
`GlobalTradeRiskReport` narrative leaves (`qualityFlags[].message`,
`jurisdiction_profiles[].notes[]` / `.quality_flags[].message` / `.status_reason`,
`mrl_violations[].message`). The substantive scientific conclusions
(external-dose intake, signoff/blocking status, exposure uncertainty) are gated by
their own structured codes.

**RESIDUAL (accepted, advisory gate):** a key-name match is, by construction, an
allowlist — operator prose placed in a *secondary* field whose key carries **no**
narrative token (e.g. `actionItems[].title`, `requiredReviewQuestions[]`,
`reviewPrompts[].prompt`, `recommendedSteps`, `intendedUse`, a relayed
`displayName`) is **not** scanned, so a determined operator could route an
overclaim through one of those fields. This residual is accepted because: (a) the
gate is **advisory** (no required-status-checks on the Free-plan private repo);
(b) every *substantive scientific conclusion* and every *primary* operator-note
sink is already gated; (c) the construction-closed alternative — scanning **all**
string leaves regardless of key — risks false positives on relayed external data
(e.g. a chemical `displayName`) and was judged not worth that cost for an advisory
gate at this time.

**RE-INTRODUCTION TRIGGER:** if any of those secondary prose fields becomes a
material operator-overclaim vector (or the gate is promoted to blocking), replace
the key-substring allowlist with a **scan-all-string-leaves** design that
structurally excludes non-prose (ids / enums / codes / hashes / timestamps /
numeric-strings / known relay fields), and re-verify the pristine corpus stays
engine-clean (no false positive) under the wider scan.
