# PRD — Dietary MCP

**Product name:** Dietary MCP  
**Version target:** v0.1.0  
**Product type:** Public MCP server for food-residue and dietary oral intake workflows  
**Date:** 2026-04-08

## 1. Product summary

Dietary MCP is the ToxMCP service that converts **commodity residue assumptions plus food-consumption profiles** into **population-specific oral dietary intake outputs** and PBPK-ready oral dose handoffs.

Its scope is intentionally narrow: **diet-mediated oral exposure only**.

It exists to keep dietary workflows separate from direct-use oral scenarios, because the input taxonomies, validation regimes, and regulatory semantics differ materially from consumer product-use exposure.

## 2. Critical boundary rule

**Dietary MCP is not “the oral MCP.”**

### Dietary MCP owns
- food-mediated oral intake
- commodity residue inputs
- food-consumption mappings
- acute/chronic dietary intake summaries
- commodity contribution summaries
- oral PBPK-ready external dose handoff for dietary scenarios

### Dietary MCP does not own
- direct-use oral exposure from product tasks
- incidental oral exposure from consumer-use scenarios
- generic soil or drinking-water ingestion by default
- PBPK execution
- risk characterization

Direct-use oral remains in Direct-Use Exposure MCP.

## 3. Problem statement

The suite currently has direct-use oral capability but lacks a dedicated dietary layer that can:

- normalize residue inputs at commodity level,
- map foods to consumption profiles and populations,
- calculate oral intake in a way aligned with dietary regulatory semantics,
- separate acute/chronic dietary workflows from consumer-use scenarios,
- export stable oral dose objects for PBPK or ToxClaw.

Without a Dietary MCP, the platform risks either:
- mixing food-residue logic into Direct-Use Exposure MCP, or
- exposing dietary model brands directly instead of stable harmonized contracts.

## 4. Goals

### Primary goals
1. Represent commodity residue and diet-consumption inputs as typed contracts.
2. Produce deterministic or bounded oral intake summaries by population.
3. Preserve contribution transparency by commodity / food group / scenario driver.
4. Export PBPK-ready oral dose objects with stable semantics.
5. Keep dietary workflows scientifically and operationally separate from direct-use oral scenarios.

### Secondary goals
1. Support acute and chronic dietary framing.
2. Support region-aware consumption profile packs.
3. Support residue evidence reconciliation.
4. Support later alignment with PRIMo- or DEEM-style workflows without making either brand the core abstraction.

## 5. Non-goals

Dietary MCP v0.1 does **not** own:
- consumer product direct-use scenarios,
- indoor or near-field inhalation,
- mechanistic environmental fate as a required upstream layer,
- full farm-to-fork crop residue generation,
- PBPK execution,
- final pass/fail regulatory conclusions,
- mandatory Monte Carlo distributions in the first release.

## 6. Users and consumers

### Primary users
- dietary exposure assessors
- toxicologists needing oral intake context
- ToxClaw orchestrations comparing dietary vs other pathways
- PBPK workflows needing oral external dose inputs

### System consumers
- PBPK MCP
- ToxClaw
- Direct-Use Exposure MCP only indirectly for aggregate cross-pathway orchestration

## 7. Scientific stance for v0.1

Dietary MCP should follow the suite’s auditable-first philosophy:

- deterministic or bounded intake summaries first,
- clear acute vs chronic semantics,
- explicit population and body-weight context,
- explicit residue-source provenance,
- no opaque probabilistic layer in v0.1.

## 8. v0.1 scope

### Included
- reviewed or curated commodity residue inputs
- commodity-to-food mapping and processing-factor handling where explicitly supported
- population-specific consumption profiles
- acute and chronic intake summaries
- contribution analysis by commodity or food class
- scenario comparison and assumption deltas
- PBPK-ready oral dose handoff
- schema publication, examples, defaults manifest, validation resources

### Deferred
- mandatory proprietary diet survey dependencies
- full probabilistic population engines
- full crop-fate / pesticide dissipation modeling
- automatic conversion of arbitrary residue spreadsheets without validation
- generic environmental-media ingestion pathways beyond food-residue workflows

## 9. Core user stories

1. As a dietary assessor, I want to supply commodity residue values and a population profile to obtain an oral intake summary.
2. As ToxClaw, I want to compare acute and chronic dietary scenarios with explicit contribution differences.
3. As PBPK MCP, I want a normalized oral dose bundle without food-taxonomy clutter.
4. As a reviewer, I want every intake output to show which commodities, consumption assumptions, and defaults contributed to the result.

## 10. Proposed tool catalog

### Scenario construction
- `dietary_build_residue_profile`
- `dietary_build_dietary_intake_scenario`
- `dietary_build_bounded_intake_summary`
- `dietary_compare_dietary_scenarios`

### Evidence and utilities
- `dietary_assess_residue_evidence_fit`
- `dietary_apply_residue_evidence`
- `dietary_reconcile_residue_evidence`
- `dietary_select_consumption_profile`

### Export
- `dietary_export_pbpk_oral_input`
- `dietary_export_toxclaw_dietary_evidence_bundle`

## 11. Proposed resource catalog

### Contracts and examples
- `contracts://manifest`
- `schemas://{schema_name}`
- `examples://{example_name}`
- `defaults://manifest`
- `consumption-profiles://manifest`
- `commodity-taxonomy://manifest`

### Documentation
- `docs://operator-guide`
- `docs://provenance-policy`
- `docs://dietary-boundary-guide`
- `docs://population-profile-guide`
- `docs://acute-vs-chronic-guide`
- `docs://suite-integration-guide`
- `docs://validation-framework`
- `docs://release-readiness`

### Release and review
- `release://metadata-report`
- `release://readiness-report`
- `release://security-provenance-review-report`

## 12. Required contracts

### Shared inputs
- `chemical_identity`
- `route_dose_estimate` (for cross-pathway aggregation later)
- `pbpk_external_import_bundle`

### Dietary-owned contracts
- `dietary_commodity_residue_record`
- `dietary_residue_profile`
- `dietary_consumption_profile`
- `dietary_intake_scenario_definition`
- `dietary_intake_summary`
- `dietary_contribution_record`
- `dietary_assumption_record`
- `dietary_scenario_comparison_record`

## 13. Contract semantics

### `dietary_commodity_residue_record`
Must capture:
- commodity or food code
- residue concentration and unit
- source type (monitoring, modeled, curated default, user supplied)
- optional processing factor
- region / time context
- provenance and review status

### `dietary_consumption_profile`
Must capture:
- population group
- survey/profile source
- body weight context
- region
- acute or chronic applicability
- intake units
- provenance and limitations

### `dietary_intake_summary`
Must capture:
- scenario class
- intake window semantics
- oral external dose metric
- body-weight normalization semantics
- dominant commodity contributors
- assumptions, provenance, uncertainty notes
- fit-for-purpose tag

## 14. Methods and runtime design

### Preferred architecture
- thin MCP interface
- contract-validated dietary runtime
- plugin family by dietary workflow class
- governed consumption-profile registry
- residue evidence reconciliation layer
- provenance / defaults / comparison kernels

### Candidate workflow families
- deterministic point-estimate intake
- bounded acute summary
- bounded chronic summary
- PRIMo-aligned adapter
- DEEM-aligned adapter

### Design rule
The public abstraction is **not** “run PRIMo” or “run DEEM”.  
The public abstraction is “build a dietary intake scenario and compute oral intake outputs.”

## 15. Defaults and provenance

Every dietary result must:
- distinguish residue evidence from consumption defaults,
- distinguish user values from curated defaults,
- preserve commodity coding and mapping provenance,
- emit limitation notes when surrogate or heuristic mappings are used,
- identify acute/chronic semantics explicitly.

## 16. Validation strategy

### Minimum v0.1 validation
- benchmark against hand-worked intake cases
- benchmark against representative acute/chronic dietary reference cases
- schema validation across all examples
- negative tests for invalid food/unit/body-weight combinations
- regression tests for consumption-profile version drift
- comparison tests that preserve commodity contribution transparency

### Validation resources
- dietary benchmark manifest
- validation dossier
- commodity mapping gap report
- population-profile applicability notes

## 17. Release gates

A release cannot ship unless:
1. acute vs chronic semantics are explicit in contracts and examples,
2. all schemas and examples validate,
3. benchmark cases pass within declared tolerances,
4. consumption-profile and residue-default versions are published,
5. commodity contribution outputs are present and auditable,
6. PBPK oral export validates directly,
7. limitation notes prevent misuse as a final regulatory decision.

## 18. Key decisions for v0.1

### Decision 1 — Dietary only
Food-mediated oral only; not all oral.

### Decision 2 — Deterministic / bounded first
Use transparent summaries before full probabilistic population engines.

### Decision 3 — Stable oral handoff
Export PBPK-ready oral dose semantics without leaking dietary model-internal structures.

### Decision 4 — Residue evidence is reviewable
Residue source quality must remain visible and reviewable.

## 19. Risks and open questions

### Risk: boundary confusion with Direct-Use Exposure MCP
Mitigation: reject direct-use oral requests and route them to Direct-Use Exposure MCP.

### Risk: overpromising on population variability
Mitigation: label v0.1 outputs as deterministic or bounded, not full population distributions unless actually implemented.

### Risk: incompatible food taxonomies across regions
Mitigation: publish explicit taxonomy manifests and mapping provenance.

### Open questions
- Which commodity taxonomy is mandatory at launch?
- Are processing factors curated centrally or only accepted as reviewed input?
- Is drinking-water ingestion kept fully out of scope for v0.1?
- Which population profiles are first-class at launch?

## 20. Implementation phases

### Phase 1
- publish contracts, schemas, and examples
- implement residue profile ingestion and population consumption profiles
- stand up provenance/defaults kernel

### Phase 2
- implement deterministic acute/chronic intake calculations
- add scenario comparison and commodity contribution outputs
- add PBPK oral export

### Phase 3
- add adapter boundaries for PRIMo-/DEEM-aligned workflows
- add richer regional population packs
- add bounded distribution support if scientifically justified

## 21. Success criteria

Dietary MCP is successful when:
- food-mediated intake questions no longer need to be forced into Direct-Use Exposure MCP,
- oral dose outputs for dietary scenarios are stable and auditable,
- commodity contributions and evidence quality are transparent,
- downstream PBPK and ToxClaw consumers can use outputs without bespoke mappings.
