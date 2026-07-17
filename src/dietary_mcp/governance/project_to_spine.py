"""Total, deterministic projection: dietary-exposure-mcp released objects -> schema-spine objects.

The schema-spine policy engine (``vendor/schema-spine/policy-validator.mjs``)
dispatches solely on ``payload.schemaId``. The dietary-exposure released objects
are NONE of the spine shapes: ``dietaryIntakeSummary`` is an external-oral-dose
intake estimate, and ``contaminantMonitoringInterpretationBundle`` /
``contaminantMonitoringSignoffPacket`` / ``adapterReviewBundle`` are review /
qualification documents. Running the engine on a raw dietary object is therefore a
silent ``valid:true`` no-op. **This projection is where the gate's correctness
lives.**

Design contract (non-negotiable — costed the reference pilot ivive-ber 6 rounds):

* TOTAL & DETERMINISTIC — same input always yields the same projected object; no
  clocks, no randomness, no hidden defaults. (The producer stamps non-deterministic
  ``result_metadata.executed_at`` / ``provenance.generated_at``; the projection
  NEVER reads them.)
* FAITHFUL, FROM DECLARED FIELDS ONLY — every projected field is DERIVED from a
  field the producer's STRICT emission contract declares (recon'd by running the
  real DietaryRuntime export seams with ``model_dump(mode="json", by_alias=True)``
  across optional-field-bearing variants, not stale committed examples — those fail
  their own released schemas).
* ANY unmapped enum / missing required field raises ``ProjectionIncompleteError``
  (a BLOCK). It is NEVER silently defaulted to a safe branch.

ANTI-OVERCLAIM DOCTRINE (the dietary boundary). A dietary / contaminant exposure
interpretation is NOT a risk or regulatory conclusion:

* ``dietaryIntakeSummary`` -> spine ``RouteDoseEstimate.v1``: an external oral
  intake estimate cannot authorize internal-dose, risk, or regulatory claims
  (``EXTERNAL_EXPOSURE_NOT_INTERNAL_DOSE`` — bites when the producer's declared
  ``metric_label`` asserts an internal-dose / Css / AUC / risk / regulatory metric)
  and must carry explicit uncertainty + confidence-ceiling references
  (``EXPOSURE_UNCERTAINTY_AND_CEILING_REQUIRED`` — bites when the producer omits
  BOTH the bounds and the limitations narrative, i.e. declares no uncertainty).
* the three review / interpretation documents -> spine ``ToxMcpObject.v1`` (the
  generic governed envelope): the engine deep-scans every narrative leaf for
  safety / regulatory overclaims (``FREE_TEXT_OVERCLAIM``) and re-validates the
  embedded review state (``READY_WITH_BLOCKERS`` / ``READY_WITH_PENDING_HUMAN_REVIEW``
  — the signoff / review arm: a ``signed_off`` packet that still carries unresolved
  blocking actions, or an interpretation marked submission-ready while review is
  pending, cannot be release-ready) and the non-claim boundary protection.

POSITIVE STRUCTURED / CANONICAL EVIDENCE (the crux). A 'substantive' narrative is
minted ONLY from STRUCTURED content with a real value (a non-empty string that
survives the disguise fold, a finite numeric, a non-empty structured list). A
disguised string (None / empty / placeholder / Unicode-dash / combining-diacritic
/ HOMOGLYPH / leetspeak / zero-width) supplies neither, so it can never mint
content — the disguise battery blocks BY CONSTRUCTION. Identifier distinctness uses
an NFKD+Mn+Cf normalizer, never bare ``.strip()``.

AI-PROVENANCE ARM — INTENTIONALLY ABSENT. dietary-exposure-mcp is deterministic
and zero-LLM: its strict emission contracts carry NO ``aiUse`` / model-use field,
and ``grep`` of ``src/`` is clean of any LLM / model-inference lane. We therefore
do NOT project a hardcoded-clean AssessmentRun and do NOT advertise any
AI-provenance code (it would be a dead arm). See ADR 0001.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

from dietary_mcp.governance.errors import ProjectionIncompleteError

# --- spine schemaIds ---------------------------------------------------------

ROUTE_DOSE_ESTIMATE_SCHEMA_ID = (
    "https://schemas.ngra.ai/toxmcp/RouteDoseEstimate.v1.schema.json"
)
TOXMCP_OBJECT_SCHEMA_ID = "https://schemas.ngra.ai/toxmcp/ToxMcpObject.v1.schema.json"
REVIEW_STATE_SCHEMA_ID = "https://schemas.ngra.ai/toxmcp/ReviewState.v1.schema.json"
NONCLAIM_BOUNDARY_SCHEMA_ID = (
    "https://schemas.ngra.ai/toxmcp/NonClaimBoundary.v1.schema.json"
)
PROVENANCE_BUNDLE_SCHEMA_ID = (
    "https://schemas.ngra.ai/toxmcp/ProvenanceBundle.v1.schema.json"
)
AUDIT_TRACE_SCHEMA_ID = "https://schemas.ngra.ai/toxmcp/AuditTraceRef.v1.schema.json"

# .../src/dietary_mcp/governance/project_to_spine.py -> repo root is parents[3].
_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_PATH = _REPO_ROOT / "vendor" / "schema-spine" / "schema-manifest.json"


# === POSITIVE STRUCTURED / CANONICAL EVIDENCE HELPERS ========================
# Ported verbatim-in-spirit from the proven ivive-ber / iata Track-B pilots — the
# disguise-fold helpers are the gameable crux, so they are reused unchanged.

_NON_SUBSTANTIVE_PLACEHOLDERS = frozenset(
    {
        "n/a", "na", "n.a", "n.a.", "tbd", "tba", "todo", "pending", "placeholder",
        "nil", "nd", "no data", "not applicable", "not available", "not assessed",
        "not determined", "to be determined", "to be confirmed", "see notes",
        "see note", "unknown", "missing", "none", "null", "empty",
        "no", "nodata", "notapplicable", "notavailable", "notassessed",
        "notdetermined", "tobedetermined", "tobeconfirmed",
        "-", "--", "---", "...", "etc", "?", "xx", "xxx", "x", "tk",
    }
)

_ENGINE_NON_SUBSTANTIVE_TOKEN = re.compile(
    r"^(none|not[-_ ]?assessed|unknown|missing|null)$", re.IGNORECASE
)

_CONFUSABLE_ENTRIES: tuple[tuple[int, str], ...] = (
    (0x0430, "a"), (0x0435, "e"), (0x043E, "o"), (0x0440, "p"), (0x0441, "c"),
    (0x0443, "y"), (0x0445, "x"), (0x0455, "s"), (0x0456, "i"), (0x0458, "j"),
    (0x0432, "b"), (0x043A, "k"), (0x043C, "m"), (0x043D, "h"), (0x0442, "t"),
    (0x0410, "a"), (0x0412, "b"), (0x0415, "e"), (0x041A, "k"), (0x041C, "m"),
    (0x041D, "h"), (0x041E, "o"), (0x0420, "p"), (0x0421, "c"), (0x0422, "t"),
    (0x03B1, "a"), (0x03B2, "b"), (0x03B5, "e"), (0x03B9, "i"), (0x03BA, "k"),
    (0x03BD, "v"), (0x03BF, "o"), (0x03C1, "p"), (0x03C4, "t"), (0x03C5, "u"),
    (0x03C7, "x"), (0x0391, "a"), (0x0395, "e"), (0x039F, "o"), (0x03A1, "p"),
    (0x03A4, "t"), (0x0399, "i"), (0x1D00, "a"), (0x1D04, "c"), (0x1D07, "e"),
    (0xA731, "s"), (0x212A, "k"), (0x2113, "l"), (0x0585, "o"), (0x0578, "n"),
)
_CONFUSABLE_MAP = {chr(code): ascii_ for code, ascii_ in _CONFUSABLE_ENTRIES}
_CONFUSABLE_PATTERN = re.compile(
    "[" + "".join(chr(code) for code, _ in _CONFUSABLE_ENTRIES) + "]"
)

_DASH_VARIANTS = "‐‑‒–—―−⁃­"
_SPACE_VARIANTS = (
    "          "
    "    　"
)
_SEPARATOR_FOLD = re.compile("[" + _DASH_VARIANTS + _SPACE_VARIANTS + "]")


def _fold_substantive_token(value: str) -> str:
    folded = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", value)
        if unicodedata.category(ch) not in ("Mn", "Cf")
    )
    folded = _CONFUSABLE_PATTERN.sub(lambda m: _CONFUSABLE_MAP[m.group(0)], folded)
    folded = _SEPARATOR_FOLD.sub(
        lambda m: " " if m.group(0).isspace() else "-", folded
    )
    return re.sub(r"\s+", " ", folded).strip()


def _contains_finite_numeric(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return False
        return value != 0
    if isinstance(value, dict):
        return any(_contains_finite_numeric(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_finite_numeric(item) for item in value)
    return False


def _is_substantive_scalar(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return False
        return value != 0
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return False
        folded = _fold_substantive_token(stripped)
        if not folded:
            return False
        if _ENGINE_NON_SUBSTANTIVE_TOKEN.match(folded):
            return False
        norm = re.sub(r"[-_]+", " ", folded).strip().lower()
        if (
            folded.lower() in _NON_SUBSTANTIVE_PLACEHOLDERS
            or norm in _NON_SUBSTANTIVE_PLACEHOLDERS
        ):
            return False
        core = re.sub(r"[^0-9a-z ]+", " ", folded.lower())
        core = re.sub(r"\s+", " ", core).strip()
        core_despaced = core.replace(" ", "")
        if not core:
            return False
        if _ENGINE_NON_SUBSTANTIVE_TOKEN.match(core) or _ENGINE_NON_SUBSTANTIVE_TOKEN.match(
            core_despaced
        ):
            return False
        if (
            core in _NON_SUBSTANTIVE_PLACEHOLDERS
            or core_despaced in _NON_SUBSTANTIVE_PLACEHOLDERS
        ):
            return False
        if len(re.sub(r"[^0-9a-z]", "", core)) < 2:
            return False
        return True
    return True


def _normalize_identifier(value: str) -> str:
    """NFKD + drop Mn/Cf + homoglyph-fold + casefold + collapse whitespace, for
    DISTINCTNESS counting. Two ids that fold to the same token are NOT distinct, so
    a zero-width / combining-diacritic / homoglyph decoration cannot forge a
    'distinct' id (the count-inflation bypass)."""
    s = unicodedata.normalize("NFKD", value)
    s = "".join(ch for ch in s if unicodedata.category(ch) not in ("Mn", "Cf"))
    s = _CONFUSABLE_PATTERN.sub(lambda m: _CONFUSABLE_MAP[m.group(0)], s)
    return re.sub(r"\s+", " ", s).strip().casefold()


def _require(condition: bool, message: str, path: str = "$") -> None:
    if not condition:
        raise ProjectionIncompleteError(message, path=path)


def _substantive_strings(values: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    if isinstance(values, list):
        for v in values:
            if isinstance(v, str) and _is_substantive_scalar(v):
                norm = _normalize_identifier(v)
                if norm not in seen:
                    seen.add(norm)
                    out.append(v.strip())
    return out


def _limitation_messages(values: Any) -> list[str]:
    """Substantive ``LimitationNote.message`` strings from a declared limitations
    list (each item is {code, message})."""
    out: list[str] = []
    seen: set[str] = set()
    if isinstance(values, list):
        for v in values:
            if isinstance(v, dict):
                msg = v.get("message")
                if isinstance(msg, str) and _is_substantive_scalar(msg):
                    norm = _normalize_identifier(msg)
                    if norm not in seen:
                        seen.add(norm)
                        out.append(msg.strip())
    return out


# === GENERIC RECURSIVE NARRATIVE-LEAF COLLECTOR ==============================
#
# A gated surface frequently carries server-authored free-text conclusion narrative
# at arbitrary depth — at the top level (``notes[]`` / ``limitations[].message``),
# inside an embedded sub-report / bundle / packet (e.g. tradeRiskReviewBundle embeds
# a GlobalTradeRiskReport whose narrative is NOT just ``tradeReport.notes[]`` but
# ``tradeReport.qualityFlags[].message``, each ``jurisdiction_profiles[].notes[]``,
# ``jurisdiction_profiles[].quality_flags[]``/``mrl_violations[].message``, and a
# narrative ``jurisdiction_profiles[].status_reason``), AND inside operator-supplied
# free-text nested in the ``actionItems[]`` array (``actionItems[].followUpNote`` /
# ``actionItems[].triggerNote`` / ``actionItems[].summary`` / ...). Each round that a
# differently-NAMED operator-note field was added (followUpNote, triggerNote,
# packetNote, bundleNote, boardNote, ...) it escaped an EXACT-MATCH allowlist of
# narrative key names. We therefore CLOSE THE CLASS BY CONSTRUCTION: a string leaf is
# operator-narrative iff its KEY (case-insensitive) CONTAINS any narrative token
# below — a SUBSTRING / suffix match, not an exact name — so ``followUpNote`` /
# ``triggerNote`` / ``packetNote`` / ``bundleNote`` / ``boardNote`` / ``statusReason``
# / ``qualityFlags[].message`` / every ``*Note`` / ``*Message`` / ``*Reason`` is
# caught without enumerating one more field. This collector is run over the WHOLE
# released object on EVERY gated surface, so no narrative leaf — top-level, embedded,
# or nested in actionItems[] — escapes the FREE_TEXT_OVERCLAIM scan.
#
# It stays PRECISE: it harvests STRINGS ONLY under a key whose name matches the
# pattern (a scalar string leaf, or the string members of a list DIRECTLY under such
# a key); it never mints content from a numeric, an id, an enum, a boolean, or a
# non-narrative key, so a faithful pristine emission (whose narrative leaves are all
# benign coverage/scope/non-claim sentences) stays engine-clean.
#
# Narrative-key tokens (case-insensitive substring). Each names a class of operator-
# / server-authored free text. ``description`` / ``explanation`` / ``summary`` /
# ``finding`` / ``remark`` / ``annotation`` / ``comment`` / ``justification`` /
# ``caveat`` / ``narrative`` round out the prose-bearing keys so a future producer
# field named in any of those families is scanned without a code change.
_NARRATIVE_KEY_TOKENS: tuple[str, ...] = (
    "note",
    "message",
    "reason",
    "rationale",
    "summary",
    "comment",
    "justification",
    "caveat",
    "narrative",
    "description",
    "explanation",
    "finding",
    "remark",
    "annotation",
)
_NARRATIVE_KEY_PATTERN = re.compile("|".join(_NARRATIVE_KEY_TOKENS), re.IGNORECASE)


def _key_is_narrative(key: Any) -> bool:
    """A dict key names operator/server narrative iff (case-insensitively) it CONTAINS
    any narrative token (suffix/substring, not exact name) — so followUpNote /
    triggerNote / packetNote / qualityFlags[].message / statusReason / *Note /
    *Message / *Reason all match BY CONSTRUCTION."""
    return isinstance(key, str) and _NARRATIVE_KEY_PATTERN.search(key) is not None


def _collect_narrative_leaves(value: Any) -> list[str]:
    """Recursively collect EVERY substantive narrative string anywhere inside the
    released object — every dict value + every list element at ANY depth, INCLUDING
    ``actionItems[]`` and every other nested array — under any key whose name matches
    the narrative KEY-PATTERN. De-duped (NFKD/homoglyph normalizer) in stable
    discovery order. Strings outside a narrative-keyed leaf are NOT collected, so
    ids / enums / numerics / booleans never mint scanned content."""
    out: list[str] = []
    seen: set[str] = set()

    def _add(s: Any) -> None:
        if isinstance(s, str) and _is_substantive_scalar(s):
            norm = _normalize_identifier(s)
            if norm not in seen:
                seen.add(norm)
                out.append(s.strip())

    def _walk(node: Any, *, under_narrative_key: bool) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                key_is_narrative = _key_is_narrative(k)
                if key_is_narrative and isinstance(v, str):
                    _add(v)
                # always recurse so nested structures under non-narrative keys are
                # reached (the narrative leaf may be deep, e.g. actionItems[].
                # followUpNote, profiles[].notes[]); propagate the narrative-key
                # context so a list/string DIRECTLY under a narrative key has its
                # string members harvested.
                _walk(v, under_narrative_key=key_is_narrative)
        elif isinstance(node, list):
            for item in node:
                if under_narrative_key and isinstance(item, str):
                    _add(item)
                _walk(item, under_narrative_key=under_narrative_key)
        # scalars handled by the dict/list branches above.

    _walk(value, under_narrative_key=False)
    return out


# === manifest-driven digest helper ===========================================


def _toxmcp_object_digest() -> str:
    if not _MANIFEST_PATH.exists():
        raise ProjectionIncompleteError(
            f"Vendored schema manifest missing: {_MANIFEST_PATH}",
            path="$.schemaDigest",
        )
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    for entry in manifest.get("entries", []):
        if entry.get("schemaId") == TOXMCP_OBJECT_SCHEMA_ID:
            digest = entry.get("digest")
            if isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest):
                return f"sha256:{digest}"
    raise ProjectionIncompleteError(
        "ToxMcpObject schema id has no usable digest in the vendored manifest.",
        path="$.schemaDigest",
    )


# === dietaryIntakeSummary -> RouteDoseEstimate.v1 ============================
#
# The intake summary is an EXTERNAL oral-dose estimate. The producer's declared
# ``metric_label`` is the semantic label of the emitted dose; an honest summary
# labels it as an external oral dose. The projection passes that label THROUGH as
# the allowedDownstreamUse, so a metric_label that asserts an internal-dose / Css /
# AUC / risk / regulatory metric bites EXTERNAL_EXPOSURE_NOT_INTERNAL_DOSE — never a
# fabricated narrower allowlist. uncertaintyRefs / confidenceCeilingRefs are minted
# from DECLARED uncertainty content (numeric bounds + the limitations narrative); a
# summary that declares NO uncertainty (no bounds AND no limitations — both optional
# in the emission contract) yields empty refs and bites
# EXPOSURE_UNCERTAINTY_AND_CEILING_REQUIRED.

# A metric_label whose folded form matches any of these is an internal-dose / risk /
# regulatory framing and must NOT be authorized by an external intake estimate.
_INTERNAL_DOSE_METRIC = re.compile(
    r"internal[-_ ]?dose|css|c[-_ ]?max|cmax|auc|plasma|blood[-_ ]?conc|"
    r"pbpk[-_ ]?result|tissue[-_ ]?conc|risk|regulatory|adverse|hazard[-_ ]?quotient|"
    r"margin[-_ ]?of[-_ ]?exposure|moe",
    re.IGNORECASE,
)


def _allowed_downstream_uses_from_metric(metric_label: str) -> list[str]:
    """Map the producer's declared metric_label to allowedDownstreamUses. An
    external oral-dose label -> a screening external-exposure use (engine-clean). An
    internal-dose / risk / regulatory label -> the matching FORBIDDEN downstream use,
    so the engine's external-exposure invariant bites (faithful pass-through, never a
    re-derived narrower allowlist)."""
    folded = _fold_substantive_token(metric_label).lower()
    if _INTERNAL_DOSE_METRIC.search(folded):
        # Pass the producer's own (mis)label through as the downstream use it
        # implies — the engine then refuses it.
        return ["internal_dose_estimation"]
    return ["screening_dietary_intake_context"]


def project_dietary_intake_summary(
    source: dict[str, Any], *, estimate_id: str
) -> dict[str, Any]:
    """Project a ``dietaryIntakeSummary`` -> spine RouteDoseEstimate.v1."""
    _require(isinstance(source, dict), "Source intake summary is not an object.")

    scenario_id = source.get("scenario_id")
    _require(
        isinstance(scenario_id, str) and _is_substantive_scalar(scenario_id),
        "dietaryIntakeSummary has no substantive scenario_id.",
        path="$.scenario_id",
    )
    assert isinstance(scenario_id, str)

    route = source.get("route")
    _require(
        isinstance(route, str) and _is_substantive_scalar(route),
        "dietaryIntakeSummary has no substantive route.",
        path="$.route",
    )
    assert isinstance(route, str)

    dose_value = source.get("total_intake_mg_per_kg_bw_per_day")
    _require(
        isinstance(dose_value, (int, float)) and not isinstance(dose_value, bool),
        "dietaryIntakeSummary has no numeric total_intake_mg_per_kg_bw_per_day.",
        path="$.total_intake_mg_per_kg_bw_per_day",
    )

    population = source.get("population_group")
    _require(
        isinstance(population, str) and _is_substantive_scalar(population),
        "dietaryIntakeSummary has no substantive population_group.",
        path="$.population_group",
    )
    assert isinstance(population, str)

    temporal = source.get("intake_window_semantic")
    _require(
        isinstance(temporal, str) and _is_substantive_scalar(temporal),
        "dietaryIntakeSummary has no substantive intake_window_semantic.",
        path="$.intake_window_semantic",
    )
    assert isinstance(temporal, str)

    scenario_class = source.get("scenario_class")
    _require(
        isinstance(scenario_class, str) and _is_substantive_scalar(scenario_class),
        "dietaryIntakeSummary has no substantive scenario_class.",
        path="$.scenario_class",
    )
    assert isinstance(scenario_class, str)

    # metric_label is OPTIONAL in the emission contract (the producer default is the
    # external-oral-dose label). Absent -> faithful external default. Present -> pass
    # the producer's declared label through.
    metric_label = source.get("metric_label")
    if not (isinstance(metric_label, str) and _is_substantive_scalar(metric_label)):
        metric_label = "external_oral_dose_mg_per_kg_bw_per_day"
    allowed = _allowed_downstream_uses_from_metric(metric_label)

    # uncertaintyRefs / confidenceCeilingRefs from DECLARED uncertainty content.
    uncertainty_refs: list[str] = []
    lower = source.get("lower_bound_total_intake_mg_per_kg_bw_per_day")
    upper = source.get("upper_bound_total_intake_mg_per_kg_bw_per_day")
    if _contains_finite_numeric(lower) or _contains_finite_numeric(upper):
        uncertainty_refs.append(f"uncertainty:intake_bounds:{scenario_id}")
    for msg in _limitation_messages(source.get("limitations")):
        uncertainty_refs.append(f"uncertainty:limitation:{_normalize_identifier(msg)[:48]}")
    # de-dupe, deterministic order
    seen: set[str] = set()
    deduped_unc: list[str] = []
    for r in uncertainty_refs:
        if r not in seen:
            seen.add(r)
            deduped_unc.append(r)
    uncertainty_refs = deduped_unc

    confidence_refs: list[str] = []
    if uncertainty_refs:
        # A bounded/limited screening estimate carries an explicit screening-grade
        # confidence ceiling, derived from the DECLARED scenario_class + the presence
        # of declared uncertainty — never fabricated when no uncertainty is declared.
        confidence_refs.append(f"ceiling:screening:{scenario_class}")

    # The producer's declared limitations narrative is the RouteDoseEstimate's
    # limitation content; absent any, a standing protective caveat (RouteDoseEstimate
    # requires >=1 limitation). The engine does not overclaim-scan RouteDoseEstimate
    # limitations, so this is faithful carriage, not a laundering surface.
    limitations = _limitation_messages(source.get("limitations")) or [
        "External dietary intake screening estimate; expert review required before any use."
    ]

    return {
        "schemaId": ROUTE_DOSE_ESTIMATE_SCHEMA_ID,
        "routeDoseEstimateId": estimate_id,
        "exposureScenarioContextRef": f"dietary_scenario:{scenario_id}",
        "route": route,
        "doseMetric": metric_label,
        "doseValue": float(dose_value),
        "doseBasis": "body_weight",
        "temporalBasis": temporal,
        "population": population,
        "aggregationMethod": "deterministic",
        "uncertaintyRefs": uncertainty_refs,
        "confidenceCeilingRefs": confidence_refs,
        "allowedDownstreamUses": allowed,
        "prohibitedDownstreamUses": [
            "internal_dose_estimation",
            "risk_characterisation",
            "regulatory_submission",
        ],
        "limitations": limitations,
        "notAnInternalDoseConclusion": True,
        "notARegulatoryConclusion": True,
    }


# === review / interpretation documents -> ToxMcpObject.v1 ====================
#
# contaminantMonitoringInterpretationBundle / contaminantMonitoringSignoffPacket /
# adapterReviewBundle are review / qualification documents wrapped onto the generic
# governed envelope ToxMcpObject.v1 (recognized + dispatched). The engine deep-scans
# their narrative leaves for overclaims (FREE_TEXT_OVERCLAIM) and re-validates the
# embedded ReviewState (READY_WITH_BLOCKERS / READY_WITH_PENDING_HUMAN_REVIEW — the
# signoff / review arm) and NonClaimBoundary.


def _protective_nonclaim_boundary(
    boundary_id: str, extra_caveats: list[str] | None = None
) -> dict[str, Any]:
    caveats = [
        "A dietary / contaminant monitoring interpretation is a review-support "
        "object; it is not a risk or regulatory conclusion."
    ]
    for c in extra_caveats or []:
        if c not in caveats:
            caveats.append(c)
    return {
        "schemaId": NONCLAIM_BOUNDARY_SCHEMA_ID,
        "boundaryId": boundary_id,
        "prohibitedClaims": [
            "risk",
            "regulatory_translation",
            "safety_decision",
            "causal_support",
        ],
        "requiredCaveats": caveats,
        "reviewerRequirement": "expert_review_required",
        "autonomousUseProhibition": True,
    }


# Signoff status -> publication readiness. A signed-off packet is publication-ready
# (so the engine re-checks it against any unresolved blocking actions / pending
# review); an open packet is review_required.
_SIGNOFF_TO_READINESS: dict[str, str] = {
    "open": "review_required",
    "signed_off": "ready",
    "signed_off_with_waivers": "ready",
}


def _review_state_for(
    review_state_id: str,
    *,
    publication_readiness: str,
    human_review: str,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "schemaId": REVIEW_STATE_SCHEMA_ID,
        "reviewStateId": review_state_id,
        "machineReview": "passed",
        "humanReview": human_review,
        "adjudication": "not_required",
        "publicationReadiness": publication_readiness,
        "blockers": blockers,
    }


# A protective NON-CLAIM denial: a sentence that NEGATES a claim word. These are
# the producer's standing disclaimers ("... does not certify ... regulatory
# approval"); they legitimately use risk/regulatory/safety vocabulary under
# negation. The engine deep-scans ToxMcpObject narrative with the GENERAL (negation-
# UNAWARE) scanner, so feeding a denial into the scanned ``limitations`` would
# FALSE-POSITIVE FREE_TEXT_OVERCLAIM on a faithful emission. They belong in the
# NonClaimBoundary.requiredCaveats (negation-aware, NOT overclaim-scanned) — which is
# semantically where a non-claim disclaimer belongs. The match is CONSERVATIVE: it
# requires BOTH a negation token AND a claim/assertion verb AND a claim noun, all
# near each other, so a genuine NON-negated overclaim ("confirms the food is safe
# for regulatory approval") is NOT exempted and still trips the scanner in
# ``limitations``.
_NEGATION_TOKEN = re.compile(
    r"\b(?:not|never|no|cannot|can't|does not|doesn't|do not|don't|is not|isn't|"
    r"are not|aren't|without|neither|nor)\b",
    re.IGNORECASE,
)
_CLAIM_VERB = re.compile(
    r"\b(?:certif\w*|assert\w*|confirm\w*|constitut\w*|establish\w*|guarante\w*|"
    r"prove\w*|demonstrat\w*|conclud\w*|determin\w*|approv\w*|authoriz\w*|"
    r"authoris\w*|imply|implies|creat\w*|chang\w*|calculat\w*|replac\w*|"
    r"convert\w*|provide\w*)\b",
    re.IGNORECASE,
)
_CLAIM_NOUN = re.compile(
    r"\b(?:risk|regulatory|safe|safety|compliance|compliant|approval|submission|"
    r"correctness|decision|conclusion|exposure|hazard|adverse|legal|"
    r"clearance|acceptance|authorisation|authorization)\b",
    re.IGNORECASE,
)

# COPULAR / PREDICATE denial: a negated linking construction that names a claim it
# is NOT, with NO action verb ("it is NOT a final market-clearance or regulatory
# acceptance decision"; "this is NOT a regulatory conclusion"). The engine's own
# control-plane negation window is narrow (24 chars between negation and phrase), so
# a longer negated disjunction ("not a final market-clearance or regulatory
# acceptance decision") slips past its negation guard and false-positives on a
# faithful protective disclaimer. We exempt it HERE, conservatively: the negation
# must be an explicit predicate negation (``is/are/was/were not`` or ``not a/an/
# the``) and a claim noun must follow it within the SAME clause (no ``.,;:`` between
# them), so a NON-negated overclaim ("is a regulatory acceptance decision") is never
# matched.
_COPULAR_DENIAL = re.compile(
    r"\b(?:is|are|was|were|be|been|being)\s+not\b[^.,;:]{0,80}?"
    r"\b(?:risk|regulatory|safe|safety|compliance|compliant|approval|submission|"
    r"clearance|acceptance|authoris\w*|authoriz\w*|market[-\s]?authoris\w*|"
    r"market[-\s]?authoriz\w*|conclusion|decision)\b"
    r"|\bnot\s+(?:a|an|the)\b[^.,;:]{0,80}?"
    r"\b(?:risk|regulatory|safe|safety|compliance|compliant|approval|submission|"
    r"clearance|acceptance|authoris\w*|authoriz\w*|conclusion|decision)\b",
    re.IGNORECASE,
)


def _is_protective_nonclaim_denial(text: str) -> bool:
    """True for a standing non-claim disclaimer (a NEGATED claim). Conservative:
    EITHER a negation token precedes a claim verb that precedes (or co-occurs with) a
    claim noun, OR the clause is a copular/predicate denial ("is not a ... regulatory
    acceptance decision"). A non-negated overclaim is never mis-exempted (the
    negation must abut the claim noun in the same clause)."""
    neg = _NEGATION_TOKEN.search(text)
    if neg:
        verb = _CLAIM_VERB.search(text, neg.end() - 3)
        if verb and _CLAIM_NOUN.search(text, neg.end() - 3):
            return True
    # verbless copular denial ("it is not a ... regulatory acceptance decision")
    return bool(_COPULAR_DENIAL.search(text))


# Clause / sentence boundary. A single narrative leaf may pack a protective denial
# AND a separate non-negated overclaim into one string ("This does not certify
# regulatory approval; nonetheless it confirms the food is safe for regulatory
# submission."). The negation in the FIRST clause must NOT exempt the overclaim in
# the SECOND. We split on sentence terminators (.!?), hard clause separators (;:),
# and CONTRASTIVE conjunctions that start a new, independent assertion
# (however / nonetheless / nevertheless / but / yet / whereas / although / though /
# while), then classify EACH clause independently. A non-negated overclaim clause
# stays in the overclaim-scanned set even when it shares a string with a denial
# clause.
#
# We deliberately DO NOT split on the bare coordinating "and" / "or": those
# routinely join a negation to its tail inside ONE clause ("does not certify
# correctness, submission readiness, OR regulatory approval"), and splitting there
# would strip "regulatory approval" away from its governing negation and false-
# positive on a faithful protective disclaimer. The engine's own overclaim scanner
# is clause-scoped (negation must abut the phrase within one .,;: span), so an
# overclaim that genuinely needs isolating already ends a clause at a terminator or
# a contrastive conjunction.
_CLAUSE_SPLIT = re.compile(
    r"""
    (?: [.!?;:]+ )                                   # sentence / hard-clause terminator
    | (?: \s* \b(?:however|nonetheless|nevertheless|but|yet|whereas|
                   although|though|while)\b \s* )    # contrastive conjunction
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _clauses(text: str) -> list[str]:
    """Split one narrative leaf into clauses/sentences for PER-CLAUSE classification.
    Empty / whitespace-only fragments are dropped; if nothing splits out, the whole
    (stripped) string is returned as a single clause."""
    parts = [p.strip() for p in _CLAUSE_SPLIT.split(text) if p and p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def _split_narrative(*lists: Any) -> tuple[list[str], list[str]]:
    """De-dupe substantive narrative leaves and SPLIT them into
    (scanned_limitations, protective_caveats), classifying PER-CLAUSE.

    Each leaf is first split into clauses/sentences. A clause that is a protective
    non-claim denial (a NEGATED claim) goes to the NonClaimBoundary.requiredCaveats
    (negation-aware, NOT overclaim-scanned); EVERY OTHER clause — including a
    non-negated overclaim clause that merely shares a string with a denial clause —
    stays in the overclaim-scanned ``limitations`` so a genuine overclaim still bites
    FREE_TEXT_OVERCLAIM. Routing the whole leaf on a single global denial match (the
    pre-fix behaviour) let a non-negated overclaim launder past the scanner by being
    co-located with a denial clause."""
    scanned: list[str] = []
    caveats: list[str] = []
    seen: set[str] = set()
    for lst in lists:
        for s in lst:
            for clause in _clauses(s):
                if not _is_substantive_scalar(clause):
                    # a non-substantive fragment cannot mint scanned content and is
                    # not a meaningful caveat — drop it.
                    continue
                norm = _normalize_identifier(clause)
                if norm in seen:
                    continue
                seen.add(norm)
                if _is_protective_nonclaim_denial(clause):
                    caveats.append(clause)
                else:
                    scanned.append(clause)
    return scanned, caveats


def _toxmcp_envelope(
    *,
    object_id: str,
    object_type: str,
    review_state: dict[str, Any],
    limitations: list[str],
    extra_caveats: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schemaId": TOXMCP_OBJECT_SCHEMA_ID,
        "schemaDialect": "https://json-schema.org/draft/2020-12/schema",
        "schemaFamily": "dietary_exposure",
        "schemaMajor": 1,
        "schemaVersion": "1.0.0",
        "schemaDigest": _toxmcp_object_digest(),
        "packageVersion": "dietary-exposure-mcp",
        "objectId": object_id,
        "objectType": object_type,
        "createdAt": "1970-01-01T00:00:00Z",
        "createdBy": {
            "mcp": "dietary-exposure-mcp",
            "tool": object_type,
            "toolVersion": "1.0.0",
        },
        "provenance": {
            "schemaId": PROVENANCE_BUNDLE_SCHEMA_ID,
            "provenanceId": f"{object_id}:provenance",
            "sources": [],
            "transforms": [],
            "agents": [],
            "citations": [],
            "licensePolicy": "internal_only",
        },
        "assessmentRunRef": None,
        "audit": {
            "schemaId": AUDIT_TRACE_SCHEMA_ID,
            "auditTraceId": f"{object_id}:audit",
            "runId": object_id,
            "toolCallId": f"{object_id}:call",
            "requestHash": "sha256:" + "0" * 64,
            "responseHash": "sha256:" + "0" * 64,
            "schemaDigest": "sha256:" + "0" * 64,
            "chainHash": "sha256:" + "0" * 64,
        },
        "reviewState": review_state,
        "nonClaimBoundaries": [
            _protective_nonclaim_boundary(f"{object_id}:nonclaim", extra_caveats)
        ],
        "limitations": limitations,
        "knownDataGaps": [],
    }


def project_contaminant_interpretation_bundle(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project a ``contaminantMonitoringInterpretationBundle`` -> ToxMcpObject.v1."""
    _require(isinstance(source, dict), "Source bundle is not an object.")
    check_status = source.get("checkStatus")
    _require(
        isinstance(check_status, str) and _is_substantive_scalar(check_status),
        "interpretation bundle has no substantive checkStatus.",
        path="$.checkStatus",
    )

    embedded = _collect_narrative_leaves(source)
    scanned, caveats = _split_narrative(embedded)
    limitations = scanned or [
        "Contaminant monitoring interpretation bundle; review-support only, not a "
        "risk or regulatory conclusion."
    ]

    # A monitoring interpretation always requires human review before any
    # submission-grade use; it never self-certifies a publication.
    review_state = _review_state_for(
        f"{object_id}:review_state",
        publication_readiness="review_required",
        human_review="required",
        blockers=[],
    )
    return _toxmcp_envelope(
        object_id=object_id,
        object_type="contaminantMonitoringInterpretationBundle",
        review_state=review_state,
        limitations=limitations,
        extra_caveats=caveats,
    )


def project_contaminant_signoff_packet(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project a ``contaminantMonitoringSignoffPacket`` -> ToxMcpObject.v1.

    The REVIEW / SIGNOFF arm: the producer's declared ``overallSignoffStatus`` maps
    to publicationReadiness, and the declared ``unresolvedBlockingActionIds`` map to
    the ReviewState ``blockers``. A ``signed_off`` packet that still carries
    unresolved blocking actions bites READY_WITH_BLOCKERS; a ``signed_off`` packet
    whose review has not actually completed bites READY_WITH_PENDING_HUMAN_REVIEW —
    both reachable on producer-emittable contradictions."""
    _require(isinstance(source, dict), "Source signoff packet is not an object.")
    signoff_status = source.get("overallSignoffStatus")
    _require(
        isinstance(signoff_status, str) and signoff_status in _SIGNOFF_TO_READINESS,
        f"signoff packet has no recognized overallSignoffStatus: {signoff_status!r}",
        path="$.overallSignoffStatus",
    )
    assert isinstance(signoff_status, str)
    readiness = _SIGNOFF_TO_READINESS[signoff_status]
    # A genuinely signed-off packet has had human review; an open one is still pending.
    human_review = "passed" if readiness == "ready" else "required"
    blockers = _substantive_strings(source.get("unresolvedBlockingActionIds"))

    embedded = _collect_narrative_leaves(source)
    scanned, caveats = _split_narrative(embedded)
    limitations = scanned or [
        "Contaminant monitoring signoff packet; reviewer overlay only, not a risk or "
        "regulatory conclusion."
    ]
    review_state = _review_state_for(
        f"{object_id}:review_state",
        publication_readiness=readiness,
        human_review=human_review,
        blockers=blockers,
    )
    return _toxmcp_envelope(
        object_id=object_id,
        object_type="contaminantMonitoringSignoffPacket",
        review_state=review_state,
        limitations=limitations,
        extra_caveats=caveats,
    )


def project_adapter_review_bundle(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project an ``adapterReviewBundle`` -> ToxMcpObject.v1."""
    _require(isinstance(source, dict), "Source adapter review bundle is not an object.")
    review_status = source.get("review_status")
    _require(
        isinstance(review_status, str) and _is_substantive_scalar(review_status),
        "adapter review bundle has no substantive review_status.",
        path="$.review_status",
    )
    assert isinstance(review_status, str)
    # A review bundle is an internal interoperability review artifact; it always
    # requires human review before any release-grade use (it never self-certifies a
    # publication). The mismatch count is the declared blocker signal.
    mismatch = source.get("mismatch_field_count")
    blockers: list[str] = []
    if isinstance(mismatch, int) and not isinstance(mismatch, bool) and mismatch > 0:
        blockers.append(f"adapter_field_mismatch:{mismatch}")

    embedded = _collect_narrative_leaves(source)
    scanned, caveats = _split_narrative(embedded)
    limitations = scanned or [
        "Adapter review bundle; internal interoperability review only, not a risk or "
        "regulatory conclusion."
    ]
    review_state = _review_state_for(
        f"{object_id}:review_state",
        publication_readiness="review_required",
        human_review="required",
        blockers=blockers,
    )
    return _toxmcp_envelope(
        object_id=object_id,
        object_type="adapterReviewBundle",
        review_state=review_state,
        limitations=limitations,
        extra_caveats=caveats,
    )


# === BC-6 EXHAUSTIVE SWEEP: the remaining independent server-authored-conclusion
# === surfaces (every released object carrying free-text notes/limitations and/or a
# === signoff/blocking arm). Each projects to the SAME generic governed envelope
# === ToxMcpObject.v1, so the SAME invariants proven to bite on the contaminant
# === siblings (FREE_TEXT_OVERCLAIM on a narrative leaf; READY_WITH_BLOCKERS on a
# === signed-off packet still carrying unresolved blocking actions) bite here too.
# === This closes the metals-signoff LAUNDERING CHANNEL (a SIGNED_OFF packet emitted
# === while unresolvedBlockingActionIds is non-empty + an unchecked packet_note
# === appended to notes[]) by running it through the same projection + engine.


def _project_signoff_packet(
    source: dict[str, Any], *, object_id: str, object_type: str, fallback_limitation: str
) -> dict[str, Any]:
    """Generic REVIEW / SIGNOFF arm projection -> ToxMcpObject.v1, shared by every
    signoff packet (contaminant / metals / interoperability / scientific-follow-up
    owner). The producer's declared ``overallSignoffStatus`` maps to
    publicationReadiness and the declared ``unresolvedBlockingActionIds`` map to the
    ReviewState ``blockers`` — so a ``signed_off`` packet that still carries
    unresolved blocking actions bites READY_WITH_BLOCKERS, and any overclaim in the
    declared ``notes[]`` (e.g. an appended unchecked packet_note) bites
    FREE_TEXT_OVERCLAIM."""
    _require(isinstance(source, dict), f"Source {object_type} is not an object.")
    signoff_status = source.get("overallSignoffStatus")
    _require(
        isinstance(signoff_status, str) and signoff_status in _SIGNOFF_TO_READINESS,
        f"{object_type} has no recognized overallSignoffStatus: {signoff_status!r}",
        path="$.overallSignoffStatus",
    )
    assert isinstance(signoff_status, str)
    readiness = _SIGNOFF_TO_READINESS[signoff_status]
    human_review = "passed" if readiness == "ready" else "required"
    blockers = _substantive_strings(source.get("unresolvedBlockingActionIds"))

    # Deep-scan the WHOLE released object: every narrative leaf at any depth — the
    # top-level notes[], limitations[].message, AND every operator-supplied note
    # nested in actionItems[] (followUpNote / triggerNote / summary / ...) — so no
    # narrative escapes the FREE_TEXT_OVERCLAIM scan (the key-pattern collector keeps
    # it precise: only string leaves under a narrative-keyed field are harvested).
    embedded = _collect_narrative_leaves(source)
    scanned, caveats = _split_narrative(embedded)
    limitations = scanned or [fallback_limitation]
    review_state = _review_state_for(
        f"{object_id}:review_state",
        publication_readiness=readiness,
        human_review=human_review,
        blockers=blockers,
    )
    return _toxmcp_envelope(
        object_id=object_id,
        object_type=object_type,
        review_state=review_state,
        limitations=limitations,
        extra_caveats=caveats,
    )


def _project_review_document(
    source: dict[str, Any],
    *,
    object_id: str,
    object_type: str,
    fallback_limitation: str,
) -> dict[str, Any]:
    """Generic REVIEW / INTERPRETATION / DOSSIER projection -> ToxMcpObject.v1,
    shared by every narrative-bearing review document that is NOT a signoff packet
    (metals interpretation bundle, trade-risk review bundle, version-pinned review
    dossiers, sanitised public review dossier, follow-up board/queue/handoff/
    remediation). It always requires human review before any release-grade use (it
    never self-certifies a publication), and deep-scans the WHOLE released object:
    EVERY narrative leaf found recursively at any depth under the narrative
    KEY-PATTERN — the top-level ``notes[]`` / ``limitations[].message``, an embedded
    sub-report's ``qualityFlags[].message`` / per-jurisdiction ``notes[]`` /
    ``status_reason``, AND every operator-supplied note nested in ``actionItems[]``
    (``followUpNote`` / ``triggerNote`` / ``summary`` / ...) — so no narrative leaf,
    top-level or embedded, escapes the FREE_TEXT_OVERCLAIM scan."""
    _require(isinstance(source, dict), f"Source {object_type} is not an object.")
    embedded = _collect_narrative_leaves(source)
    scanned, caveats = _split_narrative(embedded)
    limitations = scanned or [fallback_limitation]
    review_state = _review_state_for(
        f"{object_id}:review_state",
        publication_readiness="review_required",
        human_review="required",
        blockers=[],
    )
    return _toxmcp_envelope(
        object_id=object_id,
        object_type=object_type,
        review_state=review_state,
        limitations=limitations,
        extra_caveats=caveats,
    )


# --- metals monitoring (the proven LAUNDERING CHANNEL sibling) ----------------


def project_metals_monitoring_interpretation_bundle(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project a ``metalsMonitoringInterpretationBundle`` -> ToxMcpObject.v1."""
    return _project_review_document(
        source,
        object_id=object_id,
        object_type="metalsMonitoringInterpretationBundle",
        fallback_limitation=(
            "Metals monitoring interpretation bundle; review-support only, not a "
            "risk or regulatory conclusion."
        ),
    )


def project_metals_monitoring_signoff_packet(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project a ``metalsMonitoringSignoffPacket`` -> ToxMcpObject.v1.

    THE LAUNDERING CHANNEL the BC-6 sweep closes: the metals signoff producer emits
    ``overallSignoffStatus=SIGNED_OFF`` while ``unresolvedBlockingActionIds`` is
    non-empty and appends ``packet_note`` to ``notes[]`` unchecked. Routed through
    the SAME generic signoff projection as its contaminant sibling, that now bites
    READY_WITH_BLOCKERS (signed-off + unresolved blockers) and FREE_TEXT_OVERCLAIM
    (an overclaiming note)."""
    return _project_signoff_packet(
        source,
        object_id=object_id,
        object_type="metalsMonitoringSignoffPacket",
        fallback_limitation=(
            "Metals monitoring signoff packet; reviewer overlay only, not a risk or "
            "regulatory conclusion."
        ),
    )


# --- trade-risk review (bundle embeds GlobalTradeRiskReport.notes) ------------


def project_trade_risk_review_bundle(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project a ``tradeRiskReviewBundle`` -> ToxMcpObject.v1. The embedded
    ``tradeReport`` (a GlobalTradeRiskReport) carries server-authored conclusion
    narrative at MANY leaves — not only ``tradeReport.notes[]`` but also
    ``tradeReport.qualityFlags[].message``, each ``jurisdiction_profiles[].notes[]``,
    ``jurisdiction_profiles[].quality_flags[]``/``mrl_violations[].message`` and a
    narrative ``jurisdiction_profiles[].status_reason``. The whole embedded report is
    deep-scanned recursively (every narrative leaf at any depth) alongside the
    bundle's own ``notes`` / ``limitations``, so an overclaim in ANY of those leaves
    bites FREE_TEXT_OVERCLAIM. The whole released object (bundle + embedded
    ``tradeReport``) is deep-scanned by the generic review-document projection."""
    _require(isinstance(source, dict), "Source trade-risk review bundle is not an object.")
    return _project_review_document(
        source,
        object_id=object_id,
        object_type="tradeRiskReviewBundle",
        fallback_limitation=(
            "Trade-risk review bundle; internal review only, not a risk or "
            "regulatory conclusion."
        ),
    )


# --- interoperability signoff -------------------------------------------------


def project_interoperability_signoff_packet(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project an ``interoperabilitySignoffPacket`` -> ToxMcpObject.v1."""
    return _project_signoff_packet(
        source,
        object_id=object_id,
        object_type="interoperabilitySignoffPacket",
        fallback_limitation=(
            "Interoperability signoff packet; reviewer overlay only, not a risk or "
            "regulatory conclusion."
        ),
    )


# --- scientific follow-up owner signoff ---------------------------------------


def project_scientific_follow_up_owner_signoff_packet(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project a ``scientificFollowUpOwnerSignoffPacket`` -> ToxMcpObject.v1."""
    return _project_signoff_packet(
        source,
        object_id=object_id,
        object_type="scientificFollowUpOwnerSignoffPacket",
        fallback_limitation=(
            "Scientific follow-up owner signoff packet; reviewer overlay only, not a "
            "risk or regulatory conclusion."
        ),
    )


# --- sanitised public review dossier (PUBLIC-released narrative) --------------


def project_sanitised_public_review_dossier(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project a ``sanitisedPublicReviewDossier`` -> ToxMcpObject.v1. This is a
    PUBLIC-release artifact, so its declared ``notes[]`` / ``limitations[]`` narrative
    is the highest-stakes overclaim surface; the embedded ``publicReviewBundle`` is
    deep-scanned recursively (every narrative leaf at any depth — its own notes plus
    any nested report/message/reason narrative) too, via the whole-object scan in the
    generic review-document projection."""
    _require(isinstance(source, dict), "Source sanitised review dossier is not an object.")
    return _project_review_document(
        source,
        object_id=object_id,
        object_type="sanitisedPublicReviewDossier",
        fallback_limitation=(
            "Sanitised public review dossier; review-support disclosure only, not a "
            "risk or regulatory conclusion."
        ),
    )


# === BC-6 FINAL: the four remaining UNGATED top-level operator-note SINK results.
# === dietary_export_scientific_follow_up_queue_bundle (bundle_note),
# === scientificFollowUpReviewBoard (board_note),
# === scientificFollowUpOwnerHandoffPacket / OwnerRemediationPacket (packet_note)
# === each append the operator-controlled note VERBATIM into a server-authored
# === producer ``notes[]``, then land in a TOP-LEVEL MCP tool result that no gated
# === surface traversed — so an operator could launder a safety/regulatory overclaim
# === that the engine never saw. Each is a follow-up REVIEW document (its readiness
# === signal is ``overallStatus``, NOT a signoff status — there is no producer-
# === emittable ``overallSignoffStatus``, so the signoff/READY_WITH_BLOCKERS arm is
# === unreachable here and intentionally NOT projected), so each routes through the
# === SAME generic review-document projection that deep-scans every declared narrative
# === leaf (notes[] + limitations[].message) for FREE_TEXT_OVERCLAIM — closing the
# === sink. (The follow-up SIGNOFF arm — scientificFollowUpOwnerSignoffPacket — that
# === DOES carry overallSignoffStatus is already gated through _project_signoff_packet
# === and bites READY_WITH_BLOCKERS on the SIGNED_OFF + unresolved-blockers laundering.)


def project_scientific_follow_up_queue_bundle(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project a ``scientificFollowUpQueueBundle`` -> ToxMcpObject.v1 (review doc).
    Closes the ``bundle_note`` -> ``notes[]`` operator-note sink."""
    return _project_review_document(
        source,
        object_id=object_id,
        object_type="scientificFollowUpQueueBundle",
        fallback_limitation=(
            "Scientific follow-up queue bundle; reviewer routing only, not a risk or "
            "regulatory conclusion."
        ),
    )


def project_scientific_follow_up_review_board(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project a ``scientificFollowUpReviewBoard`` -> ToxMcpObject.v1 (review doc).
    Closes the ``board_note`` -> ``notes[]`` operator-note sink."""
    return _project_review_document(
        source,
        object_id=object_id,
        object_type="scientificFollowUpReviewBoard",
        fallback_limitation=(
            "Scientific follow-up review board; reviewer routing only, not a risk or "
            "regulatory conclusion."
        ),
    )


def project_scientific_follow_up_owner_handoff_packet(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project a ``scientificFollowUpOwnerHandoffPacket`` -> ToxMcpObject.v1 (review
    doc). Closes the ``packet_note`` -> ``notes[]`` operator-note sink."""
    return _project_review_document(
        source,
        object_id=object_id,
        object_type="scientificFollowUpOwnerHandoffPacket",
        fallback_limitation=(
            "Scientific follow-up owner handoff packet; reviewer routing only, not a "
            "risk or regulatory conclusion."
        ),
    )


def project_scientific_follow_up_owner_remediation_packet(
    source: dict[str, Any], *, object_id: str
) -> dict[str, Any]:
    """Project a ``scientificFollowUpOwnerRemediationPacket`` -> ToxMcpObject.v1
    (review doc). Closes the ``packet_note`` -> ``notes[]`` operator-note sink."""
    return _project_review_document(
        source,
        object_id=object_id,
        object_type="scientificFollowUpOwnerRemediationPacket",
        fallback_limitation=(
            "Scientific follow-up owner remediation packet; reviewer routing only, "
            "not a risk or regulatory conclusion."
        ),
    )
