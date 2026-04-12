"""Client tests for the LiteLLM MCP server."""

from __future__ import annotations

import base64

import pytest
import respx
from httpx import Response

from mcp_litellm.client import LiteLLMClient
from mcp_litellm.config import Settings


@pytest.mark.asyncio
async def test_client_sends_auth_headers_and_parses_json() -> None:
    client = LiteLLMClient(
        Settings(
            litellm_base_url="https://litellm.example",
            litellm_api_key="sk-test",
        )
    )

    with respx.mock(assert_all_called=True) as router:
        route = router.post("https://litellm.example/key/generate").mock(return_value=Response(200, json={"key": "value"}))
        result = await client.request("POST", "/key/generate", body={"foo": "bar"})

    assert route.called
    request = route.calls[0].request
    assert request.headers["x-litellm-api-key"] == "sk-test"
    assert request.headers["Authorization"] == "Bearer sk-test"
    assert result["ok"] is True
    assert result["data"] == {"key": "value"}


@pytest.mark.asyncio
async def test_client_parses_binary_response() -> None:
    client = LiteLLMClient(Settings(litellm_base_url="https://litellm.example"))
    payload = b"\x00\xff\x00\xff"

    with respx.mock(assert_all_called=True) as router:
        router.get("https://litellm.example/files/file-1/content").mock(
            return_value=Response(200, content=payload, headers={"content-type": "application/octet-stream"})
        )
        result = await client.request("GET", "/files/file-1/content")

    assert result["ok"] is True
    assert result["base64"] == base64.b64encode(payload).decode("ascii")
