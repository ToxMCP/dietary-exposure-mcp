from __future__ import annotations

import gzip
import hashlib
import io
import tarfile
from pathlib import Path

from scripts.normalize_sdist import normalize_sdist


def _write_test_sdist(path: Path, *, epoch: int, reverse: bool) -> None:
    members = [
        ("example-1.0/", None),
        ("example-1.0/PKG-INFO", b"Name: example\nVersion: 1.0\n"),
        ("example-1.0/src/example.py", b"VALUE = 1\n"),
    ]
    if reverse:
        members.reverse()
    with path.open("wb") as raw_output:
        with gzip.GzipFile(filename="source.tar.gz", mode="wb", fileobj=raw_output, mtime=epoch) as gzip_output:
            with tarfile.open(fileobj=gzip_output, mode="w") as archive:
                for name, payload in members:
                    member = tarfile.TarInfo(name)
                    member.mtime = epoch
                    member.uid = epoch % 1000
                    member.gid = epoch % 100
                    if payload is None:
                        member.type = tarfile.DIRTYPE
                        archive.addfile(member)
                    else:
                        member.size = len(payload)
                        archive.addfile(member, io.BytesIO(payload))


def test_normalize_sdist_removes_archive_metadata_variance(tmp_path: Path) -> None:
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    _write_test_sdist(first, epoch=1_700_000_000, reverse=False)
    _write_test_sdist(second, epoch=1_800_000_000, reverse=True)

    release_epoch = 1_600_000_000
    normalize_sdist(first, epoch=release_epoch)
    normalize_sdist(second, epoch=release_epoch)

    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()
    with tarfile.open(first, mode="r:gz") as archive:
        assert [member.name for member in archive.getmembers()] == [
            "example-1.0",
            "example-1.0/PKG-INFO",
            "example-1.0/src/example.py",
        ]
        assert all(member.mtime == release_epoch for member in archive.getmembers())
        assert archive.extractfile("example-1.0/src/example.py").read() == b"VALUE = 1\n"
