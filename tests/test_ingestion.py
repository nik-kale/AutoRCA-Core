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


def test_to_utc_normalizes_naive_aware_and_strings():
    from datetime import timedelta

    from autorca_core.model.events import to_utc

    expected = datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc)
    assert to_utc("2025-11-10T10:00:00Z") == expected
    assert to_utc("2025-11-10T12:00:00+02:00") == expected
    assert to_utc(datetime(2025, 11, 10, 10, 0)) == expected
    assert to_utc(expected.astimezone(timezone(timedelta(hours=-8)))).tzinfo == timezone.utc


def test_load_traces_mixes_epoch_and_iso_timestamps(tmp_path):
    """Epoch timestamps used to produce naive datetimes that could not be sorted
    alongside ISO "Z" timestamps from the same source."""
    from autorca_core.ingestion import load_traces

    trace_file = tmp_path / "traces.jsonl"
    _write_jsonl(
        trace_file,
        [
            {"timestamp": "2025-11-10T10:00:01Z", "service": "api", "span_id": "b",
             "trace_id": "t"},
            # 2025-11-10T10:00:00Z in epoch nanoseconds
            {"start_time": 1762768800_000_000_000, "service": "db", "span_id": "a",
             "trace_id": "t"},
        ],
    )

    spans = load_traces(str(trace_file))

    assert [s.span_id for s in spans] == ["a", "b"]
    assert spans[0].timestamp == datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc)


def test_load_configs_from_directory_finds_json_and_yaml(tmp_path):
    """The directory glob used brace expansion, which pathlib does not support,
    so a configs directory always loaded zero changes."""
    from autorca_core.ingestion import load_configs

    (tmp_path / "deploys.json").write_text(
        json.dumps([{"timestamp": "2025-11-10T10:00:00Z", "service": "api", "type": "deploy",
                     "version": "v2"}])
    )
    (tmp_path / "flags.yaml").write_text(
        "- timestamp: 2025-11-10T10:01:00Z\n  service: db\n  change_type: config\n"
    )

    changes = load_configs(str(tmp_path))

    assert [(c.service, c.change_type) for c in changes] == [
        ("api", "deployment"),
        ("db", "config"),
    ]


def test_single_record_json_files_are_not_dropped(tmp_path):
    """A one-line JSONL file (or a single JSON object) used to be read as a
    top-level object, ignored, and then the exhausted file yielded nothing."""
    from autorca_core.ingestion import load_configs, load_metrics, load_traces

    metric = tmp_path / "metrics.jsonl"
    metric.write_text(json.dumps({"timestamp": "2025-11-10T10:00:00Z", "service": "api",
                                  "metric_name": "cpu_percent", "value": 97}) + "\n")
    span = tmp_path / "traces.json"
    span.write_text(json.dumps({"timestamp": "2025-11-10T10:00:00Z", "service": "api",
                                "span_id": "s1", "trace_id": "t1"}))
    change = tmp_path / "change.json"
    change.write_text(json.dumps({"timestamp": "2025-11-10T10:00:00Z", "service": "api"}))

    assert len(load_metrics(str(metric))) == 1
    assert len(load_traces(str(span))) == 1
    assert len(load_configs(str(change))) == 1


def test_malformed_records_are_skipped_not_fatal(tmp_path):
    from autorca_core.ingestion import load_metrics

    metric = tmp_path / "metrics.jsonl"
    metric.write_text(
        "\n".join([
            json.dumps("not an object"),
            json.dumps({"timestamp": "2025-11-10T10:00:00Z", "service": "api",
                        "metric_name": "cpu_percent", "value": None}),
            json.dumps({"timestamp": "2025-11-10T10:00:01Z", "service": "api",
                        "metric_name": "cpu_percent", "value": 42}),
        ]) + "\n"
    )

    metrics = load_metrics(str(metric))

    assert [m.value for m in metrics] == [42.0]


def test_explicit_duration_ms_is_not_rescaled(tmp_path):
    """duration_ms=1500 is 1.5s; the unit heuristic used to treat it as
    microseconds and report 1.5ms, hiding the latency."""
    from autorca_core.ingestion import load_traces

    trace_file = tmp_path / "traces.jsonl"
    _write_jsonl(
        trace_file,
        [
            {"timestamp": "2025-11-10T10:00:00Z", "service": "api", "span_id": "a",
             "trace_id": "t", "duration_ms": 1500},
            {"timestamp": "2025-11-10T10:00:01Z", "service": "api", "span_id": "b",
             "trace_id": "t", "duration": 2_500_000_000},  # unitless, nanoseconds
            {"timestamp": "2025-11-10T10:00:02Z", "service": "api", "span_id": "c",
             "trace_id": "t", "status_code": "ERROR", "error": True},
        ],
    )

    spans = {s.span_id: s for s in load_traces(str(trace_file))}

    assert spans["a"].duration_ms == 1500.0
    assert spans["b"].duration_ms == 2500.0
    # A non-numeric status code no longer drops the span
    assert spans["c"].status_code is None and spans["c"].is_error()


def _metric(second):
    return {"timestamp": f"2025-11-10T10:00:{second:02d}Z", "service": "api",
            "metric_name": "cpu_percent", "value": 50}


def test_symlink_escaping_source_dir_is_skipped(tmp_path):
    """A symlink pointing outside the directory used to raise PathTraversalError
    out of load_logs and abort the whole load; it is now skipped."""
    outside = tmp_path / "outside.log"
    outside.write_text("2025-11-10T10:00:00Z ERROR secret-service do not read\n")
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "app.log").write_text("2025-11-10T10:00:01Z ERROR api boom\n")
    (logs_dir / "escape.log").symlink_to(outside)

    events = load_logs(str(logs_dir))

    assert [e.service for e in events] == ["api"]


def test_file_and_event_limits_apply_to_every_loader(tmp_path):
    from autorca_core.ingestion import load_metrics
    from autorca_core.validation import IngestionLimits

    for i in range(3):
        _write_jsonl(tmp_path / f"m{i}.jsonl", [_metric(i * 10 + s) for s in range(4)])
    _write_jsonl(tmp_path / "extra.json", [_metric(50)])

    by_files = load_metrics(str(tmp_path), limits=IngestionLimits(max_files_per_directory=2))
    by_events = load_metrics(str(tmp_path), limits=IngestionLimits(max_total_events=5))

    # File limit spans all patterns, not just the first extension
    assert len(by_files) == 8
    # Event cap is enforced, not merely warned about after loading everything
    assert len(by_events) == 5


def test_oversized_file_is_skipped_in_directory(tmp_path):
    from autorca_core.ingestion import load_traces
    from autorca_core.validation import IngestionLimits

    big = tmp_path / "big.json"
    big.write_text(json.dumps([{"timestamp": "2025-11-10T10:00:00Z", "service": "api",
                                "span_id": str(i), "trace_id": "t"} for i in range(2000)]))
    _write_jsonl(tmp_path / "small.jsonl", [{"timestamp": "2025-11-10T10:00:00Z",
                                            "service": "db", "span_id": "x", "trace_id": "u"}])

    spans = load_traces(str(tmp_path), limits=IngestionLimits(max_file_size_mb=0.01))

    assert [s.service for s in spans] == ["db"]
