"""Async HTTP client for the LiteLLM proxy."""

from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

import httpx

from mcp_litellm.errors import InvalidMultipartBodyError, LiteLLMRequestError

if TYPE_CHECKING:
    from mcp_litellm.config import Settings

JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class LiteLLMClient:
    """Thin async client for calling LiteLLM endpoints."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the client with resolved runtime settings."""
        self._settings = settings

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
        }
        if self._settings.litellm_api_key:
            headers["x-litellm-api-key"] = self._settings.litellm_api_key
            if self._settings.include_bearer_auth:
                headers["Authorization"] = f"Bearer {self._settings.litellm_api_key}"
        return headers

    @staticmethod
    def _build_files(
        multipart_files: list[dict[str, str]] | None,
    ) -> list[tuple[str, tuple[str, bytes, str]]]:
        files: list[tuple[str, tuple[str, bytes, str]]] = []
        for file_spec in multipart_files or ():
            field_name = file_spec["field_name"]
            path = Path(file_spec["path"]).expanduser()
            content_type = file_spec.get("content_type") or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            filename = file_spec.get("filename") or path.name
            files.append((field_name, (filename, path.read_bytes(), content_type)))
        return files

    @staticmethod
    def _multipart_form_data(body: JsonValue) -> dict[str, str]:
        if body is None:
            return {}
        if not isinstance(body, dict):
            raise InvalidMultipartBodyError

        form_data: dict[str, str] = {}
        for key, value in body.items():
            if isinstance(value, str):
                form_data[key] = value
            else:
                form_data[key] = json.dumps(value)
        return form_data

    @staticmethod
    def _parse_response(response: httpx.Response) -> dict[str, Any]:
        content_type = response.headers.get("content-type", "")
        result: dict[str, Any] = {
            "ok": response.is_success,
            "status_code": response.status_code,
            "content_type": content_type,
            "headers": {
                key: value
                for key, value in response.headers.items()
                if key.lower() in {"content-type", "content-length", "location"}
            },
        }

        if "application/json" in content_type:
            result["data"] = response.json()
            return result

        if content_type.startswith("text/") or "application/xml" in content_type:
            result["text"] = response.text
            return result

        try:
            result["text"] = response.content.decode("utf-8")
        except UnicodeDecodeError:
            result["base64"] = base64.b64encode(response.content).decode("ascii")

        return result

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: JsonValue = None,
        multipart_files: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Send a single HTTP request to LiteLLM and normalize the response."""
        url = urljoin(f"{self._settings.litellm_base_url.rstrip('/')}/", path.lstrip("/"))
        headers = self._build_headers()
        request_kwargs: dict[str, Any] = {
            "headers": headers,
            "params": query,
            "timeout": self._settings.timeout_seconds,
        }

        if multipart_files:
            request_kwargs["files"] = self._build_files(multipart_files)
            request_kwargs["data"] = self._multipart_form_data(body)
        elif body is not None:
            request_kwargs["json"] = body

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.request(method=method, url=url, **request_kwargs)
        except httpx.HTTPError as exc:  # pragma: no cover - thin wrapper
            raise LiteLLMRequestError(str(exc)) from exc

        parsed = self._parse_response(response)
        parsed["method"] = method.upper()
        parsed["path"] = path
        return parsed
