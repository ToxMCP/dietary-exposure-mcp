# Regulatory Governance

Dietary MCP v0.1 publishes an EU-first governance layer for version-pinned adapter review dossiers.

## Source status semantics

Each governed source record now carries:

- `documentStatus`
- `regulatoryRole`
- `submissionUse`
- `normativeFor`
- lifecycle links through `supersedes` and `supersededBy`

These fields are intended to help reviewers distinguish binding or guidance inputs from datasets, technical reports, and tool metadata.

Dietary MCP also publishes governed local source-database packs for:

- authority-specific reference values
- consumption-dataset support
- method-registry support
- legal-authority anchors
- emerging-contaminant family posture

These packs preserve authority conflicts rather than flattening them into one canonical answer.

## Model governance semantics

Each model family publishes:

- a `governanceStatus`
- whether `submissionAllowed` is true or false
- the current version label and dataset basis
- required disclaimers
- active errata records

Current v0.1 defaults are conservative:

- `reference_dietary` and `adapter_stub` are internal-reference-only
- `efsa_primo_adapter` and `epa_deem_adapter` are compatibility-harness-only
- no current model family is submission-capable

The new emerging-contaminant layer now exposes:

- `microplastics_emerging` for evidence-limited microplastics and nanoplastics review
- `pfas_food_contaminants` for PFAS food-contaminant provenance, legal anchors, and monitoring context
- `acrylamide_process_contaminants` for acrylamide benchmark-dose, mitigation, and monitoring context
- `bisphenol_food_contact_migration` for BPA and bisphenol dietary food-contact migration provenance
- `cadmium_food_contaminants` for cadmium dietary exposure, health-based guidance, legal provenance, and official-control sampling/analysis context
- `lead_food_contaminants` for lead benchmark-dose, dietary exposure, legal provenance, and official-control sampling/analysis context
- `inorganic_arsenic_food_contaminants` for inorganic arsenic benchmark-dose, dietary exposure, legal provenance, and official-control sampling/analysis context
- `mercury_food_contaminants` for mercury and methylmercury TWI provenance, dietary exposure, legal provenance, and official-control sampling/analysis context

None of these families is a submission-capable model family in v0.1.

## Readiness profiles

Dietary MCP publishes three fixed Phase 1 readiness profiles:

- `eu_internal_review`
- `eu_submission_candidate`
- `eu_consultation_exploratory`

These are evaluated through a fixed ruleset implemented in code and published as reviewable rule metadata under `validation://regulatory-rules`.

## Confidentiality-aware public packaging

Dietary MCP now also publishes a Phase 2 confidentiality-aware packaging layer:

- internal review dossiers stay version-pinned and fully auditable
- sanitised public dossiers preserve governed provenance for retained content
- confidential fields and resources are represented through machine-readable sanitisation records

This packaging layer does not change model governance or make any current model family submission-capable.

## Why current adapters are not submission-capable

The built-in PRIMo- and DEEM-aligned families normalize compatibility inputs through Dietary MCP contracts. They do not claim official engine equivalence, proprietary dataset reproduction, or regulator endorsement.

As a result:

- they may support internal review
- they may support consultation-oriented exploration when the dossier remains explicitly watermarked
- they should fail the `eu_submission_candidate` profile in v0.1
