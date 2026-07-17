"""Adversarial self-tests for the dietary-exposure-mcp Track-B scientific-invariants gate.

These tests prove the gate is HONEST and FAIL-CLOSED:

* the source-contract guard REJECTS a forbidden/undeclared-field packet
  (fail-closed, BEFORE projection) — the structural fix for the producer-emission
  -contract dead-arm class — and ACCEPTS every faithful real-producer emission
  (no over-tightening), including optional-field-bearing variants;
* every advertised BLOCKING_SCIENTIFIC_CODE bites on an Ajv-VALID, declared-field,
  producer-emittable fault, and is absent on the pristine packet (clean->fault
  proof through the real bridge — NOT a projected-object mutation);
* the projection's disguise battery blocks (a homoglyph/zero-width/placeholder
  overclaim cannot launder past the substantive scanner);
* the bridge fails closed on a vendored-digest tamper and an unrecognized schemaId;
* the AI-provenance arm is intentionally absent (no AssessmentRun/AiModelUseRecord
  is ever projected — a deterministic, zero-LLM producer);
* the pristine corpus gate is GREEN and DETERMINISTIC.

The tests are skipped only if ``node`` is unavailable (the vendored engine needs
it); the source-contract guard tests run pure-Python and never skip.
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dietary_mcp.governance import project_to_spine as projector  # noqa: E402
from dietary_mcp.governance import source_contract  # noqa: E402
from dietary_mcp.governance import spine_bridge as bridge  # noqa: E402
from dietary_mcp.governance.errors import (  # noqa: E402
    SOURCE_CONTRACT_VIOLATION,
    UNRECOGNIZED_SPINE_SCHEMA_ID,
    VENDOR_DIGEST_MISMATCH,
)

import importlib.util as _ilu  # noqa: E402

_gate_spec = _ilu.spec_from_file_location(
    "dietary_scientific_invariants_gate",
    REPO_ROOT / "scripts" / "scientific_invariants_gate.py",
)
gate = _ilu.module_from_spec(_gate_spec)
_gate_spec.loader.exec_module(gate)

_NODE = shutil.which("node")
needs_node = pytest.mark.skipif(
    _NODE is None, reason="node required for the vendored spine engine"
)

_CORPUS = "tests/governance_spine/corpus"
INTAKE_REL = f"{_CORPUS}/dietary_intake_summary.json"
BUNDLE_REL = f"{_CORPUS}/contaminant_interpretation_bundle.json"
PACKET_REL = f"{_CORPUS}/contaminant_signoff_packet.json"
ADAPTER_REL = f"{_CORPUS}/adapter_review_bundle.json"
# --- BC-6 exhaustive-sweep newly-gated surfaces ------------------------------
METALS_BUNDLE_REL = f"{_CORPUS}/metals_interpretation_bundle.json"
METALS_PACKET_REL = f"{_CORPUS}/metals_signoff_packet.json"
TRADE_REL = f"{_CORPUS}/trade_risk_review_bundle.json"
INTEROP_PACKET_REL = f"{_CORPUS}/interoperability_signoff_packet.json"
SFU_PACKET_REL = f"{_CORPUS}/scientific_follow_up_owner_signoff_packet.json"
SANITISED_REL = f"{_CORPUS}/sanitised_public_review_dossier.json"
# --- BC-6 FINAL: the four remaining ungated operator-note SINK results --------
SFU_QUEUE_REL = f"{_CORPUS}/scientific_follow_up_queue_bundle.json"
SFU_BOARD_REL = f"{_CORPUS}/scientific_follow_up_review_board.json"
SFU_HANDOFF_REL = f"{_CORPUS}/scientific_follow_up_owner_handoff_packet.json"
SFU_REMEDIATION_REL = f"{_CORPUS}/scientific_follow_up_owner_remediation_packet.json"

INTAKE_KIND = "dietary_intake_summary"
BUNDLE_KIND = "contaminant_interpretation_bundle"
PACKET_KIND = "contaminant_signoff_packet"
ADAPTER_KIND = "adapter_review_bundle"
METALS_BUNDLE_KIND = "metals_interpretation_bundle"
METALS_PACKET_KIND = "metals_signoff_packet"
TRADE_KIND = "trade_risk_review_bundle"
INTEROP_PACKET_KIND = "interoperability_signoff_packet"
SFU_PACKET_KIND = "scientific_follow_up_owner_signoff_packet"
SANITISED_KIND = "sanitised_public_review_dossier"
SFU_QUEUE_KIND = "scientific_follow_up_queue_bundle"
SFU_BOARD_KIND = "scientific_follow_up_review_board"
SFU_HANDOFF_KIND = "scientific_follow_up_owner_handoff_packet"
SFU_REMEDIATION_KIND = "scientific_follow_up_owner_remediation_packet"


def _load(rel: str) -> dict:
    return json.loads((REPO_ROOT / rel).read_text())


def _project(kind: str, obj: dict) -> dict:
    if kind == INTAKE_KIND:
        return projector.project_dietary_intake_summary(obj, estimate_id="probe")
    if kind == BUNDLE_KIND:
        return projector.project_contaminant_interpretation_bundle(obj, object_id="probe")
    if kind == PACKET_KIND:
        return projector.project_contaminant_signoff_packet(obj, object_id="probe")
    if kind == ADAPTER_KIND:
        return projector.project_adapter_review_bundle(obj, object_id="probe")
    if kind == METALS_BUNDLE_KIND:
        return projector.project_metals_monitoring_interpretation_bundle(obj, object_id="probe")
    if kind == METALS_PACKET_KIND:
        return projector.project_metals_monitoring_signoff_packet(obj, object_id="probe")
    if kind == TRADE_KIND:
        return projector.project_trade_risk_review_bundle(obj, object_id="probe")
    if kind == INTEROP_PACKET_KIND:
        return projector.project_interoperability_signoff_packet(obj, object_id="probe")
    if kind == SFU_PACKET_KIND:
        return projector.project_scientific_follow_up_owner_signoff_packet(obj, object_id="probe")
    if kind == SANITISED_KIND:
        return projector.project_sanitised_public_review_dossier(obj, object_id="probe")
    if kind == SFU_QUEUE_KIND:
        return projector.project_scientific_follow_up_queue_bundle(obj, object_id="probe")
    if kind == SFU_BOARD_KIND:
        return projector.project_scientific_follow_up_review_board(obj, object_id="probe")
    if kind == SFU_HANDOFF_KIND:
        return projector.project_scientific_follow_up_owner_handoff_packet(obj, object_id="probe")
    if kind == SFU_REMEDIATION_KIND:
        return projector.project_scientific_follow_up_owner_remediation_packet(obj, object_id="probe")
    raise AssertionError(kind)


def _contract_valid(kind: str, obj: dict) -> bool:
    return source_contract.validate_source_packet(obj, kind=kind, corpus="probe") is None


def _codes(kind: str, obj: dict) -> set[str]:
    """End-to-end: assert the (faulted) packet is producer-contract-VALID, then
    project + run the real bridge and return the engine codes that fired."""
    assert _contract_valid(kind, obj), (
        f"fault is NOT producer-contract-valid for {kind} — a schema-forbidden "
        "fault would be a dead-arm proof"
    )
    result = bridge.validate_object(_project(kind, obj))
    return {f.code for f in result.findings}


# ---------------------------------------------------------------------------
# 1. Source-contract guard: rejects forbidden field, accepts faithful emissions
# ---------------------------------------------------------------------------


def test_guard_rejects_undeclared_field_fail_closed():
    obj = _load(INTAKE_REL)
    obj["smuggledRegulatoryVerdict"] = "approved"
    finding = source_contract.validate_source_packet(
        obj, kind=INTAKE_KIND, corpus="probe"
    )
    assert finding is not None
    assert finding.code == SOURCE_CONTRACT_VIOLATION
    assert finding.origin == "meta"


def test_guard_rejects_out_of_enum_value():
    obj = _load(BUNDLE_REL)
    obj["checkStatus"] = "definitely_passes"  # not in {pass, review_required, fail}
    finding = source_contract.validate_source_packet(
        obj, kind=BUNDLE_KIND, corpus="probe"
    )
    assert finding is not None and finding.code == SOURCE_CONTRACT_VIOLATION


@pytest.mark.parametrize(
    "kind,rel",
    [
        (INTAKE_KIND, INTAKE_REL),
        (BUNDLE_KIND, BUNDLE_REL),
        (PACKET_KIND, PACKET_REL),
        (ADAPTER_KIND, ADAPTER_REL),
    ],
)
def test_guard_accepts_faithful_real_producer_emission(kind, rel):
    assert _contract_valid(kind, _load(rel)), (
        f"guard over-tightened: a faithful real-producer emission ({rel}) was rejected"
    )


def test_guard_accepts_optional_bearing_and_optional_omitting_intake():
    """The strict contract must accept BOTH a bounded summary (bounds + limitations
    present) and a minimal summary that omits those optionals (no over-tighten)."""
    obj = _load(INTAKE_REL)
    assert _contract_valid(INTAKE_KIND, obj)  # optionals present
    minimal = copy.deepcopy(obj)
    for k in (
        "lower_bound_total_intake_mg_per_kg_bw_per_day",
        "upper_bound_total_intake_mg_per_kg_bw_per_day",
        "limitations",
        "metric_label",
    ):
        minimal.pop(k, None)
    assert _contract_valid(INTAKE_KIND, minimal), "guard over-tightened an optional"


# ---------------------------------------------------------------------------
# 2. Every advertised code bites on a producer-contract-valid fault
# ---------------------------------------------------------------------------


@needs_node
def test_external_exposure_not_internal_dose_bites():
    clean = _load(INTAKE_REL)
    assert "EXTERNAL_EXPOSURE_NOT_INTERNAL_DOSE" not in _codes(INTAKE_KIND, clean)
    fault = copy.deepcopy(clean)
    fault["metric_label"] = "internal_dose_css_mg_per_l"
    assert "EXTERNAL_EXPOSURE_NOT_INTERNAL_DOSE" in _codes(INTAKE_KIND, fault)


@needs_node
def test_exposure_uncertainty_and_ceiling_required_bites():
    clean = _load(INTAKE_REL)
    assert "EXPOSURE_UNCERTAINTY_AND_CEILING_REQUIRED" not in _codes(INTAKE_KIND, clean)
    fault = copy.deepcopy(clean)
    for k in (
        "lower_bound_total_intake_mg_per_kg_bw_per_day",
        "upper_bound_total_intake_mg_per_kg_bw_per_day",
        "limitations",
    ):
        fault.pop(k, None)
    assert "EXPOSURE_UNCERTAINTY_AND_CEILING_REQUIRED" in _codes(INTAKE_KIND, fault)


@needs_node
def test_free_text_overclaim_bites_on_bundle_note():
    clean = _load(BUNDLE_REL)
    assert "FREE_TEXT_OVERCLAIM" not in _codes(BUNDLE_KIND, clean)
    fault = copy.deepcopy(clean)
    fault["notes"] = fault.get("notes", []) + [
        "This monitoring dataset confirms the food is safe and compliant for "
        "regulatory approval."
    ]
    assert "FREE_TEXT_OVERCLAIM" in _codes(BUNDLE_KIND, fault)


@needs_node
def test_free_text_overclaim_bites_on_adapter_note():
    clean = _load(ADAPTER_REL)
    assert "FREE_TEXT_OVERCLAIM" not in _codes(ADAPTER_KIND, clean)
    fault = copy.deepcopy(clean)
    fault["notes"] = fault.get("notes", []) + [
        "Adapter parity proves the dietary intake is a safe, regulatory-grade dose."
    ]
    assert "FREE_TEXT_OVERCLAIM" in _codes(ADAPTER_KIND, fault)


@needs_node
def test_ready_with_blockers_bites_on_signed_off_with_unresolved_actions():
    clean = _load(PACKET_REL)
    assert "READY_WITH_BLOCKERS" not in _codes(PACKET_KIND, clean)
    fault = copy.deepcopy(clean)
    fault["overallSignoffStatus"] = "signed_off"
    fault["unresolvedBlockingActionIds"] = ["review_governance_links"]
    assert "READY_WITH_BLOCKERS" in _codes(PACKET_KIND, fault)


# ---------------------------------------------------------------------------
# 3. Disguise battery — a disguised overclaim cannot launder
# ---------------------------------------------------------------------------


@needs_node
def test_disguised_overclaim_in_note_still_blocks():
    """A placeholder/empty note does not mint a (fake) clean narrative, and a
    homoglyph-decorated genuine overclaim still folds to the overclaim it is."""
    clean = _load(BUNDLE_REL)
    # zero-width + homoglyph decorated overclaim (Cyrillic а/е/о, zero-width spaces)
    disguised = "This​ dataset confirms the food is sаfe for regulаtory apprоval."
    fault = copy.deepcopy(clean)
    fault["notes"] = fault.get("notes", []) + [disguised]
    # producer-contract-valid (it is just a string note) and still trips the engine
    assert "FREE_TEXT_OVERCLAIM" in _codes(BUNDLE_KIND, fault)


def test_placeholder_note_is_not_substantive_narrative():
    # _is_substantive_scalar rejects placeholders/disguises -> they never become
    # scanned narrative content (cannot fake a clean leaf).
    for junk in ["n/a", "  ", "tbd", "​​", "not‑assessed", "none"]:
        assert not projector._is_substantive_scalar(junk)


# ---------------------------------------------------------------------------
# 4. Bridge fail-closed: digest tamper + unrecognized schemaId
# ---------------------------------------------------------------------------


@needs_node
def test_bridge_blocks_on_vendor_digest_tamper(tmp_path, monkeypatch):
    # Point the bridge at a tampered copy of the vendored tree.
    src = REPO_ROOT / "vendor" / "schema-spine"
    dst = tmp_path / "schema-spine"
    shutil.copytree(src, dst)
    tampered = dst / "policy-validator.mjs"
    tampered.write_text(tampered.read_text() + "\n// tamper\n")
    monkeypatch.setattr(bridge, "_VENDOR_ROOT", dst)
    monkeypatch.setattr(bridge, "_RUN_POLICY_CLI", dst / "run-policy.mjs")
    monkeypatch.setattr(bridge, "_INDEX_MJS", dst / "index.mjs")
    monkeypatch.setattr(bridge, "_VENDORED_FROM", dst / "VENDORED_FROM.json")
    finding = bridge.verify_vendor_digests()
    assert finding is not None and finding.code == VENDOR_DIGEST_MISMATCH


@needs_node
def test_bridge_blocks_on_unrecognized_schema_id():
    obj = {"schemaId": "https://schemas.ngra.ai/toxmcp/NotARealShape.v1.schema.json"}
    result = bridge.validate_object(obj)
    assert not result.valid
    assert UNRECOGNIZED_SPINE_SCHEMA_ID in result.blocking_codes


# ---------------------------------------------------------------------------
# 5. AI-provenance arm intentionally absent + pristine GREEN + deterministic
# ---------------------------------------------------------------------------


def test_no_ai_provenance_object_is_ever_projected():
    for kind, rel in [
        (INTAKE_KIND, INTAKE_REL),
        (BUNDLE_KIND, BUNDLE_REL),
        (PACKET_KIND, PACKET_REL),
        (ADAPTER_KIND, ADAPTER_REL),
    ]:
        obj = _project(kind, _load(rel))
        sid = obj["schemaId"]
        assert "AssessmentRun" not in sid and "AiModelUseRecord" not in sid
        assert "aiUse" not in obj and "modelUseRecords" not in obj


@needs_node
def test_pristine_gate_is_green():
    assert gate.run_gate(list(gate.DEFAULT_CORPUS)) == 0


@needs_node
def test_projection_is_deterministic():
    obj = _load(INTAKE_REL)
    a = projector.project_dietary_intake_summary(obj, estimate_id="x")
    b = projector.project_dietary_intake_summary(obj, estimate_id="x")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# ===========================================================================
# BC-6 DEFECT 1: ungated independent server-authored surfaces + the metals
# signoff LAUNDERING CHANNEL. Each newly-gated surface is contract-guarded,
# pristine-green, and bites its advertised code(s) on a producer-emittable fault.
# ===========================================================================

_OVERCLAIM_NOTE = (
    "This dataset confirms the food is safe and compliant for regulatory approval."
)

_NEWLY_GATED = [
    (METALS_BUNDLE_KIND, METALS_BUNDLE_REL),
    (METALS_PACKET_KIND, METALS_PACKET_REL),
    (TRADE_KIND, TRADE_REL),
    (INTEROP_PACKET_KIND, INTEROP_PACKET_REL),
    (SFU_PACKET_KIND, SFU_PACKET_REL),
    (SANITISED_KIND, SANITISED_REL),
]

_SIGNOFF_SURFACES = [
    (METALS_PACKET_KIND, METALS_PACKET_REL),
    (INTEROP_PACKET_KIND, INTEROP_PACKET_REL),
    (SFU_PACKET_KIND, SFU_PACKET_REL),
]

_OVERCLAIM_SURFACES = [
    (METALS_BUNDLE_KIND, METALS_BUNDLE_REL),
    (METALS_PACKET_KIND, METALS_PACKET_REL),
    (TRADE_KIND, TRADE_REL),
    (INTEROP_PACKET_KIND, INTEROP_PACKET_REL),
    (SFU_PACKET_KIND, SFU_PACKET_REL),
    (SANITISED_KIND, SANITISED_REL),
]


@pytest.mark.parametrize("kind,rel", _NEWLY_GATED)
def test_newly_gated_surface_accepts_faithful_real_producer_emission(kind, rel):
    assert _contract_valid(kind, _load(rel)), (
        f"guard over-tightened: a faithful real-producer emission ({rel}) was rejected"
    )


@pytest.mark.parametrize("kind,rel", _NEWLY_GATED)
def test_newly_gated_surface_guard_rejects_undeclared_field(kind, rel):
    obj = _load(rel)
    obj["smuggledRegulatoryVerdict"] = "approved"
    finding = source_contract.validate_source_packet(obj, kind=kind, corpus="probe")
    assert finding is not None and finding.code == SOURCE_CONTRACT_VIOLATION


@needs_node
@pytest.mark.parametrize("kind,rel", _OVERCLAIM_SURFACES)
def test_newly_gated_surface_free_text_overclaim_bites(kind, rel):
    clean = _load(rel)
    assert "FREE_TEXT_OVERCLAIM" not in _codes(kind, clean)
    fault = copy.deepcopy(clean)
    fault["notes"] = fault.get("notes", []) + [_OVERCLAIM_NOTE]
    assert "FREE_TEXT_OVERCLAIM" in _codes(kind, fault)


@needs_node
@pytest.mark.parametrize("kind,rel", _SIGNOFF_SURFACES)
def test_newly_gated_signoff_ready_with_blockers_bites(kind, rel):
    clean = _load(rel)
    assert "READY_WITH_BLOCKERS" not in _codes(kind, clean)
    fault = copy.deepcopy(clean)
    fault["overallSignoffStatus"] = "signed_off"
    fault["unresolvedBlockingActionIds"] = ["review_governance_links"]
    assert "READY_WITH_BLOCKERS" in _codes(kind, fault)


@needs_node
def test_metals_signoff_laundering_channel_is_closed():
    """THE proven laundering channel: the metals signoff producer can emit
    overallSignoffStatus=SIGNED_OFF while unresolvedBlockingActionIds is non-empty
    AND append an unchecked packet_note. Both now bite — the SAME invariants proven
    on the contaminant signoff sibling."""
    clean = _load(METALS_PACKET_REL)
    assert "READY_WITH_BLOCKERS" not in _codes(METALS_PACKET_KIND, clean)
    assert "FREE_TEXT_OVERCLAIM" not in _codes(METALS_PACKET_KIND, clean)

    # arm 1: signed-off WITH unresolved blockers
    laundered = copy.deepcopy(clean)
    laundered["overallSignoffStatus"] = "signed_off"
    laundered["unresolvedBlockingActionIds"] = ["review_governance_links"]
    assert "READY_WITH_BLOCKERS" in _codes(METALS_PACKET_KIND, laundered)

    # arm 2: unchecked overclaiming packet_note in notes[]
    noted = copy.deepcopy(clean)
    noted["notes"] = clean["notes"] + [
        "This signoff confirms the food is safe and approved for regulatory submission."
    ]
    assert "FREE_TEXT_OVERCLAIM" in _codes(METALS_PACKET_KIND, noted)


@needs_node
def test_trade_risk_embedded_report_notes_are_scanned():
    """The trade-risk bundle embeds a GlobalTradeRiskReport whose OWN notes[] are a
    server-authored conclusion surface; an overclaim there is deep-scanned too."""
    clean = _load(TRADE_REL)
    fault = copy.deepcopy(clean)
    fault["tradeReport"]["notes"] = clean["tradeReport"].get("notes", []) + [
        "Trade screening confirms the product is safe and approved for regulatory "
        "market clearance."
    ]
    assert "FREE_TEXT_OVERCLAIM" in _codes(TRADE_KIND, fault)


# ===========================================================================
# BC-6 DEFECT 2: FREE_TEXT_OVERCLAIM clause bypass. A non-negated overclaim
# clause sharing a string with a protective denial clause must STAY scanned.
# ===========================================================================


def test_per_clause_split_keeps_overclaim_alongside_denial():
    """Unit: a leaf packing a denial clause AND a non-negated overclaim clause routes
    ONLY the denial to caveats; the overclaim stays in the engine-scanned set."""
    mixed = (
        "This does not certify regulatory approval; nonetheless it confirms the food "
        "is safe for regulatory submission and is approved."
    )
    scanned, caveats = projector._split_narrative([mixed])
    assert any("confirms the food is safe" in s for s in scanned), (
        "the non-negated overclaim clause must stay in the overclaim-scanned set"
    )
    assert any("does not certify" in c for c in caveats), (
        "the protective denial clause is exempted to the non-claim caveats"
    )


def test_per_clause_split_does_not_false_positive_a_faithful_denial():
    """A wholly-protective multi-part denial (no non-negated overclaim) must NOT leak
    any overclaim-bearing fragment into the scanned set."""
    denial = (
        "Signed-off status records closure of the governed review workflow only; it "
        "does not certify scientific correctness, submission readiness, or regulatory "
        "approval."
    )
    scanned, caveats = projector._split_narrative([denial])
    assert not any(
        s.strip().lower() in {"regulatory approval", "submission readiness"}
        for s in scanned
    ), "a negated phrase fragment was wrongly split away from its negation"


@needs_node
def test_clause_bypass_overclaim_still_bites_end_to_end():
    """End-to-end (through the real bridge): the documented multi-clause bypass note
    now bites FREE_TEXT_OVERCLAIM (pre-fix it returned no finding)."""
    clean = _load(BUNDLE_REL)
    assert "FREE_TEXT_OVERCLAIM" not in _codes(BUNDLE_KIND, clean)
    fault = copy.deepcopy(clean)
    fault["notes"] = clean.get("notes", []) + [
        "This does not certify regulatory approval; nonetheless it confirms the food "
        "is safe for regulatory submission and is approved."
    ]
    assert "FREE_TEXT_OVERCLAIM" in _codes(BUNDLE_KIND, fault)


@needs_node
def test_full_corpus_gate_is_green_across_all_gated_surfaces():
    """All 14 gated surfaces (4 original + 6 BC-6 + 4 BC-6-FINAL) clear the engine on
    the pristine real-producer corpus."""
    assert len(gate.DEFAULT_CORPUS) == 14
    assert gate.run_gate(list(gate.DEFAULT_CORPUS)) == 0


# ===========================================================================
# BC-6 FINAL DEFECT 1: the four remaining UNGATED top-level operator-note SINK
# results. Each appends an operator note (bundle_note / board_note / packet_note)
# verbatim into a server-authored notes[] that lands in a top-level MCP tool
# result no gated surface traversed. Each is now gated through the generic
# review-document projection so an overclaim laundered into that note bites
# FREE_TEXT_OVERCLAIM.
# ===========================================================================

_BC6_FINAL_SINKS = [
    (SFU_QUEUE_KIND, SFU_QUEUE_REL),
    (SFU_BOARD_KIND, SFU_BOARD_REL),
    (SFU_HANDOFF_KIND, SFU_HANDOFF_REL),
    (SFU_REMEDIATION_KIND, SFU_REMEDIATION_REL),
]


@pytest.mark.parametrize("kind,rel", _BC6_FINAL_SINKS)
def test_bc6_final_sink_accepts_faithful_real_producer_emission(kind, rel):
    assert _contract_valid(kind, _load(rel)), (
        f"guard over-tightened: a faithful real-producer emission ({rel}) was rejected"
    )


@pytest.mark.parametrize("kind,rel", _BC6_FINAL_SINKS)
def test_bc6_final_sink_guard_rejects_undeclared_field(kind, rel):
    obj = _load(rel)
    obj["smuggledRegulatoryVerdict"] = "approved"
    finding = source_contract.validate_source_packet(obj, kind=kind, corpus="probe")
    assert finding is not None and finding.code == SOURCE_CONTRACT_VIOLATION


@needs_node
@pytest.mark.parametrize("kind,rel", _BC6_FINAL_SINKS)
def test_bc6_final_sink_operator_note_overclaim_bites(kind, rel):
    """An overclaim laundered into the operator-controlled note (bundle/board/packet
    note -> producer notes[]) now bites FREE_TEXT_OVERCLAIM at this top-level result."""
    clean = _load(rel)
    assert "FREE_TEXT_OVERCLAIM" not in _codes(kind, clean)
    fault = copy.deepcopy(clean)
    fault["notes"] = clean.get("notes", []) + [_OVERCLAIM_NOTE]
    assert "FREE_TEXT_OVERCLAIM" in _codes(kind, fault)


# ===========================================================================
# BC-6 FINAL DEFECT 2: tradeRiskReviewBundle embedded-report laundering. The
# embedded GlobalTradeRiskReport stamps server-authored free text into MANY
# narrative leaves, not just tradeReport.notes[]. The generic recursive
# narrative-leaf collector now deep-scans EVERY leaf at any depth, so an overclaim
# in ANY of them bites FREE_TEXT_OVERCLAIM (pre-fix only tradeReport.notes[] was
# scanned -> engine valid=True, no code).
# ===========================================================================


def _trade_with(mutate) -> dict:
    obj = copy.deepcopy(_load(TRADE_REL))
    mutate(obj)
    return obj


_TRADE_OVERCLAIM = (
    "Trade screening confirms the product is safe and approved for regulatory "
    "market clearance."
)


def _set_report_quality_flag_message(obj):
    obj["tradeReport"]["qualityFlags"][0]["message"] = _TRADE_OVERCLAIM


def _append_profile_note(obj):
    obj["tradeReport"]["jurisdiction_profiles"][0]["notes"].append(_TRADE_OVERCLAIM)


def _set_profile_quality_flag_message(obj):
    obj["tradeReport"]["jurisdiction_profiles"][0]["qualityFlags"][0]["message"] = (
        _TRADE_OVERCLAIM
    )


def _set_profile_status_reason(obj):
    obj["tradeReport"]["jurisdiction_profiles"][0]["statusReason"] = _TRADE_OVERCLAIM


def _set_profile_mrl_violation_message(obj):
    obj["tradeReport"]["jurisdiction_profiles"][0]["mrl_violations"] = [
        {"code": "x", "severity": "warning", "message": _TRADE_OVERCLAIM}
    ]


_TRADE_NARRATIVE_LEAVES = [
    ("tradeReport.qualityFlags[].message", _set_report_quality_flag_message),
    ("jurisdiction_profiles[].notes[]", _append_profile_note),
    ("jurisdiction_profiles[].quality_flags[].message", _set_profile_quality_flag_message),
    ("jurisdiction_profiles[].status_reason", _set_profile_status_reason),
    ("jurisdiction_profiles[].mrl_violations[].message", _set_profile_mrl_violation_message),
]


@needs_node
@pytest.mark.parametrize("leaf,mutate", _TRADE_NARRATIVE_LEAVES)
def test_trade_report_every_narrative_leaf_is_deep_scanned(leaf, mutate):
    """Each server-authored narrative leaf of the embedded GlobalTradeRiskReport — at
    any depth — is now deep-scanned; an overclaim there bites FREE_TEXT_OVERCLAIM."""
    assert "FREE_TEXT_OVERCLAIM" not in _codes(TRADE_KIND, _load(TRADE_REL))
    assert "FREE_TEXT_OVERCLAIM" in _codes(TRADE_KIND, _trade_with(mutate)), (
        f"overclaim in {leaf} escaped the deep narrative scan"
    )


def test_recursive_collector_harvests_only_narrative_leaves():
    """Unit: the recursive collector harvests substantive strings under narrative
    keys at any depth, and NEVER mints content from ids / enums / numerics."""
    embedded = {
        "notes": ["A top note."],
        "id": "not-a-narrative-id",
        "count": 7,
        "profiles": [
            {
                "jurisdiction": "us",
                "statusReason": "A status reason narrative.",
                "qualityFlags": [{"code": "c", "message": "A flag message."}],
                "notes": ["A nested profile note."],
            }
        ],
    }
    leaves = projector._collect_narrative_leaves(embedded)
    assert "A top note." in leaves
    assert "A status reason narrative." in leaves
    assert "A flag message." in leaves
    assert "A nested profile note." in leaves
    assert "not-a-narrative-id" not in leaves  # an id is never harvested
    assert "us" not in leaves  # an enum/value outside a narrative key is never harvested
    assert gate.run_gate(list(gate.DEFAULT_CORPUS)) == 0


# ===========================================================================
# BC-6 FINAL ROUND-4: the actionItems[] operator-note laundering CLASS. Earlier
# rounds closed each differently-NAMED operator-note field one at a time (the
# exact-match _NARRATIVE_LEAF_KEYS allowlist), so a new field escaped every round:
# now actionItems[].followUpNote (on all 4 follow-up surfaces) and
# interoperabilitySignoffPacket.actionItems[].triggerNote launder a free-text
# overclaim nested in the actionItems[] array that NO projector deep-scanned. We
# close the CLASS BY CONSTRUCTION: a string leaf is operator-narrative iff its KEY
# (case-insensitive) CONTAINS a narrative token, scanned over the WHOLE released
# object at any depth (incl every actionItems[] element). The SAME overclaim string
# that bites in top-level notes[] now bites in any *Note / *Message / *Reason leaf.
# ===========================================================================

_ACTIONITEM_NOTE_SURFACES = [
    (SFU_QUEUE_KIND, SFU_QUEUE_REL),
    (SFU_BOARD_KIND, SFU_BOARD_REL),
    (SFU_HANDOFF_KIND, SFU_HANDOFF_REL),
    (SFU_REMEDIATION_KIND, SFU_REMEDIATION_REL),
    (SFU_PACKET_KIND, SFU_PACKET_REL),
    (INTEROP_PACKET_KIND, INTEROP_PACKET_REL),
    (METALS_PACKET_KIND, METALS_PACKET_REL),
    (PACKET_KIND, PACKET_REL),
]


@needs_node
@pytest.mark.parametrize("kind,rel", _ACTIONITEM_NOTE_SURFACES)
def test_action_item_follow_up_note_overclaim_bites(kind, rel):
    """An overclaim laundered into actionItems[].followUpNote — operator-supplied
    free text nested in the actionItems[] array — now bites FREE_TEXT_OVERCLAIM
    (independently reproduced: pre-fix the SAME string bit in top-level notes[] but
    passed valid=True nested in actionItems[].followUpNote)."""
    clean = _load(rel)
    assert clean.get("actionItems"), f"{rel} has no actionItems[] to launder into"
    assert "FREE_TEXT_OVERCLAIM" not in _codes(kind, clean)
    fault = copy.deepcopy(clean)
    fault["actionItems"][0]["followUpNote"] = _OVERCLAIM_NOTE
    assert "FREE_TEXT_OVERCLAIM" in _codes(kind, fault), (
        "overclaim in actionItems[].followUpNote escaped the whole-object deep scan"
    )


@needs_node
@pytest.mark.parametrize("kind,rel", _ACTIONITEM_NOTE_SURFACES)
def test_action_item_trigger_note_overclaim_bites(kind, rel):
    """An overclaim laundered into actionItems[].triggerNote (the interop-packet
    field, exercised on every actionItems[]-bearing surface) bites
    FREE_TEXT_OVERCLAIM by construction — a *Note key suffix is matched, never an
    exact field name."""
    clean = _load(rel)
    assert clean.get("actionItems"), f"{rel} has no actionItems[] to launder into"
    assert "FREE_TEXT_OVERCLAIM" not in _codes(kind, clean)
    fault = copy.deepcopy(clean)
    fault["actionItems"][0]["triggerNote"] = _OVERCLAIM_NOTE
    assert "FREE_TEXT_OVERCLAIM" in _codes(kind, fault), (
        "overclaim in actionItems[].triggerNote escaped the whole-object deep scan"
    )


@needs_node
def test_interop_action_item_trigger_note_specifically_bites():
    """The exact independently-reproduced bypass: interoperabilitySignoffPacket
    actionItems[].triggerNote (its real producer-emittable field)."""
    clean = _load(INTEROP_PACKET_REL)
    assert "FREE_TEXT_OVERCLAIM" not in _codes(INTEROP_PACKET_KIND, clean)
    fault = copy.deepcopy(clean)
    fault["actionItems"][0]["triggerNote"] = _OVERCLAIM_NOTE
    assert "FREE_TEXT_OVERCLAIM" in _codes(INTEROP_PACKET_KIND, fault)


def test_key_pattern_matcher_catches_note_family_by_construction():
    """Unit: the key-pattern matcher catches differently-NAMED operator-note fields
    by SUBSTRING/SUFFIX — followUpNote / triggerNote / packetNote / bundleNote /
    boardNote / statusReason / qualityMessage — not an exact-name allowlist. Keys
    with no narrative token (ids / enums / counts / booleans) are NOT matched."""
    for narrative_key in [
        "followUpNote", "triggerNote", "packetNote", "bundleNote", "boardNote",
        "statusReason", "status_reason", "qualityMessage", "reviewerComment",
        "justification", "caveat", "description", "explanation", "remark",
        "annotation", "narrative", "finding", "rationale", "summary", "notes",
        "message", "messages",
    ]:
        assert projector._key_is_narrative(narrative_key), narrative_key
    for non_narrative_key in [
        "actionId", "priority", "blocking", "decisionStatus", "linkedRecordIds",
        "queueLabels", "supportingUris", "actionType", "ruleId", "reviewedAt",
        "resolved", "title", "category", "escalated", "escalationType",
    ]:
        assert not projector._key_is_narrative(non_narrative_key), non_narrative_key


def test_whole_object_scan_keeps_pristine_corpus_engine_clean():
    """Precision guard: the whole-object key-pattern scan must NOT false-positive on
    the faithful pristine corpus — every surface stays engine-clean (no pristine
    non-overclaim string under a matched key trips a code)."""
    assert gate.run_gate(list(gate.DEFAULT_CORPUS)) == 0
