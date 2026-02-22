"""Custom exception hierarchy for FXHoudini-MCP."""

from __future__ import annotations

# Built-in
from typing import Any


class FXHoudiniError(Exception):
    """Base exception for all FXHoudini-MCP errors."""

    def __init__(self, message: str, code: str = "UNKNOWN", details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ConnectionError(FXHoudiniError):
    """Cannot connect to Houdini's hwebserver."""

    def __init__(self, message: str = "Cannot connect to Houdini", details: dict | None = None):
        super().__init__(message, code="CONNECTION_ERROR", details=details)


class NodeNotFoundError(FXHoudiniError):
    """The specified node path does not exist."""

    def __init__(self, node_path: str):
        super().__init__(f"Node not found: {node_path}", code="NODE_NOT_FOUND")


class InvalidParameterError(FXHoudiniError):
    """A parameter name or value is invalid."""

    def __init__(self, message: str):
        super().__init__(message, code="INVALID_PARAMETER")


class GeometryError(FXHoudiniError):
    """Error accessing geometry data."""

    def __init__(self, message: str):
        super().__init__(message, code="GEOMETRY_ERROR")


class USDError(FXHoudiniError):
    """Error in USD stage operations."""

    def __init__(self, message: str):
        super().__init__(message, code="USD_ERROR")


class CookError(FXHoudiniError):
    """Node cooking failed."""

    def __init__(self, message: str):
        super().__init__(message, code="COOK_ERROR")


class TimeoutError(FXHoudiniError):
    """Main thread execution timed out."""

    def __init__(self, message: str = "Operation timed out"):
        super().__init__(message, code="TIMEOUT_ERROR")


class HoudiniCommandError(FXHoudiniError):
    """Error returned from a Houdini command execution."""

    def __init__(self, message: str, code: str = "COMMAND_ERROR", details: dict | None = None):
        super().__init__(message, code=code, details=details)
