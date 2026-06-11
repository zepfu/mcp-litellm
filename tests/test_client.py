"""Client tests for the LiteLLM MCP server."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from httpx import Response

from mcp_litellm.client import LiteLLMClient
from mcp_litellm.config import Settings
from mcp_litellm.errors import LiteLLMResponseTooLargeError
from mcp_litellm.models import MultipartFileSpec


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


async def test_client_rejects_oversized_response() -> None:
    client = LiteLLMClient(
        Settings(
            litellm_base_url="https://litellm.example",
            max_response_bytes=4,
        )
    )

    with respx.mock(assert_all_called=True) as router:
        router.get("https://litellm.example/files/file-1/content").mock(
            return_value=Response(
                200,
                content=b"hello",
                headers={"content-type": "text/plain"},
            )
        )
        with pytest.raises(LiteLLMResponseTooLargeError, match="4 bytes"):
            await client.request("GET", "/files/file-1/content")


async def test_client_streams_multipart_uploads_from_file_handles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_file = tmp_path / "upload.txt"
    upload_file.write_text("hello world")

    def fail_read_bytes(self: Path) -> bytes:
        raise AssertionError("read_bytes should not be used for multipart uploads")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)

    client = LiteLLMClient(Settings(litellm_base_url="https://litellm.example"))

    with respx.mock(assert_all_called=True) as router:
        router.post("https://litellm.example/upload").mock(return_value=Response(200, json={"ok": True}))
        result = await client.request(
            "POST",
            "/upload",
            body={"purpose": "test"},
            multipart_files=(MultipartFileSpec(field_name="file", path=upload_file),),
        )

    assert result["data"] == {"ok": True}


# ---------------------------------------------------------------------------
# §4.1 shared AsyncClient pooling
# ---------------------------------------------------------------------------


async def test_reuses_single_async_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two requests on the same LiteLLMClient must reuse a single AsyncClient."""
    instantiation_count = 0
    original_init = httpx.AsyncClient.__init__

    def counting_init(self: httpx.AsyncClient, *args: Any, **kwargs: Any) -> None:
        nonlocal instantiation_count
        instantiation_count += 1
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", counting_init)

    client = LiteLLMClient(Settings(litellm_base_url="https://litellm.example"))

    with respx.mock(assert_all_called=False) as router:
        router.get("https://litellm.example/health").mock(return_value=Response(200, json={"ok": True}))
        router.get("https://litellm.example/test").mock(return_value=Response(200, json={"ok": True}))
        await client.request("GET", "/health")
        await client.request("GET", "/test")

    assert instantiation_count == 1


# ---------------------------------------------------------------------------
# §4.3 follow_redirects=False
# ---------------------------------------------------------------------------


async def test_does_not_follow_redirects() -> None:
    """A 302 response must be returned as-is; redirect target NOT fetched."""
    client = LiteLLMClient(Settings(litellm_base_url="https://litellm.example"))

    with respx.mock(assert_all_called=False) as router:
        router.get("https://litellm.example/old-path").mock(
            return_value=Response(
                302,
                headers={"location": "https://litellm.example/new-path"},
            )
        )
        # Ensure /new-path is NOT called
        new_route = router.get("https://litellm.example/new-path").mock(
            return_value=Response(200, json={"should": "not reach here"})
        )
        result = await client.request("GET", "/old-path")

    assert result["status_code"] == 302
    assert "location" in result["headers"]
    assert not new_route.called


# ---------------------------------------------------------------------------
# §4.2 malformed JSON parse error
# ---------------------------------------------------------------------------


async def test_malformed_json_raises_parse_error() -> None:
    """content-type application/json with invalid JSON body must raise LiteLLMResponseParseError."""
    from mcp_litellm.errors import LiteLLMResponseParseError

    client = LiteLLMClient(Settings(litellm_base_url="https://litellm.example"))

    with respx.mock(assert_all_called=False) as router:
        router.get("https://litellm.example/test").mock(
            return_value=Response(
                200,
                content=b"{not json",
                headers={"content-type": "application/json"},
            )
        )
        with pytest.raises(LiteLLMResponseParseError):
            await client.request("GET", "/test")


# ---------------------------------------------------------------------------
# §4.2 text/* bad encoding falls back to base64
# ---------------------------------------------------------------------------


async def test_declared_text_bad_encoding_falls_back_to_base64() -> None:
    """text/plain with non-ASCII bytes must yield a base64 key, not raise."""
    client = LiteLLMClient(Settings(litellm_base_url="https://litellm.example"))
    # Non-ASCII bytes that are invalid in ASCII charset
    bad_bytes = b"\xff\xfe"

    with respx.mock(assert_all_called=False) as router:
        router.get("https://litellm.example/test").mock(
            return_value=Response(
                200,
                content=bad_bytes,
                headers={"content-type": "text/plain; charset=ascii"},
            )
        )
        result = await client.request("GET", "/test")

    assert "base64" in result
    assert result["base64"] == base64.b64encode(bad_bytes).decode("ascii")


# ---------------------------------------------------------------------------
# §4.5 None query values dropped
# ---------------------------------------------------------------------------


async def test_none_query_values_dropped() -> None:
    """Query params with None scalar values must be omitted from the request URL."""
    client = LiteLLMClient(Settings(litellm_base_url="https://litellm.example"))

    with respx.mock(assert_all_called=True) as router:
        route = router.get("https://litellm.example/test").mock(return_value=Response(200, json={}))
        await client.request("GET", "/test", query={"a": None, "b": "x"})

    sent_url = str(route.calls[0].request.url)
    assert "b=x" in sent_url
    assert "a=" not in sent_url


# ---------------------------------------------------------------------------
# §2.5 None list members dropped from query
# ---------------------------------------------------------------------------


async def test_none_query_list_member_dropped() -> None:
    """Query list values with None members must drop those members.

    After the fix, query={'t': ['x', None]} must send t=x only — the None
    member must be fully omitted (not sent as t= or t=None).
    """
    client = LiteLLMClient(Settings(litellm_base_url="https://litellm.example"))

    with respx.mock(assert_all_called=True) as router:
        route = router.get("https://litellm.example/test").mock(return_value=Response(200, json={}))
        await client.request("GET", "/test", query={"t": ["x", None]})

    sent_url = str(route.calls[0].request.url)
    assert "t=x" in sent_url
    # None must not appear as "None" string or as an empty value
    assert "t=None" not in sent_url
    # The param must appear exactly once (the None entry must be dropped entirely)
    assert sent_url.count("t=") == 1


# ---------------------------------------------------------------------------
# §4.6 multipart None field omitted
# ---------------------------------------------------------------------------


async def test_multipart_none_field_omitted(tmp_path: Path) -> None:
    """Multipart body fields with None values must be omitted (no literal 'null')."""
    upload_file = tmp_path / "f.txt"
    upload_file.write_text("data")
    client = LiteLLMClient(Settings(litellm_base_url="https://litellm.example"))

    with respx.mock(assert_all_called=True) as router:
        route = router.post("https://litellm.example/upload").mock(return_value=Response(200, json={}))
        await client.request(
            "POST",
            "/upload",
            body={"a": None, "b": "x"},
            multipart_files=(MultipartFileSpec(field_name="file", path=upload_file),),
        )

    sent_request = route.calls[0].request
    body_text = sent_request.content.decode("latin-1")
    assert "b" in body_text
    assert "null" not in body_text
    # "a" field name should not appear
    assert 'name="a"' not in body_text


# ---------------------------------------------------------------------------
# §2.3 multipart blocked when uploads disabled
# ---------------------------------------------------------------------------


async def test_multipart_blocked_when_uploads_disabled(tmp_path: Path) -> None:
    """When allow_local_file_uploads=False, multipart raises LocalFileUploadNotAllowedError before HTTP."""
    from mcp_litellm.errors import LocalFileUploadNotAllowedError

    upload_file = tmp_path / "f.txt"
    upload_file.write_text("data")
    client = LiteLLMClient(Settings(litellm_base_url="https://litellm.example", allow_local_file_uploads=False))

    with respx.mock(assert_all_called=False) as router:
        router.post("https://litellm.example/upload").mock(return_value=Response(200, json={}))
        with pytest.raises(LocalFileUploadNotAllowedError):
            await client.request(
                "POST",
                "/upload",
                multipart_files=(MultipartFileSpec(field_name="file", path=upload_file),),
            )

        # HTTP must NOT have been called
        assert not router.calls


# ---------------------------------------------------------------------------
# §2.4 file deleted after validation → clean McpLiteLLMError
# ---------------------------------------------------------------------------


async def test_multipart_file_deleted_after_validation_raises_clean_error(tmp_path: Path) -> None:
    """When a file is deleted after MultipartFileSpec validation, request() raises McpLiteLLMError."""
    from mcp_litellm.errors import McpLiteLLMError

    upload_file = tmp_path / "f.txt"
    upload_file.write_text("data")
    file_spec = MultipartFileSpec(field_name="file", path=upload_file)
    # Delete the file after validation passes
    upload_file.unlink()

    client = LiteLLMClient(Settings(litellm_base_url="https://litellm.example"))

    with respx.mock(assert_all_called=False) as router:
        router.post("https://litellm.example/upload").mock(return_value=Response(200, json={}))
        with pytest.raises(McpLiteLLMError):
            await client.request("POST", "/upload", multipart_files=(file_spec,))


# ---------------------------------------------------------------------------
# §4.8 transport error wrapped (formerly pragma: no cover)
# ---------------------------------------------------------------------------


async def test_transport_error_wrapped() -> None:
    """httpx.ConnectError must be caught and re-raised as LiteLLMRequestError."""
    from mcp_litellm.errors import LiteLLMRequestError

    client = LiteLLMClient(Settings(litellm_base_url="https://litellm.example"))

    with respx.mock(assert_all_called=False) as router:
        router.get("https://litellm.example/test").mock(side_effect=httpx.ConnectError("connection refused"))
        with pytest.raises(LiteLLMRequestError):
            await client.request("GET", "/test")
