---
schema_version: 2
doc_type: spec
title: "notebooklm-report Workflow Spec — NotebookLM Grounded Artifacts as Non-Authoritative RF Run Evidence"
status: active
phase: RF/NLM
created: 2026-06-13
owner: nick
related_documents:
  - .claude/specs/workflows/workflow-authoring-spec.md
  - .claude/specs/workflows/research-foundry-swarm-workflow-spec.md
  - .claude/specs/workflows/schemas/execution-report.schema.json
  - .claude/skills/notebooklm/SKILL.md
  - .claude/skills/research-foundry/SKILL.md
  - .claude/skills/dev-execution/orchestration/workflow-patterns.md
  - .claude/rules/delegation-modes.md
  - .claude/rules/context-budget.md
  - docs/projects/research-foundry/notebooklm-integration-plan.md
script: .claude/workflows/notebooklm-report.js
---

# notebooklm-report Workflow Spec

Per-workflow contract for `.claude/workflows/notebooklm-report.js`. Extends, never
contradicts, `workflow-authoring-spec.md`. Authors: read the master contract first, then
§3.2 RUNNING REPORTS of `docs/projects/research-foundry/notebooklm-integration-plan.md` and
the `notebooklm` skill at `.claude/skills/notebooklm/SKILL.md` (the source of the exact CLI
command syntax quoted into the inner-agent prompts).

---

## Purpose

`notebooklm-report` drives NotebookLM grounded artifact generation from a **synthesized** RF
run and attaches the results to the run as **NON-AUTHORITATIVE** artifacts. It implements
§3.2 ("RUNNING REPORTS") of the NotebookLM integration plan.

It sits **between `rf synthesize` (stage 7) and `rf verify` (stage 8)** of the RF run loop:
Opus invokes it once the report draft exists, before the claim-verification gate. The
workflow generates the cheap, reliable NotebookLM artifacts — briefing-doc report, mind-map,
data-table — and skips the latency/rate-limited ones (audio, video), which are deferred to
the separate `notebooklm-extended` workflow (§3.3 of the plan).

The workflow spans three phases:

1. **Prepare** — a read-only `codebase-explorer` (Mode A) confirms the synthesized run dir
   layout (`reports/report_draft.md`, `claims/claim_ledger.yaml`) exists and resolves the
   notebook id. No NLM mutation.
2. **Generate** — `parallel()` fan-out over the requested formats; each leg is a
   `python-backend-engineer` that runs exactly one `notebooklm generate ...` and captures a
   `task_id` (or, for the synchronous mind-map, a no-task-id marker). Budget-guarded;
   degrades on rate-limit/failure.
3. **Integrate** — `pipeline()` over the generated legs; each `python-backend-engineer` waits
   for the artifact (async legs), downloads it into `runs/<run_id>/nlm_artifacts/`, and
   records it in `runs/<run_id>/evidence_bundle.yaml` under `artifacts.notebooklm_report[]`.

The workflow returns a **custom shape** (not a standard `ExecutionReport`) describing the
attached artifacts and whether the bundle was updated (see Return Value below).

---

## CRITICAL Governance Rule — Non-Authoritative Artifacts

**The generated NotebookLM artifacts are NEVER spliced into `runs/<run_id>/reports/report_draft.md`.**

This is the load-bearing governance invariant of the workflow. It is enforced two ways:

1. **In the spec** (this section) — stated as the controlling contract.
2. **In the inner Integrate-agent prompt** — the agent is explicitly told it MUST NOT edit,
   append to, or touch `report_draft.md`; its edits are confined to `evidence_bundle.yaml`
   and the downloaded artifact file under `runs/<run_id>/nlm_artifacts/`.

The artifacts are recorded as evidence-bundle metadata only:

```yaml
artifacts:
  notebooklm_report:
    - type: report          # report | mind-map | data-table
      path: runs/<run_id>/nlm_artifacts/report.md
      task_id: <task_id>    # "" for the synchronous mind-map
      status: ok
      generated_at: <args.timestamp>
```

**The claim-ledger discipline is preserved**: any prose from a NotebookLM artifact that
someone later wants to cite in the report must FIRST become a source card (via `rf ingest`,
§3.1 of the plan) and earn a `[claim:<id>]`. Cheap models extract, expensive models
synthesize, and every material claim maps to a source card — the NotebookLM output is
grounded supporting evidence, not an authority that bypasses the ledger. The artifacts are
attached so a human (or a later `rf ingest` step) can decide which slices, if any, are worth
promoting to source cards — never auto-merged.

---

## `args` Contract

The script handles `args` arriving as a JSON string or object:
`const a = typeof args === 'string' ? JSON.parse(args) : (args || {})`

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `run_id` | string | **yes** | RF run identifier (e.g. `rf_run_20260613_topic`). Must correspond to a synthesized run under `runs/` (report draft + claim ledger present). |
| `notebook_id` | string | no | The NotebookLM notebook holding the run's already-uploaded sources. Full UUID preferred (parallel-safety per the notebooklm skill). **OPTIONAL** — when absent it is resolved (and created on miss) via the correlation CLI at the **start** of the Prepare phase (see *Notebook Resolution* below). Pass it to skip resolution (correlation source `explicit`). |
| `project` | string | no | Project slug scoping the correlation registry. Forwarded to `rf notebooklm resolve --project <project>` during resolution. Only consulted when `notebook_id` is absent. |
| `notebook_mode` | `'project'` \| `'run'` \| `'explicit'` | no | How the run is correlated to a notebook during resolution. Forwarded to `rf notebooklm resolve --mode <notebook_mode>`. Any other value is ignored (CLI/registry default applies). Only consulted when `notebook_id` is absent. |
| `formats` | string[] | no | Subset of `['briefing-doc','mind-map','data-table']`. Defaults to `['briefing-doc','mind-map']`. Unknown values are filtered out. |
| `data_table_desc` | string | no | The data-table description. Used **only** if `'data-table'` is in `formats`. If `'data-table'` is requested without a non-empty `data_table_desc`, that leg is skipped (`status: 'skipped_invalid'`). |
| `timestamp` | string | no | ISO 8601 timestamp set by Opus pre-flight. Used for `generated_at` in the bundle and as `result.timestamp`. **Never `Date.now()` in script.** |
| `dry_run` | boolean | no | If `true`, return `{ status: 'dry_run', parsed_args }` without spawning agents. |

**Pre-flight invariants** (Opus confirms before invoking — see Preconditions):
- `runs/<run_id>/reports/report_draft.md` exists (run is synthesized).
- `runs/<run_id>/claims/claim_ledger.yaml` exists.
- The operator has run `notebooklm login` out-of-band and the run's sources are uploaded to
  the notebook (the `notebook_id` arg, or the correlation-resolved notebook when `notebook_id`
  is omitted).

### No ExecutionGraph / waves

This workflow does NOT use the standard `ExecutionGraph.waves[]` shape. It is a research-domain
workflow with a fixed three-phase structure (mirroring `research-foundry-swarm`). The `args`
contract is the simpler `run_id` + optional `notebook_id` (+ `project` / `notebook_mode` for
resolution) + `formats` envelope above.

---

## Phases

Every `phase()` call in the script matches `meta.phases` exactly: **Prepare**, **Generate**,
**Integrate**.

| Phase title | What happens |
|---|---|
| `Prepare` | **(a) Resolve (when `notebook_id` absent):** a Bash-capable `python-backend-engineer` runs `rf notebooklm resolve --run <run_id> [--project] [--mode] --create` ONCE to resolve/create the correlated notebook. Degrades to `{ status:'blocked', reason:'notebook_unresolved' }` if NLM is unreachable — never throws. **(b) Inspect:** `codebase-explorer` (Mode A, read-only) confirms `reports/report_draft.md` and `claims/claim_ledger.yaml` exist, notes `evidence_bundle.yaml` / `nlm_artifacts/` presence, and re-confirms the (now resolved) `notebook_id` (may run read-only `notebooklm list --json`; degrades to `notebook_resolved:false` if NLM is unreachable). No NLM mutation in the inspect step. Returns a schema'd ok/missing report. If the required paths are missing the workflow returns `{ status:'blocked', reason:'run_not_synthesized' }`. |
| `Generate` | `parallel()` over the requested formats. Each leg → `python-backend-engineer` that runs **exactly one** of: `notebooklm generate report --format briefing-doc --json -n <nb>` (→ task_id), `notebooklm generate mind-map -n <nb>` (sync/instant, no task_id), or `notebooklm generate data-table "<desc>" --json -n <nb>` (→ task_id). Budget guard: `budget.remaining() < 50_000` → `status:'skipped_budget'`. Rate-limit/failure → `status:'skipped_rate_limited'`. Never fails the run. |
| `Integrate` | `pipeline()` over the legs that generated. Each → `python-backend-engineer` that runs `notebooklm artifact wait <task_id> -n <nb> --timeout 1200` (exit 0=ok, 2=timeout; skipped for the sync mind-map) then `notebooklm download <type> ./runs/<run_id>/nlm_artifacts/<type>.<ext> -a <task_id> -n <nb>`, then edits `runs/<run_id>/evidence_bundle.yaml` to append `artifacts.notebooklm_report[]`. It MUST NOT touch `report_draft.md`. Degrades on timeout / download failure. |

### Phase sequencing note

`parallel()` in Generate (a barrier — all generation kicks complete before any integration
begins, so the Integrate pipeline operates on a settled set of `task_id`s). `pipeline()` in
Integrate (no inter-item barrier — a slow briefing-doc `artifact wait` must not block the
instant mind-map download from completing and being recorded).

### Format → download-type → extension mapping

| `formats` value | generate verb | download `<type>` | ext | sync? |
|---|---|---|---|---|
| `briefing-doc` | `generate report --format briefing-doc` | `report` | `md` | no (async, task_id) |
| `mind-map` | `generate mind-map` | `mind-map` | `json` | **yes** (instant; no wait) |
| `data-table` | `generate data-table "<desc>"` | `data-table` | `csv` | no (async, task_id) |

The `briefing-doc` format maps to the `report` download type because NotebookLM's report
generator (`generate report --format briefing-doc`) downloads via `download report`. The
mind-map is synchronous per the notebooklm skill ("Mind Map — *(sync, instant)*"), so its
Integrate leg skips `artifact wait` and downloads with `-n <nb>` (no `-a <task_id>`).

### Notebook Resolution (start of Prepare, when `notebook_id` is absent)

`notebook_id` is **optional**. When it is not supplied, the workflow resolves it through the
RF correlation CLI at the **start** of the Prepare phase — before the read-only inspector runs
— via a single Bash-capable `python-backend-engineer` agent (NOT `codebase-explorer`, because
resolution may **create** the notebook):

```
rf notebooklm resolve --run <run_id> [--project <project>] [--mode <notebook_mode>] --create
```

`--create` makes resolution idempotent: it maps the run to its correlated notebook via
`registries/notebooklm/notebooks.yaml` and creates the notebook on a registry miss. The agent
returns `{ resolved, notebook_id, notebook_title, project, mode }` and **degrades** — on any
failure (NLM unauthenticated/offline, RPC error, non-zero exit) it returns
`{ resolved: false, reason }` and the workflow returns `{ status:'blocked', reason:
'notebook_unresolved' }` with a clear error; it **never throws or fails the pipeline**. When
`notebook_id` is passed explicitly, resolution is skipped and the correlation source is
recorded as `explicit`; otherwise it is `resolved:<mode>`. The resolved id then flows into the
inspector and all Generate/Integrate legs, and is surfaced as `notebook_source` in the return.

---

## Agent Routing

| agentType | Role | edit-less? | Phase | Notes |
|---|---|---|---|---|
| `python-backend-engineer` | Notebook resolver | No (`acceptEdits`) | Prepare | Runs ONCE when `notebook_id` is absent: `rf notebooklm resolve --run <run_id> [--project] [--mode] --create`. Returns the resolved id; degrades to `resolved:false` (no throw). No generation, no download, no bundle edit, no file writes. |
| `codebase-explorer` | NLM/RF preflight inspector | Yes (Mode A) | Prepare | Read-only run-dir inspection + notebook confirmation. No writes, no NLM mutation. |
| `python-backend-engineer` | NLM artifact generator | No (`acceptEdits`) | Generate | Runs one `notebooklm generate ...` via Bash, captures task_id. Writes nothing in this phase. |
| `python-backend-engineer` | NLM artifact integrator | No (`acceptEdits`) | Integrate | Runs `notebooklm artifact wait` + `download`; edits `evidence_bundle.yaml` only. Forbidden from touching `report_draft.md`. |

Mirrors the swarm convention: NLM/`rf`-driving agents are `python-backend-engineer`
(write-capable, Bash); read-only inspection is `codebase-explorer` (Mode A, edit-less).
**No reviewer agent is used** — this workflow performs no code review, so constraint 3
(edit-less reviewer `agentType`) is satisfied vacuously (there is no reviewer to inline-prompt).

Every write-capable inner prompt includes "Do NOT git add/commit/push/stash."

---

## Mode D Handling

This workflow does not use `ExecutionGraph.waves[]` and therefore does not call
`modeBoundary()`. There is no Mode D phase:

- **NLM auth is a documented PRECONDITION, not a Mode D gate.** The operator runs
  `notebooklm login` out-of-band before invocation. The script never performs or waits on
  auth, so constraint 2 ("no mid-run human sign-off") is not implicated.
- **Destructive NLM ops (`notebooklm delete` / `notebooklm notebook delete`) are FORBIDDEN**
  and never appear in any inner-agent prompt. The Generate and Integrate prompts explicitly
  instruct the agent never to run them, and never to run `notebooklm create`.

If a generation or download fails (rate-limit, timeout, auth, offline), the affected leg
degrades to a `skipped_*` status and is reported; the workflow continues with the remaining
legs and never fails the run.

---

## Dry-Run Mode

`args.dry_run === true` → return `{ status: 'dry_run', parsed_args: a }` immediately, before
any required-arg validation or agent spawn. Used by Opus pre-flight to confirm args parsing
and the early-return paths.

---

## Preconditions

- [ ] `runs/<run_id>/reports/report_draft.md` exists (run is synthesized — `rf synthesize` done).
- [ ] `runs/<run_id>/claims/claim_ledger.yaml` exists.
- [ ] The run's sources are already uploaded to NotebookLM notebook `notebook_id`.
- [ ] `notebooklm login` completed out-of-band; `notebooklm status` shows authenticated
      (the Prepare inspector degrades gracefully if not, but Generate legs will skip).
- [ ] `args.run_id` and `args.notebook_id` are set (else `{ status:'blocked', reason:'missing_args' }`).
- [ ] `args.timestamp` set by Opus pre-flight (used for `generated_at`).
- [ ] Budget sufficient: at minimum `N_formats * 50K` tokens for generation + a small Integrate margin.
- [ ] **run-in-worktree** is NOT required for this workflow. It writes only into the run's own
      `nlm_artifacts/` and `evidence_bundle.yaml`; no source-tree code is modified, so worktree
      isolation is unnecessary (unlike `execute-plan`/`execute-contract`). Per §16, the
      Integrate agent still must not `git add/commit/push/stash`.

---

## Post-conditions / Exit Gates

After the workflow returns, Opus verifies:

- [ ] `status === 'complete'` (at least one artifact attached) — or inspect a degraded status.
- [ ] For each `artifacts[]` entry with `status:'ok'`, the file exists at `path` and an entry
      exists in `evidence_bundle.yaml` under `artifacts.notebooklm_report`.
- [ ] `report_draft.md` is **unchanged** (governance invariant; spot-check `git diff` on it).
- [ ] `bundle_updated === true` when any artifact attached.

**Next step in the RF loop**: `rf verify --fail-on-unsupported`. The NotebookLM artifacts do
not participate in claim verification — they are non-authoritative evidence. Exit codes for
`rf verify` (4 = unsupported claim, 7 = council review required) are handled by Opus per the
swarm spec §7.

---

## Return Value (Custom Shape)

This workflow returns a **custom object**, not a standard `ExecutionReport`, for the same
reason as `research-foundry-swarm`: it is a research-domain workflow without waves/phases in
the `ExecutionGraph` sense, and there is no reviewer verdict / fix-loop to report. The
standard `ExecutionReport` (`status` + `report: WaveResult[]`) cannot express the
per-artifact attachment manifest this workflow produces. Documenting the divergence here
satisfies the master contract's allowance (the swarm precedent) for a custom return.

```js
{
  status: 'complete' | 'needs_opus' | 'blocked' | 'dry_run',
  run_id: string,
  notebook_id: string,                // resolved or passed
  notebook_source: string | null,     // 'explicit' | 'resolved:<mode>' | null
  timestamp: string,                  // from args.timestamp
  artifacts: Array<{
    type: 'report' | 'mind-map' | 'data-table',
    path: string | null,              // null when not downloaded (skipped/degraded)
    task_id: string | null,           // null for sync mind-map or skipped legs
    status: 'ok' | 'skipped_timeout' | 'skipped_download_failed'
          | 'skipped_rate_limited' | 'skipped_budget' | 'skipped_invalid',
  }>,
  bundle_updated: boolean,            // true if any artifact was recorded in evidence_bundle.yaml
  report: Array<{ phase, ...stats }>, // per-phase summary
}
```

| `status` | Meaning | Opus action |
|---|---|---|
| `complete` | At least one artifact downloaded + recorded in the bundle | Proceed to `rf verify` |
| `needs_opus` | Zero artifacts generated, or generated but none integrated | Inspect per-leg statuses (budget / rate-limit); rerun later |
| `blocked` | Missing required args, notebook could not be resolved (`notebook_unresolved`), prepare failed, or run not synthesized | Fix `args`, run `rf synthesize` first, or (for `notebook_unresolved`) run `notebooklm login` / pass an explicit `notebook_id` |
| `dry_run` | `args.dry_run === true` | Inspect `parsed_args`; no agents ran |

Additional fields on non-`complete` returns: `reason` (`missing_args` / `notebook_unresolved`
/ `prepare_failed` / `run_not_synthesized` / `no_artifacts_generated`), `missing` (string[] for
`missing_args`), and `error` (human-readable hint).

---

## Patterns Used

- `parallel()` — Generate phase: fan-out over requested formats (barrier; all kicks settle
  before Integrate). Budget-guarded per leg.
- `pipeline()` — Integrate phase: per-artifact wait → download → bundle-record with no
  inter-item barrier (a slow report wait does not stall the instant mind-map).
- Early `return` guards — dry-run, missing-args, prepare-failed, run-not-synthesized,
  no-artifacts-generated. All return structured objects; the script never throws.
- Budget guard — `budget.remaining() < 50_000` → `skipped_budget`, mirroring the swarm's
  ingest-pipeline budget guard.
- No `waveFanout`, `modeBoundary`, `reviewerGate`, `fixLoop`, or `councilEscalation` — not
  applicable to this workflow shape (no waves, no Mode D phase, no reviewer, no fix-loop).

---

## Governance / Claim-Ledger Notes

1. **Non-authoritative by construction.** NotebookLM output never enters `report_draft.md`.
   The artifacts are bundle-attached metadata + downloaded files under `nlm_artifacts/`.
2. **Claim ledger remains the authority.** Promotion of any NotebookLM prose to a citable
   claim requires the standard `rf ingest` → source card → `[claim:<id>]` path. This workflow
   does not bypass it; it only stages grounded supporting evidence for a later human/`rf`
   decision.
3. **Destructive ops forbidden.** No `notebooklm delete` anywhere; the inner prompts forbid it.
4. **Auth is a precondition, not a runtime gate.** No mid-run sign-off (constraint 2 satisfied).
5. **Degrade-on-failure.** Rate-limit, timeout, offline, and budget conditions degrade the
   affected leg to a `skipped_*` status; the run continues and reports the partial result.

---

## Extension Points

- **Add audio/video**: out of scope here — those long-latency, rate-limited artifacts belong
  to the separate `notebooklm-extended` workflow (§3.3) with `pipeline()` + background polling.
- **Auto-create notebook**: implemented. `notebook_id` is now OPTIONAL — when absent, the
  Prepare phase resolves (and creates on miss) the run's correlated notebook via
  `rf notebooklm resolve --run <run_id> [--project] [--mode] --create` (see *Notebook
  Resolution*). The resolve step uses a Bash-capable `python-backend-engineer` (resolution may
  create), while the subsequent inspector stays read-only. Future extension: seed the new
  notebook with the run's source set as part of resolution (§3.4 of the plan).
- **Per-format model override**: add a `task.model` channel if specific formats warrant a
  different model for the driving agent.
- **Promotion helper**: a follow-on step could offer to `rf ingest` a downloaded artifact as a
  source card (the explicit, governed path to citing its prose).

---

## Four-Constraints Checklist

```
[x] No FS/shell access in script body — all NLM/rf/file ops via inner agents (codebase-explorer, python-backend-engineer)
[x] Mode D phases trigger early return — N/A: no Mode D phase. NLM auth is an out-of-band PRECONDITION, not a runtime sign-off; destructive NLM ops forbidden in inner prompts
[x] All reviewer agents use edit-less agentType — N/A: no reviewer is used (no inline-prompted write-capable reviewer)
[x] No Date.now() / Math.random() / new Date() in script body — generated_at + result.timestamp from args.timestamp; agent labels varied by array index or fixed (nlm_report_resolve)
[x] meta is a pure literal object — no variables, no function calls, no template interpolation
[x] phase() titles match meta.phases exactly: Prepare, Generate, Integrate (resolve step runs under phase('Prepare'))
[x] Budget guard present in Generate parallel legs (budget.remaining() < 50_000 → skipped_budget)
[x] notebook_id is optional: resolved via `rf notebooklm resolve ... --create` at start of Prepare; degrades to blocked (notebook_unresolved), never throws
[x] Implementation agent prompts include "Do NOT git add/commit/push/stash"
[x] args parsed at top: const a = typeof args === 'string' ? JSON.parse(args) : (args || {})
[x] Dry-run guard immediately after parse: args.dry_run === true → { status:'dry_run', parsed_args }
[x] Required-arg validation returns { status:'blocked', reason:'missing_args', missing:[...] } (never throws); notebook_id no longer required
[x] Exact notebooklm CLI commands quoted from SKILL.md into inner prompts; degrade-on-failure instructed
[x] Custom return shape documented (rationale: research-domain, no waves/reviewer — swarm precedent)
[x] Syntax check: async-IIFE-wrapped copy passes `node --check` (exit 0) per authoring-spec §15 recipe
```
