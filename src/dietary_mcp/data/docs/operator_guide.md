# Dietary Exposure MCP Operator Guide

Dietary Exposure MCP accepts governed residue profiles plus population consumption profiles and returns auditable dietary oral intake summaries for downstream use.

Review workflows in this repo remain explicit about scope:

- readiness is a governed review assessment with scientific-integrity checks, not a final regulatory decision
- signoff records reviewer closure state and supporting evidence, not automatic proof of submission acceptance

The bundled illustrative screening defaults currently cover `adult_general`, `child_1_6`, `adolescent_11_17`, `older_adult_65_plus`, and `pregnant_adult` across thirteen canonical commodity codes for transparent internal screening and review-support workflows.

## Jurisdiction coverage

Wave 1 jurisdiction expansion is now pinned to official primary sources for `us`, `codex_global`, and `cn`, with strict no-borrowing semantics across authorities.

- `deep curated` means the repo ships official source records plus a legal anchor and at least one jurisdiction-specific reference value or exact curated MRL record for the current taxonomy.
- `deep curated` also covers lanes where the repo ships exact jurisdiction-specific contaminant legal-limit records from final official sources.
- `anchor-only` means the repo ships an official source and legal anchor, but not a jurisdiction-specific reference-value layer or exact curated ML extraction yet.
- `explicit gap` means the repo does not ship a final official wave-1 record for that jurisdiction/family/substance, and lookup or trade-risk outputs should surface the gap instead of substituting EU or Codex values.

The source-of-truth coverage matrix for this wave is [jurisdiction_expansion_wave1_matrix.md](jurisdiction_expansion_wave1_matrix.md).

The runtime now also exposes this coverage posture in machine-readable form through jurisdiction-coverage manifests and reference-value lookup coverage summaries, so downstream review systems do not need to infer lane strength from prose alone.

Current headline coverage is:

- `EU`: still the deepest end-to-end review baseline across deterministic intake, readiness, signoff, and monitoring support.
- `US`: deep curated pesticide tolerance coverage for selected wave-1 residue pairs plus exact official contaminant legal limits for lead, inorganic arsenic, and methylmercury in their shipped FDA guidance scopes.
- `Codex`: deep curated JMPR/CXL pesticide coverage for selected wave-1 residues plus exact current CXS 193 contaminant legal-limit coverage for selected lead, cadmium, and inorganic-arsenic lanes; Codex mercury remains anchor-only because the shipped taxonomy does not yet map the species-specific methylmercury rows exactly.
- `China`: deep curated GB 2763 pesticide ADI/MRL coverage for selected wave-1 residues plus exact GB 2762 contaminant legal-limit coverage for cadmium, lead, inorganic arsenic, and methylmercury.

## Supported workflows

- build residue profiles from reviewed or user-supplied commodity residue inputs
- select governed population consumption profiles
- build dietary intake scenarios with explicit acute/chronic semantics
- compute deterministic point-estimate or bounded intake summaries
- compare dietary scenarios and contribution drivers
- assess version-pinned adapter, contaminant-monitoring, and metals-monitoring review dossiers against governed readiness profiles
- inspect readiness outputs for exact ledger-derived scientific follow-up items already present on contaminant-monitoring or metals-monitoring dossier signoff packets
- use readiness-side scientific follow-up queues to separate open, pending, acknowledged, completed, waived, and escalated monitoring follow-up without reclassifying raw action state downstream
- export machine-readable scientific follow-up queue bundles from readiness assessments when downstream review systems need ordered action items, queue labels, and linked workflow documentation in one handoff object
- inspect `legalLimitReviews` on readiness assessments and scientific follow-up queue bundles when submission-candidate screening needs explicit visibility into partial, anchor-only, or gap legal-limit support before work is routed downstream
- export scientific follow-up review boards when downstream reviewer operations need deterministic owner-lane and due-state routing on top of the readiness-side queue bundle
- export scientific follow-up owner handoff packets when downstream reviewer operations need one owner-lane packet, optionally filtered by due state, instead of the full routing board
- export scientific follow-up owner remediation packets when one owner lane needs deterministic next-step classes such as resolve now, review this cycle, track in progress, or record closure
- export scientific follow-up owner signoff packets when one owner lane needs auditable acknowledgement, completion, or waiver decisions on those remediation items
- export version-pinned scientific follow-up owner signoff dossiers when one owner lane needs a pinned audit overlay that freezes the exact signoff packet, upstream dossier payload, and remaining escalations
- look up authority-specific reference values without flattening EFSA, JMPR, EPA, or WHO conflicts
- use `requestedJurisdictionStatus` and `curatedSupportTypes` on reference-value lookups to distinguish exact jurisdictional values from anchor-only families, family-curated-without-value lanes, and explicit gaps
- look up jurisdiction-specific contaminant legal limits without borrowing EU, Codex, US, or China values across authorities
- use `requestedLaneStatus`, `curatedScopeCommodityCodes`, and `curatedScopeMatrixGroups` on contaminant legal-limit lookups to distinguish exact curated matches from family-level curated coverage that still does not support the requested commodity or matrix exactly
- inspect `referenceValueJurisdictionStatus` on trade-risk jurisdiction profiles when trade screening needs to know whether the reference-value side is exact, anchor-only, family-curated-without-value, or an explicit gap
- inspect `mrlCoverageStatus`, `mrlCuratedSupportTypes`, and `mrlCuratedScopeCommodityCodes` on trade-risk jurisdiction profiles when residue screening needs to distinguish exact requested-pair MRL coverage from partial curated scope, family-curated-without-MRL lanes, anchor-only families, and explicit gaps
- read trade-risk `notes` as the reviewer-facing explanation layer; they now restate no-borrowing semantics, pass-status limits, and the exact meaning of partial or missing MRL/reference-value support in plain language
- export `tradeRiskReviewBundle` and `versionPinnedTradeRiskReviewDossier` when trade screening needs an auditable internal-review packet with reviewer prompts, pinned MRL/reference/jurisdiction manifests, and frozen no-borrowing semantics
- inspect governed method-support posture and consumption-dataset support for pesticide and emerging-contaminant families
- inspect governed reporting profiles when a family needs more than one defensible reporting convention, for example primary EU PFAS EFSA-4 reporting plus optional Dutch advisory PEQ-style extensions
- inspect governed occurrence-evidence and analytical-method-evidence records for pesticide-residue and contaminants monitoring review
- validate contaminant-monitoring CSV inputs against governed evidence objects before reviewer interpretation, including the governed pesticide-residue monitoring examples for glyphosate, acetamiprid, imidacloprid, glufosinate, oxamyl, ethiprole, tetraconazole, tebuconazole, spirotetramat, and difenoconazole
- inspect `applicableReportingProfileIds` on contaminant-monitoring checks when the same monitoring table should be kept compatible with both a primary EU reporting basis and optional national advisory extensions such as Dutch home-egg or fish and biota PFAS PEQ reporting
- use `reportingProfileSummary` in contaminant-monitoring checks, interpretation bundles, signoff packets, and version-pinned dossiers when downstream review needs the primary EU basis, optional advisory extensions, and non-substitution links separated explicitly
- inspect structured uncertainty-and-assumption ledgers on contaminant-monitoring checks and interpretation bundles so analytical gaps, lower-bound handling assumptions, and review-only governance posture remain explicit
- export contaminant-monitoring interpretation bundles that package the validated monitoring check, linked evidence context, linked review-focus records, and reviewer prompts into one audit-ready object
- inspect `legalLimitReviews` on contaminant-monitoring interpretation bundles, signoff packets, and pinned dossiers when reviewer-facing monitoring packets need the same exact-versus-partial-versus-anchor-versus-gap legal-limit semantics now used by the source lookups
- export contaminant-monitoring signoff packets that record reviewer completion, acknowledgement, waiver, and unresolved blocking actions on top of the interpretation bundle, including ledger-derived actions for analytical gaps and explicit assumptions
- export version-pinned contaminant-monitoring review dossiers that freeze the exact governed manifests and workflow docs used during review and surface remaining waivers or unresolved blocking actions, including ledger-derived scientific follow-up, as escalation items
- inspect governed metals occurrence and monitoring context for cadmium, lead, inorganic arsenic, and mercury
- use governed metals-occurrence interpretation fields such as priority food groups, high-attention foods, sensitive populations, and review questions as review aids without treating them as autonomous exposure logic
- inspect governed metals review-focus records for commodity- and population-specific follow-up on cadmium, lead, inorganic arsenic, and mercury
- inspect structured uncertainty-and-assumption ledgers on metals interpretation bundles so monitoring-context assumptions, trend-signal limits, and review-only governance remain explicit
- export metals monitoring interpretation bundles that package occurrence context, review-focus records, linked governance ids, and reviewer prompts into one audit-ready object
- inspect `legalLimitReviews` on metals monitoring interpretation bundles, signoff packets, and pinned dossiers when family-level legal-limit support must stay explicit instead of being inferred from occurrence context alone
- export metals monitoring signoff packets that record reviewer completion, acknowledgement, waiver, and unresolved blocking actions on top of the interpretation bundle, including ledger-derived actions for monitoring-context assumptions and trend-signal limits
- export version-pinned metals monitoring review dossiers that freeze the exact governed manifests and workflow docs used during review and surface remaining waivers or unresolved blocking actions, including ledger-derived scientific follow-up, as escalation items
- export PBPK-ready oral dose bundles and ToxClaw evidence bundles
- export adapter review bundles and version-pinned review dossiers with governance snapshots
- derive sanitised-public review dossiers with explicit redaction records for non-confidential exchange, including monitoring-derived dossiers that preserve legal-limit posture and escalation visibility, owner-lane signoff dossiers that preserve waiver/blocking escalation posture without retaining exact internal payload fingerprints, and trade-risk dossiers that preserve jurisdiction screening semantics without retaining confidential identity-bearing resources
- publish provisional food-vocabulary and processed-commodity crosswalks for workflow hardening
- build validation-only OHT/IUCLID-aligned JSON interoperability previews with explicit unsupported-field reporting
- assess staged interoperability previews against governed exchange-readiness profiles before any future XML work
- export governed remediation bundles that translate interoperability readiness findings into machine-readable reviewer actions
- export reviewer signoff packets that record completion, acknowledgement, or waiver rationale for remediation actions

## Not supported in v0.1

- direct-use oral product scenarios
- medicinal TCM regimens and product-centric supplement dosing
- environmental-media oral intake from water or soil outside food-mediated semantics
- PBPK execution
- final risk characterization
- opaque probabilistic population engines
- regulator-facing submission decisions from the built-in model families
- microplastics submission-oriented decisions from immature or non-standardized evidence and methods
- PFAS submission-oriented decisions without a reviewed PFAS-specific method pack and explicit jurisdictional signoff
- acrylamide submission-oriented decisions without a reviewed acrylamide-specific method pack and explicit jurisdictional signoff
- bisphenol submission-oriented decisions without a reviewed food-contact migration method pack and explicit jurisdictional signoff
- cadmium submission-oriented decisions without a reviewed cadmium-specific method pack, including official-control method coverage and explicit jurisdictional signoff
- lead submission-oriented decisions without a reviewed lead-specific method pack, including official-control method coverage and explicit jurisdictional signoff
- inorganic arsenic submission-oriented decisions without a reviewed inorganic-arsenic-specific method pack, including official-control method coverage and explicit jurisdictional signoff
- mercury submission-oriented decisions without a reviewed mercury-specific method pack, including official-control method coverage and explicit jurisdictional signoff

Blocking signoff actions that are marked `completed` or `waived` must carry supporting evidence URIs. Closed review dossiers also require the underlying scientific blockers to be resolved rather than hidden behind workflow state alone.
