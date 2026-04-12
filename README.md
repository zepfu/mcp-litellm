# mcp-litellm

MCP server for LiteLLM native API workflows, with primary emphasis on LiteLLM's
non-provider-pass-through endpoints.

## What It Provides

- Curated family tools for common LiteLLM admin and control-plane workflows:
  models, keys, teams, identities, budgets/spend, runtime, governance,
  search/RAG, MCP registry management, config, exports, and audit/compliance.
- `litellm_native_request` for any allowlisted LiteLLM-native route that is not
  exposed as a first-class family action yet.
- Startup-time tool filtering so `stdio` clients can load only the LiteLLM tool
  families they actually need.
- Route discovery helpers:
  `litellm_list_routes`,
  `litellm_route_details`,
  `litellm://routes/native`,
  `litellm://routes/typed`,
  `litellm://tools/actions`,
  `litellm://tools/active`.
- A vendored LiteLLM OpenAPI snapshot in `vendor/litellm/openapi.json`.
- A root [`TOOLS.md`](TOOLS.md) reference covering every MCP tool exposed by this server.

## Requirements

- Python `3.14`
- `uv`
- Access to a LiteLLM proxy endpoint

## Configuration

Set these environment variables before running the server:

- `MCP_LITELLM_LITELLM_BASE_URL`
  Example: `http://127.0.0.1:4000`
- `MCP_LITELLM_LITELLM_API_KEY`
  LiteLLM API key or proxy key
- `MCP_LITELLM_TRANSPORT`
  Optional. One of `stdio`, `sse`, `streamable-http`
- `MCP_LITELLM_HOST`
  Optional HTTP host for non-stdio transports
- `MCP_LITELLM_PORT`
  Optional HTTP port for non-stdio transports
- `MCP_LITELLM_TOOL_PROFILES`
  Optional. Comma-separated list or JSON array of tool profiles. Defaults to `core`.
- `MCP_LITELLM_ENABLE_TOOLS`
  Optional. Comma-separated list or JSON array of individual tool names to force-enable.
- `MCP_LITELLM_DISABLE_TOOLS`
  Optional. Comma-separated list or JSON array of individual tool names to disable after profile resolution.

## Tool Loading

The server now resolves its toolset at startup:

- Base set: `tool_profiles`
- Then additive overrides: `enable_tools`
- Then subtractive overrides: `disable_tools`

Default profile:

- `core`
  Loads `litellm_list_routes`, `litellm_route_details`, `litellm_models_catalog`,
  `litellm_keys`, `litellm_teams`, and `litellm_runtime`

Available profiles:

- `none`
- `discovery`
- `catalog`
- `access_admin`
- `identity_admin`
- `spend_admin`
- `runtime_ops`
- `governance`
- `search_rag`
- `mcp_admin`
- `config_admin`
- `native_escape_hatch`
- `core`
- `platform_admin`
- `full`

Notes:

- `litellm_native_request` is not loaded by default. Enable it with the
  `native_escape_hatch` profile or `enable_tools`.
- `litellm://tools/active` reports the exact resolved toolset for a running server instance.
- This is especially useful for `stdio` MCP clients where each client session usually owns its own server process.

## Install

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv sync --extra dev
```

## Run

Default `stdio` transport:

```bash
.venv/bin/mcp-litellm
```

Or with `uv`:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync mcp-litellm
```

Run with a narrow platform-admin toolset:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync mcp-litellm \
  --tool-profile platform_admin \
  --disable-tool litellm_config_admin
```

Run with only discovery plus the generic escape hatch:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync mcp-litellm \
  --tool-profile none \
  --enable-tool litellm_list_routes,litellm_route_details,litellm_native_request
```

Run as streamable HTTP:

```bash
.venv/bin/mcp-litellm --transport streamable-http --host 127.0.0.1 --port 8000
```

## Verify

```bash
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/vulture
.venv/bin/pytest
pre-commit run --all-files
```
