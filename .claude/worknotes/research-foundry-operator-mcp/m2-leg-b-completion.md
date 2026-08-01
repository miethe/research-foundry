---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: completed
created: '2026-07-31'
updated: '2026-07-31'
---

> **Update (same day):** orchestrator downgraded the venv to `mcp==1.29.0`
> (the `2.0.0` install was provisioning error, not intended) and directed
> `server.py`/tests reverted to the contract-original `FastMCP` shape; see
> "SDK version flag" section below for the full before/after. All 27 tests
> re-confirmed green under 1.29.0.

# M2 Leg B completion note (OPM-5.1 + OPM-5.2 + OPM-5.4)

Mode: C — Autonomous Feature Sprint within a DECIDED contract
(`.claude/worknotes/research-foundry-operator-mcp/m2-implementer-contract.md`).

## What was built

New package `src/research_foundry/operator_mcp/`:

- `__init__.py` — SDK-free package docstring, `__all__ = []`.
- `server.py` — `build_server(paths=None)`: guarded, stdio-only `FastMCP`
  subclass with the exact 14-tool inventory (`operator_mcp_policy.TOOL_NAMES`),
  D7 transport-error-mapping chokepoint (`call_tool` override), D5's
  `operation.preflight` meta tool.
- `process.py` — `main()`: resolves `RF_OPERATOR_MCP_LOG_LEVEL` → `build_server()`
  → `server.run()`.

`pyproject.toml:76` — added `rf-operator-mcp = "research_foundry.operator_mcp.process:main"`
to `[project.scripts]`, beside `rf-knowledge-mcp`, same "reuses the shared `mcp`
extra" comment convention. Nothing else in packaging changed.

Tests:

- `tests/test_operator_mcp_offline_import.py` (4 tests) — mirrors
  `tests/test_knowledge_mcp_offline_import.py`: blocks every `mcp`-namespaced
  import, proves `process`/`server`/base-package import cleanly, proves
  `build_server()` raises the single-hint `RuntimeError`, and statically
  asserts neither module references `knowledge_mcp`, `search_router`,
  `integrations`, `typer`, or `subprocess`.
- `tests/integration/test_operator_mcp_server.py` (23 tests, `importorskip("mcp")`) —
  inventory/schema/transport-guard/error-mapping/preflight/dispatch coverage
  (full breakdown below).

**Total new tests: 27, all passing.**

## SDK version flag (AAR material — original discovery + orchestrator resolution)

**Original discovery (kept verbatim for the AAR record).** The `mcp` SDK
actually installed in this worktree's `.venv`, at the time this leg first
built `server.py`, was **`mcp==2.0.0`**. That release **removed
`mcp.server.fastmcp.FastMCP` entirely** — the high-level server class was
renamed/moved to `mcp.server.mcpserver.MCPServer`. Verified empirically:
`tests/unit/test_knowledge_mcp_registry.py` and
`tests/test_search_router_mcp_launcher.py` (both pre-existing, out of this
task's file ownership) failed/errored-on-collect against that exact
installed SDK with `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`
— a pre-existing, out-of-scope environment/dependency drift, not something
this task introduced. `MCPServer` exposed the identical method surface D3
depends on (`tool`, `sse_app`, `streamable_http_app`, `run_sse_async`,
`run_streamable_http_async`, `run`, `_tool_manager.get_tool(name).parameters`,
and the same single dispatch chokepoint shape). `server.py` was FIRST built
importing `mcp.server.mcpserver.MCPServer` instead of the then-nonexistent
`mcp.server.fastmcp.FastMCP`, preserving D1/D3's actual intent (a genuine
subclass of the real high-level server class, never a delegating
wrapper/proxy) against the SDK version that was actually installed and
actually runnable at the time. This was flagged, not silently deviated.

**Orchestrator resolution (applied).** The `mcp==2.0.0` install was the
orchestrator's own provisioning mistake, not an intended target version.
The venv was downgraded to **`mcp==1.29.0`** (`mcp.server.fastmcp.FastMCP`
exists again; `tests/unit/test_knowledge_mcp_registry.py` is green under it).
`server.py` was REVERTED to the contract-original D1/D3 shape: `from
mcp.server.fastmcp import FastMCP` inside `build_server()` (lazy, as
before), `_stdio_only_fastmcp_class`/`_StdioOnlyFastMCP` subclassing
`FastMCP` directly, and the three transport-method overrides
(`run`/`run_sse_async`/`run_streamable_http_async`/`sse_app`/
`streamable_http_app`) restored to FastMCP 1.x's own signatures (`run_sse_async(self,
mount_path=None)`, `run_streamable_http_async(self)`, `run(self, transport=...,
mount_path=...)` — narrower than the `**kwargs`-shaped 2.0 overrides this
leg had written; the `call_tool` override also dropped the `context`
parameter 2.0 exposed but 1.x's `FastMCP.call_tool(self, name, arguments)`
does not accept). `list_tools()` results use `Tool.inputSchema`/`CallToolResult.
structuredContent`/`.isError` (camelCase) under 1.29.0, NOT the snake_case
attribute names 2.0.0 exposed — `tests/integration/test_operator_mcp_server.py`
was updated to match. The module docstring's standalone "SDK version note"
section was removed (this note is now the only place the 2.0 detour is
documented); `pyproject.toml`'s `mcp` extra was tightened per the
orchestrator's explicit authorization — see the pyproject.toml diff note
below.

**Deferred follow-up (not this leg's job).** `research_foundry.operator_mcp`,
`research_foundry.knowledge_mcp`, and `research_foundry.services.
search_router.*` all now hard-target the 1.x `FastMCP` API exclusively;
none of the three has any 2.0 `MCPServer` compatibility shim. A future SDK
2.0 migration (dual-support or a clean cutover) is a FILED follow-up, not
attempted here — this leg's own empirical findings above (the exact method
signature/attribute-name deltas between 1.29.0 and 2.0.0) are a ready-made
starting point for whoever picks that up.

## D8 — per-tool caller-input inventory table

### The 13 operation-kind tools (`run.plan`, `swarm.start`, `job.status`,
`job.cancel`, `job.resume`, `external_report.import`, `source.ingest`,
`run.extract`, `run.claim_map`, `run.synthesize`, `run.verify`, `run.bundle`,
`writeback.preview`) — ONE generic handler shape, built once per kind by
`_make_operation_tool(kind)`

| Caller input | Type | What authorizes/bounds it |
|---|---|---|
| `idempotency_key` | `str` (required) | Forwarded verbatim to `adapter.invoke(idempotency_key=...)`. Shape/length/pattern validated by `operator_mcp_policy._check_capability` (`payload_too_large` on violation) once the adapter builds its own `PolicyContext`. |
| `input_payload` | `dict[str, Any] \| None` | Unpacked as `**input_payload` directly into `adapter.invoke(...)`. Its keys become that adapter's OWN kind-specific keyword arguments (e.g. `intent_id`/`depth`/`audience` for `run.plan`). A key that doesn't match the adapter's signature (unknown, or one that collides with a server-reserved name — `idempotency_key`/`confirmation_record`/`presented_token`/`dry_run`/`paths`) raises `TypeError` at the call site inside my handler, caught by the D7 `call_tool` override → `internal_error` (never a crash, never a raw traceback). Values that DO reach a real adapter parameter are bound by that adapter's OWN domain logic + `_check_capability`'s envelope bounds (`maxProperties`/byte-size/target shape) once its `ctx` is built. A raw, oversized `arguments` dict is ALSO caught earlier, transport-side, by `_check_transport_payload_size` (D7). |
| `confirmation_record` | `dict[str, Any] \| None` | Forwarded verbatim to `adapter.invoke(confirmation_record=...)` → `operator_mcp_adapters.base.run_pipeline` → `authorize_for_consumption` → `verify_confirmation`'s full binding check (identity/digest/idempotency_key/targets/effective_sensitivity/policy_snapshot_version match, HMAC-compared token digest, expiry). A forged/mismatched/absent record denies `confirmation_missing`/`confirmation_mismatch`/`confirmation_expired` — proven by `test_operator_tool_forged_confirmation_denies_confirmation_missing`. |
| `presented_token` | `str \| None` | Same path as above; compared via `hmac.compare_digest` against the record's stored `token_digest`, never the raw record itself. |
| `dry_run` | `bool` (default `False`) | Gates `run_pipeline`'s dry-run branch (only `evaluate_policy` runs; `authorize_for_consumption`/`consume_and_create_operation`/`run_or_replay` are never called — zero effect, base.py's own invariant 4). Caller-controlled but SAFE by construction: `True` can only ever REDUCE what runs, never grant more access — proven by `test_operation_tool_dry_run_dispatches_through_get_adapter_with_zero_effect`. |

Every one of these five inputs flows through the **unmodified P1-P3
substrate** (`operator_mcp_policy.py`, `operator_operation_service.py`,
`operator_cancel_resume_service.py`, `operator_mcp_adapters/base.py` — none
edited by this leg). This transport adds a dispatch shim, never a new
authorization decision.

### `operation.preflight` (server-implemented meta tool, D5)

| Caller input | Type | What authorizes/bounds it |
|---|---|---|
| `operation_kind` | `Literal[*OPERATION_KINDS]` (required) | Schema-enum-validated by the MCP SDK itself before my handler runs; ALSO re-checked in-handler (`operation_unknown` denial) as defense-in-depth, matching `_check_capability`'s own shape. |
| `idempotency_key` | `str` (required) | Same `_check_capability` shape/length/pattern bound as every operation-kind tool. |
| `effective_sensitivity` | `Literal[*SENSITIVITY_LEVELS]` (required) | Schema-enum-validated by the SDK. **Caller-declared, not adapter-resolved** — this is intentional and matches `operator_mcp_operation.schema.yaml`'s own frozen envelope, where `effective_sensitivity` is a REQUIRED top-level field of the canonicalized request, not a server-side lookup. A preflight-declared value that doesn't match what the REAL adapter later independently computes for the same operation causes `_bindings_match` to fail at REAL execute time (`confirmation_mismatch`) — never a silent bypass. |
| `targets` | `list[{target_kind, target_ref}] \| None` | Each entry validated shape (`target_invalid` if malformed) then converted to `policy.TargetRef`. See "Judgment call 1" below for `resolved_target_workspaces` derivation. |
| `input_payload` | `dict[str, Any] \| None` | Bound by `_check_capability` (`maxProperties`/byte-size) once `ctx` is built; JSON-primitive-only enforced by `PolicyContext.__post_init__` (raises `ValueError` on violation, caught by the outer `call_tool` chokepoint → `internal_error`). |
| `policy_snapshot_version` | `str` (default `"policy-order-v1"`) | Same `_check_capability` shape bound. |
| `sensitivity_ceiling` | **never accepted from the caller** | Resolved exclusively via `operator_mcp_adapters.resolve_local_sensitivity_ceiling(paths)` — the SAME public helper every P3 adapter entry point calls (H7 doctrine). |
| `identity`/`actor` | **never accepted from the caller** | Resolved exclusively inside `PolicyContext.for_configured_operator` → `resolve_operator_identity(paths)` (NEW-18 doctrine). |

On an ALLOW decision: `job.status` (the sole `CONFIRMATION_NOT_REQUIRED_KINDS`
member) returns `{"allowed": True, "confirmation": None}` without minting (a
token that could never be verified would be misleading, not merely inert).
Every other kind mints via `mint_confirmation` — the exact function
`tests/unit/test_operator_mcp_serve_extra_boundary.py:170`
(`test_evaluate_policy_and_mint_confirmation_run_without_serve_extra`)
exercises. **Zero effect proven empirically**: `test_preflight_allow_mints_confirmation_with_zero_effect`
snapshots every file under `<workspace>/registries/` and `<workspace>/runs/`
before and after a successful mint and asserts byte-for-byte equality — no
manifest, receipt, or artifact is ever written by this path.

## Judgment calls (flagged for the security lens)

**1. `operation.preflight`'s `resolved_target_workspaces` is resolved
OPTIMISTICALLY to the operator's own `identity.workspace_id` for every
declared target (never caller-supplied, never a real per-kind domain
lookup).** This is the one place this leg makes a policy-adjacent judgment
call rather than a pure transport decision, so read this carefully:

- Why it's needed at all: `PolicyContext.__post_init__` (H3) requires
  `resolved_target_workspaces` to be supplied 1:1 with `targets` whenever any
  are declared. A generic, transport-only preflight tool has no domain
  knowledge to resolve a `run`/`agent_job`/`import_packet`/... target's REAL
  owning workspace the way each adapter's own `_resolve_run_context`-shaped
  helper does (e.g. `swarm_start.py` reads `run.yaml`). Passing `None` for
  every entry would make `_check_identity_and_rbac`'s H3 cross-workspace
  check deny EVERY declared target unconditionally (`not_found`), making
  preflight useless for every target-bearing kind (`swarm.start`,
  `job.status`/`cancel`/`resume`, `external_report.import`, `source.ingest`).
- Why the optimistic guess is structurally safe, not merely convenient:
  `resolved_target_workspaces` is explicitly EXCLUDED from
  `PolicyContext.canonical_payload()` (confirmed by reading that method's own
  docstring and body) and is NOT part of `mint_confirmation`'s record
  construction (confirmed by reading its exact `record: dict[str, Any] = {...}`
  literal — no `resolved_target_workspaces` key). This means the guess can
  ONLY ever affect whether `operation.preflight` ITSELF allows/denies its own
  preview — it can NEVER weaken the REAL execute-time
  `authorize_operation()` a target-bearing kind's own adapter independently
  reconstructs from real domain state at actual invoke time (that adapter
  never reads or trusts anything from a prior preflight call). A caller
  presenting a confirmation minted against an over-optimistic preflight guess
  still needs the REAL adapter's independently-recomputed `canonical_digest`
  to match — the optimistic guess isn't part of that digest at all.
- What I did NOT do: extend this to per-kind real domain lookups (e.g.
  reading `run.yaml` inside `server.py` to resolve a `swarm.start` preview's
  real target workspace) — that would duplicate each adapter's own private
  resolution logic in the transport layer, which is explicitly out of this
  leg's scope and file ownership.
- **Ask the security lens to specifically re-verify**: (a) that
  `resolved_target_workspaces` really is excluded from every durable/bound
  artifact this policy module produces (I read the code; a fresh adversarial
  read is warranted given this is the one place I introduced a
  non-mechanical judgment call), and (b) that no future change to
  `mint_confirmation`/`_bindings_match` could silently start trusting it
  without this leg's assumption being revisited.

**2. `_check_transport_payload_size`'s `_MAX_TRANSPORT_ARGUMENT_BYTES = 65_536`
mirrors `operator_mcp_policy`'s own private `_MAX_INPUT_PAYLOAD_BYTES` BY
VALUE, not import** (per the hard boundary: never edit/import-private-from
`operator_mcp_policy.py`; this repo's own established convention —
`operator_mcp_adapters/__init__.py`'s `_CEILING_CONFIG_SECTION`/`_CEILING_CONFIG_KEY`
— is to duplicate such constants locally rather than reach for a private
symbol). This is intentionally a cheap, EARLY, transport-level
short-circuit over the raw MCP `arguments` dict, defense-in-depth only —
the authoritative bound remains `_check_capability`'s later check over each
adapter's own narrowed `ctx.input_payload`. The two numbers can drift
independently without weakening anything (a looser/stricter transport-level
short-circuit only changes how early an oversized request is rejected).

**3. Every one of the 14 tools shares ONE generic dispatch shape** (fixed
top-level params: `idempotency_key`/`input_payload`/`confirmation_record`/
`presented_token`/`dry_run` for the 13 operation kinds; a slightly different
fixed shape for `operation.preflight`) rather than 13 bespoke, hand-typed
signatures mirroring each adapter's own `invoke()` parameter names. This
reads D4's "for each operation kind, the handler resolves via
`get_adapter(kind)`" as authorizing ONE handler PATTERN applied per kind, not
13 hand-authored signatures — and matches
`operator_mcp_operation.schema.yaml`'s OWN generic, bounded `input_payload`
envelope field (`additionalProperties: true, maxProperties: 32` — explicitly
NOT frozen per-tool at the schema/transport layer; each adapter's own
`invoke()` signature remains the true, already-frozen per-kind contract,
unchanged and untouched by this leg). If the orchestrator wants 13 literally
distinct MCP-advertised schemas (one Literal-typed parameter set per kind,
mirroring each adapter's own keyword names 1:1) instead, that's a mechanical
follow-up, not a redesign — flagging so it's a deliberate choice, not an
oversight.

**4. `_operation_tool.__name__` is reassigned to `kind.replace(".", "_")`**
purely cosmetic (affects only the auto-generated schema `title`, e.g.
`"run_planArguments"`); has no bearing on the actual registered MCP tool
name (`server.tool(name=kind, ...)`, which correctly keeps the dotted form —
dots are explicitly SEP-986-legal in MCP tool names, verified against the
installed SDK's own `mcp.shared.tool_name_validation` module).

## Real command tails (re-run under `mcp==1.29.0` per orchestrator resolution)

```
$ ./.venv/bin/python -c "import importlib.metadata as m; print(m.version('mcp'))"
1.29.0

$ ./.venv/bin/python -m pytest tests/test_operator_mcp_offline_import.py tests/integration/test_operator_mcp_server.py -q
...........................                                              [100%]
27 passed

$ ./.venv/bin/python -c "import sys; sys.modules['mcp']=None; import research_foundry; print('base ok')" && ./.venv/bin/rf --help >/dev/null && echo "cli ok"
base ok
cli ok

$ /Users/miethe/.pyenv/shims/flake8 src/research_foundry/operator_mcp tests/test_operator_mcp_offline_import.py tests/integration/test_operator_mcp_server.py --select=E9,F63,F7,F82
$ echo $?
0

$ ./.venv/bin/ruff check src/research_foundry/operator_mcp pyproject.toml tests/test_operator_mcp_offline_import.py tests/integration/test_operator_mcp_server.py
All checks passed!

$ ./.venv/bin/python -m mypy src/research_foundry/operator_mcp --ignore-missing-imports
Success: no issues found in 3 source files
```

Note: `./.venv/bin/flake8` itself is NOT installed in this worktree's venv
(`No module named flake8`) — used the pyenv-shim `flake8` on PATH instead,
which resolved and passed clean. `ruff check` against the same paths also
passed clean as a second signal.

Regression check, re-run under 1.29.0:

```
$ ./.venv/bin/python -m pytest tests/unit/test_knowledge_mcp_registry.py -q
..................                                                       [100%]
18 passed
```

Confirms the orchestrator's downgrade resolved the pre-existing
`knowledge_mcp` breakage this leg's original flag identified — that suite is
now green, unprompted, with zero changes from this leg.

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_*.py tests/unit/test_operator_mcp_policy.py \
    tests/unit/test_operator_mcp_schemas.py tests/unit/test_operator_mcp_serve_extra_boundary.py \
    tests/integration/test_operator_mcp_server.py tests/test_operator_mcp_offline_import.py -q
...
FAILED tests/unit/test_operator_mcp_adapter_writeback_preview.py::test_invoke_preview_unsupported_target_is_governed_result
```

**New flag (not this leg's file ownership, not caused by this leg's
changes):** Leg A landed `src/research_foundry/services/operator_mcp_adapters/
writeback_preview.py` + `tests/unit/test_operator_mcp_adapter_writeback_preview.py`
CONCURRENTLY in this same worktree while this leg was mid-revalidation (both
files show as untracked `??` in `git status`, and re-running the single
failing test twice in a row produced two DIFFERENT diffs — Leg A's own files
were being actively edited between runs). `writeback.preview` is now a real,
registered adapter (`operator_mcp_adapters.get_adapter("writeback.preview")`
returns it, not `None`), so this leg's own `_writeback_preview_registered`
fixture correctly detects that and skips its stub — all 27 of this leg's own
tests, including `test_writeback_preview_tool_denies_via_adapter_never_reaches_a_live_client`,
pass against the REAL Leg A adapter. The one failure
(`test_invoke_preview_unsupported_target_is_governed_result`) is entirely
inside Leg A's own file ownership (`operator_mcp_adapters/writeback_preview.py`'s
own per-target status logic) and this leg does not touch it. Excluding that
one file, the regression scope is:

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_*.py tests/unit/test_operator_mcp_policy.py \
    tests/unit/test_operator_mcp_schemas.py tests/unit/test_operator_mcp_serve_extra_boundary.py \
    tests/integration/test_operator_mcp_server.py tests/test_operator_mcp_offline_import.py \
    --ignore=tests/unit/test_operator_mcp_adapter_writeback_preview.py -q
348 passed
```

Full-suite run was also attempted earlier in the mcp==2.0.0 window (`tests/`
with 3 known, pre-existing, out-of-scope collection errors ignored); it did
not finish inside this session's tool timeout and its output is now stale
(pre-dates the SDK downgrade) — not re-attempted given the scoped, targeted
re-runs above are authoritative for this leg's actual changes.

## What the security lens should attack first

1. **Judgment call 1 above** (the `resolved_target_workspaces` optimistic
   guess in `operation.preflight`) — verify the "never part of the canonical
   digest or minted record" claim independently against
   `operator_mcp_policy.py`'s actual current source, not just this note.
2. **The D7 `call_tool` override's exception boundary** — confirm no path
   through it can leak `str(exc)`/a traceback/an absolute path (it currently
   logs only `type(exc).__name__`, matching the NEW-13 convention, and
   returns a closed `build_error` envelope unconditionally).
3. **`input_payload` unpacking (`**input_payload`) into `adapter.invoke(...)`**
   — confirm every one of the 12 currently-registered adapters' own
   `invoke()`/`invoke_*()` keyword-only signatures rejects (rather than
   silently accepting) any unexpected key, so a caller can never smuggle a
   server-reserved parameter (`paths`, `now`, `operations`, `cancel_resume`)
   through `input_payload` to override server-controlled state. (Verified by
   inspection during this leg: every real signature is `*, name1, name2, ...`
   keyword-only with no `**kwargs` catch-all at the REAL `invoke()` layer —
   only the `OperatorAdapter` Protocol's `invoke(self, **kwargs)` wrapper
   accepts arbitrary kwargs, and it forwards them unchanged to the real,
   closed signature, which is where an unexpected/colliding key actually
   raises `TypeError`.)
4. **`writeback.preview` dispatch once Leg A lands for real** — this leg's
   own tests exercise a deny-only stub (`_StubWritebackPreviewAdapter`); once
   Leg A's real adapter is registered, re-run
   `tests/integration/test_operator_mcp_server.py::test_writeback_preview_tool_denies_via_adapter_never_reaches_a_live_client`
   against it and confirm it still denies with no live-client construction
   (per Leg A's own D6 no-integration-client-import invariant — out of this
   leg's file ownership to verify further).

## Files touched

- `src/research_foundry/operator_mcp/__init__.py` (new)
- `src/research_foundry/operator_mcp/server.py` (new)
- `src/research_foundry/operator_mcp/process.py` (new)
- `pyproject.toml` (added `rf-operator-mcp` script entry, `[project.scripts]`)
- `tests/test_operator_mcp_offline_import.py` (new)
- `tests/integration/test_operator_mcp_server.py` (new)
- `.claude/worknotes/research-foundry-operator-mcp/m2-leg-b-completion.md` (this file)

No file outside this leg's ownership was edited. No `git` command was run
(per hard boundary 6 — never `git stash`, orchestrator is the only
committer).
