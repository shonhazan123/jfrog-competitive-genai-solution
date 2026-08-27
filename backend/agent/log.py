from __future__ import annotations

import logging
from typing import Any


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def step(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit one structured line for an agent or pipeline step."""
    if not fields:
        logger.info(event)
        return
    detail = " ".join(f"{key}={_format_field(value)}" for key, value in fields.items())
    logger.info("%s %s", event, detail)


def _format_field(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str) and len(value) > 120:
        return repr(value[:117] + "...")
    return repr(value)
