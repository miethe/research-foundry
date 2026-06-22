---
schema_version: 2
doc_type: spec
title: "execute-plan Workflow Spec — Tier 2/3 Plan Execution (Research Foundry)"
status: active
created: 2026-06-22
owner: nick
related_documents:
  - .claude/specs/workflows/workflow-authoring-spec.md
  - .claude/specs/workflows/schemas/execution-graph.schema.json
  - .claude/specs/workflows/schemas/execution-report.schema.json
  - .claude/skills/dev-execution/orchestration/workflow-patterns.md
  - .claude/plans/tiered-workflow-overhaul.md
  - .claude/rules/delegation-modes.md
  - .claude/rules/context-budget.md
workflow_script: .claude/workflows/execute-plan.js
registry_entry: .claude/specs/workflows/workflow-registry.md
command: .claude/commands/dev/execute-plan.md
---

# execute-plan Workflow Spec (Research Foundry)

Per-workflow contract for `.claude/workflows/execute-plan.js`. Extends, never contradicts,
`workflow-authoring-spec.md`. Read the master contract first.

---

## Purpose

`execute-plan` is the Tier 2/3 prime target. It replaces the manual Opus dispatch-and-poll wave
loop in `/dev:execute-plan` with a deterministic background script that:

- Runs waves sequentially (dependency ordering preserved).
- Fans phases within each wave out in parallel.
- Dispatches tasks through precomputed file-ownership batches (serial batches, parallel within).
- Routes each task to the exact registered RF specialist named in `task.assigned_to`.
- Gates each phase with a tier-appropriate reviewer; runs a budget-guarded fix-loop on rejection.
- Detects Mode D boundaries and halts, returning control to Opus before any high-risk agents spawn.
- Updates progress YAML per phase via a `trackerStep` agent (no FS in script).
- Returns a structured `ExecutionReport` Opus post-processes for merges, commits, and plan completion.

Replaces: the `parallel(Task(...))` wave loop in the `/dev:execute-plan` command.
Fallback: the manual loop remains until the pilot gate passes.

---

## `args` Contract

**Canonical schema**: `.claude/specs/workflows/schemas/execution-graph.schema.json`

The script accepts one `args` value: a serialized `ExecutionGraph`. Opus builds it pre-flight from
the plan's `wave_plan` frontmatter (~2–3K tokens) and passes it when invoking the workflow. **The
script never reads plan files itself** (constraint 1). It parses `args` (JSON string or object) at
the top before any destructuring.

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `waves` | `Wave[]` | yes | Sequential dependency levels. Each wave completes before the next begins. |
| `tier` | `1\|2\|3` | yes | Execution tier. Retained for signature compatibility; reviewer routing is per-phase. |
| `plan_ref` | `string` | yes | Relative path from RF repo root to the source plan file. Agents may read it. |
| `timestamp` | `string` | yes | ISO 8601 from Opus pre-flight. Never generated inside the script. |
| `budget_total` | `integer` | no | Token ceiling, derived from plan `effort_estimate`. |
| `dry_run` | `boolean` | no | When `true`, return `{status:'dry_run', graph}` immediately, no agents spawned. |
| `progressFile` | `string` | no | Resolved path to the per-phase progress YAML. Set by Opus pre-flight. |
| `provider_routing_enabled` | `boolean` | no | DEFAULT FALSE. When true, AC validation routes to codex-executor two-stage (P3) and `phase.provider:'bob'` routes fix-cycles to bob-delegate-executor (P4). These offload agentTypes are NOT in RF's default roster — leave off for the standard RF path. |
| `phase_owner_nesting_enabled` | `boolean` | no | DEFAULT FALSE. When true, adaptive phase-owners MAY nest bounded depth-1 implementers (single-committer). Off → byte-for-byte pre-pilot prompt. |

### Wave / Phase / Task shape

See `execution-graph.schema.json` for the full nested definition. Key fields:

**Phase-level** (`waves[].phases[]`):

| Field | Default | Script use |
|---|---|---|
| `mode` | — | `'D'` triggers `modeBoundary` → early return. |
| `review_intensity` | `standard` | `councilEscalation()` routing (per-phase only): `council` → `council-review`; `tier3` → `karen`; `standard`/unset → `task-completion-validator`. |
| `isolation` | `shared` | `'worktree'` → `isolation:'worktree'` on each task agent. |
| `phase_strategy` | `static` | `'adaptive'` → single `agentType:'phase-owner'` for the whole phase. |
| `fix_agent` | — | Override agentType for fix-loop; falls back to first task's `assigned_to`. |
| `batches` | — | Precomputed by Opus. Serial outer loop; `parallel()` inner loop per batch. |
| `provider` | — | `'bob'` (with `provider_routing_enabled`) routes fix-cycles to bob-delegate-executor after a Mode-D guard. |

**Task-level** (`phases[].tasks[]` / `phases[].batches[][]`): `id`, `prompt` (must include "Do NOT
git add/commit/push/stash"), `assigned_to` (agentType; unknown value or `hitl:true` → HITL gate),
`model`, `isolation`, `hitl`.

---

## Phases

`meta.phases` (displayed in the `/workflows` TUI): `Dry run`, `Wave wave-1`..`Wave wave-5`,
`Review`, `Fix cycle 1`, `Fix cycle 2`, `Progress update`. Phase groups are created via
`phase('Wave <id>')` etc.; the literal list in the script must match `meta.phases` exactly.

---

## Agent Routing

### Implementation agents (`agentType = task.assigned_to`)

The script reads `task.assigned_to` from the graph and passes it as `agentType` — never
hard-coded. Common RF values: `python-backend-engineer`, `ui-engineer-enhanced`, `ui-engineer`,
`frontend-developer`, `data-layer-expert`, `refactoring-expert`. The known-agent set in the script
(`KNOWN_AGENT_TYPES`) is RF's roster; an `assigned_to` outside it is treated as a HITL gate.

**RF validation**: every implementation/fix prompt carries validation guidance — Python uses
`./.venv/bin/python -m pytest` (NOT the pyenv `python` shim — it fails with "No module named
research_foundry"), `--cov=research_foundry`, `ruff`/`flake8`, `mypy`; frontend validation runs
**only** if files under `frontend/runs-viewer/` changed, scoped to that pnpm package.

**Adaptive phases** (`phase_strategy === 'adaptive'`): a single `agentType:'phase-owner'` runs the
whole phase. Narrow fallback only; static dispatch preferred.

### Reviewer routing (`councilEscalation`)

Driven purely by per-phase `review_intensity` (NOT plan tier):

```
council-review            ← review_intensity === 'council'
karen                     ← review_intensity === 'tier3'
task-completion-validator ← 'standard' or unset (default)
```

Opus pre-flight sets `tier3` ONLY on milestone phases (e.g. end-of-feature, security cutover); all
other phases stay `standard`. The `tier` argument is retained in `councilEscalation(p, tier)` for
compatibility but no longer affects routing.

**RF council note**: `review_intensity: 'council'` routes to the **edit-less `council-review`
agentType** directly via a `councilPhasePrompt` (diverse-lens adversarial code-tracing review),
NOT to a `review-council.js` sub-workflow. RF has no dev-phase council workflow — its council
workflow (`research-foundry-council.js`) is research-run-scoped (keyed on `run_id`, reviews a report
+ claim ledger) and is not a drop-in for a code-phase gate. The single edit-less reviewer preserves
the gate (codifying the "pair adversarial reviewer with AC validator" lesson) without nesting a
missing workflow. All reviewer agentTypes are edit-less by definition (constraint 3).

### HITL routing (human-assigned tasks)

A task whose `assigned_to` is not a registered agentType (e.g. `nick`), or which sets `hitl: true`,
is a human-in-the-loop gate. The script never passes it to `agent()`; it dispatches the phase's
*agent* tasks, runs the reviewer gate on their output, collects pending HITL tasks into
`hitl_gates`, and — after the wave's agent work + reviewer gates complete — returns
`{ status: 'needs_opus', reason: 'hitl_required', hitl_tasks: [...], report }`. This honors
constraint 2 (no mid-run human sign-off): automatable work in the wave completes, then the human
gate bubbles up to Opus, which relaunches with the HITL tasks trimmed from `args.waves`.

### Tracker agent

`agentType: 'artifact-tracker'` (`model: 'haiku'`) runs `update-batch.py` once per phase after
`taskOut` is populated. Prompt includes "Do NOT git add/commit/push/stash".

---

## ExecutionReport Output

**Canonical schema**: `.claude/specs/workflows/schemas/execution-report.schema.json`

| `status` | `reason` | Meaning |
|---|---|---|
| `complete` | — | All waves finished; all reviewer gates approved. |
| `blocked` | `mode_d` | A wave contained a Phase with `mode === 'D'`. `blocked_phase` names it. |
| `needs_opus` | `mode_d` | Implicit Mode D (files_affected heuristic) — Opus inspects before deciding. |
| `needs_opus` | `reviewer_unresolved` | Fix-loop exhausted (2 cycles) without approval. |
| `needs_opus` | `budget_exhausted` | `budget.remaining()` fell below the fix-loop guard mid-wave. |
| `needs_opus` | `hitl_required` | A human-assigned task gates the next wave. |
| `dry_run` | — | `args.dry_run === true`. Returns `{status:'dry_run', graph}` (an inspection artifact, not an ExecutionReport). |

The `report` array contains `WaveResult[]` with per-phase `tasks`, `verdict`, `fix_cycles`,
`escalate`, `files_touched`, `blockers`.

---

## Opus Pre-flight Graph-Builder Procedure (not in script)

1. **Read `wave_plan` frontmatter** (~2–3K tokens; `head -n 80` slice). Do not read the full body.
2. **Build the ExecutionGraph**: map waves → phases → tasks; compute `batches` by `files_affected`
   disjointness (sharing tasks → separate batches; disjoint → same batch); annotate `mode:'D'` on
   any phase touching auth/payments/migrations/deletion; set `tier`, `plan_ref`, `timestamp`,
   `budget_total` (`effort_estimate × ~25K`), and resolve `progressFile`
   (`.claude/progress/<resolved-dir>/phase-<N>-progress.md`).
3. **Validate before launch**: every `task.assigned_to` maps to a registered RF agent; high-risk
   phases carry `mode:'D'`; use `dry_run:true` to inspect the parsed graph first.
4. **Invoke** with the serialized graph as `args`. Record `git rev-parse HEAD` as the checkpoint.

**Post-wave** (Opus): `git merge --squash` each worktree branch; record a wave checkpoint; on
`blocked` (Mode D) run the phase interactively then relaunch with `args.waves` trimmed; on
`needs_opus`/`reviewer_unresolved` inspect `verdict.required_fixes` and adjudicate.
**Post-run** (Opus): final commit; mark the plan complete; consume any `council_artifacts`.

---

## dryRun Short-circuit

`args.dry_run === true` → `{ status: 'dry_run', graph }` immediately, before any `agent()` call.
This is the **first conditional after graph parsing** and is an inspection artifact, not an
ExecutionReport.

---

## Mode D Boundary

Mode D phases (auth, payments, migrations, data deletion, force-push, secret rotation) are **never
executed inside the workflow**. The `modeBoundary` check runs at the top of each wave loop, before
any agents spawn:

1. **Explicit flag**: `phase.mode === 'D'` → `{status:'blocked', reason:'mode_d', blocked_phase}`.
2. **Implicit heuristic**: `files_affected` matching `/auth/i`, `/payment/i`, `/billing/i`,
   `/migration/i`, `/alembic/i`, `/delete/i`, `/drop_table/i`, `/secret/i`, `/token/i` →
   `{status:'needs_opus', reason:'mode_d', blocked_phase}`.

---

## Durability Design (commit-checkpoints + per-task fallback structurer)

- **Commit-checkpoints**: every implementation prompt appends `DURABILITY_FOOTER` (commit each
  logical unit to the worktree branch before returning). `fixPrompt` and `adaptivePhasePrompt`
  append it; `reviewPrompt` and `trackerPrompt` do NOT (they are edit-less — correct).
- **Per-task fallback structurer**: each static per-task `agent(..., {schema: TASK_RESULT_SCHEMA})`
  call is wrapped in try/catch inside its `parallel()` thunk. On a schema miss, a cheap haiku
  `general-purpose` structurer runs `git log -1`/`git rev-parse HEAD` and emits a minimal
  `TASK_RESULT_SCHEMA` result so the task is not silently dropped (a `parallel()` thunk that throws
  resolves to `null`). The adaptive phase-owner path is schema-free and manually wrapped already.

---

## Self-Modification (Bootstrap) Exception

Per master contract §17: if any plan phase edits the workflow orchestrator scripts themselves
(`.claude/workflows/*.js`, especially `execute-plan.js`/`execute-contract.js`), route to the manual
wave loop, NOT this workflow — editing the running orchestrator mid-plan invalidates the resume
cache. Detection signal: any phase whose `files_affected` touches `.claude/workflows/*.js`.

---

## Four-Constraints Checklist (this workflow)

```
[x] No FS/shell access in script body
[x] Mode D phases trigger early return (blocked_phase returned), never executed
[x] All reviewer agents use edit-less agentType (task-completion-validator | karen | council-review)
[x] No Date.now() / Math.random() / new Date() in script body
[x] meta is a pure literal object
[x] phase() titles match meta.phases exactly
[x] Budget guard present in every while/loop-until-dry pattern (budget.remaining() > 60_000)
[x] Durability: DURABILITY_FOOTER appended to static task prompts, fixPrompt, adaptivePhasePrompt
[x] Durability: per-task fallback structurer in try/catch inside parallel() thunk
[x] Durability: reviewPrompt and trackerPrompt do NOT include the durability footer (edit-less)
[x] RF validation guidance (pytest under .venv; scoped frontend/runs-viewer pnpm) on impl/fix prompts
```
