from __future__ import annotations

from mcp.server import MCPServer
from mcp.server.caching import CacheHint

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.logging_config import configure_logging
from dietary_mcp.package_metadata import PACKAGE_NAME, VERSION
from dietary_mcp.runtime import DietaryRuntime
from dietary_mcp.server_resources import register_resources
from dietary_mcp.server_tools import register_tools


def create_server(
    asset_root: str | None = None,
    runtime: DietaryRuntime | None = None,
    defaults: DefaultsRegistry | None = None,
) -> MCPServer:
    configure_logging()
    asset_root = asset_root or runtime_asset_root()
    runtime = runtime or DietaryRuntime(asset_root)
    defaults = defaults or DefaultsRegistry(asset_root)
    mcp = MCPServer(
        PACKAGE_NAME,
        version=VERSION,
        # Catalogs are fixed at startup. Keep hints private to each client's
        # authorization context; calculation results and resources are uncached.
        cache_hints={
            "tools/list": CacheHint(ttl_ms=60_000),
            "resources/list": CacheHint(ttl_ms=60_000),
            "resources/templates/list": CacheHint(ttl_ms=60_000),
        },
    )
    register_tools(mcp, runtime)
    register_resources(mcp, asset_root, defaults, runtime)
    return mcp
