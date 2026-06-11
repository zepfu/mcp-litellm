"""Shared pytest fixtures for the LiteLLM MCP server test suite."""

from __future__ import annotations

import os

import pytest

from mcp_litellm.config import Settings


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all MCP_LITELLM_* env vars and disable .env file loading.

    This fixture ensures every test runs in a hermetic environment: no ambient
    environment variables and no .env file bleed-through can influence Settings.
    """
    for key in list(os.environ):
        if key.startswith("MCP_LITELLM_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
