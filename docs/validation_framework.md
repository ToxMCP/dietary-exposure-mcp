# Validation Framework

Minimum v0.1 validation covers:

- schema generation and example validation
- defaults-manifest integrity
- deterministic acute and chronic benchmark replication
- transparent uncertainty-assessment checks for two-dimensional Monte Carlo summaries, censored-residue policies, sensitivity ranking, health-reference exceedance, and reproducibility fingerprints
- executable dietary reference-case checks for governed profile selection, canonical commodity coverage, alias resolution, and preferred-profile routing
- negative-path checks for unknown commodities, invalid units, and unsupported profile combinations
- comparison-output transparency for commodity drivers
- PBPK export integrity checks
- adapter normalization checks for PRIMo-/DEEM-shaped tabular payloads
- provisional food-vocabulary and processed-commodity mapping checks
- source-database checks for authority-conflict preservation, EFSA-first pesticide metadata, PFAS provenance, acrylamide, BPA, cadmium, lead, inorganic arsenic, and mercury source coverage, shared EU official-control method governance for metals contaminants, and microplastics hard submission gates
- reporting-profile checks for governed primary EU bases, optional advisory extensions, and non-substitutable profile routing
- occurrence-evidence and analytical-method-evidence checks for governed contaminants-monitoring evidence linkage and official-control context
- contaminant-monitoring import checks for header normalization, evidence matching, reporting-profile surfacing, review-question surfacing, high-attention food detection, and structured uncertainty/assumption ledger generation
- contaminant-monitoring interpretation-bundle checks for packaging validated monitoring imports with linked evidence context, linked review-focus records, reviewer prompts, governance ids, and carried-forward uncertainty/assumption ledgers
- contaminant-monitoring signoff checks for reviewer-facing acknowledgement, waiver, completion, and unresolved-blocking overlays on top of the interpretation bundle, including ledger-derived scientific review actions
- contaminant-monitoring review dossier checks for version-pinned manifest capture and escalation overlays derived from reviewer waivers or unresolved blocking actions, including ledger-derived scientific follow-up
- metals-occurrence registry checks for family-level exposure-report, dataset, legal-anchor, official-control linkage, and interpretation fields such as priority food groups and high-attention foods across cadmium, lead, inorganic arsenic, and mercury
- metals-review-focus registry checks for commodity-group, focus-food, and sensitive-population review context linked back to the governed metals-occurrence records
- metals-monitoring interpretation bundle checks for linked occurrence/focus packaging, reviewer prompts, governance-id coverage, and structured uncertainty/assumption ledgers
- metals-monitoring signoff checks for reviewer-facing acknowledgement, waiver, completion, and unresolved-blocking overlays on top of the interpretation bundle, including ledger-derived scientific review actions
- metals-monitoring review dossier checks for version-pinned manifest capture and escalation overlays derived from reviewer waivers or unresolved blocking actions, including ledger-derived scientific follow-up
- staged interoperability preview checks for governed OHT/IUCLID-aligned JSON mapping profiles
- staged interoperability-readiness checks for governed exchange gates on top of preview outputs
- interoperability-remediation checks for governed action bundles derived from exchange-readiness outcomes
- interoperability-signoff checks for reviewer-facing action-decision packets layered on remediation bundles
- governance-aware dossier readiness checks against fixed EU and family-specific review profiles across adapter, contaminant-monitoring, and metals-monitoring dossiers, including exact ledger-derived scientific follow-up items for monitoring dossier shapes
- readiness queue checks for open, pending, acknowledged, completed, waived, and escalated scientific follow-up action ids on monitoring dossier shapes
- scientific follow-up queue bundle checks for exporting ordered readiness-side follow-up handoffs without reconstructing queue state downstream
- scientific follow-up review board checks for deterministic owner-lane and due-state routing on top of readiness queue bundles
- scientific follow-up owner handoff checks for exporting owner-scoped packets with optional due-state filtering on top of review boards
- scientific follow-up owner remediation checks for exporting deterministic next-step classifications on top of owner-scoped handoff packets
- scientific follow-up owner signoff checks for exporting auditable acknowledgement, completion, and waiver overlays on top of owner remediation packets
- scientific follow-up owner signoff dossier checks for exporting a version-pinned owner-lane audit overlay on top of owner signoff packets and governed source dossiers
- sanitised-public dossier checks for confidential-resource removal, machine-readable redaction markers, retained legal-limit posture on monitoring-derived and owner-lane public handoffs, preserved owner-lane escalation visibility without leaked internal payload fingerprints, and retained jurisdiction-screening semantics on trade-risk public handoffs

Benchmark fixtures in this repository are illustrative screening cases intended to lock contract and arithmetic behavior.

Reference artifacts are published under `validation/v1/`:

- `benchmark_cases.json`
- `dietary_reference_cases.json`
- `commodity_mapping_gap_report.json`
- `adapter_normalization_cases.json`
- `food_vocabulary_cases.json`
- `regulatory_rules.json`
- `source_database_cases.json`
- `survey_distribution_summary_cases.json`
- `probabilistic_intake_summary_cases.json`
- `uncertainty_intake_assessment_cases.json`
- `censored_residue_policy_cases.json`
- `uncertainty_sensitivity_cases.json`
- `health_reference_exceedance_cases.json`
- `uncertainty_reproducibility_cases.json`
- `contaminant_monitoring_check_cases.json`
- `contaminant_monitoring_bundle_cases.json`
- `contaminant_monitoring_signoff_cases.json`
- `contaminant_monitoring_review_dossier_cases.json`
- `metals_monitoring_bundle_cases.json`
- `metals_monitoring_signoff_cases.json`
- `metals_monitoring_review_dossier_cases.json`
- `interoperability_profiles.json`
- `interoperability_preview_cases.json`
- `interoperability_readiness_profiles.json`
- `interoperability_rules.json`
- `interoperability_readiness_cases.json`
- `interoperability_remediation_actions.json`
- `interoperability_remediation_cases.json`
- `interoperability_signoff_cases.json`
- `sanitisation_rules.json`
- `review_dossier_readiness_cases.json`
- `scientific_follow_up_queue_bundle_cases.json`
- `scientific_follow_up_review_board_cases.json`
- `scientific_follow_up_owner_handoff_cases.json`
- `scientific_follow_up_owner_remediation_cases.json`
- `scientific_follow_up_owner_signoff_cases.json`
- `scientific_follow_up_owner_signoff_dossier_cases.json`
- `sanitised_public_review_cases.json`
- `manifest.json`
