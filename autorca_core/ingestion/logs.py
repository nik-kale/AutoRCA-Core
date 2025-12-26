"""
Log ingestion: Load and parse log files into LogEvent objects.

Supports JSON Lines, plain text, and structured log formats.
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from autorca_core.model.events import LogEvent, Severity


def load_logs(
    source: str,
    time_from: Optional[datetime] = None,
    time_to: Optional[datetime] = None,
    service_filter: Optional[str] = None,
) -> List[LogEvent]:
    """
    Load logs from a file or directory.

    Args:
        source: Path to log file or directory
        time_from: Start of time window (inclusive)
        time_to: End of time window (inclusive)
        service_filter: Only include logs from this service

    Returns:
        List of LogEvent objects
    """
    source_path = Path(source)

    if not source_path.exists():
        raise FileNotFoundError(f"Log source not found: {source}")

    events = []

    if source_path.is_file():
        events.extend(_load_log_file(source_path))
    else:
        # Load all .log, .jsonl, .txt files in directory
        extensions = ['*.log', '*.jsonl', '*.txt']
        for ext in extensions:
            for file_path in source_path.glob(f"**/{ext}"):
                events.extend(_load_log_file(file_path))

    # Apply filters
    if time_from:
        events = [e for e in events if e.timestamp >= time_from]
    if time_to:
        events = [e for e in events if e.timestamp <= time_to]
    if service_filter:
        events = [e for e in events if e.service == service_filter]

    return sorted(events, key=lambda e: e.timestamp)


def _load_log_file(file_path: Path) -> List[LogEvent]:
    """Load a single log file."""
    events = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                # Try JSON parsing first
                event = _parse_json_log(line)
                if event:
                    events.append(event)
                else:
                    # Fall back to plain text parsing
                    event = _parse_text_log(line)
                    if event:
                        events.append(event)
            except Exception as e:
                # Log parsing errors are non-fatal
                print(f"Warning: Failed to parse line {line_num} in {file_path}: {e}")

    return events


def _parse_json_log(line: str) -> Optional[LogEvent]:
    """Parse a JSON-formatted log line."""
    try:
        data = json.loads(line)

        # Extract timestamp
        timestamp_str = data.get('timestamp') or data.get('time') or data.get('@timestamp')
        if not timestamp_str:
            # Use current time as fallback
            timestamp = datetime.utcnow()
        else:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

        # Extract service
        service = data.get('service') or data.get('service_name') or data.get('app') or 'unknown'

        # Extract message
        message = data.get('message') or data.get('msg') or str(data)

        # Extract level
        level_str = data.get('level') or data.get('severity') or data.get('loglevel') or 'INFO'
        level = _parse_severity(level_str)

        # Extract optional fields
        logger = data.get('logger') or data.get('logger_name')
        trace_id = data.get('trace_id') or data.get('traceId')
        request_id = data.get('request_id') or data.get('requestId')
        error_type = data.get('error_type') or data.get('exception_type')
        stack_trace = data.get('stack_trace') or data.get('stacktrace')

        return LogEvent(
            timestamp=timestamp,
            service=service,
            message=message,
            level=level,
            logger=logger,
            trace_id=trace_id,
            request_id=request_id,
            error_type=error_type,
            stack_trace=stack_trace,
            raw_data=data,
        )
    except (json.JSONDecodeError, ValueError):
        return None


def _parse_text_log(line: str) -> Optional[LogEvent]:
    """
    Parse a plain text log line.

    Attempts to extract timestamp, level, service, and message using common patterns.
    """
    # Common log pattern: [timestamp] [level] [service] message
    # Example: 2025-11-10T10:00:00Z ERROR api-gateway Upstream timeout
    pattern = r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)\s+(\w+)\s+(\S+)\s+(.+)'
    match = re.match(pattern, line)

    if match:
        timestamp_str, level_str, service, message = match.groups()

        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            timestamp = datetime.utcnow()

        level = _parse_severity(level_str)

        return LogEvent(
            timestamp=timestamp,
            service=service,
            message=message.strip(),
            level=level,
            raw_data={"raw_line": line},
        )

    # If pattern doesn't match, create a basic log event
    return LogEvent(
        timestamp=datetime.utcnow(),
        service="unknown",
        message=line,
        level=Severity.INFO,
        raw_data={"raw_line": line},
    )


def _parse_severity(level_str: str) -> Severity:
    """Parse severity string into Severity enum."""
    level_upper = level_str.upper()

    if 'CRIT' in level_upper or 'FATAL' in level_upper:
        return Severity.CRITICAL
    elif 'ERR' in level_upper:
        return Severity.ERROR
    elif 'WARN' in level_upper:
        return Severity.WARN
    elif 'DEBUG' in level_upper or 'TRACE' in level_upper:
        return Severity.DEBUG
    else:
        return Severity.INFO
