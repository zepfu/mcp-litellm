"""Custom exceptions for the LiteLLM MCP server."""

from __future__ import annotations


class InvalidMultipartBodyError(TypeError):
    """Raised when a multipart request is given a non-object JSON body."""

    def __init__(self) -> None:
        """Initialize the exception with the standard multipart-body message."""
        super().__init__("Multipart requests require a JSON object body.")


class LiteLLMRequestError(RuntimeError):
    """Raised when an outbound LiteLLM HTTP request fails before a response arrives."""

    def __init__(self, detail: str) -> None:
        """Initialize the exception with the underlying transport detail."""
        super().__init__(f"LiteLLM request failed: {detail}")


class UnknownLiteLLMRouteError(KeyError):
    """Raised when a route key is not present in the vendored LiteLLM spec."""

    def __init__(self, route_key: str) -> None:
        """Initialize the exception for a missing LiteLLM route key."""
        super().__init__(f"Unknown LiteLLM route: {route_key}")


class InvalidToolSpecError(ValueError):
    """Raised when a configured MCP tool points at an invalid LiteLLM route."""

    def __init__(self, detail: str) -> None:
        """Initialize the exception with a tool-spec validation message."""
        super().__init__(detail)


class MissingPathParametersError(ValueError):
    """Raised when a templated LiteLLM path is missing required parameters."""

    def __init__(self, missing_params: list[str]) -> None:
        """Initialize the exception with the unresolved path-parameter names."""
        joined = ", ".join(missing_params)
        super().__init__(f"Missing required path parameters: {joined}")


class RouteNotAllowedError(ValueError):
    """Raised when a route classification is outside an allowed request scope."""

    def __init__(self, route_key: str, classification: str) -> None:
        """Initialize the exception for a disallowed route classification."""
        message = f"Route {route_key} is classified as {classification} and is not allowed here."
        super().__init__(message)


class UnknownToolActionError(ValueError):
    """Raised when a family tool is called with an unsupported action value."""

    def __init__(self, action: str, allowed_actions: list[str]) -> None:
        """Initialize the exception with the unknown action and allowed values."""
        joined = ", ".join(allowed_actions)
        super().__init__(f"Unknown action '{action}'. Allowed actions: {joined}")
