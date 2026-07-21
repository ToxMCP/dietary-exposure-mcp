# Limitations and Intended Use

## Plain-language summary

Dietary Exposure MCP is a transparent screening and evidence-handoff tool. It
can calculate food-mediated oral exposure from explicit inputs, compare results
with governed reference values, and preserve the assumptions and sources used.
It cannot decide whether a product, food, chemical, exposure, or dossier is
safe, legal, compliant, or acceptable to a regulator.

The software is useful when a qualified user needs a reproducible first-pass
calculation or a structured packet for further review. It is not a substitute
for current primary sources, professional judgement, a validated higher-tier
model, or jurisdiction-specific regulatory assessment.

## Appropriate uses

Version `v0.1.0` is suitable for:

- deterministic acute and chronic dietary-exposure screening
- bounded calculations when the lower and upper residue assumptions are stated
- governed ingestion and summary of supported dietary-survey data
- bounded bootstrap and uncertainty-support workflows with explicit methods
- comparison with versioned reference values and legal-limit records
- review of contaminant, metals, MRL, and trade-risk evidence
- preparation of auditable PBPK dose handoffs without running a PBPK model
- technical and scientific evaluation of the released screening software

## Decisions it must not make

Do not use this server by itself to:

- declare a substance, product, food, exposure, or population safe or unsafe
- make a final regulatory, legal, clinical, enforcement, or market-access decision
- claim that a submission is complete or accepted by an authority
- replace a qualified toxicologist, dietary-risk assessor, statistician, or regulator
- infer an acute conclusion from a chronic value, or the reverse
- claim equivalence to PRIMo, DEEM, DietEx, or another external engine
- execute PBPK or internal-dose simulation

An output can inform a decision, but a qualified person remains responsible for
checking the inputs, applicability domain, current authority sources,
uncertainty, and interpretation.

## Scientific data status

The release contains a checksum-pinned OpenFoodTox 3.0 version-7 migration with
2,417 bulk runtime records and matching provenance records. Those bulk records
remain `review_required`; importing a record does not make it curated or
approved.

A separate 16-record high-impact review identifies exact support, primary-source
unit corrections, unit normalizations, and source-encoding anomalies. Its
canonical content SHA-256 is
`0feb8e3e4f9852c2d102375dd89d814ed08407a602d699882cf48bdd7f3c8c90`.
The first independent review returned `not approved`. Its four blocking findings
were remediated, but a new positive signoff from an independent toxicologist or
dietary-risk assessor has not yet been recorded. The `v0.1.0` stable software
label does not change those review states. The affected records remain public
screening and review material, not an independently approved scientific corpus.

Reference values, MRLs, legal limits, guidance, and authority interpretations
can change after a snapshot is published. For any decision-relevant use, verify
the value, unit, population, assessment date, qualifier, and legal status in the
current primary authority output.

## Calculation and input limits

- Results depend on the supplied residue concentrations, food mappings,
  consumption values, body weights, processing factors, occurrence data, and
  censored-data policy. Incorrect or inapplicable inputs produce misleading
  outputs even when the arithmetic is correct.
- The engine is deterministic-first. Its survey distribution, cohort-bootstrap,
  and two-dimensional uncertainty workflows are bounded support lanes, not a
  general-purpose population exposure platform.
- A bounded result does not become probabilistic simply because it has a lower
  and upper value. Bounds reflect the assumptions provided.
- Built-in profiles are governed screening defaults. They do not automatically
  represent every country, subpopulation, eating occasion, season, or vulnerable
  group.
- Unsupported commodity mappings and arbitrary spreadsheets are not silently
  accepted. A user must resolve validation errors or review flags.
- Missing evidence is not proof of no exposure, no hazard, or compliance.

## External tools and regulatory systems

Adapter and interoperability outputs test structured compatibility and preserve
handoff context. They do not demonstrate numerical or regulatory equivalence to
proprietary PRIMo, DEEM, DietEx, submission portals, or authority workflows.
When an assessment requires one of those systems, run the authoritative system
and retain its native inputs, version, output, and reviewer record.

Dietary Exposure MCP covers food-mediated oral exposure. Direct-use product
regimens belong in Direct-Use Exposure MCP, and internal-dose simulation belongs
in PBPK MCP.

## Review-state meanings

- `review_required` means a qualified person still has work to do before the
  record or packet can support a controlled downstream decision.
- `signed_off` and `signed_off_with_waivers` mean the configured workflow was
  closed for that exact versioned packet. They do not mean regulator acceptance.
- `draft_ready` means automated evidence is internally consistent and ready for
  review. It is not scientific approval and does not describe the software
  release channel.

Always preserve the record identifiers, source versions, hashes, quality flags,
assumptions, limitations, and reviewer decisions that accompany an output.

## Deployment and security limits

The supported `v0.1.0` path is local stdio operation. Streamable HTTP binds to
loopback by default and refuses unauthenticated startup unless an operator
deliberately configures an authenticated gateway. Do not expose the server
directly to an untrusted network. A public or multi-user deployment needs a
separate security review covering authentication, authorization, TLS, proxy
trust, rate limiting, logging, retention, and incident response.

Do not place credentials, personal data, confidential studies, unpublished
dossiers, or restricted applicant material in public issues or example inputs.

## Third-party data and redistribution

Original project code is Apache-2.0, but scientific data and vendored materials
retain their own source terms. In particular, WHO-derived GEMS/Food profile
redistribution requires attention for the intended audience and commercial use.
Review the repository's
[THIRD_PARTY_NOTICES.md](https://github.com/ToxMCP/dietary-exposure-mcp/blob/main/THIRD_PARTY_NOTICES.md)
before redistributing or repackaging the data.

## Version maturity

`v0.1.0` is an early `0.x` software baseline. Interfaces, defaults, evidence
packs, and review workflows may evolve in later minor releases. Pin the exact
version used for a calculation, preserve its evidence packet, and review release
notes before upgrading.

## Safe-use checklist

Before relying on an output:

1. Confirm the chemical, commodity, population, route, and time basis.
2. Confirm every decision-relevant value against the current primary source.
3. Review assumptions, provenance, quality flags, and limitation notes.
4. Check whether the method and defaults fit the intended population and jurisdiction.
5. Escalate `review_required`, conflicting, anomalous, or corrected records.
6. Use a validated higher-tier or authority system when the screening model is insufficient.
7. Record qualified human review and preserve the exact versioned evidence packet.

See also the [dietary boundary guide](./dietary_boundary_guide.md),
[release readiness](./release_readiness.md), and
[public release process](./public_release.md).
