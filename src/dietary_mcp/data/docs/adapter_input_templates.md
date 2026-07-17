# Adapter Input Templates

Dietary MCP publishes read-only adapter input templates for synthetic PRIMo- and DEEM-aligned imports.

## Resources

- `adapter-input-templates://manifest`
- `adapter-template://{template_name}`
- `adapter-import-walkthroughs://manifest`
- `adapter-walkthrough://{walkthrough_name}`

## Tool

- `dietary_check_adapter_import`
- `dietary_compare_adapter_import_to_walkthrough`
- `dietary_export_adapter_review_bundle`
- `dietary_export_version_pinned_adapter_review_dossier`
- `dietary_assess_review_dossier_readiness`
- `dietary_export_interoperability_preview`
- `dietary_assess_interoperability_preview_readiness`

## Current templates

- `efsa_primo_tabular_template`
- `epa_deem_csv_template`

Each template manifest entry includes a `walkthroughName` pointing to a validated normalization example.

Use `dietary_check_adapter_import` when you want to validate prepared CSV text against the published headers and obtain the same stable normalized projection described by the walkthrough resources.

Use `dietary_compare_adapter_import_to_walkthrough` after that check when you want a governed diff against a published walkthrough baseline.

Use `dietary_export_adapter_review_bundle` when you need to hand off the checked result and governed diff as one auditable review package.

Use `dietary_export_version_pinned_adapter_review_dossier` when that handoff package also needs release metadata hashes plus exact template and walkthrough manifest fingerprints.

Use `dietary_assess_review_dossier_readiness` after dossier export when the review handoff needs a machine-readable status such as internal-review-ready, consultation-only, or blocked as a submission candidate.

Use `dietary_export_interoperability_preview` when reviewers need a validation-only OHT/IUCLID-aligned JSON projection with explicit unsupported-field reporting before any future downstream export work.

Use `dietary_assess_interoperability_preview_readiness` when that staged JSON preview needs a governed exchange-gate status such as internal exchange, consultation exchange, or blocked pre-XML candidate.

These files are illustrative compatibility templates. They document accepted header aliases and example row layouts for the adapter harness, but they are not official PRIMo or DEEM exchange formats.
