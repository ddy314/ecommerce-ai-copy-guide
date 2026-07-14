"""Shared logger configuration using Loguru.

Provides a pre-configured :class:`loguru.Logger` instance that writes
structured logs to both stderr and a rotating file.  Import ``logger``
from this module anywhere in the project.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger as _logger

from ai_service.config.settings import get_settings


# ---------------------------------------------------------------------------
# Remove the default Loguru handler — we'll add our own
# ---------------------------------------------------------------------------
_logger.remove()


# ---------------------------------------------------------------------------
# Build a format string that includes module/function/line for debugging
# ---------------------------------------------------------------------------
_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


# ---------------------------------------------------------------------------
# Configure handlers from settings
# ---------------------------------------------------------------------------
def _configure_logger() -> None:
    """Register stderr and file sinks based on application settings."""
    settings = get_settings()

    # --- stderr sink (always on) ---
    _logger.add(
        sys.stderr,
        format=_LOG_FORMAT,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # --- rotating file sink ---
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    _logger.add(
        str(log_path),
        format=_LOG_FORMAT,
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        encoding="utf-8",
        backtrace=True,
        diagnose=False,         # keep diagnostics out of production log files
    )


_configure_logger()

# ---------------------------------------------------------------------------
# Public alias — import THIS
# ---------------------------------------------------------------------------
logger = _logger
"""Pre-configured Loguru logger instance.

Usage::

    from ai_service.utils.logger import logger
    logger.info("Service started on port {}", port)
    logger.error("LLM call failed: {}", exc_info=True)
"""
