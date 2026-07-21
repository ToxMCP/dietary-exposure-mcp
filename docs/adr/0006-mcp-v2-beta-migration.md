# ADR 0006 - Opt-in MCP Python SDK v2 beta migration

Status: Proposed
Date: 2026-07-17
Supersedes: none

## Context

Dietary Exposure MCP v0.1.0 is a production candidate on the stable MCP Python
SDK line (`mcp[cli]>=1.28.1,<2`). The stable line receives critical security
fixes and is the correct release target while v2 remains a prerelease.

MCP Python SDK v2 supports the `2026-07-28` protocol era and makes intentional
breaking changes. The current beta must be explicitly and exactly pinned. This
ADR prepares a separate migration branch; it does not authorize changing the
v0.1.0 release branch or publishing beta-dependent artifacts.

Primary references:

- [MCP Python v2 migration guide](https://py.sdk.modelcontextprotocol.io/v2/migration/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP 2026-07-28 release candidate](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/)
- [MCP package releases](https://pypi.org/project/mcp/)

## Decision

1. Release v0.1.0 from the stable-v1 branch only.
2. Start v2 work from that verified baseline on a separate
   `codex/dietary-mcp-v2-beta` branch.
3. Pin `mcp[cli]==2.0.0b2` exactly and update one prerelease at a time. Do not pin
   `mcp-types` independently; the SDK pins its matching version.
4. Do not publish, tag, or merge the v2 branch until all gates below pass and the
   SDK version is explicitly approved.
5. Treat MCP transport/API changes as infrastructure only. Scientific models,
   algorithms, defaults, evidence, schemas, and governed output semantics must
   remain unchanged unless reviewed as a separate scientific change.

## Repository impact

The expected first-pass changes are narrow but breaking:

| Area | Current v1 use | Required v2 move |
|---|---|---|
| Server | `mcp.server.fastmcp.FastMCP` | `mcp.server.mcpserver.MCPServer` |
| Wire types | `mcp.types` | `mcp_types` |
| Type fields | `isError`, `structuredContent`, `inputSchema`, hint fields | snake_case Python fields; camelCase remains wire-only |
| Tests | `call_tool()` tuple/legacy result assumptions | assert the v2 `CallToolResult` contract |
| Transport | HTTP options passed to the constructor | pass options to `run()` or `streamable_http_app()` |
| Identity | private v1 version shim | public `MCPServer(..., version=VERSION)` |
| Client | explicit `initialize()` only | test `server/discover` auto mode and legacy mode |

Files in the direct MCP blast radius:

- `src/dietary_mcp/server.py`
- `src/dietary_mcp/server_tools.py`
- `src/dietary_mcp/server_resources.py`
- `src/dietary_mcp/tool_surface_validation.py`
- `src/dietary_mcp/transport/http.py`
- `tests/test_server_surface.py`
- `tests/test_mcp_conformance.py`

## Migration sequence

1. Record the stable baseline: package hashes, 49 tool names, 34 direct resource
   URIs, schemas, examples, release dossier, and all validation counts.
2. Apply the exact beta pin and regenerate the lockfile in the v2 branch only.
3. Make mechanical imports and snake_case field changes. Preserve every public
   wire name and schema unless a reviewed MCP protocol change requires otherwise.
4. Move `json_response`, `stateless_http`, request-body limits, and transport
   security to `run()` / `streamable_http_app()` calls.
5. Remove the v1 server-version shim and pass `version=VERSION` publicly.
6. Audit shared state for worker-thread safety before accepting v2's concurrent
   execution of synchronous handlers. In particular, inspect `DietaryRuntime`,
   `DefaultsRegistry`, release-report caches, and every artifact-writing tool.
7. Port tests to v2 return values and snake_case Python attributes.
8. Add modern and legacy protocol tests, then run every engineering, security,
   scientific, packaging, and reproducibility gate.

## Security gates

- Keep HTTP fail-closed. Starting without explicit remote-transport approval must
  fail; production HTTP remains behind an authenticated gateway.
- Keep DNS-rebinding protection and exact Host/Origin allowlists. Test accepted
  and rejected values against the live ASGI app.
- Decide the HTTP request-body limit explicitly. V2 defaults to 4 MiB while the
  model's hard CSV ceiling is 5,000,000 characters. Either lower the scientific
  input ceiling or set the smallest transport limit that safely contains it,
  including JSON overhead; test both 413 and domain-limit behavior.
- Verify required `Mcp-Method`, `Mcp-Name`, and parameter headers are checked
  against the JSON body. Mismatches must fail.
- Review OpenTelemetry defaults before enabling an exporter. Raw exposure inputs,
  evidence payloads, confidential fields, and tokens must not enter span names,
  attributes, logs, or error events.
- Repeat `pip-audit`, Trivy, Bandit, Gitleaks, SBOM generation, Twine checks, and a
  clean-wheel import on the exact beta lock and artifacts.
- Exercise malformed JSON-RPC, unknown methods, oversized bodies, duplicate IDs,
  cancellations, timeouts, and parallel requests.

## Protocol compatibility gates

- Modern stdio and HTTP clients must succeed through `server/discover` using
  `2026-07-28` with no initialize handshake or `Mcp-Session-Id`.
- Legacy clients must still complete `initialize` and preserve the same 49-tool
  and 34-resource surface where the SDK promises fallback.
- Stateless HTTP requests must work on independent server instances without
  process-local session state.
- Tool errors must preserve the existing structured dietary error payload and
  request ID while using v2's `is_error` / `structured_content` API.
- Tool input/output schemas and resource/template URIs need a reviewed semantic
  diff against the stable baseline.

## MRTR decision

Do not add Multi Round-Trip Requests during the mechanical migration. Current
Dietary tools are deterministic and do not need elicitation, sampling, or roots
mid-call. Adding MRTR without a scientific workflow would increase state,
security, and compatibility risk without improving the release.

Any later MRTR proposal must be separate and must define:

- a real reviewed use case, such as explicit human confirmation of a signoff;
- bounded, versioned, integrity-protected, expiring `requestState` with no secrets;
- idempotent retry behavior and replay protection;
- client capability fallback and cancellation behavior;
- scientific provenance showing which human/client response affected the result.

## Scientific equivalence gates

- All 14 schema-spine projected objects must remain blocker-free.
- All 455 cases across 35 validation suites must pass with zero warnings.
- All 320+ engineering tests, including adversarial scientific tests, must pass.
- Generated schemas, examples, defaults, validation artifacts, and downstream dry
  runs must have no unexplained semantic drift.
- The scientific-review dossier must remain `draft_ready`; external scientific
  expert review and signoff are still required before promoting review-gated
  records or making stronger scientific-validation claims.
- Run concurrent calls against representative lookup, deterministic calculation,
  probabilistic, and artifact-writing tools. Results must be deterministic and
  isolated, with no cache contamination or file races.

## Exit and rollback

The v2 branch is mergeable only when all gates pass on an exact approved SDK pin,
the migration diff is reviewed, and stable-v1 clients have a tested fallback or a
documented support decision. Rollback is the verified v0.1.0 stable-v1 artifact;
the beta branch must never overwrite or retag that release.

Estimated focused effort for Dietary after v0.1.0 is frozen: one to two days for
the mechanical beta port, two to four days for transport/concurrency/security
hardening, and one to two days for scientific equivalence review. Beta changes or
new findings can extend that range.
