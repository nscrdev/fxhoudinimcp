"""Tests for Houdini-side startup health checks."""

from __future__ import annotations

# Built-in
import os
import sys

# Third-party
import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "houdini", "scripts", "python"),
)

from fxhoudinimcp_server import startup  # noqa: E402


@pytest.fixture(autouse=True)
def reset_startup_state(monkeypatch):
    monkeypatch.setattr(startup, "_server_started", False)
    monkeypatch.setattr(startup, "_port", 8100)


def test_wait_for_current_process_health_accepts_current_pid(monkeypatch):
    monkeypatch.setattr(
        startup,
        "_query_health",
        lambda port: {
            "status": "ok",
            "pid": os.getpid(),
            "houdini_version": "21.0.631",
        },
    )

    health = startup._wait_for_current_process_health(8100)

    assert health is not None
    assert health["pid"] == os.getpid()


def test_ensure_running_restarts_when_cached_state_is_stale(monkeypatch):
    calls = []
    monkeypatch.setattr(startup, "_server_started", True)
    monkeypatch.setattr(
        startup,
        "_wait_for_current_process_health",
        lambda port, timeout_seconds=0.5: None,
    )
    monkeypatch.setattr(startup, "start", lambda: calls.append("start"))

    startup.ensure_running()

    assert calls == ["start"]


def test_ensure_running_keeps_live_server(monkeypatch):
    calls = []
    monkeypatch.setattr(startup, "_server_started", True)
    monkeypatch.setattr(
        startup,
        "_wait_for_current_process_health",
        lambda port, timeout_seconds=0.5: {"pid": os.getpid()},
    )
    monkeypatch.setattr(startup, "start", lambda: calls.append("start"))

    startup.ensure_running()

    assert calls == []
