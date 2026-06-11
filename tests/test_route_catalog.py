"""Route catalog tests for the LiteLLM MCP server."""

from __future__ import annotations

import hashlib
import json

from mcp_litellm.route_catalog import build_route_catalog, get_route


def test_route_catalog_classifies_typed_route() -> None:
    route = get_route("GET /team/info")
    assert route.classification == "typed"


def test_route_catalog_classifies_alias_route() -> None:
    route = get_route("GET /v1/models")
    assert route.classification == "alias"


def test_route_catalog_classifies_pass_through_route() -> None:
    route = get_route("GET /openai/{endpoint}")
    assert route.classification == "excluded_pass_through"


def test_route_catalog_classifies_cursor_route_as_pass_through() -> None:
    route = get_route("POST /cursor/chat/completions")
    assert route.classification == "excluded_pass_through"


def test_route_catalog_classifies_protocol_route() -> None:
    route = get_route("GET /.well-known/openid-configuration")
    assert route.classification == "excluded_protocol"


def test_route_catalog_classifies_vertex_ai_live_as_protocol() -> None:
    route = get_route("GET /vertex_ai/live")
    assert route.classification == "excluded_protocol"


def test_route_catalog_classifies_generic_native_route() -> None:
    route = get_route("POST /v1/evals")
    assert route.classification == "generic_native"


def test_route_catalog_preserves_openai_realtime_alias() -> None:
    route = get_route("POST /openai/v1/realtime/calls")
    assert route.classification == "alias"


# ---------------------------------------------------------------------------
# §5.1 / §5.3 snapshot drift guards (regression guards — must pass at red time)
# ---------------------------------------------------------------------------


def test_typed_classification_set_is_stable() -> None:
    """The full sorted set of typed route keys must match a pinned baseline.

    317 keys, SHA-256 of newline-joined sorted keys.
    This pins current behavior across the route-catalog refactor.
    """
    catalog = build_route_catalog()
    typed_keys = [k for k, v in catalog.items() if v.classification == "typed"]
    assert len(typed_keys) == 317
    digest = hashlib.sha256("\n".join(sorted(typed_keys)).encode()).hexdigest()
    assert digest == "8d73e94ca8acd6c7f7bb1d26cbee61754499d699972b0e08ac29c8718dacb76d"


def test_generic_native_baseline() -> None:
    """Count of generic_native routes must equal 175 (snapshot drift guard).

    Any future spec refresh adding/removing native routes fails this until
    consciously updated.
    """
    catalog = build_route_catalog()
    generic_native_keys = [k for k, v in catalog.items() if v.classification == "generic_native"]
    assert len(generic_native_keys) == 175


# ---------------------------------------------------------------------------
# §5.3 prefix structure integrity (will FAIL at red — requires TYPED_PATH_PREFIXES/TYPED_EXACT_PATHS)
# ---------------------------------------------------------------------------


def test_no_typed_prefix_shadows_another() -> None:
    """No TYPED_PATH_PREFIXES entry is a prefix of another entry.

    Also: no TYPED_EXACT_PATHS entry starts with any prefix in TYPED_PATH_PREFIXES.
    These are new module-level names the engineer adds in the refactor.
    """
    from mcp_litellm.route_catalog import TYPED_EXACT_PATHS, TYPED_PATH_PREFIXES

    # Validate no prefix is a prefix of another (shadowing)
    prefix_list = list(TYPED_PATH_PREFIXES)
    for i, a in enumerate(prefix_list):
        for j, b in enumerate(prefix_list):
            if i != j:
                assert not a.startswith(b), f"Prefix '{a}' is shadowed by '{b}' — one would always match before the other"

    # No exact path starts with any prefix (would be unreachable dead code)
    for exact in TYPED_EXACT_PATHS:
        for prefix in TYPED_PATH_PREFIXES:
            assert not exact.startswith(prefix), f"Exact path '{exact}' starts with prefix '{prefix}' — exact entry is redundant"


# ---------------------------------------------------------------------------
# §5.2 non-HTTP-method path-item keys (e.g. "parameters") ignored
# ---------------------------------------------------------------------------


def test_non_http_method_path_item_keys_ignored(tmp_path) -> None:
    """A spec with a 'parameters' list in a path-item must build without error or bogus route."""
    # Build a minimal spec with a "parameters" key in a path-item (valid OpenAPI)
    spec: dict = {
        "openapi": "3.0.0",
        "info": {"title": "test", "version": "0.1"},
        "paths": {
            "/test-path": {
                "parameters": [{"name": "x", "in": "query", "schema": {"type": "string"}}],
                "get": {
                    "summary": "Test",
                    "operationId": "test_get",
                    "responses": {"200": {"description": "OK"}},
                },
            }
        },
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    catalog = build_route_catalog(spec_path)

    # Must have exactly one route (GET /test-path), not a bogus "PARAMETERS /test-path"
    assert list(catalog.keys()) == ["GET /test-path"]
    assert catalog["GET /test-path"].method == "GET"
