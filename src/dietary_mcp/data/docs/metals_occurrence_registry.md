# Metals Occurrence Registry

Dietary MCP v0.1 exposes a governed `metals_occurrence_registry.json` pack for cadmium, lead, inorganic arsenic, and mercury. This registry does not publish a live occurrence database or a new quantitative engine. It publishes reviewed linkage records that connect:

- EFSA dietary exposure or food-risk publications
- governed consumption-dataset context
- shared EU official-control sampling and analysis governance
- current EU contaminants-law anchors

## Scope

Current covered families:

- `cadmium_food_contaminants`
- `lead_food_contaminants`
- `inorganic_arsenic_food_contaminants`
- `mercury_food_contaminants`

Each record is family-level and review-oriented. It is intended to help a downstream reviewer answer:

- which EFSA occurrence or exposure publication is being used
- which dataset metadata record is linked
- which official-control method record applies
- which EU legal anchors were attached
- which reference-value records govern interpretation of the occurrence context
- which food groups or commodities deserve explicit attention during review
- which sensitive population groups should not be collapsed into a generic consumer view
- which review questions should be answered before the record is used in a decision-support bundle
- whether the overall posture is still `review_required`

Commodity- and population-specific follow-up now lives in the separate `metals_review_focus_registry.json` pack so the occurrence manifest can stay family-level and provenance-oriented.

## Interpretation fields

The registry now carries additive interpretation metadata for each family-level record:

- `referenceValueRecordIds`
- `priorityFoodGroups`
- `highAttentionFoods`
- `sensitivePopulationGroups`
- `reviewQuestions`
- `trendSignals`

These fields are governed review aids. They do not create a native contaminant engine and they do not override the source publications they reference.

Current examples:

- cadmium records keep chronic review focused on staple plant-food contributors and separate mollusc attention
- lead records preserve updated contributor and trend-review context, including explicit attention to game meat
- inorganic arsenic records keep rice and rice-based foods explicit rather than hiding them inside broad cereal groupings
- mercury records preserve species-sensitive fish context for high consumers, pregnancy-related advice, and other sensitive groups

## Boundary

The registry does not:

- store raw analytical monitoring datasets
- reproduce EFSA occurrence calculations
- imply that submission-oriented use is allowed
- replace family-specific scientific review

Mercury records preserve fish-and-seafood sensitivity notes and explicit high-attention species context, but that is still provenance and review context. It is not a species-level exposure model.

## MCP surfaces

Read-only resource surfaces:

- `metals-occurrence://manifest`
- `metals-occurrence://family/{family_id}`

Read-only tool:

- `dietary_lookup_metals_occurrence`

The tool returns governed records plus the aggregate `overallSubmissionUse` and `submissionCandidateAllowed` posture. In v0.1 all current metals-occurrence records remain `review_required`.
