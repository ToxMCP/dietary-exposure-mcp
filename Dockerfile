# Production image for dietary-mcp (streamable-HTTP transport).
# Mirrors the fleet pattern (ngra-ttc-tier0-mcp / bioactivity-pod-mcp).
#
# Transport: streamable-HTTP via uvicorn, port 8000.
# Stdio entrypoint (dietary-mcp) is preserved in the installed package.
# No secrets or API keys are baked in; pass env vars at runtime.
#
# AUTH: this image runs the HTTP entrypoint. The fail-closed security guard
# in dietary_mcp.__main__.validate_transport_security will REFUSE to start
# unless DIETARY_MCP_ALLOW_UNAUTHENTICATED_HTTP=true is set. Deploy only
# behind an authenticated reverse proxy or API gateway, and set that env
# var in your container runtime configuration.

ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ${PYTHON_IMAGE}

ARG APP_HOME=/app

# Reproducible, no .pyc noise.
# UV_PYTHON_PREFERENCE=only-system: force uv to use the base image's world-readable
# system interpreter (python:3.12-slim-bookworm ships CPython 3.12) instead of
# downloading a managed CPython under /root (mode 0700) that the non-root appuser
# cannot read.  This is the critical fix for non-root container startup.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_PYTHON_PREFERENCE=only-system

WORKDIR ${APP_HOME}

# Install uv from PyPI so no external registry pull is required at build time.
RUN pip install --no-cache-dir "uv==0.7.12"

# Copy only the dependency manifests first so Docker cache layers survive
# source-only changes.
COPY pyproject.toml uv.lock README.md ./

# Install all runtime dependencies from the locked file.
# --no-install-project: only deps, not the package itself yet.
# --no-dev: production image does not need pytest/ruff.
RUN uv sync --locked --no-install-project --no-dev

# Copy source tree and install the project itself (no extra deps).
COPY src/ src/

RUN uv sync --locked --no-dev

# Create a non-root user and hand ownership over.
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser ${APP_HOME}

USER appuser

# Streamable-HTTP transport port.
EXPOSE 8000

# Confirm the MCP endpoint is live. A bare GET /mcp returns 406 when the
# MCP Accept header is missing; that still proves the server is up. Fail only
# when the endpoint is unreachable or returns a server-side error (5xx).
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "\
import http.client, sys; \
c = http.client.HTTPConnection('localhost', 8000, timeout=8); \
c.request('GET', '/mcp', headers={'Accept': 'application/json, text/event-stream'}); \
r = c.getresponse(); \
sys.exit(0 if r.status < 500 else 1)" || exit 1

# Run the venv binary directly (frozen at build time, no re-resolve / no managed
# Python download at container start).  Host and port are tunable via env vars
# DIETARY_MCP_HOST / DIETARY_MCP_PORT.
# Requires DIETARY_MCP_ALLOW_UNAUTHENTICATED_HTTP=true (set in your orchestrator).
CMD ["/app/.venv/bin/dietary-mcp-http"]
