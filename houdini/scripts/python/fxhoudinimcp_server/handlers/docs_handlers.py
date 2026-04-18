"""Docs handlers — expose Houdini's built-in help server to the MCP.

Houdini ships a local HTTP documentation server that serves the same pages
as sidefx.com/docs but for the exact Houdini version that is running. This
handler's sole job is to tell the MCP process what URL that help server is
bound to. The MCP then fetches docs directly from that URL over localhost,
bypassing the bridge entirely for the actual content — no main-thread
marshalling needed for what is fundamentally just HTTP to 127.0.0.1.
"""

from __future__ import annotations

# Built-in
import os

# Third-party
import hou

# Internal
from fxhoudinimcp_server.dispatcher import register_handler


def get_help_server_url() -> dict:
    """Return the URL of Houdini's local help server.

    Discovery methods, tried in order:
      1. HScript ``helpserverurl`` command (primary — works on all versions).
      2. ``HOUDINI_HELPSERVER_PORT`` env var (fallback).

    Returns:
        ``{"url": "http://127.0.0.1:<port>"}``

    Raises:
        RuntimeError: if no discovery method returns a valid URL.
    """
    try:
        out, _err = hou.hscript("helpserverurl")
        if out:
            url = out.strip() if isinstance(out, str) else str(out[0]).strip()
            if url:
                return {"url": url}
    except Exception:
        pass

    port = os.environ.get("HOUDINI_HELPSERVER_PORT")
    if port:
        return {"url": f"http://127.0.0.1:{port}"}

    raise RuntimeError(
        "Could not discover Houdini help server URL. "
        "Enable it via Edit > Preferences > Help Browser, "
        "or set HOUDINI_HELPSERVER_PORT."
    )


register_handler("docs.get_help_server_url", get_help_server_url)
