---
schema_version: 2
doc_type: spec
title: "notebooklm-sourcing Workflow Spec — NotebookLM Grounded Sourcing → RF Source Cards"
status: active
phase: 1
created: 2026-06-13
owner: nick
related_documents:
  - .claude/specs/workflows/workflow-authoring-spec.md
  - .claude/specs/workflows/research-foundry-swarm-workflow-spec.md
  - .claude/skills/notebooklm/SKILL.md
  - .claude/skills/research-foundry/SKILL.md
  - .claude/skills/dev-execution/orchestration/workflow-patterns.md
  - .claude/rules/delegation-modes.md
  - .claude/rules/context-budget.md
  - docs/projects/research-foundry/notebooklm-integration-plan.md
  - docs/projects/research-foundry/research-foundry-mvp-spec.md
script: .claude/workflows/notebooklm-sourcing.js
---

# notebooklm-sourcing Workflow Spec

Per-workflow contract for `.claude/workflows/notebooklm-sourcing.js`. Extends, never
contradicts, `workflow-authoring-spec.md`. Authors: read the master contract first, then
the `notebooklm` skill at `.claude/skills/notebooklm/SKILL.md` for the exact CLI surface,
then §3.1 SOURCING of `docs/projects/research-foundry/notebooklm-integration-plan.md`.

---

## Purpose

`notebooklm-sourcing` is the **standalone "sourcing" use case** (§3.1 of the integration
plan): it drives Google NotebookLM (NLM) grounded research + cited Q&A for an RF run's
research questions, then ingests the discovered references into Research Foundry as source
cards via `rf ingest`. It is **purely additive** — no Python/`src/` changes — and
complements the future `NotebookLMAdapter` (the adapter is the in-pipeline `rf swarm run
--adapters notebooklm` path; this workflow is the Opus-orchestrated standalone path that
exercises the same end-to-end flow today, before the adapter exists).

NLM is a **cloud, online-only, non-deterministic** engine. RF is **offline-first,
deterministic-by-default, claim-ledger-authoritative**. The integration philosophy
(identical to the existing ARC/IntentTree bidirectional work): always write a deterministic
on-disk artifact (the RF source card) first; degrade silently on missing auth/CLI; never
let NLM break the pipeline; never let NLM-authored prose enter a report body without a
claim id. Every NLM-derived source card is tagged `usage.requires_network: true` and a
`trust.reliability_notes` reproducibility note.

The workflow spans three phases:

1. **Plan** — one read-only agent reads `runs/<run_id>/research_brief.md` and returns the
   `research_question`, an ordered question list (primary + secondary), `sensitivity`, and
   `max_sources`. No NLM call.
2. **Source** — `parallel()` fan-out (one leg per question, capped at `max_sources`): each
   leg drives the `notebooklm` CLI for grounded research / cited Q&A and maps each NLM
   reference into a `gpt_researcher`-shaped source candidate. Degrades to empty candidates
   on missing auth/CLI; never fails.
3. **Ingest** — `pipeline()` over the merged + deduped candidates: each candidate is
   governance-gated via `rf guard check`, written as a source card via `rf ingest
   ... --source-type notebooklm`, then tagged `requires_network` / non-reproducible.

**Dedup between Source and Ingest is plain in-script JS** (merge by locator url/id), no
agent — mirroring the swarm's `Dedup` phase.

The workflow returns a **custom source manifest**, not the standard `ExecutionReport`. The
deterministic tail (extract → claim-map → synthesize → verify → bundle → writeback) is a
**post-run step** executed by Opus/operator after reviewing the manifest (see §7).

Replaces: the manual "run notebooklm research, copy references, `rf ingest` each" loop.
Fallback: that manual loop, and the eventual `NotebookLMAdapter` (`--adapters notebooklm`).

---

## `args` Contract

The script handles `args` arriving as a JSON string or object:
`const a = typeof args === 'string' ? JSON.parse(args) : (args || {})`

### Top-level fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `run_id` | string | **yes** | — | RF run identifier (e.g. `rf_run_20260613_topic`). Must correspond to an initialized run under `runs/`. |
| `notebook_id` | string | no | — | The NotebookLM notebook the Source legs query via `notebooklm ask -n <id>`. **OPTIONAL** — when absent it is resolved (and created on miss) via the correlation CLI at the end of the Plan phase (see *Notebook Resolution* below). Pass it to skip resolution (correlation mode `explicit`). |
| `project` | string | no | — | Project slug scoping the correlation registry. Forwarded to `rf notebooklm resolve --project <project>` during notebook resolution. If absent, the CLI infers/uses the registry default. Only consulted when `notebook_id` is absent. |
| `notebook_mode` | `'project'` \| `'run'` \| `'explicit'` | no | — | How the run is correlated to a notebook during resolution. `project`: one shared notebook per project; `run`: one notebook per run; `explicit`: caller-supplied. Forwarded to `rf notebooklm resolve --mode <notebook_mode>`. Any other value is ignored (CLI/registry default applies). Only consulted when `notebook_id` is absent. |
| `mode` | `'fast'` \| `'deep'` | no | `deep` | NLM research depth for `source add-research`. `fast`: 5-10 sources, seconds. `deep`: 20+ sources, 2-5 min. Any non-`fast` value normalizes to `deep`. |
| `questions` | string[] | no | — | Operator-supplied questions, included verbatim and ranked first as "primary". If absent, the Plan agent derives the question list entirely from `research_brief.md`. |
| `max_sources` | number | no | `12` | Cap on questions fanned out in Source AND on accepted candidates after Dedup. The Plan agent may recommend a lower cap; the effective cap is `min(plan.max_sources, max_sources)`. |
| `profile` | string | no | `personal` | Key profile: `personal` \| `work_approved` \| `client_approved` \| `offline_only`. Passed to `rf guard check --profile`. |
| `timestamp` | string | no | — | ISO 8601 timestamp set by Opus pre-flight. Echoed into the return. **Never** `Date.now()` in script. |
| `dry_run` | boolean | no | `false` | If `true`, return `{ status: 'dry_run', parsed_args: a }` without spawning agents. |

**Pre-flight invariant** (Opus confirms before invoking):
- `runs/<run_id>/research_brief.md` exists and is non-empty.
- `rf doctor` is green for the workspace.
- **`notebooklm login` has been run out-of-band and the CLI is authenticated** (NLM has no
  REST API; the agents wrap the CLI). This is the NLM equivalent of ARC/IntentTree
  reachability — a documented PRECONDITION, **not** a Mode D gate.
- `rf guard check --profile <profile>` exits 0.

### No ExecutionGraph / waves

This workflow does **not** use the standard `ExecutionGraph.waves[]` shape (same gap noted
in OQ-8 of the integration plan and in `research-foundry-swarm.js`). It is a research-domain
workflow with its own fixed three-phase structure. The `args` contract is the simpler
`run_id` + `notebook_id` + `mode` + `questions` + `max_sources` + `profile` + `timestamp`
envelope above.

---

## Phases

Every `phase()` call in the script matches `meta.phases` exactly: `Plan`, `Source`, `Ingest`.

| Phase title | What happens |
|---|---|
| `Plan` | ONE `codebase-explorer` agent (Mode A, read-only) reads `runs/<run_id>/research_brief.md` (inspecting the run dir if the canonical path is missing), and `swarm_plan.yaml` / `run.yaml` if present. Returns `{ research_question, questions[], sensitivity, max_sources }` via `PLAN_SCHEMA`. Operator-supplied `args.questions` are injected into the prompt and ranked first. No NLM, no rf, no writes. |
| `Source` | `parallel()` over the ordered questions (capped at the effective `max_sources`). Each leg is a `python-backend-engineer` agent that, AT RUNTIME, runs `notebooklm` to obtain grounded, cited evidence and maps each reference into a `gpt_researcher`-shaped candidate. Budget guard: skip a leg (status `skipped_budget`) when `budget.remaining() < 40_000`. |
| `Ingest` | `pipeline()` over the deduped candidates. Each item is a `python-backend-engineer` agent that, AT RUNTIME, runs `rf guard check` then `rf ingest ... --source-type notebooklm`, and edits the new card's front matter to add `usage.requires_network: true` + reliability note. Budget guard: skip the leg (status `skipped`) when `budget.remaining() < 60_000`. |

### Notebook Resolution (end of Plan, when `notebook_id` is absent)

`notebook_id` is **optional**. When it is not supplied, the workflow resolves it through the
RF correlation CLI at the end of the Plan phase — after the question list is confirmed
non-empty, before the Source fan-out — via a single Bash-capable `python-backend-engineer`
agent (NOT the read-only Plan inspector, because resolution may **create** the notebook):

```
rf notebooklm resolve --run <run_id> [--project <project>] [--mode <notebook_mode>] --create
```

`--create` makes resolution idempotent: it maps the run to its correlated notebook via
`registries/notebooklm/notebooks.yaml` and creates the notebook on a registry miss. The agent
returns `{ resolved, notebook_id, notebook_title, project, mode }` and **degrades** — on any
failure (NLM unauthenticated/offline, RPC error, non-zero exit) it returns
`{ resolved: false, reason }` and the workflow returns `{ status: 'needs_opus', reason:
'notebook_unresolved' }` with a clear error; it **never throws or fails the pipeline**. When
`notebook_id` is passed explicitly, resolution is skipped and the correlation source is
recorded as `explicit`; otherwise it is `resolved:<mode>`. After resolution every Source leg
queries the (now always-present) notebook via `notebooklm ask -n <id>` plus
`notebooklm source add-research` for grounded discovery — there is no longer a "no notebook"
discovery-only branch. The resolved id and `notebook_source` flow into the return manifest.

### Dedup (between Source and Ingest, plain JS — no agent)

Mirrors the swarm. Merge all leg candidates; dedup by normalized locator key
(`locator.url` first, then `locator.notebook_source_id`, then `candidate_id`); trim to the
effective `max_sources`. No FS, no shell, no agent. Tracks `degradedLegs` and `skippedLegs`
counts for the manifest/report.

### Exact NLM/RF commands quoted in agent prompts

Quoted verbatim from `.claude/skills/notebooklm/SKILL.md` (Source legs) and verified against
`src/research_foundry/cli_commands.py` (Ingest legs):

Source leg (discovery mode, no `notebook_id`):
```
notebooklm status                                            # cheap auth probe (exit 0 = authed)
notebooklm source add-research "<question>" --mode <fast|deep> --json
notebooklm ask "<question>" --json
notebooklm source fulltext <source_id> --json                # best-effort quote-level evidence
```

Source leg (notebook mode, `notebook_id` present):
```
notebooklm status
notebooklm ask "<question>" --json -n <notebook_id>
notebooklm source fulltext <source_id> --json
```

Ingest leg:
```
rf guard check --profile <profile> --run <run_id> --sensitivity <sensitivity>
rf ingest "<locator>" --run <run_id> --source-type notebooklm --sensitivity <sensitivity> --title "<title>"
```

`--source-type` is a free-form Typer option on `rf ingest`
(`cli_commands.py:196`, default `"other"`); `"notebooklm"` is the correct value and is
accepted as-is. `rf guard check` exits 3 on a governance violation (`ExitCode.GOVERNANCE`).

---

## Candidate Shape (gpt_researcher contract)

Each Source candidate matches the RF `gpt_researcher` source-candidate shape
(`adapters/gpt_researcher.py:76-87`):

```js
{
  candidate_id: string,            // stable, e.g. "nlm-<source_id-or-index>"
  title: string,
  source_type: 'notebook',         // always "notebook" for NLM-discovered candidates
  locator: { url?: string, notebook_source_id?: string },  // >=1 present
  discovery_method: 'notebook_knowledge',
  label: string,                   // one-line relevance tie to the question
  notes: string,                   // "NotebookLM-grounded (cited_text #N); non-reproducible (online)."
  quote?: string,                  // verbatim passage from `source fulltext`, if available
}
```

NLM's synthesized `answer` text is **telemetry only** — it is never emitted as a candidate
field that would flow into the report body. Only the cited `references` become candidates.

---

## Agent Routing

| agentType | Role | edit-less? | Phase | Notes |
|---|---|---|---|---|
| `codebase-explorer` | Sourcing planner (Plan) | Yes (Mode A) | Plan | Reads research brief; returns the ordered question list. No writes, no NLM, no rf. |
| `python-backend-engineer` | Notebook resolver | No (acceptEdits) | Plan | Runs ONCE when `notebook_id` is absent: `rf notebooklm resolve --run <run_id> [--project] [--mode] --create`. Returns the resolved id; degrades to `resolved:false` (no throw). No sourcing, no ingest, no file writes. |
| `python-backend-engineer` | NLM sourcing runner | No (acceptEdits) | Source | One per question. Drives `notebooklm` CLI; maps references → candidates. Degrade-on-failure. Does NOT write files, does NOT run rf, does NOT delete. |
| `python-backend-engineer` | RF ingest runner | No (acceptEdits) | Ingest | One per candidate. Runs `rf guard check` + `rf ingest`; edits ONLY the one new source card to add the `requires_network` tag. Does NOT run NLM, does NOT delete, does NOT git add/commit/push/stash. |

Per the master contract §7, all workflow agents run `acceptEdits`; read-only enforcement is
via the `codebase-explorer` `agentType` definition (`disallowedTools`). There is **no
reviewer gate** in this workflow (constraint 3 is satisfied vacuously — no inline-prompted
reviewer exists). Mirrors the swarm's inner-agent assignment (`python-backend-engineer` for
the CLI-driving ingest agents).

---

## Mode D / Governance Handling

This workflow does **not** use the standard `ExecutionGraph.waves[]` and therefore does not
call `modeBoundary()`. Mode D detection is not applicable: no phase touches auth, payments,
or schema migrations.

- **NLM auth is a PRECONDITION, not a Mode D gate.** The operator runs `notebooklm login`
  out-of-band (NLM has no service-layer auth bridge). If auth is missing at runtime, the
  Source legs degrade (status `skipped_no_auth`, empty candidates) — they do **not** block
  the workflow. This is the deliberate fail-soft posture from §3.1 / §5 of the plan.
- **Destructive NLM ops are forbidden.** Every Source-leg prompt explicitly instructs the
  agent: "NEVER run `notebooklm delete` or `notebooklm notebook delete`." The Ingest-leg
  prompts forbid deleting any notebook, source, or file. This is the workflow-level analog
  of constraint 4's "no destructive ops without sign-off" — encoded in prompt text because
  these workflows need no waves-based Mode D return.
- **Governance preflight** is the `rf guard check` run by each Ingest agent before every
  `rf ingest`. A non-zero exit (3 = governance violation) marks that ingest
  `{ success: false }` and lands it in `manifest.failed_sources`; the workflow continues
  with the remaining candidates.

---

## Dry-Run Mode

`args.dry_run === true` → return `{ status: 'dry_run', parsed_args: a }` immediately, before
any required-arg validation or agent spawn. Used by Opus pre-flight to confirm args parsing.

---

## Budget Conventions

Per-leg cost hints (mirror the swarm):

| Leg | Guard threshold | Rationale |
|---|---|---|
| Source (per question) | `budget.remaining() < 40_000` → skip leg (`skipped_budget`) | One NLM research + ask + fulltext round-trip + mapping. |
| Ingest (per candidate) | `budget.remaining() < 60_000` → skip leg (`skipped`) | `rf guard check` + `rf ingest` + front-matter edit; matches the swarm's `60_000` ingest guard. |

The thresholds are runaway guards, not quality knobs. Skipped legs are counted into
`manifest.skipped_count` and surfaced in the `report`.

---

## Pre-conditions

- [ ] `runs/<run_id>/research_brief.md` exists and is non-empty.
- [ ] RF workspace is initialized (`rf init` complete, `rf doctor` green).
- [ ] **`notebooklm login` has been run out-of-band; `notebooklm status` reports
      authenticated.** (Documented precondition — degrades silently if not.)
- [ ] `rf guard check --profile <profile>` exits 0 before workflow invocation.
- [ ] `args.run_id` matches an existing `runs/` directory.
- [ ] `args.timestamp` is set by Opus pre-flight (ISO 8601 string).
- [ ] Budget is sufficient: at minimum `(N_questions + N_candidates + 1) * ~30K` tokens.

---

## Post-conditions / Exit Gates

After the workflow returns, Opus verifies:

- [ ] `status === 'complete'` (at least one source ingested successfully).
- [ ] `manifest.ingested_count > 0`.
- [ ] Each new source card carries `usage.requires_network: true` and the reliability note.
- [ ] `manifest.failed_sources` reviewed; investigate if failures > 20% of candidates.
- [ ] Source cards exist on disk at the paths in `manifest.source_cards[].path`.

**Post-run steps (NOT run by this workflow — run by Opus/operator after reviewing manifest)**:

```bash
rf extract <run_id> --model-profile rf_extract_cheap
rf claim-map <run_id>
rf synthesize <run_id> --report reports/report_draft.md --model-profile rf_synthesize_deep
rf verify <run_id> --report reports/report_draft.md --claim-ledger claims/claim_ledger.yaml --fail-on-unsupported
# If rf verify exits 7: invoke research-foundry-council workflow before bundling
rf bundle <run_id> --verify --out evidence_bundle.yaml
rf writeback <run_id> --targets meatywiki,skillmeat,ccdash --require-review
```

These are returned in `post_run_commands` for operator convenience.

---

## Return Value (custom shape)

This workflow returns a **custom object**, not a standard `ExecutionReport`, because it is a
research-domain workflow without `waves`. It follows the precedent set by
`research-foundry-swarm.js` (documented in OQ-8 of the integration plan: reuse the swarm's
custom-return rather than forcing the `waves/phases/tasks` shape). The custom shape carries
a domain-specific `manifest` (the ingested source cards) plus `post_run_commands` for the
deterministic tail — neither of which the standard report schema models.

```js
{
  status: 'complete' | 'needs_opus' | 'blocked' | 'dry_run',
  run_id: string,
  profile: string,
  timestamp: string,                 // echoed from args.timestamp
  manifest: {
    ingested_count: number,
    failed_count: number,
    skipped_count: number,           // budget-skipped Source legs + Ingest legs
    source_cards: Array<{ path, candidate_id, locator, title, source_type:'notebooklm' }>,
    failed_sources: Array<{ candidate_id, title, step, exit_code, error }>,
    notebook_id: string | null,
    notebook_source: string | null,  // 'explicit' | 'resolved:<mode>' | null
  },
  notebook_id: string | null,        // top-level mirror (resolved or passed) for convenience
  notebook_source: string | null,    // how notebook_id was obtained: explicit vs resolved:<mode>
  post_run_commands: string[],       // ordered deterministic tail
  report: Array<{ phase, ...stats }>,
}
```

| `status` | Meaning | Opus action |
|---|---|---|
| `complete` | ≥1 source ingested | Run the deterministic tail per `post_run_commands` |
| `needs_opus` | Zero questions / zero candidates / zero ingested, OR notebook could not be resolved (`notebook_unresolved`) | Inspect `error`/`reason` (`no_questions`, `no_candidates`, `notebook_unresolved`); fix auth/brief/connectivity (for `notebook_unresolved`, run `notebooklm login` or pass an explicit `notebook_id`); rerun |
| `blocked` | `run_id` missing (`missing_args`) or Plan agent returned null (`plan_failed`) | Fix `args` or create `research_brief.md` |
| `dry_run` | `args.dry_run === true` | Inspect `parsed_args`; no agents ran |

---

## Patterns Used

- `exploreLegs` shape — `parallel()` fan-out over the question list (Source phase).
- `pipeline()` — per-candidate ingest with no inter-item barrier (Ingest phase).
- Plain-JS dedup — in-script merge/dedup between Source and Ingest (no agent), mirroring the
  swarm's `Dedup`.
- Early-return guards — dry-run, missing-args (`blocked`), plan-failure (`blocked`),
  no-questions / no-candidates (`needs_opus`).
- No `waveFanout`, `modeBoundary`, `reviewerGate`, or `fixLoop` — not applicable to this
  workflow shape.

---

## Governance & Claim-Ledger Notes

1. **Claim authority is unchanged.** NLM prose enters the ledger **only** through a source
   card; it is never pasted into `report_draft.md`. The downstream `rf verify
   --fail-on-unsupported` (exit 4) still enforces that every material claim resolves to a
   `claim_id` or carries `**Inference:**`/`**Speculation:**`.
2. **NLM output is non-reproducible.** Every NLM-derived source card is tagged
   `usage.requires_network: true` + a `trust.reliability_notes` reproducibility note (the
   Ingest agent edits the card after `rf ingest`), preserving the offline-first invariant by
   making the exception explicit rather than silent.
3. **Sensitivity flows into governance.** The run sensitivity (from the Plan agent) is
   passed to both `rf guard check --sensitivity` and `rf ingest --sensitivity`, so the §7.2
   governance rules fire with the correct context.
4. **Fail-soft everywhere.** Missing NLM auth, rate limits, or RPC errors degrade a leg
   (empty candidates, `skipped_no_auth` / `degraded`) rather than failing the run.
5. **No destructive ops.** `notebooklm delete` / `notebook delete` and any file deletion are
   explicitly forbidden in every agent prompt.

---

## Four-Constraints Checklist

```
[x] No FS/shell access in script body — all NLM/rf calls and file edits via agents
[x] No mid-run human sign-off — NLM auth is an out-of-band PRECONDITION, not a Mode D gate;
    no phase touches auth/payments/migration, so no waves-based Mode D return is needed
[x] All reviewer agents use edit-less agentType — N/A: this workflow has NO reviewer gate
    (no inline-prompted reviewer); the only read-only role uses codebase-explorer (Mode A)
[x] No Date.now() / Math.random() / new Date() in script body — timestamp from args.timestamp;
    agent labels vary by array index (q${idx+1}, seenKeys.size) or are fixed
    (nlm_sourcing_resolve), never randomness
[x] meta is a pure literal object — no variables, no function calls, no interpolation
[x] phase() titles match meta.phases exactly: Plan, Source, Ingest (the resolve step reuses
    phase('Plan') — same title, no ghost phase group)
[x] args parsed at top: const a = typeof args === 'string' ? JSON.parse(args) : (args || {})
[x] Dry-run guard immediately after parse: a.dry_run === true → { status:'dry_run', parsed_args }
[x] Required-arg validation returns { status:'blocked', reason:'missing_args', missing } (no throw)
[x] Budget guards on every NLM-generation leg: Source < 40_000, Ingest < 60_000
[x] Inner NLM/ingest/resolve agents are python-backend-engineer; read-only inspector is codebase-explorer
[x] notebook_id is optional: resolved via `rf notebooklm resolve ... --create` at end of Plan;
    degrades to needs_opus (notebook_unresolved), never throws
[x] Inner agent prompts quote the EXACT notebooklm/rf commands and instruct degrade-on-failure
[x] Destructive NLM ops (delete) explicitly forbidden in every agent prompt
[x] Implementation agent prompts include "Do NOT git add/commit/push/stash"
[x] Custom return shape documented (manifest + post_run_commands), not standard ExecutionReport
```

### Durability notes

No heavy top-level executor carries a terminal schema; the per-leg schema calls
(`PLAN_SCHEMA`, `CANDIDATE_LEG_SCHEMA`, `INGEST_SCHEMA`) are small and degrade gracefully
(`parallel`/`pipeline` resolve throwing thunks to `null`, which are `.filter(Boolean)`-ed).
The Ingest agent edits exactly one source card and never commits; RF source cards are the
durable artifact (they persist on disk independent of resume). This workflow performs no git
operations.

---

## Extension Points

- **Notebook mode default**: persist the run's notebook id (from a prior upload-back, §3.4)
  into `run.yaml` so the Plan agent can auto-populate `notebook_id`.
- **Quote-level fidelity**: if `notebooklm source fulltext --json` yields good quote spans
  (OQ-2 in the plan), promote `quote` from best-effort to required and feed it into the
  ingest agent so the source card's `extracted_points[].quote` is populated at ingest time.
- **Adapter convergence**: once `adapters/notebooklm.py` ships, this workflow and
  `rf swarm run --adapters notebooklm` should produce identical source cards; keep the
  candidate shape in sync with `gpt_researcher.py`.
- **Council escalation**: if the deterministic tail's `rf verify` exits 7, chain into the
  `research-foundry-council` workflow before `rf bundle`.
