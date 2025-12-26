"""
AutoRCA-Core (ADAPT-RCA): Agentic Root Cause Analysis Engine

A graph-based RCA engine for AI-powered autonomous reliability, SRE, and support.
Analyzes logs, metrics, traces, configs, and documentation to identify root causes
and recommend remediation steps.
"""

__version__ = "0.2.0"
__author__ = "Nik Kale"

from autorca_core.model.events import Event, LogEvent, MetricPoint, Span
from autorca_core.model.graph import Service, Dependency, IncidentNode
from autorca_core.reasoning.loop import run_rca, RCARunResult
from autorca_core.reasoning.llm import AnthropicLLM, DummyLLM
from autorca_core.logging import configure_logging, get_logger
from autorca_core.config import ThresholdConfig
from autorca_core.validation import IngestionLimits, ValidationError

__all__ = [
    "Event",
    "LogEvent",
    "MetricPoint",
    "Span",
    "Service",
    "Dependency",
    "IncidentNode",
    "run_rca",
    "RCARunResult",
    "AnthropicLLM",
    "DummyLLM",
    "configure_logging",
    "get_logger",
    "ThresholdConfig",
    "IngestionLimits",
    "ValidationError",
]
