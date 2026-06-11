# Adversarial Review Remediation — Implementation Plan

**Date:** 2026-06-10
**Author:** researcher
**Subject:** Remediate every actionable finding from `.analysis/adversarial-review-20260610.md` — no deferrals
**Scope:** All 8 modules under `src/mcp_litellm/`, `__init__.py`, `tests/`, `pyproject.toml`, `.pre-commit-config.yaml`, plus two new files (`tests/conftest.py`, `.github/workflows/ci.yml`) and one new leaf module (`src/mcp_litellm/_parsing.py`)
**Status:** PROMOTED (2026-06-11)

---

## Executive Summary

The adversarial review produced 47 numbered observations. After removing the entries
marked GOOD / OBSERVATION / RESOLVED / CORRECTED-no-action, **41 are actionable** and
**all 41 are remediated in this plan** — none deferred, per operator instruction. The
work is a single cohesive hardening pass over the existing server: no new product
surface, no database, no schema. Changes cluster into five themes:

1. **Error hygiene** — a common `McpLiteLLMError` base, fix the `KeyError` repr-quoting
   bug, retain structured fields, single-source the multipart message.
2. **HTTP client correctness/perf** — one pooled `httpx.AsyncClient` (closed via FastMCP
   `lifespan`), `follow_redirects=False`, parse-error wrapping, `None`-query dropping,
   transport-gated local file uploads.
3. **Route classification robustness** — HTTP-method-only path-item iteration, exact-vs-prefix
   normalization, hoisted alias table, and snapshot drift guards.
4. **Tool surface** — generated action lists (kill hand-maintained drift), `Literal`
   action enums in the MCP schema, escape-hatch honoring `--disable-tool`, validated
   CLI overrides, clean CLI error exit.
5. **Project hygiene** — version bump past the stale `0.1.0` artifacts, hermetic tests,
   error-path + drift-guard coverage, a minimal CI workflow, dead-config cleanup.

No emergency wave was added. Single implementation wave (Wave 1) because all changes are
interdependent (shared error base, shared response type, shared parsing helper) and the
total fits one engineer's ~125k budget; a config/Python split is pre-authorized as a
contingency only.

## Rollout Order

<!-- Dependency diagram showing dispatch sequencing. -->

```
Wave 0: Infra health check (orchestrator, foreground)
  │
Wave 1: Adversarial-review remediation
  ├── Dispatch 1: Tester    — writes ALL failing tests (~75k est.)
  ├── Dispatch 2: Engineer  — ALL source + config changes (~110k est.)
  │                           [contingency split → Engineer A Python / Engineer B config]
  └── Dispatch 3: QA        — reviews everything (~30k est.)
```

**No database work** — there is no migration, DDL, ORM, or DAL in scope, so **no DB
Foundation wave** is required (see Schema Verification: N/A).

**Dependencies:** Wave 1 is the only implementation wave. Internal ordering (errors →
models → client/service → server → tool_definitions; new leaf `_parsing.py` first) is
handled *within* the engineer dispatch, not as separate waves.

**Dispatch sizing:** One tester writes all failing tests. One engineer implements all
source. One QA reviews all. The engineer split is pre-authorized **only** if work exceeds
~125k tokens, along the tooling boundary (Python source vs `pyproject.toml` /
`.pre-commit-config.yaml` / `.github/workflows/ci.yml`). Do not split by finding,
module, or theme.

**Maximum concurrent agents: 1.** This is a serial plan (tester → engineer → QA).

## Implementation Waves

<!-- SPECIFICATION ONLY — do not modify after operator approval. -->

### Wave 1: Server Hardening — Adversarial-Review Remediation

**Depends on:** (none)
**Scope:** All files in this plan
**Surface area:** Whole `mcp_litellm` package + tests + project config

#### Impact Analysis

**Type:** modification (behavior-preserving refactor + hardening) + net-new (3 files)

**Net-new files** (`N/A — net-new, no existing behavior modified`):
  - `src/mcp_litellm/_parsing.py` — shared CSV-splitting helper
  - `tests/conftest.py` — autouse hermeticity fixture
  - `.github/workflows/ci.yml` — CI running ruff/mypy/pytest

**Modified public symbols and their consumers** (grep-verified against `src/` and `tests/`):

- **`errors.py` exception bases change; new common base `McpLiteLLMError`.**
  - `grep -rn "from mcp_litellm.errors import\|mcp_litellm.errors" src/ tests/`:
    - `client.py:15` imports `InvalidMultipartBodyError, LiteLLMRequestError, LiteLLMResponseTooLargeError` — still exported, unaffected (bases widen only).
    - `service.py:10` imports `MissingPathParametersError, RouteNotAllowedError, UnknownToolActionError` — still exported, unaffected.
    - `server.py:14` imports `InvalidToolSpecError` — still exported, unaffected.
    - `route_catalog.py:12` imports `UnknownLiteLLMRouteError` — base changes `KeyError`→`LookupError`; the only construction site (`route_catalog.py:260`) and its `except KeyError` (catches the *dict* lookup, not the custom type) are unaffected. Verified: no code does `except UnknownLiteLLMRouteError` expecting `KeyError` semantics.
    - `tests/test_client.py:14` imports `LiteLLMResponseTooLargeError` — unaffected.
  - **Public name removal:** none. All existing error classes remain; bases only widen and new classes are added.

- **`MULTIPART_BODY_ERROR` constant moves `models.py` → `errors.py`, re-exported from `models.py`.**
  - `grep -rn "MULTIPART_BODY_ERROR" src/ tests/`:
    - `models.py:17` (definition → becomes re-export), `models.py:65` (usage),
      `tests/test_models.py:10` (import from models), `tests/test_server.py:13` (import from models).
  - All four keep working: `models.py` re-exports the name, so `from mcp_litellm.models import MULTIPART_BODY_ERROR` is preserved. No consumer updated.

- **`RequestOptions._coerce_path_params` now rejects `None`/`bool`.**
  - Consumers: `_render_path`/`execute_route` (service.py), tool bodies (server.py). Behavior change is *stricter validation only*; existing valid inputs (str/int) unaffected. `tests/test_models.py:16` (int→str coercion) still passes.

- **`execute_route_key` signature gains `denied_route_keys`; `allowed_classifications` retyped `set[str]`→`set[RouteClassification]`.**
  - `grep -rn "execute_route_key" src/ tests/`: `service.py:74` (def), `service.py:100` (called by `execute_action`), `server.py:251` (called by native_request). Both call sites pass keyword args; new param is optional (defaults `None`). Retyping is a type-only change (runtime identical). All call sites updated in this wave.

- **`LiteLLMClient.request` return type → `LiteLLMResponse` TypedDict; internal client pooling.**
  - `grep -rn "\.request(" src/ tests/`: `service.py:62` (await), `tests/test_client.py:29,48,72,92`. Return shape is unchanged at runtime (TypedDict is a dict); all callers unaffected. Pooling is internal.

- **`Settings` gains `allow_local_file_uploads`, `port` bounds, `DEFAULT_TOOL_PROFILES`; drops `env_nested_delimiter`.**
  - `grep -rn "Settings(" tests/`: constructed in `test_client.py`, `test_server.py`. New field has a default; existing constructions unaffected. `env_nested_delimiter` removal is inert (no nested models). Verified no test references `env_nested_delimiter`.

- **`tool_definitions.ToolSpec.actions` retyped `dict`→`Mapping`; descriptions now generated.**
  - `grep -rn "\.actions" src/ tests/`: `server.py:80,81,110` (iterates `.items()`, passes dict), `service.py:96,98` (subscript + `sorted`). `Mapping` supports all of these. Generated descriptions change the *string value* but no test pins exact description text (verified: `grep -rn "Actions:" tests/` → 0 results).
  - **Public name removal:** none — `DISCOVERY_TOOL_NAMES`, `ESCAPE_HATCH_TOOL_NAMES`, `ALL_TOOL_NAMES`, `TOOL_PROFILES`, `TOOL_SPECS`, `DEFAULT_TOOL_PROFILES` all retained with identical names/values.

- **`server.main` refactor extracts `_resolve_settings`; `_parse_name_args` uses shared helper.**
  - `grep -rn "_parse_name_args\|def main" src/ tests/`: `server.py:134,420`; not imported elsewhere, not currently tested. New `_resolve_settings` is net-new (tested).

**Grep verification summary:** all modified public symbols enumerated above with their
call sites; every site is either unaffected (widening/optional) or updated within this
wave. No public name is removed.

#### Test Spec (tester's input)

**Test files:**
  - `tests/conftest.py` — new; autouse hermeticity fixture (infra for all tests)
  - `tests/test_config.py` — new; unit
  - `tests/test_errors.py` — new; unit
  - `tests/test_client.py` — extend; unit (respx)
  - `tests/test_models.py` — extend; unit
  - `tests/test_route_catalog.py` — extend; unit
  - `tests/test_service.py` — extend; unit
  - `tests/test_server.py` — extend; API (FastMCP) + unit
  - `tests/smoke/test_adversarial_review_remediation.py` — new; smoke

**Test cases (must fail before implementation):**

*Hermeticity (§10.1):*
  - `test_config.py::test_settings_ignores_ambient_env` — with `MCP_LITELLM_TOOL_PROFILES=full` planted in `os.environ`, `Settings().tool_profiles == ("core",)` (proves the conftest fixture neutralizes ambient env + `.env`).

*config.py (§1.1–1.6, §2.3, §8.5):*
  - `test_config.py::test_json_array_tool_list_strips_whitespace` — `Settings(enable_tools='[" litellm_keys "]').enable_tools == ("litellm_keys",)`.
  - `test_config.py::test_set_input_is_sorted_deterministically` — `Settings(tool_profiles={"b","a"}).tool_profiles == ("a","b")`.
  - `test_config.py::test_port_rejects_out_of_range` — `Settings(port=70000)` raises `ValidationError`; `Settings(port=0)` raises.
  - `test_config.py::test_default_openapi_path_raises_when_absent` — monkeypatch both candidate paths' `.exists()`→False; calling `default_openapi_path()` raises `FileNotFoundError` whose message contains both probed paths.
  - `test_config.py::test_allow_local_file_uploads_defaults_true` — `Settings().allow_local_file_uploads is True`.
  - `test_config.py::test_default_tool_profiles_constant_matches_settings_default` — `DEFAULT_TOOL_PROFILES == Settings().tool_profiles == ("core",)`.

*errors.py (§3.1–3.3, §2.1):*
  - `test_errors.py::test_all_errors_subclass_common_base` — every custom error class is a subclass of `McpLiteLLMError`.
  - `test_errors.py::test_unknown_route_error_message_not_quoted` — `str(UnknownLiteLLMRouteError("GET /x")) == "Unknown LiteLLM route: GET /x"` (no surrounding single quotes); and it is NOT a `KeyError`.
  - `test_errors.py::test_errors_retain_structured_fields` — `MissingPathParametersError(["a","b"]).missing_params == ["a","b"]`; `RouteNotAllowedError("GET /x","alias").route_key == "GET /x"` and `.classification == "alias"`; `UnknownToolActionError("z",["a"]).action == "z"`.
  - `test_errors.py::test_multipart_body_error_uses_shared_constant` — `str(InvalidMultipartBodyError()) == MULTIPART_BODY_ERROR` and `InvalidMultipartBodyError` is a `ValueError`.

*models.py (§2.2, §2.4-via-client, §4.9):*
  - `test_models.py::test_path_params_reject_none_value` — `RequestOptions.model_validate({"path_params": {"k": None}})` raises `ValidationError`.
  - `test_models.py::test_path_params_reject_bool_value` — `{"path_params": {"k": True}}` raises `ValidationError`.
  - `test_models.py::test_path_params_still_coerce_int` — existing `{"k":123}`→`"123"` still holds (regression guard).
  - `test_models.py::test_litellm_response_typeddict_importable` — `from mcp_litellm.models import LiteLLMResponse` succeeds and it is a `TypedDict`.

*client.py (§4.1, §4.2, §4.3, §4.5, §4.6, §4.7, §4.8, §2.3, §2.4):*
  - `test_client.py::test_reuses_single_async_client` — monkeypatch `httpx.AsyncClient` with a counting wrapper; two `await client.request(...)` calls instantiate the underlying client at most once.
  - `test_client.py::test_does_not_follow_redirects` — respx returns 302 with `location` header; result has `status_code == 302` and `headers["location"]` present, and the redirect target is NOT fetched.
  - `test_client.py::test_malformed_json_raises_parse_error` — content-type `application/json` with body `b"{not json"` raises `LiteLLMResponseParseError`.
  - `test_client.py::test_declared_text_bad_encoding_falls_back_to_base64` — content-type `text/plain; charset=ascii` with non-ascii bytes yields a `base64` key (no crash).
  - `test_client.py::test_none_query_values_dropped` — `query={"a": None, "b": "x"}`; captured request URL has `b=x` and no `a`.
  - `test_client.py::test_none_query_list_member_dropped` — `query={"t": ["x", None]}`; sent as `t=x` only.
  - `test_client.py::test_multipart_none_field_omitted` — `body={"a": None, "b": "x"}` with multipart; form data has `b` and omits `a` (no literal `"null"`).
  - `test_client.py::test_multipart_blocked_when_uploads_disabled` — `Settings(allow_local_file_uploads=False)`; a multipart request raises `LocalFileUploadNotAllowedError` before any HTTP call.
  - `test_client.py::test_multipart_file_deleted_after_validation_raises_clean_error` — construct `MultipartFileSpec` for an existing file, delete it, then `request(...)` raises a `McpLiteLLMError` (not bare `FileNotFoundError`).
  - `test_client.py::test_transport_error_wrapped` — respx raises `httpx.ConnectError`; `request(...)` raises `LiteLLMRequestError` (covers the formerly `pragma: no cover` branch).

*route_catalog.py (§5.1, §5.2, §5.3, §5.4):*
  - `test_route_catalog.py::test_typed_classification_set_is_stable` — the full sorted set of route keys classified `typed` equals a checked-in baseline of **317** keys (pins behavior across the refactor; tester captures the current set as the expected literal).
  - `test_route_catalog.py::test_generic_native_baseline` — count of `generic_native` routes equals **175** (snapshot drift guard for §5.1; any future spec refresh adding native routes fails this until consciously updated).
  - `test_route_catalog.py::test_no_typed_prefix_shadows_another` — no two distinct entries in `TYPED_PATH_PREFIXES` satisfy `a.startswith(b)`; and no entry in `TYPED_EXACT_PATHS` starts with any prefix.
  - `test_route_catalog.py::test_non_http_method_path_item_keys_ignored` — a spec whose path-item has a `"parameters"` list key builds without error and does not emit a bogus route.
  - `test_route_catalog.py::test_existing_classification_cases_unchanged` — keep the 8 existing classification assertions (regression).

*service.py (§6.1, §6.2, §6.4, §7.3-support):*
  - `test_service.py::test_render_path_rejects_empty_value` — `_render_path("/key/{k}", {"k": ""})` raises (empty treated as invalid).
  - `test_service.py::test_render_path_rejects_surplus_keys` — `_render_path("/key/{k}", {"k":"a","extra":"b"})` raises `InvalidPathParameterError`.
  - `test_service.py::test_render_path_still_encodes` — existing `foo/bar baz`→`foo%2Fbar%20baz` regression.
  - `test_service.py::test_denied_route_key_rejected` — `execute_route_key("GET /x", allowed_classifications={"typed"}, denied_route_keys={"GET /x"}, ...)` raises `RouteNotAllowedError` (uses a stub catalog/client).

*server.py (§7.1, §7.2, §7.3, §7.5, §4.1-lifespan):*
  - `test_server.py::test_native_request_denies_disabled_family_routes` — build server with `tool_profiles=("full",)`, `disable_tools=("litellm_config_admin",)`; calling `litellm_native_request` with a config_admin route key (`"GET /config/cost_discount_config"`) raises `ToolError` (denied), while a still-enabled typed route is allowed.
  - `test_server.py::test_family_tool_action_param_has_enum` — `(await server.list_tools())` entry for `litellm_keys` has `inputSchema["properties"]["action"]["enum"]` equal to the sorted action names of that spec.
  - `test_server.py::test_resolve_settings_validates_overrides` — `_resolve_settings(Settings(), argparse.Namespace(port=70000, ...))` raises `ValidationError` (proves `model_validate` path, not `model_copy`).
  - `test_server.py::test_main_unknown_profile_exits_cleanly` — invoking `main()` (monkeypatched argv) with `--tool-profile bogus` raises `SystemExit` (code 2), not a raw `ValueError` traceback.
  - `test_server.py::test_lifespan_closes_client` — entering and exiting the server's `lifespan` context calls `LiteLLMClient.aclose` exactly once (spy).
  - keep all existing `test_server.py` cases (regression).

*tool_definitions.py (§8.2, §8.3, §8.4):*
  - `test_server.py::test_every_action_name_appears_in_description` — for every `ToolSpec`, each action key is a substring of `tool_spec.description` (drift guard replacing hand-maintenance).
  - `test_server.py::test_tool_spec_actions_is_read_only_mapping` — `tool_spec.actions` does not support item assignment (raises `TypeError`).
  - `test_server.py::test_tool_profiles_keys_match_names` — `all(k == v.name for k,v in TOOL_PROFILES.items())`.

*pyproject / packaging (§9.2):*
  - `tests/smoke/test_adversarial_review_remediation.py::test_version_is_bumped` — `mcp_litellm.__version__ == "0.2.0"` and matches `pyproject.toml`’s `version`.

*Existing-test cleanup (§10.4):* tester removes redundant `@pytest.mark.asyncio`
decorators from `test_client.py`/`test_server.py` (asyncio auto-mode) as part of editing
those files — verified by the suite still collecting/passing.

**Integration test enforcement:** `N/A — no database or external integration; all tests
are unit/API/smoke against in-process objects and respx mocks.`

#### Source Spec (engineer's input — make the tests above pass)

Implement in this internal order (leaf-first to avoid import cycles):

1. **`src/mcp_litellm/_parsing.py`** (new leaf): `split_csv(value: str) -> tuple[str, ...]`
   — split on `,`, strip each, drop empties.

2. **`src/mcp_litellm/errors.py`** (§3.1, §3.2, §3.3, §2.1):
   - Add `MULTIPART_BODY_ERROR = "Multipart requests require a JSON object body."`.
   - Add `class McpLiteLLMError(Exception)` base.
   - Reparent all errors onto `McpLiteLLMError` + a sensible stdlib base; `UnknownLiteLLMRouteError(McpLiteLLMError, LookupError)` (NOT `KeyError`).
   - Retain structured fields (`self.route_key`, `self.missing_params`, `self.classification`, `self.action`, `self.allowed_actions`, `self.limit_bytes`).
   - `InvalidMultipartBodyError(McpLiteLLMError, ValueError)` message = `MULTIPART_BODY_ERROR`.
   - New: `LocalFileUploadNotAllowedError(McpLiteLLMError, PermissionError)`, `InvalidPathParameterError(McpLiteLLMError, ValueError)` (takes a detail string), `LiteLLMResponseParseError(McpLiteLLMError, RuntimeError)` (takes a detail string).

3. **`src/mcp_litellm/models.py`** (§2.2, §4.9, §2.1):
   - Import `InvalidMultipartBodyError, MULTIPART_BODY_ERROR` from `errors`; re-export `MULTIPART_BODY_ERROR`.
   - `_coerce_path_params`: raise `InvalidPathParameterError` for `None` or `bool` values; coerce `int`/`float`/`str` via `str()`.
   - `_validate_multipart_body`: raise `InvalidMultipartBodyError` (not bare `ValueError`).
   - Define `class LiteLLMResponse(TypedDict, total=False)` with keys: `ok, status_code, content_type, headers, data, text, base64, method, path, route_key, summary, classification, action`.

4. **`src/mcp_litellm/config.py`** (§1.1–1.6, §2.3, §8.5, §7.6):
   - `default_openapi_path`: raise `FileNotFoundError` (message lists both probed paths) when neither exists; add a comment explaining the editable-install fallback (also satisfies §9.1 rationale).
   - `_parse_name_list`: strip items in the JSON-array and iterable branches; sort `set`/`frozenset` inputs; use `split_csv` for the comma string branch; remove `_ = cls`.
   - `port: int = Field(default=8000, ge=1, le=65535)`.
   - Remove `env_nested_delimiter="__"`.
   - Add `allow_local_file_uploads: bool = Field(default=True)`.
   - Add module constant `DEFAULT_TOOL_PROFILES = ("core",)`; set `tool_profiles` default to it.

5. **`src/mcp_litellm/client.py`** (§4.1, §4.2, §4.3, §4.5, §4.6, §4.7, §4.8, §2.3, §2.4):
   - Hold a lazily-created shared `httpx.AsyncClient(follow_redirects=False)` guarded by an `asyncio.Lock`; add `async def aclose()`.
   - `request`: enforce `allow_local_file_uploads` (raise `LocalFileUploadNotAllowedError` when multipart and disabled); drop `None` query values and `None` list members; use the shared client; remove the `# pragma: no cover` on the `httpx.HTTPError` branch; annotate return `-> LiteLLMResponse`.
   - `_parse_response`: wrap `json.loads` failure → `LiteLLMResponseParseError`; declared-`text/*` decode failure → base64 fallback instead of raising.
   - `_multipart_form_data`: omit fields whose value is `None`.
   - `_build_files`: drop the redundant `expanduser`; wrap `path.open` in `try/except OSError` → `LiteLLMRequestError` (clean §2.4 error).

6. **`src/mcp_litellm/route_catalog.py`** (§5.1, §5.2, §5.3, §5.4, §5.5, §5.6):
   - Iterate path-items only over HTTP method keys (`get/put/post/delete/options/head/patch/trace`).
   - Hoist `deployment_aliases` to a module constant.
   - Split typed matching into `TYPED_EXACT_PATHS: frozenset[str]` + slash-terminated `TYPED_PATH_PREFIXES`; remove the redundant `/model/info`; keep `/search_tools` coverage via a `/search_tools/` prefix + `/search_tools` exact, and `/search` exact + `/search/` prefix (analysis: `/search` is the only over-matching bare prefix). Derive buckets so the two pinning tests pass.
   - `_matches_prefix`: pure `startswith` (drop the redundant `==`).
   - `_classify_route`: `path in TYPED_EXACT_PATHS or _matches_prefix(path, TYPED_PATH_PREFIXES)`.
   - Resolve the openapi path once (remove the double `.resolve()`).
   - Add a module docstring note: `generic_native` is intentionally default-allow and guarded by `test_generic_native_baseline`.

7. **`src/mcp_litellm/service.py`** (§6.1, §6.2, §6.3, §6.4, §6.5, §7.3-support):
   - `_render_path`: reject empty/whitespace-only param values and surplus keys → `InvalidPathParameterError`.
   - `execute_route_key`: retype `allowed_classifications: set[RouteClassification]`; add `denied_route_keys: set[str] | None = None`; raise `RouteNotAllowedError` when the resolved route key is denied.
   - Annotate response returns `-> LiteLLMResponse`.
   - Add a one-line comment on `ActionSpec` documenting it as a deliberate extension point (§6.5 — intentional, no structural change).

8. **`src/mcp_litellm/tool_definitions.py`** (§8.2, §8.3, §8.4, §8.5):
   - Add `_spec(name, prose, actions)` building `description = f"{prose} Actions: {', '.join(sorted(actions))}."` and wrapping actions in `MappingProxyType`; retype `ToolSpec.actions: Mapping[str, ActionSpec]`.
   - Rewrite the 12 specs to prose-only via `_spec(...)`.
   - Build `TOOL_PROFILES` from a tuple of `ToolProfile` via `{p.name: p for p in _PROFILES}`.
   - Import `DEFAULT_TOOL_PROFILES` from `config` (remove the local duplicate).

9. **`src/mcp_litellm/server.py`** (§7.1, §7.2, §7.3, §7.4, §7.5, §7.6, §7.7, §4.1):
   - `_make_family_tool`: set `tool.__annotations__["action"] = Literal[*sorted(actions)]` (via `Literal.__getitem__(tuple(sorted(actions)))`); remove the redundant `tool.__doc__` assignment (keep `__name__`).
   - `build_server`: compute `denied_route_keys` = route keys of disabled family specs not owned by any still-active family; pass to `_register_native_request_tool` → `execute_route_key(..., denied_route_keys=...)`. Resolve `allow_local_file_uploads` to `False` when `transport != "stdio"` and the operator did not set it (`"allow_local_file_uploads" not in settings.model_fields_set`). Pass a `lifespan` to `FastMCP` that `await client.aclose()` on shutdown.
   - Add a thin error boundary around tool bodies catching `McpLiteLLMError`/`ValidationError` → raise `ToolError(str(exc))` (§7.4) so messages are clean and consistent.
   - `main`: extract `_resolve_settings(base, args) -> Settings` using `Settings.model_validate({**base.model_dump(), **overrides})`; wrap `build_server` in `try/except ValueError` → `sys.exit(2)` with a one-line stderr message (§7.2).
   - `_parse_name_args`: use `split_csv`.

10. **`src/mcp_litellm/__init__.py`** (§9.2): add `__version__ = "0.2.0"`.

11. **`pyproject.toml`** (§9.2, §9.3): `version = "0.2.0"`; remove `@click.command`/`@click.group` from `[tool.vulture] ignore_decorators`.

12. **`.github/workflows/ci.yml`** (new, §9.4): on push/PR — `uv sync --extra dev`, `ruff check .`, `mypy`, `pytest`.

13. **`.pre-commit-config.yaml`** (§9.4): unchanged (actionlint now has a workflow to guard); verify it still passes.

14. **`tests/conftest.py`** (new, §10.1): autouse fixture that `monkeypatch.delenv`s every `MCP_LITELLM_*` var and `monkeypatch.setitem(Settings.model_config, "env_file", None)`.

## Schema Verification

`N/A — no SQL, ORM, migrations, or column references anywhere in scope. The only
"schema" touched is the in-memory OpenAPI route catalog, whose invariants are pinned by
`test_typed_classification_set_is_stable`, `test_generic_native_baseline`, and
`test_no_typed_prefix_shadows_another` rather than a database.`

## Risks and Mitigations

| # | Risk | Likelihood | Mitigation |
|---|------|-----------|------------|
| 1 | Route-catalog refactor (§5.3) silently reclassifies a real route | Med | `test_typed_classification_set_is_stable` pins the full 317-key typed set; any drift fails the suite. |
| 2 | Shared `httpx.AsyncClient` + `lifespan` interacts badly with stdio transport | Med | `test_lifespan_closes_client` + `test_reuses_single_async_client`; lazy creation under an `asyncio.Lock`; smoke test builds a server. |
| 3 | Dynamic `Literal` action annotation not honored by FastMCP | Low | De-risked at spec time — verified the annotation surfaces as `enum` in `inputSchema`; pinned by `test_family_tool_action_param_has_enum`. |
| 4 | `follow_redirects=False` breaks a legitimate LiteLLM redirect flow | Low | Admin/control-plane endpoints don't redirect; `Location` is surfaced (already whitelisted) so callers can act. Documented in client. |
| 5 | Escape-hatch denylist (§7.3) accidentally blocks a route that a still-active family owns | Low | Denylist subtracts route keys owned by active families; `test_native_request_denies_disabled_family_routes` checks both deny and allow sides. |
| 6 | `_coerce_path_params` stricter validation rejects a previously-accepted caller | Low | Only `None`/`bool` newly rejected (both were bugs producing `"None"`/`"True"`); int/str regression test retained. |
| 7 | Single large engineer dispatch exceeds token budget | Med | Pre-authorized contingency split along Python/config tooling boundary; precise per-file source spec minimizes exploration. |
| 8 | Generated descriptions diverge from TOOLS.md prose | Low | TOOLS.md documents actions in tables, not by mirroring the description string; no test pins description text. TOOLS.md left as-is (out of scope, still accurate). |

## Close-Out Checklist

- [x] QA is MANDATORY for every wave. No exceptions.
- [x] QA dispatched and PASS for every wave (inline under Wave 1-c: QA)
- [x] Eyes tristore update (if context injection changed) — N/A (no persona/context injection changed)
- [x] Ops validation (folded into CO-2: deterministic toolset builds across the suite; server builds identically each test)
- [x] Gate check green (CO-1: ruff/mypy/vulture/gitleaks/actionlint + 74 tests)
- [x] Smoke test PASS (CO-2: 4/4)
- [x] Operator nudges captured (see Operator Nudges — 2 documented)
- [x] Lessons learned (see Hindsight + If I Could Start This Plan Over + metrics)
- [x] Hindsight ("what would you do differently" — 7 items)
- [x] Tool errors documented (see Tool Errors and Infrastructure Failures — 4 entries)
- [x] Suggested persona/template adjustments (see If I Could Start This Plan Over)
- [ ] Plan promoted to `docs/implemented/2026-06-<slug>.md` (this step, in progress)

## Smoke Test Procedure

Smoke tests are pytest functions in `tests/smoke/test_adversarial_review_remediation.py`.

CO-2 executes: `run_gate_check(mode='targeted', test_path='tests/smoke/test_adversarial_review_remediation.py')`

Required smoke assertions:
- `test_package_imports()` — `from mcp_litellm.server import build_server, main` loads without error.
- `test_build_server_default_toolset()` — `build_server(Settings())` returns a server exposing the core toolset (no exception).
- `test_version_is_bumped()` — `mcp_litellm.__version__ == "0.2.0"` and equals the `pyproject.toml` version.
- `test_errors_module_imports()` — `from mcp_litellm.errors import McpLiteLLMError` loads without error.

No `@pytest.mark.integration` assertions — there is no live DB/session dependency.

## Confidence Notes (Pre-Execution)

| Wave | Pre-Execution | Post-Execution | Notes |
|------|--------------|----------------|-------|
| 1 | HIGH | HIGH (confirmed) | All 41 findings landed; 74 tests green; QA PASS; lint/type/vulture/gitleaks/actionlint clean. Every risky mechanism verified at spec time held in execution (dynamic `Literal`→enum, FastMCP `lifespan` closing the pooled client once, `model_fields_set` transport-gating, typed-set sha256 byte-identical). The breadth risk materialized not in the source (engineer's source was clean first try) but in the **tests** — the tester's respx usage + a spec-flawed env meta-test caused a land deadlock that took 3 recovery dispatches to clear. |

## Dispatch Plan

<!-- EXECUTION LOG — update in real-time during execution. -->

### Keepalive Cron

- Job ID: `4f00b072` — fires hourly at :13. Do NOT cancel unless operator asks.

### Wave 0: Infrastructure Health Check (Required before first dispatch)

| Check | Command | Expected | Actual |
|-------|---------|----------|--------|
| CWD | `pwd` | `/home/zepfu/projects/mcp-litellm` | ✅ `/home/zepfu/projects/mcp-litellm` |
| Branch | `git branch --show-current` | `develop` | ✅ `develop` (tracks origin/develop, in sync @ acee9aa) |
| Worktrees | `ls .claude/worktrees/` | empty | ✅ none |
| Gate baseline | `run_gate_check(branch='develop')` | lint PASS, tests N passed | ⚠️ run_gate_check **unavailable** (`[tool.aawm.gate]` not configured in this standalone repo). Substituted repo-native tooling: **26 tests pass**, ruff clean, mypy clean (16 files). |
| MCP tasks | `list_tasks()` | none | ✅ none |
| Commit infra | pre-commit / gitleaks / docker / origin | available | ✅ pre-commit 4.5.1, gitleaks 8.18.4, docker OK (actionlint runnable), origin reachable+pushable |

**Gate-tool substitution (recorded deviation):** `run_gate_check` and the aawm gate
config are absent here, so all gate/smoke checks (Wave 0 baseline, CO-1, CO-2) use the
repo's own commands via `uv run --no-sync`: `ruff check .`, `mypy`, `pytest`,
`pre-commit run --all-files`. Agents still `stage`/`land` normally (those use git +
pre-commit, not the gate config).

### Infrastructure Prerequisites Checklist

| Capability | Required By | Exists? | If Not: Add as Wave 0 step |
|-----------|------------|---------|---------------------------|
| Test database accessible | (no DB waves) | N/A | — |
| Migration tool configured | (no migration waves) | N/A | — |
| Integration test suite runnable | (no integration tests) | N/A | — |
| `uv` + `.venv` with dev extras | All test/lint | Yes (`.venv/bin/pytest` present) | — |
| respx installed | client tests | Yes (dev dep) | — |

### Total Estimated Effort

| Category | Planned Dispatches | Notes |
|----------|-------------------|-------|
| Tester | 1 | Writes ALL failing tests (~45 cases across 8 files) |
| Engineer | 1 (contingency: 2) | All source+config; split only if >125k, on Python/config boundary |
| QA | 1 | Reviews ALL changes together |
| Ops/Data | 0 | No pipeline/infra ops |
| **Total waves** | **1** | |
| **Max concurrent agents** | **1** | Serial plan |

### Token Estimate

| Dispatch | Target files | Est. tokens | Rationale |
|----------|-------------|-------------|-----------|
| Tester | `tests/conftest.py`, `tests/test_config.py`, `tests/test_errors.py`, `tests/test_client.py`, `tests/test_models.py`, `tests/test_route_catalog.py`, `tests/test_service.py`, `tests/test_server.py`, `tests/smoke/test_adversarial_review_remediation.py` | ~75k | ~45 test functions; 8 source files to read for context (already small) |
| Engineer | 11 source files + `pyproject.toml` + `.github/workflows/ci.yml` + `tests/conftest.py` review | ~110k | ~50 discrete edits across 14 files + red→green iteration |
| QA | (read-only) | ~30k | Review all changes + run gate check |

### Wave 1: Server Hardening — Adversarial-Review Remediation

#### Dispatch 1: Tester
| Agent | Target files | Task |
|-------|-------------|------|
| tester | all `tests/**` listed above | Write failing tests per the Test Spec; capture the 317-key typed baseline + 175 generic_native count as literals |

**Outcome:** DONE. **Commit:** `d6f2606` (merge `b659379`). 48 new test functions across 9 files + `tests/smoke/`. Red/green split verified on develop: **39 fail / 34 pass** — new-behavior tests fail on missing symbols; regression guards green (typed-set count+sha256 `8d73e94c…`, generic_native==175, 8 existing classifications, int coercion, URL-encoding, description-drift, profile-name-match). Removed 7 redundant `@pytest.mark.asyncio` decorators (§10.4). Worktree removed.

#### Dispatch 2: Engineer
| Agent | Target files | Task |
|-------|-------------|------|
| engineer | all `src/**` + `pyproject.toml` + `.github/workflows/ci.yml` | Implement the Source Spec leaf-left; make all tests green; keep ruff/mypy/vulture clean |

**Outcome:** IMPLEMENTED but DID NOT LAND (correctly escalated). Engineer (`a05db0ee`) wrote all 12 source/config files leaf-first; **source is ruff/mypy/vulture clean** and the route refactor preserves the typed-set sha256 byte-identically. Result on its worktree: **66 pass / 7 fail**, where all 7 failures + 23 mypy errors are **defects in the tester-landed `tests/` files** (which the engineer is forbidden to edit), not source bugs. Orchestrator independently verified the defects:
- **respx router-binding bug (5 tests):** `with respx.mock():` opens a fresh nested router but routes register on the module-global `respx.get/post` → active router empty → `AllMockedAssertionError`. (Passing tests correctly use `with respx.mock(...) as router:` + `router.get`.)
- **`assert_all_called` mismatch (redirect + upload-blocked tests):** a defensive route is intentionally never called.
- **`test_settings_ignores_ambient_env` (my spec flaw):** plants `MCP_LITELLM_TOOL_PROFILES=full` *after* the autouse fixture; pydantic-settings always reads `os.environ`, so it can't be ignored — the meta-test is self-contradictory. The conftest fixture itself is correct and valuable.
- **23 mypy errors in `tests/`:** stale `# type: ignore[attr-defined]` (symbols now exist; `warn_unused_ignores=true`) + wrong code (`[assignment]`→`[index]`) at `test_server.py:260`.

**Recovery — Dispatch 2b (salvage, ABANDONED):** salvage (`a258a52f`, haiku) copied the 12 source files and reverted a stray `uv.lock` change but terminated early twice before fixing any test (first stop: tried blocked `python -m pytest`; after a `uv run --no-sync` correction it resumed, reverted the lock, then stopped again). Reliability problem with the haiku salvage agent, not a source problem.

**Recovery — Dispatch 2c (engineer, sonnet):** copy the verified source from `agent-a05db0ee7441fc638`, fix the 4 confirmed test-defect categories (respx router-binding, `assert_all_called`, env meta-test, stale mypy ignores), verify all 73 green, land. Test edits explicitly authorized for this recovery dispatch.

**Outcome: DONE & LANDED.** **Commits:** `d3717f2` (source + test fixes) + `68728d7` (new files + actionlint-hook fix), merged as `acaafe6` on develop. Orchestrator-verified on origin/develop: **73 passed**, ruff clean, mypy clean (22 files), vulture clean, `version`/`__version__` both `0.2.0`. No source bugs found — every previously-failing test passed against the copied source once the respx binding was corrected. Test edits: (a) 5 respx router-binding fixes in test_client.py, (b) 2 `assert_all_called=False` fixes, (c) `test_settings_ignores_ambient_env` rewritten to a deterministic hermetic check, (d) 22 stale `# type: ignore` removed + 1 recoded to `[index]`. **Incidental infra fix:** `.pre-commit-config.yaml` actionlint hook passed a redundant `actionlint` token (rhysd/actionlint ENTRYPOINT is already actionlint) → errored on any workflow file; the new `ci.yml` was the first to trip it; hook corrected by dropping the duplicate token. All 3 leftover worktrees removed.

**Two-Strike Escalation (if Dispatch 2 agent fails twice):**
- Root cause: identify before 3rd dispatch (most likely: route-catalog bucket derivation or FastMCP lifespan wiring).
- Escalation: split per contingency (Engineer A = Python source, Engineer B = config/YAML/TOML); if a single finding blocks, isolate it to a follow-up micro-dispatch rather than stalling the wave.

#### Dispatch 3: QA
| Agent | Target files | Task |
|-------|-------------|------|
| qa | (read-only) | Verify test quality + every finding addressed; confirm no public name removed; run full gate check |

#### Wave 1-c: QA

**Verdict: PASS** (QA, 2026-06-11, read-only review on develop @ `acaafe6` = `d3717f2` + `68728d7`)

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | All tests pass, no skips/xfails | PASS | `uv run --no-sync pytest -q` → **73 passed in 1.24s**; `grep -rn "skip\|xfail\|pytest.mark.asyncio" tests/` → 0 hits (no skips, no xfails, §10.4 markers gone; `asyncio_mode = "auto"` at pyproject.toml:51). |
| 2 | No regressions; typed set byte-identical | PASS | `test_typed_classification_set_is_stable` asserts count **317** + sha256 `8d73e94c…dacb76d` (test_route_catalog.py:64-66); `git show d6f2606:tests/test_route_catalog.py` confirms the **same digest was pinned at red time against the pre-refactor source** — the route-catalog exact/prefix refactor preserved the typed set byte-identically. `test_generic_native_baseline` ==175 green; all 8 original classification cases + original client/models/server/service guards present and green. |
| 3 | Recovery-fixed tests assert real values | PASS | Reviewed `git diff d6f2606 acaafe6 -- tests/`: edits are exactly the 4 authorized categories; **no assertion was weakened or removed**. (a) 5 respx fixes correctly bind routes to the active router (`with respx.mock(...) as router` + `router.get`). (b) `assert_all_called=False` is justified per-test: `test_does_not_follow_redirects` keeps `status_code == 302`, `"location" in headers`, **and `assert not new_route.called`** (would fail if redirects were followed); `test_multipart_blocked_when_uploads_disabled` keeps `pytest.raises(LocalFileUploadNotAllowedError)` **and `assert not router.calls`** (fails if any HTTP escapes); the other `False` sites (`malformed_json`, `text_fallback`, `transport_error`, `file_deleted`) all require the mocked response/side-effect to fire for their `pytest.raises`/value assertions to hold — none vacuous. (c) `test_settings_ignores_ambient_env` rewrite: the original was self-contradictory (planted env after the fixture); the new check is deterministic, and I **independently proved non-vacuousness** by running the full suite with `MCP_LITELLM_TOOL_PROFILES=full MCP_LITELLM_PORT=9999` planted → 73 passed (without the conftest fixture, the env-hygiene assertion and the default-toolset tests would fail). (d) 22 stale ignores removed + `[assignment]`→`[index]` at test_server.py:260 — no behavioral change. `test_reuses_single_async_client` monkeypatches `httpx.AsyncClient.__init__` with a counter; a per-request-client implementation yields count=2 → fail. `test_malformed_json_raises_parse_error` requires `LiteLLMResponseParseError` (raised only from the `json.loads` wrap at client.py:140-142). |
| 4 | Coverage Table: all 41 findings | PASS | Walked all 41 rows; every cited test exists (by name, in the cited file) and every cited source change is present and non-cosmetic. Spot evidence: §1.1 config.py:39-40 (FileNotFoundError lists both probed paths); §1.5 config.py:61 (`ge=1, le=65535`); §1.6 model_config has no `env_nested_delimiter`; §2.1 errors.py:5 + models.py re-export (`__all__` models.py:17); §2.2 models.py:94-103; §2.3 client.py:182-183 + server.py:382-394; §2.4 client.py:82-86 (`OSError`→`LiteLLMRequestError`); §2.5 client.py:115-119; §3.1 errors.py:45-51 (`LookupError`, unquoted message); §4.1 client.py:44-58 (lazy client + `asyncio.Lock` + `aclose`); §4.3 client.py:51 (`follow_redirects=False`); §4.7/§4.8 grep: no `expanduser` in client.py, no `pragma: no cover` in src/; §5.2 route_catalog.py:33-44,255 (HTTP_METHODS filter); §5.3 TYPED_EXACT_PATHS/TYPED_PATH_PREFIXES (route_catalog.py:46-112); §5.5 DEPLOYMENT_ALIASES hoisted (151); §6.1/§6.2 service.py:61-70; §6.4 `set[RouteClassification]` (service.py:94); §6.5 ActionSpec docstring (service.py:33-35); §7.1 server.py:505-523 (`model_validate`); §7.2 server.py:531-535 (`sys.exit(2)`); §7.3 server.py:199-213 + service.py:100-101; §7.4 ToolError boundary (server.py:123-124, 299-300); §7.5 server.py:129 (dynamic `Literal`); §7.6 `split_csv` used in config.py:87 + server.py:151; §8.2-8.4 tool_definitions.py:39-42, 562; §8.5 DEFAULT_TOOL_PROFILES single-sourced (config.py:17, imported tool_definitions.py:9); §9.2 `__init__.py` + pyproject both `0.2.0`; §9.3 vulture `ignore_decorators` = `@pytest.fixture` only (click entries gone); §9.4 `.github/workflows/ci.yml` present (ruff/mypy/pytest); §10.1-10.4 conftest + drift guards + marker removal verified above. |
| 5 | No public name removed | PASS | grep-verified definitions + green imports in the suite: `DISCOVERY_TOOL_NAMES` (tool_definitions.py:434), `ESCAPE_HATCH_TOOL_NAMES` (:440), `ALL_TOOL_NAMES` (:444), `TOOL_PROFILES` (:562), `TOOL_SPECS` (:45), `FAMILY_TOOL_SPECS_BY_NAME` (:442), `DEFAULT_TOOL_PROFILES` (config.py:17), `MULTIPART_BODY_ERROR` re-exported from models (models.py:11,17) and imported by test_models.py:10/test_server.py:15; all 11 original+new error classes importable from `mcp_litellm.errors` (test_errors.py:12-25 passes). |
| 6 | Security findings: real fixes | PASS | §2.3: enforcement is in the client (`client.py:182-183` raises `LocalFileUploadNotAllowedError` **before** URL/headers/file-open) and transport-gating in `server.py:382-394` (`transport != "stdio"` and `"allow_local_file_uploads" not in settings.model_fields_set` → resolved False, applied via `model_copy` in `build_server`). Test asserts both the raise and `not router.calls`. §7.3: `_compute_denied_route_keys` (server.py:199-213) subtracts active-family route keys; denial enforced in `service.execute_route_key` (service.py:100-101) **before** the classification check and before any HTTP. The test's denied route `GET /config/cost_discount_config` is `typed` (prefix `/config/`), which `native_request` otherwise allows (`{"typed","generic_native"}`) — so the ToolError can only come from the denylist; the test genuinely exercises the boundary. |
| 7 | Spec-flagged risk items | PASS | `test_family_tool_action_param_has_enum` asserts `inputSchema["properties"]["action"]["enum"] == sorted(actions)` against the live `server.list_tools()` output (test_server.py:156-170; annotation set at server.py:129). `test_lifespan_closes_client` spies `LiteLLMClient.aclose` and asserts **exactly 1** call after entering/exiting `server.lifespan` (test_server.py:212-232; lifespan wired at server.py:417-437). |
| 8 | Lint/type/vulture clean | PASS | `ruff check .` → "All checks passed!"; `mypy` → "Success: no issues found in 22 source files"; `vulture` → exit 0, no output. |

**Observations / follow-ups (non-blocking, for orchestrator):**
1. **§7.3 allow-side assertion missing.** The Test Spec (and Risk #5) promised `test_native_request_denies_disabled_family_routes` would also show "a still-enabled typed route is allowed"; the landed test asserts only the deny side (this was true of the tester's original too — not a recovery weakening). Nothing in the suite proves `native_request` still permits non-denied routes, so a hypothetical deny-everything regression would pass the suite (the multipart test at test_server.py:110 errors at validation, before denial). Suggest a follow-up micro-test using respx behind `server.call_tool`.
2. **Escape-hatch semantics note.** `_compute_denied_route_keys` treats every *inactive* family as disabled, so under `native_escape_hatch`-only profiles all family-owned typed routes are denied via `litellm_native_request`. This matches TOOLS.md ("Discovery plus generic native route calls") but is a behavior change vs. pre-wave and is unpinned by tests — worth a line in TOOLS.md.
3. **Minor test-strength nits (tester-original, not recovery):** `test_default_openapi_path_raises_when_absent` asserts `"_data" in msg or "openapi" in msg` rather than both probed paths (source does list both); `test_main_unknown_profile_exits_cleanly` asserts `code != 0` vs. spec's `code 2` (source exits 2); `test_reuses_single_async_client` asserts `<= 1` (0 would pass, though a real request cannot avoid instantiation). The non-stdio upload-gating resolution (`_resolve_allow_local_file_uploads`) has no direct test — per the plan's Coverage Table that's acceptable (§2.3 maps to the blocked-upload test), but a one-liner would pin it.

**Rules:**
- Dispatches sized by token budget (~125k) — not by finding, module, or theme.
- One tester → one engineer → one QA. Engineer splits only on token-budget/tooling.
- No deletion-only wave here (changes are modifications + net-new), so the tester phase is required.

## Operator Nudges

*Update immediately when operator corrects approach. Do not batch or defer.*

1. **No agents during review** — operator required the adversarial review be done solo; the review (input to this plan) was authored without dispatch. (Implementation may use agents per the standard pipeline, per the `/implement` instruction.)
2. **No deferrals** — every actionable finding must be remediated in this plan; the two security findings (§2.3, §7.3) get real fixes, not documentation-only.

## Tool Errors and Infrastructure Failures

*Log as they occur, not reconstructed at close-out.*

| Error | Frequency | Context | Resolution |
|-------|-----------|---------|------------|
| `run_gate_check` unavailable (`[tool.aawm.gate]` unconfigured) | persistent | This standalone repo isn't aawm-gate-managed | Substituted repo-native `uv run --no-sync ruff/mypy/vulture/pytest` + `pre-commit run --all-files` for Wave 0 baseline, CO-1, CO-2 |
| Auto-mode classifier blocked salvage agent's `python -m pytest` / `python -c` | 2× (salvage dispatch) | Salvage (haiku) used banned invocations; got `No module named mcp_litellm` from bare `python` | Corrected via SendMessage (use `uv run --no-sync`); ultimately pivoted to a sonnet engineer |
| Salvage (haiku) terminated early mid-task | 2× | Returned truncated thoughts at 30–38 tool uses without landing | Abandoned salvage path; dispatched sonnet engineer (Dispatch 2c) which completed reliably |
| `.pre-commit-config.yaml` actionlint hook passed redundant `actionlint` token | 1× (first land of a workflow file) | rhysd/actionlint image ENTRYPOINT is already `actionlint`; the token was read as a filename → exit 3 | Engineer dropped the duplicate token (commit `68728d7`); latent bug surfaced by the new `ci.yml` |

## Hindsight

Self-generated at close-out from execution evidence (≥5 items):

1. **The risk was in the tests, not the source — I budgeted backwards.** Pre-execution I rated the 14-file breadth as the main risk and verified every *source* mechanism at spec time (Literal enum, lifespan, model_fields_set). The engineer's source landed clean on the first try. What actually broke was the **test suite**: 5 respx router-binding bugs + a spec-flawed env meta-test + 22 stale `# type: ignore` from the red phase. Lesson: when the spec mandates `warn_unused_ignores=true` + a heavy respx surface + an env-hermeticity test, pre-brief the **tester** on those exact footguns (respx `as router` binding; ignores that vanish at green; you cannot plant an env var after an autouse clearing fixture).

2. **My own spec contained the worst test bug.** `test_settings_ignores_ambient_env` (§10.1) was logically impossible — it planted `MCP_LITELLM_TOOL_PROFILES=full` *after* the autouse fixture and expected it ignored, which pydantic-settings can never do. The tester faithfully implemented my flawed spec. Lesson: when specifying a *meta-test* that verifies a fixture, write the assertion against the fixture's guarantee (no ambient var survives), not against a post-fixture plant.

3. **Two dispatches (≈67k tokens + wall time) were wasted on the haiku salvage agent.** Salvage stopped early twice and never touched a test file. The salvage agent type is haiku and proved unreliable for multi-step copy-fix-land work. Lesson: for recovery work that requires running the full toolchain and landing, dispatch a **sonnet engineer** with explicit test-edit authorization rather than the haiku salvage agent — the salvage path's value (rescue/cherry-pick) didn't apply here since the stuck work was uncommitted.

4. **Propagated command bans bit a sub-agent.** My global "never `python -c` / never bare pytest" guidance reached the salvage agent, whose attempts were then *blocked by the classifier*, and it misread the resulting `No module named mcp_litellm` as an environment failure. Lesson: when banning command forms, always pair the ban with the **exact allowed form** (`env UV_CACHE_DIR=… uv run --no-sync pytest`) in the dispatch prompt so a blocked attempt has an obvious fallback.

5. **The TDD red/green split needed an explicit carve-out for regression guards.** Several planned tests (typed-set hash, generic_native count, int-coercion, URL-encoding, description-drift) legitimately PASS at red time because they pin pre-existing behavior. I anticipated this and told the tester — which worked (39 red / 34 green) — but it's a recurring friction point. Lesson: standardize a "guard vs red" label in the Test Spec so the tester never force-fails a regression pin.

6. **The gate-tool mismatch should have been caught in planning, not Wave 0.** The plan assumed `run_gate_check`; this standalone repo has no `[tool.aawm.gate]`. I adapted cleanly at Wave 0, but the Infrastructure Prerequisites Checklist could have flagged "gate tooling configured?" up front. Lesson: add a prereq row verifying the gate/CI mechanism the plan's CO steps depend on actually exists in *this* repo.

7. **QA earned its keep by proving non-vacuousness, not just running tests.** QA re-ran the suite with `MCP_LITELLM_TOOL_PROFILES=full` planted to prove the hermeticity fixture genuinely works, and diffed `d6f2606→acaafe6` to confirm the recovery didn't weaken assertions. That independent adversarial check is exactly what caught the §7.3 deny-only coverage gap. Lesson: this is the bar for QA — reproduce the threat, don't just confirm green.

## Execution Outcome (close-out)

- **Status:** all waves complete. Wave 1 + QA follow-ups (1-d) landed; QA PASS.
- **Final state on develop @ `7ae6432`:** 74 tests pass; ruff/mypy(22 files)/vulture/gitleaks/actionlint all clean; version `0.2.0` in `pyproject.toml` + `__init__.py`.
- **All 41 actionable findings remediated** (QA-verified against the Coverage Table); the 3 QA follow-ups closed in Dispatch 1-d.
- **CO-1 gate check:** PASS (ruff format/check, mypy, vulture, gitleaks, actionlint, 74 tests). **CO-2 smoke:** PASS (4/4 smoke + deterministic toolset builds).
- **Landed commits:** `d6f2606` (tests), `d3717f2`+`68728d7` (source+fixes, merge `acaafe6`), `a07b8fb` (QA follow-ups, merge `7ae6432`).

### Consolidated Dispatch Log

| Wave | Phase | Agent | Model | Result | Commit(s) |
|------|-------|-------|-------|--------|-----------|
| 1 | a (test) | tester | sonnet | LANDED — 48 tests, 39 red/34 guard-green | `d6f2606` |
| 1 | b (impl) | engineer | sonnet | IMPLEMENTED, did not land (test defects blocked) | (uncommitted) |
| 1 | 2b (recovery) | salvage | haiku | ABANDONED — copied source, stopped early ×2 | (none) |
| 1 | 2c (recovery) | engineer | sonnet | LANDED — source + 4 test-defect fixes + actionlint-hook fix | `d3717f2`,`68728d7` |
| 1 | c (qa) | qa | sonnet | PASS — all 41 findings verified, 3 non-blocking follow-ups | — |
| 1 | d (qa follow-ups) | engineer | sonnet | LANDED — allow-side test, gating test, 3 nits tightened, TOOLS.md line | `a07b8fb` |

### Metrics

| Metric | Value | Source |
|--------|-------|--------|
| Total agent dispatches | 6 | tester, engineer, salvage, engineer (2c), qa, engineer (1d) |
| Successful first-attempt | 4 of 6 | tester, engineer-impl (source correct but blocked by tests), qa, hardening |
| Failed/retried | salvage ×2 (abandoned) + 1 recovery engineer | Dispatch Log |
| Land deadlock recoveries | 1 (3 dispatches to clear) | salvage→salvage-resume→engineer-2c |
| Git commits to develop | 4 content (+3 merges) | `d6f2606`,`d3717f2`,`68728d7`,`a07b8fb` + 3 merge commits |
| Tests | 26 → 74 (+48 new: 47 in `d6f2606`, 1 in `a07b8fb`) | pytest |
| Findings remediated | 41 of 41 actionable | QA Coverage Table |
| Session duration | ~ (spec + implement, single session) | — |
| Biggest time waste | salvage (haiku) ×2 early terminations | Hindsight #3 |

## If I Could Start This Plan Over

Actionable, plan-specific changes (doubles as suggested template/process adjustments):

1. **Pre-brief the tester on the three test footguns this spec creates.** Add a Test Spec note: (a) respx requires `with respx.mock(...) as router:` + `router.get` — never module-global `respx.get` inside a nested `respx.mock()`; (b) under `warn_unused_ignores=true`, every red-phase `# type: ignore` on a not-yet-existing symbol must be removed once green; (c) you cannot verify an autouse env-clearing fixture by planting a var *after* it. This would have prevented all 7 land-blocking defects and the entire 3-dispatch recovery.

2. **Fix the §10.1 meta-test in the spec itself.** Specify `test_settings_ignores_ambient_env` as "assert no `MCP_LITELLM_*` survives the fixture, then assert defaults hold" — not a post-fixture plant. My spec shipped a logically impossible test.

3. **Never route recovery/land work to the haiku salvage agent.** Use a sonnet engineer with explicit test-edit authorization. Salvage's rescue/cherry-pick value didn't apply (stuck work was uncommitted), and the haiku agent terminated early twice. Suggested dispatch-rule update: "salvage is for cherry-pickable committed work; for uncommitted copy-fix-land recovery, dispatch a sonnet engineer."

4. **Pair every command ban with the allowed form in the dispatch prompt.** The salvage agent's `python -m pytest` was classifier-blocked and it floundered. Always include `env UV_CACHE_DIR=… uv run --no-sync pytest` as the explicit substitute.

5. **Add a planning prereq: "does this repo have the gate/CI tooling the CO steps assume?"** `run_gate_check` was unconfigured here; caught at Wave 0, but the Infrastructure Prerequisites Checklist should verify it up front and pre-authorize the repo-native substitute.

6. **Standardize a "guard vs red" label in the Test Spec** so the tester never force-fails regression pins (typed-set hash, generic_native count, etc.) that legitimately pass at red time.

## Suggested Persona and Template Adjustments

- **Dispatch rules:** add the salvage-vs-engineer recovery rule (item 3 above).
- **Plan template (Test Spec):** add a "tester footguns" subsection prompt (respx binding, stale type-ignores at green, autouse-fixture meta-tests) and a "guard vs red" label (item 6).
- **Infrastructure Prerequisites Checklist:** add a "gate/CI tooling present in this repo?" row (item 5).
- **Eyes/context injection:** none needed — no persona context records were changed by this plan.

---

## Phase 3 — Validation

### Coverage Table

Every actionable finding mapped to where it is satisfied (all in Wave 1):

| Finding | Satisfied by (Source Spec step / Test) |
|---------|----------------------------------------|
| §1.1 openapi fallback raises | config step 4 / `test_default_openapi_path_raises_when_absent` |
| §1.2 JSON-array strip | config step 4 / `test_json_array_tool_list_strips_whitespace` |
| §1.3 set ordering | config step 4 / `test_set_input_is_sorted_deterministically` |
| §1.4 `_ = cls` removal | config step 4 / lint (ruff) |
| §1.5 port range | config step 4 / `test_port_rejects_out_of_range` |
| §1.6 dead `env_nested_delimiter` | config step 4 / suite still green |
| §2.1 dup multipart message | errors step 2 + models step 3 / `test_multipart_body_error_uses_shared_constant` |
| §2.2 path-param None/bool | models step 3 / `test_path_params_reject_none_value`, `_reject_bool_value` |
| §2.3 arbitrary file read | config+client+server steps 4/5/9 / `test_multipart_blocked_when_uploads_disabled` |
| §2.4 file-delete race | client step 5 / `test_multipart_file_deleted_after_validation_raises_clean_error` |
| §2.5 None in query list | client step 5 / `test_none_query_list_member_dropped` |
| §3.1 KeyError quoting | errors step 2 / `test_unknown_route_error_message_not_quoted` |
| §3.2 common base | errors step 2 / `test_all_errors_subclass_common_base` |
| §3.3 retain fields | errors step 2 / `test_errors_retain_structured_fields` |
| §4.1 client pooling | client+server steps 5/9 / `test_reuses_single_async_client`, `test_lifespan_closes_client` |
| §4.2 parse-error wrap | client step 5 / `test_malformed_json_raises_parse_error`, `test_declared_text_bad_encoding_falls_back_to_base64` |
| §4.3 redirect leak | client step 5 / `test_does_not_follow_redirects` |
| §4.5 None query | client step 5 / `test_none_query_values_dropped` |
| §4.6 multipart None field | client step 5 / `test_multipart_none_field_omitted` |
| §4.7 dup expanduser | client step 5 / suite green |
| §4.8 pragma no cover | client step 5 / `test_transport_error_wrapped` |
| §4.9 untyped envelope | models step 3 + client/service / `test_litellm_response_typeddict_importable` |
| §5.1 default-allow guard | route_catalog step 6 / `test_generic_native_baseline` |
| §5.2 path-item iteration | route_catalog step 6 / `test_non_http_method_path_item_keys_ignored` |
| §5.3 prefix over-match | route_catalog step 6 / `test_no_typed_prefix_shadows_another`, `test_typed_classification_set_is_stable` |
| §5.4 redundant `==` | route_catalog step 6 / suite green |
| §5.5 hoist alias dict | route_catalog step 6 / suite green |
| §5.6 double resolve | route_catalog step 6 / suite green |
| §6.1 empty path param | service step 7 / `test_render_path_rejects_empty_value` |
| §6.2 surplus keys | service step 7 / `test_render_path_rejects_surplus_keys` |
| §6.3 envelope layering | models/service steps 3/7 / TypedDict + mypy |
| §6.4 `set[str]` typing | service step 7 / mypy |
| §6.5 ActionSpec intent | service step 7 / comment (documented as intentional) |
| §7.1 model_copy no validate | server step 9 / `test_resolve_settings_validates_overrides` |
| §7.2 raw traceback | server step 9 / `test_main_unknown_profile_exits_cleanly` |
| §7.3 disable bypass | server step 9 / `test_native_request_denies_disabled_family_routes` |
| §7.4 error boundary | server step 9 / clean `ToolError` messages (covered by §7.3 + native error tests) |
| §7.5 action enum | server step 9 / `test_family_tool_action_param_has_enum` |
| §7.6 CSV dup | _parsing step 1 + config/server / suite green |
| §7.7 redundant naming | server step 9 / suite green |
| §8.2 description drift | tool_definitions step 8 / `test_every_action_name_appears_in_description` |
| §8.3 mutable dict | tool_definitions step 8 / `test_tool_spec_actions_is_read_only_mapping` |
| §8.4 profile name dup | tool_definitions step 8 / `test_tool_profiles_keys_match_names` |
| §8.5 default profile dup | config+tool_definitions steps 4/8 / `test_default_tool_profiles_constant_matches_settings_default` |
| §9.1 fallback rationale | config step 4 / comment (with §1.1) |
| §9.2 version regression | __init__/pyproject steps 10/11 / `test_version_is_bumped` |
| §9.3 vulture click | pyproject step 11 / vulture clean |
| §9.4 no CI / actionlint | ci.yml step 12 / workflow present, actionlint passes |
| §10.1 hermetic tests | conftest step 14 / `test_settings_ignores_ambient_env` |
| §10.2 error-path tests | tester wave / the client/service/errors cases above |
| §10.3 drift guards | tester wave / typed-set, generic_native, description, prefix-shadow tests |
| §10.4 redundant markers | tester wave / decorators removed, suite green |

**Non-actionable (no work — recorded so they're demonstrably not missed):** §1.7, §4.4,
§5.7, §6.0, §6.6, §7.0, §8.1, §8.6, §9.5, §10.5 (RESOLVED/CORRECTED/GOOD/OBSERVATION in
the review). §9.1's only action (a clarifying comment) is folded into §1.1.

### Alternatives Considered

1. **§5.1 pure default-deny (unknown routes → excluded) instead of a snapshot guard.**
   Rejected: `generic_native` *is* the escape hatch's whole purpose
   (`litellm_native_request` exists to call it); default-deny would gut the feature and
   break `test_route_catalog_classifies_generic_native_route`. The review explicitly
   offered "a CI check that diffs classifications" as the alternative — the baseline
   tests implement exactly that, surfacing new routes for conscious review without
   removing capability.
2. **§7.3 documentation-only ("filtering is ergonomic, not a boundary").** Rejected:
   operator mandated real fixes for security findings; the denylist makes
   `--disable-tool` an actual boundary, which is the stronger and testable choice.
3. **Splitting into multiple waves by module/theme.** Rejected: violates token-budget
   sizing (the work fits one engineer) and the changes share foundations (`McpLiteLLMError`,
   `LiteLLMResponse`, `split_csv`) that would force awkward cross-wave dependencies.

### Self-Critique

- **The weakest part of this spec is** the route-catalog prefix re-bucketing (§5.3 / step 6).
  I verified `/search` is the only *currently* over-matching bare prefix, but the engineer
  must hand-derive the exact/prefix split for ~60 entries; the safety net is
  `test_typed_classification_set_is_stable` pinning all 317 typed keys, so a wrong bucket
  fails loudly rather than shipping — but it could cost the engineer an iteration or two.
- **The biggest assumption I made is** that FastMCP's `lifespan` parameter cleanly closes
  the pooled `httpx.AsyncClient` across all three transports (stdio/sse/streamable-http).
  I confirmed the parameter exists and accepts an async context manager, but I verified
  shutdown semantics only by signature, not by running each transport; `test_lifespan_closes_client`
  exercises the context manager directly to compensate.
- **The thing most likely to need revision after first execution** is the escape-hatch
  denylist computation (server step 9): the rule "route keys of disabled families minus
  route keys owned by still-active families" assumes each typed route is owned by at most
  one family. If the vendored spec has a typed route mapped by two families, the
  subtraction logic may need refinement — the test covers the common case but not that
  overlap, which the engineer should check while deriving the denylist.

---

## Researcher Review

**Date:** 2026-06-11
**Reviewer:** researcher
**Verdict:** APPROVED

### Findings

#### 1. Spec-to-Outcome Consistency — PASS (with one minor narrative drift)

All 41 actionable findings are demonstrably remediated. Every symbol named in the Source Spec exists and is reachable: `McpLiteLLMError` (errors.py:8), `LiteLLMResponse` TypedDict (models.py:34), `split_csv` (\_parsing.py:6, imported and invoked in config.py:87 and server.py:151), `Settings.allow_local_file_uploads` (config.py:57), `DEFAULT_TOOL_PROFILES` (config.py:17, single-sourced and imported by tool_definitions.py:9), `TYPED_EXACT_PATHS`/`TYPED_PATH_PREFIXES` (route_catalog.py:46,69), `_resolve_settings`/`lifespan`/`_compute_denied_route_keys` (server.py:199,418,505), and `litellm_native_request` registration (server.py:269). The action `Literal` enum is set at server.py:129 via `Literal.__getitem__`. Not one of the 41 findings lacks a corresponding landed symbol or test.

**Minor narrative drift:** The Dispatch 1 outcome states "48 new test functions" but the actual count from `d6f2606` is 47 new functions (the spec specified one `test_port_rejects_out_of_range` but the tester correctly split it into `_high` and `_zero` variants, netting 47 rather than 48 in that commit). The 48th function (`test_resolve_allow_local_file_uploads_gated_by_transport`) arrived in `a07b8fb`. The total of 74 is accurate (26 original + 47 + 1 = 74). This is a narrative precision issue, not a functional gap.

**Second minor item:** The Metrics table entry "Git commits to develop: 5" lists four content hashes (`d6f2606`, `d3717f2`, `68728d7`, `a07b8fb`) with "+ merges." There are actually 4 content commits and 3 merge commits (b659379, acaafe6, 7ae6432), totalling 7 git objects. The "5" figure is internally inconsistent in the table.

Neither of these affects the correctness of the implementation.

#### 2. Deviation Documentation — PASS

All deviations are documented transparently with rationale:

- **Engineer source not landing (Dispatch 2):** The plan clearly explains why — test defects in the tester-landed files blocked a clean merge, not source bugs. The decision to escalate rather than have the engineer edit tests is documented and the root causes (respx router-binding, `assert_all_called` misuse, spec-flawed env meta-test, stale mypy ignores) are enumerated with evidence.
- **Salvage → Engineer recovery path:** The haiku salvage agent's two early terminations are logged in the Tool Errors table and dispatched log. The decision to pivot to a sonnet engineer with explicit test-edit authorization is explained and cross-referenced in Hindsight #3.
- **Actionlint hook fix:** The `pre-commit-config.yaml` fix (dropping the redundant `actionlint` token that was being treated as a filename) is documented as an incidental infra fix surfaced by the new `ci.yml`, and the fix appears correctly in `68728d7`.
- **`0.0.1rc2` → `0.2.0` version:** The plan documents the version as `0.2.0`, not `0.0.1rc2`; both `__init__.py` and `pyproject.toml` confirm the bump. The "0.0.1rc2" reference in the task prompt refers to the original stale version that predated this wave — the plan tracks the before (`0.1.0`) and after (`0.2.0`) correctly and the source matches.
- **Wave 0 gate-tool substitution:** `run_gate_check` being absent is explicitly noted and the substitution (repo-native `uv run --no-sync`) is pre-authorized and consistently applied.

#### 3. Lessons-Learned Quality — PASS

Seven Hindsight items and six "If I Could Start This Plan Over" items are all specific, evidence-backed, and referenced to real wave/agent/finding events:

- Items cite concrete agent IDs, dispatch phases, and finding numbers (§10.1 meta-test flaw, respx binding pattern, haiku salvage agent reliability, `warn_unused_ignores` footgun).
- The "guard vs red" label distinction is a real operational gap that the tester hit (39 red / 34 green was a known-correct split, but it required pre-briefing to avoid force-failing regression pins).
- The process improvement for salvage dispatch (haiku → sonnet for copy-fix-land recovery) is actionable and specific.
- No items are platitudes. Each one names the specific failure mode and the corrective action.

One enhancement opportunity: Hindsight #7 mentions QA "re-ran the suite with `MCP_LITELLM_TOOL_PROFILES=full` planted" but this is not directly reflected in the If I Could Start This Plan Over list — there's no item suggesting QA instructions be standardized to "reproduce the threat scenario, not just run the test suite." This is a gap in the process-improvement section, not a factual inaccuracy.

#### 4. Gap Detection — ONE OPEN ITEM (tracked, non-blocking)

The QA observations section (lines 444–447) identifies three follow-up items, all of which were addressed in Dispatch 1-d (`a07b8fb`):

- §7.3 allow-side assertion: added to `test_native_request_denies_disabled_family_routes`; verified non-vacuous by inspection (the respx mock fails if the route never fires, and `assert structured_result["ok"] is True` would fail if the call was denied).
- §2.3 `_resolve_allow_local_file_uploads` direct test: added as `test_resolve_allow_local_file_uploads_gated_by_transport`; covers stdio True, streamable-http default False, and explicit opt-in True.
- Three test-strength nits: all tightened (both path fragments asserted, `code == 2`, `count == 1`).
- TOOLS.md updated with a note on inactive-family route denial.

**One residual gap not in the plan:** QA observation #2 notes that the escape-hatch semantics under `native_escape_hatch`-only profiles (all family-owned typed routes denied through `litellm_native_request`) is "unpinned by tests — worth a line in TOOLS.md." The TOOLS.md update (`a07b8fb`) adds a single line on this behavior. However, the QA report says the behavior itself "is a behavior change vs. pre-wave" — this claim is unverified in the plan (there is no before/after behavioral comparison). The Self-Critique notes the subtraction logic assumes each typed route is owned by at most one family, and no test covers the overlap case. This remains an open informational gap but does not affect correctness of the landed code.

#### 5. QA Coverage — PASS (adversarial, not rubber-stamp)

QA independently verified non-vacuousness by:
- Re-running the suite with `MCP_LITELLM_TOOL_PROFILES=full MCP_LITELLM_PORT=9999` planted in the environment, confirming the hermeticity fixture blocks ambient injection.
- Diffing `d6f2606 → acaafe6` to confirm no assertion was weakened or removed during the recovery — each of the four fix categories is justified and the assertion body of all affected tests was reviewed.
- Identifying the §7.3 allow-side gap independently of the dispatch log.
- Confirming the security boundary tests (§2.3 and §7.3) exercise the enforcement *before* any HTTP escapes (not just after-the-fact error checking).

The QA section references specific line numbers in source and tests, not just grep patterns or test names. This is genuine adversarial QA.

#### 6. Implementation Wiring — VERIFIED END-TO-END

Confirmed via live execution and grep:

| Check | Result |
|-------|--------|
| `McpLiteLLMError` base — all 11 error classes inherit it | ✅ errors.py:8–102 |
| `LiteLLMResponse` TypedDict — returned by client and service | ✅ client.py:26,124; service.py:74,97,112 |
| `split_csv` — imported and invoked (not dead) | ✅ config.py:13,87; server.py:18,151 |
| `TYPED_EXACT_PATHS` frozenset + `TYPED_PATH_PREFIXES` tuple | ✅ route_catalog.py:46,69; `test_typed_classification_set_is_stable` green |
| `_resolve_settings` / `lifespan` / `_compute_denied_route_keys` | ✅ server.py:199,418,505 |
| `litellm_native_request` registered | ✅ server.py:269; guarded by tool-profile check at :457 |
| `Literal` action enum surfaces in `inputSchema` | ✅ server.py:129; `test_family_tool_action_param_has_enum` green |
| Shared `httpx.AsyncClient` with double-checked locking | ✅ client.py:41–58 |
| `aclose` called exactly once in lifespan exit | ✅ server.py:422; `test_lifespan_closes_client` green |
| `follow_redirects=False` | ✅ client.py:51 |
| Error boundary `McpLiteLLMError/ValidationError` → `ToolError` | ✅ server.py:123–124, 299–300, 317–318 |
| `MappingProxyType` on `ToolSpec.actions` | ✅ tool_definitions.py:42 |
| Full suite: 74 passed, ruff/mypy(22 files)/vulture/gitleaks/actionlint clean | ✅ verified live |

**Vulture clarification:** Running `vulture src/` alone reports `cls` as unused (100% confidence) in `config.py` and `models.py`. This is a known vulture false-positive for `@classmethod`-stacked `@field_validator` functions in Pydantic v2 — `cls` is required by the descriptor protocol. Running `vulture` with the `pyproject.toml` config (paths include `tests/`) exits 0 because the tests directory provides sufficient whitelist coverage. Pre-commit uses the pyproject config and passes. This behavior is not a regression introduced by this wave — the `_ = cls` suppression removed by §1.4 was working around this same false-positive. The pre-commit path remains the authoritative check.

#### 7. Infrastructure Readiness — PASS

- No DB, no migration, no container restart required (stdio/HTTP MCP server confirmed).
- `.github/workflows/ci.yml` is actionlint-valid: `pre-commit run actionlint --all-files` → Passed.
- Pre-commit full run (`ruff format`, `ruff check`, `mypy`, `vulture`, `gitleaks`, `actionlint`) → all Passed.
- The actionlint hook fix (dropping the redundant `actionlint` argument from the docker entrypoint command) is confirmed correct in `.pre-commit-config.yaml` — the hook now passes `bash -lc 'docker run ... rhysd/actionlint:1.7.12 "$@"' --` where `"$@"` receives the workflow file paths from pre-commit's `files:` filter.

#### 8. Plan-to-Implementation Alignment — PASS (one commit message anomaly)

| Commit | Planned scope | Actual scope | Alignment |
|--------|--------------|--------------|-----------|
| `d6f2606` | All failing tests per Test Spec | 47 new test functions across 9 files; smoke/; regression guards green | ✅ aligned |
| `d3717f2` | Source + 4 authorized test-defect fixes | All 9 source files + pyproject + 8 test file fixes + smoke rewrite | ✅ aligned |
| `68728d7` | New files not in tracked stage | `.github/workflows/ci.yml`, `src/mcp_litellm/_parsing.py`, `.pre-commit-config.yaml` fix | ✅ aligned |
| `a07b8fb` | QA follow-ups (3 nits + allow-side + gating test + TOOLS.md) | Exactly those + no source changes | ✅ aligned |

**Commit message anomaly:** `d6f2606` uses scope `test(db)` — there is no database in this project. This is almost certainly a template artifact (the tester agent's commit scaffolding defaults). It is a cosmetic issue only; the commit body is accurate. The QA follow-up commit (`a07b8fb`) correctly uses `test(api)`. Worth a note for dispatch template hygiene.

**Source Spec alignment spot-checks:**
- exact/prefix split preserving the typed-set sha256: `TYPED_EXACT_PATHS` (frozenset, 18 entries) + `TYPED_PATH_PREFIXES` (tuple, 42 entries); `test_typed_classification_set_is_stable` pins count=317 and sha256 `8d73e94c…dacb76d` — same digest captured at red time against pre-refactor source.
- TypedDict: `LiteLLMResponse(TypedDict, total=False)` with all 13 keys from the spec (ok, status_code, content_type, headers, data, text, base64, method, path, route_key, summary, classification, action).
- Error base reparenting: `UnknownLiteLLMRouteError(McpLiteLLMError, LookupError)` — NOT `KeyError`, matching spec.
- `_parsing.py` is 15 lines, imported in both `config.py` and `server.py`, not dead code.

### Recommendations (if NEEDS_REVISION)

*N/A — verdict is APPROVED.* The following are advisory items for future reference:

1. **Commit message scope hygiene:** Add a note to the dispatch template that the tester agent's commit scope should be `test(api)` or `test(unit)`, not `test(db)`, in a project with no database. One-line addition to the tester dispatch prompt.

2. **Vulture `cls` false-positive:** Consider adding `"cls"` to `ignore_names` in `[tool.vulture]` in pyproject.toml. Running `vulture src/` in isolation currently produces false-positive warnings that could confuse a developer not using the full pre-commit suite. The pre-commit path (which includes `tests/`) works correctly, but the asymmetry is a footgun.

3. **Overlap case in denylist logic:** The Self-Critique flags the assumption that each typed route is owned by at most one family. A follow-up verification (grep the tool spec actions for any route key appearing in two different `ToolSpec.actions` dicts) would close this open informational gap with minimal effort.

4. **QA process note:** The "reproduce the threat scenario" QA technique (planting env vars, running deny + allow sides of security tests) that made QA valuable here should be codified in the QA dispatch template as a standard step, not left as initiative-dependent.
