"""Custom exceptions for the LiteLLM MCP server."""

from __future__ import annotations

MULTIPART_BODY_ERROR = "Multipart requests require a JSON object body."


class McpLiteLLMError(Exception):
    """Common base class for all LiteLLM MCP server errors."""


class InvalidMultipartBodyError(McpLiteLLMError, ValueError):
    """Raised when a multipart request is given a non-object JSON body."""

    def __init__(self) -> None:
        """Initialize the exception with the standard multipart-body message."""
        super().__init__(MULTIPART_BODY_ERROR)


class LiteLLMRequestError(McpLiteLLMError, RuntimeError):
    """Raised when an outbound LiteLLM HTTP request fails before a response arrives."""

    def __init__(self, detail: str) -> None:
        """Initialize the exception with the underlying transport detail."""
        super().__init__(f"LiteLLM request failed: {detail}")


class LiteLLMResponseTooLargeError(McpLiteLLMError, RuntimeError):
    """Raised when a LiteLLM response body exceeds the configured size limit."""

    def __init__(self, limit_bytes: int) -> None:
        """Initialize the exception with the configured maximum response size."""
        self.limit_bytes = limit_bytes
        super().__init__(f"LiteLLM response exceeded the configured limit of {limit_bytes} bytes.")


class LiteLLMResponseParseError(McpLiteLLMError, RuntimeError):
    """Raised when a LiteLLM response body cannot be parsed as declared."""

    def __init__(self, detail: str) -> None:
        """Initialize the exception with a response-parse failure detail."""
        super().__init__(detail)


class UnknownLiteLLMRouteError(McpLiteLLMError, LookupError):
    """Raised when a route key is not present in the vendored LiteLLM spec."""

    def __init__(self, route_key: str) -> None:
        """Initialize the exception for a missing LiteLLM route key."""
        self.route_key = route_key
        super().__init__(f"Unknown LiteLLM route: {route_key}")


class InvalidToolSpecError(McpLiteLLMError, ValueError):
    """Raised when a configured MCP tool points at an invalid LiteLLM route."""

    def __init__(self, detail: str) -> None:
        """Initialize the exception with a tool-spec validation message."""
        super().__init__(detail)


class MissingPathParametersError(McpLiteLLMError, ValueError):
    """Raised when a templated LiteLLM path is missing required parameters."""

    def __init__(self, missing_params: list[str]) -> None:
        """Initialize the exception with the unresolved path-parameter names."""
        self.missing_params = missing_params
        joined = ", ".join(missing_params)
        super().__init__(f"Missing required path parameters: {joined}")


class InvalidPathParameterError(McpLiteLLMError, ValueError):
    """Raised when a path parameter value is missing, empty, or wrongly typed."""

    def __init__(self, detail: str) -> None:
        """Initialize the exception with a path-parameter validation detail."""
        super().__init__(detail)


class RouteNotAllowedError(McpLiteLLMError, ValueError):
    """Raised when a route classification is outside an allowed request scope."""

    def __init__(self, route_key: str, classification: str) -> None:
        """Initialize the exception for a disallowed route classification."""
        self.route_key = route_key
        self.classification = classification
        message = f"Route {route_key} is classified as {classification} and is not allowed here."
        super().__init__(message)


class UnknownToolActionError(McpLiteLLMError, ValueError):
    """Raised when a family tool is called with an unsupported action value."""

    def __init__(self, action: str, allowed_actions: list[str]) -> None:
        """Initialize the exception with the unknown action and allowed values."""
        self.action = action
        self.allowed_actions = allowed_actions
        joined = ", ".join(allowed_actions)
        super().__init__(f"Unknown action '{action}'. Allowed actions: {joined}")


class LocalFileUploadNotAllowedError(McpLiteLLMError, PermissionError):
    """Raised when a multipart upload is attempted but local uploads are disabled."""

    def __init__(self) -> None:
        """Initialize the exception with the local-upload denial message."""
        super().__init__("Local file uploads are disabled for this server instance.")
