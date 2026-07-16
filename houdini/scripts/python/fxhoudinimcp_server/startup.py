"""Server startup and lifecycle management.

Handles starting/stopping the hwebserver and loading handler modules.
"""

from __future__ import annotations

# Built-in
import json
import os
import time
import urllib.parse
import urllib.request

_server_started = False
_port = 8100


def _health_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/api"


def _health_body() -> bytes:
    return urllib.parse.urlencode(
        {"json": json.dumps(["mcp.health", [], {}])}
    ).encode("utf-8")


def _query_health(port: int, timeout: float = 0.5) -> dict | None:
    request = urllib.request.Request(
        _health_url(port),
        data=_health_body(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except Exception:
        return None

    try:
        data = json.loads(payload)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _wait_for_current_process_health(
    port: int,
    timeout_seconds: float = 3.0,
) -> dict | None:
    deadline = time.time() + max(0.0, timeout_seconds)
    current_pid = os.getpid()
    last_health = None
    while time.time() < deadline:
        health = _query_health(port)
        if health is not None:
            last_health = health
            if health.get("pid") == current_pid:
                return health
        time.sleep(0.1)
    return last_health


def start(port: int | None = None) -> None:
    """Start the FXHoudini-MCP server.

    Registers all command handlers and ensures hwebserver is running.

    Args:
        port: Port for hwebserver. Defaults to FXHOUDINIMCP_PORT env var or 8100.
    """
    global _server_started, _port

    if _server_started:
        print("[fxhoudinimcp] Server already running")
        return

    _port = port or int(os.environ.get("FXHOUDINIMCP_PORT", "8100"))

    # Import handlers to trigger registration via register_handler() calls
    from fxhoudinimcp_server import handlers  # noqa: F401

    # Import hwebserver_app to register the API functions
    from fxhoudinimcp_server import hwebserver_app  # noqa: F401

    # Start hwebserver if not already running. In Houdini 20.5+ it may already
    # be running for built-in features; in that case registering the functions
    # above is enough. Either way, prove the HTTP endpoint is reachable before
    # advertising readiness.
    import hwebserver

    run_error = None
    try:
        hwebserver.run(_port, debug=False)
    except Exception as exc:
        run_error = exc

    # mcp.health is served on Houdini's main thread, so polling it
    # synchronously here (also the main thread during startup) deadlocks
    # until the timeout and reports a false failure. Verify from a
    # background thread instead, once the main loop is free again.
    _server_started = True

    def _verify() -> None:
        global _server_started
        health = _wait_for_current_process_health(_port, timeout_seconds=10.0)
        if health is None:
            _server_started = False
            detail = f": {run_error}" if run_error is not None else ""
            print(
                "[fxhoudinimcp] Startup FAILED: hwebserver did not answer "
                f"mcp.health on port {_port}{detail}"
            )
            return

        health_pid = health.get("pid")
        if health_pid != os.getpid():
            _server_started = False
            print(
                "[fxhoudinimcp] Startup FAILED: hwebserver port {} is owned "
                "by another Houdini process (pid {}), current pid {}".format(
                    _port, health_pid, os.getpid()
                )
            )
            return

        print(
            "[fxhoudinimcp] Server ready on port {} "
            "(Houdini {}, pid {})".format(
                _port,
                health.get("houdini_version", "unknown"),
                health.get("pid", "unknown"),
            )
        )

    import threading

    threading.Thread(
        target=_verify, name="fxhoudinimcp-health", daemon=True
    ).start()


def stop() -> None:
    """Stop the FXHoudini-MCP server."""
    global _server_started
    if not _server_started:
        return

    # Note: we don't call hwebserver.requestShutdown() because that would
    # kill Houdini's built-in web server too. We just mark ourselves as stopped.
    _server_started = False
    print("[fxhoudinimcp] Server stopped")


def is_running() -> bool:
    """Check if the server is currently running."""
    return _server_started


def get_port() -> int:
    """Get the port the server is running on."""
    return _port


def ensure_running() -> None:
    """Start the server if it's not already running."""
    global _server_started
    if _server_started:
        health = _wait_for_current_process_health(_port, timeout_seconds=0.5)
        if health is not None and health.get("pid") == os.getpid():
            return
        _server_started = False
    start()
