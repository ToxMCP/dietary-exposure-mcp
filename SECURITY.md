# Security Policy

## Supported Versions

The current main branch and the latest tagged release receive security fixes.
Older internal snapshots are unsupported unless a release note says otherwise.

## Reporting a Vulnerability

Use [GitHub private vulnerability reporting](https://github.com/ToxMCP/dietary-exposure-mcp/security/advisories/new).
Do not open public issues with exploit details, tokens, local file paths,
dossier outputs, personal data, or unpublished data. If private reporting is
temporarily unavailable, open a minimal public issue requesting maintainer
contact without including technical details.

## Response Targets

| Severity | Initial response | Target remediation |
| --- | --- | --- |
| Critical | 1 business day | 7 days |
| High | 2 business days | 14 days |
| Medium | 5 business days | 30 days |
| Low | 10 business days | Next planned release |

## Deployment Baseline

Hosted MCP deployment must include transport authentication, tool-level scopes,
origin checks, request size limits, and append-only or tamper-evident audit
logging. Human confirmation is required before a downstream system persists,
publishes, or acts on a returned dossier. Current Dietary MCP tools only return
data and do not themselves write or publish it. Stdio operation is for local
trusted agent use.

The HTTP entrypoint binds to `127.0.0.1` by default and limits request bodies to
1 MiB. Set `DIETARY_MCP_HOST`, `DIETARY_MCP_MAX_REQUEST_BYTES`, and exact
Host/Origin allowlists deliberately at the authenticated gateway.
