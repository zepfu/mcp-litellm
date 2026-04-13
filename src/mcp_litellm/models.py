"""Shared Pydantic models for MCP request validation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, FilePath, field_validator, model_validator

JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None
QueryScalar = str | int | float | bool | None
QueryValue = QueryScalar | list[QueryScalar]
PathParams = dict[str, str]
QueryParams = dict[str, QueryValue]
NonEmptyString = Annotated[str, Field(min_length=1)]

MULTIPART_BODY_ERROR = "Multipart requests require a JSON object body."


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
        if isinstance(value, dict):
            return {str(key): str(item) for key, item in value.items()}
        return value

    @model_validator(mode="after")
    def _validate_multipart_body(self) -> RequestOptions:
        if self.multipart_files and self.body is not None and not isinstance(self.body, dict):
            raise ValueError(MULTIPART_BODY_ERROR)
        return self
