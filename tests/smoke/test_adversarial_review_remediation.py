"""Smoke tests for the adversarial-review remediation (Wave 1).

These tests validate that the feature works end-to-end after implementation
and serve as permanent regression guards.

CO-2 executes:
    run_gate_check(mode='targeted', test_path='tests/smoke/test_adversarial_review_remediation.py')
"""

from __future__ import annotations


def test_package_imports() -> None:
    """build_server and main must be importable from mcp_litellm.server."""
    from mcp_litellm.server import build_server, main

    assert callable(build_server)
    assert callable(main)


def test_build_server_default_toolset() -> None:
    """build_server(Settings()) must return a server without raising."""
    from mcp_litellm.config import Settings
    from mcp_litellm.server import build_server

    server = build_server(Settings())
    assert server is not None


def test_version_is_bumped() -> None:
    """mcp_litellm.__version__ must be '0.2.0' and match pyproject.toml version."""
    import tomllib
    from pathlib import Path

    import mcp_litellm

    assert mcp_litellm.__version__ == "0.2.0"

    # Locate pyproject.toml relative to this file (tests/smoke/ -> repo root)
    pyproject_path = Path(__file__).parents[2] / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        pyproject = tomllib.load(f)

    pyproject_version = pyproject["project"]["version"]
    assert mcp_litellm.__version__ == pyproject_version


def test_errors_module_imports() -> None:
    """McpLiteLLMError must be importable from mcp_litellm.errors."""
    from mcp_litellm.errors import McpLiteLLMError

    assert issubclass(McpLiteLLMError, Exception)
