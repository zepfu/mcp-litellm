"""Server registration tests for the LiteLLM MCP server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from mcp_litellm.config import Settings
from mcp_litellm.models import MULTIPART_BODY_ERROR
from mcp_litellm.server import build_server


def _write_custom_openapi_spec(tmp_path: Path) -> Path:
    openapi_path = Path("vendor/litellm/openapi.json")
    spec = json.loads(openapi_path.read_text())
    spec["paths"]["/zzz-test-edge"] = {
        "get": {
            "summary": "Edge Route",
            "operationId": "edge_route_get",
            "responses": {"200": {"description": "Successful Response"}},
        }
    }
    custom_openapi_path = tmp_path / "openapi.json"
    custom_openapi_path.write_text(json.dumps(spec))
    return custom_openapi_path


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


def test_server_builds_outside_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    server = build_server(Settings())

    assert server is not None


@pytest.mark.asyncio
async def test_server_registers_resources() -> None:
    server = build_server(Settings())
    resources = await server.list_resources()
    resource_uris = {str(resource.uri) for resource in resources}

    assert "litellm://routes/native" in resource_uris
    assert "litellm://routes/typed" in resource_uris
    assert "litellm://tools/active" in resource_uris


@pytest.mark.asyncio
async def test_server_uses_custom_openapi_path_for_route_listing(tmp_path: Path) -> None:
    custom_openapi_path = _write_custom_openapi_spec(tmp_path)
    server = build_server(Settings(openapi_path=custom_openapi_path))
    _, result = await server.call_tool("litellm_list_routes", {"prefix": "/zzz-test-edge"})
    structured_result = cast("dict[str, Any]", result)

    assert structured_result["count"] == 1
    assert structured_result["routes"][0]["route_key"] == "GET /zzz-test-edge"


@pytest.mark.asyncio
async def test_server_rejects_invalid_multipart_request_before_http() -> None:
    server = build_server(Settings(tool_profiles=("native_escape_hatch",)))

    with pytest.raises(ToolError, match=MULTIPART_BODY_ERROR):
        await server.call_tool(
            "litellm_native_request",
            {
                "route_key": "GET /team/info",
                "body": ["not", "an", "object"],
                "multipart_files": [{"field_name": "file", "path": __file__}],
            },
        )
