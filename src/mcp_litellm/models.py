"""Shared Pydantic models for MCP request validation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, ConfigDict, Field, FilePath, field_validator, model_validator

from mcp_litellm.errors import (
    MULTIPART_BODY_ERROR,
    InvalidMultipartBodyError,
    InvalidPathParameterError,
)

__all__ = [
    "MULTIPART_BODY_ERROR",
    "JsonValue",
    "LiteLLMResponse",
    "MultipartFileSpec",
    "PathParams",
    "QueryParams",
    "RequestOptions",
]

JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None
QueryScalar = str | int | float | bool | None
QueryValue = QueryScalar | list[QueryScalar]
PathParams = dict[str, str]
QueryParams = dict[str, QueryValue]
NonEmptyString = Annotated[str, Field(min_length=1)]


class LiteLLMResponse(TypedDict, total=False):
    """Normalized response envelope returned by the LiteLLM client."""

    ok: bool
    status_code: int
    content_type: str
    headers: dict[str, str]
    data: Any
    text: str
    base64: str
    method: str
    path: str
    route_key: str
    summary: str
    classification: str
    action: str


class MultipartFileSpec(BaseModel):
    """Validated local file-upload specification for multipart requests."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_name: NonEmptyString
    path: FilePath
    filename: NonEmptyString | None = None
    content_type: NonEmptyString | None = None

    @field_validator("field_name", "filename", "content_type", mode="before")
    @classmethod
    def _strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("path", mode="before")
    @classmethod
    def _expand_path(cls, value: object) -> object:
        if isinstance(value, str | Path):
            return Path(value).expanduser()
        return value


class RequestOptions(BaseModel):
    """Validated request details passed from an MCP tool invocation to LiteLLM."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path_params: PathParams | None = None
    query: QueryParams | None = None
    body: JsonValue = None
    multipart_files: tuple[MultipartFileSpec, ...] | None = None

    @field_validator("path_params", mode="before")
    @classmethod
    def _coerce_path_params(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        coerced: dict[str, str] = {}
        for key, item in value.items():
            # bool is an int subclass, so reject it before the int/float branch.
            if item is None or isinstance(item, bool):
                detail = f"Path parameter {key!r} must be a string or number, got {item!r}."
                raise InvalidPathParameterError(detail)
            if isinstance(item, int | float | str):
                coerced[str(key)] = str(item)
            else:
                detail = f"Path parameter {key!r} must be a string or number, got {type(item).__name__}."
                raise InvalidPathParameterError(detail)
        return coerced

    @model_validator(mode="after")
    def _validate_multipart_body(self) -> RequestOptions:
        if self.multipart_files and self.body is not None and not isinstance(self.body, dict):
            raise InvalidMultipartBodyError
        return self
