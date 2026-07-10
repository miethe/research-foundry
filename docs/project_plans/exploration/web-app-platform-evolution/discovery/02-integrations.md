---
doc_type: report
report_category: investigation
title: Research Foundry — Agentic & External-System Integration Inventory
status: draft
created: 2026-07-10
feature_slug: web-app-platform-evolution
---

# Integration Inventory

Scope: every agentic / external-system integration point in Research Foundry
(`src/research_foundry/`), with wiring status verified against code, not
assumed from prior notes. Statuses:

- **live** — exercised end-to-end with no external dependency (pure file I/O,
  deterministic), or confirmed reachable/running via config/deploy evidence.
- **untested-live** — client code + wiring exists and targets a real remote
  API, but no confirmed successful live call in this repo (candidate files
  never generated on disk).
- **offline-unvalidated** — implemented against an inferred external
  interface (CLI or REST) with graceful degradation; never run against the
  real external system from this repo.
- **spec-only** — stub/contract present, no working call path yet.

## 1. Integration inventory table

| Integration | Direction | Transport | Status | Key file path(s) |
|---|---|---|---|---|
| MeatyWiki writeback | write | file (Markdown mirror) | live | `src/research_foundry/services/writeback.py:284` (`_render_meatywiki`), `:376` (`_render_decision_record`) |
| SkillMeat/SkillBOM writeback | write | file (Markdown mirror) | live | `src/research_foundry/services/writeback.py:478` (`_render_skillbom`), `:1223` (`skillbom_propose`) |
| CCDash execution-event writeback | write | file (YAML mirror, `ccdash/events/`) | live | `src/research_foundry/services/telemetry.py:132` (`emit_ccdash_event`), example: `ccdash/events/exec_20260710_intent_research_20260613_what_is_the.yaml` |
| ARC / council-review | write + read | HTTP (`ArcClient`) | untested-live | `src/research_foundry/integrations/arc.py`, `src/research_foundry/adapters/arc_council.py`, `src/research_foundry/services/writeback.py:704` (`_render_arc_council`) |
| IntentTree (task dispatch, bidirectional) | bidir | HTTP (`IntentTreeClient`) | untested-live | `src/research_foundry/integrations/intenttree.py`, `src/research_foundry/services/intake.py:81`, `src/research_foundry/services/writeback.py:625` (`_render_intenttree_update`), `src/research_foundry/services/telemetry.py:448` (status push) |
| NotebookLM (correlation/adapter/sync/intake) | bidir | CLI subprocess (`notebooklm` binary) | offline-unvalidated | `src/research_foundry/integrations/notebooklm.py`, `src/research_foundry/adapters/notebooklm.py`, `src/research_foundry/services/notebook_correlation.py`, `src/research_foundry/services/writeback.py:807` (`_render_notebooklm_update`) |
| RF Search Router MCP server (`rf-mcp`) | tool exposure | MCP (stdio, `FastMCP`) | offline-unvalidated | `src/research_foundry/services/search_router/mcp_server.py`, entry point `pyproject.toml:58` |
| RF HTTP API (`rf serve`) | read + write | HTTP (FastAPI/uvicorn) | live (deployed) | `src/research_foundry/api/app.py`, `src/research_foundry/cli_commands.py:2397` (`serve` command) |
| Agent Jobs API (subprocess-spawning agent runs) | write | HTTP (subprocess spawn) | spec-only (flag-gated off by default) | `src/research_foundry/api/routers/agent_jobs.py`, `src/research_foundry/services/agent_job_service.py` |
| Claude Agent SDK adapter | invoke | in-process Python SDK | live (used by Path B swarm) | `src/research_foundry/adapters/claude_agent_sdk.py` |
| OpenAI Agents adapter | invoke | in-process Python SDK | offline-unvalidated | `src/research_foundry/adapters/openai_agents.py` |
| GPT Researcher adapter | invoke | in-process Python package | offline-unvalidated | `src/research_foundry/adapters/gpt_researcher.py` |
| PaperQA2 adapter | invoke | in-process Python package | offline-unvalidated | `src/research_foundry/adapters/paperqa2.py` |
| OpenCode adapter | invoke | CLI subprocess | offline-unvalidated | `src/research_foundry/adapters/opencode.py` |
| LiteLLM router adapter | invoke | in-process (multi-provider LLM routing) | offline-unvalidated | `src/research_foundry/adapters/litellm_router.py` |
| Search Router providers (Brave/Exa/GitHub) | read | HTTP | live (per project memory: offline-validated only, live-provider pending) | `src/research_foundry/services/search_router/` |
| Clerk auth provider | read (identity) | HTTP (JWKS) | spec-only (opt-in, lazy-imported) | `src/research_foundry/api/auth/adapters/clerk.py` (referenced from `api/app.py:214`) |
| local_static auth provider | read (identity) | in-process token check | live (default) | `src/research_foundry/api/auth/adapters/local_static.py` |

## 2. Per-integration notes

### Writebacks (deterministic, file-based — default targets)

**MeatyWiki.** `writeback()` always renders `writebacks/meatywiki_writeback.md`
(a source-note candidate) plus an additive `decision_record` when inference
claims exist. It is marked `proposed` and NOT mirrored into the wiki when the
run requires review or is work/client-sensitive (`writeback.py:972`). No live
HTTP call to a MeatyWiki service exists in this path — the "integration" is a
file drop at `paths.meatywiki/sources/<slug>.md`, consumed by the separate
MeatyWiki compile loop out-of-band. Proven: exercised on every `rf writeback`
call.

**SkillMeat/SkillBOM.** `_render_skillbom` writes
`writebacks/skillbom_candidate.md` plus a mirror under
`paths.skillmeat/skillboms/<id>.md`, referencing the CCDash event id for
performance evidence. `skillbom_propose`/`promote` (writeback.py:1223+) manage
the candidate lifecycle. Same file-mirror pattern as MeatyWiki — no HTTP.

**CCDash.** `emit_ccdash_event` (telemetry.py:132) always writes
`runs/<run>/writebacks/ccdash_event.yaml` and mirrors it to
`ccdash/events/<event_id>.yaml`, validated against the `ccdash_event` schema.
Proven live and actively exercised — six mirror files dated 2026-07-05
through 2026-07-10 exist in `ccdash/events/` in this repo's current working
tree, generated by real `rf writeback` runs against
`rf_run_20260613_what_is_the_current_release_state` and a governance-run
intent.

### Bidirectional / opt-in integrations (`--targets intenttree,arc,notebooklm`)

**ARC (council-review).** `ArcClient` (`integrations/arc.py`) is a thin
stdlib-`urllib` HTTP client with health check `GET /api/health` and calls
`POST /api/runs` (`scaffold_review`) + `GET /api/runs/{id}` (`get_run`).
`_render_arc_council` (writeback.py:704) always writes
`writebacks/arc_review_request.yaml` with `status: proposed`; when ARC is
reachable, not review-gated, and profile isn't `offline_only`, it POSTs the
evidence bundle for review and maps ARC's verdict (`approve`/`concern`/
`block`) to an `rf_exit_code`. **Verified via disk search: no run directory in
this repo (41 runs) has ever produced an `arc_review_request.yaml` with
`status != proposed`** — the live push path has never fired. Method stubs
were explicitly called out in the module docstring as "Phase 0 foundation
only" pending "Phase 3"; unclear from code alone whether Phase 3 has since
landed on the ARC side.

**IntentTree.** `IntentTreeClient` (`integrations/intenttree.py`) supports
inbound (`rf intake intenttree <node_id>`, `services/intake.py:81`) and
outbound paths: `_render_intenttree_update` (writeback.py:625) always writes
`writebacks/intenttree_update.yaml`, and pushes a status patch +
`add_node_artifact` calls when the client's `GET /api/meta/version` health
check succeeds. `telemetry.py:448` provides an additional standalone
progress-stage pusher (`patch_node`) called independently of the writeback
step. Auth is an optional bearer token (`INTENTTREE_API_TOKEN`). **Same disk
check as ARC: no `intenttree_update.yaml` with a `pushed` status exists
anywhere in `runs/`** — inbound intake path is unverified in this repo too
(no evidence of `rf intake intenttree` having been run against a live node).
This client targets an inferred API shape (`/api/nodes/{id}`,
`/api/nodes/{id}/artifacts`) that does not match the schema of the IntentTree
MCP tools available in this session (`get_node`, `update_node`,
`link_external`, etc.) — the two IntentTree surfaces (this RF-side HTTP
client vs. the MCP server) are not obviously the same contract; reconciling
them is unverified.

**NotebookLM.** Two layers exist: `integrations/notebooklm.py`
(`NotebookLMClient`, a thin `available()`/`create_notebook()`/`add_source()`/
`get_notebook()` wrapper around the `notebooklm` CLI, subprocess + JSON) and
`adapters/notebooklm.py` (`NotebookLMAdapter`, spec §13.x — grounded-research
sourcing that degrades to deterministic stub candidates when the CLI is
unavailable, never spawning a subprocess in that fallback). CLI resolution is
`shutil.which("notebooklm")` or `NOTEBOOKLM_CLI_PATH`. `notebook_correlation.py`
maintains a project/run → notebook-id registry at
`registries/notebooklm/notebooks.yaml` in three correlation modes
(`project`/`run`/`explicit`). CLI entry points: `rf notebooklm resolve|status|
sync` and `rf intake notebooklm <notebook_id>` (`cli_commands.py:1027-1167,
989`). Notably, `rf notebooklm sync` does **not** execute a sync — it only
*prints* the `notebooklm add-source` command for the operator to run
manually (`cli_commands.py:1121-1166`). `_render_notebooklm_update`
(writeback.py:807) follows the same always-write-candidate pattern as ARC/
IntentTree. Per project memory, this integration was implemented offline and
is unvalidated against a live NotebookLM session; the disk search corroborates
this — no `notebooklm_update.yaml` exists in any run.

### MCP surface

**`rf-mcp` (Search Router only).** The console script
`rf-mcp = research_foundry.services.search_router.mcp_server:main`
(`pyproject.toml:58`) wraps only the Search Router's `run_search`/
`extract_urls` functions as five MCP tools (`search_run`, `extract_url`,
`search_source_discovery`, `search_semantic_discovery`,
`search_github_discovery`) via `FastMCP`, transport stdio. The module is
designed to import cleanly without the `mcp` SDK installed; only
`build_server()`/`main()` require `uv sync --extra mcp`. **This is the only
MCP tool surface RF exposes** — there is no MCP server exposing runs, claims,
reports, or writeback operations; agent harnesses (Claude Code, OpenCode,
Hermes) that want that surface must use the HTTP API instead.

### RF HTTP API (`rf serve`)

See §3 below for the full endpoint enumeration. Confirmed deployed and live
on the agentic node per user memory (`10.42.10.76:7432`, token-auth). The API
surface is **broader than read-only**: `POST /api/runs` scaffolds+plans a run
(does not spawn the discovery swarm — status is always `"planned"`), and
`POST /api/agent-jobs` can spawn an actual agent subprocess when
`foundry.agents.enabled=true` (default `false`, opt-in, gated behind
`guard_check()`). Both write endpoints exist in code; whether either has
ever been called against the live nuc deployment is not verifiable from this
repo's files alone.

### In-process/CLI-subprocess adapters (non-network "integrations")

`adapters/` holds 8 self-registering modules (`load_all()` in
`adapters/__init__.py:19`) that each degrade to `AdapterResult(degraded=True)`
on any import/subprocess error, never raising into the pipeline:
`arc_council` (thin wrapper delegating to `integrations/arc.py`),
`claude_agent_sdk` (in-process, used by the live Path B discovery swarm per
project memory), `gpt_researcher`, `notebooklm`, `openai_agents`, `paperqa2`,
`opencode` (CLI subprocess), `litellm_router`. Only `claude_agent_sdk` has
confirmed live usage (the documented Path B swarm workflow); the rest are
implemented-but-unexercised in this repo's run history.

## 3. API surface (`rf serve`)

Auth model, from `api/app.py` and `cli_commands.py:2397`:

- Providers (`foundry.yaml: auth.provider`): `none` (no middleware, no
  identity — default for pure-loopback), `local_static` (multi-token →
  `{user_id, workspace_id, roles}` mapping, constant-time compare; **this is
  the live-deployment default** per project memory — `RF_TOKEN_AGENT` bearer
  token), `clerk` (lazy-imported, requires `PyJWT`+`cryptography`, JWKS
  verify), and a documented `oidc` BYO seam.
- Fail-closed gate: binding to a non-loopback host (`--bind-host 0.0.0.0`)
  requires `auth_mode=token` or `auth.provider=local_static` AND a non-empty
  token env var; `cli_commands.py:_validate_nonloopback_bind` (around line
  119) refuses to open the port otherwise. This check and `create_app()` read
  the same post-CLI-override config object (a fixed P1 bypass is documented
  inline).
- RBAC: `resolve_rbac_enforced()` and (separately, WKSP-304)
  `resolve_workspace_isolation_enforced()` are computed at `create_app()`
  time and stored on `app.state`; workspace isolation enforcement is
  "advisory by default" and was landed 2026-07-09 per project memory (flag-
  gated, with a known incomplete-scoping-enumeration gap: DI-1 full-surface
  audit still pending before multi-tenant deploy).

Endpoint groups (all prefixed `/api` except `/health` and
`/data/governance.json`):

| Router | Endpoints |
|---|---|
| Meta | `GET /health`, `GET /data/governance.json` |
| runs | `GET /runs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/claims`, `GET /runs/{run_id}/sources/{sc_id}`, `GET /reports/{run_id}/anchors`, `POST /runs` (scaffold+plan only) |
| catalog | `GET /catalog/stats`, `GET /catalog/search`, `GET /catalog/items/{id}`, `POST /catalog/import/run/{run_id}`, `POST /catalog/import` |
| reports (Report Builder) | `POST/GET/DELETE /reports[/{id}]`, `GET/POST /reports/{id}/versions[/{version_id}]`, `POST/PATCH/DELETE /reports/{id}/blocks[/{block_id}]`, `PATCH /reports/{id}/blocks/reorder`, `POST/DELETE /reports/{id}/claim-links`, `POST/DELETE /reports/{id}/source-links`, `POST /reports/{id}/verify`, `POST /reports/{id}/publish-preview`, `GET /reports/{id}/export`, plus 2 more POST/GET routes (lines 1000, 1075) |
| agent-jobs (flag-gated, `agents.enabled`, default off) | `POST /agent-jobs`, `GET /agent-jobs/{id}`, `GET /agent-jobs/{id}/artifacts`, `GET /agent-jobs/{id}/events` (SSE), `POST /agent-jobs/{id}/cancel`, `POST /agent-jobs/{id}/accept` (sole write path to catalog/report) |
| audit | `GET /audit`, `GET /audit/health`, `GET /audit/{audit_event_id}` |
| auth | `GET /auth/identity` |
| admin | 6 endpoints (member/rate-limit/RBAC-toggle management), all gated `require_role("owner","admin")` |

Access boundary (from user's global CLAUDE.md, corroborated by the
`local_static` default + fail-closed gate above): local agents/orchestrators
call the deployed API with `Authorization: Bearer $RF_TOKEN_AGENT`; external
delegates (ICA, opencode) are not given the token; runs are launched via the
`rf` CLI in practice even though `POST /api/runs` exists in code (it only
scaffolds+plans, never drives the actual Claude-agent discovery swarm — see
Feature Contract `docs/project_plans/feature_contracts/features/
http-run-launch-endpoint.md`, `api/routers/runs.py:268-278`).

## 4. Gaps / risks

- **Memory anchor was incomplete, not just stale.** The task's "known status
  anchor" describing the RF API as "read-only for runs" undersells the
  surface: `POST /api/runs` and the entire `agent-jobs` router (subprocess
  spawning, gated by `agents.enabled` + `guard_check()`) are real write
  paths. `agents.enabled` defaults to `false` and is documented as
  loopback/single-operator-only pre-P5, so this is contained but should be
  re-verified against the live nuc `foundry.yaml` before assuming it's
  reachable there.
- **ARC and IntentTree writeback pushes are unexercised, not merely
  "untested."** A search across all 41 run directories in this repo found
  zero instances of `arc_review_request.yaml` or `intenttree_update.yaml`
  reaching `status: submitted`/`pushed`. The `available()` health checks,
  the `scaffold_review`/`patch_node` payload shapes, and the verdict-mapping
  logic have never been exercised against a live remote — first contact
  could surface auth mismatches, schema drift, or endpoint-path errors that
  unit tests (which mock the client) would not catch.
- **IntentTree contract mismatch risk.** RF's `IntentTreeClient` targets
  `/api/nodes/{id}` + `/api/nodes/{id}/artifacts` + `/api/meta/version`. The
  IntentTree MCP tool surface available in this session exposes a
  differently-shaped API (`get_node`, `update_node`, `link_external`,
  `claim_node`, workspace-scoped `ready_nodes`, etc.). Whether RF's inferred
  REST shape actually matches IntentTree's live API is unverified — this is
  a plausible first-contact break point flagged by prior project memory and
  confirmed still true by this pass.
- **NotebookLM `sync` command is non-executing by design** (prints a command
  rather than running it) — the "sync" leg of the bidirectional loop has a
  manual step that is easy to assume is automatic when it isn't.
- **`rf-mcp` is Search-Router-only.** Any assumption that RF exposes runs/
  claims/reports as MCP tools is false; that surface is HTTP-only. A
  general-purpose RF MCP server (if desired for the web-app-platform-
  evolution work) does not exist yet.
- **Search Router live providers unvalidated.** Per project memory, Brave/
  Exa/GitHub search is offline-validated only; a live-provider run + source-
  type vocabulary unification is still pending.
- **Adapter fan-out is mostly dormant.** Of the 8 self-registering adapters,
  only `claude_agent_sdk` has confirmed live usage (the Path B swarm);
  `gpt_researcher`, `openai_agents`, `paperqa2`, `opencode`, `litellm_router`,
  and the `notebooklm` adapter's live (non-stub) code path are implemented
  but unexercised by any run artifact found in this repo.
- **Workspace isolation enforcement is advisory-by-default with a known
  incomplete-audit gap** (WKSP-304, per project memory) — relevant if the
  web-app-platform-evolution work extends the API surface before that
  full-surface audit lands.
