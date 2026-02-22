"""Tests for protocol dataclasses."""

from __future__ import annotations

# Internal
from fxhoudinimcp.protocol import ErrorCode, Request, Response


class TestRequest:
    def test_default_fields(self):
        r = Request(command="scene.get_info")
        assert r.command == "scene.get_info"
        assert r.params == {}
        assert isinstance(r.request_id, str)
        assert len(r.request_id) > 0

    def test_to_dict(self):
        r = Request(command="nodes.create", params={"type": "box"}, request_id="abc-123")
        d = r.to_dict()
        assert d == {
            "command": "nodes.create",
            "params": {"type": "box"},
            "request_id": "abc-123",
        }

    def test_auto_generated_request_id_unique(self):
        r1 = Request(command="a")
        r2 = Request(command="b")
        assert r1.request_id != r2.request_id


class TestResponse:
    def test_from_dict_success(self):
        d = {"status": "success", "data": {"key": "val"}, "timing_ms": 5.2, "request_id": "x"}
        resp = Response.from_dict(d)
        assert resp.status == "success"
        assert resp.data == {"key": "val"}
        assert resp.timing_ms == 5.2
        assert resp.request_id == "x"
        assert resp.is_success is True

    def test_from_dict_error(self):
        d = {"status": "error", "error": {"code": "COOK_ERROR", "message": "failed"}}
        resp = Response.from_dict(d)
        assert resp.status == "error"
        assert resp.is_success is False
        assert resp.error["code"] == "COOK_ERROR"

    def test_from_dict_missing_fields(self):
        resp = Response.from_dict({})
        assert resp.status == "error"
        assert resp.data is None
        assert resp.error is None
        assert resp.request_id == ""
        assert resp.timing_ms == 0.0

    def test_is_success_property(self):
        assert Response(status="success").is_success is True
        assert Response(status="error").is_success is False
        assert Response(status="other").is_success is False


class TestErrorCode:
    def test_all_constants_are_strings(self):
        for name in dir(ErrorCode):
            if name.isupper():
                assert isinstance(getattr(ErrorCode, name), str)

    def test_expected_codes_exist(self):
        assert ErrorCode.NODE_NOT_FOUND == "NODE_NOT_FOUND"
        assert ErrorCode.TIMEOUT_ERROR == "TIMEOUT_ERROR"
        assert ErrorCode.UNKNOWN_COMMAND == "UNKNOWN_COMMAND"
        assert ErrorCode.CONNECTION_ERROR == "CONNECTION_ERROR"
