from __future__ import annotations

import argparse
import os

from dietary_mcp.server import create_server


REMOTE_TRANSPORTS = {"streamable-http", "sse"}
ALLOW_UNAUTHENTICATED_HTTP_ENV = "DIETARY_MCP_ALLOW_UNAUTHENTICATED_HTTP"


def validate_transport_security(transport: str) -> None:
    if transport not in REMOTE_TRANSPORTS:
        return
    if os.getenv(ALLOW_UNAUTHENTICATED_HTTP_ENV, "").strip().lower() in {"1", "true", "yes"}:
        return
    raise SystemExit(
        "Refusing to start unauthenticated HTTP/SSE transport. Keep stdio for local use or set "
        f"{ALLOW_UNAUTHENTICATED_HTTP_ENV}=true only behind an authenticated local gateway."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Dietary Exposure MCP.")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http", "sse"],
        help="MCP transport to use.",
    )
    args = parser.parse_args()
    validate_transport_security(args.transport)
    if args.transport == "streamable-http":
        from dietary_mcp.transport.http import main as http_main

        http_main()
        return
    server = create_server()
    if args.transport == "sse":
        from dietary_mcp.transport.http import (
            build_transport_security_settings,
            max_request_bytes,
        )

        server.run(
            transport="sse",
            host=os.environ.get("DIETARY_MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("DIETARY_MCP_PORT", "8000")),
            max_request_body_size=max_request_bytes(),
            transport_security=build_transport_security_settings(),
        )
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
