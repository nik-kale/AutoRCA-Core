"""
Tests for logging configuration helpers.
"""

import io
import json
import logging

import pytest

from autorca_core.logging import configure_logging, get_logger


@pytest.fixture(autouse=True)
def restore_logging():
    base = logging.getLogger("autorca_core")
    handlers, level, propagate = list(base.handlers), base.level, base.propagate
    yield
    base.handlers[:] = handlers
    base.setLevel(level)
    base.propagate = propagate


def test_get_logger_keeps_configured_level():
    """get_logger() checked the child logger for handlers (it never has any) and so
    re-ran configure_logging(), resetting the package logger to INFO each call."""
    configure_logging(level="DEBUG")

    get_logger("autorca_core.some.module")

    assert logging.getLogger("autorca_core").level == logging.DEBUG


def test_get_logger_does_not_double_prefix_module_names():
    assert get_logger("autorca_core.ingestion.logs").name == "autorca_core.ingestion.logs"
    assert get_logger("plugin").name == "autorca_core.plugin"
    assert get_logger().name == "autorca_core"


def test_structured_logging_emits_valid_json():
    configure_logging(level="INFO", structured=True)
    stream = io.StringIO()
    logging.getLogger("autorca_core").handlers[0].setStream(stream)

    get_logger("autorca_core.test").warning('bad "quoted" value\nsecond line')

    record = json.loads(stream.getvalue())
    assert record["message"] == 'bad "quoted" value\nsecond line'
    assert record["level"] == "WARNING"
