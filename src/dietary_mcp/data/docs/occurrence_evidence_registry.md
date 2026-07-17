# Occurrence Evidence Registry

`occurrence_evidence_registry.json` publishes governed occurrence-evidence objects for contaminant monitoring review.

These records are not raw monitoring databases. They package:

- the contaminant family
- analyte and matrix-group scope
- the governed occurrence record ids they summarize
- linked dataset, legal, method, and reference-value ids
- linked metals review-focus ids
- linked reporting-profile ids where review outputs may need more than one governed reporting convention
- review-only submission posture

Use this registry when you need a stable evidence object that explains why a monitoring table is relevant, which governed records it depends on, and which review-focus records should be considered during interpretation.

Current v0.1 scope:

- pesticide residues monitoring context for governed glyphosate, acetamiprid, imidacloprid, ethiprole, tetraconazole, tebuconazole, glufosinate, oxamyl, spirotetramat, and difenoconazole review
- cadmium
- lead
- inorganic arsenic
- mercury
- PFAS, including matrix-specific egg, fish, and dairy review contexts
- acrylamide, including fried-potato and coffee-product review context
- BPA food-contact dietary context, including canned-food and beverage review context

Not yet represented in this registry:

- microplastics, because the current family is still governed primarily as an evidence-maturity and method-limit layer rather than as a structured occurrence-evidence pack

Current limitations:

- review-oriented provenance only
- no live occurrence database ingestion
- no automatic lower-bound or upper-bound exposure calculation
- no final regulatory decision semantics
- reporting-profile ids are metadata only and do not execute aggregate calculations by themselves
