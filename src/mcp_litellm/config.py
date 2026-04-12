"""Runtime configuration for the LiteLLM MCP server."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings for the LiteLLM MCP server."""

    model_config = SettingsConfigDict(
        env_prefix="MCP_LITELLM_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    litellm_base_url: str = Field(default="http://127.0.0.1:4000")
    litellm_api_key: str | None = Field(default=None)
    timeout_seconds: float = Field(default=60.0, gt=0)
    include_bearer_auth: bool = Field(default=True)

    transport: Literal["stdio", "sse", "streamable-http"] = Field(default="stdio")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    mount_path: str = Field(default="/")
    sse_path: str = Field(default="/sse")
    message_path: str = Field(default="/messages/")
    streamable_http_path: str = Field(default="/mcp")

    openapi_path: Path = Field(default=Path("vendor/litellm/openapi.json"))
    tool_profiles: tuple[str, ...] = Field(default=("core",))
    enable_tools: tuple[str, ...] = Field(default=())
    disable_tools: tuple[str, ...] = Field(default=())

    @field_validator("tool_profiles", "enable_tools", "disable_tools", mode="before")
    @classmethod
    def _parse_name_list(cls, value: object) -> object:
        _ = cls
        if value is None:
            return value
        if isinstance(value, str):
            stripped_value = value.strip()
            if not stripped_value:
                return ()
            if stripped_value.startswith("["):
                parsed_value = json.loads(stripped_value)
                if not isinstance(parsed_value, list):
                    message = "Expected a JSON array for tool-selection settings."
                    raise ValueError(message)
                return tuple(str(item) for item in parsed_value if str(item).strip())
            return tuple(item.strip() for item in stripped_value.split(",") if item.strip())
        if isinstance(value, list | tuple | set | frozenset):
            return tuple(str(item) for item in value if str(item).strip())
        message = "Tool-selection settings must be a string or iterable of strings."
        raise TypeError(message)

    @property
    def resolved_openapi_path(self) -> Path:
        """Return the vendored LiteLLM OpenAPI path as an absolute path."""
        return self.openapi_path.resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object."""
    return Settings()
