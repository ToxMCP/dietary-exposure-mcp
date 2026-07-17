from __future__ import annotations

import argparse
import copy
import gzip
import os
import stat
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


def _validate_member(member: tarfile.TarInfo, seen: set[str]) -> None:
    path = PurePosixPath(member.name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe sdist member path: {member.name}")
    if member.name in seen:
        raise ValueError(f"Duplicate sdist member path: {member.name}")
    if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
        raise ValueError(f"Unsupported sdist member type: {member.name}")
    seen.add(member.name)


def normalize_sdist(path: Path, *, epoch: int) -> None:
    """Rewrite an sdist with stable ordering, ownership, and timestamps."""
    path = path.resolve()
    original_mode = stat.S_IMODE(path.stat().st_mode)
    with tarfile.open(path, mode="r:gz") as source:
        members = source.getmembers()
        seen: set[str] = set()
        for member in members:
            _validate_member(member, seen)

        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as raw_output:
            temporary_path = Path(raw_output.name)
            with gzip.GzipFile(
                filename="",
                mode="wb",
                compresslevel=9,
                fileobj=raw_output,
                mtime=epoch,
            ) as compressed_output:
                with tarfile.open(
                    fileobj=compressed_output,
                    mode="w",
                    format=tarfile.PAX_FORMAT,
                ) as destination:
                    for source_member in sorted(members, key=lambda item: item.name):
                        member = copy.copy(source_member)
                        member.mtime = epoch
                        member.uid = 0
                        member.gid = 0
                        member.uname = ""
                        member.gname = ""
                        member.pax_headers = {}
                        payload = source.extractfile(source_member) if source_member.isfile() else None
                        destination.addfile(member, payload)

    try:
        os.chmod(temporary_path, original_mode)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize Python source distributions reproducibly.")
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument(
        "--epoch",
        type=int,
        default=int(os.environ.get("SOURCE_DATE_EPOCH", "0")),
        help="Timestamp applied to gzip and tar metadata.",
    )
    args = parser.parse_args()
    if args.epoch <= 0:
        parser.error("--epoch or SOURCE_DATE_EPOCH must be a positive Unix timestamp")
    for archive in args.archives:
        normalize_sdist(archive, epoch=args.epoch)


if __name__ == "__main__":
    main()
