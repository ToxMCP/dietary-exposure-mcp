# Contaminant Monitoring Import

`dietary_check_contaminant_monitoring_import` validates contaminant-monitoring CSV input against governed occurrence-evidence and analytical-method-evidence records.

Accepted header aliases include:

- `commodity`, `food`, `matrix`, `product`
- `analyte`, `substance`, `contaminant`
- `result`, `concentration`, `result_value`
- `unit`, `result_unit`, `concentration_unit`
- optional `lod`, `loq`, `recovery_percent`, `measurement_uncertainty_percent`, `sampling_year`

The checker returns:

- header resolution
- a stable normalized projection
- matched occurrence-evidence records
- matched analytical-method-evidence records
- applicable reporting-profile ids
- linked review-focus ids
- high-attention food hits
- required review questions
- a structured `uncertaintyAndAssumptionLedger`
- review-only status and coverage notes

Current v0.1 scope is limited to:

- pesticide residues for governed glyphosate, acetamiprid, imidacloprid, ethiprole, tetraconazole, tebuconazole, glufosinate, oxamyl, spirotetramat, and difenoconazole monitoring review
- cadmium
- lead
- inorganic arsenic
- mercury
- PFAS, including matrix-specific egg, fish, and dairy review context
- acrylamide, including fried-potato and coffee-product review context
- BPA food-contact dietary review, including canned-food and beverage context

Not yet represented in this workflow:

- microplastics, because the family is still governed primarily as an evidence-maturity and method-limit layer rather than as a structured monitoring-import pack

Current limitations:

- review-only
- no native exposure calculation
- no live regulatory database connectivity
- no automatic acceptance of submission readiness

The structured ledger is intended to keep analytical gaps explicit. It records items such as incomplete row-level LOD/LOQ or measurement-uncertainty coverage, lower-bound handling assumptions taken from governed occurrence evidence, storage-stability and sampling-plan context taken from governed analytical-method evidence, and review-only governance posture.

For PFAS, the checker can now surface both the primary EU EFSA-4 reporting basis and optional national advisory extensions, such as the Dutch RIVM PEQ-style home-egg and fish and biota profiles, through `applicableReportingProfileIds`. Those ids are governance metadata and do not imply that Dietary MCP is executing the underlying aggregate metric directly.

When reporting profiles are applicable, the check result also exposes a structured `reportingProfileSummary` that separates the recommended primary EU basis from optional advisory extensions, compliance variants, supporting-detail profiles, and active non-substitution links.
