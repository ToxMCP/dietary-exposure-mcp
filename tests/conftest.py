"""Shared test fixtures and configuration for Dietary_MCP."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from dietary_mcp.defaults import DefaultsRegistry
    from dietary_mcp.runtime import DietaryRuntime


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def defaults_registry(repo_root: Path) -> "DefaultsRegistry":
    """Session-scoped DefaultsRegistry to avoid repeated file I/O."""
    from dietary_mcp.defaults import DefaultsRegistry

    return DefaultsRegistry(repo_root)


@pytest.fixture(scope="session")
def dietary_runtime(repo_root: Path) -> "DietaryRuntime":
    """Session-scoped DietaryRuntime to avoid repeated plugin registration."""
    from dietary_mcp.runtime import get_cached_dietary_runtime

    return get_cached_dietary_runtime(repo_root)
