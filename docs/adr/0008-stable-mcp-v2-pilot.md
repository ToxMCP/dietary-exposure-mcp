# ADR 0008 - Stable MCP SDK v2 compatibility pilot

Status: Accepted for the Dietary pilot; rollout follows compatibility review
Date: 2026-10-01
Supersedes: ADR 0006's prerelease SDK and branch decisions

Dietary v0.1.1 is the released rollback baseline. The maintainer approved a
separate SDK v2 pilot after the maintenance/security releases. SDK 2.2.0 is
stable and includes the current HTTP-body, session-retention, OAuth-client,
and schema-reference security fixes. Pin `mcp[cli]==2.2.0` exactly; allow its
matching `mcp-types` dependency to resolve through the frozen lockfile.

The application candidate is v0.2.0. Its 49 tools, 34 fixed resources, 32
templates, scientific schemas, algorithms, defaults, units, review flags and
screening scope retain their v0.1.1 contracts. The Python integration API uses
`MCPServer` and snake_case SDK result attributes. `create_server()` builds the
shared tool/resource surface; HTTP settings now belong to `create_http_app()`
or the SDK's public transport factories. Code importing SDK v1 types or
passing HTTP keywords to `create_server()` requires adaptation. Normal MCP
host configurations keep their existing console commands and endpoint paths.

The same HTTP endpoint supports `2026-07-28` discovery and older initialization
handshakes. Production HTTP stays stateless, loopback by default, fail-closed
without explicit gateway configuration, and bounded to 1 MiB. This transport
limit retains the released behavior and can reject inputs below the separate
scientific CSV ceiling. The SSE compatibility entrypoint retains its paths
and receives explicit Host/Origin allowlists and a body limit.

Only catalog listings receive 60-second **private** cache hints. Results and
resource contents remain uncached. No exporter or OpenTelemetry SDK is added;
the API dependency uses no-op tracing without an externally configured
provider. Configuring telemetry export requires a separate review of error
events and request metadata. Do not export confidential inputs or exception
messages by turning on an external provider without that review.

Synchronous handlers now execute in SDK worker threads. Runtime plugin and
default indexes are constructed before dispatch; request methods use local
working collections and seeded local random generators. MCP exports return
payloads. They do not invoke artifact/report writers. Tests cover parallel
seeded calculations and exports, result isolation, and unchanged generated
files. Release-resource reads serialize expensive report-cache fills within
each server so concurrent requests cannot duplicate that work. CLI artifact
generation remains an explicit maintenance operation.

The compatibility gate runs actual SDK 1.30 and SDK 2.2 clients in separate
environments and compares catalogs and seven calculation/export workflows.
Catalog SHA-256 fixtures originate from the released v0.1.1 wheel, rather
than regenerated expected schemas. Comparisons exclude only per-invocation
timestamps and trace IDs. Release acceptance additionally compares the
candidate with the released wheel and exercises stdio and HTTP.

Retain all existing scientific, engineering, security, packaging and
reproducibility gates. Keep OpenFoodTox records `review_required` and
independent scientific promotion/signoff pending. Do not publish under the
existing v0.1.1 tag. A rollback reinstalls its original wheel and checksums.

Multi-round-trip workflows, MCP Apps, subscriptions and Tasks are separate
feature decisions. This migration does not advertise those features or
change scientific workflow design. Apply the pilot pattern to other MCPs
only after their own SDK, language and transport compatibility review.

References:

- [SDK v2 migration](https://py.sdk.modelcontextprotocol.io/migration/)
- [Legacy client serving](https://py.sdk.modelcontextprotocol.io/run/legacy-clients/)
- [Modern HTTP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [SDK security advisories](https://github.com/modelcontextprotocol/python-sdk/security/advisories)
