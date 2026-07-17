"""Streamable-HTTP transport entrypoint for dietary-mcp.

Run with the ``dietary-mcp-http`` console script (hosted mode).
Host and port are controlled by env vars:

    DIETARY_MCP_HOST   (default: 127.0.0.1)
    DIETARY_MCP_PORT   (default: 8000)
    DIETARY_MCP_MAX_REQUEST_BYTES (default: 1048576)

DNS-rebinding protection is always enabled. Configure the exact public gateway
names when hosted; the defaults accept local development only:

    DIETARY_MCP_ALLOWED_HOSTS
    DIETARY_MCP_ALLOWED_ORIGINS

Security: the existing fail-closed auth guard is honoured here.
The HTTP transport is refused unless the caller explicitly opts in via env var:

    DIETARY_MCP_ALLOW_UNAUTHENTICATED_HTTP=true

This delegates directly to dietary_mcp.__main__.validate_transport_security.
Deploy this entrypoint only behind an authenticated gateway (reverse proxy,
API gateway, etc.) and set the env var in that context.

The same FastMCP server object is used here as for the stdio entrypoint —
the MCP tool surface is identical on both transports.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.transport_security import TransportSecuritySettings


_DEFAULT_ALLOWED_HOSTS = "localhost:*,127.0.0.1:*,[::1]:*"
_DEFAULT_ALLOWED_ORIGINS = "http://localhost:*,http://127.0.0.1:*,http://[::1]:*"
_DEFAULT_MAX_REQUEST_BYTES = 1_048_576

ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]
ASGIApp = Callable[[dict[str, Any], ASGIReceive, ASGISend], Awaitable[None]]


def _csv_env(name: str, default: str) -> list[str]:
    values = [value.strip() for value in os.environ.get(name, default).split(",") if value.strip()]
    if not values:
        raise SystemExit(f"{name} must contain at least one explicit allowlisted value.")
    return values


def build_transport_security_settings() -> TransportSecuritySettings:
    """Build fail-closed Host and Origin allowlists for streamable HTTP."""
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_csv_env("DIETARY_MCP_ALLOWED_HOSTS", _DEFAULT_ALLOWED_HOSTS),
        allowed_origins=_csv_env("DIETARY_MCP_ALLOWED_ORIGINS", _DEFAULT_ALLOWED_ORIGINS),
    )


def max_request_bytes() -> int:
    """Return the configured positive request-body limit."""
    raw_value = os.environ.get("DIETARY_MCP_MAX_REQUEST_BYTES", str(_DEFAULT_MAX_REQUEST_BYTES))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise SystemExit("DIETARY_MCP_MAX_REQUEST_BYTES must be a positive integer.") from exc
    if value <= 0:
        raise SystemExit("DIETARY_MCP_MAX_REQUEST_BYTES must be a positive integer.")
    return value


class RequestBodyLimitMiddleware:
    """Buffer and reject oversized HTTP requests before MCP dispatch."""

    def __init__(self, app: ASGIApp, limit: int) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: dict[str, Any], receive: ASGIReceive, send: ASGISend) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                parsed_content_length = int(content_length)
                if parsed_content_length < 0:
                    await self._reject(send, status=400, detail="Invalid Content-Length header.")
                    return
                if parsed_content_length > self.limit:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send, status=400, detail="Invalid Content-Length header.")
                return

        messages: list[dict[str, Any]] = []
        total = 0
        while True:
            message = await receive()
            messages.append(message)
            if message.get("type") == "http.disconnect":
                return
            if message.get("type") != "http.request":
                continue
            total += len(message.get("body", b""))
            if total > self.limit:
                await self._reject(send)
                return
            if not message.get("more_body", False):
                break

        async def replay_receive() -> dict[str, Any]:
            if messages:
                return messages.pop(0)
            return {"type": "http.disconnect"}

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(send: ASGISend, *, status: int = 413, detail: str = "Request body too large.") -> None:
        body = ('{"error":"' + detail + '"}').encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def main() -> None:
    """HTTP entrypoint: honour auth guard, wrap the MCP server with streamable-http, run uvicorn."""
    # Honour the fail-closed remote-transport security guard.
    # This is the same check performed by __main__.validate_transport_security.
    from dietary_mcp.__main__ import validate_transport_security

    validate_transport_security("streamable-http")

    try:
        import uvicorn
    except ImportError:
        print(
            "uvicorn is required for the HTTP transport.  "
            "Install it with:  pip install 'uvicorn[standard]'",
            file=sys.stderr,
        )
        sys.exit(1)

    from dietary_mcp.server import create_server

    host = os.environ.get("DIETARY_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("DIETARY_MCP_PORT", "8000"))

    mcp = create_server(
        stateless_http=True,
        transport_security=build_transport_security_settings(),
    )
    # streamable_http_app() returns a Starlette ASGI app that speaks the
    # MCP streamable-HTTP protocol (same tool surface as the stdio server).
    app = RequestBodyLimitMiddleware(mcp.streamable_http_app(), max_request_bytes())

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
