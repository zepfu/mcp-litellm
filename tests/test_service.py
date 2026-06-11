"""Service-layer tests for the LiteLLM MCP server."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from mcp_litellm.errors import RouteNotAllowedError
from mcp_litellm.route_catalog import RouteInfo
from mcp_litellm.service import LiteLLMToolService


def test_render_path_url_encodes_path_parameters() -> None:
    rendered_path = LiteLLMToolService._render_path(
        "/search/{search_tool_name}",
        {"search_tool_name": "foo/bar baz"},
    )

    assert rendered_path == "/search/foo%2Fbar%20baz"


# ---------------------------------------------------------------------------
# §6.1 empty path param value rejected
# ---------------------------------------------------------------------------


def test_render_path_rejects_empty_value() -> None:
    """_render_path must raise when a path param value is empty or whitespace."""
    from mcp_litellm.errors import InvalidPathParameterError

    with pytest.raises((InvalidPathParameterError, ValueError)):
        LiteLLMToolService._render_path("/key/{k}", {"k": ""})


# ---------------------------------------------------------------------------
# §6.2 surplus keys rejected
# ---------------------------------------------------------------------------


def test_render_path_rejects_surplus_keys() -> None:
    """_render_path must raise InvalidPathParameterError for extra keys not in the template."""
    from mcp_litellm.errors import InvalidPathParameterError

    with pytest.raises(InvalidPathParameterError):
        LiteLLMToolService._render_path("/key/{k}", {"k": "a", "extra": "b"})


# ---------------------------------------------------------------------------
# §6.1 / regression guard: encoding still works
# ---------------------------------------------------------------------------


def test_render_path_still_encodes() -> None:
    """URL-encoding regression guard — must still encode slashes and spaces."""
    rendered_path = LiteLLMToolService._render_path(
        "/search/{search_tool_name}",
        {"search_tool_name": "foo/bar baz"},
    )
    assert rendered_path == "/search/foo%2Fbar%20baz"


# ---------------------------------------------------------------------------
# §7.3 denied_route_keys prevents execution
# ---------------------------------------------------------------------------


async def test_denied_route_key_rejected() -> None:
    """execute_route_key with a denied route key must raise RouteNotAllowedError before HTTP."""
    # Build a minimal stub route catalog with one typed route
    stub_catalog: dict[str, RouteInfo] = {
        "GET /x": RouteInfo(
            key="GET /x",
            method="GET",
            path="/x",
            summary="Test route",
            operation_id=None,
            tags=(),
            classification="typed",
        )
    }

    # Fake client whose request must NOT be called if denial fires first
    fake_client = AsyncMock()
    fake_client.request = AsyncMock(return_value={"ok": True, "status_code": 200})

    service = LiteLLMToolService(fake_client, route_catalog=stub_catalog)

    with pytest.raises(RouteNotAllowedError):
        await service.execute_route_key(
            "GET /x",
            allowed_classifications={"typed"},
            denied_route_keys={"GET /x"},
        )

    # The HTTP request must NOT have been made
    fake_client.request.assert_not_called()
