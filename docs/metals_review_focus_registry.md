# Metals Review Focus Registry

Dietary MCP v0.1 exposes a governed `metals_review_focus_registry.json` pack for cadmium, lead, inorganic arsenic, and mercury. This registry sits on top of the family-level metals-occurrence registry and turns that provenance into reviewer-facing commodity and population focus records.

It does not publish raw occurrence data and it does not create a native metals exposure engine. It publishes governed review-focus records that connect:

- linked metals-occurrence records
- governing EFSA source publications
- governed dataset, method, legal-authority, and reference-value records
- explicit commodity-group, focus-food, and sensitive-population review context

## Scope

Current covered families:

- `cadmium_food_contaminants`
- `lead_food_contaminants`
- `inorganic_arsenic_food_contaminants`
- `mercury_food_contaminants`

Current covered focus areas include:

- cadmium staple plant-food contributors and mollusc-specific follow-up
- lead game meat/offal review and current contributor-group follow-up
- inorganic arsenic rice and rice-based product review
- mercury large predatory fish and sensitive-population fish-advice review

## Record fields

Each record carries additive reviewer context:

- `commodityGroups`
- `focusFoods`
- `sensitivePopulationGroups`
- `linkedOccurrenceRecordIds`
- `reviewQuestions`

These fields are governed review aids. They do not replace the underlying EFSA publications, and they do not authorize submission-oriented use.

## Query model

The lookup surface supports:

- family-level retrieval
- optional `commodityGroup` filtering
- optional `focusFood` filtering

Filtering is still review-oriented. It is not a live search across monitoring datasets.

## Boundary

The registry does not:

- calculate occurrence values
- infer new toxicological reference points
- replace EFSA or EU legal interpretation
- convert a review-required metals family into a submission-capable engine

## MCP surfaces

Read-only resources:

- `metals-review-focus://manifest`
- `metals-review-focus://family/{family_id}`

Read-only tool:

- `dietary_lookup_metals_review_focus`

The lookup result returns governed focus records plus aggregate `overallSubmissionUse` and `submissionCandidateAllowed` posture. In v0.1 all current metals review-focus records remain `review_required`.
