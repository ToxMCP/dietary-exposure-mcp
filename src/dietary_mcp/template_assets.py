from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.errors import DietaryRegistryError


def _template_root(repo_root: Path) -> Path:
    candidate = repo_root / "templates" / "adapter_inputs"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "templates" / "adapter_inputs"


def read_adapter_template_manifest(repo_root: Path) -> dict:
    root = _template_root(repo_root)
    return json.loads((root / "manifest.json").read_text())


def read_adapter_template(repo_root: Path, template_name: str) -> str:
    manifest = read_adapter_template_manifest(repo_root)
    for item in manifest["templates"]:
        if item["name"] == template_name:
            return (_template_root(repo_root) / Path(item["path"]).name).read_text()
    raise DietaryRegistryError(
        code="unknown_adapter_template",
        message=f"Unknown adapter template: {template_name}",
        suggestion="Use a template listed in adapter-input-templates://manifest.",
    )
