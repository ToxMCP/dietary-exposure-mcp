from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from tests.fixtures.cross_suite.woe_roundtrip import (  # noqa: E402
    IVIVE_SYNC_TARGET_PATH,
    WOE_ROUNDTRIP_FIXTURE_PATH,
    WOE_SYNC_TARGET_PATH,
    build_dietary_woe_roundtrip_bundle,
    write_dietary_woe_roundtrip_bundle,
)


def _stable_json(payload: object) -> str:
    return f"{json.dumps(payload, indent=2, sort_keys=True)}\n"


def _sync(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the deterministic Dietary -> WoE cross-suite source fixture."
    )
    parser.add_argument("--write", action="store_true", help="Write the checked-in fixture.")
    parser.add_argument(
        "--sync-woe-target",
        action="store_true",
        help="Sync the checked-in source fixture into the WoE repo fixture path.",
    )
    parser.add_argument(
        "--sync-ivive-target",
        action="store_true",
        help="Sync the checked-in source fixture into the IVIVE upstream fixture path.",
    )
    args = parser.parse_args()

    generated = build_dietary_woe_roundtrip_bundle()
    next_payload = _stable_json(generated)

    if args.write:
        write_dietary_woe_roundtrip_bundle()
        print(f"Wrote Dietary -> WoE source fixture: {WOE_ROUNDTRIP_FIXTURE_PATH}")
    else:
        current = WOE_ROUNDTRIP_FIXTURE_PATH.read_text(encoding="utf-8")
        if current != next_payload:
            raise SystemExit(
                "Dietary -> WoE source fixture is stale: "
                f"{WOE_ROUNDTRIP_FIXTURE_PATH}\n"
                "Run: uv run python scripts/generate_dietary_woe_roundtrip_bundle.py --write"
            )
        print(f"Dietary -> WoE source fixture is current: {WOE_ROUNDTRIP_FIXTURE_PATH}")

    if args.sync_woe_target:
        _sync(WOE_ROUNDTRIP_FIXTURE_PATH, WOE_SYNC_TARGET_PATH)
        print(f"Synced Dietary source fixture into WoE: {WOE_SYNC_TARGET_PATH}")

    if args.sync_ivive_target:
        _sync(WOE_ROUNDTRIP_FIXTURE_PATH, IVIVE_SYNC_TARGET_PATH)
        print(f"Synced Dietary source fixture into IVIVE: {IVIVE_SYNC_TARGET_PATH}")


if __name__ == "__main__":
    main()
