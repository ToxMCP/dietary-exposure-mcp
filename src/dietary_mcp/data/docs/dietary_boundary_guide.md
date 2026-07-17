# Dietary Boundary Guide

Dietary Exposure MCP owns food-mediated oral intake workflows only.

## In scope

- commodity residue inputs
- reviewed processing-factor handling
- population consumption profiles
- acute and chronic dietary summaries
- commodity contribution outputs
- PBPK-ready oral dose exports for dietary scenarios

## Out of scope

- direct-use oral product scenarios
- medicinal TCM regimens and product-centric supplement dosing
- environmental-media oral intake outside food-mediated semantics
- PBPK execution
- final regulatory decisions
- mandatory proprietary survey dependencies in v0.1

## Herbal and supplement split

- TCM pills, decoctions, tinctures, and other therapeutic herbal regimens do not belong in
  Dietary MCP when the workflow is product-centric or prescribed direct-use dosing.
- Topical or inhaled herbal preparations do not belong in Dietary MCP.
- Herbal teas, food-like botanicals, and nutrition-style supplement intake do belong here when
  the workflow is food-mediated consumption.

## Environmental-media oral seam

Environmental-media oral intake from water or soil is not treated as a Dietary MCP workflow by
default. That future seam should start from Fate MCP `concentration_surface` outputs and only
enter Dietary MCP when food-mediated residue and consumption semantics actually apply.
