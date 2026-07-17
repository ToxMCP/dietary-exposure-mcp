# Contaminant Monitoring Interpretation Bundle

The `dietary_export_contaminant_monitoring_interpretation_bundle` workflow packages a validated contaminant-monitoring import check with governed evidence context and reviewer prompts.

## Inputs

- a `contaminantMonitoringImportCheckResult`
- an optional bundle note

The bundle is intentionally downstream of `dietary_check_contaminant_monitoring_import`. It does not parse raw CSV text directly.

## Output shape

The bundle preserves:

- the original monitoring check result
- the carried-forward `reportingProfileSummary` when the monitoring check matched governed reporting conventions
- linked occurrence-evidence records
- linked analytical-method-evidence records
- linked metals review-focus records when the check result references them
- covered source, method, legal-authority, dataset, and reference-value identifiers
- a carried-forward `uncertaintyAndAssumptionLedger` from the monitoring check, plus any unresolved review-focus linkage gaps
- reviewer prompts derived from occurrence context, analytical-method summaries, quality flags, linked review-focus records, and any reporting-convention non-substitution posture
- audit-ready MCP resource references to the supporting manifests and operator documentation

## Current scope

In v0.1 this workflow is governed for:

- pesticide residues
- PFAS
- acrylamide
- BPA food-contact dietary context
- cadmium
- lead
- inorganic arsenic
- mercury

If a linked review-focus id cannot be resolved from the governed defaults pack, the bundle keeps that id in `unresolvedLinkedReviewFocusIds` and stays review-oriented.

## Boundary

This bundle is not a native exposure engine and it does not produce final regulatory decisions.

- It supports interpretation and review of contaminants-monitoring inputs.
- It preserves official-control and evidence context without pretending to execute laboratory methods.
- It keeps primary-vs-optional reporting conventions explicit when governed reporting profiles apply.
- It keeps submission posture explicit through `overallSubmissionUse` and `submissionCandidateAllowed`.

The intended use is internal review, reviewer preparation, and auditable handoff into downstream signoff or dossier workflows.
