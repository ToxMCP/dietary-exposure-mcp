# Third-Party Notices

The Apache-2.0 license in `LICENSE` applies to original Dietary Exposure MCP
code and documentation. It does not replace the terms attached to third-party
data, publications, standards, or software. Source links are provided for
traceability and do not imply endorsement by the source organizations.

## EFSA OpenFoodTox

Dietary Exposure MCP includes a normalized extract of human-consumer reference
values derived from:

- European Food Safety Authority (EFSA), OpenFoodTox 2.0 reference-values
  snapshot, version 6
- DOI: `10.5281/zenodo.8120114`
- source file: `ReferenceValues_KJ_2023.xlsx`
- source MD5: `c3574a602191e9ef3c63f09c8263c7a7`
- source coverage: EFSA outputs through September 2022

The source workbook itself is not redistributed. The normalized records are
marked as a superseded, review-required snapshot because OpenFoodTox 3.0 is now
current. EFSA owns OpenFoodTox and its content. EFSA's legal notice authorizes
reuse with source acknowledgement, subject to any source-specific limitations:
https://www.efsa.europa.eu/en/legalnotice

For legal or regulatory reuse, cite the original EFSA scientific output. If an
OpenFoodTox record conflicts with the original output, the original output is
authoritative. EFSA has not reviewed or endorsed Dietary Exposure MCP.

## European Union Pesticide MRL Data

The package includes normalized maximum-residue-level and commodity records
derived from the European Commission EU Pesticides Database DataLake API v3.0:
https://food.ec.europa.eu/plants/pesticides/eu-pesticides-database_en

Dietary Exposure MCP filters and maps those records into its own governed
schemas. It is not an official copy of the EU Pesticides Database, and the
Official Journal of the European Union remains authoritative. European
Commission material is subject to the applicable Commission reuse policy and
any source-specific notice. The Commission's general policy requires source
acknowledgement and identification of changes.

Attribution: European Union, EU Pesticides Database; normalized and modified by
ToxMCP. No endorsement by the European Commission is implied.

## WHO GEMS/Food Cluster Diets

The package contains 17 compact chronic screening profiles adapted from the WHO
GEMS/Food Cluster Diets 2012 workbook:

- source: World Health Organization, GEMS/Food Cluster Diets 2012
- source URL: https://www.who.int/data/gho/samples/food-cluster-diets
- downloaded workbook SHA-256:
  `5bfec6bcbcd37d838022fba9518b3842a8503ebade40b15286ad42b5fca884ed`

The profiles map broad WHO categories to a small number of representative MCP
commodities and add a 60 kg screening body-weight basis. They are adaptations,
not WHO survey records or WHO-endorsed commodity profiles. WHO is not
responsible for their content or accuracy.

The downloaded workbook does not state a specific license. WHO's general
publishing terms vary by material and may require permission for commercial
reuse or database redistribution. The WHO-derived profiles are not relicensed
under Apache-2.0. Before commercial redistribution, verify the applicable WHO
terms or obtain permission from WHO:
https://www.who.int/about/policies/publishing/copyright

## ToxMCP Schema Spine

The scientific-invariants gate includes a digest-pinned vendored copy of the
ToxMCP schema-spine policy engine from:
https://github.com/ToxMCP/toxmcp-schema-spine

The pinned source commit is
`e0a6a0581efd8dfd5b10c2de14435d87769c5944`. Exact file digests and provenance
are recorded in `vendor/schema-spine/VENDORED_FROM.json`.

## Python Dependencies

Python dependencies are resolved separately and retain their own licenses. The
release CycloneDX SBOM enumerates the exact environment used for release
verification. No dependency license is replaced by the Dietary Exposure MCP
license.
