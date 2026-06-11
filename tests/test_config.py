"""Unit tests for config.py -- Settings validation and defaults."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from mcp_litellm.config import Settings

# ---------------------------------------------------------------------------
# §10.1 hermeticity
# ---------------------------------------------------------------------------


def test_settings_ignores_ambient_env() -> None:
    """The autouse _hermetic_env fixture clears ambient MCP_LITELLM_* vars."""
    assert not any(key.startswith("MCP_LITELLM_") for key in os.environ)
    assert Settings().tool_profiles == ("core",)


# ---------------------------------------------------------------------------
# §1.2 JSON-array strip
# ---------------------------------------------------------------------------


def test_json_array_tool_list_strips_whitespace() -> None:
    """JSON-array items must be stripped of surrounding whitespace."""
    settings = Settings(enable_tools='[" litellm_keys "]')  # type: ignore[arg-type]
    assert settings.enable_tools == ("litellm_keys",)


# ---------------------------------------------------------------------------
# §1.3 set ordering
# ---------------------------------------------------------------------------


def test_set_input_is_sorted_deterministically() -> None:
    """Set input for tool_profiles must be sorted to ensure determinism."""
    settings = Settings(tool_profiles={"b", "a"})  # type: ignore[arg-type]
    assert settings.tool_profiles == ("a", "b")


# ---------------------------------------------------------------------------
# §1.5 port range
# ---------------------------------------------------------------------------


def test_port_rejects_out_of_range_high() -> None:
    """Port 70000 must raise ValidationError (out of valid range 1-65535)."""
    with pytest.raises(ValidationError):
        Settings(port=70000)


def test_port_rejects_out_of_range_zero() -> None:
    """Port 0 must raise ValidationError (out of valid range 1-65535)."""
    with pytest.raises(ValidationError):
        Settings(port=0)


# ---------------------------------------------------------------------------
# §1.1 default_openapi_path raises when neither candidate exists
# ---------------------------------------------------------------------------


def test_default_openapi_path_raises_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """default_openapi_path() must raise FileNotFoundError naming both paths."""
    import mcp_litellm.config as config_module

    def fake_exists(self: Path) -> bool:
        return False

    monkeypatch.setattr(Path, "exists", fake_exists)

    with pytest.raises(FileNotFoundError) as exc_info:
        config_module.default_openapi_path()

    error_message = str(exc_info.value)
    # Both probed path fragments must appear: the packaged _data path AND the
    # repo-vendored path. A weaker "or" check would let a regression that drops
    # one probe slip through.
    assert str(Path("_data") / "openapi.json") in error_message
    assert str(Path("vendor") / "litellm" / "openapi.json") in error_message


# ---------------------------------------------------------------------------
# §2.3 allow_local_file_uploads default
# ---------------------------------------------------------------------------


def test_allow_local_file_uploads_defaults_true() -> None:
    """Settings.allow_local_file_uploads must default to True."""
    assert Settings().allow_local_file_uploads is True


# ---------------------------------------------------------------------------
# §8.5 DEFAULT_TOOL_PROFILES constant
# ---------------------------------------------------------------------------


def test_default_tool_profiles_constant_matches_settings_default() -> None:
    """DEFAULT_TOOL_PROFILES constant must equal Settings().tool_profiles == ("core",)."""
    from mcp_litellm.config import DEFAULT_TOOL_PROFILES

    assert DEFAULT_TOOL_PROFILES == ("core",)
    assert Settings().tool_profiles == ("core",)
    assert Settings().tool_profiles == DEFAULT_TOOL_PROFILES
