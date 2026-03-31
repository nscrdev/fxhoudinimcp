"""Utility for loading markdown prompt files with disk-read caching."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_MD_DIR = Path(__file__).parent / "prompts" / "markdown"


@lru_cache(maxsize=None)
def _read(name: str) -> str:
    """Read a markdown file once and cache it for the process lifetime."""
    return (_MD_DIR / name).read_text(encoding="utf-8")


def load_markdown(name: str, **kwargs: str) -> str:
    """Load a markdown prompt file, optionally formatting placeholders.

    File contents are cached after the first read — the files never change
    at runtime, so this avoids repeated disk I/O on every prompt invocation.

    Args:
        name: Filename (with .md extension) inside the ``markdown/`` directory.
        **kwargs: Values to substitute into ``{placeholder}`` tokens in the
            markdown text.  The special key ``network_housekeeping`` is
            automatically populated from ``network_housekeeping.md`` if not
            explicitly provided.

    Returns:
        The formatted markdown string.
    """
    text = _read(name)

    if kwargs:
        if (
            "network_housekeeping" not in kwargs
            and "{network_housekeeping}" in text
        ):
            kwargs["network_housekeeping"] = _read("network_housekeeping.md")
        text = text.format(**kwargs)

    return text
