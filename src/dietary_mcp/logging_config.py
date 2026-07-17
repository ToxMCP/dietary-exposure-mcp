from __future__ import annotations

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the dietary_mcp package logger with a standard format."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
