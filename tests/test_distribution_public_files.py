from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.verify_distribution_public_files import verify_distribution_public_files


def _write_distribution_pair(dist_dir: Path, *, include_notice: bool = True) -> None:
    wheel = dist_dir / "dietary_mcp-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "dietary_mcp-0.1.0.dist-info/METADATA",
            "\n".join(
                [
                    "Metadata-Version: 2.4",
                    "Name: dietary-mcp",
                    "Version: 0.1.0",
                    "License-Expression: Apache-2.0",
                    *(f"Project-URL: {label}, https://example.test" for label in sorted({"Homepage", "Repository", "Documentation", "Issues", "Security"})),
                    "",
                ]
            ),
        )
        archive.writestr("dietary_mcp-0.1.0.dist-info/licenses/LICENSE", "Apache-2.0")
        if include_notice:
            archive.writestr("dietary_mcp-0.1.0.dist-info/licenses/THIRD_PARTY_NOTICES.md", "notices")

    source_root = dist_dir / "dietary_mcp-0.1.0"
    source_root.mkdir()
    for name in ("CITATION.cff", "LICENSE", "README.md", "THIRD_PARTY_NOTICES.md"):
        (source_root / name).write_text(name, encoding="utf-8")
    with tarfile.open(dist_dir / "dietary_mcp-0.1.0.tar.gz", "w:gz") as archive:
        archive.add(source_root, arcname=source_root.name)


def test_distribution_public_files_accepts_complete_pair(tmp_path: Path) -> None:
    _write_distribution_pair(tmp_path)
    verify_distribution_public_files(tmp_path)


def test_distribution_public_files_rejects_missing_notice(tmp_path: Path) -> None:
    _write_distribution_pair(tmp_path, include_notice=False)
    with pytest.raises(SystemExit, match="THIRD_PARTY_NOTICES.md"):
        verify_distribution_public_files(tmp_path)
