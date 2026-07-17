# ADR 0001: Dietary Boundary

Dietary MCP is the ToxMCP service for food-mediated oral intake only.

## Decision

The module owns commodity residue inputs, governed food-consumption profiles, dietary intake summaries, commodity contribution outputs, and PBPK-ready oral dose exports for dietary scenarios.

The module does not own direct-use oral product scenarios, environmental-media oral intake
outside food-mediated semantics, PBPK execution, or final regulatory decisions.

## Consequence

Direct-use oral questions must be routed to Direct-Use Exposure MCP rather than being normalized
inside Dietary MCP.
This includes medicinal TCM regimens and product-centric supplement dosing, even when they are
in pill or capsule form.
Environmental-media oral intake from water or soil should start from Fate MCP concentration
outputs and remain outside Dietary MCP unless the workflow becomes food-mediated.
