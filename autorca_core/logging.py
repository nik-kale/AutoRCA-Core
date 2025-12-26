"""
Logging configuration for AutoRCA-Core.

Provides structured logging with configurable log levels and formats.
"""

import logging
import sys
from typing import Optional


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

    if structured:
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(module)s", "function": "%(funcName)s", '
            '"message": "%(message)s"}'
        )
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
        name: Optional logger name (defaults to "autorca_core")

    Returns:
        Logger instance
    """
    logger_name = f"autorca_core.{name}" if name else "autorca_core"
    logger = logging.getLogger(logger_name)

    # If logger has no handlers, configure it with default settings
    if not logger.handlers:
        configure_logging()

    return logger

