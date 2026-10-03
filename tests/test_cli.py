"""
Tests for the autorca command-line interface.
"""

import json
import os
import sys

import pytest

from autorca_core.cli.__main__ import main

QUICKSTART = os.path.join(os.path.dirname(__file__), "..", "examples", "quickstart_local_logs")


@pytest.fixture(autouse=True)
def restore_logging():
    import logging

    base = logging.getLogger("autorca_core")
    handlers, level = list(base.handlers), base.level
    yield
    base.handlers[:] = handlers
    base.setLevel(level)


def _run_cli(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["autorca", *argv])
    main()


def test_json_report_on_stdout_is_valid_json(monkeypatch, capsys):
    """Progress banners were printed to stdout around the report, so
    `autorca run --format json > report.json` produced an unparsable file."""
    _run_cli(
        monkeypatch, "run", "--quiet", "--format", "json",
        "--logs", os.path.join(QUICKSTART, "logs.jsonl"),
        "--metrics", os.path.join(QUICKSTART, "metrics.jsonl"),
        "--from", "2025-11-10T10:00:00Z", "--to", "2025-11-10T10:05:00",
    )

    out = capsys.readouterr()
    report = json.loads(out.out)
    assert report["metadata"]["num_logs"] == 20
    assert "RCA completed successfully!" in out.err


def test_from_without_to_is_an_error(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_cli(monkeypatch, "run", "--quiet", "--logs", QUICKSTART,
                 "--from", "2025-11-10T10:00:00Z")

    assert exc.value.code == 1
    assert "--from and --to" in capsys.readouterr().err
