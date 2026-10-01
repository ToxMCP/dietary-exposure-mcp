# Changelog

## [Unreleased]

## [0.1.1] - 2026-10-01

- Update the Python MCP SDK to 1.30 and retain bounded HTTP requests and session lifecycle protections.
- Require patched AnyIO, cryptography, PyJWT and settings versions; patch release-tool pip and urllib3.
- Audit the complete frozen runtime, development and release-tool graph.
- Run scientific CI on Node 24 and regenerate release metadata without changing scientific models or qualification boundaries.

Release compatibility: require Starlette 1.7 or later within 1.x and add HTTPX2 to the development extra so the patched AnyIO stack passes warnings-as-errors transport tests.
