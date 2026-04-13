"""Pydantic contract tests for MCP request inputs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from mcp_litellm.models import MULTIPART_BODY_ERROR, MultipartFileSpec, RequestOptions

if TYPE_CHECKING:
    from pathlib import Path


def test_request_options_coerces_path_params_to_strings() -> None:
    raw_options: dict[str, Any] = {"path_params": {"team_id": 123}}
    options = RequestOptions.model_validate(raw_options)

    assert options.path_params == {"team_id": "123"}


def test_request_options_rejects_nested_query_objects() -> None:
    raw_options: dict[str, Any] = {"query": {"nested": {"nope": True}}}

    with pytest.raises(ValidationError, match=r"query\.nested"):
        RequestOptions.model_validate(raw_options)


def test_request_options_rejects_non_object_multipart_body(tmp_path: Path) -> None:
    upload_file = tmp_path / "upload.txt"
    upload_file.write_text("hello")
    raw_options: dict[str, Any] = {
        "body": ["not", "an", "object"],
        "multipart_files": (MultipartFileSpec(field_name="file", path=upload_file),),
    }

    with pytest.raises(ValidationError, match=MULTIPART_BODY_ERROR):
        RequestOptions.model_validate(raw_options)


def test_multipart_file_spec_requires_existing_file(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.txt"

    with pytest.raises(ValidationError, match="Path does not point to a file"):
        MultipartFileSpec(field_name="file", path=missing_file)
