"""LiteLLM route catalog and classification helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from mcp_litellm.config import get_settings
from mcp_litellm.errors import UnknownLiteLLMRouteError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

RouteClassification = Literal[
    "typed",
    "generic_native",
    "alias",
    "excluded_pass_through",
    "excluded_protocol",
]

TYPED_PATH_PREFIXES = (
    "/models",
    "/model/",
    "/model/info",
    "/key/",
    "/team/",
    "/user/",
    "/organization/",
    "/project/",
    "/customer/",
    "/budget/",
    "/spend/",
    "/global/spend/",
    "/provider/budgets",
    "/tag/",
    "/cost/estimate",
    "/usage/ai/chat",
    "/add/allowed_ip",
    "/delete/allowed_ip",
    "/agent/daily/activity",
    "/test",
    "/health",
    "/active/callbacks",
    "/settings",
    "/debug/asyncio-tasks",
    "/cache/",
    "/callbacks/",
    "/router/",
    "/fallback",
    "/credentials",
    "/jwt/key/mapping/",
    "/prompts",
    "/policies",
    "/policy/",
    "/guardrails",
    "/search_tools",
    "/search",
    "/rag/",
    "/v1/tool/",
    "/v1/mcp/",
    "/mcp-rest/",
    "/public/mcp_hub",
    "/config/",
    "/config_overrides/",
    "/cloudzero/",
    "/vantage/",
    "/audit",
    "/compliance/",
    "/access_group/",
    "/model_group/",
    "/public/model_hub",
    "/public/providers",
    "/public/endpoints",
    "/public/litellm_model_cost_map",
    "/get/",
    "/update/",
    "/email/event_settings",
    "/sso/readiness",
    "/upload/logo",
    "/in_product_nudges",
)

PASS_THROUGH_PATH_PREFIXES = (
    "/openai/",
    "/openai_passthrough/",
    "/anthropic/",
    "/azure/",
    "/azure_ai/",
    "/vertex_ai/",
    "/bedrock/",
    "/cohere/",
    "/mistral/",
    "/vllm/",
    "/milvus/",
    "/gemini/",
    "/assemblyai/",
    "/eu.assemblyai/",
    "/langfuse/",
    "/cursor/",
)

PROTOCOL_EXACT_PATHS = {
    "/authorize",
    "/token",
    "/callback",
    "/register",
}

PROTOCOL_DYNAMIC_PATHS = {
    "/{mcp_server_name}/authorize",
    "/{mcp_server_name}/token",
    "/{mcp_server_name}/register",
}

WEBSOCKET_PROTOCOL_PATHS = {
    ("GET", "/responses"),
    ("GET", "/realtime"),
}


@dataclass(frozen=True, slots=True)
class RouteInfo:
    """Normalized metadata for a single LiteLLM route."""

    key: str
    method: str
    path: str
    summary: str
    operation_id: str | None
    tags: tuple[str, ...]
    classification: RouteClassification


def route_key(method: str, path: str) -> str:
    """Build a canonical route key from an HTTP method and path."""
    return f"{method.upper()} {path}"


def _matches_prefix(path: str, prefixes: Iterable[str]) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in prefixes)


def _is_protocol_path(method: str, path: str) -> bool:
    if path in PROTOCOL_EXACT_PATHS or path in PROTOCOL_DYNAMIC_PATHS:
        return True
    if path.startswith("/.well-known/"):
        return True
    return (method, path) in WEBSOCKET_PROTOCOL_PATHS


def _is_pass_through_path(path: str) -> bool:
    return _matches_prefix(path, PASS_THROUGH_PATH_PREFIXES)


def _is_alias_path(path: str, all_paths: set[str]) -> bool:
    if path.startswith("/v1/"):
        canonical_path = path.removeprefix("/v1")
        if canonical_path in all_paths:
            return True

    if path.startswith("/openai/v1/responses"):
        canonical_path = path.removeprefix("/openai/v1")
        if canonical_path in all_paths:
            return True

    if path.startswith("/openai/v1/realtime"):
        canonical_path = path.removeprefix("/openai/v1")
        if canonical_path in all_paths:
            return True

    deployment_aliases = {
        "/openai/deployments/{model}/chat/completions": "/chat/completions",
        "/openai/deployments/{model}/completions": "/completions",
        "/openai/deployments/{model}/embeddings": "/embeddings",
        "/openai/deployments/{model}/images/generations": "/images/generations",
        "/openai/deployments/{model}/images/edits": "/images/edits",
        "/engines/{model}/chat/completions": "/chat/completions",
        "/engines/{model}/completions": "/completions",
        "/engines/{model}/embeddings": "/embeddings",
        "/{provider}/v1/files": "/files",
        "/{provider}/v1/files/{file_id}": "/files/{file_id}",
        "/{provider}/v1/files/{file_id}/content": "/files/{file_id}/content",
        "/{provider}/v1/batches": "/batches",
        "/{provider}/v1/batches/{batch_id}": "/batches/{batch_id}",
        "/{provider}/v1/batches/{batch_id}/cancel": "/batches/{batch_id}/cancel",
    }
    deployment_canonical_path = deployment_aliases.get(path)
    return bool(deployment_canonical_path and deployment_canonical_path in all_paths)


def _classify_route(
    method: str,
    path: str,
    all_paths: set[str],
    tags: tuple[str, ...],
) -> RouteClassification:
    if _is_protocol_path(method, path) or "WebSocket" in tags:
        return "excluded_protocol"
    if _is_alias_path(path, all_paths):
        return "alias"
    if _is_pass_through_path(path):
        return "excluded_pass_through"
    if _matches_prefix(path, TYPED_PATH_PREFIXES):
        return "typed"
    return "generic_native"


def load_openapi_spec(path: Path | None = None) -> dict:
    """Load the vendored LiteLLM OpenAPI spec into memory."""
    source = path or get_settings().resolved_openapi_path
    return json.loads(source.read_text())


@cache
def _build_route_catalog_cached(resolved_path: str) -> dict[str, RouteInfo]:
    """Build the normalized route catalog from the vendored LiteLLM spec."""
    spec = load_openapi_spec(path=Path(resolved_path))
    all_paths = set(spec["paths"])
    catalog: dict[str, RouteInfo] = {}

    for route_path, operations in spec["paths"].items():
        for method, operation in operations.items():
            operation_method = method.upper()
            tags = tuple(operation.get("tags", ()))
            key = route_key(operation_method, route_path)
            catalog[key] = RouteInfo(
                key=key,
                method=operation_method,
                path=route_path,
                summary=operation.get("summary", ""),
                operation_id=operation.get("operationId"),
                tags=tags,
                classification=_classify_route(operation_method, route_path, all_paths, tags),
            )

    return catalog


def build_route_catalog(path: Path | None = None) -> dict[str, RouteInfo]:
    """Build the normalized route catalog from the vendored LiteLLM spec."""
    resolved_path = (path or get_settings().resolved_openapi_path).resolve()
    return _build_route_catalog_cached(str(resolved_path))


def get_route(
    route_key_value: str,
    *,
    catalog: Mapping[str, RouteInfo] | None = None,
    path: Path | None = None,
) -> RouteInfo:
    """Return a single route definition by its canonical route key."""
    resolved_catalog = catalog or build_route_catalog(path)
    try:
        return resolved_catalog[route_key_value]
    except KeyError as exc:  # pragma: no cover - thin wrapper
        raise UnknownLiteLLMRouteError(route_key_value) from exc


def list_routes(
    *,
    classifications: set[RouteClassification] | None = None,
    catalog: Mapping[str, RouteInfo] | None = None,
    path: Path | None = None,
) -> list[RouteInfo]:
    """List LiteLLM routes, optionally filtered by classification."""
    resolved_catalog = (catalog or build_route_catalog(path)).values()
    if classifications is None:
        return sorted(resolved_catalog, key=lambda route: route.key)
    return sorted(
        (route for route in resolved_catalog if route.classification in classifications),
        key=lambda route: route.key,
    )
