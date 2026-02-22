"""Tests for custom exception hierarchy."""

from __future__ import annotations

# Third-party
import pytest

# Internal
from fxhoudinimcp.errors import (
    ConnectionError,
    CookError,
    FXHoudiniError,
    GeometryError,
    HoudiniCommandError,
    InvalidParameterError,
    NodeNotFoundError,
    TimeoutError,
    USDError,
)


class TestFXHoudiniError:
    def test_base_error(self):
        e = FXHoudiniError("something broke", code="TEST", details={"a": 1})
        assert str(e) == "something broke"
        assert e.code == "TEST"
        assert e.details == {"a": 1}

    def test_defaults(self):
        e = FXHoudiniError("msg")
        assert e.code == "UNKNOWN"
        assert e.details == {}


class TestConnectionError:
    def test_default_message(self):
        e = ConnectionError()
        assert "Cannot connect" in str(e)
        assert e.code == "CONNECTION_ERROR"

    def test_custom_message(self):
        e = ConnectionError("custom", details={"url": "http://x"})
        assert str(e) == "custom"
        assert e.details["url"] == "http://x"

    def test_is_subclass(self):
        assert issubclass(ConnectionError, FXHoudiniError)


class TestNodeNotFoundError:
    def test_formats_path(self):
        e = NodeNotFoundError("/obj/geo1")
        assert "/obj/geo1" in str(e)
        assert e.code == "NODE_NOT_FOUND"

    def test_is_subclass(self):
        assert issubclass(NodeNotFoundError, FXHoudiniError)


class TestOtherErrors:
    @pytest.mark.parametrize(
        "cls,code",
        [
            (InvalidParameterError, "INVALID_PARAMETER"),
            (GeometryError, "GEOMETRY_ERROR"),
            (USDError, "USD_ERROR"),
            (CookError, "COOK_ERROR"),
            (TimeoutError, "TIMEOUT_ERROR"),
        ],
    )
    def test_error_code(self, cls, code):
        e = cls("test message")
        assert e.code == code
        assert str(e) == "test message"
        assert isinstance(e, FXHoudiniError)


class TestHoudiniCommandError:
    def test_with_custom_code_and_details(self):
        e = HoudiniCommandError("failed", code="MY_CODE", details={"tb": "..."})
        assert str(e) == "failed"
        assert e.code == "MY_CODE"
        assert e.details["tb"] == "..."

    def test_defaults(self):
        e = HoudiniCommandError("msg")
        assert e.code == "COMMAND_ERROR"
        assert e.details == {}
