---
schema_version: 2
doc_type: report
report_category: investigation
title: "Research Foundry — Current State & Direction (Platform Evolution)"
status: draft
created: 2026-07-10
updated: 2026-07-10
feature_slug: web-app-platform-evolution
related_documents:
  - docs/project_plans/exploration/web-app-platform-evolution/discovery/01-cli-core.md
  - docs/project_plans/exploration/web-app-platform-evolution/discovery/02-integrations.md
  - docs/project_plans/exploration/web-app-platform-evolution/discovery/03-web-app.md
  - docs/project_plans/exploration/web-app-platform-evolution/discovery/04-public-service.md
  - docs/project_plans/exploration/web-app-platform-evolution/discovery/05-docs-intent.md
---

# Research Foundry — Current State & Direction (Platform Evolution)

## 1. Executive summary

Research Foundry started as a 7-day MVP CLI (`README.md:35-40`) — capture → triage → plan → ingest →
extract → claim-map → synthesize → verify → bundle → writeback, all file-backed, all offline-capable.
That core is still intact and still the differentiated value: the deterministic report verifier
(`src/research_foundry/services/verification.py`, its own module docstring calling it "the
differentiated value of Research Foundry") and the claim ledger it checks against are unchanged in
spirit and hardened through several rounds of adversarial review. Around that core, four distinct
surfaces have grown up in the last several weeks: (1) the **CLI/core engine** itself, now ~30
commands deep with a Report Builder, evidence catalog, audit log, and workspace-migration tooling
bolted on; (2) an **agentic/integration layer** — eight self-registering research adapters, a
Search Router, an MCP server, and bidirectional hooks into ARC, IntentTree, and NotebookLM; (3) an
**HTTP API + web app** (`rf serve` + the `frontend/runs-viewer/` Vite+React SPA) that turned RF from
a CLI-only tool into something with a real UI and a real (if narrow) API surface; and (4) an early
**public/multi-user service scaffold** — auth providers, RBAC, workspace row-level isolation, rate
limiting, and audit logging, shipped but still advisory-by-default.

The headline maturity split is stark and worth stating plainly for anyone orienting to this codebase:
the **CLI core and its deterministic pipeline (extract → claim-map → verify → bundle → guard) are
solid, offline, and battle-tested** — no network dependency, no LLM dependency (synthesis is
deliberately a deterministic no-op even with `--llm`, `src/research_foundry/services/synthesis.py:210-220`).
Everything layered on top of that core to make RF a *platform* — live external integrations (ARC,
IntentTree, NotebookLM), the Search Router's keyed providers, the embedded agent-job subprocess
model, and the entire public-multi-user auth/RBAC/workspace-isolation stack — is either
**offline-unvalidated**, **shipped-but-flag-gated-off**, or **shipped-advisory-by-default**. None of
these platform-expanding pieces has failed; they simply have not yet had first contact with a live
remote system or a real second tenant. The INTENT doc that should explain all of this to a new agent
or human is, itself, an unfilled template (`intents/intent.md`) — the single biggest documentation
gap in the repo, and the reason this report and the coming rewrite exist.

## 2. Capability map

Maturity legend: **shipped-enforced** (live, hard-gated, default-on) · **shipped-advisory** (code
path exists and runs, but the safety property it provides defaults to warn-only or off) ·
**experimental** (implemented, exercised in this repo, not hardened against adversarial load) ·
**offline-unvalidated** (implemented against an inferred external contract, never run against the
real system) · **gap** (does not exist yet).

### 2.1 CLI / core engine

| Capability | Maturity | Notes |
|---|---|---|
| Capture→triage→plan→ingest pipeline | shipped-enforced | Offline, deterministic (`docs/.../01-cli-core.md` §2) |
| Claim extraction / claim-map / ledger | shipped-enforced | Regex-heuristic classifiers, hardened over review rounds (`services/verification.py:219-243`) |
| Deterministic verifier (`rf verify`) | shipped-enforced | The core differentiator; stable exit-code precedence (`services/verification.py:737-756`) |
| LLM-assisted synthesis (`rf synthesize --llm`) | gap (by design) | Deterministic body always wins; flag only appends a note (`services/synthesis.py:210-220`) |
| Governance gate (`rf guard check`) | shipped-enforced | ~9 deterministic policy rules, network-free, secret scanning (`services/governance.py`) |
| Search Router (`rf search`/`rf fetch`) | offline-unvalidated | Keyless providers degrade gracefully; keyed providers (brave/exa/firecrawl) never exercised live |
| Report Builder (`rf report draft *`) | shipped-enforced | File-canonical drafts, fail-closed D13 verify/publish-preview checks |
| Evidence catalog (`rf catalog *`) | shipped-enforced | SQLite+FTS5 derived read model, sensitivity-gated fail-closed |
| Workspace migration (`rf workspace migrate*`) | shipped-enforced (dry-run guaranteed zero-write) | Backfill/rollback runbook exists |
| Agent jobs (`rf agent-job *`) | shipped, flag-gated off | In-process-only providers enforced; subprocess spawn opt-in |
| `rf serve` loopback API | shipped-enforced | Fails closed on non-loopback bind without token auth |

### 2.2 Agentic & external-system integrations

| Integration | Maturity | Notes |
|---|---|---|
| MeatyWiki / SkillMeat / CCDash writebacks | shipped-enforced (live) | File-mirror pattern, no HTTP; CCDash mirror confirmed exercised (`ccdash/events/*.yaml`) |
| ARC (council-review) | offline-unvalidated | Zero `arc_review_request.yaml` has ever reached `status != proposed` across 41 run dirs |
| IntentTree (bidirectional) | offline-unvalidated | Zero `intenttree_update.yaml` has ever reached `pushed`; RF's inferred REST shape does not obviously match the live IntentTree MCP contract |
| NotebookLM (correlation/sync/intake) | offline-unvalidated | `rf notebooklm sync` prints a command rather than executing it — the "sync" leg is manual by design |
| `rf-mcp` (Search Router MCP server) | offline-unvalidated | Only MCP surface RF exposes; no MCP server for runs/claims/reports/writebacks |
| Claude Agent SDK adapter | shipped-enforced (live) | Confirmed live usage via the Path B discovery-swarm workflow |
| GPT-Researcher / PaperQA2 / OpenAI Agents / OpenCode / LiteLLM adapters | offline-unvalidated | Implemented, self-registering, degrade-safe; none exercised by any run artifact in-repo |
| Agent Jobs API (`POST /api/agent-jobs`) | shipped, flag-gated off | Real subprocess-spawning write path; `agents.enabled=false` default |

### 2.3 HTTP API + MCP surface

| Capability | Maturity | Notes |
|---|---|---|
| `rf serve` core routers (runs/catalog/reports/audit/auth/admin) | shipped-enforced | Broader than "read-only" — `POST /api/runs` scaffolds+plans (never drives the swarm) |
| Report Builder API | shipped-enforced (backend) / offline-unvalidated (frontend integration) | `BuilderScreen.tsx` header itself notes the HTTP API "had not landed" at authoring time |
| Auth middleware (`AuthProviderMiddleware`) | shipped-enforced when armed | True no-op when `auth.provider=none` (default) |
| RBAC (`require_role`) | shipped-enforced when identity present; shipped-advisory-passthrough on `provider=none` | Fail-closed: `disabled` only honored on loopback bind |
| Workspace isolation (row-level) | shipped-enforced when armed; shipped-advisory by default | DI-1 full-surface audit still open (§7) |
| Rate limiting | shipped-enforced | Exempt when `auth.provider=none` |
| Audit log | shipped-enforced | Gated by RBAC on read |
| General-purpose RF MCP server (runs/claims/reports) | gap | Does not exist; HTTP-only today |

### 2.4 Web app (`frontend/runs-viewer/`)

| Capability | Maturity | Notes |
|---|---|---|
| Static-export mode (Portfolio, Run Detail, Catalog, Alerts, Policies, Settings, Help) | shipped-enforced | Deployed to `10.42.10.76:3030`; no backend required at runtime |
| Live loopback mode (`VITE_RUNS_FRONTEND_LOOPBACK_API=true`) | shipped, opt-in build flag | Only mode that unlocks `/agents` + Builder writes + admin panels |
| Report Builder UI | experimental | Validated only against a typed client + mock draft, not a live backend integration test |
| Agent-job launch/monitor UI (`/agents`) | shipped, loopback-only, no static-build nav entry | Discoverability dead-end outside a local `rf serve` |
| Auth UI (Clerk / local_static / none) | shipped-enforced (P5.8) | Renders only when `auth.provider != none` |
| Admin panels (members/roles/rate-limit/auth-status/RBAC-status) | shipped, advisory-consistent with backend | Own-workspace-only visibility, no cross-tenant admin |
| Workspace switcher | gap | No component exists; one token = one workspace today |
| Cross-run analytics/trend dashboard | gap | Catalog is the only cross-run surface |
| Full-text/semantic cross-run search | gap | Portfolio search is substring-only |
| Command palette / global nav search | gap | Per-component shortcuts only |
| Export/share affordance beyond report share tokens | gap | No PDF/markdown export or invite flow |

### 2.5 Public / multi-user service

| Capability | Maturity | Notes |
|---|---|---|
| Auth provider registry (`none`/`local_static`/`clerk`) | shipped-enforced | `oidc` recognized in vocab, not implemented (raises `ValueError`) |
| RBAC 5-role matrix | shipped-enforced when identity present | CLI/service-direct mutation bypasses RBAC entirely (classified single-operator-trust) |
| Workspace row-level isolation (WKSP-304) | shipped-advisory by default | Two post-hoc leaks already found and fixed after "100% coverage" sign-off (`eba75ab`) |
| Workspace scoping-enumeration completeness | gap (DI-1 open) | Hard pre-multi-tenant-deploy gate |
| True multi-tenant shared store | gap | Today's isolation = separate filesystem roots per deployment, not one shared store |
| Sharing (report share tokens) | shipped-enforced | Token-is-credential, re-checked for sensitivity |
| Embedded agent jobs at scale | shipped, flag-gated off | Blocked from multi-user-reachable deployment until P5.2+P5.3 both sealed |

## 3. The four surfaces

**CLI & core engine.** The `rf` Typer CLI (`src/research_foundry/cli/__init__.py:25`,
`cli_commands.py`, 2551 lines) is the product's spine: ~30 commands spanning the original
capture→verify→bundle→writeback loop plus everything added since — Report Builder
(`cli_commands.py:1846-2263`), evidence catalog (`services/catalog_service.py`, 1970 lines), audit
log (`cli_commands.py:2265+`), workspace migration (`services/workspace_migration_service.py`), and
`rf serve` itself (`cli_commands.py:2396`). The claim ledger, source cards, evidence bundle, and
telemetry trace remain the durable file-backed artifacts the rest of the platform is built on top
of; the verifier (`services/verification.py`) is explicitly documented in its own module docstring
as "the differentiated value of Research Foundry."

**Agentic integrations.** Eight self-registering adapters (`src/research_foundry/adapters/`,
`load_all()` at `adapters/__init__.py:19`) each degrade to `AdapterResult(degraded=True)` rather than
raise, but only the Claude Agent SDK adapter has confirmed live usage (the Path B discovery-swarm
workflow). Writebacks to MeatyWiki, SkillMeat, and CCDash are live, file-based, and proven —
`ccdash/events/*.yaml` mirrors dated through 2026-07-10 confirm real `rf writeback` runs. The
bidirectional ARC and IntentTree integrations (`src/research_foundry/integrations/arc.py`,
`integrations/intenttree.py`) and NotebookLM correlation (`services/notebook_correlation.py`) are
implemented against inferred external contracts but have never fired against a live remote server in
this repo — first contact remains a real risk (§7).

**HTTP/MCP API.** `rf serve` (`src/research_foundry/api/app.py`) exposes a broader-than-read-only
surface — runs, catalog, reports/Builder, audit, auth, admin routers, plus a flag-gated agent-jobs
router that can spawn a real subprocess (`api/routers/agent_jobs.py`). It is confirmed deployed live
on the agentic node at `10.42.10.76:7432` (token-auth, `local_static` default). The only MCP tool
surface RF exposes is `rf-mcp` (Search Router only, `services/search_router/mcp_server.py`) — there
is no MCP server for runs/claims/reports/writebacks; agent harnesses that want that must use the HTTP
API directly.

**Web app.** `frontend/runs-viewer/` (Vite 5 + React 18.3 + `react-router-dom` v6, **not** Next.js —
`frontend/runs-viewer/package.json:1-53`) is the only frontend in the repo. It runs in two modes from
one codebase: a static-export mode (`scripts/prebuild-static-data.mjs`, deployed to
`10.42.10.76:3030`, no backend required) and a live-loopback mode gated by the build-time flag
`VITE_RUNS_FRONTEND_LOOPBACK_API=true` (`src/api/client.ts:33-55`), which is the only mode that makes
the Report Builder's writes and the `/agents` agent-launch screen functional. Nine screens (Portfolio,
Run Detail with 7 tabs, Alerts, Policies, Catalog, Builder, Agents, Settings, Help) cover the read
surface thoroughly; authoring and agent-orchestration remain gated behind a locally-running `rf serve`
process with no path to a hosted, always-on authoring experience today.

## 4. Cross-cutting truths & corrections

The following corrections resolve discrepancies found between prior project memory / assumptions and
what the code actually shows:

- **No `RF_UI_LOOPBACK` flag and no "Tray Insert" feature exist in the codebase.** A full-tree grep
  of `frontend/runs-viewer/src` and `README.md` for `Tray`, `"Tray Insert"`, and `RF_UI_LOOPBACK`
  returned zero hits. The real build-time flag is **`VITE_RUNS_FRONTEND_LOOPBACK_API`**
  (`src/api/client.ts:56-63`; documented in `frontend/runs-viewer/README.md:19-79`). Whatever "Tray
  Insert" referred to in prior memory, it does not correspond to a named component or string in the
  current tree — flagging for reconciliation rather than assuming continuity.
- **The web app is Vite + React, not Next.js.** There is no SSR/server-component layer and no
  `apps/`/`web/` directory structure; "static export" means a standard Vite production build, not a
  Next.js static-export mode.
- **The run-export schema is at `"1.4"`, not `"1.3"`.** `src/types/rf/run-export.ts:8` is the
  authoritative header. `1.3` is still real but describes a narrower threshold — the Context tab's
  render gate (`ContextPane.tsx:13`) — not the overall schema version.
- **ARC and IntentTree writebacks have never fired live.** A disk search across all 41 run
  directories in this repo found zero instances of `arc_review_request.yaml` or
  `intenttree_update.yaml` reaching a `submitted`/`pushed` status. This is stronger than "untested" —
  it is "implemented and never exercised against the real remote."
- **NotebookLM integration is offline-implemented and unvalidated**, and its `sync` command is
  non-executing by design (`cli_commands.py:1121-1166` prints the `notebooklm add-source` command
  rather than running it) — the bidirectional loop has a manual step that is easy to mistake for
  automatic.
- **`rf synthesize --llm` is a no-op by design, not merely unwired.** Even with the adapter available,
  the deterministic ledger-faithful body always wins; the flag only appends an explanatory note
  (`services/synthesis.py:210-220`). The real LLM-assisted synthesis path in production use today is
  the external Path B swarm workflow (`.claude/workflows/rf-run-execute.js`), which edits
  `claim_ledger.yaml`/`report_draft.md` directly and re-runs `rf verify` — not a CLI flag.
- **The deterministic verifier is the differentiated value**, not synthesis quality or integration
  breadth. `services/verification.py`'s own module docstring says so, and the code shows several
  rounds of adversarial hardening (`verification.py:219-243`'s "Sources"/"References" special-casing,
  the "R2 CRITICAL fix" comment at `verification.py:975-987`).
- **Workspace isolation enforcement is advisory by default and had two post-hoc leaks** after a
  "100% coverage" sign-off (`create_draft_from_run`/`create_draft_from_collection` identity-threading
  leak and a `catalog_service.get_item` scope leak, both fixed in `eba75ab`) — the enumeration method
  itself was proven unreliable, not just incomplete by omission.
- **Today's real-world tenant boundary is separate filesystem roots per deployment**, not row-level
  scoping in one shared store — WKSP-304 makes row-level scoping *available*, but a single shared
  multi-tenant store does not exist yet.

## 5. Documentation & INTENT debt

`intents/intent.md` (leg 05 §1) is **not stale — it was never completed**. Only the frontmatter and
the one-line Mission (`intents/intent.md:15`) were ever filled in; every other section (Primary
Users, Core JTBD, Non-Goals, Product Principles, Experience Goals, Long-Term Direction, Current
Priority — `intents/intent.md:41-127`) is still verbatim template placeholder text. It currently
provides zero orientation for the web-app user, the multi-tenant operator/admin, or the API/MCP
consumer — only the CLI/research-pipeline user is implied by the mission line, and even that
undersells what RF has become.

Other documentation debt, prioritized (full detail in
`docs/project_plans/exploration/web-app-platform-evolution/discovery/05-docs-intent.md` §6):

1. **`intents/intent.md`** — write it for real (P0, cheapest highest-leverage fix).
2. **`.claude/specs/skills-index.md`** — stale/wrong: omits `research-foundry` and
   `research-foundry-swarm` entirely while listing ~15 skills that don't exist in this repo (appears
   to be an unedited copy from a sibling project).
3. **`docs/dev/architecture/artifact-type-reference.md`** — a **dangling pointer**: the top-level
   `CLAUDE.md` references it directly, but the file does not exist anywhere in the repo. Zero written
   reference exists for RF's ~17 YAML-schema-backed artifact types plus the newer DB-backed platform
   types (draft, agent_job, catalog_item, audit_log, workspace, auth identity) that have no YAML
   schema counterpart.
4. **`docs/projects/research-foundry/SERVICE_CONTRACT.md`** — stale: still calls itself the "single
   coordination contract" but documents only the original 12 MVP service modules, missing Search
   Router, `rf serve`, agent-job service, Builder service, catalog service, workspace migration
   service, and audit/auth/RBAC entirely.
5. **`README.md`** — the top-level `## Status: MVP` banner (`README.md:35-40`, *"This is the 7-day
   MVP described in the spec"*) contradicts the README's own body, which documents `rf serve`,
   loopback API, and auth-adjacent flags fairly currently.
6. **`docs/projects/research-foundry/_spec-agent-readable.md`** — appears to be a stale byte-identical
   duplicate of the MVP spec; needs reconciliation or deletion.
7. **`research-foundry`/`research-foundry-swarm` SKILL.md route tables** — otherwise the
   best-maintained docs in the repo, but missing rows for Report Builder, `rf audit`, agent-jobs, and
   catalog import/search (additive gap, not corrective).
8. Minor: Search Router docs (`docs/dev/architecture/search-router/*`) are current but isolated —
   nothing in `intent.md`/`SERVICE_CONTRACT.md` cross-links them.

## 6. Direction decision space

The following are open strategic axes this report deliberately does **not** resolve — they are the
decision surface the operator (or a follow-on planning pass) should settle before the INTENT rewrite
and UI/UX capability outline are finalized.

| Axis | Options | One-line tradeoff |
|---|---|---|
| **(a) Service model ambition** | 1. Personal-first (single-operator-trust remains the default; multi-user is opt-in LAN convenience) <br> 2. Small-team-ready (harden `local_static` + RBAC + advisory-to-enforced isolation for a handful of trusted collaborators, still one filesystem-root-per-deployment) <br> 3. Full multi-tenant SaaS (shared store, self-service signup, cross-tenant admin, DI-1 closed) | Personal-first costs the least and matches today's proven reality; small-team-ready requires closing DI-1 and flipping isolation to enforced but reuses existing primitives; full SaaS requires a genuinely new shared-store data layer, self-service auth flows, and billing/ops maturity RF does not have today. |
| **(b) Web-app center of gravity** | 1. Operator console (surface agent-jobs, admin, governance, and Builder authoring as first-class, always-on) <br> 2. Research reader (double down on Portfolio/Catalog/Report read surfaces; treat authoring as CLI-only) <br> 3. Both, cleanly separated (a read-optimized public reader + a separately-gated operator console) | Operator-console framing amplifies the current loopback-only authoring gaps (needs a hosted backend); research-reader framing plays to the app's actual current strength (mature, well-tested read surfaces) but caps ambition; "both" is the most work but avoids conflating a public-facing reader with an admin tool. |
| **(c) Run authoring in web app** | 1. Read-only (keep authoring CLI/agent-only; web app never mutates runs) <br> 2. Phased authoring (ship Builder + agent-jobs behind loopback/auth gates incrementally, as today, without a hosted backend commitment) <br> 3. Full control (make the web app a first-class run-launching/authoring surface with a hosted, always-available backend) | Read-only is safest and matches the deployed static SPA's actual current behavior; phased authoring is what's already built (Builder + `/agents`) but is discoverability-limited and loopback-gated; full control requires solving the "no hosted backend" problem, live E2E validation against Clerk/RBAC/workspace isolation, and DI-1 closure first. |

## 7. Hard gates & risks

1. **DI-1 — full workspace-data-access completeness audit.** Every read/create/list/delete service
   path across every service, re-enumerated from scratch (the prior "100% coverage" claim was
   falsified post-hoc by two leaked paths found in Phase 6 review). Explicitly named as a hard
   pre-deploy gate: `.claude/progress/wksp-304-workspace-isolation-enforcement/plan-completion.md:59-63,75`
   and the WKSP-304 plan's `OQ-4`. **Must close before any shared-store multi-tenant deploy.**
2. **Integration first-contact risk (ARC / IntentTree).** Both clients target inferred REST shapes
   never exercised against a live remote from this repo. IntentTree specifically: RF's
   `IntentTreeClient` targets `/api/nodes/{id}` + `/api/nodes/{id}/artifacts` + `/api/meta/version`,
   while the IntentTree MCP tool surface available in-session exposes a differently-shaped contract
   (`get_node`, `update_node`, `link_external`, `claim_node`, workspace-scoped `ready_nodes`). Whether
   these are the same underlying API is unverified — first contact could surface auth mismatches,
   schema drift, or endpoint-path errors that mocked unit tests would not catch.
3. **Export-threading drift chain.** A new run-export field must be hand-updated in three places —
   `export_service.py:export_run()` (backend) → `prebuild-static-data.mjs` summary object → the
   hand-written `run-export.ts` TS type — with no single schema-driven source of truth
   (`docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md:97,190`). The Evidence
   Catalog mapping logic has the same duplicated-twin risk one layer up (`catalog_service.py` vs.
   `src/lib/catalog.ts`). Any platform-evolution work that adds fields will hit this every time until
   codegen or a shared schema source is adopted.
4. **Embedded agent jobs — real-provider-key gates deferred.** Gate #2/#3 for P4 (a real-provider-key
   run + redaction verification on a real trace) remain operationally deferred; `openai_agents`/live
   tool-loop is explicitly blocked from any multi-user-reachable deployment until RBAC (P5.2) and
   workspace isolation (P5.3) are both sealed.
5. **No live E2E validation exists yet** against a real Clerk tenant or the live RF API — P5
   validation is 284 backend tests + 57/57 regression + static E2E (32 passed/4 skipped); no
   live-mode E2E has been run.
6. **Search Router live providers are unvalidated** — Brave/Exa/GitHub keyed providers have never
   been exercised against real API keys from this repo; a live-provider run plus source-type
   vocabulary unification is still pending.
7. **Push-then-redeploy discipline remains a separate, human-gated step** — per the project's own
   git-workflow rule, committing/merging locally does not imply pushing to origin or deploying
   outward-facing changes; any direction chosen here still requires an explicit deploy step before it
   reaches the live node.
