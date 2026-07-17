# Interoperability Signoff

Dietary MCP publishes a reviewer-facing signoff packet on top of the interoperability remediation bundle. This layer does not change readiness outcomes or remediation semantics. It records how a reviewer handled each remediation action and keeps any waiver rationale machine-readable.

## Surface

- tool: `dietary_export_interoperability_signoff_packet`
- input dependency: `dietary_export_interoperability_remediation_bundle`
- documentation resource: `docs://interoperability-signoff`

## Decision semantics

Each remediation action can be marked as:

- `pending`
- `acknowledged`
- `completed`
- `waived`

`acknowledged`, `completed`, and `waived` require explicit rationale. `waived` actions remain visible in the packet and are not silently treated as completed.

## Overall packet status

- `open`: one or more actions remain pending or only acknowledged, or a blocking action remains unresolved
- `signed_off`: all actions were completed with no waivers
- `signed_off_with_waivers`: all actions were resolved, but one or more were waived

## Boundary

This packet:

- does not override the underlying readiness assessment
- does not imply XML readiness or submission acceptance
- does not convert a screening engine into a submission-capable engine
- is a review-control artifact for human governance, not an automated approval object
