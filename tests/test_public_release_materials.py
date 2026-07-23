import hashlib
from pathlib import Path

from scripts.public_release_audit import audit_current_tree


ROOT = Path(__file__).resolve().parents[1]


def test_public_release_tree_has_no_current_metadata_leaks() -> None:
    assert audit_current_tree() == []


def test_owner_attestation_preserves_independent_review_boundary() -> None:
    source = (
        ROOT
        / "docs"
        / "reviews"
        / "submissions"
        / "openfoodtox-3-owner-attestation-source-2026-07-22.txt"
    )
    attestation = (
        ROOT / "docs" / "reviews" / "openfoodtox-3-owner-attestation-2026-07-22.md"
    ).read_text(encoding="utf-8")
    normalized_attestation = " ".join(attestation.split())

    assert "owner/maintainer capacity" in normalized_attestation
    assert "does not close the independent scientific promotion gate" in normalized_attestation
    assert "all 2,417 bulk records constrained to `review_required`" in normalized_attestation
    assert "0feb8e3e4f9852c2d102375dd89d814ed08407a602d699882cf48bdd7f3c8c90" in attestation

    source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_sha256 == "f4c8f52b922df70c75546a6fff9a2f34cf898e5579be1bee51975834da71fa58"
    assert source_sha256 in attestation


def test_readme_places_release_status_next_to_explicit_limitations() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    architecture_index = readme.index("## Architecture")
    release_status_index = readme.index("## Release status and intended use")
    notice_index = readme.index("**Release status:**")
    limitations_index = readme.index("## Current limitations")

    assert "**Release status:**" not in readme[:architecture_index]
    assert architecture_index < release_status_index < notice_index < limitations_index
    assert "all 2,417 bulk records remain `review_required`" in readme
    assert "accepts the 16-record high-impact report" in readme
    assert "It is not independent signoff" in readme
