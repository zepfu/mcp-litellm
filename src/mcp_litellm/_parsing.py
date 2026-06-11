"""Shared parsing helpers for the LiteLLM MCP server."""

from __future__ import annotations


def split_csv(value: str) -> tuple[str, ...]:
    """Split a comma-separated string into stripped, non-empty parts.

    Args:
        value: The raw comma-separated string to split.

    Returns:
        A tuple of stripped tokens with empty entries removed.
    """
    return tuple(item.strip() for item in value.split(",") if item.strip())
