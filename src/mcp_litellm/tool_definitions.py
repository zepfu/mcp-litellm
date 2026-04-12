"""Curated MCP family-tool definitions for LiteLLM-native workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mcp_litellm.route_catalog import route_key
from mcp_litellm.service import ActionSpec

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Metadata describing a first-class MCP family tool."""

    name: str
    description: str
    actions: dict[str, ActionSpec]


@dataclass(frozen=True, slots=True)
class ToolProfile:
    """Metadata describing a startup-time tool-loading profile."""

    name: str
    description: str
    tools: frozenset[str]


def _action(method: str, path: str) -> ActionSpec:
    return ActionSpec(route_key=route_key(method, path))


TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="litellm_models_catalog",
        description=(
            "Inspect LiteLLM model discovery and public catalog endpoints. "
            "Actions: list_models, get_model, model_info, public_model_hub, "
            "public_model_hub_info, public_cost_map, public_providers, "
            "public_provider_fields, public_endpoints."
        ),
        actions={
            "list_models": _action("GET", "/models"),
            "get_model": _action("GET", "/models/{model_id}"),
            "model_info": _action("GET", "/model/info"),
            "public_model_hub": _action("GET", "/public/model_hub"),
            "public_model_hub_info": _action("GET", "/public/model_hub/info"),
            "public_cost_map": _action("GET", "/public/litellm_model_cost_map"),
            "public_providers": _action("GET", "/public/providers"),
            "public_provider_fields": _action("GET", "/public/providers/fields"),
            "public_endpoints": _action("GET", "/public/endpoints"),
        },
    ),
    ToolSpec(
        name="litellm_models_admin",
        description=(
            "Manage LiteLLM models and access groups. Actions: create_model, update_model, "
            "patch_model, delete_model, create_access_group, list_access_groups, "
            "get_access_group, update_access_group, delete_access_group, model_group_info, "
            "model_group_make_public."
        ),
        actions={
            "create_model": _action("POST", "/model/new"),
            "update_model": _action("POST", "/model/update"),
            "patch_model": _action("PATCH", "/model/{model_id}/update"),
            "delete_model": _action("POST", "/model/delete"),
            "create_access_group": _action("POST", "/access_group/new"),
            "list_access_groups": _action("GET", "/access_group/list"),
            "get_access_group": _action("GET", "/access_group/{access_group}/info"),
            "update_access_group": _action("PUT", "/access_group/{access_group}/update"),
            "delete_access_group": _action("DELETE", "/access_group/{access_group}/delete"),
            "model_group_info": _action("GET", "/model_group/info"),
            "model_group_make_public": _action("POST", "/model_group/make_public"),
        },
    ),
    ToolSpec(
        name="litellm_keys",
        description=(
            "Manage LiteLLM virtual keys. Actions: create_key, create_service_account_key, "
            "update_key, bulk_update_keys, delete_key, get_key, list_keys, list_key_aliases, "
            "regenerate_key, regenerate_key_by_value, reset_key_spend, block_key, unblock_key, "
            "key_health."
        ),
        actions={
            "create_key": _action("POST", "/key/generate"),
            "create_service_account_key": _action("POST", "/key/service-account/generate"),
            "update_key": _action("POST", "/key/update"),
            "bulk_update_keys": _action("POST", "/key/bulk_update"),
            "delete_key": _action("POST", "/key/delete"),
            "get_key": _action("GET", "/key/info"),
            "list_keys": _action("GET", "/key/list"),
            "list_key_aliases": _action("GET", "/key/aliases"),
            "regenerate_key": _action("POST", "/key/regenerate"),
            "regenerate_key_by_value": _action("POST", "/key/{key}/regenerate"),
            "reset_key_spend": _action("POST", "/key/{key}/reset_spend"),
            "block_key": _action("POST", "/key/block"),
            "unblock_key": _action("POST", "/key/unblock"),
            "key_health": _action("POST", "/key/health"),
        },
    ),
    ToolSpec(
        name="litellm_teams",
        description=(
            "Manage LiteLLM teams, memberships, team model access, and callbacks. "
            "Actions: create_team, update_team, delete_team, get_team, list_teams, "
            "list_available_teams, add_member, update_member, delete_member, bulk_add_members, "
            "add_model, delete_model, list_permissions, update_permissions, daily_activity, "
            "get_callbacks, add_callbacks, disable_logging."
        ),
        actions={
            "create_team": _action("POST", "/team/new"),
            "update_team": _action("POST", "/team/update"),
            "delete_team": _action("POST", "/team/delete"),
            "get_team": _action("GET", "/team/info"),
            "list_teams": _action("GET", "/team/list"),
            "list_available_teams": _action("GET", "/team/available"),
            "add_member": _action("POST", "/team/member_add"),
            "update_member": _action("POST", "/team/member_update"),
            "delete_member": _action("POST", "/team/member_delete"),
            "bulk_add_members": _action("POST", "/team/bulk_member_add"),
            "add_model": _action("POST", "/team/model/add"),
            "delete_model": _action("POST", "/team/model/delete"),
            "list_permissions": _action("GET", "/team/permissions_list"),
            "update_permissions": _action("POST", "/team/permissions_update"),
            "daily_activity": _action("GET", "/team/daily/activity"),
            "get_callbacks": _action("GET", "/team/{team_id}/callback"),
            "add_callbacks": _action("POST", "/team/{team_id}/callback"),
            "disable_logging": _action("POST", "/team/{team_id}/disable_logging"),
        },
    ),
    ToolSpec(
        name="litellm_identities",
        description=(
            "Manage users, organizations, projects, and customers. Actions include "
            "create_user, get_user, update_user, bulk_update_users, list_users, delete_user, "
            "user_daily_activity, user_daily_activity_aggregated, available_users, "
            "create_organization, update_organization, delete_organization, list_organizations, "
            "get_organization, organization_daily_activity, organization_add_member, "
            "organization_update_member, organization_delete_member, create_project, "
            "update_project, delete_project, get_project, list_projects, create_customer, "
            "get_customer, update_customer, delete_customer, list_customers, block_customer, "
            "unblock_customer, customer_daily_activity."
        ),
        actions={
            "create_user": _action("POST", "/user/new"),
            "get_user": _action("GET", "/user/info"),
            "update_user": _action("POST", "/user/update"),
            "bulk_update_users": _action("POST", "/user/bulk_update"),
            "list_users": _action("GET", "/user/list"),
            "delete_user": _action("POST", "/user/delete"),
            "user_daily_activity": _action("GET", "/user/daily/activity"),
            "user_daily_activity_aggregated": _action("GET", "/user/daily/activity/aggregated"),
            "available_users": _action("GET", "/user/available_users"),
            "create_organization": _action("POST", "/organization/new"),
            "update_organization": _action("PATCH", "/organization/update"),
            "delete_organization": _action("DELETE", "/organization/delete"),
            "list_organizations": _action("GET", "/organization/list"),
            "get_organization": _action("POST", "/organization/info"),
            "organization_daily_activity": _action("GET", "/organization/daily/activity"),
            "organization_add_member": _action("POST", "/organization/member_add"),
            "organization_update_member": _action("PATCH", "/organization/member_update"),
            "organization_delete_member": _action("DELETE", "/organization/member_delete"),
            "create_project": _action("POST", "/project/new"),
            "update_project": _action("POST", "/project/update"),
            "delete_project": _action("DELETE", "/project/delete"),
            "get_project": _action("GET", "/project/info"),
            "list_projects": _action("GET", "/project/list"),
            "create_customer": _action("POST", "/customer/new"),
            "get_customer": _action("GET", "/customer/info"),
            "update_customer": _action("POST", "/customer/update"),
            "delete_customer": _action("POST", "/customer/delete"),
            "list_customers": _action("GET", "/customer/list"),
            "block_customer": _action("POST", "/customer/block"),
            "unblock_customer": _action("POST", "/customer/unblock"),
            "customer_daily_activity": _action("GET", "/customer/daily/activity"),
        },
    ),
    ToolSpec(
        name="litellm_budgets_spend",
        description=(
            "Manage budgets, spend tracking, tags, cost estimation, and IP allowlists. "
            "Actions: create_budget, update_budget, get_budget, list_budgets, delete_budget, "
            "budget_settings, spend_tags, spend_calculate, spend_logs, spend_logs_v2, "
            "global_spend_report, global_spend_tags, global_spend_reset, provider_budgets, "
            "create_tag, update_tag, get_tag, list_tags, delete_tag, tag_daily_activity, "
            "tag_distinct, tag_dau, tag_wau, tag_mau, tag_summary, tag_per_user_analytics, "
            "cost_estimate, usage_ai_chat, add_allowed_ip, delete_allowed_ip, agent_daily_activity."
        ),
        actions={
            "create_budget": _action("POST", "/budget/new"),
            "update_budget": _action("POST", "/budget/update"),
            "get_budget": _action("POST", "/budget/info"),
            "list_budgets": _action("GET", "/budget/list"),
            "delete_budget": _action("POST", "/budget/delete"),
            "budget_settings": _action("GET", "/budget/settings"),
            "spend_tags": _action("GET", "/spend/tags"),
            "spend_calculate": _action("POST", "/spend/calculate"),
            "spend_logs": _action("GET", "/spend/logs"),
            "spend_logs_v2": _action("GET", "/spend/logs/v2"),
            "global_spend_report": _action("GET", "/global/spend/report"),
            "global_spend_tags": _action("GET", "/global/spend/tags"),
            "global_spend_reset": _action("POST", "/global/spend/reset"),
            "provider_budgets": _action("GET", "/provider/budgets"),
            "create_tag": _action("POST", "/tag/new"),
            "update_tag": _action("POST", "/tag/update"),
            "get_tag": _action("POST", "/tag/info"),
            "list_tags": _action("GET", "/tag/list"),
            "delete_tag": _action("POST", "/tag/delete"),
            "tag_daily_activity": _action("GET", "/tag/daily/activity"),
            "tag_distinct": _action("GET", "/tag/distinct"),
            "tag_dau": _action("GET", "/tag/dau"),
            "tag_wau": _action("GET", "/tag/wau"),
            "tag_mau": _action("GET", "/tag/mau"),
            "tag_summary": _action("GET", "/tag/summary"),
            "tag_per_user_analytics": _action("GET", "/tag/user-agent/per-user-analytics"),
            "cost_estimate": _action("POST", "/cost/estimate"),
            "usage_ai_chat": _action("POST", "/usage/ai/chat"),
            "add_allowed_ip": _action("POST", "/add/allowed_ip"),
            "delete_allowed_ip": _action("POST", "/delete/allowed_ip"),
            "agent_daily_activity": _action("GET", "/agent/daily/activity"),
        },
    ),
    ToolSpec(
        name="litellm_runtime",
        description=(
            "Inspect health, cache, router, callback, and fallback runtime state. "
            "Actions: test, health, health_services, health_history, health_latest, "
            "health_shared_status, health_license, health_readiness, health_backlog, "
            "health_liveness, health_liveliness, health_test_connection, active_callbacks, "
            "settings, debug_asyncio_tasks, cache_ping, cache_delete, cache_redis_info, "
            "cache_flushall, get_cache_settings, update_cache_settings, test_cache_settings, "
            "list_callbacks, callback_configs, router_settings, router_fields, create_fallback, "
            "get_fallback, delete_fallback."
        ),
        actions={
            "test": _action("GET", "/test"),
            "health": _action("GET", "/health"),
            "health_services": _action("GET", "/health/services"),
            "health_history": _action("GET", "/health/history"),
            "health_latest": _action("GET", "/health/latest"),
            "health_shared_status": _action("GET", "/health/shared-status"),
            "health_license": _action("GET", "/health/license"),
            "health_readiness": _action("GET", "/health/readiness"),
            "health_backlog": _action("GET", "/health/backlog"),
            "health_liveness": _action("GET", "/health/liveness"),
            "health_liveliness": _action("GET", "/health/liveliness"),
            "health_test_connection": _action("POST", "/health/test_connection"),
            "active_callbacks": _action("GET", "/active/callbacks"),
            "settings": _action("GET", "/settings"),
            "debug_asyncio_tasks": _action("GET", "/debug/asyncio-tasks"),
            "cache_ping": _action("GET", "/cache/ping"),
            "cache_delete": _action("POST", "/cache/delete"),
            "cache_redis_info": _action("GET", "/cache/redis/info"),
            "cache_flushall": _action("POST", "/cache/flushall"),
            "get_cache_settings": _action("GET", "/cache/settings"),
            "update_cache_settings": _action("POST", "/cache/settings"),
            "test_cache_settings": _action("POST", "/cache/settings/test"),
            "list_callbacks": _action("GET", "/callbacks/list"),
            "callback_configs": _action("GET", "/callbacks/configs"),
            "router_settings": _action("GET", "/router/settings"),
            "router_fields": _action("GET", "/router/fields"),
            "create_fallback": _action("POST", "/fallback"),
            "get_fallback": _action("GET", "/fallback/{model}"),
            "delete_fallback": _action("DELETE", "/fallback/{model}"),
        },
    ),
    ToolSpec(
        name="litellm_auth_admin",
        description=(
            "Manage stored credentials and JWT key mappings. Actions: list_credentials, "
            "create_credential, get_credential_by_name, get_credential_by_model, "
            "update_credential, delete_credential, create_jwt_key_mapping, "
            "update_jwt_key_mapping, delete_jwt_key_mapping, list_jwt_key_mappings, "
            "get_jwt_key_mapping."
        ),
        actions={
            "list_credentials": _action("GET", "/credentials"),
            "create_credential": _action("POST", "/credentials"),
            "get_credential_by_name": _action("GET", "/credentials/by_name/{credential_name}"),
            "get_credential_by_model": _action("GET", "/credentials/by_model/{model_id}"),
            "update_credential": _action("PATCH", "/credentials/{credential_name}"),
            "delete_credential": _action("DELETE", "/credentials/{credential_name}"),
            "create_jwt_key_mapping": _action("POST", "/jwt/key/mapping/new"),
            "update_jwt_key_mapping": _action("POST", "/jwt/key/mapping/update"),
            "delete_jwt_key_mapping": _action("POST", "/jwt/key/mapping/delete"),
            "list_jwt_key_mappings": _action("GET", "/jwt/key/mapping/list"),
            "get_jwt_key_mapping": _action("GET", "/jwt/key/mapping/info"),
        },
    ),
    ToolSpec(
        name="litellm_governance",
        description=(
            "Manage prompts, policies, guardrails, and tool policy settings. Actions include "
            "list_prompts, create_prompt, get_prompt, get_prompt_info, get_prompt_versions, "
            "update_prompt, patch_prompt, delete_prompt, test_prompt, policies_usage_overview, "
            "list_policies, create_policy, list_policy_versions, create_policy_version, "
            "update_policy_status, compare_policy_versions, get_policy, update_policy, "
            "delete_policy, delete_all_policy_versions, get_policy_resolved_guardrails, "
            "test_policy_pipeline, list_policy_attachments, create_policy_attachment, "
            "get_policy_attachment, delete_policy_attachment, resolve_policies, "
            "estimate_attachment_impact, validate_policy, list_legacy_policies, "
            "get_policy_info, test_policy_matching, get_policy_templates, "
            "enrich_policy_template, enrich_policy_template_stream, suggest_policy_templates, "
            "test_policy_template, list_guardrails, create_guardrail, get_guardrail, "
            "get_guardrail_info, update_guardrail, patch_guardrail, delete_guardrail, "
            "register_guardrail, list_guardrail_submissions, get_guardrail_submission, "
            "approve_guardrail_submission, reject_guardrail_submission, "
            "validate_blocked_words_file, get_guardrail_ui_settings, get_guardrail_category_yaml, "
            "get_guardrail_major_airlines, get_guardrail_provider_specific_params, "
            "test_custom_code_guardrail, apply_guardrail, guardrails_usage_overview, "
            "guardrails_usage_detail, guardrails_usage_logs, get_tool_policy_options, "
            "list_tools, get_tool_detail, get_tool, get_tool_logs, update_tool_policy, "
            "delete_tool_policy_override."
        ),
        actions={
            "list_prompts": _action("GET", "/prompts/list"),
            "create_prompt": _action("POST", "/prompts"),
            "get_prompt": _action("GET", "/prompts/{prompt_id}"),
            "get_prompt_info": _action("GET", "/prompts/{prompt_id}/info"),
            "get_prompt_versions": _action("GET", "/prompts/{prompt_id}/versions"),
            "update_prompt": _action("PUT", "/prompts/{prompt_id}"),
            "patch_prompt": _action("PATCH", "/prompts/{prompt_id}"),
            "delete_prompt": _action("DELETE", "/prompts/{prompt_id}"),
            "test_prompt": _action("POST", "/prompts/test"),
            "policies_usage_overview": _action("GET", "/policies/usage/overview"),
            "list_policies": _action("GET", "/policies/list"),
            "create_policy": _action("POST", "/policies"),
            "list_policy_versions": _action("GET", "/policies/name/{policy_name}/versions"),
            "create_policy_version": _action("POST", "/policies/name/{policy_name}/versions"),
            "update_policy_status": _action("PUT", "/policies/{policy_id}/status"),
            "compare_policy_versions": _action("GET", "/policies/compare"),
            "get_policy": _action("GET", "/policies/{policy_id}"),
            "update_policy": _action("PUT", "/policies/{policy_id}"),
            "delete_policy": _action("DELETE", "/policies/{policy_id}"),
            "delete_all_policy_versions": _action("DELETE", "/policies/name/{policy_name}/all-versions"),
            "get_policy_resolved_guardrails": _action("GET", "/policies/{policy_id}/resolved-guardrails"),
            "test_policy_pipeline": _action("POST", "/policies/test-pipeline"),
            "list_policy_attachments": _action("GET", "/policies/attachments/list"),
            "create_policy_attachment": _action("POST", "/policies/attachments"),
            "get_policy_attachment": _action("GET", "/policies/attachments/{attachment_id}"),
            "delete_policy_attachment": _action("DELETE", "/policies/attachments/{attachment_id}"),
            "resolve_policies": _action("POST", "/policies/resolve"),
            "estimate_attachment_impact": _action("POST", "/policies/attachments/estimate-impact"),
            "validate_policy": _action("POST", "/policy/validate"),
            "list_legacy_policies": _action("GET", "/policy/list"),
            "get_policy_info": _action("GET", "/policy/info/{policy_name}"),
            "test_policy_matching": _action("POST", "/policy/test"),
            "get_policy_templates": _action("GET", "/policy/templates"),
            "enrich_policy_template": _action("POST", "/policy/templates/enrich"),
            "enrich_policy_template_stream": _action("POST", "/policy/templates/enrich/stream"),
            "suggest_policy_templates": _action("POST", "/policy/templates/suggest"),
            "test_policy_template": _action("POST", "/policy/templates/test"),
            "list_guardrails": _action("GET", "/guardrails/list"),
            "create_guardrail": _action("POST", "/guardrails"),
            "get_guardrail": _action("GET", "/guardrails/{guardrail_id}"),
            "get_guardrail_info": _action("GET", "/guardrails/{guardrail_id}/info"),
            "update_guardrail": _action("PUT", "/guardrails/{guardrail_id}"),
            "patch_guardrail": _action("PATCH", "/guardrails/{guardrail_id}"),
            "delete_guardrail": _action("DELETE", "/guardrails/{guardrail_id}"),
            "register_guardrail": _action("POST", "/guardrails/register"),
            "list_guardrail_submissions": _action("GET", "/guardrails/submissions"),
            "get_guardrail_submission": _action("GET", "/guardrails/submissions/{guardrail_id}"),
            "approve_guardrail_submission": _action("POST", "/guardrails/submissions/{guardrail_id}/approve"),
            "reject_guardrail_submission": _action("POST", "/guardrails/submissions/{guardrail_id}/reject"),
            "validate_blocked_words_file": _action("POST", "/guardrails/validate_blocked_words_file"),
            "get_guardrail_ui_settings": _action("GET", "/guardrails/ui/add_guardrail_settings"),
            "get_guardrail_category_yaml": _action("GET", "/guardrails/ui/category_yaml/{category_name}"),
            "get_guardrail_major_airlines": _action("GET", "/guardrails/ui/major_airlines"),
            "get_guardrail_provider_specific_params": _action("GET", "/guardrails/ui/provider_specific_params"),
            "test_custom_code_guardrail": _action("POST", "/guardrails/test_custom_code"),
            "apply_guardrail": _action("POST", "/guardrails/apply_guardrail"),
            "guardrails_usage_overview": _action("GET", "/guardrails/usage/overview"),
            "guardrails_usage_detail": _action("GET", "/guardrails/usage/detail/{guardrail_id}"),
            "guardrails_usage_logs": _action("GET", "/guardrails/usage/logs"),
            "get_tool_policy_options": _action("GET", "/v1/tool/policy/options"),
            "list_tools": _action("GET", "/v1/tool/list"),
            "get_tool_detail": _action("GET", "/v1/tool/{tool_name}/detail"),
            "get_tool": _action("GET", "/v1/tool/{tool_name}"),
            "get_tool_logs": _action("GET", "/v1/tool/{tool_name}/logs"),
            "update_tool_policy": _action("POST", "/v1/tool/policy"),
            "delete_tool_policy_override": _action("DELETE", "/v1/tool/{tool_name}/overrides"),
        },
    ),
    ToolSpec(
        name="litellm_search_rag",
        description=(
            "Manage search tools and LiteLLM RAG endpoints. Actions: list_search_tools, "
            "create_search_tool, get_search_tool, update_search_tool, delete_search_tool, "
            "test_search_tool_connection, get_search_tool_providers, search, search_named, "
            "list_search_backends, rag_ingest, rag_query."
        ),
        actions={
            "list_search_tools": _action("GET", "/search_tools/list"),
            "create_search_tool": _action("POST", "/search_tools"),
            "get_search_tool": _action("GET", "/search_tools/{search_tool_id}"),
            "update_search_tool": _action("PUT", "/search_tools/{search_tool_id}"),
            "delete_search_tool": _action("DELETE", "/search_tools/{search_tool_id}"),
            "test_search_tool_connection": _action("POST", "/search_tools/test_connection"),
            "get_search_tool_providers": _action("GET", "/search_tools/ui/available_providers"),
            "search": _action("POST", "/search"),
            "search_named": _action("POST", "/search/{search_tool_name}"),
            "list_search_backends": _action("GET", "/search/tools"),
            "rag_ingest": _action("POST", "/rag/ingest"),
            "rag_query": _action("POST", "/rag/query"),
        },
    ),
    ToolSpec(
        name="litellm_mcp_admin",
        description=(
            "Manage LiteLLM's MCP registry, MCP REST bridge, and MCP-related settings. "
            "Actions: list_mcp_tools, list_mcp_access_groups, get_mcp_client_ip, "
            "get_mcp_registry, list_mcp_servers, add_mcp_server, edit_mcp_server, "
            "mcp_server_health, register_mcp_server, list_mcp_submissions, "
            "approve_mcp_submission, reject_mcp_submission, get_mcp_server, delete_mcp_server, "
            "add_mcp_oauth_session, store_mcp_user_credential, delete_mcp_user_credential, "
            "store_mcp_oauth_user_credential, delete_mcp_oauth_user_credential, "
            "get_mcp_oauth_credential_status, list_mcp_user_credentials, make_mcp_public, "
            "discover_mcp_servers, get_mcp_openapi_registry, list_mcp_rest_tools, "
            "call_mcp_rest_tool, test_mcp_rest_connection, test_mcp_rest_list_tools, "
            "public_mcp_hub, get_mcp_semantic_filter_settings, update_mcp_semantic_filter_settings."
        ),
        actions={
            "list_mcp_tools": _action("GET", "/v1/mcp/tools"),
            "list_mcp_access_groups": _action("GET", "/v1/mcp/access_groups"),
            "get_mcp_client_ip": _action("GET", "/v1/mcp/network/client-ip"),
            "get_mcp_registry": _action("GET", "/v1/mcp/registry.json"),
            "list_mcp_servers": _action("GET", "/v1/mcp/server"),
            "add_mcp_server": _action("POST", "/v1/mcp/server"),
            "edit_mcp_server": _action("PUT", "/v1/mcp/server"),
            "mcp_server_health": _action("GET", "/v1/mcp/server/health"),
            "register_mcp_server": _action("POST", "/v1/mcp/server/register"),
            "list_mcp_submissions": _action("GET", "/v1/mcp/server/submissions"),
            "approve_mcp_submission": _action("PUT", "/v1/mcp/server/{server_id}/approve"),
            "reject_mcp_submission": _action("PUT", "/v1/mcp/server/{server_id}/reject"),
            "get_mcp_server": _action("GET", "/v1/mcp/server/{server_id}"),
            "delete_mcp_server": _action("DELETE", "/v1/mcp/server/{server_id}"),
            "add_mcp_oauth_session": _action("POST", "/v1/mcp/server/oauth/session"),
            "store_mcp_user_credential": _action("POST", "/v1/mcp/server/{server_id}/user-credential"),
            "delete_mcp_user_credential": _action("DELETE", "/v1/mcp/server/{server_id}/user-credential"),
            "store_mcp_oauth_user_credential": _action("POST", "/v1/mcp/server/{server_id}/oauth-user-credential"),
            "delete_mcp_oauth_user_credential": _action("DELETE", "/v1/mcp/server/{server_id}/oauth-user-credential"),
            "get_mcp_oauth_credential_status": _action("GET", "/v1/mcp/server/{server_id}/oauth-user-credential/status"),
            "list_mcp_user_credentials": _action("GET", "/v1/mcp/user-credentials"),
            "make_mcp_public": _action("POST", "/v1/mcp/make_public"),
            "discover_mcp_servers": _action("GET", "/v1/mcp/discover"),
            "get_mcp_openapi_registry": _action("GET", "/v1/mcp/openapi-registry"),
            "list_mcp_rest_tools": _action("GET", "/mcp-rest/tools/list"),
            "call_mcp_rest_tool": _action("POST", "/mcp-rest/tools/call"),
            "test_mcp_rest_connection": _action("POST", "/mcp-rest/test/connection"),
            "test_mcp_rest_list_tools": _action("POST", "/mcp-rest/test/tools/list"),
            "public_mcp_hub": _action("GET", "/public/mcp_hub"),
            "get_mcp_semantic_filter_settings": _action("GET", "/get/mcp_semantic_filter_settings"),
            "update_mcp_semantic_filter_settings": _action("PATCH", "/update/mcp_semantic_filter_settings"),
        },
    ),
    ToolSpec(
        name="litellm_config_admin",
        description=(
            "Manage proxy configuration and UI/SSO settings. Actions: list_pass_through_endpoints, "
            "list_team_pass_through_endpoints, create_pass_through_endpoint, update_pass_through_endpoint, "
            "delete_pass_through_endpoint, get_cost_discount_config, update_cost_discount_config, "
            "get_cost_margin_config, update_cost_margin_config, get_hashicorp_vault_config, "
            "update_hashicorp_vault_config, delete_hashicorp_vault_config, "
            "test_hashicorp_vault_connection, get_internal_user_settings, "
            "update_internal_user_settings, get_default_team_settings, update_default_team_settings, "
            "get_sso_settings, update_sso_settings, sso_readiness, get_ui_theme_settings, "
            "update_ui_theme_settings, get_ui_settings, update_ui_settings, get_email_event_settings, "
            "update_email_event_settings, reset_email_event_settings, upload_logo, in_product_nudges."
        ),
        actions={
            "list_pass_through_endpoints": _action("GET", "/config/pass_through_endpoint"),
            "list_team_pass_through_endpoints": _action("GET", "/config/pass_through_endpoint/team/{team_id}"),
            "create_pass_through_endpoint": _action("POST", "/config/pass_through_endpoint"),
            "update_pass_through_endpoint": _action("POST", "/config/pass_through_endpoint/{endpoint_id}"),
            "delete_pass_through_endpoint": _action("DELETE", "/config/pass_through_endpoint"),
            "get_cost_discount_config": _action("GET", "/config/cost_discount_config"),
            "update_cost_discount_config": _action("PATCH", "/config/cost_discount_config"),
            "get_cost_margin_config": _action("GET", "/config/cost_margin_config"),
            "update_cost_margin_config": _action("PATCH", "/config/cost_margin_config"),
            "get_hashicorp_vault_config": _action("GET", "/config_overrides/hashicorp_vault"),
            "update_hashicorp_vault_config": _action("POST", "/config_overrides/hashicorp_vault"),
            "delete_hashicorp_vault_config": _action("DELETE", "/config_overrides/hashicorp_vault"),
            "test_hashicorp_vault_connection": _action("POST", "/config_overrides/hashicorp_vault/test_connection"),
            "get_internal_user_settings": _action("GET", "/get/internal_user_settings"),
            "update_internal_user_settings": _action("PATCH", "/update/internal_user_settings"),
            "get_default_team_settings": _action("GET", "/get/default_team_settings"),
            "update_default_team_settings": _action("PATCH", "/update/default_team_settings"),
            "get_sso_settings": _action("GET", "/get/sso_settings"),
            "update_sso_settings": _action("PATCH", "/update/sso_settings"),
            "sso_readiness": _action("GET", "/sso/readiness"),
            "get_ui_theme_settings": _action("GET", "/get/ui_theme_settings"),
            "update_ui_theme_settings": _action("PATCH", "/update/ui_theme_settings"),
            "get_ui_settings": _action("GET", "/get/ui_settings"),
            "update_ui_settings": _action("PATCH", "/update/ui_settings"),
            "get_email_event_settings": _action("GET", "/email/event_settings"),
            "update_email_event_settings": _action("PATCH", "/email/event_settings"),
            "reset_email_event_settings": _action("POST", "/email/event_settings/reset"),
            "upload_logo": _action("POST", "/upload/logo"),
            "in_product_nudges": _action("GET", "/in_product_nudges"),
        },
    ),
    ToolSpec(
        name="litellm_exports_audit",
        description=(
            "Manage CloudZero, Vantage, audit logs, and compliance checks. Actions: "
            "get_cloudzero_settings, update_cloudzero_settings, init_cloudzero, "
            "cloudzero_dry_run, cloudzero_export, delete_cloudzero_settings, "
            "get_vantage_settings, update_vantage_settings, init_vantage, "
            "vantage_dry_run, vantage_export, delete_vantage_settings, list_audit_logs, "
            "get_audit_log, check_eu_ai_act, check_gdpr."
        ),
        actions={
            "get_cloudzero_settings": _action("GET", "/cloudzero/settings"),
            "update_cloudzero_settings": _action("PUT", "/cloudzero/settings"),
            "init_cloudzero": _action("POST", "/cloudzero/init"),
            "cloudzero_dry_run": _action("POST", "/cloudzero/dry-run"),
            "cloudzero_export": _action("POST", "/cloudzero/export"),
            "delete_cloudzero_settings": _action("DELETE", "/cloudzero/delete"),
            "get_vantage_settings": _action("GET", "/vantage/settings"),
            "update_vantage_settings": _action("PUT", "/vantage/settings"),
            "init_vantage": _action("POST", "/vantage/init"),
            "vantage_dry_run": _action("POST", "/vantage/dry-run"),
            "vantage_export": _action("POST", "/vantage/export"),
            "delete_vantage_settings": _action("DELETE", "/vantage/delete"),
            "list_audit_logs": _action("GET", "/audit"),
            "get_audit_log": _action("GET", "/audit/{id}"),
            "check_eu_ai_act": _action("POST", "/compliance/eu-ai-act"),
            "check_gdpr": _action("POST", "/compliance/gdpr"),
        },
    ),
)

DISCOVERY_TOOL_NAMES = frozenset(
    {
        "litellm_list_routes",
        "litellm_route_details",
    }
)
ESCAPE_HATCH_TOOL_NAMES = frozenset({"litellm_native_request"})

FAMILY_TOOL_SPECS_BY_NAME = {tool_spec.name: tool_spec for tool_spec in TOOL_SPECS}
FAMILY_TOOL_NAMES = frozenset(FAMILY_TOOL_SPECS_BY_NAME)
ALL_TOOL_NAMES = FAMILY_TOOL_NAMES | DISCOVERY_TOOL_NAMES | ESCAPE_HATCH_TOOL_NAMES

TOOL_PROFILES = {
    "none": ToolProfile(
        name="none",
        description="Start with no tools and add individual tools explicitly.",
        tools=frozenset(),
    ),
    "discovery": ToolProfile(
        name="discovery",
        description="Expose route-discovery helpers without broader admin capabilities.",
        tools=DISCOVERY_TOOL_NAMES,
    ),
    "catalog": ToolProfile(
        name="catalog",
        description="Expose public and internal model-catalog discovery endpoints.",
        tools=frozenset({"litellm_models_catalog"}),
    ),
    "access_admin": ToolProfile(
        name="access_admin",
        description="Manage keys, teams, and related access-control workflows.",
        tools=frozenset(
            {
                "litellm_keys",
                "litellm_teams",
            }
        ),
    ),
    "identity_admin": ToolProfile(
        name="identity_admin",
        description="Manage users, organizations, projects, customers, and credentials.",
        tools=frozenset(
            {
                "litellm_identities",
                "litellm_auth_admin",
            }
        ),
    ),
    "spend_admin": ToolProfile(
        name="spend_admin",
        description="Manage budgets, spend analytics, exports, and compliance checks.",
        tools=frozenset(
            {
                "litellm_budgets_spend",
                "litellm_exports_audit",
            }
        ),
    ),
    "runtime_ops": ToolProfile(
        name="runtime_ops",
        description="Inspect and operate runtime health, cache, router, and callback state.",
        tools=frozenset({"litellm_runtime"}),
    ),
    "governance": ToolProfile(
        name="governance",
        description="Manage prompts, policies, guardrails, and tool-policy settings.",
        tools=frozenset({"litellm_governance"}),
    ),
    "search_rag": ToolProfile(
        name="search_rag",
        description="Manage LiteLLM search tools plus search and RAG workflows.",
        tools=frozenset({"litellm_search_rag"}),
    ),
    "mcp_admin": ToolProfile(
        name="mcp_admin",
        description="Manage LiteLLM MCP registry, bridge, and MCP-specific settings.",
        tools=frozenset({"litellm_mcp_admin"}),
    ),
    "config_admin": ToolProfile(
        name="config_admin",
        description="Manage proxy, SSO, UI, vault, and pass-through endpoint settings.",
        tools=frozenset({"litellm_config_admin"}),
    ),
    "native_escape_hatch": ToolProfile(
        name="native_escape_hatch",
        description="Enable the generic native-request tool for uncovered LiteLLM-native routes.",
        tools=DISCOVERY_TOOL_NAMES | ESCAPE_HATCH_TOOL_NAMES,
    ),
    "core": ToolProfile(
        name="core",
        description=(
            "Default compact toolset for common LiteLLM administration: discovery, "
            "model catalog, keys, teams, and runtime operations."
        ),
        tools=DISCOVERY_TOOL_NAMES
        | frozenset(
            {
                "litellm_models_catalog",
                "litellm_keys",
                "litellm_teams",
                "litellm_runtime",
            }
        ),
    ),
    "platform_admin": ToolProfile(
        name="platform_admin",
        description="Broad LiteLLM platform administration without the generic escape hatch.",
        tools=DISCOVERY_TOOL_NAMES
        | frozenset(
            {
                "litellm_models_catalog",
                "litellm_models_admin",
                "litellm_keys",
                "litellm_teams",
                "litellm_identities",
                "litellm_auth_admin",
                "litellm_runtime",
                "litellm_config_admin",
            }
        ),
    ),
    "full": ToolProfile(
        name="full",
        description="Expose every MCP tool implemented by this server, including the escape hatch.",
        tools=ALL_TOOL_NAMES,
    ),
}

DEFAULT_TOOL_PROFILES = ("core",)


def _normalize_names(names: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    normalized: list[str] = []
    for name in names:
        stripped_name = name.strip()
        if not stripped_name or stripped_name in seen:
            continue
        normalized.append(stripped_name)
        seen.add(stripped_name)
    return tuple(normalized)


def _ensure_known_profiles(profile_names: Iterable[str]) -> tuple[str, ...]:
    normalized_profile_names = _normalize_names(profile_names)
    unknown_profiles = sorted(profile_name for profile_name in normalized_profile_names if profile_name not in TOOL_PROFILES)
    if unknown_profiles:
        choices = ", ".join(sorted(TOOL_PROFILES))
        detail = ", ".join(unknown_profiles)
        message = f"Unknown tool profile(s): {detail}. Valid profiles: {choices}."
        raise ValueError(message)
    return normalized_profile_names


def _ensure_known_tools(tool_names: Iterable[str]) -> tuple[str, ...]:
    normalized_tool_names = _normalize_names(tool_names)
    unknown_tools = sorted(tool_name for tool_name in normalized_tool_names if tool_name not in ALL_TOOL_NAMES)
    if unknown_tools:
        choices = ", ".join(sorted(ALL_TOOL_NAMES))
        detail = ", ".join(unknown_tools)
        message = f"Unknown tool name(s): {detail}. Valid tools: {choices}."
        raise ValueError(message)
    return normalized_tool_names


def list_tool_profiles() -> tuple[ToolProfile, ...]:
    """Return the available tool-loading profiles in sorted order."""
    return tuple(TOOL_PROFILES[profile_name] for profile_name in sorted(TOOL_PROFILES))


def resolve_enabled_tool_names(
    *,
    profile_names: Iterable[str] = DEFAULT_TOOL_PROFILES,
    enable_tools: Iterable[str] = (),
    disable_tools: Iterable[str] = (),
) -> tuple[str, ...]:
    """Resolve the final enabled tool set from profiles plus explicit overrides."""
    validated_profiles = _ensure_known_profiles(profile_names)
    validated_enable_tools = _ensure_known_tools(enable_tools)
    validated_disable_tools = _ensure_known_tools(disable_tools)

    active_tools: set[str] = set()
    for profile_name in validated_profiles:
        active_tools.update(TOOL_PROFILES[profile_name].tools)
    active_tools.update(validated_enable_tools)
    active_tools.difference_update(validated_disable_tools)

    return tuple(sorted(active_tools))
