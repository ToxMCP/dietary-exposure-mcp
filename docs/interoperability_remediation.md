# Interoperability Remediation

Dietary MCP publishes a governed remediation bundle on top of the interoperability readiness assessment. This layer does not change the staged preview or dossier. It converts triggered readiness rules into machine-readable review actions so downstream teams can see what must be fixed, reviewed, or documented before reconsidering the selected exchange gate.

## Surface

- tool: `dietary_export_interoperability_remediation_bundle`
- follow-on tool: `dietary_export_interoperability_signoff_packet`
- catalog resource: `interoperability-remediation://catalog`
- action resource: `interoperability-remediation://action/{action_id}`
- validation resource: `validation://interoperability-remediation-actions`

## Bundle contents

Each remediation bundle includes:

- the selected interoperability readiness profile
- the linked dossier-readiness profile and observed status
- ordered remediation items derived from triggered blocking and warning rules
- blocking and warning action counts
- a recommended action sequence
- linked documentation and governed resource URIs

Remediation items are governed catalog entries keyed by readiness `ruleId`. If a rule is triggered without a published remediation action, Dietary MCP emits a generic review item instead of silently dropping the rule.

## Current intent

This layer is designed for:

- internal exchange-review triage
- consultation-oriented package cleanup
- explicit remediation handoff between technical operators and regulatory reviewers

It is not an automated waiver system and it is not a substitute for human assessment of exchange suitability.

## Boundary

This remediation layer:

- does not imply XML readiness
- does not imply IUCLID or OHT completeness
- does not override dossier-readiness governance
- does not claim that resolving the listed actions is sufficient for formal submission

Use the signoff packet when a reviewer needs to acknowledge, complete, or waive the resulting action list with explicit rationale.
