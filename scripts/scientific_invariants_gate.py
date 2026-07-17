#!/usr/bin/env python3
"""Track-B scientific-invariants gate (vendored schema-spine engine) for dietary-exposure-mcp.

Projects each RELEASED server-authored interpretive object onto its canonical
ToxMCP schema-spine shape, runs the vendored, digest-pinned spine policy engine
over the projection via a fail-closed Node bridge, aggregates every blocking
finding, and EXITS NON-ZERO if any public-release-blocking code fires.

dietary-exposure-mcp is deterministic and zero-LLM and already enforces these
invariants natively (a dietary / contaminant exposure interpretation is review
context, never a risk or regulatory conclusion), so on the PRISTINE corpus this
gate is GREEN. Its job is to BLOCK if a future change ever lets one of these
regressions into a released object.

EXHAUSTIVE CANDIDACY SWEEP (see ADR 0005 for the full classification table). The
BC-6 sweep gates EVERY independent server-authored-conclusion released surface (14):

  RouteDoseEstimate (dietaryIntakeSummary — an external oral-dose intake estimate),
  plumbed from DECLARED fields:
    EXTERNAL_EXPOSURE_NOT_INTERNAL_DOSE      <- the producer's declared metric_label
                                                asserts an internal-dose / Css / AUC /
                                                risk / regulatory metric
    EXPOSURE_UNCERTAINTY_AND_CEILING_REQUIRED<- the producer declares NO uncertainty
                                                (omits both the intake bounds and the
                                                limitations narrative)
  ToxMcpObject (the review / qualification / signoff documents:
   contaminantMonitoringInterpretationBundle / contaminantMonitoringSignoffPacket /
   adapterReviewBundle + BC-6: metalsMonitoringInterpretationBundle /
   metalsMonitoringSignoffPacket / tradeRiskReviewBundle /
   interoperabilitySignoffPacket / scientificFollowUpOwnerSignoffPacket /
   sanitisedPublicReviewDossier + BC-6 FINAL (the four remaining operator-note
   SINK results): scientificFollowUpQueueBundle / scientificFollowUpReviewBoard /
   scientificFollowUpOwnerHandoffPacket / scientificFollowUpOwnerRemediationPacket):
    FREE_TEXT_OVERCLAIM                       <- a safety / regulatory overclaim in a
                                                declared narrative leaf (notes[] /
                                                limitations[].message, incl an embedded
                                                report's/bundle's own notes[]); scanned
                                                PER CLAUSE so an overclaim sharing a
                                                string with a protective denial bites
    READY_WITH_BLOCKERS                        <- a signed_off signoff packet (incl the
                                                metals laundering-channel sibling) that
                                                still carries unresolved blocking actions
                                                (declared unresolvedBlockingActionIds);
                                                the nested ReviewState arm

  Meta fail-closed (synthesized by the bridge / projection / guard, ALWAYS blocking):
    SOURCE_CONTRACT_VIOLATION, ENGINE_UNAVAILABLE, UNRECOGNIZED_SPINE_SCHEMA_ID,
    VENDOR_DIGEST_MISMATCH, PROJECTION_INCOMPLETE

HONEST-DROPPED (documented N/A in ADR 0005):
  AI-provenance codes — dietary-exposure-mcp is deterministic / zero-LLM; the strict
    emission contracts carry NO aiUse / model-use field and src/ has no LLM lane, so
    the gate projects neither an AssessmentRun nor an AiModelUseRecord (a dead arm).
  READY_WITH_PENDING_HUMAN_REVIEW / READY_WITHOUT_HUMAN_REVIEW — the signoff packet's
    only review-readiness signal is overallSignoffStatus; signed_off semantically IS
    completed human review, so there is no producer-emittable state yielding
    publicationReadiness=ready WITH humanReview=required/not_required. Unreachable on
    a contract-valid fault -> honest-dropped. READY_WITH_BLOCKERS covers the
    signed-off-but-not-actually-ready arm.
  consumptionProfileSelectionResult / lookup* results — FAITHFUL RELAYS of curated
    profile / reference records (the matched/missing split is a deterministic set
    operation, not an authored scientific qualification); no spine shape adjudicates
    a relay, so they are NON-CANDIDATES (classified, not gated).

This gate is ADVISORY on the free-plan private repo (no required-status-checks on
private repos). PROMOTE-TO-BLOCKING: when the repo gains branch protection /
rulesets, mark the ``scientific-invariants`` CI job a required status check.

Exit codes:
    0 — every projected object passed the engine (no blocking code fired)
    1 — at least one blocking code fired (release-blocking regression)
    2 — usage / corpus-loading error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from dietary_mcp.governance import project_to_spine as projector  # noqa: E402
from dietary_mcp.governance import source_contract  # noqa: E402
from dietary_mcp.governance import spine_bridge as bridge  # noqa: E402
from dietary_mcp.governance.errors import (  # noqa: E402
    PROJECTION_INCOMPLETE,
    BlockingFinding,
    ProjectionIncompleteError,
)

# --- corpus ------------------------------------------------------------------
DIETARY_INTAKE_SUMMARY = "dietary_intake_summary"
CONTAMINANT_INTERPRETATION_BUNDLE = "contaminant_interpretation_bundle"
CONTAMINANT_SIGNOFF_PACKET = "contaminant_signoff_packet"
ADAPTER_REVIEW_BUNDLE = "adapter_review_bundle"
# --- BC-6 exhaustive-sweep newly-gated independent server-authored surfaces ---
METALS_INTERPRETATION_BUNDLE = "metals_interpretation_bundle"
METALS_SIGNOFF_PACKET = "metals_signoff_packet"
TRADE_RISK_REVIEW_BUNDLE = "trade_risk_review_bundle"
INTEROPERABILITY_SIGNOFF_PACKET = "interoperability_signoff_packet"
SCIENTIFIC_FOLLOW_UP_OWNER_SIGNOFF_PACKET = "scientific_follow_up_owner_signoff_packet"
SANITISED_PUBLIC_REVIEW_DOSSIER = "sanitised_public_review_dossier"
# --- BC-6 FINAL: the four remaining ungated operator-note SINK results ---------
SCIENTIFIC_FOLLOW_UP_QUEUE_BUNDLE = "scientific_follow_up_queue_bundle"
SCIENTIFIC_FOLLOW_UP_REVIEW_BOARD = "scientific_follow_up_review_board"
SCIENTIFIC_FOLLOW_UP_OWNER_HANDOFF_PACKET = "scientific_follow_up_owner_handoff_packet"
SCIENTIFIC_FOLLOW_UP_OWNER_REMEDIATION_PACKET = (
    "scientific_follow_up_owner_remediation_packet"
)

_CORPUS_DIR = "tests/governance_spine/corpus"

DEFAULT_CORPUS: tuple[tuple[str, str], ...] = (
    (f"{_CORPUS_DIR}/dietary_intake_summary.json", DIETARY_INTAKE_SUMMARY),
    (f"{_CORPUS_DIR}/contaminant_interpretation_bundle.json", CONTAMINANT_INTERPRETATION_BUNDLE),
    (f"{_CORPUS_DIR}/contaminant_signoff_packet.json", CONTAMINANT_SIGNOFF_PACKET),
    (f"{_CORPUS_DIR}/adapter_review_bundle.json", ADAPTER_REVIEW_BUNDLE),
    (f"{_CORPUS_DIR}/metals_interpretation_bundle.json", METALS_INTERPRETATION_BUNDLE),
    (f"{_CORPUS_DIR}/metals_signoff_packet.json", METALS_SIGNOFF_PACKET),
    (f"{_CORPUS_DIR}/trade_risk_review_bundle.json", TRADE_RISK_REVIEW_BUNDLE),
    (
        f"{_CORPUS_DIR}/interoperability_signoff_packet.json",
        INTEROPERABILITY_SIGNOFF_PACKET,
    ),
    (
        f"{_CORPUS_DIR}/scientific_follow_up_owner_signoff_packet.json",
        SCIENTIFIC_FOLLOW_UP_OWNER_SIGNOFF_PACKET,
    ),
    (
        f"{_CORPUS_DIR}/sanitised_public_review_dossier.json",
        SANITISED_PUBLIC_REVIEW_DOSSIER,
    ),
    (
        f"{_CORPUS_DIR}/scientific_follow_up_queue_bundle.json",
        SCIENTIFIC_FOLLOW_UP_QUEUE_BUNDLE,
    ),
    (
        f"{_CORPUS_DIR}/scientific_follow_up_review_board.json",
        SCIENTIFIC_FOLLOW_UP_REVIEW_BOARD,
    ),
    (
        f"{_CORPUS_DIR}/scientific_follow_up_owner_handoff_packet.json",
        SCIENTIFIC_FOLLOW_UP_OWNER_HANDOFF_PACKET,
    ),
    (
        f"{_CORPUS_DIR}/scientific_follow_up_owner_remediation_packet.json",
        SCIENTIFIC_FOLLOW_UP_OWNER_REMEDIATION_PACKET,
    ),
)

BLOCKING_SCIENTIFIC_CODES: frozenset[str] = frozenset(
    {
        "EXTERNAL_EXPOSURE_NOT_INTERNAL_DOSE",
        "EXPOSURE_UNCERTAINTY_AND_CEILING_REQUIRED",
        "FREE_TEXT_OVERCLAIM",
        "READY_WITH_BLOCKERS",
    }
)


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _project(
    kind: str, source: dict[str, Any], rel: str
) -> list[tuple[str, dict[str, Any]]]:
    if kind == DIETARY_INTAKE_SUMMARY:
        return [
            (
                f"{rel}#route_dose_estimate",
                projector.project_dietary_intake_summary(source, estimate_id=rel),
            )
        ]
    if kind == CONTAMINANT_INTERPRETATION_BUNDLE:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_contaminant_interpretation_bundle(source, object_id=rel),
            )
        ]
    if kind == CONTAMINANT_SIGNOFF_PACKET:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_contaminant_signoff_packet(source, object_id=rel),
            )
        ]
    if kind == ADAPTER_REVIEW_BUNDLE:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_adapter_review_bundle(source, object_id=rel),
            )
        ]
    if kind == METALS_INTERPRETATION_BUNDLE:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_metals_monitoring_interpretation_bundle(
                    source, object_id=rel
                ),
            )
        ]
    if kind == METALS_SIGNOFF_PACKET:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_metals_monitoring_signoff_packet(source, object_id=rel),
            )
        ]
    if kind == TRADE_RISK_REVIEW_BUNDLE:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_trade_risk_review_bundle(source, object_id=rel),
            )
        ]
    if kind == INTEROPERABILITY_SIGNOFF_PACKET:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_interoperability_signoff_packet(source, object_id=rel),
            )
        ]
    if kind == SCIENTIFIC_FOLLOW_UP_OWNER_SIGNOFF_PACKET:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_scientific_follow_up_owner_signoff_packet(
                    source, object_id=rel
                ),
            )
        ]
    if kind == SANITISED_PUBLIC_REVIEW_DOSSIER:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_sanitised_public_review_dossier(source, object_id=rel),
            )
        ]
    if kind == SCIENTIFIC_FOLLOW_UP_QUEUE_BUNDLE:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_scientific_follow_up_queue_bundle(source, object_id=rel),
            )
        ]
    if kind == SCIENTIFIC_FOLLOW_UP_REVIEW_BOARD:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_scientific_follow_up_review_board(source, object_id=rel),
            )
        ]
    if kind == SCIENTIFIC_FOLLOW_UP_OWNER_HANDOFF_PACKET:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_scientific_follow_up_owner_handoff_packet(
                    source, object_id=rel
                ),
            )
        ]
    if kind == SCIENTIFIC_FOLLOW_UP_OWNER_REMEDIATION_PACKET:
        return [
            (
                f"{rel}#toxmcp_object",
                projector.project_scientific_follow_up_owner_remediation_packet(
                    source, object_id=rel
                ),
            )
        ]
    raise ProjectionIncompleteError(f"Unknown projection kind {kind!r}.")


def run_gate(corpus: list[tuple[str, str]], *, emit_json: bool = False) -> int:
    findings: list[tuple[str, BlockingFinding]] = []
    checked = 0
    for rel, kind in corpus:
        path = REPO_ROOT / rel
        if not path.exists():
            print(f"[scientific-invariants] FAIL: corpus file missing: {rel}", file=sys.stderr)
            return 2
        source = _load(path)

        # SOURCE-CONTRACT GUARD (fail-closed, BEFORE any projection). A packet that
        # violates the producer's STRICT emission contract (additionalProperties:false
        # JSON schema) BLOCKS and is NEVER projected — so a "fault" that could only
        # fire a scientific code by carrying a schema-forbidden / undeclared field (or
        # an out-of-enum value the producer cannot emit) is caught here as a contract
        # violation instead of silently exercising a dead arm.
        contract_violation = source_contract.validate_source_packet(
            source, kind=kind, corpus=rel
        )
        if contract_violation is not None:
            findings.append((rel, contract_violation))
            continue

        try:
            projected = _project(kind, source, rel)
        except ProjectionIncompleteError as exc:
            findings.append(
                (
                    rel,
                    BlockingFinding.meta(
                        PROJECTION_INCOMPLETE, exc.message, path=exc.path, corpus=rel
                    ),
                )
            )
            continue

        for label, obj in projected:
            checked += 1
            result = bridge.validate_object(obj)
            for finding in result.findings:
                findings.append((label, finding))

    # SAFE-BY-DEFAULT: every finding (meta or scientific) blocks. The explicit
    # allowlist above is documentation; we never silently drop an engine code.
    blocking = list(findings)

    if emit_json:
        print(
            json.dumps(
                {
                    "checkedObjects": checked,
                    "blocking": [
                        {"object": label, **f.as_dict()} for (label, f) in blocking
                    ],
                },
                indent=2,
            )
        )

    if blocking:
        print(
            f"[scientific-invariants] BLOCK — {len(blocking)} release-blocking "
            f"finding(s) across {checked} projected object(s):",
            file=sys.stderr,
        )
        for label, f in blocking:
            print(f"  - [{f.origin}] {f.code} @ {label} {f.path}: {f.message}", file=sys.stderr)
        return 1

    print(
        f"[scientific-invariants] PASS — {checked} projected object(s) cleared the "
        "vendored schema-spine policy engine.",
        file=sys.stderr,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable findings")
    args = parser.parse_args(argv)
    return run_gate(list(DEFAULT_CORPUS), emit_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
