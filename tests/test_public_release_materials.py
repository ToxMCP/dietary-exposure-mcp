from scripts.public_release_audit import audit_current_tree


def test_public_release_tree_has_no_current_metadata_leaks() -> None:
    assert audit_current_tree() == []
