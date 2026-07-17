from dietary_mcp.package_metadata import VERSION

__all__ = ["VERSION", "create_server"]


def create_server():
    from dietary_mcp.server import create_server as _create_server

    return _create_server()
