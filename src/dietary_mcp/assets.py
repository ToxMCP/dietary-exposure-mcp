from __future__ import annotations

import shutil
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PACKAGED_DATA_ROOT = PACKAGE_ROOT / "data"


def source_checkout_root() -> Path | None:
    candidate = PACKAGE_ROOT.parents[1]
    # Identify a source checkout by committed markers only. The previous
    # marker (Dietary_MCP_tasks.json) matches *_tasks.json in .gitignore, so
    # it is absent in CI/clean checkouts and detection silently failed there.
    if (candidate / "pyproject.toml").exists() and (candidate / "src" / "dietary_mcp" / "__init__.py").exists():
        return candidate
    return None


def runtime_asset_root() -> Path:
    checkout_root = source_checkout_root()
    if checkout_root and (checkout_root / "defaults" / "v1" / "core_defaults.json").exists():
        return checkout_root
    return PACKAGED_DATA_ROOT


def can_generate_repo_artifacts() -> bool:
    return source_checkout_root() is not None


def sync_packaged_data(source_root: Path) -> Path:
    data_root = PACKAGED_DATA_ROOT
    mappings = [
        (source_root / "defaults", data_root / "defaults", "manifest.json"),
        (source_root / "defaults" / "v1", data_root / "defaults" / "v1", "*.json"),
        (source_root / "config", data_root / "config", "*.json"),
        (source_root / "validation" / "v1", data_root / "validation" / "v1", "*.json"),
        (source_root / "docs", data_root / "docs", "*.md"),
        (source_root / "evals", data_root / "evals", "*.xml"),
        (source_root / "templates" / "adapter_inputs", data_root / "templates" / "adapter_inputs", "*.json"),
        (source_root / "templates" / "adapter_inputs", data_root / "templates" / "adapter_inputs", "*.csv"),
    ]
    for source_dir, target_dir, pattern in mappings:
        target_dir.mkdir(parents=True, exist_ok=True)
        for source_path in sorted(source_dir.glob(pattern)):
            shutil.copy2(source_path, target_dir / source_path.name)

    extensions_readme = source_root / "defaults" / "extensions" / "README.md"
    if extensions_readme.exists():
        target_dir = data_root / "defaults" / "extensions"
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(extensions_readme, target_dir / "README.md")
    extensions_root = source_root / "defaults" / "extensions" / "v1"
    if extensions_root.exists():
        for source_path in sorted(extensions_root.rglob("*.json")):
            relative_path = source_path.relative_to(source_root / "defaults" / "extensions")
            target_path = data_root / "defaults" / "extensions" / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
    return data_root
