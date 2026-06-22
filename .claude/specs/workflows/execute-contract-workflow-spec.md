---
schema_version: 2
doc_type: spec
title: "execute-contract Workflow Spec (Research Foundry)"
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
workflow_script: .claude/workflows/execute-contract.js
registry_entry: .claude/specs/workflows/workflow-registry.md
command: .claude/commands/dev/execute-contract.md
---

# execute-contract Workflow Spec (Research Foundry)

Per-workflow contract for `.claude/workflows/execute-contract.js`. Extends, never contradicts,
`workflow-authoring-spec.md` (the master contract). Read the master contract first.

---

## §1 — Purpose and Trigger

`execute-contract` is the **Tier 1 sprint workflow**. It replaces the manual
`feature-sprint-executor` + `task-completion-validator` Task-pair, making Tier 1 sprints
**resumable, inspectable via `/workflows`, and deterministically gated**.

**When to use**:
- A Feature Contract (`doc_type: feature_contract`) exists and has `status: approved`.
- Estimated effort is 3–8 story points (Tier 1 range).
- The contract does **not** touch auth, payments, production migrations, data deletion, or secret
  rotation — those are Mode D; use `execute-plan` with Mode D boundary detection or invoke
  interactively.

**Invocation**: `workflow execute-contract` with a JSON `args` envelope (see §2), or via the
`/dev:execute-contract` saved command.

**Do not use for**:
- Tier 0 tasks (use `/dev:quick-feature` directly).
- Tier 2/3 plans with multiple phases and waves (use `execute-plan`).
- Contracts flagged Mode D in their metadata (workflow returns `needs_opus` immediately).

---

## §2 — `args` Envelope (Feature Contract Envelope)

`execute-contract` uses a simplified subset of the full `ExecutionGraph` schema. Opus builds this
pre-flight from the contract file and passes it as the workflow `args`. The workflow script
**never reads the contract file itself** (constraint 1 — no FS access from script).

```json
{
  "contract_path":  "string — relative path from RF repo root to the Feature Contract .md",
  "plan_ref":       "string — same as contract_path (aliases execution-graph convention)",
  "tier":           1,
  "timestamp":      "string — ISO 8601 set by Opus pre-flight; never Date.now() in script",
  "budget_total":   50000,
  "context_paths":  ["string — optional list of relevant file paths for agent context"],
  "fix_agent":      "string — optional agentType override for fix-loop; default 'feature-sprint-executor'",
  "review_intensity": "standard | tier3 | council — default 'standard'",
  "dry_run":        false,

  "contract_metadata": {
    "slug":           "string — e.g. 'source-health-polling'",
    "mode":           "string — delegation mode from contract; 'D' triggers needs_opus",
    "files_affected": ["string — relative paths the contract expects to touch"],
    "effort_points":  3
  }
}
```

**Field notes**:

| Field | Required | Notes |
|---|---|---|
| `contract_path` | yes | Path to the Feature Contract `.md` (usually under `docs/project_plans/feature_contracts/`). Agents read this file; the script does not. |
| `tier` | yes | Always `1` for this workflow. |
| `timestamp` | yes | ISO 8601 string from Opus. Never call `Date.now()` inside the script. |
| `budget_total` | no | Default `50000`. Derived from `effort_points × 6250`. Opus sets this based on contract effort. |
| `context_paths` | no | Additional codebase paths the sprint agent should read. Passed verbatim into the sprint prompt. |
| `fix_agent` | no | Override `agentType` for fix-loop agents. Defaults to `'feature-sprint-executor'`. |
| `review_intensity` | no | Reviewer routing (see §5). Default `'standard'` → `task-completion-validator`. |
| `dry_run` | no | When `true`, returns the parsed `args` envelope without spawning agents. |
| `contract_metadata.mode` | no | If `'D'`, the workflow returns `{status:'needs_opus', reason:'mode_d'}` before spawning the sprint. Also checked via `files_affected` heuristic (§4). |
| `contract_metadata.files_affected` | no | Paths the contract expects to touch. Used for implicit Mode D detection. |
| `provider_routing_enabled` | no | DEFAULT FALSE. When true, AC validation routes to the codex-executor two-stage pattern (P3) and `fix_provider:'bob'` routes the fix-cycle to bob-delegate-executor (P4). These offload agentTypes are NOT in RF's default roster — leave the flag off for the standard RF path. |

---

## §3 — Phases

Three named phases, matching the `meta.phases` array in `execute-contract.js` exactly:

```
1. Sprint        — feature-sprint-executor autonomous implementation
2. Review        — task-completion-validator (or tier3/council) reviewer gate
3. Fix cycle N   — feature-sprint-executor (or fix_agent) targeted fix (≤2 cycles)
```

### Phase 1: Sprint

**Agent**: `agentType: 'feature-sprint-executor'`, Mode C, `acceptEdits`.

The sprint runs explore → implement → test → validate → Completion Report autonomously. The agent
commits each logical unit to its worktree branch (commit-as-you-go — constraint 4) and writes a
Completion Report to a deterministic path before returning. See §11 for the two-stage durability
design.

**RF validation**: the sprint prompt instructs the agent to run, for the scope it changed:
`./.venv/bin/python -m pytest` (NOT the pyenv `python` shim — it fails with "No module named
research_foundry"), `--cov=research_foundry` for coverage, `ruff`/`flake8` lint, `mypy` type-check.
Frontend validation runs **only** if files under `frontend/runs-viewer/` changed, and is scoped to
that pnpm package (`pnpm --dir frontend/runs-viewer test / build / exec tsc --noEmit`).

### Phase 2: Review

**Agent**: `agentType: 'task-completion-validator'` (or `'karen'` / `'council-review'` per
`review_intensity`), Mode E, edit-less by agent definition. The reviewer reads the diff, the
Completion Report, and the contract AC list, then returns `{approved, reviewer_type, required_fixes?}`.

### Phase 3: Fix Cycle N (≤2 cycles)

**Agent**: `agentType: fix_agent` (default `'feature-sprint-executor'`), Mode C.
**Budget guard**: `budget.remaining() > 60_000`. After each fix cycle the reviewer re-runs against
the post-fix HEAD. After 2 failed cycles → `{status:'needs_opus', reason:'reviewer_unresolved'}`.

---

## §4 — Mode D Boundary (Contract Metadata Check)

Per master contract §7 (constraint 2: no mid-run sign-off), the workflow detects Mode D and returns
early **before spawning any agents**:

- **Explicit flag**: `args.contract_metadata.mode === 'D'`.
- **Implicit heuristic**: any `files_affected` path matching auth / payments / billing / migrations /
  alembic / delete / drop_table / secret / token.

Either path → `{ status: 'needs_opus', reason: 'mode_d', blocked_phase: 'sprint', report: [] }`.
The sprint agent is never spawned. Opus runs the work interactively under Mode D discipline.

---

## §5 — Reviewer Routing

| `review_intensity` | Reviewer agentType |
|---|---|
| `standard` (default) | `task-completion-validator` |
| `tier3` | `karen` |
| `council` | `council-review` |

**RF council note**: `review_intensity: 'council'` routes to the **edit-less `council-review`
agentType** (in RF's roster), NOT to a `review-council.js` sub-workflow. RF has no dev-phase
council workflow — its council workflow (`research-foundry-council.js`) is research-run-scoped
(keyed on `run_id`) and reviews a report + claim ledger, so it is not a drop-in for a code-phase
gate. The single edit-less `council-review` agent preserves the diverse-lens / adversarial gate.
All reviewer agentTypes are edit-less by definition (constraint 3).

---

## §6 — Output Schemas

`SPRINT_RESULT_SCHEMA` and `VERDICT_SCHEMA` are inline `schema` options passed to `agent()` (the
script cannot read schema files — constraint 1). `VERDICT_SCHEMA.reviewer_type` enumerates the
edit-less reviewer set; the `council_artifacts` object carries ARC artifact paths when a council
gate runs. Both mirror the `ReviewerVerdict` shape in `execution-report.schema.json`.

---

## §7 — ExecutionReport Return Value

Conforms to `execution-report.schema.json`. The `report` array contains a single `WaveResult`
with a single `PhaseResult` (the sprint phase), so Opus post-processes it identically whether the
work ran via `execute-plan` or `execute-contract`.

| Status | When | Opus action |
|---|---|---|
| `complete` | Sprint done + reviewer approved (≤2 fix cycles) | Commit/merge worktree; update contract frontmatter (`status: completed`, `commit_refs`) |
| `needs_opus` (`mode_d`) | Contract is Mode D | Run sprint interactively |
| `needs_opus` (`reviewer_unresolved`) | Fix-loop exhausted, reviewer still disapproves | Opus adjudicates or re-scopes |
| `needs_opus` (`budget_exhausted`) | Fix-loop hit the budget floor before 2 cycles | Opus decides whether to continue with fresh budget |

---

## §8 — Opus Post-Run Responsibilities

On `status: 'complete'`, Opus (not the script — constraint 1): reads the sprint commit SHA from
`report[0].phases[0].tasks[0].commit_sha`; merges the worktree branch (`git merge --squash`); runs
final validation (`./.venv/bin/python -m pytest` + `ruff`/`mypy`; scoped `pnpm` only if
`frontend/runs-viewer` changed); updates contract frontmatter; updates any progress file via
`update-batch.py`.

---

## §9 — Budget Convention

`budget_total` defaults to `50000` tokens, derived from `effort_points × 6250` (8 pts → 50K, 4 pts
→ 25K). **Fix-loop guard**: `budget.remaining() > 60_000` — a runaway guard, not a quality dial; do
not lower it. For 8-pt contracts expected to generate large diffs, set `budget_total: 80000`.

---

## §10 — Extension Points

1. **`fix_agent` override** — pass a domain expert (e.g. `python-backend-engineer`) for targeted fixes.
2. **`review_intensity: 'council'`** — escalate to the `council-review` reviewer for cross-domain work.
3. **`context_paths`** — inject narrow extra context for the sprint agent.
4. **Budget scaling** — `budget_total: 80000` for 8-pt contracts; `25000` for 3-pt.
5. **Sub-workflow nesting** — a future RF workflow could invoke `execute-contract` (one level only).
6. **Sub-task sharding** (`subtask_sharding_enabled: true`, DEFAULT FALSE) — lets the on-primary
   sprint executor shard bounded mechanical sub-tasks (test-writer, doc-updater, fixture-builder) to
   depth-1 helpers (single-committer; helpers never commit). Mitigates the
   *execute-contract-blows-context-on-large-files* failure mode. With the flag off, `sprintPrompt`
   is byte-for-byte identical to the non-pilot behaviour.

---

## §11 — Durability Design (two-stage sprint)

The Sprint phase runs two sequential stages inside one `phase('Sprint')` group (master contract §16):

- **Stage A — `feature-sprint-executor` (no schema)**: runs the full sprint, commits checkpoints,
  writes the Completion Report to `reportPathForContract(parsed)` BEFORE returning a plain-text summary.
- **Stage B — `general-purpose` haiku (schema: SPRINT_RESULT_SCHEMA)**: reads the report from disk,
  runs `git log`/`git diff --name-only`/`git rev-parse HEAD` to fill `commit_sha`/`files_touched`,
  parses the AC Status section. Wrapped in try/catch → minimal fallback result on failure.

A terminal StructuredOutput miss in Stage B never discards Stage A's committed work.
`reportPathForContract` is a pure string function (no FS): returns `parsed.completion_report_path`
if set, else `.claude/worknotes/<slug>/completion-report.md` from the contract filename.

---

## §12 — Four-Constraints Checklist (this workflow)

```
[x] No FS/shell access in script body
    — args envelope passed by Opus; no readFile/exec/import fs in execute-contract.js
[x] Mode D phases trigger early return, never executed
    — contract_metadata.mode === 'D' OR files_affected heuristic → needs_opus before sprint spawns
[x] All reviewer agents use edit-less agentType
    — task-completion-validator / karen / council-review (all edit-less by definition)
[x] No Date.now() / Math.random() / new Date() in script body
    — timestamp via args.timestamp; deterministic AC-validation artifact path from args
[x] meta is a pure literal object (no computed values, no function calls)
[x] phase() titles match meta.phases exactly: 'Sprint', 'Review', 'Fix cycle 1', 'Fix cycle 2'
[x] Budget guard present in fix-loop: budget.remaining() > 60_000
[x] Durability: sprint (Stage A) has no schema; commits checkpoints; writes report to disk
[x] Durability: structure stage (Stage B) wrapped in try/catch with fallback result
[x] Durability: fix agent prompt includes the commit-to-worktree instruction (no push/merge/stash)
[x] All implementation/fix prompts carry RF validation guidance (pytest under .venv; scoped pnpm)
[x] reportPathForContract is pure string — no FS access
[x] args parsed at top; args.dry_run handled (return envelope without spawning agents)
```
