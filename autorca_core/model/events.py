"""
Event models: LogEvent, MetricPoint, Span, and base Event class.

These models represent normalized observations from logs, metrics, traces, and configs.
"""

from datetime import datetime
from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass, field
from enum import Enum


class EventType(str, Enum):
    """Type of observability event."""
    LOG = "log"
    METRIC = "metric"
    TRACE = "trace"
    CONFIG = "config"
    DEPLOYMENT = "deployment"


class Severity(str, Enum):
    """Severity/level of an event."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Event:
    """
    Base event class for all observability signals.

    All ingestion modules normalize their data into Event or subclass instances.
    """
    timestamp: datetime
    service: str
    event_type: EventType
    raw_data: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure timestamp is a datetime object."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))


@dataclass
class LogEvent(Event):
    """
    Normalized log event.

    Attributes:
        message: Log message text
        level: Log severity (DEBUG, INFO, WARN, ERROR, CRITICAL)
        logger: Logger name (optional)
        trace_id: Distributed trace ID (optional, for correlation)
        request_id: Request ID (optional, for correlation)
        error_type: Error class or type (optional)
        stack_trace: Stack trace if available (optional)
    """
    message: str = ""
    level: Severity = Severity.INFO
    logger: Optional[str] = None
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.LOG

    def is_error(self) -> bool:
        """Check if this is an error-level log."""
        return self.level in (Severity.ERROR, Severity.CRITICAL)


@dataclass
class MetricPoint:
    """
    Normalized metric data point.

    Represents a single metric observation (e.g., CPU%, request count, latency p95).
    """
    timestamp: datetime
    service: str
    metric_name: str
    value: float
    unit: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure timestamp is a datetime object."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))


@dataclass
class Span:
    """
    Normalized distributed trace span.

    Represents a single operation in a distributed trace.
    """
    timestamp: datetime
    service: str
    span_id: str
    trace_id: str
    parent_span_id: Optional[str] = None
    operation_name: str = ""
    duration_ms: float = 0.0
    status_code: Optional[int] = None
    error: bool = False
    tags: Dict[str, str] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure timestamp is a datetime object."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))

    def is_error(self) -> bool:
        """Check if this span represents an error."""
        return self.error or (self.status_code is not None and self.status_code >= 400)


@dataclass
class ConfigChange:
    """
    Represents a configuration or deployment change event.

    Used to correlate incidents with recent changes.
    """
    timestamp: datetime
    service: str
    change_type: Literal["config", "deployment", "scaling", "other"] = "config"
    description: str = ""
    version_before: Optional[str] = None
    version_after: Optional[str] = None
    changed_by: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure timestamp is a datetime object."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
