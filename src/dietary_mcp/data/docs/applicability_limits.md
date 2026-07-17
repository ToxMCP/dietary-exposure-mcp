# Applicability Limits

Dietary Exposure MCP v0.1 is appropriate for:

- deterministic screening-style dietary intake summaries
- bounded summaries when residue bounds are explicit
- transparent two-dimensional uncertainty intake assessments with explicit residue models, survey-design assumptions, censored-data policy, and reproducibility fingerprints
- downstream PBPK dose handoff after dietary normalization
- additive adapter-harness normalization for PRIMo- or DEEM-aligned workflows when the output is explicitly treated as contract-compatibility testing

Dietary Exposure MCP v0.1 is not sufficient on its own for:

- final pass/fail regulatory conclusions
- hidden or undocumented probabilistic inference, including unreported censored-data substitution or unreported survey-weight assumptions
- official equivalence to PRIMo, DEEM, DietEx, or other external regulatory engines without a separate curated cross-engine benchmark package
- unsupported or unreviewed commodity taxonomy expansion
- arbitrary spreadsheet ingestion without validation
- claiming official equivalence to PRIMo, DEEM, or other external engines from the built-in harness families
- treating governance-aware readiness assessment as final regulator acceptance
