"""
RCA reasoning loop: Orchestrates the end-to-end RCA process.

The main entry point for running root cause analysis.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from autorca_core.ingestion import load_logs, load_metrics, load_traces, load_configs
from autorca_core.model.events import LogEvent, MetricPoint, Span, ConfigChange
from autorca_core.model.graph import ServiceGraph
from autorca_core.graph_engine.builder import build_service_graph
from autorca_core.graph_engine.queries import GraphQueries
from autorca_core.reasoning.rules import apply_rules, RootCauseCandidate
from autorca_core.reasoning.llm import LLMInterface, DummyLLM


@dataclass
class DataSourcesConfig:
    """
    Configuration for data sources.

    Attributes:
        logs_dir: Path to logs directory or file
        metrics_dir: Path to metrics directory or file
        traces_dir: Path to traces directory or file
        configs_dir: Path to configs directory or file
    """
    logs_dir: Optional[str] = None
    metrics_dir: Optional[str] = None
    traces_dir: Optional[str] = None
    configs_dir: Optional[str] = None


@dataclass
class RCARunResult:
    """
    Result of an RCA run.

    Attributes:
        primary_symptom: The symptom being investigated
        root_cause_candidates: Ranked list of root cause candidates
        service_graph: Constructed service topology graph
        summary: Human-readable RCA summary
        timeline: Chronological list of incidents
        metadata: Additional metadata about the run
    """
    primary_symptom: str
    root_cause_candidates: List[RootCauseCandidate]
    service_graph: ServiceGraph
    summary: str
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "primary_symptom": self.primary_symptom,
            "root_cause_candidates": [c.to_dict() for c in self.root_cause_candidates],
            "service_graph": self.service_graph.to_dict(),
            "summary": self.summary,
            "timeline": self.timeline,
            "metadata": self.metadata,
        }


def run_rca(
    incident_window: tuple[datetime, datetime],
    primary_symptom: str,
    data_sources: DataSourcesConfig,
    llm: Optional[LLMInterface] = None,
) -> RCARunResult:
    """
    Run root cause analysis.

    This is the main entry point for RCA. It:
    1. Loads observability data (logs, metrics, traces, configs)
    2. Builds a service topology graph
    3. Detects incidents and anomalies
    4. Applies rule-based heuristics to identify root causes
    5. Optionally uses an LLM to enhance the analysis
    6. Returns a ranked list of root cause candidates with evidence

    Args:
        incident_window: Tuple of (start_time, end_time) for the analysis window
        primary_symptom: Description of the symptom (e.g., "Checkout API 500 errors")
        data_sources: Configuration for data sources
        llm: Optional LLM interface for enhanced analysis

    Returns:
        RCARunResult with root cause candidates and analysis

    Example:
        >>> from datetime import datetime
        >>> from autorca_core import run_rca, DataSourcesConfig
        >>>
        >>> window = (
        ...     datetime(2025, 11, 10, 10, 0, 0),
        ...     datetime(2025, 11, 10, 10, 5, 0),
        ... )
        >>> sources = DataSourcesConfig(logs_dir="./logs", metrics_dir="./metrics")
        >>> result = run_rca(window, "API 500 errors", sources)
        >>> print(result.summary)
    """
    time_from, time_to = incident_window

    # Use DummyLLM if no LLM provided
    if llm is None:
        llm = DummyLLM()

    # Step 1: Load observability data
    print(f"Loading data for window: {time_from} to {time_to}")

    logs: List[LogEvent] = []
    metrics: List[MetricPoint] = []
    traces: List[Span] = []
    configs: List[ConfigChange] = []

    if data_sources.logs_dir:
        logs = load_logs(data_sources.logs_dir, time_from, time_to)
        print(f"  Loaded {len(logs)} log events")

    if data_sources.metrics_dir:
        metrics = load_metrics(data_sources.metrics_dir, time_from, time_to)
        print(f"  Loaded {len(metrics)} metric points")

    if data_sources.traces_dir:
        traces = load_traces(data_sources.traces_dir, time_from, time_to)
        print(f"  Loaded {len(traces)} trace spans")

    if data_sources.configs_dir:
        configs = load_configs(data_sources.configs_dir, time_from, time_to)
        print(f"  Loaded {len(configs)} config changes")

    # Step 2: Build service graph
    print("Building service graph...")
    graph = build_service_graph(logs=logs, metrics=metrics, traces=traces, configs=configs)
    print(f"  Graph: {len(graph.services)} services, {len(graph.dependencies)} dependencies, {len(graph.incidents)} incidents")

    # Step 3: Run rule-based analysis
    print("Applying RCA rules...")
    candidates = apply_rules(graph)
    print(f"  Identified {len(candidates)} root cause candidates")

    # Step 4: Generate summary using LLM
    print("Generating RCA summary...")
    summary = llm.summarize_rca(graph, candidates, primary_symptom)

    # Step 5: Build incident timeline
    queries = GraphQueries(graph)
    timeline_incidents = queries.get_incident_timeline()
    timeline = [
        {
            "timestamp": i.timestamp.isoformat(),
            "service": i.service,
            "type": i.incident_type.value,
            "description": i.description,
            "severity": i.severity,
        }
        for i in timeline_incidents
    ]

    # Step 6: Compile metadata
    metadata = {
        "window_start": time_from.isoformat(),
        "window_end": time_to.isoformat(),
        "num_logs": len(logs),
        "num_metrics": len(metrics),
        "num_traces": len(traces),
        "num_configs": len(configs),
        "num_services": len(graph.services),
        "num_dependencies": len(graph.dependencies),
        "num_incidents": len(graph.incidents),
        "num_candidates": len(candidates),
    }

    return RCARunResult(
        primary_symptom=primary_symptom,
        root_cause_candidates=candidates,
        service_graph=graph,
        summary=summary,
        timeline=timeline,
        metadata=metadata,
    )


def run_rca_from_files(
    logs_path: str,
    metrics_path: Optional[str] = None,
    traces_path: Optional[str] = None,
    configs_path: Optional[str] = None,
    primary_symptom: str = "Unknown incident",
    window_minutes: int = 60,
) -> RCARunResult:
    """
    Convenience function to run RCA from file paths.

    Automatically determines the time window from the data.

    Args:
        logs_path: Path to logs file/directory
        metrics_path: Path to metrics file/directory
        traces_path: Path to traces file/directory
        configs_path: Path to configs file/directory
        primary_symptom: Description of the symptom
        window_minutes: Size of the analysis window in minutes

    Returns:
        RCARunResult
    """
    # Load all data without time filtering to determine the time range
    all_logs = load_logs(logs_path) if logs_path else []
    all_metrics = load_metrics(metrics_path) if metrics_path else []
    all_traces = load_traces(traces_path) if traces_path else []
    all_configs = load_configs(configs_path) if configs_path else []

    # Determine time window from data
    timestamps = []
    timestamps.extend([log.timestamp for log in all_logs])
    timestamps.extend([metric.timestamp for metric in all_metrics])
    timestamps.extend([span.timestamp for span in all_traces])
    timestamps.extend([config.timestamp for config in all_configs])

    if not timestamps:
        raise ValueError("No data found in provided files")

    time_from = min(timestamps)
    time_to = max(timestamps)

    # Optionally constrain to window_minutes
    if (time_to - time_from).total_seconds() / 60 > window_minutes:
        time_to = time_from + timedelta(minutes=window_minutes)

    # Run RCA
    sources = DataSourcesConfig(
        logs_dir=logs_path,
        metrics_dir=metrics_path,
        traces_dir=traces_path,
        configs_dir=configs_path,
    )

    return run_rca((time_from, time_to), primary_symptom, sources)
