"""Runtime configuration flags for the in-Houdini MCP server."""

from __future__ import annotations

# Built-in
import os

# Third-party
import hou

_FALSY = {"0", "false", "off", "no"}


def auto_layout_enabled() -> bool:
    """Whether handlers may auto-arrange nodes in the network editor.

    Reads ``FXHOUDINIMCP_AUTO_LAYOUT`` via ``hou.getenv`` first (so it can
    be set in houdini.env or toggled at runtime with ``hou.putenv``), then
    falls back to the process environment. Defaults to enabled; set to
    ``0`` to preserve existing node layouts.
    """
    value = hou.getenv("FXHOUDINIMCP_AUTO_LAYOUT")
    if value is None:
        value = os.environ.get("FXHOUDINIMCP_AUTO_LAYOUT", "1")
    return value.strip().lower() not in _FALSY


def layout_if_enabled(node: hou.Node) -> None:
    """Lay out *node*'s children unless auto-layout is disabled."""
    if auto_layout_enabled():
        node.layoutChildren()
