"""Server registration tests for the LiteLLM MCP server."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

import pytest
import respx
from httpx import Response
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


async def test_server_registers_full_profile_toolset() -> None:
    server = build_server(Settings(tool_profiles=("full",)))
    tools = await server.list_tools()
    tool_names = {tool.name for tool in tools}

    assert "litellm_governance" in tool_names
    assert "litellm_native_request" in tool_names
    assert "litellm_exports_audit" in tool_names


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


async def test_server_registers_resources() -> None:
    server = build_server(Settings())
    resources = await server.list_resources()
    resource_uris = {str(resource.uri) for resource in resources}

    assert "litellm://routes/native" in resource_uris
    assert "litellm://routes/typed" in resource_uris
    assert "litellm://tools/active" in resource_uris


async def test_server_uses_custom_openapi_path_for_route_listing(tmp_path: Path) -> None:
    custom_openapi_path = _write_custom_openapi_spec(tmp_path)
    server = build_server(Settings(openapi_path=custom_openapi_path))
    _, result = await server.call_tool("litellm_list_routes", {"prefix": "/zzz-test-edge"})
    structured_result = cast("dict[str, Any]", result)

    assert structured_result["count"] == 1
    assert structured_result["routes"][0]["route_key"] == "GET /zzz-test-edge"


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


# ---------------------------------------------------------------------------
# §7.3 native_request denies disabled-family routes
# ---------------------------------------------------------------------------


async def test_native_request_denies_disabled_family_routes() -> None:
    """native_request must raise ToolError for a route in a disabled family.

    Profile full + disable litellm_config_admin: the config_admin route
    GET /config/cost_discount_config must be denied, while a still-enabled
    typed route (e.g. GET /team/info) must be allowed through.
    """
    server = build_server(
        Settings(
            tool_profiles=("full",),
            disable_tools=("litellm_config_admin",),
        )
    )

    # Config admin route (disabled family) must be denied
    with pytest.raises(ToolError):
        await server.call_tool(
            "litellm_native_request",
            {"route_key": "GET /config/cost_discount_config"},
        )

    # ALLOW side: a route owned by a STILL-ACTIVE family (litellm_keys) that is
    # NOT denied must reach the client. This guards against a deny-everything
    # regression silently passing the deny-side assertion above.
    with respx.mock(assert_all_called=False) as router:
        router.get("http://127.0.0.1:4000/key/info").mock(return_value=Response(200, json={}))
        _, result = await server.call_tool(
            "litellm_native_request",
            {"route_key": "GET /key/info"},
        )

    structured_result = cast("dict[str, Any]", result)
    assert structured_result["ok"] is True


# ---------------------------------------------------------------------------
# §7.5 family tool action param has enum in inputSchema
# ---------------------------------------------------------------------------


async def test_family_tool_action_param_has_enum() -> None:
    """litellm_keys inputSchema must have action.enum equal to sorted action names."""
    from mcp_litellm.tool_definitions import FAMILY_TOOL_SPECS_BY_NAME

    server = build_server(Settings())
    tools = await server.list_tools()
    keys_tool = next(t for t in tools if t.name == "litellm_keys")
    schema = keys_tool.inputSchema

    assert "properties" in schema
    action_schema = schema["properties"]["action"]
    assert "enum" in action_schema

    expected_actions = sorted(FAMILY_TOOL_SPECS_BY_NAME["litellm_keys"].actions)
    assert action_schema["enum"] == expected_actions


# ---------------------------------------------------------------------------
# §7.1 _resolve_settings validates overrides
# ---------------------------------------------------------------------------


def test_resolve_settings_validates_overrides() -> None:
    """_resolve_settings with port=70000 must raise ValidationError (not silently accept)."""
    from pydantic import ValidationError

    from mcp_litellm.server import _resolve_settings

    base = Settings()
    args = argparse.Namespace(port=70000, host=None, transport=None, tool_profile=None, enable_tool=None, disable_tool=None)
    with pytest.raises(ValidationError):
        _resolve_settings(base, args)


# ---------------------------------------------------------------------------
# §2.3 transport-gated local file uploads
# ---------------------------------------------------------------------------


def test_resolve_allow_local_file_uploads_gated_by_transport() -> None:
    """Local file uploads default off on network transports unless opted in.

    Over network transports (streamable-http) uploads are unsafe by default, so
    the resolver returns False when the operator did not explicitly opt in. An
    explicit allow_local_file_uploads=True survives, and stdio (trusted local
    operator) keeps the default of True.
    """
    from mcp_litellm.server import _resolve_allow_local_file_uploads

    # Network transport, no explicit opt-in -> gated off.
    assert _resolve_allow_local_file_uploads(Settings(transport="streamable-http")) is False
    # Network transport, explicit opt-in -> honoured.
    assert _resolve_allow_local_file_uploads(Settings(transport="streamable-http", allow_local_file_uploads=True)) is True
    # stdio (trusted local) -> default True preserved.
    assert _resolve_allow_local_file_uploads(Settings(transport="stdio")) is True


# ---------------------------------------------------------------------------
# §7.2 main() with unknown profile exits cleanly (SystemExit, not ValueError)
# ---------------------------------------------------------------------------


def test_main_unknown_profile_exits_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() with --tool-profile bogus must raise SystemExit(2), not a raw ValueError."""
    import mcp_litellm.server as server_module

    monkeypatch.setattr(sys, "argv", ["mcp-litellm", "--tool-profile", "bogus"])

    with pytest.raises(SystemExit) as exc_info:
        server_module.main()

    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# §4.1 lifespan closes the LiteLLMClient
# ---------------------------------------------------------------------------


async def test_lifespan_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entering and exiting the server lifespan must call LiteLLMClient.aclose once."""
    from mcp_litellm.client import LiteLLMClient

    close_calls: list[None] = []

    original_aclose = LiteLLMClient.aclose if hasattr(LiteLLMClient, "aclose") else None

    async def spy_aclose(self: LiteLLMClient) -> None:
        close_calls.append(None)
        if original_aclose is not None:
            await original_aclose(self)

    monkeypatch.setattr(LiteLLMClient, "aclose", spy_aclose)

    server = build_server(Settings())
    # Trigger the lifespan by using the server as an async context manager
    async with server.lifespan(server):  # type: ignore[attr-defined]
        pass

    assert len(close_calls) == 1


# ---------------------------------------------------------------------------
# §8.2 every action name appears in its ToolSpec description
# ---------------------------------------------------------------------------


def test_every_action_name_appears_in_description() -> None:
    """For every ToolSpec, each action key must be a substring of tool_spec.description."""
    from mcp_litellm.tool_definitions import TOOL_SPECS

    for tool_spec in TOOL_SPECS:
        for action_name in tool_spec.actions:
            assert action_name in tool_spec.description, f"Action '{action_name}' not found in {tool_spec.name}.description"


# ---------------------------------------------------------------------------
# §8.3 tool_spec.actions is a read-only Mapping
# ---------------------------------------------------------------------------


def test_tool_spec_actions_is_read_only_mapping() -> None:
    """tool_spec.actions must reject item assignment (TypeError, not silent accept)."""
    from mcp_litellm.tool_definitions import TOOL_SPECS

    tool_spec = TOOL_SPECS[0]
    with pytest.raises(TypeError):
        tool_spec.actions["__injected__"] = None  # type: ignore[index]


# ---------------------------------------------------------------------------
# §8.4 TOOL_PROFILES keys match profile names
# ---------------------------------------------------------------------------


def test_tool_profiles_keys_match_names() -> None:
    """Every TOOL_PROFILES key must equal its ToolProfile.name."""
    from mcp_litellm.tool_definitions import TOOL_PROFILES

    assert all(k == v.name for k, v in TOOL_PROFILES.items())
