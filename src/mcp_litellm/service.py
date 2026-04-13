"""Service layer for mapping MCP tool calls onto LiteLLM routes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from mcp_litellm.errors import (
    MissingPathParametersError,
    RouteNotAllowedError,
    UnknownToolActionError,
)
from mcp_litellm.models import RequestOptions
from mcp_litellm.route_catalog import RouteInfo, get_route

if TYPE_CHECKING:
    from collections.abc import Mapping

    from mcp_litellm.client import LiteLLMClient

PATH_PARAM_PATTERN = re.compile(r"{([^}]+)}")


@dataclass(frozen=True, slots=True)
class ActionSpec:
    """A named tool action mapped to a specific LiteLLM route key."""

    route_key: str


class LiteLLMToolService:
    """Execute curated tool actions and route-key calls against LiteLLM."""

    def __init__(
        self,
        client: LiteLLMClient,
        *,
        route_catalog: Mapping[str, RouteInfo] | None = None,
    ) -> None:
        """Create a service wrapper around the shared LiteLLM client."""
        self._client = client
        self._route_catalog = route_catalog

    @staticmethod
    def _render_path(path_template: str, path_params: dict[str, str] | None) -> str:
        params = path_params or {}
        required_params = set(PATH_PARAM_PATTERN.findall(path_template))
        missing_params = sorted(required_params - set(params))
        if missing_params:
            raise MissingPathParametersError(missing_params)
        rendered_path = path_template
        for key in required_params:
            rendered_path = rendered_path.replace(f"{{{key}}}", quote(str(params[key]), safe=""))
        return rendered_path

    async def execute_route(self, route: RouteInfo, options: RequestOptions | None = None) -> dict[str, Any]:
        """Execute a single LiteLLM route using normalized request options."""
        resolved_options = options or RequestOptions()
        rendered_path = self._render_path(route.path, resolved_options.path_params)
        result = await self._client.request(
            method=route.method,
            path=rendered_path,
            query=resolved_options.query,
            body=resolved_options.body,
            multipart_files=resolved_options.multipart_files,
        )
        result["route_key"] = route.key
        result["summary"] = route.summary
        result["classification"] = route.classification
        return result

    async def execute_route_key(
        self,
        route_key: str,
        *,
        allowed_classifications: set[str],
        options: RequestOptions | None = None,
    ) -> dict[str, Any]:
        """Execute a route key if its classification is within the allowed set."""
        route = get_route(route_key, catalog=self._route_catalog)
        if route.classification not in allowed_classifications:
            raise RouteNotAllowedError(route.key, route.classification)
        return await self.execute_route(route, options)

    async def execute_action(
        self,
        action: str,
        actions: dict[str, ActionSpec],
        *,
        options: RequestOptions | None = None,
    ) -> dict[str, Any]:
        """Execute a named family-tool action against its mapped LiteLLM route."""
        try:
            action_spec = actions[action]
        except KeyError as exc:
            raise UnknownToolActionError(action, sorted(actions)) from exc

        result = await self.execute_route_key(
            action_spec.route_key,
            allowed_classifications={"typed"},
            options=options,
        )
        result["action"] = action
        return result
