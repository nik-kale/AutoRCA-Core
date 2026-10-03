"""
Tests for the ingestion layer (logs, metrics, traces, configs).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from autorca_core.ingestion import load_logs
from autorca_core.model.events import EventType, LogEvent, Severity

EXAMPLES = Path(__file__).parent.parent / "examples" / "quickstart_local_logs"


def _write_jsonl(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def test_log_event_constructible_without_event_type():
    event = LogEvent(
        timestamp=datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc),
        service="api",
        message="boom",
        level=Severity.ERROR,
    )
    assert event.event_type == EventType.LOG
    assert event.is_error()


def test_load_logs_parses_json_lines(tmp_path):
    log_file = tmp_path / "app.jsonl"
    _write_jsonl(
        log_file,
        [
            {"timestamp": "2025-11-10T10:00:00Z", "service": "api", "level": "ERROR",
             "message": "upstream timeout", "trace_id": "t1"},
            {"timestamp": "2025-11-10T10:00:01Z", "service": "db", "level": "warn",
             "message": "slow query"},
        ],
    )

    events = load_logs(str(log_file))

    assert [e.service for e in events] == ["api", "db"]
    assert events[0].level == Severity.ERROR
    assert events[0].trace_id == "t1"
    assert events[1].level == Severity.WARN


def test_load_logs_parses_plain_text(tmp_path):
    log_file = tmp_path / "app.log"
    log_file.write_text("2025-11-10T10:00:00Z ERROR api-gateway Upstream timeout\n")

    events = load_logs(str(log_file))

    assert len(events) == 1
    assert events[0].service == "api-gateway"
    assert events[0].level == Severity.ERROR
    assert events[0].message == "Upstream timeout"


def test_quickstart_logs_are_all_ingested():
    events = load_logs(str(EXAMPLES / "logs.jsonl"))
    line_count = sum(1 for line in (EXAMPLES / "logs.jsonl").read_text().splitlines() if line)
    assert len(events) == line_count
