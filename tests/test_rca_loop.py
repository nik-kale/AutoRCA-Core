"""
Tests for the end-to-end RCA loop and the public package API.
"""

import json
from datetime import datetime, timezone

from autorca_core.config import ThresholdConfig
from autorca_core.model.graph import IncidentType
from autorca_core.reasoning.loop import DataSourcesConfig, run_rca


def _write_jsonl(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def test_public_api_exports_readme_names():
    """The names used in the README quickstart import from the package root."""
    import autorca_core

    for name in ("run_rca", "DataSourcesConfig", "AnthropicLLM", "RCARunResult"):
        assert hasattr(autorca_core, name), name
        assert name in autorca_core.__all__, name


def test_run_rca_honors_threshold_config(tmp_path):
    """Thresholds passed to run_rca must reach anomaly detection and the rules."""
    metrics_file = tmp_path / "metrics.jsonl"
    _write_jsonl(
        metrics_file,
        [
            {
                "timestamp": f"2025-11-10T10:00:{s:02d}Z",
                "service": "api",
                "metric_name": "request_latency_p95",
                "value": 1500,
            }
            for s in (0, 10, 20)
        ],
    )
    window = (
        datetime(2025, 11, 10, 10, 0, 0, tzinfo=timezone.utc),
        datetime(2025, 11, 10, 10, 5, 0, tzinfo=timezone.utc),
    )
    sources = DataSourcesConfig(metrics_dir=str(metrics_file))

    default = run_rca(window, "slow api", sources)
    relaxed = run_rca(window, "slow api", sources, thresholds=ThresholdConfig.relaxed())

    def latency_incidents(result):
        return [
            i
            for i in result.service_graph.incidents
            if i.incident_type == IncidentType.LATENCY_SPIKE
        ]

    # 1500ms breaches the default 1000ms threshold but not the relaxed 2000ms one.
    assert len(latency_incidents(default)) == 1
    assert latency_incidents(relaxed) == []
