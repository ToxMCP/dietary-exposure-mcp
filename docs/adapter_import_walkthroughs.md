# Adapter Import Walkthroughs

Dietary MCP publishes governed adapter walkthroughs that pair each packaged import template with a validated normalized-summary projection.

## Resources

- `adapter-import-walkthroughs://manifest`
- `adapter-walkthrough://{walkthrough_name}`

## Tool

- `dietary_check_adapter_import`
- `dietary_compare_adapter_import_to_walkthrough`
- `dietary_export_adapter_review_bundle`
- `dietary_export_version_pinned_adapter_review_dossier`
- `dietary_export_sanitised_public_review_dossier`
- `dietary_assess_review_dossier_readiness`
- `dietary_export_interoperability_preview`
- `dietary_assess_interoperability_preview_readiness`

## What each walkthrough includes

- Template linkage through `templateName` and `templateResourceUri`
- The exact sample input used for the walkthrough, as rows or CSV text
- Header-to-canonical field resolution for the example input
- The declared external totals supplied to the harness
- A stable `expectedNormalizedProjection` built from the normalized dietary summary without runtime-generated IDs or timestamps
- Validation expectations and pass/fail checks derived from the governed adapter normalization cases

## Intended use

Use these walkthroughs to prepare import files that match the published templates, then compare the resulting normalized output to the stable projection fields before wiring a real external import path.

When you already have a prepared CSV file or CSV text payload, use `dietary_check_adapter_import` to run the same compatibility normalization path and return a stable projection without runtime-generated IDs or timestamps.

Then use `dietary_compare_adapter_import_to_walkthrough` to compare that checked result against one of the governed walkthroughs and get a focused diff over totals, canonical commodities, contribution values, dominant contributors, required source IDs, required quality flags, and unmapped headers.

When food-vocabulary mappings are available for the resolved commodities, the walkthrough projection and focused diff also retain the optional `foodex2_code`, `rpc_code`, `rpcd_code`, `processed_status`, and `mapping_confidence` fields without changing the canonical commodity identifiers.

Finally, use `dietary_export_adapter_review_bundle` to package the check result, focused diff, and referenced template and walkthrough URIs into one auditable review handoff object.

When reviewers need the exact release context as well, use `dietary_export_version_pinned_adapter_review_dossier` to pin the handoff bundle to the release metadata hashes and the exact template and walkthrough manifest fingerprints used during the review.

If the resulting dossier needs a non-confidential handoff form, use `dietary_export_sanitised_public_review_dossier` to derive a sanitised-public package that retains governed provenance and retained fingerprints while removing confidential resources and emitting explicit redaction markers.

Then use `dietary_assess_review_dossier_readiness` to evaluate that version-pinned dossier against a governed readiness profile such as `eu_internal_review`, `eu_submission_candidate`, or `eu_consultation_exploratory`.

If the dossier is being staged for future interoperability work rather than reviewed as an MCP-native handoff, use `dietary_export_interoperability_preview` to produce a validation-only OHT/IUCLID-aligned JSON preview with missing-required-field and unsupported-field reporting.

Then use `dietary_assess_interoperability_preview_readiness` to evaluate that staged preview against a governed exchange gate such as `eu_internal_exchange_preview`, `eu_consultation_exchange_preview`, or `eu_submission_xml_candidate`.

These walkthroughs validate the harnessed compatibility pathway only. They do not represent official PRIMo or DEEM engine exports.
