# Limitations

This case pack is a public-source slice for demonstrating Dietary Exposure MCP governance. It is not a full PESS reproduction.

## Explicit Non-Claims

- The residue values are illustrative regulatory-screening inputs, not row-level EFSA monitoring records.
- The apple-juice lane uses a raw-apple residue assumption translated to apple-juice consumption with a processing factor. It is not a measured apple-juice residue lane.
- The apple-juice consumption lane uses the governed apples consumption amount as a compact processed-derivative proxy. It is not a row-level apple-juice survey estimate.
- The consumption values used for deterministic summaries come from the current governed Dietary MCP consumption profiles, not a direct export from EFSA dashboards.
- The raw-survey dataset is a compact synthetic review fixture designed to exercise the survey and bootstrap lanes.
- The survey distribution summary is an unweighted subject-level fixture summary. Survey weights are preserved in the raw records and used by the uncertainty workflow, but the distribution summary is not a survey-weighted population estimate.
- Percentiles in the survey, bootstrap, and uncertainty outputs are regression-demo outputs from a tiny fixture, not population percentiles.
- The uncertainty assessment demonstrates censored-residue policy handling; it is not an official probabilistic dietary assessment.
- The trade-risk output reflects the current shipped defaults and coverage gaps. It is not legal advice or final import/export clearance.
- The PBPK handoff is an external oral dose packet only. It does not execute PBPK or estimate internal dose.
- Biomonitoring comparison is out of scope for Dietary MCP v0.1 and should route to a future Biomonitoring or Reverse Exposure MCP.

## Backlog

- Add row-locked EFSA dashboard or API-derived residue examples once a durable public extraction path is selected.
- Add mancozeb and endosulfan follow-up case packs after glyphosate.
- Add a separate multi-module route comparison demo using Fate MCP and Direct-Use Exposure MCP.
- Add a future biomonitoring plausibility handoff instead of embedding reverse dosimetry in Dietary MCP.
