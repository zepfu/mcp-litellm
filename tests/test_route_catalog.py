"""Route catalog tests for the LiteLLM MCP server."""

from mcp_litellm.route_catalog import get_route


def test_route_catalog_classifies_typed_route() -> None:
    route = get_route("GET /team/info")
    assert route.classification == "typed"


def test_route_catalog_classifies_alias_route() -> None:
    route = get_route("GET /v1/models")
    assert route.classification == "alias"


def test_route_catalog_classifies_pass_through_route() -> None:
    route = get_route("GET /openai/{endpoint}")
    assert route.classification == "excluded_pass_through"


def test_route_catalog_classifies_protocol_route() -> None:
    route = get_route("GET /.well-known/openid-configuration")
    assert route.classification == "excluded_protocol"


def test_route_catalog_classifies_generic_native_route() -> None:
    route = get_route("POST /v1/evals")
    assert route.classification == "generic_native"
