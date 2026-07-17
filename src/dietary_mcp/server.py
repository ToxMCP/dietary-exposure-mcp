from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

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
    *,
    stateless_http: bool = False,
    transport_security: TransportSecuritySettings | None = None,
) -> FastMCP:
    configure_logging()
    asset_root = asset_root or runtime_asset_root()
    runtime = runtime or DietaryRuntime(asset_root)
    defaults = defaults or DefaultsRegistry(asset_root)
    mcp = FastMCP(
        PACKAGE_NAME,
        json_response=True,
        stateless_http=stateless_http,
        transport_security=transport_security,
    )
    # FastMCP v1 has no public version argument and otherwise advertises the
    # SDK version. MCPServer v2 exposes this directly on its constructor.
    mcp._mcp_server.version = VERSION
    register_tools(mcp, runtime)
    register_resources(mcp, asset_root, defaults, runtime)
    return mcp
