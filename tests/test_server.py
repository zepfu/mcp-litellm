"""Server registration tests for the LiteLLM MCP server."""

from __future__ import annotations

import pytest

from mcp_litellm.config import Settings
from mcp_litellm.server import build_server


@pytest.mark.asyncio
async def test_server_registers_default_compact_toolset() -> None:
    server = build_server(Settings())
    tools = await server.list_tools()
    tool_names = {tool.name for tool in tools}

    assert "litellm_models_catalog" in tool_names
    assert "litellm_keys" in tool_names
    assert "litellm_teams" in tool_names
    assert "litellm_runtime" in tool_names
    assert "litellm_list_routes" in tool_names
    assert "litellm_route_details" in tool_names
    assert "litellm_native_request" not in tool_names
    assert "litellm_governance" not in tool_names


@pytest.mark.asyncio
async def test_server_registers_full_profile_toolset() -> None:
    server = build_server(Settings(tool_profiles=("full",)))
    tools = await server.list_tools()
    tool_names = {tool.name for tool in tools}

    assert "litellm_governance" in tool_names
    assert "litellm_native_request" in tool_names
    assert "litellm_exports_audit" in tool_names


@pytest.mark.asyncio
async def test_explicit_tool_overrides_apply_after_profiles() -> None:
    server = build_server(
        Settings(
            tool_profiles=("discovery",),
            enable_tools=("litellm_governance",),
            disable_tools=("litellm_route_details",),
        )
    )
    tools = await server.list_tools()
    tool_names = {tool.name for tool in tools}

    assert tool_names == {"litellm_governance", "litellm_list_routes"}


def test_invalid_tool_profile_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown tool profile"):
        build_server(Settings(tool_profiles=("not-a-profile",)))


def test_invalid_tool_name_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown tool name"):
        build_server(Settings(enable_tools=("not-a-tool",)))


@pytest.mark.asyncio
async def test_server_registers_resources() -> None:
    server = build_server(Settings())
    resources = await server.list_resources()
    resource_uris = {str(resource.uri) for resource in resources}

    assert "litellm://routes/native" in resource_uris
    assert "litellm://routes/typed" in resource_uris
    assert "litellm://tools/active" in resource_uris
