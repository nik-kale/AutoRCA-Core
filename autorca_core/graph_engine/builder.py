"""
Graph builder: Construct service topology and dependency graphs from observability data.

Builds a ServiceGraph from logs, metrics, traces, and config changes.
"""

from typing import List, Dict, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from autorca_core.model.events import LogEvent, MetricPoint, Span, ConfigChange
from autorca_core.model.graph import (
    ServiceGraph,
    Service,
    Dependency,
    DependencyType,
    IncidentNode,
    IncidentType,
)


class GraphBuilder:
    """
    Builds a ServiceGraph from observability data.

    The graph includes:
    - Service nodes (discovered from logs/traces)
    - Dependency edges (inferred from trace spans)
    - Incident nodes (detected anomalies/errors)
    """

    def __init__(self):
        self.graph = ServiceGraph()
        self._service_metadata: Dict[str, Dict] = defaultdict(dict)

    def add_logs(self, logs: List[LogEvent]) -> None:
        """
        Add log events to the graph.

        - Discovers services from log events
        - Detects error spikes and creates incident nodes
        """
        # Discover services
        for log in logs:
            if log.service not in self.graph.services:
                self.graph.add_service(Service(name=log.service, service_type="unknown"))

        # Detect error spikes
        error_logs = [log for log in logs if log.is_error()]
        if error_logs:
            self._detect_error_spikes(error_logs)

    def add_metrics(self, metrics: List[MetricPoint]) -> None:
        """
        Add metric data points to the graph.

        - Discovers services from metrics
        - Detects latency spikes, throughput drops, resource exhaustion
        """
        # Discover services
        for metric in metrics:
            if metric.service not in self.graph.services:
                self.graph.add_service(Service(name=metric.service, service_type="unknown"))

        # Detect anomalies by service
        by_service: Dict[str, List[MetricPoint]] = defaultdict(list)
        for metric in metrics:
            by_service[metric.service].append(metric)

        for service, service_metrics in by_service.items():
            self._detect_metric_anomalies(service, service_metrics)

    def add_traces(self, spans: List[Span]) -> None:
        """
        Add trace spans to the graph.

        - Discovers services from spans
        - Infers dependencies between services (parent -> child span relationships)
        - Detects error spans
        """
        # Discover services
        for span in spans:
            if span.service not in self.graph.services:
                self.graph.add_service(Service(name=span.service, service_type="api"))

        # Build dependency map from parent-child span relationships
        dependencies_found: Set[Tuple[str, str]] = set()

        # Group spans by trace_id
        traces: Dict[str, List[Span]] = defaultdict(list)
        for span in spans:
            traces[span.trace_id].append(span)

        # For each trace, infer dependencies
        for trace_id, trace_spans in traces.items():
            span_map = {s.span_id: s for s in trace_spans}

            for span in trace_spans:
                if span.parent_span_id and span.parent_span_id in span_map:
                    parent_span = span_map[span.parent_span_id]
                    if parent_span.service != span.service:
                        # Parent service depends on child service
                        dep_key = (parent_span.service, span.service)
                        if dep_key not in dependencies_found:
                            self.graph.add_dependency(Dependency(
                                from_service=parent_span.service,
                                to_service=span.service,
                                dependency_type=DependencyType.HTTP,
                            ))
                            dependencies_found.add(dep_key)

        # Detect error spans
        error_spans = [s for s in spans if s.is_error()]
        if error_spans:
            self._detect_error_spans(error_spans)

    def add_config_changes(self, changes: List[ConfigChange]) -> None:
        """
        Add config/deployment changes to the graph.

        - Creates incident nodes for recent deployments/config changes
        - These can be correlated with other incidents
        """
        for change in changes:
            if change.service not in self.graph.services:
                self.graph.add_service(Service(name=change.service, service_type="unknown"))

            # Create an incident node for the change
            incident_type = IncidentType.DEPLOYMENT if change.change_type == "deployment" else IncidentType.CONFIG_CHANGE
            description = change.description or f"{change.change_type}: {change.version_after or 'unknown'}"

            self.graph.add_incident(IncidentNode(
                service=change.service,
                incident_type=incident_type,
                timestamp=change.timestamp,
                severity=0.6,  # Changes are moderately important
                description=description,
                evidence=[f"{change.change_type} at {change.timestamp.isoformat()}"],
            ))

    def build(self) -> ServiceGraph:
        """Return the constructed ServiceGraph."""
        return self.graph

    def _detect_error_spikes(self, error_logs: List[LogEvent]) -> None:
        """
        Detect error spikes by service and create incident nodes.

        Simple heuristic: if a service has multiple errors in a short time window,
        create an error_spike incident.
        """
        # Group errors by service
        by_service: Dict[str, List[LogEvent]] = defaultdict(list)
        for log in error_logs:
            by_service[log.service].append(log)

        # Detect spikes (simple threshold: 3+ errors)
        for service, service_errors in by_service.items():
            if len(service_errors) >= 3:
                # Sort by timestamp
                service_errors.sort(key=lambda e: e.timestamp)
                first_error = service_errors[0]
                last_error = service_errors[-1]

                # If errors span less than 5 minutes, it's a spike
                time_span = (last_error.timestamp - first_error.timestamp).total_seconds()
                if time_span <= 300:  # 5 minutes
                    evidence = [f"Error: {e.message}" for e in service_errors[:5]]  # Show first 5
                    self.graph.add_incident(IncidentNode(
                        service=service,
                        incident_type=IncidentType.ERROR_SPIKE,
                        timestamp=first_error.timestamp,
                        severity=0.8,
                        description=f"{len(service_errors)} errors in {time_span:.0f}s",
                        evidence=evidence,
                    ))

    def _detect_metric_anomalies(self, service: str, metrics: List[MetricPoint]) -> None:
        """
        Detect metric anomalies (latency spikes, throughput drops, resource exhaustion).

        Simple heuristic: look for sudden changes or threshold breaches.
        """
        # Group by metric name
        by_metric: Dict[str, List[MetricPoint]] = defaultdict(list)
        for metric in metrics:
            by_metric[metric.metric_name].append(metric)

        for metric_name, metric_points in by_metric.items():
            if len(metric_points) < 2:
                continue

            # Sort by timestamp
            metric_points.sort(key=lambda m: m.timestamp)

            # Simple threshold-based detection
            if 'latency' in metric_name.lower() or 'duration' in metric_name.lower():
                # Detect latency spike (value > 1000ms)
                high_latency = [m for m in metric_points if m.value > 1000]
                if len(high_latency) >= 2:
                    self.graph.add_incident(IncidentNode(
                        service=service,
                        incident_type=IncidentType.LATENCY_SPIKE,
                        timestamp=high_latency[0].timestamp,
                        severity=0.7,
                        description=f"High latency detected: {metric_name}",
                        evidence=[f"{m.metric_name}={m.value:.2f}{m.unit or ''}" for m in high_latency[:3]],
                    ))

            elif 'cpu' in metric_name.lower() or 'memory' in metric_name.lower():
                # Detect resource exhaustion (value > 90%)
                high_usage = [m for m in metric_points if m.value > 90]
                if len(high_usage) >= 2:
                    self.graph.add_incident(IncidentNode(
                        service=service,
                        incident_type=IncidentType.RESOURCE_EXHAUSTION,
                        timestamp=high_usage[0].timestamp,
                        severity=0.9,
                        description=f"High resource usage: {metric_name}",
                        evidence=[f"{m.metric_name}={m.value:.2f}%" for m in high_usage[:3]],
                    ))

    def _detect_error_spans(self, error_spans: List[Span]) -> None:
        """Detect error patterns in trace spans."""
        # Group by service
        by_service: Dict[str, List[Span]] = defaultdict(list)
        for span in error_spans:
            by_service[span.service].append(span)

        # Detect error spikes (3+ error spans)
        for service, service_errors in by_service.items():
            if len(service_errors) >= 3:
                service_errors.sort(key=lambda s: s.timestamp)
                evidence = [f"Span error: {s.operation_name} (status={s.status_code})" for s in service_errors[:5]]
                self.graph.add_incident(IncidentNode(
                    service=service,
                    incident_type=IncidentType.ERROR_SPIKE,
                    timestamp=service_errors[0].timestamp,
                    severity=0.8,
                    description=f"{len(service_errors)} failed spans",
                    evidence=evidence,
                ))


def build_service_graph(
    logs: List[LogEvent] = None,
    metrics: List[MetricPoint] = None,
    traces: List[Span] = None,
    configs: List[ConfigChange] = None,
) -> ServiceGraph:
    """
    Convenience function to build a ServiceGraph from observability data.

    Args:
        logs: Log events
        metrics: Metric data points
        traces: Trace spans
        configs: Config/deployment changes

    Returns:
        Constructed ServiceGraph
    """
    builder = GraphBuilder()

    if logs:
        builder.add_logs(logs)
    if metrics:
        builder.add_metrics(metrics)
    if traces:
        builder.add_traces(traces)
    if configs:
        builder.add_config_changes(configs)

    return builder.build()
