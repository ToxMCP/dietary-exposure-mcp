# Acute vs Chronic Guide

Dietary MCP does not treat acute and chronic outputs as interchangeable.

- `acute` means short-window dietary intake using acute consumption semantics.
- `chronic` means repeated or average daily dietary intake using chronic consumption semantics.
- `point_estimate` scenarios can be declared acute or chronic, but the declared window is always explicit.
- `bounded_acute` and `bounded_chronic` scenarios surface lower and upper intake bounds whenever the residue profile carries explicit bounds.

If a bounded workflow is requested without explicit residue bounds, Dietary MCP keeps lower and upper equal to the point estimate and emits a limitation note rather than inventing a hidden probabilistic spread.
