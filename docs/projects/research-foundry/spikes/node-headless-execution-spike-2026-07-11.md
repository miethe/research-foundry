---
title: "SPIKE — Node-Resident Headless Execution of RF Path-B Runs via ica-claude.sh"
type: spike
created: 2026-07-11
status: draft
author: Nick Miethe (orchestrated by Claude Opus, spike-writer)
feature_slug: node-headless-execution
scope: >
  Design (not implement) a node-resident headless executor that drives Research Foundry
  Path-B research runs (discovery + synthesis + deterministic tail) on the agentic nuc
  (10.42.10.76) using ~/ica-claude.sh (headless Claude Code via IBM ICA), closing gap 1
  ("the API creates work it cannot finish") from the KnitWit nuc-execution AAR.
related:
  - docs/projects/research-foundry/aars/knitwit-extension-runs-nuc-execution-aar-2026-07-11.md
  - .claude/workflows/rf-run-execute.js
  - docs/projects/research-foundry/SERVICE_CONTRACT.md
  - src/research_foundry/services/agent_job_service.py
  - src/research_foundry/services/search_router/router.py
verdict: partial
verdict_confidence: 0.85
---

# SPIKE — Node-Resident Headless Execution of RF Path-B Runs via ica-claude.sh

> **Mode B — Contract/Spec Drafting.** This is a design document. No node service, executor,
> or module is implemented here. Every empirical result below is tagged **[VERIFIED]** (a command
> was actually run and its output observed) or **[INFERENCE]** (reasoned, not directly tested).

---

## 0. Executive Summary

**Web-tool feasibility verdict: PARTIAL.** Empirically, through the IBM ICA gateway:

- **`WebFetch` WORKS** — client-side URL fetch + local Haiku processing; returns real content. **[VERIFIED]**
- **`WebSearch` is BROKEN** — it is *listed* as an available tool but *fails on execution* with a
  gateway `400 {"message":"The provided request is not valid"}` (server-side tool; the ICA gateway
  does not honor it). **[VERIFIED]**

This does **not** block a node executor, because **Path-B discovery does not need the model's
`WebSearch` tool at all.** Research Foundry already ships its own `search_router` with live-capable
discovery providers (Brave, Exa, GitHub) and extraction providers (Firecrawl, Jina). The design
therefore routes **all web discovery through RF's deterministic search-router (API-key gated), not
through the model** — sidestepping the broken `WebSearch` entirely — and uses ICA `claude-sonnet-5[1m]`
only for the *intelligence* layers (query strategy, source curation/ranking, deep reading, carding
judgment, synthesis). The deterministic tail needs no model at all.

**Recommended direction:** Build the executor on RF's **already-scaffolded `AgentJobService`
subprocess-spawn machinery** (governance guard, SSE events, artifact staging, credential delivery
all exist today), implementing the currently-missing `research_foundry.agents.sdk_runner` module as
the headless discovery/synthesis agent — pointed at the ICA gateway. A thinner **`ica-claude.sh`
driver** is a viable faster interim. Either way, the API hands off `planned` runs to the executor via
a new `awaiting_local_execution` sub-state + a watch/queue, and fan-out (which cannot use the
interactive-only Workflow tool) is done by a Python driver spawning bounded-concurrency headless
subagents.

---

## 1. Problem & Scope

Per the AAR (`knitwit-extension-runs-nuc-execution-aar-2026-07-11.md` §2–3), the agentic node can
**scaffold** runs (`POST /api/runs` → capture→triage→plan → `planned`) and **serve** them (API +
viewer), but **cannot execute** them. Execution is Path-B: a Claude Code **Workflow-tool** swarm in
the operator's *interactive* session fans out ~9–12 subagents that do real web discovery and author
source cards into `runs/<id>/sources/`, followed by a deterministic, model-free `rf` tail. The
Workflow tool is interactive-session-only and the node has no mechanism to drive the swarm, so
API-created runs strand at `planned` until a human notices. This is gap 1 (**[High]** in the AAR):
*"the API creates work it cannot finish."*

**In scope:** design of a node-resident headless executor (mechanism + API handoff + fan-out sans
Workflow tool), model routing, concurrency/rate-limit handling, risks, phased plan.

**Out of scope:** implementation; the viewer-deploy foot-gun (AAR gap 2) and scaffold-junk GC (gap 3);
non-Claude provider stacks (GPT-5.x/Perplexity per the KnitWit Operating Spec).

---

## 2. The Web-Tool Feasibility Gate (empirical results)

All three probes were run against the **live IBM ICA gateway** via `~/ica-claude.sh`
(`ANTHROPIC_BASE_URL=https://api.nextgen-beta.ica.ibm.com/ica`, model
`claude-sonnet-5[1m]`, 1M context confirmed in `modelUsage`). Probes were executed from the Mac; the
gateway and wrapper are host-independent (see §2.4 caveat).

### 2.1 Tool inventory — WebSearch/WebFetch are present in the manifest **[VERIFIED]**

`ica-claude.sh --model claude-sonnet-5[1m] --output-format json -p "List the EXACT tool names…"`
returned a manifest including `Bash`, `Read`, `Write`, `Edit`, `Agent`, `Task*`, `Skill`,
`Workflow`, **`WebFetch`**, **`WebSearch`**, plus MCP servers (`context7`, `intenttree`, `stitch`,
`openai-docs`). Presence in the manifest is necessary but **not sufficient** — a listed tool can
still fail on execution.

### 2.2 WebSearch — BROKEN on execution **[VERIFIED]**

Prompt instructed the model to actually *use* `WebSearch`. Result:

```
WEBSEARCH_FAILED: API Error: 400 {"message":"The provided request is not valid"}.
Received Model Group=claude-haiku-4-5, Available Model Group Fallbacks=None
```

`server_tool_use.web_search_requests: 0` confirms nothing executed. **`WebSearch` is a server-side
tool** — the search is executed by the Anthropic API backend, and the ICA gateway rejects that
server-tool request (it routes the search sub-call to a `claude-haiku-4-5` model group that the
gateway will not serve). **Conclusion: the model's `WebSearch` cannot be relied on through ICA.**

### 2.3 WebFetch — WORKS on execution **[VERIFIED]**

Prompt instructed the model to *use* `WebFetch` on `https://example.com`. Result:

```
The page's main heading is **"Example Domain"**.
```

`modelUsage` shows a small `claude-haiku-4-5[1m]` pass (208 in / 19 out) alongside the sonnet-5 main
turn — i.e. Claude Code fetched the URL **client-side** and used its internal small model to process
the page. `server_tool_use.web_fetch_requests: 0` confirms it is **not** a server-side tool. Because
the fetch happens client-side, the ICA gateway is never asked to run a server tool, so it succeeds.
**Conclusion: `WebFetch` is fully usable through ICA for reading known URLs.**

### 2.4 Node-parity caveat **[INFERENCE]**

Probes ran from the Mac. The MeatyWiki-precedent investigation confirmed the node carries a
**byte-identical** `~/ica-claude.sh` and `~/.claude/ica-settings.json` (same IBM gateway URL, same
model pins) **[VERIFIED by codebase-explorer]**. Gateway tool-execution behavior is a property of the
*gateway + Claude Code CLI version*, not the client host, so the WebSearch-fails / WebFetch-works
result is expected to hold on the node. The only unverified variable is the node's local Claude Code
CLI version. **→ Phase 0 must re-run the three probes on the node (`ssh agentic-nuc`) before build.**

### 2.5 Why PARTIAL is still a green light

| Path-B web need | Normal (interactive) tool | On ICA | Replacement on-node |
|---|---|---|---|
| Find candidate URLs from a query | `WebSearch` | ❌ broken | **RF `search_router` discovery providers** (Brave/Exa/GitHub) |
| Read a known URL into a source card | `WebFetch` | ✅ works | `WebFetch` **or** RF `search_router` extraction providers (Firecrawl/Jina) |

The discovery swarm's *only* hard dependency on a broken tool is URL-finding, and RF already owns a
deterministic substitute. **The executor is designed to not call the model's web tools at all** (see §4).

---

## 3. Precedent & Existing Substrate (what already exists)

### 3.1 MeatyWiki is NOT a headless-executor precedent **[VERIFIED]**

Investigation found MeatyWiki runs as a **permanent daemon** (`meatywiki-portal.service` +
`-ui.service`); it does **not** run a headless ICA executor. External delegators (the Operator,
CCDash) invoke `~/ica-claude.sh` **on-demand** via the Python `IcaDelegateAdapter`
(`agentic_meta_dev/src/operator_core/adapters/ica_delegate.py`), which shells
`ica-claude.sh --append-system-prompt-file <ctx> --output-format json -p <prompt>`, captures the JSON
envelope, redacts secrets, and returns an `AdapterResult`. **No timer/cron/queue and no web-tool use**
— MW's delegations are Bash/file/reasoning work. **Reusable patterns for RF:** (a) the wrapper +
availability-probe, (b) JSON-envelope capture, (c) fail-closed redaction before persistence,
(d) `--append-system-prompt-file` for injecting agent-persona context. **Not reusable:** MW gives RF
no batch-executor or fan-out pattern — RF must design its own.

### 3.2 `ica-claude.sh` wrapper **[VERIFIED]**

`exec claude --settings ~/.claude/ica-settings.json --fallback-model <opus/sonnet/haiku [1m] chain> "$@"`.
Pins `ANTHROPIC_MODEL=claude-opus-4-8[1m]`; `ica-settings.json` sets
`ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-5[1m]`. `--model claude-sonnet-5[1m]` override works
**[VERIFIED]**. The wrapper does **not** pass `--allowedTools` — tool governance is Claude Code's, so
the executor must pass its own `--allowedTools` to constrain the headless agent (see §4.4).

### 3.3 RF `AgentJobService` — a ready-made subprocess-spawn substrate **[VERIFIED]**

`src/research_foundry/services/agent_job_service.py` + `api/routers/agent_jobs.py` already implement
a substantial headless-job harness:

- `POST /agent-jobs` (`launch_job`) → `spawn_job()` runs a **subprocess** child; `_build_command()`
  defaults `_cmd_module = "research_foundry.agents.sdk_runner"`; supports `command_override`.
- Per-job **credential file** delivery (temp file, crash-safe unlink), registry of `(Popen, cred_path)`.
- **Governance guard** already wired: child exit-code `3` (GOVERNANCE block) → HTTP 422; `7`
  (HUMAN_REVIEW) → 400.
- **SSE event stream** (`GET /agent-jobs/{id}/events`) with terminal states
  `completed | failed | canceled | accepted`; **artifact staging** (`/agent-jobs/{id}/artifacts`).
- **Job-tool catalog** (in-process handlers) already maps `run_search`, `extract_urls`, and
  `create_source_card` — i.e. RF-native discovery/carding tools an SDK agent can call **without any
  model web tool**.
- `claude_agent_sdk` and `openai_agents` are explicitly designated **subprocess-spawned** providers.

**Gap [VERIFIED]:** `src/research_foundry/agents/` is **empty** — the referenced
`research_foundry.agents.sdk_runner` module **does not exist yet**. The spawn machinery is built; the
headless agent body it spawns is not.

### 3.4 RF `search_router` — the deterministic web substrate **[VERIFIED]**

`src/research_foundry/services/search_router/router.py` is "offline-first and degrade-safe" with
provider adapters under `providers/`: **brave.py** (`discovery`, `https://api.search.brave.com`, gated
on `RF_BRAVE_API_KEY`/`BRAVE_API_KEY`), **exa.py**, **firecrawl.py**, **github.py**, **jina.py**. Each
`available()` = "required module importable AND ≥1 env key set." Per project memory
(`search-router-mvp-offline`), providers are implemented but **validated offline only** — a live
discovery run with a real key is still pending. **This is the substitute for the broken `WebSearch`.**

---

## 4. Proposed Architecture

### 4.1 Guiding principle: model does judgment, RF does web I/O

The headless agent **never** calls the model's `WebSearch`. All URL discovery goes through RF's
`search_router` (discovery providers, API-key gated). Reading/extraction goes through the
`search_router` extraction providers (Firecrawl/Jina) **or** `WebFetch` (which works on ICA). ICA
`claude-sonnet-5[1m]` supplies only: query-strategy expansion, candidate ranking/curation, deep
reading judgment, source-card authoring, and synthesis narrative. The deterministic tail is model-free.

```
POST /api/runs  ──►  planned  ──►  awaiting_local_execution  (handoff marker)
                                          │
                          ┌───────────────┴────────────────┐
                          │   NODE EXECUTOR (watch + lock)  │
                          └───────────────┬────────────────┘
                                          │  claims one run (global "one deep swarm" lock)
                                          ▼
   ┌──────────────────────── DISCOVERY (Python fan-out driver) ─────────────────────────┐
   │  bounded-concurrency subagents, each a headless job:                                │
   │   [ICA sonnet-5] plan queries  ─►  [RF search_router] Brave/Exa/GitHub → URLs       │
   │   [RF search_router] Firecrawl/Jina extract  (or [ICA] WebFetch) → page text        │
   │   [ICA sonnet-5] read + judge + author source_card.md → runs/<id>/sources/          │
   └────────────────────────────────────────────┬───────────────────────────────────────┘
                                                 ▼
   ┌──────────────── DETERMINISTIC TAIL (no model) — same host, shared FS ───────────────┐
   │  rf extract → rf claim-map → rf synthesize --deterministic --draft                   │
   │            → rf verify → rf bundle --verify → rf writeback                           │
   └──────────────────────────────────────────────────────────────────────────────────────┘
                                                 ▼
                          run → verified/published (viewer re-export)
```

### 4.2 Executor mechanism — two options, one recommendation

**Option A (RECOMMENDED, strategic): `AgentJobService` + implement `sdk_runner`.**
Implement the missing `research_foundry.agents.sdk_runner` as the headless discovery/synthesis agent
(Claude Agent SDK or a `claude -p` harness), spawned by the existing `spawn_job()`. Point its
`ANTHROPIC_BASE_URL`/model at the ICA gateway (reuse `ica-settings.json`). It calls the existing
job-tool catalog (`run_search`, `extract_urls`, `create_source_card`) — all RF-native, all governed.
- **Pros:** governance guard, SSE progress, artifact staging, credential delivery, cancellation, and
  RBAC scoping **already exist**; tools are RF-owned (no model-web-tool dependency); single coherent
  governance surface; artifacts land through RF's redaction path.
- **Cons:** must build `sdk_runner`; must confirm the SDK/harness honors ICA base-url + `[1m]` model.

**Option B (interim, thinner): external `ica-claude.sh` driver.**
A Python/shell driver fans out `ica-claude.sh --model claude-sonnet-5[1m] --append-system-prompt-file
<rf_*_agent_persona> --allowedTools Bash,Read,Write --output-format json -p <task>` subprocesses.
Carders reach the web by shelling `rf search` / `rf fetch` (which internally use `search_router`),
**not** the model's `WebSearch`.
- **Pros:** fastest to stand up; mirrors the proven MeatyWiki `IcaDelegateAdapter` shape; no SDK
  dependency; identical to how the interactive `rf-run-execute.js` workflow already thinks.
- **Cons:** re-implements job lifecycle/governance/artifact-staging that `AgentJobService` already
  gives Option A; JSON-envelope parsing is brittle; concurrency/rate-limit control is hand-rolled.

**Recommendation:** ship **Option B as an MVP** to close gap 1 quickly, then **migrate to Option A**
as the durable path once `sdk_runner` exists. Both share the §4.3 handoff and §4.4 fan-out design.

### 4.3 API → executor handoff

1. **New run sub-state `awaiting_local_execution`** (AAR-recommended). `POST /api/runs` continues to
   run capture→triage→plan, then sets `awaiting_local_execution` instead of leaving a bare `planned`
   — making stranded runs a *surfaced queue item*, not something a human stumbles on. `planned` is
   reserved for runs with no executor intent.
2. **Watch/claim loop.** The executor (systemd `--user` service on the node, linger-enabled) polls
   the API/registry for `awaiting_local_execution` runs (or subscribes to a queue). On pick-up it
   atomically transitions `awaiting_local_execution → running` (claim), preventing double-execution.
   Reuse the AgentJob SSE/event pattern for progress. **[INFERENCE]** a lightweight file/registry
   marker is sufficient; a full message broker is YAGNI for single-node single-operator.
3. **Filesystem coherence (hard invariant).** Discovery subagents and the deterministic tail **must
   share one filesystem** — the whole Path-B premise (AAR §2.3–2.4). On-node this is native (both run
   on the nuc against `runs/<id>/sources/`). The `rf` shim split-brain trap from the AAR
   (`AOS_TARGET=node` SSH-exec) does **not** apply here because the executor *is* on the node; it must
   pin the local on-node `rf` binary for the tail.
4. **Terminal + writeback.** On tail success → `verified`/`published`, trigger viewer re-export.
   The API should also **commit the runs it scaffolds/executes** (AAR gap 2 best-fix) so landing is
   not a manual ritual — noted as an adjacent fix, out of this spike's build scope.

### 4.4 Fan-out without the Workflow tool

The interactive **Workflow tool is unavailable headless** — fan-out is done by a **driver process**:

- **Discovery lead (1 ICA call):** given `swarm_plan`/`research_brief`, expand into N source-strategy
  work units (query clusters / domains). Mirrors the `rf_discovery_lead` persona.
- **Driver fan-out (Python):** spawn N discovery/carding subagents with **bounded concurrency**
  (Option A: `spawn_job()` per unit; Option B: `ica-claude.sh` subprocess per unit). Each subagent
  works its assigned query cluster: `search_router` discovery → extraction → ICA-authored
  `source_card.md`. Personas already exist as agent definitions (`rf_domain_researcher`,
  `rf_source_scout`, `rf_deep_reader`, `rf_source_carder`) and are injected via
  `--append-system-prompt-file` (Option B) or the SDK agent config (Option A).
- **Note:** headless ICA sessions *do* expose the `Agent`/`Task` tools **[VERIFIED in §2.1]**, so a
  single ICA orchestrator *could* self-fan-out. **Rejected:** its subagents inherit the same broken
  `WebSearch`, one long session is hard to rate-limit/cancel, and it duplicates `AgentJobService`.
  An **external driver with explicit bounded concurrency** is preferred.
- **Barrier + tail:** driver waits for all carders (or a timeout/partial-quorum), then runs the
  deterministic tail in-process on the same host. **Never trust workflow-reported `bundle_ok`** —
  re-run authoritative `rf verify` as the gate (project memory `rf-run-execution-path-b`).
- **`--allowedTools` hardening:** headless subagents get a minimal allowlist (e.g.
  `Bash(rf …),Read,Write` for Option B; the RF job-tool set for Option A). **Do not** grant broad
  Bash or web tools — least privilege, and `WebSearch` is dead weight anyway.

---

## 5. Model Routing

| Stage | Engine | Model | Effort | Rationale |
|---|---|---|---|---|
| Query strategy / discovery-lead planning | ICA headless | `claude-sonnet-5[1m]` | adaptive | Judgment; cheap free-tier offload; 1M context holds brief + plan |
| URL discovery (find candidates) | **RF `search_router`** | — (no model) | — | Deterministic providers; **replaces broken `WebSearch`** |
| Page extraction (read known URL) | RF extraction providers **or** `WebFetch` | — / client-side Haiku | — | Both work; `WebFetch` verified on ICA |
| Deep read + source-card authoring | ICA headless | `claude-sonnet-5[1m]` | adaptive | Curation/credibility judgment |
| Synthesis draft (narrative) | ICA headless | `claude-sonnet-5[1m]` | adaptive | Path-B uses `synthesize --deterministic --draft`; model drafts prose only |
| Extract / claim-map / verify / bundle / writeback | **`rf` deterministic tail** | — (no model) | — | Model-free by design; the governance authority |

ICA fallback chain (`opus-4-8[1m] → … → sonnet-5 → haiku`) degrades under load; pin `sonnet-5` via
`--model` for cost/consistency. **Cost note [INFERENCE]:** probe envelopes reported
`total_cost_usd ≈ $0.78–1.05` per call, but ICA is the **free owner-offload tier** — the dollar figure
is the notional native-API equivalent, not an actual charge. The real constraint is **rate limits**,
not spend (see §6).

---

## 6. Concurrency & Rate-Limit Handling

- **Global "one deep swarm at a time" lock (hard).** Project memory (`rf-run-execution-path-b`) and
  the AAR (§4) both record that concurrent deep swarms trigger carder rate-limiting. The executor
  **must hold a node-global lock** so only one deep run executes at once; additional
  `awaiting_local_execution` runs queue behind it. Reuse the redeploy `flock` pattern.
- **Bounded intra-run fan-out.** Cap parallel carders (start **≤4**, tune) to stay within ICA
  free-tier limits. The driver owns a semaphore; on `429`/gateway-degrade, back off and retry with
  jitter (mirror the AAR's "sequential discipline paid off").
- **ICA degrade-safe.** On repeated gateway failures the run pauses to `awaiting_local_execution`
  (re-queue) rather than failing hard — matches `search_router`'s degrade-safe ethos.
- **Cancellation** already exists via `AgentJobService.cancel_job` (Option A) — child unlinked, status
  → `canceled`.

---

## 7. Risk Assessment

| # | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| R1 | Node Claude Code CLI version behaves differently than Mac for web tools | High | Low | **Phase 0** re-runs the 3 probes on-node before any build (§2.4) |
| R2 | `search_router` providers never live-validated (only offline) → no real URLs | High | Medium | Phase 1 gates on a live `rf search` run with a real `RF_BRAVE_API_KEY`; deal-breaker if unfixable |
| R3 | `WebSearch` silently "fixed" then re-broken by ICA changes → design regresses to depend on it | Medium | Low | Design **never** uses model `WebSearch`; immune by construction |
| R4 | Concurrent swarms rate-limited by ICA free tier | High | High (if unguarded) | Global one-swarm lock + bounded fan-out + backoff (§6) |
| R5 | FS split-brain (agents write local, tail runs elsewhere) — the AAR shim trap | High | Low on-node | Executor pins on-node `rf`; both stages same host; never use `AOS_TARGET=node` shim |
| R6 | `sdk_runner` (Option A) can't honor ICA base-url/`[1m]` model | Medium | Low | Interim Option B (`ica-claude.sh`) is verified-working; de-risks Option A |
| R7 | API scaffolds untracked runs the destructive viewer-deploy deletes (AAR gap 2) | High | Medium | Adjacent fix: API commits executed runs; non-destructive deploy (out of build scope, flagged) |
| R8 | Governance bypass in headless path (secrets, sensitivity) | High | Low | Option A reuses wired governance guard (exit 3→422) + redaction; Option B must add redaction (copy `IcaDelegateAdapter`) |
| R9 | Quality regression vs interactive Path-B (191 claims / 0 unsupported baseline) | Medium | Medium | Keep `[claim:clm_NNN]` gate + authoritative `rf verify`; compare first headless run against baseline before trusting |

---

## 8. Phased Implementation Plan (design only — do not build here)

- **Phase 0 — On-node feasibility re-confirmation (0.5 pt).** SSH to the node; re-run the three §2
  probes (`--model claude-sonnet-5[1m]`) to confirm WebSearch-fails / WebFetch-works parity, and run
  `rf search "<query>"` with a real `RF_BRAVE_API_KEY` to confirm live URL discovery. **Gate: both
  must pass (R1, R2) before Phase 1.**
- **Phase 1 — Search-router live-provider hardening (3 pt).** Wire + validate ≥1 live discovery
  provider (Brave/Exa) end-to-end producing real candidate URLs, and ≥1 extraction path
  (Firecrawl/Jina or `WebFetch`) producing page text into a `source_card.md`. Deliver a deterministic
  `rf search`/`rf fetch` → source-card slice with no model in the loop.
- **Phase 2 — API handoff + `awaiting_local_execution` (3 pt).** Add the sub-state; make `POST
  /api/runs` set it; add the executor watch/claim loop + node-global one-swarm `flock`; atomic
  `awaiting_local_execution → running` claim.
- **Phase 3 — Discovery driver + fan-out MVP (Option B) (5 pt).** Python driver spawning bounded
  `ica-claude.sh` carder subprocesses (personas via `--append-system-prompt-file`, hardened
  `--allowedTools`), each using `rf search`/`rf fetch` + ICA carding. Barrier → deterministic tail
  (pin on-node `rf`) → authoritative `rf verify` gate → writeback + viewer re-export. Add redaction.
- **Phase 4 — First governed headless run + baseline compare (2 pt).** Execute one real deep run
  headless; compare claims/unsupported against the interactive baseline (AAR: 191 claims / 0 unsup).
  Only trust the path if verify-clean.
- **Phase 5 (strategic migration) — `sdk_runner` + `AgentJobService` (8 pt).** Implement
  `research_foundry.agents.sdk_runner`; migrate fan-out to `spawn_job()` with the RF-native job-tool
  catalog; retire the hand-rolled Option-B lifecycle in favor of the wired governance/SSE/artifact
  surface. Confirm SDK honors ICA base-url + `[1m]` (R6).

**Suggested tier:** the full build (Phases 0–5) is **Tier 3** (≥13 pts, no comparable past feature,
`risk_level: high`) → warrants a PRD + Implementation Plan after this spike. The MVP subset
(Phases 0–4, Option B) is a bounded Tier 2.

---

## 9. ADR Recommendations

- **ADR-N1 — "Headless RF discovery routes web I/O through `search_router`, never the model's web
  tools."** Records the empirical WebSearch-broken / WebFetch-works finding as the forcing function
  and makes provider-based discovery the standing architecture (immune to ICA tool regressions).
- **ADR-N2 — "Node executor is a governed job, not an ad-hoc script."** Chooses `AgentJobService` +
  `sdk_runner` as the durable substrate (with `ica-claude.sh` driver as sanctioned interim), so the
  headless path inherits governance/redaction/SSE rather than re-implementing them.
- **ADR-N3 — "One deep swarm at a time is a node-global invariant."** Elevates the memory/AAR
  operational rule to an enforced lock in the executor.

---

## 10. Handoff Checklist (for `prd-writer` / `implementation-planner`)

- [ ] Phase 0 probes re-run on-node and passing (WebFetch ✅, WebSearch ❌-expected, `rf search` live ✅).
- [ ] Decision recorded: MVP via Option B (`ica-claude.sh` driver) then migrate to Option A (`sdk_runner`).
- [ ] `awaiting_local_execution` sub-state spec'd in `SERVICE_CONTRACT.md`; `planned` semantics clarified.
- [ ] Executor systemd `--user` unit design (watch loop, `flock`, linger) drafted for the node.
- [ ] `--allowedTools` least-privilege allowlist defined for headless carders.
- [ ] Redaction path confirmed for Option B (port from `IcaDelegateAdapter`).
- [ ] Adjacent AAR gap-2 fix (API commits executed runs; non-destructive viewer deploy) tracked separately.
- [ ] Baseline-compare acceptance criterion set (verify-clean vs interactive Path-B).

---

## Appendix A — Verification Ledger

| Claim | Status | Evidence |
|---|---|---|
| ICA lists WebSearch + WebFetch | VERIFIED | tool-list probe output (§2.1) |
| WebSearch fails on ICA (400, server-tool) | VERIFIED | `WEBSEARCH_FAILED … Model Group=claude-haiku-4-5` (§2.2) |
| WebFetch works on ICA (client-side) | VERIFIED | returned "Example Domain"; local haiku pass (§2.3) |
| `--model claude-sonnet-5[1m]` override works via ica-claude.sh | VERIFIED | `modelUsage` shows sonnet-5, 1M ctx |
| MeatyWiki has no headless ICA executor (daemon + on-demand adapter) | VERIFIED | codebase-explorer read of units + `ica_delegate.py` |
| `AgentJobService` spawns subprocess SDK jobs; governance/SSE/artifacts/tools wired | VERIFIED | grep of `agent_job_service.py` + `agent_jobs.py` |
| `research_foundry.agents.sdk_runner` referenced but not implemented (empty `agents/`) | VERIFIED | `ls src/research_foundry/agents/` empty; `_cmd_module` ref |
| `search_router` has Brave/Exa/Firecrawl/GitHub/Jina, offline-first, env-key gated | VERIFIED | grep of `search_router/providers/*.py` |
| `POST /api/runs` leaves runs `planned` | VERIFIED | AAR §2 + runs router / export status |
| Node ICA behavior == Mac ICA behavior | INFERENCE | identical wrapper/settings/gateway; node CLI version unverified → Phase 0 |
| `search_router` returns real URLs with a live key | INFERENCE | providers implemented; validated offline only (memory) → Phase 1 |
| ICA reported `$` cost is notional (free offload tier) | INFERENCE | global CLAUDE.md: ICA = free owner-scoped offload |
