"""JSON protocol definitions for communication between MCP server and Houdini plugin."""

from __future__ import annotations

# Built-in
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Request:
    """A request to execute a command in Houdini."""

    command: str
    params: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "params": self.params,
            "request_id": self.request_id,
        }


@dataclass
class Response:
    """A response from Houdini after executing a command."""

    status: str  # "success" or "error"
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    request_id: str = ""
    timing_ms: float = 0.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Response:
        return cls(
            status=d.get("status", "error"),
            data=d.get("data"),
            error=d.get("error"),
            request_id=d.get("request_id", ""),
            timing_ms=d.get("timing_ms", 0.0),
        )

    @property
    def is_success(self) -> bool:
        return self.status == "success"


# Error codes used across the protocol
class ErrorCode:
    NODE_NOT_FOUND = "NODE_NOT_FOUND"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    GEOMETRY_ERROR = "GEOMETRY_ERROR"
    USD_ERROR = "USD_ERROR"
    COOK_ERROR = "COOK_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    UNKNOWN_COMMAND = "UNKNOWN_COMMAND"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    DISPATCH_ERROR = "DISPATCH_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
