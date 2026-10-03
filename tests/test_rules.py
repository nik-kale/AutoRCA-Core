"""
Tests for anomaly detection in the graph builder and the RCA rules.
"""

from datetime import datetime, timedelta, timezone

from autorca_core.config import ThresholdConfig
from autorca_core.graph_engine.builder import build_service_graph
from autorca_core.model.events import ConfigChange, LogEvent, MetricPoint, Severity, Span
from autorca_core.model.graph import IncidentType
from autorca_core.reasoning.rules import apply_rules

T0 = datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc)


def _errors(service, *offsets_s):
    return [
        LogEvent(
            timestamp=T0 + timedelta(seconds=s),
            service=service,
            message=f"error at +{s}s",
            level=Severity.ERROR,
        )
        for s in offsets_s
    ]


def _spikes(graph):
    return [i for i in graph.incidents if i.incident_type == IncidentType.ERROR_SPIKE]


def test_error_spike_found_despite_earlier_stray_error():
    """The spike check measured first-to-last error over all data, so one error an
    hour earlier hid a burst of errors inside the window."""
    logs = _errors("db", -3600, 0, 1, 2)

    spikes = _spikes(build_service_graph(logs=logs))

    assert len(spikes) == 1
    assert spikes[0].timestamp == T0
    assert spikes[0].description == "3 errors in 2s"


def test_spread_out_errors_are_not_a_spike():
    logs = _errors("db", 0, 400, 800)

    assert _spikes(build_service_graph(logs=logs)) == []


def test_error_span_detection_uses_configured_threshold():
    """Span-based detection ignored ThresholdConfig and always required 3 spans."""
    spans = [
        Span(timestamp=T0 + timedelta(seconds=i), service="api", span_id=str(i),
             trace_id="t", status_code=503)
        for i in range(2)
    ]

    default = build_service_graph(traces=spans)
    sensitive = build_service_graph(traces=spans, thresholds=ThresholdConfig.strict())

    assert _spikes(default) == []
    assert len(_spikes(sensitive)) == 1


def _deploy(service, offset_s):
    return ConfigChange(
        timestamp=T0 + timedelta(seconds=offset_s),
        service=service,
        change_type="deployment",
        description=f"deploy {service} v2",
    )


def test_change_is_not_blamed_for_errors_that_preceded_it():
    """Correlation used abs(), so errors before a deployment were attributed to it."""
    graph = build_service_graph(logs=_errors("api", 0, 1, 2), configs=[_deploy("api", 120)])

    candidates = apply_rules(graph)

    assert IncidentType.DEPLOYMENT not in {c.incident_type for c in candidates}


def test_change_followed_by_errors_is_top_candidate():
    graph = build_service_graph(logs=_errors("api", 60, 61, 62), configs=[_deploy("api", 0)])

    top = apply_rules(graph)[0]

    assert (top.service, top.incident_type) == ("api", IncidentType.DEPLOYMENT)


def test_rules_do_not_repeat_the_same_candidate():
    """Several rules flag the same database; each (service, type) appears once and
    keeps the extra context from the merged duplicates."""
    # frontend -> api -> {users, orders} -> db
    parents = {"0": None, "1": "0", "2": "1", "3": "2", "4": "1", "5": "4"}
    services = {"0": "frontend", "1": "api", "2": "users", "3": "db", "4": "orders", "5": "db"}
    spans = [
        Span(timestamp=T0, service=services[sid], span_id=sid, trace_id="t", parent_span_id=p)
        for sid, p in parents.items()
    ]
    logs = (
        _errors("db", 0, 1, 2)
        + _errors("users", 5, 6, 7)
        + _errors("api", 10, 11, 12)
        + _errors("frontend", 15, 16, 17)
    )
    metrics = [
        MetricPoint(timestamp=T0 + timedelta(seconds=s), service="db",
                    metric_name="cpu_percent", value=97)
        for s in range(3)
    ]

    candidates = apply_rules(build_service_graph(logs=logs, traces=spans, metrics=metrics))

    keys = [(c.service, c.incident_type) for c in candidates]
    assert len(keys) == len(set(keys))
    assert candidates[0].service == "db"
    db_spike = candidates[keys.index(("db", IncidentType.ERROR_SPIKE))]
    assert any(r.startswith("Causal chain: db") for r in db_spike.remediation)


def test_causal_chain_ordering_uses_earliest_incident_per_service():
    """Chain scoring compared whichever incident was stored last for a service, so a
    later config change on the root service cancelled the temporal-order bonus."""
    from autorca_core.graph_engine.queries import GraphQueries
    from autorca_core.model.graph import Dependency, IncidentNode, ServiceGraph

    graph = ServiceGraph()
    graph.add_dependency(Dependency(from_service="api", to_service="db"))
    graph.add_incident(IncidentNode("db", IncidentType.ERROR_SPIKE, T0, severity=0.8))
    graph.add_incident(IncidentNode("api", IncidentType.ERROR_SPIKE, T0 + timedelta(seconds=10),
                                    severity=0.8))
    graph.add_incident(IncidentNode("db", IncidentType.CONFIG_CHANGE, T0 + timedelta(seconds=300),
                                    severity=0.6))

    chain = GraphQueries(graph).find_causal_chains()[0]

    assert chain.services == ["db", "api"]
    # severities (0.8 + 0.6 + 0.8) plus the 0.5 bonus for db failing before api
    assert abs(chain.score - 2.7) < 1e-9
