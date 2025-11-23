"""
Ingestion layer: Load and normalize logs, metrics, traces, and configs.
"""

from autorca_core.ingestion.logs import load_logs
from autorca_core.ingestion.metrics import load_metrics
from autorca_core.ingestion.traces import load_traces
from autorca_core.ingestion.configs import load_configs

__all__ = [
    "load_logs",
    "load_metrics",
    "load_traces",
    "load_configs",
]
