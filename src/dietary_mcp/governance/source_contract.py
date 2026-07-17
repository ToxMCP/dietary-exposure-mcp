"""Fail-closed PRODUCER EMISSION-CONTRACT validation for the iata-mcp Track-B gate.

Before projecting any RELEASED iata-testing-strategy object onto the spine, the
gate MUST validate the raw source packet against the producer's STRICT emission
contract — the ``additionalProperties:false`` JSON schema under
``schemas/spine-emission-contract/`` that mirrors what the REAL producer seam
stamps:

* ``strategyReviewPacket`` — emitted by ``buildStrategyReviewPacket``
  (src/renderers/PacketBuilderService.ts);
* ``rankedActionPlan`` — emitted by the planning orchestrator / import
  normalization (RankedActionPlanSchema);
* ``strategyVerificationSummary`` — emitted by ``verifyStrategyBundle``
  (src/verification/VerificationService.ts);
* ``semanticLossEvent`` — emitted on each import semantic-loss record
  (SemanticLossEventSchema, src/services/import/import-contract-schemas.ts).

WHY THIS GUARD EXISTS (the dead-arm root cause it closes)
---------------------------------------------------------
A gate that projects FIRST and validates never (or validates a projected object,
not the source packet) can "advertise" public-release-blocking codes whose only
trigger is a SOURCE field the producer's own strict contract cannot carry, or a
field the projection synthesizes as a CONSTANT. Such a code bites only on a
hand-crafted, schema-INVALID fixture (one carrying an undeclared root field, or a
hand-mutated projected object) and NEVER on a packet the real producer emits — a
DEAD ARM.

This module is the structural fix: every source packet is validated against the
strict emission schema for its corpus kind at the TOP of ``run_gate`` BEFORE any
projection. A packet that FAILS the producer contract is a
``SOURCE_CONTRACT_VIOLATION`` meta finding that BLOCKS (exit 1) and is NEVER
projected / safe-defaulted. An undeclared root field (a smuggled ``releaseRef`` /
``versionPins`` payload, or a ``lossClass`` value the producer enum cannot emit)
is rejected here, so the dead-arm class cannot silently return.

TIGHTEN-NOT-WIDEN / DECLARE-WHAT-THE-PRODUCER-STAMPS
---------------------------------------------------
The published ``schemas/core/*.1.0.0.json`` are ``additionalProperties:false``
Draft-07 schemas, but they (a) use ``$ref``/``definitions`` indirection and the
permissive ``MetadataEnvelope`` superset (``releaseRef`` / ``versionPins`` /
``operatorAnnotations`` / ``upstreamRefs`` / ``reviewContext`` / ...), and (b)
declare envelope optionals the three target producers NEVER stamp. The emission
schemas here are the TIGHTENED, self-contained mirrors: flat (no ``$ref``),
``additionalProperties:false`` at every object level, declaring EXACTLY the field
set the real producer seam emits (recon'd by reading the producers and the
producer Zod schemas — not stale fixtures). They are a STRICT SUBSET of the
published schema (every object they accept the published schema also accepts), so
they never under-validate.

FAIL-CLOSED / DEPENDENCY-FREE
-----------------------------
The validator is a small, self-contained Draft-07 *subset* checker covering
exactly the keywords the emission schemas use (``type`` — string OR a list of
primitive type-names, ``properties``, ``required``, ``enum``, ``const``,
``additionalProperties``, ``items``, ``minItems``, ``maxItems``, ``minLength``,
``minimum``, ``maximum``, ``format: date-time``). It depends on nothing outside
the standard library, so the guard can never be silently skipped because an
optional dependency is missing. A schema we cannot load, a corpus kind with no
registered schema, or a keyword we do not recognise appearing in the schema, is
itself treated as a hard block (we refuse to under-validate).
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import Any

from dietary_mcp.governance.errors import (
    SOURCE_CONTRACT_VIOLATION,
    BlockingFinding,
)

__all__ = ["SOURCE_CONTRACT_VIOLATION", "validate_source_packet", "schema_path_for_kind"]

# .../src/dietary_mcp/governance/source_contract.py -> repo root is parents[3].
_REPO_ROOT = Path(__file__).resolve().parents[3]
_EMISSION_DIR = _REPO_ROOT / "schemas" / "spine-emission-contract"

# Corpus projection-kind -> producer emission schema file. Each file is the
# TIGHTENED, self-contained (no $ref) additionalProperties:false mirror of the
# released docs/contracts/schemas/<name>.v1.json, declaring EXACTLY the field set
# the REAL producer seam stamps (recon'd by running DietaryRuntime + the export
# builders with model_dump(mode="json", by_alias=True), incl optional-field paths
# — not stale committed examples, which fail their own released schemas).
_KIND_TO_SCHEMA: dict[str, str] = {
    "dietary_intake_summary": "dietaryIntakeSummary.emission.v1.json",
    "contaminant_interpretation_bundle": (
        "contaminantMonitoringInterpretationBundle.emission.v1.json"
    ),
    "contaminant_signoff_packet": (
        "contaminantMonitoringSignoffPacket.emission.v1.json"
    ),
    "adapter_review_bundle": "adapterReviewBundle.emission.v1.json",
    # --- BC-6 exhaustive-sweep newly-gated surfaces ----------------------------
    "metals_interpretation_bundle": (
        "metalsMonitoringInterpretationBundle.emission.v1.json"
    ),
    "metals_signoff_packet": "metalsMonitoringSignoffPacket.emission.v1.json",
    "trade_risk_review_bundle": "tradeRiskReviewBundle.emission.v1.json",
    "interoperability_signoff_packet": (
        "interoperabilitySignoffPacket.emission.v1.json"
    ),
    "scientific_follow_up_owner_signoff_packet": (
        "scientificFollowUpOwnerSignoffPacket.emission.v1.json"
    ),
    "sanitised_public_review_dossier": (
        "sanitisedPublicReviewDossier.emission.v1.json"
    ),
    # --- BC-6 FINAL: the four remaining ungated operator-note SINK results -------
    "scientific_follow_up_queue_bundle": (
        "scientificFollowUpQueueBundle.emission.v1.json"
    ),
    "scientific_follow_up_review_board": (
        "scientificFollowUpReviewBoard.emission.v1.json"
    ),
    "scientific_follow_up_owner_handoff_packet": (
        "scientificFollowUpOwnerHandoffPacket.emission.v1.json"
    ),
    "scientific_follow_up_owner_remediation_packet": (
        "scientificFollowUpOwnerRemediationPacket.emission.v1.json"
    ),
}

# Bounded set of Draft-07 keywords the emission schemas use. A schema growing a
# keyword outside this set is REFUSED at load (fail-closed: never under-validate).
_SUPPORTED_KEYWORDS: frozenset[str] = frozenset(
    {
        "$schema", "$id", "title", "description", "type", "properties",
        "required", "enum", "const", "additionalProperties", "items",
        "minItems", "maxItems", "minLength", "minimum", "maximum", "format",
        "default",
    }
)

_PRIMITIVE_TYPES: frozenset[str] = frozenset(
    {"object", "array", "string", "boolean", "number", "integer", "null"}
)

# RFC3339 date-time (the only ``format`` the schemas use).
_DATE_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$"
)


class SchemaUnsupportedError(Exception):
    """The emission schema uses a keyword/type the validator does not enforce.

    Raised at load time so the gate fails closed rather than under-validating.
    """


def schema_path_for_kind(kind: str) -> Path:
    name = _KIND_TO_SCHEMA.get(kind)
    if name is None:
        raise SchemaUnsupportedError(
            f"No producer emission schema registered for corpus kind {kind!r}; "
            "the source-contract guard refuses to under-validate."
        )
    return _EMISSION_DIR / name


def _assert_supported(node: Any, where: str) -> None:
    """Recursively confirm every schema node uses only enforced keywords/types."""
    if not isinstance(node, dict):
        return
    for key in node:
        if key not in _SUPPORTED_KEYWORDS:
            raise SchemaUnsupportedError(
                f"Emission schema uses unsupported keyword {key!r} at {where}; "
                "the source-contract validator refuses to under-validate."
            )
    declared_type = node.get("type")
    if isinstance(declared_type, str):
        if declared_type not in _PRIMITIVE_TYPES:
            raise SchemaUnsupportedError(
                f"Unsupported type {declared_type!r} at {where}."
            )
    elif isinstance(declared_type, list):
        for t in declared_type:
            if t not in _PRIMITIVE_TYPES:
                raise SchemaUnsupportedError(
                    f"Unsupported type {t!r} in type-list at {where}."
                )
    elif declared_type is not None:
        raise SchemaUnsupportedError(f"Malformed type at {where}: {declared_type!r}")

    props = node.get("properties")
    if isinstance(props, dict):
        for pname, subschema in props.items():
            _assert_supported(subschema, f"{where}.properties.{pname}")
    items = node.get("items")
    if isinstance(items, dict):
        _assert_supported(items, f"{where}.items")


@cache
def _emission_schema(kind: str) -> dict[str, Any]:
    path = schema_path_for_kind(kind)
    schema = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise SchemaUnsupportedError("Emission schema root is not an object.")
    _assert_supported(schema, "$")
    return schema


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _type_matches(value: Any, declared: Any) -> bool:
    if isinstance(declared, str):
        return _type_ok(value, declared)
    if isinstance(declared, list):
        return any(_type_ok(value, t) for t in declared)
    return True  # no declared type -> no type constraint


def _validate(node: dict[str, Any], value: Any, path: str, errors: list[str]) -> None:
    declared_type = node.get("type")
    if declared_type is not None and not _type_matches(value, declared_type):
        errors.append(f"{path}: expected type {declared_type!r}")
        return  # type mismatch makes deeper checks meaningless

    if "const" in node and value != node["const"]:
        errors.append(f"{path}: expected const {node['const']!r}")

    if "enum" in node and value not in node["enum"]:
        errors.append(f"{path}: value {value!r} not in enum {node['enum']!r}")

    if isinstance(value, str):
        min_len = node.get("minLength")
        if isinstance(min_len, int) and len(value) < min_len:
            errors.append(f"{path}: shorter than minLength {min_len}")
        if node.get("format") == "date-time" and not _DATE_TIME_RE.match(value):
            errors.append(f"{path}: not an RFC3339 date-time")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = node.get("minimum")
        if isinstance(minimum, (int, float)) and value < minimum:
            errors.append(f"{path}: less than minimum {minimum}")
        maximum = node.get("maximum")
        if isinstance(maximum, (int, float)) and value > maximum:
            errors.append(f"{path}: greater than maximum {maximum}")

    if isinstance(value, dict):
        props: dict[str, Any] = node.get("properties", {}) or {}
        for req in node.get("required", []) or []:
            if req not in value:
                errors.append(f"{path}: missing required property {req!r}")
        # additionalProperties:false is the load-bearing strict guard — an
        # undeclared field is a contract violation (closes the smuggling vector).
        if node.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(
                        f"{path}: additional property {key!r} is not permitted "
                        "(producer emission contract is additionalProperties:false)"
                    )
        for key, subschema in props.items():
            if key in value and isinstance(subschema, dict):
                _validate(subschema, value[key], f"{path}.{key}", errors)

    if isinstance(value, list):
        min_items = node.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(f"{path}: fewer than minItems {min_items}")
        max_items = node.get("maxItems")
        if isinstance(max_items, int) and len(value) > max_items:
            errors.append(f"{path}: more than maxItems {max_items}")
        item_schema = node.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(value):
                _validate(item_schema, item, f"{path}[{idx}]", errors)


def validate_source_packet(
    source: Any, *, kind: str, corpus: str
) -> BlockingFinding | None:
    """Validate one raw source packet against its producer STRICT emission schema.

    Returns a ``SOURCE_CONTRACT_VIOLATION`` blocking meta finding if the packet
    fails the contract (including any undeclared / schema-forbidden field, since
    every object level is ``additionalProperties:false``), else ``None``.

    A schema we cannot load / fully enforce, or a kind with no registered schema,
    is itself a hard block (fail-closed).
    """
    try:
        schema = _emission_schema(kind)
        schema_name = schema_path_for_kind(kind).name
    except (OSError, json.JSONDecodeError, SchemaUnsupportedError) as exc:
        return BlockingFinding.meta(
            SOURCE_CONTRACT_VIOLATION,
            f"Producer emission schema could not be loaded/enforced: {exc}",
            path="$",
            corpus=corpus,
        )

    errors: list[str] = []
    _validate(schema, source, "$", errors)
    if errors:
        return BlockingFinding.meta(
            SOURCE_CONTRACT_VIOLATION,
            "Source packet violates the producer's strict emission contract "
            f"({schema_name}): " + "; ".join(errors[:8]),
            path=errors[0].split(":", 1)[0] if errors else "$",
            corpus=corpus,
        )
    return None
