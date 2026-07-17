# Analytical Method Evidence Registry

`analytical_method_evidence_registry.json` publishes governed analytical-method evidence objects for contaminant monitoring review.

These records are intended to preserve method-review context, including:

- analyte and matrix-group scope
- technique summary
- LOQ and LOD context
- recovery and measurement-uncertainty context
- sampling-plan and storage-stability notes
- linked governed method and legal-authority ids
- linked reporting-profile ids where the method context should travel with more than one governed reporting basis

The registry is not a laboratory execution engine. It does not run analytical methods or certify fitness automatically. It exposes method-review context so imports, review bundles, and downstream packets can preserve the official-control boundary explicitly.

Current v0.1 scope:

- pesticide residue monitoring and analytical review context for governed glyphosate, acetamiprid, imidacloprid, ethiprole, tetraconazole, tebuconazole, glufosinate, oxamyl, spirotetramat, and difenoconazole examples
- cadmium
- lead
- inorganic arsenic
- mercury
- PFAS monitoring context, including matrix-specific egg, fish, and dairy review layers
- acrylamide monitoring and mitigation context, including fried-potato and coffee-product review
- BPA food-contact review context, including canned-food and beverage review

Current limitations:

- summary evidence only
- storage-stability linkage remains external
- no automatic matrix-specific method selection
- no final submission-capability claim
- reporting-profile linkage does not imply an embedded aggregation or equivalency calculator
