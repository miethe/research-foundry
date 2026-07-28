---
name: project-knowledge-mcp-p4-stdio-process
description: RF Knowledge MCP Phase P4 Part A (independent stdio process + core tools) shipped; superseded by [[project_knowledge_mcp_p4b_rf_tools_inventory]] for Part B — still-relevant gotchas kept below
metadata:
  type: project
---

KMCP-4.1/4.2 ("Phase P4 Part A") shipped: `src/research_foundry/knowledge_mcp/{__init__,process,registry,settings}.py`,
`rf-knowledge-mcp` console script (reuses the existing `mcp` extra, no new extra), 27 new tests
(`tests/test_knowledge_mcp_offline_import.py`, `tests/unit/test_knowledge_mcp_{settings,registry}.py`). Registered only
`search`/`fetch` at the time (frozen core, exact `{query}`/`{id}` input) — the six `rf_*` tools were deliberately NOT
registered yet. **Part B (KMCP-4.3/4.4) is now also shipped** — see [[project_knowledge_mcp_p4b_rf_tools_inventory]].
Builds on [[project_knowledge_mcp_p3b_report_run_composer]]'s committed `knowledge_access.py` service without touching
its business logic.

**Why:** decisions-block §9.1 requires an independent process/registry/settings boundary — its own entry point, never
importing from `search_router.*`/Operator, with a lazy `mcp` SDK import and a stdio-only transport guard (invariant 8).

**How to apply / non-obvious findings for KMCP-4.3, P5, P6:**

1. **`knowledge_access.py` transitively requires the `serve` extra.** It imports `AuthIdentity` from
   `..api.auth.provider` at MODULE level (not lazy/`TYPE_CHECKING`, unlike `search_router.mcp_launcher.py`'s own
   identical import of the SAME class). `research_foundry/api/__init__.py` unconditionally imports `fastapi` at
   package-init, so `rf-knowledge-mcp` — despite being "independent" and only declaring the `mcp` extra — actually
   crashes with `ModuleNotFoundError: fastapi` in an env that has `mcp` but not `serve` installed. Confirmed via
   `echo "" | rf-knowledge-mcp` after a targeted `uv sync --extra mcp --extra dev` (no `serve`). NOT fixed here per
   explicit instruction not to touch `knowledge_access.py`'s business logic — a one-line `TYPE_CHECKING`-guarded
   import fix (zero runtime behavior change, since the module has `from __future__ import annotations` and never
   isinstance-checks `AuthIdentity`) is the same precedented pattern `mcp_launcher.py` already uses for this exact
   class. Whoever owns KMCP-4.4/P6's inventory gate should decide whether to land that fix or accept the `serve`
   dependency as documented scope creep.

2. **`uv sync --extra X --extra Y` PRUNES the venv to exactly those extras — do not run it narrowly mid-session.**
   This repo's shared dev venv needs `mcp + dev + serve + pdf + search` simultaneously installed for the full
   suite's own EXPECTED baseline (serve→fastapi for `test_serve_api.py`/admin/RBAC tests; pdf→pypdf for
   `test_pdf_extractor.py` etc.). It must NOT include the `llm` extra
   (`claude-agent-sdk`/`litellm`) — `tests/test_adapters.py::test_each_adapter_unavailable_and_degrades` and
   `tests/integration/test_agent_job_e2e_claude.py::test_adapter_degraded_without_client` specifically assert
   graceful degradation when those packages are ABSENT, and fail if they're actually importable. Running
   `uv sync --extra mcp --extra dev` (forgetting `serve`/`pdf`) silently uninstalls `fastapi`/`pypdf` from a venv
   that had them, breaking unrelated previously-green tests until re-synced with the full combo. `uv.lock` itself
   was already stale re: the `pdf` extra (missing from `provides-extras`) before this task — `uv sync` corrected it
   as a side effect; that lockfile diff is expected and should be kept.

3. **`build_server()` bootstraps ALL FIVE `KindProjector`s globally** via `knowledge_access.register_projector` —
   before this task, that function was only ever called by test fixtures, never by any real process. Without this
   bootstrap, `search`/`fetch` would only ever exercise the P2 skeleton's "no projector registered" exit condition
   (permanently empty/denied). The registry is a process-global dict in `knowledge_access.py`, so repeated
   `build_server(settings)` calls against a different `paths` (e.g. across tests) simply overwrite it — correct and
   cheap, but means two servers built against different workspaces can't coexist in the same process.

4. **Dual encoding (KMCP-1.3) required bypassing FastMCP's own auto-serialization.** FastMCP's default
   `structured_output` conversion (`pydantic_core.to_json(result, indent=2)`) produces indented, insertion-ordered
   JSON for the text content block — NOT this repo's canonical-JSON convention
   (`json.dumps(..., separators=(",",":"), sort_keys=True)`, same as `assertion_identity.canonical_source_assertion_json`).
   Fix: register tools with `structured_output=False` and return an explicitly-constructed `mcp.types.CallToolResult`
   directly — `FuncMetadata.convert_result` passes an already-`CallToolResult` return value straight through
   unmodified when `output_schema is None`.

See [[project_knowledge_mcp_p3b_report_run_composer]], [[project_knowledge_mcp_p3_source_assertion_projections]] for
the wrapped service's own P3 history.
