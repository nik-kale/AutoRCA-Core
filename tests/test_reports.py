"""
Tests for report generation.
"""

import json
from datetime import datetime, timezone

import pytest

from autorca_core.model.graph import Dependency, IncidentNode, IncidentType, ServiceGraph
from autorca_core.outputs.reports import generate_html_report, generate_json_report, save_report
from autorca_core.reasoning.loop import RCARunResult
from autorca_core.reasoning.rules import RootCauseCandidate

PAYLOAD = '<img src=x onerror="alert(1)">'


@pytest.fixture
def hostile_result():
    """An RCA result where every free-text field carries markup from the input data."""
    service = f"svc{PAYLOAD}"
    graph = ServiceGraph()
    graph.add_dependency(Dependency(from_service="api", to_service=service))
    incident = IncidentNode(
        service=service,
        incident_type=IncidentType.ERROR_SPIKE,
        timestamp=datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc),
        description=f"3 errors {PAYLOAD}",
        evidence=[f"Error: {PAYLOAD}"],
    )
    graph.add_incident(incident)
    candidate = RootCauseCandidate(
        service=service,
        incident_type=IncidentType.ERROR_SPIKE,
        confidence=0.8,
        explanation=f"explained {PAYLOAD}",
        evidence=[f"Error: {PAYLOAD}"],
        remediation=[f"Fix {PAYLOAD}"],
    )
    return RCARunResult(
        primary_symptom=f"symptom {PAYLOAD}</title><script>alert(2)</script>",
        root_cause_candidates=[candidate],
        service_graph=graph,
        summary=f"summary {PAYLOAD}",
        timeline=[{
            "timestamp": incident.timestamp.isoformat(),
            "service": service,
            "type": "error_spike",
            "description": incident.description,
            "severity": 0.8,
        }],
        metadata={"window_start": PAYLOAD, "window_end": "x", "num_services": 2},
    )


def test_html_report_escapes_data_derived_text(hostile_result):
    html = generate_html_report(hostile_result)

    assert "<img" not in html
    assert "alert(2)</script>" not in html
    # Only the report's own collapsible-section script remains
    assert html.count("<script>") == 1
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html


def test_json_report_round_trips(hostile_result, tmp_path):
    report = json.loads(generate_json_report(hostile_result))
    assert report["primary_symptom"] == hostile_result.primary_symptom

    out = tmp_path / "report.html"
    save_report(hostile_result, str(out), format="html")
    assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")

    with pytest.raises(ValueError):
        save_report(hostile_result, str(tmp_path / "r.pdf"), format="pdf")


def test_service_graph_svg_fits_every_node():
    """The canvas was fixed at 800x600 while the layout radius grows with the number
    of services, so graphs with more than about seven services were clipped."""
    import re

    from autorca_core.outputs.reports import _generate_service_graph_svg

    graph = ServiceGraph()
    for i in range(12):
        graph.add_dependency(Dependency(from_service="gateway", to_service=f"svc-{i}"))

    svg = _generate_service_graph_svg(graph, [])

    width, height = map(float, re.search(r'viewBox="0 0 (\S+) (\S+)"', svg).groups())
    for cx, cy, r in re.findall(r'<circle cx="([\d.\-]+)" cy="([\d.\-]+)" r="(\d+)"', svg):
        cx, cy, r = float(cx), float(cy), float(r)
        assert r <= cx <= width - r and r <= cy <= height - r
