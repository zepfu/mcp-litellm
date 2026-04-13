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
- A bundled vendored LiteLLM OpenAPI snapshot, overrideable via `MCP_LITELLM_OPENAPI_PATH`.
- A root [`TOOLS.md`](TOOLS.md) reference covering every MCP tool exposed by this server.

## Requirements

- Python `3.14`
- `uv`
- Access to a LiteLLM proxy endpoint

## Configuration

The server is configured from three sources:

1. `.env`
2. Environment variables prefixed with `MCP_LITELLM_`
3. CLI flags

CLI flags override environment-derived values. The `.env.example` file shows the
minimal baseline.

### Server Settings

| Setting | Env var | Default | Intent |
|---|---|---|---|
| `litellm_base_url` | `MCP_LITELLM_LITELLM_BASE_URL` | `http://127.0.0.1:4000` | Base URL for the LiteLLM proxy being wrapped. |
| `litellm_api_key` | `MCP_LITELLM_LITELLM_API_KEY` | unset | LiteLLM API key or proxy key. |
| `timeout_seconds` | `MCP_LITELLM_TIMEOUT_SECONDS` | `60.0` | Upstream LiteLLM request timeout. |
| `max_response_bytes` | `MCP_LITELLM_MAX_RESPONSE_BYTES` | `5000000` | Maximum upstream response body size accepted into MCP tool output. |
| `include_bearer_auth` | `MCP_LITELLM_INCLUDE_BEARER_AUTH` | `true` | Whether to send bearer auth when an API key is present. |
| `transport` | `MCP_LITELLM_TRANSPORT` | `stdio` | MCP transport: `stdio`, `sse`, or `streamable-http`. |
| `host` | `MCP_LITELLM_HOST` | `127.0.0.1` | Bind host for HTTP transports. |
| `port` | `MCP_LITELLM_PORT` | `8000` | Bind port for HTTP transports. |
| `mount_path` | `MCP_LITELLM_MOUNT_PATH` | `/` | Root mount path for HTTP transports. |
| `sse_path` | `MCP_LITELLM_SSE_PATH` | `/sse` | SSE endpoint path when using `sse`. |
| `message_path` | `MCP_LITELLM_MESSAGE_PATH` | `/messages/` | SSE message endpoint path. |
| `streamable_http_path` | `MCP_LITELLM_STREAMABLE_HTTP_PATH` | `/mcp` | Streamable HTTP endpoint path. |
| `openapi_path` | `MCP_LITELLM_OPENAPI_PATH` | bundled package snapshot | LiteLLM OpenAPI snapshot to load. |
| `tool_profiles` | `MCP_LITELLM_TOOL_PROFILES` | `core` | Base startup toolset profile list. |
| `enable_tools` | `MCP_LITELLM_ENABLE_TOOLS` | empty | Individual tool names to add after profile resolution. |
| `disable_tools` | `MCP_LITELLM_DISABLE_TOOLS` | empty | Individual tool names to remove after profile resolution. |

### CLI Flags

The entrypoint also accepts these runtime overrides:

| Flag | Intent |
|---|---|
| `--transport` | Override the MCP transport. |
| `--host` | Override the HTTP bind host. |
| `--port` | Override the HTTP bind port. |
| `--tool-profile` | Add one or more tool profiles. Repeat the flag or pass a comma-separated list. |
| `--enable-tool` | Force-enable one or more individual tools. |
| `--disable-tool` | Disable one or more individual tools after all enables are applied. |

### Example `.env`

```dotenv
MCP_LITELLM_LITELLM_BASE_URL=http://127.0.0.1:4000
MCP_LITELLM_LITELLM_API_KEY=sk-your-litellm-key
MCP_LITELLM_TRANSPORT=stdio
MCP_LITELLM_MAX_RESPONSE_BYTES=5000000
MCP_LITELLM_TOOL_PROFILES=core
MCP_LITELLM_ENABLE_TOOLS=
MCP_LITELLM_DISABLE_TOOLS=
```

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

## Client Launch Configuration

For `stdio` MCP clients, configure the client to launch `mcp-litellm` with the
desired environment and tool flags for that client instance.

Example `Codex` config:

```toml
[mcp_servers.litellm]
command = "env"
args = [
  "UV_CACHE_DIR=/tmp/uv-cache",
  "MCP_LITELLM_LITELLM_BASE_URL=http://127.0.0.1:4000",
  "MCP_LITELLM_LITELLM_API_KEY=sk-your-litellm-key",
  "uv",
  "run",
  "--directory",
  "/absolute/path/to/mcp-litellm",
  "--no-sync",
  "mcp-litellm",
  "--tool-profile",
  "platform_admin",
  "--disable-tool",
  "litellm_config_admin",
]
```

That same pattern applies to other `stdio` MCP clients: point them at the
server command, pass the LiteLLM connection settings, and narrow the toolset
with profiles and explicit tool flags.

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
