"""Shared fixtures for fxhoudinimcp tests."""

from __future__ import annotations

# Built-in
import sys
from unittest.mock import AsyncMock, MagicMock

# Third-party
import pytest


@pytest.fixture
def mock_bridge():
    """A mocked HoudiniBridge whose execute() returns a success dict."""
    bridge = AsyncMock()
    bridge.execute = AsyncMock(return_value={"executed": True})
    bridge.health_check = AsyncMock(return_value={"status": "ok", "houdini_version": "21.0.440"})
    return bridge


@pytest.fixture
def mock_ctx(mock_bridge):
    """A mocked MCP Context wired to mock_bridge."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {"bridge": mock_bridge}
    return ctx
