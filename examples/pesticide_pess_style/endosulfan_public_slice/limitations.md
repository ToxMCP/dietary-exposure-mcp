# Limitations

This case pack is a public-source slice for demonstrating Dietary Exposure MCP governance for Endosulfan. It is not a full PESS reproduction.

## Explicit Non-Claims

- Residue values are illustrative regulatory-screening inputs within the EU MRL band, not row-level EFSA monitoring records.
- Endosulfan is an organochlorine insecticide whose EU approval lapsed; EU MRLs sit at or near the analytical LOQ band (~0.01-0.05 mg/kg).
- The apple-juice lane uses a raw-apple residue translated to apple-juice consumption with a processing factor.
- Consumption values come from governed Dietary MCP profiles; the raw survey is a compact synthetic fixture.
- Percentiles are regression-demo outputs from a tiny fixture, not population percentiles.
- ADI/ARfD are governed EFSA OpenFoodTox values; the health-reference exceedance is a chronic-context demonstration.
- DTXSID is not locked in this slice (preferredName + CASRN only).
- The PBPK handoff is an external oral dose packet only; biomonitoring comparison routes to a future Biomonitoring/Reverse-Exposure MCP.
