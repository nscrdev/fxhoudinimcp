"""Utility for loading markdown prompt files with disk-read caching."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fxhoudinimcp.config import auto_layout_enabled

_MD_DIR = Path(__file__).parent / "prompts" / "markdown"

_LAYOUT_GUIDANCE_ON = (
    "Call layout_children frequently — after every batch of 3-5 new nodes, "
    "not just at the end. A tidy graph lets the user follow along in real "
    "time."
)
_LAYOUT_GUIDANCE_OFF = (
    "Auto-layout is disabled (FXHOUDINIMCP_AUTO_LAYOUT=0). NEVER call "
    "layout_children or move existing nodes — the user manages node "
    "placement manually. Leave node positions exactly as they are."
)


@lru_cache(maxsize=None)
def _read(name: str) -> str:
    """Read a markdown file once and cache it for the process lifetime."""
    return (_MD_DIR / name).read_text(encoding="utf-8")


def _layout_guidance() -> str:
    """Layout instruction matching the current auto-layout toggle."""
    return _LAYOUT_GUIDANCE_ON if auto_layout_enabled() else _LAYOUT_GUIDANCE_OFF


def load_markdown(name: str, **kwargs: str) -> str:
    """Load a markdown prompt file, optionally formatting placeholders.

    File contents are cached after the first read — the files never change
    at runtime, so this avoids repeated disk I/O on every prompt invocation.

    Args:
        name: Filename (with .md extension) inside the ``markdown/`` directory.
        **kwargs: Values to substitute into ``{placeholder}`` tokens in the
            markdown text.  The special keys ``network_housekeeping`` and
            ``layout_guidance`` are automatically populated if not explicitly
            provided.

    Returns:
        The formatted markdown string.
    """
    text = _read(name)

    if "{layout_guidance}" in text and "layout_guidance" not in kwargs:
        kwargs["layout_guidance"] = _layout_guidance()
    if "{network_housekeeping}" in text and "network_housekeeping" not in kwargs:
        kwargs["network_housekeeping"] = _read(
            "network_housekeeping.md"
        ).format(layout_guidance=_layout_guidance())
    if kwargs:
        text = text.format(**kwargs)

    return text
