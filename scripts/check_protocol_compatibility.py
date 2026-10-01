"""Fail if isolated legacy and modern clients observe different contracts or results."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy", type=Path)
    parser.add_argument("modern", type=Path)
    parser.add_argument("--baseline", type=Path, default=Path(
        "tests/compatibility/v0.1.1-catalog-sha256.json"))
    args = parser.parse_args()
    legacy = json.loads(args.legacy.read_text())
    modern = json.loads(args.modern.read_text())
    baseline = json.loads(args.baseline.read_text())
    assert legacy["clientSdk"] == "1.30.0"
    assert legacy["protocol"] == "2025-11-25"
    assert modern["clientSdk"] == "2.2.0"
    assert modern["protocol"] == "2026-07-28"
    assert legacy["catalog"] == modern["catalog"], "Wire catalog drift between client generations"
    assert legacy["results"] == modern["results"], "Scientific/output drift between client generations"
    observed = {}
    for key, items in modern["catalog"].items():
        observed[key] = {}
        for item in items:
            name = str(item.get("name", item.get("uri", item.get("uriTemplate"))))
            canonical = json.dumps(item, sort_keys=True, separators=(",", ":"))
            observed[key][name] = hashlib.sha256(canonical.encode()).hexdigest()
    assert observed == baseline["catalog"], "Wire catalog drift from released v0.1.1 wheel"
    print("Legacy/modern compatibility passed: 49 tools, 34 resources, 32 templates, 7 workflows.")


if __name__ == "__main__":
    main()
