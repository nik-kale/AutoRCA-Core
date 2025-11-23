"""
Basic test to verify quickstart example works.
"""

import pytest
from pathlib import Path
from datetime import datetime

from autorca_core.reasoning.loop import run_rca_from_files


def test_quickstart_example():
    """Test that the quickstart example runs successfully."""
    # Find the examples directory
    examples_dir = Path(__file__).parent.parent / "examples" / "quickstart_local_logs"

    if not examples_dir.exists():
        pytest.skip("Examples directory not found")

    logs_file = examples_dir / "logs.jsonl"
    metrics_file = examples_dir / "metrics.jsonl"

    if not logs_file.exists():
        pytest.skip("Example logs not found")

    # Run RCA
    result = run_rca_from_files(
        logs_path=str(logs_file),
        metrics_path=str(metrics_file) if metrics_file.exists() else None,
        primary_symptom="Database connection exhaustion causing API errors",
        window_minutes=10,
    )

    # Verify we got results
    assert result is not None
    assert result.primary_symptom == "Database connection exhaustion causing API errors"
    assert len(result.root_cause_candidates) > 0

    # Verify the top candidate is related to postgres or connections
    top_candidate = result.root_cause_candidates[0]
    assert top_candidate.service in ["postgres", "user-service"]
    assert top_candidate.confidence > 0.5

    # Verify we have a summary
    assert len(result.summary) > 0
    assert "postgres" in result.summary.lower() or "connection" in result.summary.lower()

    print(f"\nTop root cause: {top_candidate.service}")
    print(f"Confidence: {top_candidate.confidence:.0%}")
    print(f"Explanation: {top_candidate.explanation}")


def test_rca_basic_functionality():
    """Test basic RCA functionality with minimal data."""
    from autorca_core.model.events import LogEvent, Severity
    from autorca_core.model.graph import ServiceGraph
    from autorca_core.graph_engine.builder import build_service_graph
    from autorca_core.reasoning.rules import apply_rules

    # Create some test log events
    logs = [
        LogEvent(
            timestamp=datetime(2025, 11, 10, 10, 0, 0),
            service="test-service",
            message="Error occurred",
            level=Severity.ERROR,
        ),
        LogEvent(
            timestamp=datetime(2025, 11, 10, 10, 0, 1),
            service="test-service",
            message="Another error",
            level=Severity.ERROR,
        ),
        LogEvent(
            timestamp=datetime(2025, 11, 10, 10, 0, 2),
            service="test-service",
            message="Yet another error",
            level=Severity.ERROR,
        ),
    ]

    # Build graph
    graph = build_service_graph(logs=logs)

    # Verify graph was built
    assert len(graph.services) >= 1
    assert "test-service" in graph.services

    # Apply rules
    candidates = apply_rules(graph)

    # Should have at least one candidate due to error spike
    assert len(candidates) >= 1
