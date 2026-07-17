from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from tests.fixtures.cross_suite.woe_roundtrip import (  # noqa: E402
    WOE_ROUNDTRIP_FIXTURE_PATH,
    build_dietary_woe_roundtrip_bundle,
)


def _identifier_values(item: dict[str, object], identifier_type: str) -> list[str]:
    values: list[str] = []
    for identifier in item.get("studyIdentifiers", []):
        if not isinstance(identifier, dict):
            continue
        if identifier.get("identifierType") == identifier_type:
            value = identifier.get("identifierValue")
            if isinstance(value, str):
                values.append(value)
    return sorted(values)


def test_dietary_woe_roundtrip_bundle_matches_checked_in_fixture() -> None:
    generated = build_dietary_woe_roundtrip_bundle()
    fixture = json.loads(WOE_ROUNDTRIP_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert generated == fixture


def test_dietary_woe_roundtrip_bundle_preserves_food_mediated_semantics() -> None:
    bundle = build_dietary_woe_roundtrip_bundle()
    evidence_items = bundle["evidenceItems"]

    assert len(evidence_items) == 2
    assert {item["oralExposureContext"] for item in evidence_items} == {"food_mediated"}
    assert {item["intendedUseFamily"] for item in evidence_items} == {"dietary"}
    assert {item["productCategory"] for item in evidence_items} == {"food_mediated_residue"}

    intake_windows = {
        value
        for item in evidence_items
        for value in _identifier_values(item, "intake_window_semantic")
    }
    scenario_classes = {
        value
        for item in evidence_items
        for value in _identifier_values(item, "scenario_class")
    }
    upstream_types = {
        ref["objectTypeRef"]
        for item in evidence_items
        for ref in item["upstreamArtifactRefs"]
    }

    assert intake_windows == {"acute", "chronic"}
    assert scenario_classes == {"bounded_acute", "point_estimate"}
    assert upstream_types == {
        "DietaryIntakeScenarioDefinition",
        "DietaryIntakeSummary",
        "RouteDoseEstimate",
        "PbpkExternalImportBundle",
        "ToxclawDietaryEvidenceBundle",
    }
    assert all(
        ref["producerModule"] == "dietary_exposure"
        and ref["integrityHash"].startswith("sha256:")
        for item in evidence_items
        for ref in item["upstreamArtifactRefs"]
    )
