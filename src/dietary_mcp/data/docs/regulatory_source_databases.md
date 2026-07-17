# Regulatory Source Databases

Dietary MCP v0.1 now exposes governed local source-database packs for regulatory provenance and lookup support. These packs are packaged with the MCP and resolve in both source-checkout and installed-wheel mode.

## Database layers

- `source_catalog.json` remains the single authority registry and distinguishes current EFSA OpenFoodTox 3.0 from the superseded, checksum-pinned 2023 OpenFoodTox 2.0 bulk snapshot. It also includes EFSA food-consumption infrastructure, EU Menu metadata, FAO/JMPR, WHO, OECD, Codex, FDA, PFAS legal anchors, acrylamide regulatory sources, bisphenol food-contact sources, cadmium/lead/inorganic-arsenic/mercury contaminant sources, and EU legal anchors.
- `reference_values.json` publishes curated authority-specific toxicological reference-value records without flattening EFSA, JMPR, or other authority conflicts, and now includes additional EFSA glyphosate, acetamiprid, imidacloprid, glufosinate, oxamyl, ethiprole, tetraconazole, tebuconazole, PFAS, acrylamide, BPA, cadmium, lead, inorganic arsenic, and mercury examples.
- `consumption_datasets.json` publishes governed metadata for EFSA food-consumption infrastructure, EU Menu, DietEx support metadata, WHO GEMS/Food cluster diets, PFAS monitoring context, acrylamide monitoring context, BPA food-contact dietary context, and cadmium/lead/inorganic-arsenic/mercury dietary exposure context.
- `method_registry.json` publishes governed metadata for PRIMo, DEEM, JMPR IEDI/IESTI context, OECD guidance records, EFSA 2023 annual pesticide-residues reporting context, glufosinate, oxamyl, ethiprole, tetraconazole, tebuconazole, spirotetramat, and difenoconazole review context, organic-food pesticide-findings context, shared EU official-control sampling and analysis rules for metals contaminants, and separate PFAS, acrylamide, bisphenol, cadmium, lead, inorganic-arsenic, mercury, and microplastics method-context layers.
- `legal_authorities.json` keeps EU legal anchors and official-control regulations distinct from guidance, datasets, and tool metadata.
- `reporting_profiles.json` publishes governed reporting conventions for families that need more than one defensible reporting basis, including primary EU PFAS EFSA-4 reporting plus optional advisory extensions for Dutch home-egg and fish and biota interpretation.
- `occurrence_evidence_registry.json` publishes governed occurrence-evidence objects that link pesticide-residue or contaminant occurrence context to datasets, legal anchors, reference values, and review-focus records for monitoring review, including governed glyphosate, acetamiprid, imidacloprid, glufosinate, oxamyl, ethiprole, tetraconazole, tebuconazole, spirotetramat, and difenoconazole pesticide-residue examples plus matrix-specific PFAS egg, fish, and dairy context, acrylamide fried-potato and coffee context, and BPA canned-food and beverage context.
- `analytical_method_evidence_registry.json` publishes governed analytical-method evidence objects that preserve LOQ/LOD, recovery, uncertainty, monitoring, mitigation, pesticide residue analytical-review context, and official-control context without pretending to execute laboratory methods, including matrix-specific PFAS egg, fish, and dairy contexts, acrylamide fried-potato and coffee context, BPA canned-food and beverage context, and spirotetramat and difenoconazole review layers.
- `metals_occurrence_registry.json` publishes governed family-level occurrence and monitoring support records that link EFSA metals exposure publications, dataset metadata, shared EU official-control rules, current EU contaminants-law anchors, and explicit interpretation fields such as priority food groups, high-attention foods, sensitive populations, and review questions.
- `metals_review_focus_registry.json` publishes governed commodity- and population-specific reviewer focus records for cadmium, lead, inorganic arsenic, and mercury, with explicit links back to the family-level occurrence records and their legal, method, dataset, and reference-value context.
- `emerging_contaminants.json` publishes separate `microplastics_emerging`, `pfas_food_contaminants`, `acrylamide_process_contaminants`, `bisphenol_food_contact_migration`, `cadmium_food_contaminants`, `lead_food_contaminants`, `inorganic_arsenic_food_contaminants`, and `mercury_food_contaminants` families with explicit method-maturity, evidence-limit, and submission-gating controls.

## Conflict preservation

Authority conflicts are preserved by design.

- Dietary MCP does not flatten EFSA, JMPR, EPA, WHO, or other authority outputs into a single canonical reference value.
- Conflict groups are explicit in the lookup result so downstream clients must choose a jurisdiction or review profile intentionally.
- Curated record stubs are allowed where public redistribution of the full structured source database is unclear; provenance and source links remain explicit.
- OpenFoodTox snapshot variations preserve structured population, qualifier, assessment-year, source-output, and unit context. The lookup never chooses a canonical value from those variations automatically.

## EU pesticide backbone

The first-class EU pesticide backbone in this tranche is:

- EFSA OpenFoodTox for public reference-value lookup support
- EFSA food-consumption infrastructure as the primary dataset registry
- DietEx as support-tool metadata
- PRIMo as governed method metadata with the current 3.1 application boundary preserved
- EFSA annual pesticide-residue reporting context as governed public monitoring provenance
- EU official-control sampling and analysis rules kept as separate governed method and legal records where they apply
- EU legal anchors kept separate from guidance and dataset records

JMPR, WHO GEMS/Food, OECD, Codex, and EPA records remain visible as parallel authority and method records. They are not silently merged into EFSA outputs.

## Microplastics boundary

`microplastics_emerging`, `pfas_food_contaminants`, `acrylamide_process_contaminants`, `bisphenol_food_contact_migration`, `cadmium_food_contaminants`, `lead_food_contaminants`, `inorganic_arsenic_food_contaminants`, and `mercury_food_contaminants` are intentionally separate from pesticide-residue workflows.

- It has its own source records, method records, and family metadata.
- Internal review and exploratory use are allowed.
- Submission-oriented use is hard-blocked by default for microplastics and remains review-gated for PFAS, acrylamide, bisphenol, cadmium, lead, inorganic arsenic, and mercury families unless reviewed family-specific method packs are added.
- Cadmium, lead, inorganic arsenic, and mercury now include shared EU official-control method governance, but that does not make them native submission engines or final-decision systems.
- No PRIMo, DEEM, or OpenFoodTox method record is reused as if it were a microplastics-, PFAS-, acrylamide-, bisphenol-, cadmium-, lead-, inorganic-arsenic-, or mercury-native engine.

This is a governance and provenance layer, not a claim that the MCP has a mature microplastics, PFAS, lead, cadmium, acrylamide, BPA, or inorganic-arsenic regulatory engine.

## MCP surfaces

Read-only resources:

- `reference-values://manifest`
- `reference-values://substance/{substance_key}`
- `consumption-datasets://manifest`
- `consumption-datasets://dataset/{dataset_id}`
- `method-registry://manifest`
- `method-registry://method/{method_id}`
- `legal-authorities://manifest`
- `legal-authorities://authority/{authority_id}`
- `reporting-profiles://manifest`
- `reporting-profiles://profile/{profile_id}`
- `reporting-profiles://family/{family_id}`
- `occurrence-evidence://manifest`
- `occurrence-evidence://family/{family_id}`
- `analytical-method-evidence://manifest`
- `analytical-method-evidence://family/{family_id}`
- `metals-occurrence://manifest`
- `metals-occurrence://family/{family_id}`
- `metals-review-focus://manifest`
- `metals-review-focus://family/{family_id}`
- `emerging-contaminants://manifest`
- `emerging-contaminants://family/{family_id}`

Read-only tools:

- `dietary_lookup_reference_values`
- `dietary_lookup_method_support`
- `dietary_lookup_consumption_dataset_support`
- `dietary_lookup_reporting_profiles`
- `dietary_lookup_occurrence_evidence`
- `dietary_lookup_analytical_method_evidence`
- `dietary_check_contaminant_monitoring_import`
- `dietary_export_contaminant_monitoring_interpretation_bundle`
- `dietary_export_contaminant_monitoring_signoff_packet`
- `dietary_export_version_pinned_contaminant_monitoring_review_dossier`
- `dietary_lookup_metals_occurrence`
- `dietary_lookup_metals_review_focus`
- `dietary_export_metals_monitoring_interpretation_bundle`
- `dietary_export_metals_monitoring_signoff_packet`
- `dietary_export_version_pinned_metals_monitoring_review_dossier`

These tools are intended to support review, provenance, and jurisdiction-aware configuration. They do not make final regulatory decisions.

The reporting-profile layer is additive governance metadata. It is intended to keep primary EU reporting bases, compliance-oriented variants, and optional national advisory metrics explicit without silently replacing one with another.

The contaminant-monitoring interpretation bundle does not widen scientific scope beyond the governed evidence registries. It packages the validated monitoring check together with linked evidence, linked review-focus records, and reviewer prompts so downstream review does not need to reconstruct that context manually.

The contaminant-monitoring import check and interpretation bundle now also publish `uncertaintyAndAssumptionLedger`, a structured ledger for review-only governance posture, row-level analytical gaps, lower-bound handling assumptions, and unresolved linkage gaps.

The contaminant-monitoring signoff packet also does not widen scientific scope. It records reviewer actions and waivers on top of the governed interpretation bundle so open blocking items remain explicit instead of disappearing into narrative review notes.

The version-pinned contaminant-monitoring review dossier also does not widen scientific scope. It freezes the exact governed manifests, evidence registries, and workflow documentation used during a contaminant-monitoring review so downstream reviewers can inspect waivers and unresolved blocking follow-up explicitly.

The version-pinned metals review dossier does not widen scientific scope. It freezes the exact governed manifests, workflow documentation, and reviewer decision state that were used during a metals monitoring review so downstream reviewers can inspect waivers and unresolved blocking follow-up explicitly.

The metals monitoring interpretation bundle now also publishes `uncertaintyAndAssumptionLedger`, a structured ledger for review-only governance posture, governed monitoring-context assumptions, trend-signal limits, and unresolved linkage gaps.

`dietary_assess_review_dossier_readiness` now accepts the version-pinned adapter, contaminant-monitoring, and metals-monitoring dossier shapes. Adapter dossiers remain model-governance-driven; contaminant-monitoring and metals-monitoring dossiers are evaluated against their governed emerging-contaminant family snapshots and can use the family-specific readiness profiles published in `regulatory_readiness_profiles.json`.
