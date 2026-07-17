# ADR 0003: Scenario and Semantic Taxonomy

Dietary MCP freezes the following workflow classes for v0.1:

- `point_estimate`
- `bounded_acute`
- `bounded_chronic`

Every scenario must also declare:

- acute or chronic intake semantics
- population group
- body-weight context
- region
- model family
- fit-for-purpose tag

This prevents outputs from implying richer population variability than the implemented math supports.
