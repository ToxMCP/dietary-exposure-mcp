from pathlib import Path

from dietary_mcp.adapter_walkthroughs import build_adapter_walkthrough, build_adapter_walkthrough_manifest


def test_adapter_walkthrough_manifest_and_payload() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    manifest = build_adapter_walkthrough_manifest(repo_root)
    walkthrough_names = {item["name"] for item in manifest["walkthroughs"]}

    assert {"efsa_primo_tabular_alias_case", "epa_deem_csv_alias_case"}.issubset(walkthrough_names)

    walkthrough = build_adapter_walkthrough(repo_root, "efsa_primo_tabular_alias_case")
    projection = walkthrough["expectedNormalizedProjection"]

    assert walkthrough["templateName"] == "efsa_primo_tabular_template"
    assert walkthrough["validationStatus"] == "ok"
    assert projection["commodityCodes"] == ["apples", "milk"]
    assert "external_adapter_normalized" in projection["qualityFlagCodes"]
    assert "efsa.primo" in projection["sourceIds"]
