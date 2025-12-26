"""
Trace ingestion: Load and parse distributed trace spans.

Supports OpenTelemetry and Jaeger JSON formats.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from autorca_core.model.events import Span
from autorca_core.logging import get_logger

logger = get_logger(__name__)


def load_traces(
    source: str,
    time_from: Optional[datetime] = None,
    time_to: Optional[datetime] = None,
    service_filter: Optional[str] = None,
    trace_id_filter: Optional[str] = None,
) -> List[Span]:
    """
    Load trace spans from a file or directory.

    Args:
        source: Path to trace file or directory
        time_from: Start of time window (inclusive)
        time_to: End of time window (inclusive)
        service_filter: Only include spans from this service
        trace_id_filter: Only include spans from this trace

    Returns:
        List of Span objects
    """
    source_path = Path(source)

    if not source_path.exists():
        raise FileNotFoundError(f"Trace source not found: {source}")

    spans = []

    if source_path.is_file():
        spans.extend(_load_trace_file(source_path))
    else:
        # Load all .jsonl, .json files in directory
        extensions = ['*.jsonl', '*.json']
        for ext in extensions:
            for file_path in source_path.glob(f"**/{ext}"):
                spans.extend(_load_trace_file(file_path))

    # Apply filters
    if time_from:
        spans = [s for s in spans if s.timestamp >= time_from]
    if time_to:
        spans = [s for s in spans if s.timestamp <= time_to]
    if service_filter:
        spans = [s for s in spans if s.service == service_filter]
    if trace_id_filter:
        spans = [s for s in spans if s.trace_id == trace_id_filter]

    return sorted(spans, key=lambda s: s.timestamp)


def _load_trace_file(file_path: Path) -> List[Span]:
    """Load a single trace file."""
    spans = []

    with open(file_path, 'r', encoding='utf-8') as f:
        # Try to parse as JSON array first
        try:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    span = _parse_span(item)
                    if span:
                        spans.append(span)
                return spans
        except json.JSONDecodeError:
            # Fall back to JSON Lines
            f.seek(0)

        # Parse as JSON Lines
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
                span = _parse_span(item)
                if span:
                    spans.append(span)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON line {line_num} in {file_path}: {e}")

    return spans


def _parse_span(item: Dict[str, Any]) -> Optional[Span]:
    """
    Parse a span from JSON.

    Supports OpenTelemetry and Jaeger-style span formats.
    """
    try:
        # Extract timestamp (may be in nanoseconds or ISO format)
        timestamp_val = item.get('timestamp') or item.get('start_time') or item.get('startTime')
        if not timestamp_val:
            return None

        if isinstance(timestamp_val, (int, float)):
            # Assume nanoseconds or microseconds
            if timestamp_val > 1e15:  # Likely nanoseconds
                timestamp = datetime.fromtimestamp(timestamp_val / 1e9)
            elif timestamp_val > 1e12:  # Likely microseconds
                timestamp = datetime.fromtimestamp(timestamp_val / 1e6)
            else:  # Likely seconds
                timestamp = datetime.fromtimestamp(timestamp_val)
        else:
            timestamp = datetime.fromisoformat(str(timestamp_val).replace('Z', '+00:00'))

        # Extract required fields
        span_id = item.get('span_id') or item.get('spanId') or item.get('id', 'unknown')
        trace_id = item.get('trace_id') or item.get('traceId', 'unknown')
        service = item.get('service') or item.get('service_name') or item.get('serviceName', 'unknown')

        # Extract optional fields
        parent_span_id = item.get('parent_span_id') or item.get('parentSpanId') or item.get('parent_id')
        operation_name = item.get('operation_name') or item.get('operationName') or item.get('name', '')

        # Extract duration (may be in nanoseconds, microseconds, or milliseconds)
        duration_val = item.get('duration') or item.get('duration_ms') or 0.0
        if isinstance(duration_val, (int, float)):
            if duration_val > 1e6:  # Likely nanoseconds
                duration_ms = duration_val / 1e6
            elif duration_val > 1e3:  # Likely microseconds
                duration_ms = duration_val / 1e3
            else:  # Likely milliseconds
                duration_ms = float(duration_val)
        else:
            duration_ms = 0.0

        # Extract status
        status_code = item.get('status_code') or item.get('statusCode') or item.get('http_status')
        error = item.get('error', False) or item.get('has_error', False)

        # Extract tags
        tags = item.get('tags', {})
        if isinstance(tags, dict):
            tags = {str(k): str(v) for k, v in tags.items()}
        else:
            tags = {}

        return Span(
            timestamp=timestamp,
            service=service,
            span_id=str(span_id),
            trace_id=str(trace_id),
            parent_span_id=str(parent_span_id) if parent_span_id else None,
            operation_name=operation_name,
            duration_ms=duration_ms,
            status_code=int(status_code) if status_code else None,
            error=error,
            tags=tags,
            raw_data=item,
        )
    except (ValueError, KeyError):
        return None
