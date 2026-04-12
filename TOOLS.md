# Tool Reference

This file documents every MCP tool that `mcp-litellm` can expose.

## Tool Loading Profiles

The server does not need to expose the full tool catalog on every startup.

- Default profile: `core`
- Profile env var: `MCP_LITELLM_TOOL_PROFILES`
- Explicit allowlist override: `MCP_LITELLM_ENABLE_TOOLS`
- Explicit denylist override: `MCP_LITELLM_DISABLE_TOOLS`
- CLI equivalents:
  - `--tool-profile`
  - `--enable-tool`
  - `--disable-tool`

Resolution order:

1. Start with the selected `tool_profiles`
2. Add any `enable_tools`
3. Remove any `disable_tools`

Available profiles:

| Profile | Intent | Tools |
|---|---|---|
| `none` | Start empty and opt in explicitly. | none |
| `discovery` | Route discovery only. | `litellm_list_routes`, `litellm_route_details` |
| `catalog` | Model-catalog discovery. | `litellm_models_catalog` |
| `access_admin` | Keys and teams. | `litellm_keys`, `litellm_teams` |
| `identity_admin` | Users, orgs, projects, customers, credentials. | `litellm_identities`, `litellm_auth_admin` |
| `spend_admin` | Budgets, spend, exports, compliance. | `litellm_budgets_spend`, `litellm_exports_audit` |
| `runtime_ops` | Health, cache, router, callbacks, fallbacks. | `litellm_runtime` |
| `governance` | Prompts, policies, guardrails, tool policy. | `litellm_governance` |
| `search_rag` | Search tools and RAG endpoints. | `litellm_search_rag` |
| `mcp_admin` | LiteLLM MCP registry and bridge admin. | `litellm_mcp_admin` |
| `config_admin` | Proxy, SSO, UI, vault, pass-through endpoint config. | `litellm_config_admin` |
| `native_escape_hatch` | Discovery plus generic native route calls. | `litellm_list_routes`, `litellm_route_details`, `litellm_native_request` |
| `core` | Compact default for common LiteLLM administration. | `litellm_list_routes`, `litellm_route_details`, `litellm_models_catalog`, `litellm_keys`, `litellm_teams`, `litellm_runtime` |
| `platform_admin` | Broad platform administration without the escape hatch. | `litellm_list_routes`, `litellm_route_details`, `litellm_models_catalog`, `litellm_models_admin`, `litellm_keys`, `litellm_teams`, `litellm_identities`, `litellm_auth_admin`, `litellm_runtime`, `litellm_config_admin` |
| `full` | All implemented MCP tools. | every tool in this file |

Use `litellm://tools/active` to inspect the exact toolset that a running server instance resolved.

## Shared Family-Tool Parameters

The family tools all share the same request shape.

| Param | Type | Required | Intent |
|---|---|---:|---|
| `action` | `string` | yes | Selects the LiteLLM-native operation within the family tool. |
| `path_params` | `object<string, string>` | no | Values for path placeholders such as `{team_id}` or `{policy_id}`. |
| `query` | `object` | no | Query-string parameters passed through to LiteLLM. |
| `body` | `object | array | string | number | boolean | null` | no | JSON request body. For multipart requests this must be an object. |
| `multipart_files` | `array<object>` | no | Local file uploads. Each item supports `field_name`, `path`, optional `filename`, optional `content_type`. |

## Discovery And Escape-Hatch Tools

### `litellm_list_routes`

- Intent: Discover route keys known to this server before using `litellm_native_request`.
- Params:
  - `classification`: optional route classification filter. One of `typed`, `generic_native`, `alias`, `excluded_pass_through`, `excluded_protocol`.
  - `prefix`: optional path prefix filter such as `/team`, `/guardrails`, or `/v1/mcp`.

### `litellm_route_details`

- Intent: Inspect a single route key and see its method, path, tags, classification, and LiteLLM operation id.
- Params:
  - `route_key`: exact route key in `METHOD /path` form.

### `litellm://tools/active`

- Intent: Resource showing the resolved startup profiles, explicit includes/excludes, and active tools for the current server process.

### `litellm_native_request`

- Intent: Call any allowlisted LiteLLM-native route directly without writing custom Python.
- Params:
  - `route_key`: exact route key in `METHOD /path` form.
  - `path_params`, `query`, `body`, `multipart_files`: same semantics as the family tools.
- Scope:
  - Allowed: `typed`, `generic_native`
  - Blocked: `alias`, `excluded_pass_through`, `excluded_protocol`

## Family Tools

### `litellm_models_catalog`

- Intent: Read model discovery, model metadata, and public catalog endpoints.
- Actions:
  - `list_models`
  - `get_model`
  - `model_info`
  - `public_model_hub`
  - `public_model_hub_info`
  - `public_cost_map`
  - `public_providers`
  - `public_provider_fields`
  - `public_endpoints`

### `litellm_models_admin`

- Intent: Manage models, access groups, and model-group visibility.
- Actions:
  - `create_model`
  - `update_model`
  - `patch_model`
  - `delete_model`
  - `create_access_group`
  - `list_access_groups`
  - `get_access_group`
  - `update_access_group`
  - `delete_access_group`
  - `model_group_info`
  - `model_group_make_public`

### `litellm_keys`

- Intent: Manage LiteLLM virtual keys and service-account keys.
- Actions:
  - `create_key`
  - `create_service_account_key`
  - `update_key`
  - `bulk_update_keys`
  - `delete_key`
  - `get_key`
  - `list_keys`
  - `list_key_aliases`
  - `regenerate_key`
  - `regenerate_key_by_value`
  - `reset_key_spend`
  - `block_key`
  - `unblock_key`
  - `key_health`

### `litellm_teams`

- Intent: Manage teams, memberships, permissions, team callbacks, and team model access.
- Actions:
  - `create_team`
  - `update_team`
  - `delete_team`
  - `get_team`
  - `list_teams`
  - `list_available_teams`
  - `add_member`
  - `update_member`
  - `delete_member`
  - `bulk_add_members`
  - `add_model`
  - `delete_model`
  - `list_permissions`
  - `update_permissions`
  - `daily_activity`
  - `get_callbacks`
  - `add_callbacks`
  - `disable_logging`

### `litellm_identities`

- Intent: Manage internal users, organizations, projects, and customer records.
- Actions:
  - `create_user`
  - `get_user`
  - `update_user`
  - `bulk_update_users`
  - `list_users`
  - `delete_user`
  - `user_daily_activity`
  - `user_daily_activity_aggregated`
  - `available_users`
  - `create_organization`
  - `update_organization`
  - `delete_organization`
  - `list_organizations`
  - `get_organization`
  - `organization_daily_activity`
  - `organization_add_member`
  - `organization_update_member`
  - `organization_delete_member`
  - `create_project`
  - `update_project`
  - `delete_project`
  - `get_project`
  - `list_projects`
  - `create_customer`
  - `get_customer`
  - `update_customer`
  - `delete_customer`
  - `list_customers`
  - `block_customer`
  - `unblock_customer`
  - `customer_daily_activity`

### `litellm_budgets_spend`

- Intent: Work with budgets, spend analytics, cost estimation, tags, provider budgets, and IP allowlists.
- Actions:
  - `create_budget`
  - `update_budget`
  - `get_budget`
  - `list_budgets`
  - `delete_budget`
  - `budget_settings`
  - `spend_tags`
  - `spend_calculate`
  - `spend_logs`
  - `spend_logs_v2`
  - `global_spend_report`
  - `global_spend_tags`
  - `global_spend_reset`
  - `provider_budgets`
  - `create_tag`
  - `update_tag`
  - `get_tag`
  - `list_tags`
  - `delete_tag`
  - `tag_daily_activity`
  - `tag_distinct`
  - `tag_dau`
  - `tag_wau`
  - `tag_mau`
  - `tag_summary`
  - `tag_per_user_analytics`
  - `cost_estimate`
  - `usage_ai_chat`
  - `add_allowed_ip`
  - `delete_allowed_ip`
  - `agent_daily_activity`

### `litellm_runtime`

- Intent: Inspect runtime health, cache state, callbacks, router settings, and fallback configuration.
- Actions:
  - `test`
  - `health`
  - `health_services`
  - `health_history`
  - `health_latest`
  - `health_shared_status`
  - `health_license`
  - `health_readiness`
  - `health_backlog`
  - `health_liveness`
  - `health_liveliness`
  - `health_test_connection`
  - `active_callbacks`
  - `settings`
  - `debug_asyncio_tasks`
  - `cache_ping`
  - `cache_delete`
  - `cache_redis_info`
  - `cache_flushall`
  - `get_cache_settings`
  - `update_cache_settings`
  - `test_cache_settings`
  - `list_callbacks`
  - `callback_configs`
  - `router_settings`
  - `router_fields`
  - `create_fallback`
  - `get_fallback`
  - `delete_fallback`

### `litellm_auth_admin`

- Intent: Manage stored credentials and JWT key mappings.
- Actions:
  - `list_credentials`
  - `create_credential`
  - `get_credential_by_name`
  - `get_credential_by_model`
  - `update_credential`
  - `delete_credential`
  - `create_jwt_key_mapping`
  - `update_jwt_key_mapping`
  - `delete_jwt_key_mapping`
  - `list_jwt_key_mappings`
  - `get_jwt_key_mapping`

### `litellm_governance`

- Intent: Manage prompts, policies, guardrails, and LiteLLM tool-policy settings.
- Actions:
  - `list_prompts`
  - `create_prompt`
  - `get_prompt`
  - `get_prompt_info`
  - `get_prompt_versions`
  - `update_prompt`
  - `patch_prompt`
  - `delete_prompt`
  - `test_prompt`
  - `policies_usage_overview`
  - `list_policies`
  - `create_policy`
  - `list_policy_versions`
  - `create_policy_version`
  - `update_policy_status`
  - `compare_policy_versions`
  - `get_policy`
  - `update_policy`
  - `delete_policy`
  - `delete_all_policy_versions`
  - `get_policy_resolved_guardrails`
  - `test_policy_pipeline`
  - `list_policy_attachments`
  - `create_policy_attachment`
  - `get_policy_attachment`
  - `delete_policy_attachment`
  - `resolve_policies`
  - `estimate_attachment_impact`
  - `validate_policy`
  - `list_legacy_policies`
  - `get_policy_info`
  - `test_policy_matching`
  - `get_policy_templates`
  - `enrich_policy_template`
  - `enrich_policy_template_stream`
  - `suggest_policy_templates`
  - `test_policy_template`
  - `list_guardrails`
  - `create_guardrail`
  - `get_guardrail`
  - `get_guardrail_info`
  - `update_guardrail`
  - `patch_guardrail`
  - `delete_guardrail`
  - `register_guardrail`
  - `list_guardrail_submissions`
  - `get_guardrail_submission`
  - `approve_guardrail_submission`
  - `reject_guardrail_submission`
  - `validate_blocked_words_file`
  - `get_guardrail_ui_settings`
  - `get_guardrail_category_yaml`
  - `get_guardrail_major_airlines`
  - `get_guardrail_provider_specific_params`
  - `test_custom_code_guardrail`
  - `apply_guardrail`
  - `guardrails_usage_overview`
  - `guardrails_usage_detail`
  - `guardrails_usage_logs`
  - `get_tool_policy_options`
  - `list_tools`
  - `get_tool_detail`
  - `get_tool`
  - `get_tool_logs`
  - `update_tool_policy`
  - `delete_tool_policy_override`

### `litellm_search_rag`

- Intent: Manage LiteLLM search-tool configuration and RAG endpoints.
- Actions:
  - `list_search_tools`
  - `create_search_tool`
  - `get_search_tool`
  - `update_search_tool`
  - `delete_search_tool`
  - `test_search_tool_connection`
  - `get_search_tool_providers`
  - `search`
  - `search_named`
  - `list_search_backends`
  - `rag_ingest`
  - `rag_query`

### `litellm_mcp_admin`

- Intent: Manage LiteLLM's MCP registry, MCP user credentials, discovery endpoints, and the MCP REST bridge.
- Actions:
  - `list_mcp_tools`
  - `list_mcp_access_groups`
  - `get_mcp_client_ip`
  - `get_mcp_registry`
  - `list_mcp_servers`
  - `add_mcp_server`
  - `edit_mcp_server`
  - `mcp_server_health`
  - `register_mcp_server`
  - `list_mcp_submissions`
  - `approve_mcp_submission`
  - `reject_mcp_submission`
  - `get_mcp_server`
  - `delete_mcp_server`
  - `add_mcp_oauth_session`
  - `store_mcp_user_credential`
  - `delete_mcp_user_credential`
  - `store_mcp_oauth_user_credential`
  - `delete_mcp_oauth_user_credential`
  - `get_mcp_oauth_credential_status`
  - `list_mcp_user_credentials`
  - `make_mcp_public`
  - `discover_mcp_servers`
  - `get_mcp_openapi_registry`
  - `list_mcp_rest_tools`
  - `call_mcp_rest_tool`
  - `test_mcp_rest_connection`
  - `test_mcp_rest_list_tools`
  - `public_mcp_hub`
  - `get_mcp_semantic_filter_settings`
  - `update_mcp_semantic_filter_settings`

### `litellm_config_admin`

- Intent: Manage pass-through endpoint config, cost config, vault overrides, SSO settings, UI settings, and email settings.
- Actions:
  - `list_pass_through_endpoints`
  - `list_team_pass_through_endpoints`
  - `create_pass_through_endpoint`
  - `update_pass_through_endpoint`
  - `delete_pass_through_endpoint`
  - `get_cost_discount_config`
  - `update_cost_discount_config`
  - `get_cost_margin_config`
  - `update_cost_margin_config`
  - `get_hashicorp_vault_config`
  - `update_hashicorp_vault_config`
  - `delete_hashicorp_vault_config`
  - `test_hashicorp_vault_connection`
  - `get_internal_user_settings`
  - `update_internal_user_settings`
  - `get_default_team_settings`
  - `update_default_team_settings`
  - `get_sso_settings`
  - `update_sso_settings`
  - `sso_readiness`
  - `get_ui_theme_settings`
  - `update_ui_theme_settings`
  - `get_ui_settings`
  - `update_ui_settings`
  - `get_email_event_settings`
  - `update_email_event_settings`
  - `reset_email_event_settings`
  - `upload_logo`
  - `in_product_nudges`

### `litellm_exports_audit`

- Intent: Manage CloudZero and Vantage exports, audit logs, and compliance checks.
- Actions:
  - `get_cloudzero_settings`
  - `update_cloudzero_settings`
  - `init_cloudzero`
  - `cloudzero_dry_run`
  - `cloudzero_export`
  - `delete_cloudzero_settings`
  - `get_vantage_settings`
  - `update_vantage_settings`
  - `init_vantage`
  - `vantage_dry_run`
  - `vantage_export`
  - `delete_vantage_settings`
  - `list_audit_logs`
  - `get_audit_log`
  - `check_eu_ai_act`
  - `check_gdpr`

## Usage Notes

- Prefer the family tools when a matching action exists. They are the stable, intention-revealing interface.
- Use `litellm_list_routes` and `litellm_route_details` when you need to discover a route or confirm whether it is callable.
- Use `litellm_native_request` only for LiteLLM-native routes that do not yet have a first-class family action.
- Raw provider pass-through endpoints are intentionally excluded from `litellm_native_request`.
