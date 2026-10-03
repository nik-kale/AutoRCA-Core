"""
Logging configuration for AutoRCA-Core.

Provides structured logging with configurable log levels and formats.
"""

import json
import logging
import sys
from typing import Optional

ROOT_LOGGER_NAME = "autorca_core"


class _JsonFormatter(logging.Formatter):
    """One JSON object per line, with the message properly escaped."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(
    level: str = "INFO",
    structured: bool = False,
    logger_name: str = "autorca_core",
) -> logging.Logger:
    """
    Configure AutoRCA logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: If True, use JSON-structured log format
        logger_name: Name of the logger to configure

    Returns:
        Configured logger instance

    Example:
        >>> from autorca_core.logging import configure_logging
        >>> logger = configure_logging(level="DEBUG")
        >>> logger.info("Starting RCA analysis")
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove any existing handlers
    logger.handlers.clear()

    formatter: logging.Formatter
    if structured:
        formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Optional logger name, usually __name__ (defaults to "autorca_core").
            Names outside the package are nested under "autorca_core.".

    Returns:
        Logger instance
    """
    if not name or name == ROOT_LOGGER_NAME or name.startswith(ROOT_LOGGER_NAME + "."):
        logger_name = name or ROOT_LOGGER_NAME
    else:
        logger_name = f"{ROOT_LOGGER_NAME}.{name}"

    # Child loggers propagate to the package logger, which owns the handler.
    # Only install the default configuration if nothing has configured it yet;
    # checking the child (which never has handlers) reset any level the caller
    # had set on every call.
    if not logging.getLogger(ROOT_LOGGER_NAME).handlers:
        configure_logging()

    return logging.getLogger(logger_name)
