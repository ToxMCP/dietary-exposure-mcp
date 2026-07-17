# PESS Dietary Module vs Dietary Exposure MCP

This note positions Dietary Exposure MCP against the dietary component of the PESS pesticide exposure scenario generator described in:

- Falakdin et al. (2026), *Modeling external exposure to pesticides in human populations: Developing an exposure scenario generator*, Ecotoxicology and Environmental Safety 318, 120201.

It is written for reviewers who need to understand whether the MCP is trying to reproduce PESS, replace PRIMo or DEEM, or provide a different infrastructure layer.

## Verdict

PESS is a pesticide exposure scenario simulator. Its dietary module combines EFSA food consumption data with EFSA pesticide residue data, runs Monte Carlo dietary exposure distributions, and compares the route-level output against biomonitoring-derived plausibility ranges.

Dietary Exposure MCP is a governed dietary exposure evidence layer. It packages food-mediated oral intake assumptions, commodity residue inputs, consumption mappings, uncertainty policies, MRL and tolerance checks, quality flags, provenance, review artifacts, and PBPK-ready oral dose handoffs.

The overlap is the core arithmetic:

```text
food consumption x residue concentration / body weight = dietary exposure
```

The difference is the public contract. PESS publishes an end-to-end pesticide simulation case study. Dietary Exposure MCP publishes auditable, machine-readable dietary evidence objects and handoff contracts.

## PESS Strengths To Respect

- PESS has a peer-reviewed pesticide case study using endosulfan, mancozeb, and glyphosate.
- It demonstrates EFSA-style consumption plus residue integration across age groups, food categories, pesticides, and years.
- It explicitly produces dietary distributions and route-level exposure comparisons.
- It includes biomonitoring-derived plausibility comparison, while acknowledging that back-calculated biomonitoring estimates are not strict external-dose validation.

These are scientific storytelling strengths. Dietary Exposure MCP should not frame itself as "better PESS." It should show that PESS-like dietary questions can be represented as governed, inspectable, interoperable evidence objects.

## Dietary MCP Strengths

- Deterministic-first Tier 1 intake summaries with acute and chronic semantics.
- Governed survey distribution and cohort-bootstrap support without making broad probabilistic-equivalence claims.
- Explicit censored-residue policies for lower-bound, middle-bound, upper-bound, and three-bound sensitivity handling.
- First-class processing factors, including processed-commodity mappings such as apple juice to apples.
- MRL, tolerance, reference-value, and trade-risk review lanes.
- Versioned defaults, source registries, schemas, validation dossiers, quality flags, and provenance bundles.
- PBPK-ready oral input export without executing PBPK or claiming internal-dose authority.
- Clear suite boundaries: Fate emits concentration surfaces, Direct-Use Exposure handles product-centric and environmental-media dose bridges, and Dietary owns food-mediated oral intake.

## Gap Matrix

| Dimension | PESS dietary module | Dietary Exposure MCP v0.1 position | Gap or action |
| --- | --- | --- | --- |
| Primary identity | Dietary module inside pesticide simulator | Standalone governed dietary evidence MCP | Keep positioning generous and non-competitive. |
| Chemical scope | Pesticides | Pesticides, contaminants, metals, broader food-mediated oral evidence | Highlight generality without overclaiming completeness. |
| Public case study | Endosulfan, mancozeb, glyphosate | Glyphosate public-source slice case pack | Expand later to mancozeb/endosulfan. |
| Consumption source | EFSA food consumption data | Governed profiles and survey workflows with EFSA source registry support | Do not claim row-level EFSA reproduction unless data rows are locked. |
| Residue source | EFSA pesticide monitoring data | Governed residue inputs, occurrence/method evidence, MRL records | Add curated public-source slices before claiming external dataset replication. |
| Probabilistic method | Monte Carlo using consumption and residue distributions | Deterministic-first plus governed survey/bootstrap and uncertainty lanes | Use explicit limitations and censored-data policy outputs. |
| Negative values | Normal consumption sampling can create impossible negatives, then truncates | Non-negative input validation and clipped residue draws | Use this as a cautionary method distinction. |
| Processing factors | Set to 1 in reported dietary calculations | Processing factors are public fields and governed defaults | Demonstrate processed derivative handling in examples. |
| Biomonitoring | Plausibility comparison included | Not native | Route future work to a Biomonitoring or Reverse Exposure MCP. |
| PBPK | Future integration direction | PBPK-ready oral handoff already exposed | Keep PBPK execution outside Dietary MCP. |

## Recommended Public Demo

The first case pack should be a small public-source glyphosate slice, not a full EFSA data replica. It should show the same type of dietary question PESS addresses while staying honest about source granularity:

- glyphosate as the chemical identity
- apple juice and rice as commodity inputs
- governed processing factor for apple juice
- adult chronic deterministic intake
- child acute bounded intake
- raw-survey distribution and cohort-bootstrap support
- censored-residue uncertainty assessment with three-bound sensitivity
- cross-jurisdiction trade-risk posture
- PBPK-ready oral dose export
- explicit limitations that residue values are screening inputs, not EFSA row-level monitoring records

The checked-in example lives at:

- `examples/pesticide_pess_style/glyphosate_public_slice/`

## Suite Boundary Appendix

For a PESS-style route story, do not merge all route logic into Dietary MCP.

- Fate MCP owns environmental release and concentration surfaces.
- Direct-Use Exposure MCP owns product-centric direct-use oral, inhalation, dermal, worker, and bounded environmental-media concentration-to-dose bridges.
- Dietary MCP owns food-mediated residue plus consumption workflows.
- PBPK MCP owns internal dose and toxicokinetics after an external dose is defined.

The first glyphosate case pack is Dietary-led. A future three-module demo can compare a Fate concentration precursor, a Direct-Use/Exposure environmental-media oral bridge, and a Dietary food-mediated oral packet, but that should be a separate orchestration example.

## One-Sentence Positioning

PESS is a pesticide exposure scenario simulator; Dietary Exposure MCP is a governed dietary exposure evidence layer that can represent, audit, validate, and hand off PESS-like dietary calculations as regulator-readable computational objects.
