"""FastMCP server wiring for the LiteLLM native API tool surface."""

from __future__ import annotations

import argparse
import json
import sys
import typing
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

import pydantic
from mcp.server import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from mcp_litellm._parsing import split_csv
from mcp_litellm.client import LiteLLMClient
from mcp_litellm.config import Settings, get_settings
from mcp_litellm.errors import InvalidToolSpecError, McpLiteLLMError
from mcp_litellm.models import JsonValue, LiteLLMResponse, MultipartFileSpec, RequestOptions
from mcp_litellm.route_catalog import (
    RouteClassification,
    build_route_catalog,
    get_route,
    list_routes,
)
from mcp_litellm.service import LiteLLMToolService
from mcp_litellm.tool_definitions import (
    TOOL_SPECS,
    ToolSpec,
    list_tool_profiles,
    resolve_enabled_tool_names,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Mapping

    from mcp_litellm.route_catalog import RouteInfo

RouteParams = Annotated[
    dict[str, str] | None,
    Field(default=None, description="Path template values, for example {'team_id': 'team-123'}."),
]
QueryParams = Annotated[
    dict[str, Any] | None,
    Field(default=None, description="Query string parameters to send to LiteLLM."),
]
RequestBody = Annotated[
    JsonValue,
    Field(
        default=None,
        description="JSON request body. For multipart requests this must be an object.",
    ),
]
MultipartFiles = Annotated[
    list[MultipartFileSpec] | None,
    Field(
        default=None,
        description=(
            "Optional local file uploads. Each item requires 'field_name' and 'path'. Optional keys: 'filename', 'content_type'."
        ),
    ),
]


def _build_request_options(
    *,
    path_params: RouteParams = None,
    query: QueryParams = None,
    body: RequestBody = None,
    multipart_files: MultipartFiles = None,
) -> RequestOptions:
    return RequestOptions.model_validate(
        {
            "path_params": path_params,
            "query": query,
            "body": body,
            "multipart_files": multipart_files,
        }
    )


def _validate_tool_specs(catalog: Mapping[str, RouteInfo]) -> None:
    for tool_spec in TOOL_SPECS:
        for action, action_spec in tool_spec.actions.items():
            route = catalog.get(action_spec.route_key)
            if route is None:
                detail = f"{tool_spec.name}:{action} references unknown route {action_spec.route_key}"
                raise InvalidToolSpecError(detail)
            if route.classification != "typed":
                detail = (
                    f"{tool_spec.name}:{action} references {action_spec.route_key}, "
                    f"which is classified as {route.classification} instead of typed"
                )
                raise InvalidToolSpecError(detail)


def _make_family_tool(
    service: LiteLLMToolService,
    tool_spec: ToolSpec,
) -> Callable[..., Any]:
    async def tool(
        action: str,
        path_params: RouteParams = None,
        query: QueryParams = None,
        body: RequestBody = None,
        multipart_files: MultipartFiles = None,
    ) -> LiteLLMResponse:
        try:
            options = _build_request_options(
                path_params=path_params,
                query=query,
                body=body,
                multipart_files=multipart_files,
            )
            return await service.execute_action(
                action,
                tool_spec.actions,
                options=options,
            )
        except (McpLiteLLMError, pydantic.ValidationError) as exc:
            raise ToolError(str(exc)) from exc

    tool.__name__ = tool_spec.name
    # A Literal of the sorted action names surfaces as an `enum` in the
    # generated MCP input schema (verified against FastMCP schema generation).
    tool.__annotations__["action"] = typing.Literal.__getitem__(tuple(sorted(tool_spec.actions)))
    return tool


def _routes_as_markdown(
    classifications: set[RouteClassification],
    *,
    catalog: Mapping[str, RouteInfo],
) -> str:
    lines = ["# LiteLLM Routes", ""]
    for route in list_routes(classifications=classifications, catalog=catalog):
        tags = ", ".join(route.tags)
        summary = route.summary or "-"
        lines.append(f"- `{route.key}` [{route.classification}] {summary} | tags: {tags}")
    return "\n".join(lines)


def _parse_name_args(values: list[str] | None) -> tuple[str, ...] | None:
    if values is None:
        return None
    parsed_values: list[str] = []
    for value in values:
        parsed_values.extend(split_csv(value))
    return tuple(parsed_values)


def _build_server_instructions(active_tool_names: set[str]) -> str:
    instructions = (
        "Use these tools to work with LiteLLM's native API surface. "
        "This server instance may expose only a filtered subset of the full tool catalog."
    )
    if "litellm_native_request" in active_tool_names:
        instructions += (
            " Prefer the family tools first; use litellm_native_request only for "
            "allowlisted native routes that do not yet have a first-class action."
        )
    return instructions


@dataclass(frozen=True, slots=True)
class _ActiveToolset:
    """Resolved active-tool selection shared across server wiring helpers."""

    active_tool_names: frozenset[str]
    active_family_tool_specs: tuple[ToolSpec, ...]
    standalone_tool_names: tuple[str, ...]


def _build_active_toolset_payload(
    settings: Settings,
    *,
    toolset: _ActiveToolset,
) -> dict[str, Any]:
    return {
        "tool_profiles": list(settings.tool_profiles),
        "enable_tools": list(settings.enable_tools),
        "disable_tools": list(settings.disable_tools),
        "active_tools": sorted(toolset.active_tool_names),
        "family_tools": [tool_spec.name for tool_spec in toolset.active_family_tool_specs],
        "standalone_tools": list(toolset.standalone_tool_names),
        "available_profiles": {
            profile.name: {
                "description": profile.description,
                "tools": sorted(profile.tools),
            }
            for profile in list_tool_profiles()
        },
    }


def _compute_denied_route_keys(active_tool_names: set[str]) -> set[str]:
    """Route keys owned only by disabled family tools (escape-hatch denylist).

    A typed route owned by both a disabled and a still-active family is NOT
    denied: the active family legitimately exposes it.
    """
    disabled_route_keys: set[str] = set()
    active_route_keys: set[str] = set()
    for tool_spec in TOOL_SPECS:
        route_keys = {action_spec.route_key for action_spec in tool_spec.actions.values()}
        if tool_spec.name in active_tool_names:
            active_route_keys |= route_keys
        else:
            disabled_route_keys |= route_keys
    return disabled_route_keys - active_route_keys


def _register_list_routes_tool(server: FastMCP, *, catalog: Mapping[str, RouteInfo]) -> None:
    @server.tool(
        name="litellm_list_routes",
        description=("List LiteLLM routes known to this server. Use this to discover route keys for litellm_native_request."),
        structured_output=True,
    )
    def list_known_routes(
        classification: Annotated[
            RouteClassification | None,
            Field(
                default=None,
                description=(
                    "Optional classification filter: typed, generic_native, alias, excluded_pass_through, or excluded_protocol."
                ),
            ),
        ] = None,
        prefix: Annotated[
            str | None,
            Field(
                default=None,
                description="Optional path prefix filter, for example /team or /guardrails.",
            ),
        ] = None,
    ) -> dict[str, Any]:
        routes = list_routes(
            classifications={classification} if classification else None,
            catalog=catalog,
        )
        if prefix:
            routes = [route for route in routes if route.path.startswith(prefix)]
        return {
            "count": len(routes),
            "routes": [
                {
                    "route_key": route.key,
                    "method": route.method,
                    "path": route.path,
                    "summary": route.summary,
                    "classification": route.classification,
                    "tags": route.tags,
                }
                for route in routes
            ],
        }


def _register_native_request_tool(
    server: FastMCP,
    service: LiteLLMToolService,
    *,
    denied_route_keys: set[str],
) -> None:
    @server.tool(
        name="litellm_native_request",
        description=(
            "Call any allowlisted LiteLLM-native route directly by route key. "
            "Excluded route classes are raw provider pass-through and protocol-only endpoints."
        ),
        structured_output=True,
    )
    async def native_request(
        route_key: Annotated[
            str,
            Field(description="Exact route key in the form 'METHOD /path', for example 'GET /team/info'."),
        ],
        path_params: RouteParams = None,
        query: QueryParams = None,
        body: RequestBody = None,
        multipart_files: MultipartFiles = None,
    ) -> LiteLLMResponse:
        try:
            options = _build_request_options(
                path_params=path_params,
                query=query,
                body=body,
                multipart_files=multipart_files,
            )
            return await service.execute_route_key(
                route_key,
                allowed_classifications={"typed", "generic_native"},
                denied_route_keys=denied_route_keys,
                options=options,
            )
        except (McpLiteLLMError, pydantic.ValidationError) as exc:
            raise ToolError(str(exc)) from exc


def _register_route_details_tool(server: FastMCP, *, catalog: Mapping[str, RouteInfo]) -> None:
    @server.tool(
        name="litellm_route_details",
        description="Return classification and metadata for a single LiteLLM route key.",
        structured_output=True,
    )
    def route_details(
        route_key: Annotated[
            str,
            Field(description="Exact route key in the form 'METHOD /path'."),
        ],
    ) -> dict[str, Any]:
        try:
            route = get_route(route_key, catalog=catalog)
        except McpLiteLLMError as exc:
            raise ToolError(str(exc)) from exc
        return {
            "route_key": route.key,
            "method": route.method,
            "path": route.path,
            "summary": route.summary,
            "tags": route.tags,
            "classification": route.classification,
            "operation_id": route.operation_id,
        }


def _register_resources(
    server: FastMCP,
    *,
    catalog: Mapping[str, RouteInfo],
    settings: Settings,
    toolset: _ActiveToolset,
) -> None:
    @server.resource(
        "litellm://routes/typed",
        name="LiteLLM typed routes",
        description="Typed LiteLLM-native routes promoted into first-class MCP tools.",
        mime_type="text/markdown",
    )
    def typed_routes_resource() -> str:
        return _routes_as_markdown({"typed"}, catalog=catalog)

    @server.resource(
        "litellm://routes/native",
        name="LiteLLM native routes",
        description="All callable LiteLLM-native routes, excluding pass-through and protocol-only endpoints.",
        mime_type="text/markdown",
    )
    def native_routes_resource() -> str:
        return _routes_as_markdown({"typed", "generic_native"}, catalog=catalog)

    @server.resource(
        "litellm://tools/actions",
        name="LiteLLM tool actions",
        description="Curated family-tool action catalog for the currently enabled toolset.",
        mime_type="application/json",
    )
    def tool_actions_resource() -> str:
        payload = {
            tool_spec.name: {
                "description": tool_spec.description,
                "actions": sorted(tool_spec.actions),
            }
            for tool_spec in toolset.active_family_tool_specs
        }
        return json.dumps(payload, indent=2, sort_keys=True)

    @server.resource(
        "litellm://tools/active",
        name="LiteLLM active toolset",
        description="Resolved tool profiles and the active MCP tools exposed by this server instance.",
        mime_type="application/json",
    )
    def active_toolset_resource() -> str:
        payload = _build_active_toolset_payload(settings, toolset=toolset)
        return json.dumps(payload, indent=2, sort_keys=True)


def _resolve_allow_local_file_uploads(settings: Settings) -> bool:
    # Local file uploads are only safe over stdio (a trusted local operator).
    # Over network transports, default to disabled unless the operator opted in.
    if settings.transport != "stdio" and "allow_local_file_uploads" not in settings.model_fields_set:
        return False
    return settings.allow_local_file_uploads


def build_server(settings: Settings | None = None) -> FastMCP:
    """Build and return the configured FastMCP server instance."""
    resolved_settings = settings or get_settings()
    if _resolve_allow_local_file_uploads(resolved_settings) != resolved_settings.allow_local_file_uploads:
        resolved_settings = resolved_settings.model_copy(update={"allow_local_file_uploads": False})
    route_catalog = build_route_catalog(resolved_settings.resolved_openapi_path)
    _validate_tool_specs(route_catalog)

    client = LiteLLMClient(resolved_settings)
    service = LiteLLMToolService(client, route_catalog=route_catalog)
    active_tool_names = set(
        resolve_enabled_tool_names(
            profile_names=resolved_settings.tool_profiles,
            enable_tools=resolved_settings.enable_tools,
            disable_tools=resolved_settings.disable_tools,
        )
    )
    active_family_tool_specs = tuple(tool_spec for tool_spec in TOOL_SPECS if tool_spec.name in active_tool_names)
    active_family_tool_names = {tool_spec.name for tool_spec in active_family_tool_specs}
    standalone_tool_names = tuple(sorted(name for name in active_tool_names if name not in active_family_tool_names))
    denied_route_keys = _compute_denied_route_keys(active_tool_names)
    toolset = _ActiveToolset(
        active_tool_names=frozenset(active_tool_names),
        active_family_tool_specs=active_family_tool_specs,
        standalone_tool_names=standalone_tool_names,
    )

    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await client.aclose()

    server = FastMCP(
        name="mcp-litellm",
        instructions=_build_server_instructions(active_tool_names),
        host=resolved_settings.host,
        port=resolved_settings.port,
        mount_path=resolved_settings.mount_path,
        sse_path=resolved_settings.sse_path,
        message_path=resolved_settings.message_path,
        streamable_http_path=resolved_settings.streamable_http_path,
        lifespan=lifespan,
    )
    # Expose the lifespan factory on the instance so shutdown can be exercised
    # directly (FastMCP only stores it internally on settings otherwise).
    server.lifespan = lifespan  # type: ignore[attr-defined]

    _register_resources(
        server,
        catalog=route_catalog,
        settings=resolved_settings,
        toolset=toolset,
    )

    if "litellm_list_routes" in active_tool_names:
        _register_list_routes_tool(server, catalog=route_catalog)

    for tool_spec in active_family_tool_specs:
        server.add_tool(
            _make_family_tool(service, tool_spec),
            name=tool_spec.name,
            description=tool_spec.description,
            structured_output=True,
        )

    if "litellm_native_request" in active_tool_names:
        _register_native_request_tool(server, service, denied_route_keys=denied_route_keys)

    if "litellm_route_details" in active_tool_names:
        _register_route_details_tool(server, catalog=route_catalog)

    return server


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the LiteLLM MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default=None,
        help="MCP transport override. Defaults to MCP_LITELLM_TRANSPORT or stdio.",
    )
    parser.add_argument("--host", default=None, help="HTTP host override for SSE/streamable HTTP transports.")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="HTTP port override for SSE/streamable HTTP transports.",
    )
    parser.add_argument(
        "--tool-profile",
        action="append",
        default=None,
        help=(
            "Tool profile(s) to enable. Repeat the flag or pass a comma-separated list. "
            f"Available profiles: {', '.join(profile.name for profile in list_tool_profiles())}."
        ),
    )
    parser.add_argument(
        "--enable-tool",
        action="append",
        default=None,
        help="Enable specific tool names in addition to the selected profiles.",
    )
    parser.add_argument(
        "--disable-tool",
        action="append",
        default=None,
        help="Disable specific tool names after profile and enable-tool resolution.",
    )
    return parser.parse_args()


def _resolve_settings(base: Settings, args: argparse.Namespace) -> Settings:
    """Apply validated CLI overrides on top of the base settings."""
    overrides: dict[str, Any] = {}
    if args.transport is not None:
        overrides["transport"] = args.transport
    if args.host is not None:
        overrides["host"] = args.host
    if args.port is not None:
        overrides["port"] = args.port
    parsed_tool_profiles = _parse_name_args(args.tool_profile)
    if parsed_tool_profiles is not None:
        overrides["tool_profiles"] = parsed_tool_profiles
    parsed_enable_tools = _parse_name_args(args.enable_tool)
    if parsed_enable_tools is not None:
        overrides["enable_tools"] = parsed_enable_tools
    parsed_disable_tools = _parse_name_args(args.disable_tool)
    if parsed_disable_tools is not None:
        overrides["disable_tools"] = parsed_disable_tools
    return Settings.model_validate({**base.model_dump(), **overrides})


def main() -> None:
    """Run the LiteLLM MCP server using CLI arguments plus environment defaults."""
    base_settings = get_settings()
    args = _parse_args()
    settings = _resolve_settings(base_settings, args)
    try:
        server = build_server(settings)
    except ValueError as exc:
        print(f"mcp-litellm: {exc}", file=sys.stderr)  # noqa: T201
        sys.exit(2)
    server.run(transport=settings.transport)
