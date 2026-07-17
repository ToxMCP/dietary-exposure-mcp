# Adapter SPI

Dietary MCP publishes a stable scenario-level plugin boundary for future PRIMo- or DEEM-aligned adapters.

## Contract rule

Adapters must consume and emit the public dietary contracts, not adapter-native payloads.

## Declared model families

- `reference_dietary`: native first-party deterministic kernel
- `adapter_stub`: generic extension-harness family
- `efsa_primo_adapter`: PRIMo-aligned harness family
- `epa_deem_adapter`: DEEM-aligned harness family

## Minimum adapter responsibilities

- accept `dietaryIntakeScenarioDefinition`
- preserve `acute` versus `chronic` semantics explicitly
- emit `dietaryIntakeSummary`
- preserve assumption records, quality flags, and limitation notes
- avoid hidden probabilistic behavior unless the scenario class and contract version explicitly support it
- declare official metadata sources and applicability limits when the family name references an external engine

## v0.1 reference behavior

- `adapter_stub`, `efsa_primo_adapter`, and `epa_deem_adapter` currently reuse the reference deterministic kernel so extension points can be tested without changing public schemas.
- These harness families normalize through public contracts and official source metadata, but they do not claim equivalence to external proprietary engines or regulatory implementations.
- The internal harness input shape is documented in `docs/adapter_harness_inputs.md` for maintainers extending the adapter boundary.
