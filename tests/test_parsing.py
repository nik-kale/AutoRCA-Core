"""
Tests for parsing module.
"""
import pytest
from adapt_rca.parsing.log_parser import normalize_event


def test_normalize_event_basic():
    """Test basic event normalization."""
    raw = {
        "timestamp": "2025-11-16T10:00:00Z",
        "service": "api-gateway",
        "level": "ERROR",
        "message": "Test error"
    }

    normalized = normalize_event(raw)

    assert normalized["timestamp"] == "2025-11-16T10:00:00Z"
    assert normalized["service"] == "api-gateway"
    assert normalized["level"] == "ERROR"
    assert normalized["message"] == "Test error"
    assert normalized["raw"] == raw


def test_normalize_event_component_fallback():
    """Test that 'component' field falls back to 'service'."""
    raw = {
        "timestamp": "2025-11-16T10:00:00Z",
        "component": "user-service",
        "level": "WARN",
        "message": "Warning message"
    }

    normalized = normalize_event(raw)

    assert normalized["service"] == "user-service"


def test_normalize_event_severity_fallback():
    """Test that 'severity' field falls back to 'level'."""
    raw = {
        "timestamp": "2025-11-16T10:00:00Z",
        "service": "db",
        "severity": "CRITICAL",
        "message": "Critical issue"
    }

    normalized = normalize_event(raw)

    assert normalized["level"] == "CRITICAL"


def test_normalize_event_missing_fields():
    """Test normalization with missing fields."""
    raw = {
        "message": "Incomplete log"
    }

    normalized = normalize_event(raw)

    assert normalized["timestamp"] is None
    assert normalized["service"] is None
    assert normalized["level"] is None
    assert normalized["message"] == "Incomplete log"
