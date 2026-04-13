"""Service-layer tests for the LiteLLM MCP server."""

from __future__ import annotations

from mcp_litellm.service import LiteLLMToolService


def test_render_path_url_encodes_path_parameters() -> None:
    rendered_path = LiteLLMToolService._render_path(
        "/search/{search_tool_name}",
        {"search_tool_name": "foo/bar baz"},
    )

    assert rendered_path == "/search/foo%2Fbar%20baz"
