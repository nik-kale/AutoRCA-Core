"""
Tests for the MCP tool handlers (called directly; the mcp package is not needed).
"""

import asyncio
import json
import logging
import os
import sys
import types

import pytest

from autorca_core.mcp import server

QUICKSTART_LOGS = os.path.join(
    os.path.dirname(__file__), "..", "examples", "quickstart_local_logs", "logs.jsonl"
)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def log_dir(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (allowed / "app.jsonl").write_text(
        json.dumps({"timestamp": "2025-11-10T10:00:00Z", "service": "api", "level": "ERROR",
                    "message": "boom"}) + "\n"
    )
    secret = tmp_path / "secret"
    secret.mkdir()
    (secret / "creds.log").write_text("2025-11-10T10:00:00Z ERROR vault token=abc\n")
    return tmp_path


def test_paths_outside_allowed_roots_are_rejected(log_dir, monkeypatch):
    monkeypatch.setenv(server.ALLOWED_ROOTS_ENV, str(log_dir / "allowed"))

    ok = _run(server._handle_analyze_logs({"logs_path": str(log_dir / "allowed")}))
    assert "**Error Logs:** 1" in ok

    for path in (str(log_dir / "secret"), str(log_dir / "allowed" / ".." / "secret")):
        with pytest.raises(PermissionError):
            _run(server._handle_analyze_logs({"logs_path": path}))
    with pytest.raises(PermissionError):
        _run(server._handle_get_service_graph(
            {"logs_path": str(log_dir / "allowed"), "traces_path": str(log_dir / "secret")}
        ))


def test_symlink_out_of_allowed_root_is_rejected(log_dir, monkeypatch):
    link = log_dir / "allowed" / "link.log"
    link.symlink_to(log_dir / "secret" / "creds.log")
    monkeypatch.setenv(server.ALLOWED_ROOTS_ENV, str(log_dir / "allowed"))

    with pytest.raises(PermissionError):
        _run(server._handle_analyze_logs({"logs_path": str(link)}))


def test_unrestricted_when_env_unset(log_dir, monkeypatch):
    monkeypatch.delenv(server.ALLOWED_ROOTS_ENV, raising=False)

    out = _run(server._handle_analyze_logs({"logs_path": str(log_dir / "secret")}))

    assert "vault" in out


def test_analyze_logs_accepts_z_suffixed_window():
    """fromisoformat() rejects a trailing "Z" on Python 3.10, and a naive window could
    not be compared with the parsed (aware) log timestamps."""
    out = _run(server._handle_analyze_logs({
        "logs_path": QUICKSTART_LOGS,
        "time_from": "2025-11-10T10:00:10Z",
        "time_to": "2025-11-10T10:00:20",
    }))

    assert "**Total Logs:** 8" in out


def test_run_rca_rejects_bad_window_minutes():
    with pytest.raises(ValueError):
        _run(server._handle_run_rca(
            {"logs_path": QUICKSTART_LOGS, "symptom": "x", "window_minutes": -5}
        ))


@pytest.fixture
def restore_logging():
    base = logging.getLogger("autorca_core")
    handlers, level, propagate = list(base.handlers), base.level, base.propagate
    yield
    base.handlers[:] = handlers
    base.setLevel(level)
    base.propagate = propagate


def test_log_level_env_is_honored(monkeypatch, restore_logging):
    """docs/MCP_INTEGRATION.md documents AUTORCA_LOG_LEVEL; it was ignored."""
    stdio = types.ModuleType("mcp.server.stdio")
    stdio.stdio_server = None
    monkeypatch.setitem(sys.modules, "mcp", types.ModuleType("mcp"))
    monkeypatch.setitem(sys.modules, "mcp.server", types.ModuleType("mcp.server"))
    monkeypatch.setitem(sys.modules, "mcp.server.stdio", stdio)
    monkeypatch.setattr(server, "create_mcp_server", lambda: None)
    monkeypatch.setattr(server.asyncio, "run", lambda coro: coro.close())
    monkeypatch.setenv(server.LOG_LEVEL_ENV, "debug")

    server.start_mcp_server()

    assert logging.getLogger("autorca_core").level == logging.DEBUG
