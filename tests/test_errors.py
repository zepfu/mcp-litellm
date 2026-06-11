"""Unit tests for errors.py — custom exception hierarchy and messages."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# §3.2 common base class
# ---------------------------------------------------------------------------


def test_all_errors_subclass_common_base() -> None:
    """Every custom error class must subclass McpLiteLLMError."""
    from mcp_litellm.errors import (  # type: ignore[attr-defined]
        InvalidMultipartBodyError,
        InvalidPathParameterError,
        InvalidToolSpecError,
        LiteLLMRequestError,
        LiteLLMResponseParseError,
        LiteLLMResponseTooLargeError,
        LocalFileUploadNotAllowedError,
        McpLiteLLMError,
        MissingPathParametersError,
        RouteNotAllowedError,
        UnknownLiteLLMRouteError,
        UnknownToolActionError,
    )

    error_classes = [
        InvalidMultipartBodyError,
        InvalidPathParameterError,
        InvalidToolSpecError,
        LiteLLMRequestError,
        LiteLLMResponseParseError,
        LiteLLMResponseTooLargeError,
        LocalFileUploadNotAllowedError,
        MissingPathParametersError,
        RouteNotAllowedError,
        UnknownLiteLLMRouteError,
        UnknownToolActionError,
    ]
    for cls in error_classes:
        assert issubclass(cls, McpLiteLLMError), f"{cls.__name__} must subclass McpLiteLLMError"


# ---------------------------------------------------------------------------
# §3.1 KeyError quoting bug fix
# ---------------------------------------------------------------------------


def test_unknown_route_error_message_not_quoted() -> None:
    """UnknownLiteLLMRouteError str must not have surrounding single quotes."""
    from mcp_litellm.errors import UnknownLiteLLMRouteError

    err = UnknownLiteLLMRouteError("GET /x")
    assert str(err) == "Unknown LiteLLM route: GET /x"


def test_unknown_route_error_is_not_key_error() -> None:
    """UnknownLiteLLMRouteError must NOT be a KeyError (was the old base)."""
    from mcp_litellm.errors import UnknownLiteLLMRouteError

    err = UnknownLiteLLMRouteError("GET /x")
    assert not isinstance(err, KeyError)


# ---------------------------------------------------------------------------
# §3.3 retained structured fields
# ---------------------------------------------------------------------------


def test_errors_retain_structured_fields() -> None:
    """Structured fields on error classes must be preserved."""
    from mcp_litellm.errors import (
        MissingPathParametersError,
        RouteNotAllowedError,
        UnknownToolActionError,
    )

    missing = MissingPathParametersError(["a", "b"])
    assert missing.missing_params == ["a", "b"]  # type: ignore[attr-defined]

    route_denied = RouteNotAllowedError("GET /x", "alias")
    assert route_denied.route_key == "GET /x"  # type: ignore[attr-defined]
    assert route_denied.classification == "alias"  # type: ignore[attr-defined]

    unknown_action = UnknownToolActionError("z", ["a"])
    assert unknown_action.action == "z"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# §2.1 shared multipart constant
# ---------------------------------------------------------------------------


def test_multipart_body_error_uses_shared_constant() -> None:
    """str(InvalidMultipartBodyError()) must equal MULTIPART_BODY_ERROR constant."""
    from mcp_litellm.errors import MULTIPART_BODY_ERROR, InvalidMultipartBodyError  # type: ignore[attr-defined]

    err = InvalidMultipartBodyError()
    assert str(err) == MULTIPART_BODY_ERROR
    assert isinstance(err, ValueError)
