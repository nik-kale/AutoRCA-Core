"""
Tests for reasoning module.
"""
import pytest
from adapt_rca.reasoning.heuristics import simple_grouping
from adapt_rca.reasoning.agent import analyze_incident


def test_simple_grouping_empty():
    """Test grouping with empty event list."""
    result = simple_grouping([])
    assert result == []


def test_simple_grouping_single_group():
    """Test that all events are grouped together."""
    events = [
        {"service": "api", "message": "Error 1"},
        {"service": "db", "message": "Error 2"},
        {"service": "api", "message": "Error 3"}
    ]

    groups = simple_grouping(events)

    assert len(groups) == 1
    assert len(groups[0]) == 3
    assert groups[0] == events


def test_analyze_incident_basic():
    """Test basic incident analysis."""
    events = [
        {"service": "api-gateway", "message": "Timeout"},
        {"service": "user-service", "message": "DB error"}
    ]

    result = analyze_incident(events)

    assert "incident_summary" in result
    assert "probable_root_causes" in result
    assert "recommended_actions" in result
    assert "api-gateway" in result["incident_summary"]
    assert "user-service" in result["incident_summary"]


def test_analyze_incident_empty():
    """Test analysis with empty event list."""
    result = analyze_incident([])

    assert "incident_summary" in result
    assert "probable_root_causes" in result
    assert "recommended_actions" in result


def test_analyze_incident_single_service():
    """Test analysis with events from a single service."""
    events = [
        {"service": "database", "message": "Connection lost"},
        {"service": "database", "message": "Max connections"}
    ]

    result = analyze_incident(events)

    assert "database" in result["incident_summary"]
