---
schema_version: 2
doc_type: spec
title: "notebooklm-extended Workflow Spec — Async Long-Latency NotebookLM Artifact Runs"
status: active
phase: 1
created: 2026-06-13
owner: nick
related_documents:
  - .claude/specs/workflows/workflow-authoring-spec.md
  - .claude/specs/workflows/research-foundry-swarm-workflow-spec.md
  - .claude/skills/notebooklm/SKILL.md
  - .claude/skills/dev-execution/orchestration/workflow-patterns.md
  - .claude/rules/delegation-modes.md
  - .claude/rules/context-budget.md
  - docs/projects/research-foundry/notebooklm-integration-plan.md
  - docs/projects/research-foundry/research-foundry-mvp-spec.md
script: .claude/workflows/notebooklm-extended.js
---

# notebooklm-extended Workflow Spec

Per-workflow contract for `.claude/workflows/notebooklm-extended.js`. Extends, never
contradicts, `workflow-authoring-spec.md`. Authors: read the master contract first, then
§3.3 EXTENDED RUNS of `docs/projects/research-foundry/notebooklm-integration-plan.md`, then
the `notebooklm` skill at `.claude/skills/notebooklm/SKILL.md`.

---

## Purpose

`notebooklm-extended` implements the **Extended Runs** use case (integration plan §3.3): the
home for **long-latency, rate-limited** NotebookLM artifacts (audio deep-dive 10-20 min,
video 15-45 min) generated across **N notebooks** (typically one notebook per swarm leg /
per topic), with **background polling** and **checkpoint/resume**.

Each notebook flows independently through three stages — **Generate -> Poll -> Collect** —
via `pipeline()`. There is **no inter-item barrier**: a slow or rate-limited notebook never
blocks the others (notebook A can be downloading in Collect while notebook B is still
rendering in Poll). This is the defining difference from a `parallel()` fan-out, which would
force all notebooks to complete a stage before any advances.

The workflow returns a **custom result** (not a standard `ExecutionReport`) with a
`results[]` list and — critically — a `checkpoint` map (`notebook_id -> task_id`). The
operator passes that map back as `args.resume_task_ids` to **resume** a run; the Generate
stage then **reuses** the prior `task_id` instead of regenerating a non-deterministic
artifact. This is how the workflow reconciles audio/video's inherent non-determinism with
the constraint-4 ban on `Math.random()` / non-reproducibility: never regenerate — re-attach.

NLM output here is always a **non-authoritative artifact**. It is recorded in
`runs/<run_id>/evidence_bundle.yaml` under `artifacts.notebooklm_extended[]` and downloaded
to `runs/<run_id>/nlm_artifacts/`. It is **never** spliced into `report_draft.md` and never
becomes a material claim (claim ledger remains the sole authority — integration plan §5.1).

Companion workflow: `notebooklm-report` (integration plan §3.2) handles the **fast,
reliable** artifacts (briefing-doc / mind-map / data-table) inline between `rf synthesize`
and `rf verify`. `notebooklm-extended` is specifically the async/rate-limited home.

---

## `args` Contract

The script handles `args` arriving as a JSON string or object:
`const a = typeof args === 'string' ? JSON.parse(args) : (args || {})`

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `run_id` | string | **yes** | RF run identifier (e.g. `rf_run_20260613_topic`). Downloads land under `runs/<run_id>/nlm_artifacts/` and are recorded in `runs/<run_id>/evidence_bundle.yaml`. |
| `notebooks` | array | no | Length 0..N. Each item: `{ notebook_id (full UUID, OPTIONAL), instructions (optional), label (optional) }`. One notebook per swarm leg / topic. **OPTIONAL** — when omitted/empty, or when any item lacks a `notebook_id`, the run's correlated notebook is resolved (and created on miss) via the correlation CLI at the start of the Generate phase (see *Notebook Resolution* below). |
| `project` | string | no | Project slug scoping the correlation registry. Forwarded to `rf notebooklm resolve --project <project>` during resolution. Only consulted when a resolve is needed (empty `notebooks` or an item missing `notebook_id`). |
| `notebook_mode` | `'project'` \| `'run'` \| `'explicit'` | no | How the run is correlated to a notebook during resolution. Forwarded to `rf notebooklm resolve --mode <notebook_mode>`. Any other value is ignored (CLI/registry default applies). Only consulted when a resolve is needed. |
| `artifact` | `'audio' \| 'video'` | no | Default `'audio'`. Chooses the long-latency generation kind. Anything other than `'video'` normalizes to `'audio'`. |
| `format` | string | no | Generation format. Audio default `deep-dive` (also: `brief`, `critique`, `debate`); video default `explainer` (also: `brief`). |
| `resume_task_ids` | object | no | Map `notebook_id -> prior task_id`. When present for a notebook, Generate **reuses** the task_id (resume — no regeneration). This is the `checkpoint` map from a prior run's return value. |
| `timestamp` | string | no | ISO 8601 timestamp set by Opus pre-flight. Echoed into the return. Never `Date.now()` in script. |
| `dry_run` | boolean | no | If `true`, return `{ status: 'dry_run', parsed_args: a }` without spawning agents. |

### `notebooks[]` item shape

```js
{
  notebook_id: string,   // OPTIONAL. Full UUID — passed as -n on every NLM command. Never partial.
                         // When absent, the resolve step fills it with the run's correlated notebook.
  instructions: string,  // optional. The generation prompt; defaults to a generic overview instruction.
  label: string,         // optional. Used for the artifact filename + agent label; defaults to notebook_id, else index.
}
```

**Pre-flight invariant**: Opus / the operator confirms before invoking this workflow that:
- `notebooklm login` was completed **out-of-band** (auth is a documented PRECONDITION, not a
  Mode D gate — see "Mode D Handling").
- Each explicitly-provided `notebook_id` is a valid full UUID with sources already added and
  indexed. Items without a `notebook_id` (or an empty/omitted `notebooks` list) are resolved
  via the correlation CLI at the start of the Generate phase (see *Notebook Resolution*).
- `runs/<run_id>/` exists (the run is initialized).

### Notebook Resolution (start of Generate, when a `notebook_id` is absent)

The per-item `notebook_id` is **optional**, and `notebooks` itself may be omitted/empty. When
the list is empty, OR any item lacks a `notebook_id`, the workflow resolves the run's
correlated notebook ONCE through the RF correlation CLI at the start of the Generate phase —
before the `pipeline()` starts — via a single Bash-capable `python-backend-engineer` agent
(resolution may **create** the notebook):

```
rf notebooklm resolve --run <run_id> [--project <project>] [--mode <notebook_mode>] --create
```

`--create` makes resolution idempotent: it maps the run to its correlated notebook via
`registries/notebooklm/notebooks.yaml` and creates the notebook on a registry miss. On success
the resolved id is used to **synthesize a single-item `notebooks` list** (when none was
provided) or to **fill the resolved id into any item missing one** (provided ids are
preserved). The agent **degrades** — on any failure (NLM unauthenticated/offline, RPC error,
non-zero exit) it returns `{ resolved: false, reason }`; the workflow continues, and items
that still lack a `notebook_id` follow the existing `genStage` `skipped_no_notebook_id` path.
If, after resolution, there is still nothing to process, the workflow returns `{ status:
'needs_opus', reason: 'notebook_unresolved' }`. It **never throws or fails the pipeline**. The
correlation source is surfaced as `notebook_source` (`explicit` when every notebook_id was
provided, `resolved:<mode>` on a successful resolve, `unresolved` on a degraded resolve).

### No ExecutionGraph / waves

This workflow does NOT use the standard `ExecutionGraph.waves[]` shape. It is a
research-domain workflow with a fixed three-stage pipeline. The `args` contract is the
NLM-specific envelope above, mirroring the custom-return precedent of
`research-foundry-swarm.js`.

---

## Phases

The workflow is implemented as **one** `pipeline(notebooks, genStage, pollStage, collectStage)`.
Each stage assigns `opts.phase` explicitly so the `/workflows` TUI groups correctly even
though items advance through stages independently. Every `phase()` / per-agent `phase`
string below matches `meta.phases` exactly.

| Phase title | Stage | What happens |
|---|---|---|
| `Generate` | `genStage` | Resume short-circuit (reuse `resume_task_ids[nb]`), else budget guard, else a `python-backend-engineer` agent runs `notebooklm generate <kind> "<instructions>" --format <fmt> --json -n <FULL_UUID> --retry 2` → `task_id`. |
| `Poll` | `pollStage` | `python-backend-engineer` agent runs `notebooklm artifact wait <task_id> -n <FULL_UUID> --timeout 2700` (exit 0=done, 2=timeout). Auto-runs in subagent context per NLM autonomy rules. |
| `Collect` | `collectStage` | `python-backend-engineer` agent runs `notebooklm download <kind> ./runs/<run_id>/nlm_artifacts/<label>.<ext> -a <task_id> -n <FULL_UUID>`, then records the `nlm_task_id` checkpoint + artifact path into `runs/<run_id>/evidence_bundle.yaml` (`artifacts.notebooklm_extended[]`). |

`phase('Generate')` is called once before the pipeline starts (the narrator/entry phase). The
notebook resolution step (when needed — see *Notebook Resolution*) runs under this same
`phase('Generate')`, before the pipeline. Each stage then sets its own `{ phase }` per agent so
Poll and Collect group correctly as items reach them.

### Pipeline sequencing note

`pipeline()` (no inter-item barrier) is deliberate: audio/video generation is the
longest-latency, most rate-limited operation in the NLM surface. A `parallel()` barrier
would make the slowest/most-throttled notebook gate every other notebook's download. With
`pipeline()`, each notebook's Collect fires the instant its own Poll returns `ready`.

### Stage carry-forward semantics

- A stage that **throws** drops that item to `null`; nulls are filtered before building the
  return.
- A stage that returns a **skip/terminal status** is carried forward unchanged by the next
  stage (Poll skips items without a real `task_id`; Collect only downloads items whose Poll
  returned `status: 'ready'`). This keeps degraded items in `results[]` for operator review
  rather than dropping them.

---

## Agent Routing

| agentType | Role | edit-less? | Phase | Notes |
|---|---|---|---|---|
| `python-backend-engineer` | Notebook resolver | No (acceptEdits) | Generate | Runs ONCE when the list is empty or any item lacks a `notebook_id`: `rf notebooklm resolve --run <run_id> [--project] [--mode] --create`. Returns the resolved id; degrades to `resolved:false` (no throw). No generate/poll/download, no file writes. |
| `python-backend-engineer` | NLM generate runner | No (acceptEdits) | Generate | Runs `notebooklm generate` via Bash; returns a `task_id`. No download/wait. |
| `python-backend-engineer` | NLM poll runner | No (acceptEdits) | Poll | Runs `notebooklm artifact wait` (auto-runs in subagent context). No generate/download. |
| `python-backend-engineer` | NLM collect runner | No (acceptEdits) | Collect | Runs `notebooklm download` + appends to `evidence_bundle.yaml`. No generate/wait. |

Mirrors the swarm's ingest agents: NLM-driving agents are `python-backend-engineer`
(Bash-capable, `acceptEdits`). Read-only inspection (none needed in this workflow) would use
`codebase-explorer`. **No reviewer agent is used** — this workflow has no review gate, so
constraint 3 (edit-less reviewer agentType) is satisfied vacuously and no agent is
inline-prompted as a reviewer.

Every NLM-driving agent prompt:
- Quotes the **exact** `notebooklm` command from `SKILL.md` with an explicit **FULL-UUID `-n`**.
- Sets a **per-agent `NOTEBOOKLM_HOME`** (`/tmp/nlm-<run_id>-<label>`) so concurrent
  notebooks never share `~/.notebooklm/context.json` (SKILL.md "Parallel agents" guidance).
- Instructs **degrade-on-failure**: never fail the run; record a `skipped_*` status instead.
- Includes "Do NOT git add/commit/push/stash." and forbids `notebooklm delete` (destructive).

---

## Mode D Handling

This workflow does not use the standard `ExecutionGraph.waves[]` and therefore does not call
`modeBoundary()`. Mode D detection is **not applicable**:

- **NLM auth is a PRECONDITION, not a Mode D gate.** Per integration plan §6 (open question
  3) and the ARC/IntentTree precedent, the operator runs `notebooklm login` out-of-band
  before invoking the workflow. The Generate agent does a non-prompting `notebooklm status`
  check and degrades (`skipped_no_auth`) if unauthenticated — it never opens a browser, never
  logs in mid-run, never pauses for human sign-off (constraint 2).
- **Destructive NLM ops are forbidden.** `notebooklm delete` / `notebook delete` are never
  issued by any stage; every agent prompt explicitly forbids them. There is therefore no
  deletion/migration boundary to gate.

The closest analog to a governance gate is the per-item degrade path: rate-limit, timeout,
missing auth, or budget-low all degrade the single item to a `skipped_*` status and leave the
rest of the run intact.

---

## Budget Guards

| Leg | Cost hint | Guard |
|---|---|---|
| Generate (audio/video) | ~60K tokens | If `budget.remaining() < 60_000` at the Generate stage for an item, skip generation **and** all downstream stages for that item, returning `{ notebook_id, status: 'skipped_budget' }`. |
| Poll | ~no generation cost | Only runs for items with a real `task_id`; terminal/skip states are carried forward without a poll agent. |
| Collect | ~no generation cost | Only runs for items whose Poll returned `ready`. |

The Generate budget guard mirrors `research-foundry-swarm.js`'s Ingest pipeline guard
(`budget.remaining() < 60_000`). There is no `while`/loop-until-dry pattern in this workflow,
so the only budget guard needed is the per-item generation-leg guard.

---

## Safety Invariants (multi-notebook)

Stated here per the integration plan §3.3 multi-notebook safety findings:

1. **Always pass explicit FULL-UUID `-n`** on every `generate` / `wait` / `download` command.
   Partial ids are never used (SKILL.md: partial ids can become ambiguous in automation).
2. **Per-agent `NOTEBOOKLM_HOME` isolation** for concurrent notebooks: each agent exports
   `NOTEBOOKLM_HOME=/tmp/nlm-<run_id>-<label>` so concurrent agents never overwrite each
   other's `context.json` (SKILL.md "Parallel agents").
3. **Rate-limit / timeout degrades**, never fails: `--retry 2` on generate; `artifact wait`
   exit 2 (timeout) or exit 1 (failed) → `skipped_rate_limited`; download failure →
   `skipped_download_failed`. The run always returns a result.
4. **Checkpoint/resume reuses, never regenerates.** A non-deterministic artifact is never
   regenerated on resume; the prior `task_id` is re-attached via `resume_task_ids`.
5. **NLM output is non-authoritative.** Every collected artifact is recorded with
   `authoritative: false`, `requires_network: true`, and a reliability note; it never enters
   `report_draft.md` or `claim_ledger.yaml`.

---

## Dry-Run Mode

`args.dry_run === true` → return `{ status: 'dry_run', parsed_args: a }` immediately, before
any required-arg validation or agent spawn. Used by Opus pre-flight to confirm args parsing
and the resume-map shape before committing to a full (expensive) generation run.

---

## Pre-conditions

- [ ] `notebooklm login` completed out-of-band; `notebooklm status` shows "Authenticated as: …".
- [ ] Each `notebooks[].notebook_id` is a valid **full UUID** with sources already added and indexed.
- [ ] `runs/<run_id>/` exists (run initialized); `nlm_artifacts/` will be created by Collect.
- [ ] `args.run_id` and a non-empty `args.notebooks` array are provided (else `status: 'blocked'`).
- [ ] Budget sufficient: at minimum `~60K` tokens per audio/video generation leg actually run.
- [ ] (Resume) `args.resume_task_ids` is the `checkpoint` map from a prior run, if resuming.
- [ ] run-in-worktree: Opus sets up isolation pre-flight; the script asserts this only via
      documentation (the agents append to `evidence_bundle.yaml` and write artifacts under
      `runs/<run_id>/`, but never git add/commit/push/stash).

---

## Post-conditions / Exit Gates

After the workflow returns, Opus verifies:

- [ ] `status === 'complete'` (≥1 artifact collected) OR `status === 'needs_opus'` (inspect
      skipped/degraded items — rate limits, auth, budget — then resume with the `checkpoint`).
- [ ] Collected artifacts exist on disk at `results[].artifact_path` (under
      `runs/<run_id>/nlm_artifacts/`).
- [ ] `runs/<run_id>/evidence_bundle.yaml` contains an `artifacts.notebooklm_extended[]` entry
      per collected artifact, each flagged `authoritative: false`, `requires_network: true`.
- [ ] No NLM-generated prose has entered `report_draft.md` (it is artifact-only).

**Resume**: pass the returned `checkpoint` map back as `args.resume_task_ids` to re-attach
in-flight artifacts without regenerating them.

---

## Return Value

Custom object (not a standard `ExecutionReport`) — same custom-return precedent as
`research-foundry-swarm.js` (integration plan §6 open question 8). Rationale: the workflow is
a research-domain three-stage pipeline over notebooks, not a `waves/phases/tasks` execution
graph; the `checkpoint` map and per-notebook `results[]` are the operator-facing contract and
have no place in the standard schema.

```js
{
  status: 'complete' | 'needs_opus' | 'blocked' | 'dry_run',
  run_id: string,
  notebook_source: string,            // 'explicit' | 'resolved:<mode>' | 'unresolved'
  timestamp: string,                  // echoed from args.timestamp
  results: Array<{
    notebook_id: string | null,
    label: string,
    task_id: string | null,
    status: string,                   // see status table below
    artifact_path: string | null,
  }>,
  checkpoint: { [notebook_id]: task_id },   // pass back as args.resume_task_ids to resume
  report: Array<{ phase, ...stats }>,
}
```

### Top-level `status`

| `status` | Meaning | Opus action |
|---|---|---|
| `complete` | ≥1 artifact collected and downloaded | Record artifacts in the run; proceed |
| `needs_opus` | 0 collected (all skipped/degraded/resumed-pending), OR no notebooks and resolution failed (`notebook_unresolved`) | Inspect `results[]`; for `notebook_unresolved` run `notebooklm login` or pass notebooks explicitly; otherwise address rate-limit/auth/budget and resume via `checkpoint` |
| `blocked` | Missing required args (`run_id`) | Fix `args`, re-invoke |
| `dry_run` | `args.dry_run === true` | Inspect `parsed_args`, no agents ran |

### Per-item `status` values

| `status` | Stage | Meaning |
|---|---|---|
| `collected` | Collect | Downloaded + recorded in evidence bundle (success). |
| `ready` | Poll | Finished rendering but not yet downloaded (Collect did not run / threw). |
| `generating` | Generate | Generation kicked off; `task_id` captured. |
| `resumed` | Generate | Reused a checkpointed `task_id` (no regeneration). |
| `skipped_budget` | Generate | `budget.remaining() < 60_000`; skipped + downstream skipped. |
| `skipped_no_notebook_id` | Generate | Item had no `notebook_id`. |
| `skipped_no_auth` | Generate | `notebooklm status` not authenticated; degraded. |
| `skipped_rate_limited` | Generate / Poll | Rate-limit / GENERATION_FAILED / wait timeout (exit 2) / wait failed. |
| `skipped_generate_null` | Generate | `agent()` returned null (user skipped). |
| `skipped_download_failed` | Collect | Download non-zero exit (generation incomplete / not found). |

---

## Patterns Used

- `pipeline(items, ...stages)` — per-notebook Generate → Poll → Collect with **no inter-item
  barrier** (the defining pattern; integration plan §3.3).
- Per-stage explicit `{ phase }` assignment to avoid races on global phase state inside
  `pipeline()` (master contract §1 `phase` guidance).
- Budget-guarded generation leg (`budget.remaining() < 60_000`) — mirrors
  `research-foundry-swarm.js` Ingest.
- Checkpoint/resume via a returned `checkpoint` map fed back as `args.resume_task_ids`.
- Degrade-on-failure per item — no `parallel()` barrier, no `reviewerGate`, no `fixLoop`,
  no `modeBoundary` (none applicable to this workflow shape).

---

## Extension Points

- **Mixed artifact kinds per notebook**: add a per-item `artifact` field and branch the
  generate command (`audio` vs `video`) per item instead of a single top-level `artifact`.
- **Slide-deck / infographic**: extend `artifactKind` normalization to the other rate-limited
  generation types (`slide-deck` → `.pdf`, `infographic` → `.png`) with their download exts.
- **Per-leg merge into a parent swarm manifest**: a caller (`research-foundry-swarm` /
  `research-foundry-council`) can invoke this via one level of `workflow()` nesting and merge
  each `results[]` entry back into the parent run's manifest (integration plan §3.3 step 3).
- **Tighter poll timeout**: lower `--timeout` from 2700 for audio-only runs (audio caps ~20
  min) to surface rate-limits faster.

---

## Four-Constraints Compliance Notes

```
[x] No FS/shell access in script body — every notebooklm command runs inside a
    python-backend-engineer agent via its own Bash tool; the script only calls
    agent()/pipeline()/phase()/log() and plain JS.
[x] Mode D phases trigger early return — N/A: NLM auth is a documented PRECONDITION
    (operator runs `notebooklm login` out-of-band), not a Mode D gate; destructive NLM
    ops (delete) are forbidden and never issued, so there is no deletion/migration boundary.
[x] All reviewer agents use edit-less agentType — N/A: this workflow has no review gate and
    inline-prompts no agent as a reviewer (constraint 3 satisfied vacuously).
[x] No Date.now() / Math.random() / new Date() in script body — timestamp echoed from
    args.timestamp; per-item labels vary by array index (idx) and caller-provided label,
    the resolver label is fixed (nlm_extended_resolve), never randomness; non-deterministic
    artifacts are re-attached on resume, never regenerated.
[x] meta is a pure literal object — no variables, function calls, or template interpolation.
[x] phase() titles match meta.phases exactly: Generate, Poll, Collect (the resolve step runs
    under phase('Generate'), before the pipeline).
[x] Budget guard present on the generation leg (budget.remaining() < 60_000 in genStage).
[x] notebook_id is optional: empty/partial notebooks are resolved via
    `rf notebooklm resolve ... --create` at the start of Generate; degrades (items left to the
    skipped_no_notebook_id path, or needs_opus/notebook_unresolved when nothing remains), never throws.
[x] Implementation agent prompts include "Do NOT git add/commit/push/stash."
[x] args.dry_run handled before validation (return { status: 'dry_run', parsed_args: a }).
[x] args parsed at top: const a = typeof args === 'string' ? JSON.parse(args) : (args || {}).
[x] Required-arg validation returns { status: 'blocked', reason: 'missing_args', missing }
    rather than throwing; notebooks is no longer required (only run_id).
```

### Durability notes

- No heavy top-level `await agent(..., {schema})` executor — each stage is a small, schema'd
  per-item agent inside `pipeline()`; a schema miss degrades to a carried-forward / `null`
  item (filtered) rather than crashing the run.
- Agents write durable artifacts (downloaded files + `evidence_bundle.yaml` append) before
  returning their structured result; a structured-output miss never discards the downloaded
  artifact on disk.
- No agent commits — NLM artifacts are run-local evidence, not source changes. Opus owns any
  git operations post-run (run-in-worktree precondition documented above).

---

## Governance & Claim-Ledger Notes

1. **Claim authority is unchanged.** NLM-generated audio/video is an **artifact**, never a
   claim. It is recorded in `evidence_bundle.yaml` under `artifacts.notebooklm_extended[]`
   with `authoritative: false` and never spliced into `report_draft.md` (integration plan
   §5.1; `synthesis.py` untagged-claim guard).
2. **Non-reproducible by construction.** Every entry carries `requires_network: true` and a
   reliability note ("NotebookLM-generated; non-reproducible (online, non-deterministic)") so
   downstream consumers know determinism is conditional on NLM availability — preserving the
   offline-first invariant by making the exception explicit (integration plan §5.2).
3. **Fail-soft everywhere.** Missing auth, rate-limit, timeout, or budget-low degrade the
   single item to a `skipped_*` status; the deterministic run artifacts remain the source of
   truth. The run never fails on an NLM error (integration plan §5.5).
4. **Sensitivity** is honored upstream: the operator should not invoke this workflow over a
   `work_sensitive` / `client_sensitive` notebook without the review gate that the
   `notebooklm` writeback target enforces (integration plan §5.3). This workflow downloads
   into the run only; it does not push RF content back to NLM (that is `notebooklm-report` /
   the upload-back integration).
```
