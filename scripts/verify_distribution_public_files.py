#!/usr/bin/env python3
"""Verify public notices, citation metadata, and package metadata in built distributions."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from email.parser import BytesParser
from email.policy import default
from pathlib import Path


REQUIRED_PROJECT_URL_LABELS = {"Homepage", "Repository", "Documentation", "Issues", "Security"}


def _single_match(paths: list[Path], pattern: str) -> Path:
    matches = [path for path in paths if path.match(pattern)]
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one {pattern!r} artifact, found {len(matches)}.")
    return matches[0]


def _verify_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise SystemExit(f"{path.name}: expected one METADATA file, found {len(metadata_names)}.")
        metadata_name = metadata_names[0]
        license_root = metadata_name.removesuffix("METADATA") + "licenses/"
        required_names = {
            f"{license_root}LICENSE",
            f"{license_root}THIRD_PARTY_NOTICES.md",
        }
        missing = sorted(required_names - names)
        if missing:
            raise SystemExit(f"{path.name}: missing wheel public files: {', '.join(missing)}")

        metadata = BytesParser(policy=default).parsebytes(archive.read(metadata_name))
        if metadata.get("License-Expression") != "Apache-2.0":
            raise SystemExit(f"{path.name}: missing Apache-2.0 License-Expression metadata.")
        project_url_labels = {
            value.split(",", 1)[0].strip() for value in metadata.get_all("Project-URL", [])
        }
        missing_urls = sorted(REQUIRED_PROJECT_URL_LABELS - project_url_labels)
        if missing_urls:
            raise SystemExit(f"{path.name}: missing Project-URL labels: {', '.join(missing_urls)}")


def _verify_sdist(path: Path) -> None:
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
        roots = {name.split("/", 1)[0] for name in names if "/" in name}
        if len(roots) != 1:
            raise SystemExit(f"{path.name}: expected one source-distribution root, found {len(roots)}.")
        root = next(iter(roots))
        required_names = {
            f"{root}/CITATION.cff",
            f"{root}/LICENSE",
            f"{root}/README.md",
            f"{root}/THIRD_PARTY_NOTICES.md",
        }
        missing = sorted(required_names - set(names))
        if missing:
            raise SystemExit(f"{path.name}: missing sdist public files: {', '.join(missing)}")


def verify_distribution_public_files(dist_dir: Path) -> None:
    artifacts = [path for path in dist_dir.iterdir() if path.is_file()]
    wheel = _single_match(artifacts, "*.whl")
    sdist = _single_match(artifacts, "*.tar.gz")
    _verify_wheel(wheel)
    _verify_sdist(sdist)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", type=Path, help="Directory containing exactly one wheel and one sdist.")
    args = parser.parse_args()
    verify_distribution_public_files(args.dist_dir.resolve())
    print(f"Public distribution files verified: {args.dist_dir.resolve()}")


if __name__ == "__main__":
    main()
