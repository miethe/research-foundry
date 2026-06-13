---
schema_version: 2
doc_type: spec
title: "research-foundry-swarm Workflow Spec — Path B Claude Code-Orchestrated Discovery Swarm"
status: active
phase: 5
created: 2026-06-13
owner: nick
related_documents:
  - .claude/specs/workflows/workflow-authoring-spec.md
  - .claude/skills/research-foundry-swarm/SKILL.md
  - .claude/skills/research-foundry/SKILL.md
  - .claude/skills/dev-execution/orchestration/workflow-patterns.md
  - .claude/rules/delegation-modes.md
  - .claude/rules/context-budget.md
  - docs/projects/research-foundry/research-foundry-mvp-spec.md
  - docs/projects/research-foundry/SERVICE_CONTRACT.md
script: .claude/workflows/research-foundry-swarm.js
---

# research-foundry-swarm Workflow Spec

Per-workflow contract for `.claude/workflows/research-foundry-swarm.js`. Extends, never
contradicts, `workflow-authoring-spec.md`. Authors: read the master contract first, then the
`research-foundry-swarm` skill at `.claude/skills/research-foundry-swarm/SKILL.md`.

---

## Purpose

`research-foundry-swarm` implements **Path B** of the RF swarm pattern: Claude Code agent
subagents perform source discovery, feeding results into a Research Foundry run via `rf ingest`.
RF remains the governance and evidence spine; the agent swarm is disposable discovery muscle.

The workflow spans four phases:

1. **Plan** — A discovery-lead agent reads `runs/<run_id>/research_brief.md` and produces a
   structured `DiscoveryStrategy` that maps the research question into parallel discovery legs.
2. **Discover** — Parallel domain-researcher and source-scout agents run one leg each, returning
   structured source candidates with provenance.
3. **Dedup** — Pure JS merge and deduplication of candidates (no agent, no FS, no shell).
4. **Ingest** — Pipeline-style ingest: each accepted candidate is governance-gated via
   `rf guard check` then written as a source card via `rf ingest`.

The workflow returns a **source manifest** of ingested source card paths, not a completed report.
The deterministic tail (extract → claim-map → synthesize → verify → bundle) is a **post-run
step** executed by Opus or the operator after reviewing the manifest (see §7).

Replaces: the manual `rf swarm run` + manual `rf ingest` loop described in the `research-foundry-swarm` skill §2 Path B.

Fallback: manual Path B per the skill remains available until this workflow is piloted and validated.

---

## `args` Contract

The script handles `args` arriving as a JSON string or object:
`const parsedArgs = typeof args === 'string' ? JSON.parse(args) : args`

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `run_id` | string | yes | RF run identifier (e.g. `rf_run_20260613_topic`). Must correspond to an initialized run under `runs/`. |
| `profile` | string | no | Key profile: `personal` \| `work_approved` \| `client_approved` \| `offline_only`. Defaults to `personal`. |
| `timestamp` | string | yes | ISO 8601 timestamp set by Opus pre-flight. Never `Date.now()` in script. |
| `budget_total` | integer | no | Maps to `budget.total`. |
| `dry_run` | boolean | no | If `true`, return `{ status: 'dry_run', parsed_args }` without spawning agents. |

**Pre-flight invariant**: Opus confirms before invoking this workflow that:
- `runs/<run_id>/research_brief.md` exists and is non-empty.
- `rf doctor` is green for the workspace.
- `rf guard check --profile <profile>` exits 0.

### No ExecutionGraph / waves

This workflow does NOT use the standard `ExecutionGraph.waves[]` shape. It is a
research-domain workflow with its own fixed phase structure. The `args` contract is
simpler: `run_id` + `profile` + `timestamp`.

---

## Phases

Every `phase()` call below matches `meta.phases` exactly.

| Phase title | What happens |
|---|---|
| `Plan` | `codebase-explorer` agent reads `research_brief.md` → returns `DiscoveryStrategy` (research_question, key_topics, domain_legs, sensitivity, max_sources). |
| `Discover` | `parallel()` fan-out: one agent per `domain_leg` alternating `domain_researcher` / `source_scout` personas, both `codebase-explorer` agentType. Returns `SourceCandidates` per leg. |
| `Dedup` | Pure JS: merge all leg candidates, dedup by normalized URL/path, trim to `max_sources`. No agent. |
| `Ingest` | `pipeline()` over accepted candidates: each triggers `rf guard check` then `rf ingest` via `python-backend-engineer` agent. Returns ingest result per candidate. |

### Phase sequencing note

`parallel()` is used in Discover (all legs run concurrently; all must complete before Dedup).
`pipeline()` is used in Ingest (candidates are independent; no inter-item barrier needed;
a failing ingest for one source does not block others).

---

## Agent Routing

| agentType | Role | edit-less? | Phase | Notes |
|---|---|---|---|---|
| `codebase-explorer` | Discovery lead (Plan) | Yes (Mode A) | Plan | Reads research brief; returns DiscoveryStrategy. No writes. |
| `codebase-explorer` | Domain researcher / source scout | Yes (Mode A) | Discover | Alternates persona by leg index (even=researcher, odd=scout). Uses web search tools. Returns candidates. |
| `python-backend-engineer` | RF ingest runner | No (acceptEdits) | Ingest | Runs `rf guard check` and `rf ingest` via Bash. Writes source cards to `runs/<run_id>/sources/`. |

**Important**: `python-backend-engineer` is the only write-capable agent. Its writes are
constrained to `runs/<run_id>/sources/` by explicit prompt instruction. The agent is told
explicitly: "Do NOT run rf extract, rf claim-map, rf synthesize, rf verify, rf bundle, or
rf writeback." and "Do NOT git add/commit/push/stash."

---

## Mode D Handling

This workflow does not use the standard `ExecutionGraph.waves[]` and therefore does not call
`modeBoundary()`. Mode D detection is not applicable: no phase touches auth, payments, or
schema migrations. The closest analog is the governance preflight (`rf guard check`) which is
run by the Ingest agent before every `rf ingest` call.

If `rf guard check` exits non-zero for any source, that ingest is marked `{ success: false }`
and included in `manifest.failed_sources`. The workflow continues with remaining candidates.

---

## Dry-Run Mode

`args.dry_run === true` → return `{ status: 'dry_run', parsed_args: parsedArgs }` immediately
without spawning any agents. Used by Opus pre-flight to confirm args parsing and early-return
paths before committing to a full discovery run.

---

## Pre-conditions

- [ ] `runs/<run_id>/research_brief.md` exists and is non-empty.
- [ ] RF workspace is initialized (`rf init` complete, `rf doctor` green).
- [ ] `rf guard check --profile <profile>` exits 0 before workflow invocation.
- [ ] `args.run_id` is a valid run identifier matching an existing `runs/` directory.
- [ ] `args.timestamp` is set by Opus pre-flight (ISO 8601 string).
- [ ] Budget is sufficient: at minimum `(2 * N_legs + N_candidates + 1) * ~25K` tokens.

---

## Post-conditions / Exit Gates

After the workflow returns, Opus verifies:

- [ ] `status === 'complete'` (at least one source ingested successfully).
- [ ] `manifest.ingested_count > 0` — at least one source card was created.
- [ ] `manifest.failed_sources` is reviewed; failures should be investigated if > 20% of candidates.
- [ ] Source cards exist on disk at the paths listed in `manifest.source_cards[].path`.

**Post-run steps (NOT run by this workflow — run by Opus/operator after reviewing manifest)**:

```bash
rf extract <run_id> --model-profile rf_extract_cheap
rf claim-map <run_id> --from extractions --out claims/claim_ledger.yaml
rf synthesize <run_id> --report reports/report_draft.md --model-profile rf_synthesize_deep
rf verify <run_id> --report reports/report_draft.md --claim-ledger claims/claim_ledger.yaml --fail-on-unsupported
# If rf verify exits 7: invoke research-foundry-council workflow
rf bundle <run_id> --verify --out evidence_bundle.yaml
rf writeback <run_id> --targets meatywiki,skillmeat,ccdash --require-review
```

The `post_run_commands` array in the returned object lists these commands for operator convenience.

---

## Return Value

This workflow returns a custom object (not a standard `ExecutionReport`) because it is a
research-domain workflow without waves.

```js
{
  status: 'complete' | 'needs_opus' | 'blocked' | 'dry_run',
  run_id: string,
  profile: string,
  timestamp: string,
  manifest: {
    ingested_count: number,
    failed_count: number,
    skipped_count: number,
    source_cards: Array<{ path, url_or_path, title, source_type }>,
    failed_sources: Array<{ url_or_path, title, step, exit_code, error }>,
  },
  strategy: DiscoveryStrategy,       // from Phase 1
  post_run_commands: string[],       // ordered deterministic tail commands
  report: Array<{ phase, ...stats }>,
}
```

| `status` | Meaning | Opus action |
|---|---|---|
| `complete` | At least one source ingested | Run deterministic tail per `post_run_commands` |
| `needs_opus` | Zero sources ingested, or all reviewers failed | Inspect `error`, fix root cause, rerun |
| `blocked` | `run_id` missing or plan agent returned null | Fix `args` or create `research_brief.md` |
| `dry_run` | `args.dry_run === true` | Inspect `parsed_args`, no agents ran |

---

## §7 — Deterministic Tail (post-run operator note)

The deterministic tail is intentionally out of scope for this workflow because:

1. `rf verify --fail-on-unsupported` exits 4 on unsupported claims — requires human review.
2. `rf bundle` and `rf writeback` have governance implications requiring operator sign-off.
3. `rf council` (exit code 7) requires running `research-foundry-council` as a separate gate.

The tail commands are returned in `post_run_commands` for convenience. Opus runs them after
reviewing the manifest. If `rf verify` exits 7, invoke the `research-foundry-council` workflow
before proceeding to `rf bundle`.

Exit codes to know:
| Code | Meaning | Action |
|------|---------|--------|
| 0 | Pass | Continue |
| 4 | Unsupported material claim | Label claim or add source card, re-run verify |
| 7 | Human review required | Invoke `research-foundry-council` workflow |

---

## Patterns Used

- `exploreLegs` shape — `parallel()` fan-out over discovery legs (Discover phase)
- `pipeline()` — per-candidate ingest with no inter-item barrier (Ingest phase)
- No `waveFanout`, `modeBoundary`, `reviewerGate`, or `fixLoop` — not applicable to this workflow shape

---

## Extension Points

- **Add more legs**: increase `max_sources` in args; the Plan agent will generate more domain legs.
- **Custom persona per leg**: extend the `isResearcher` alternation logic to support a `leg.persona` field from `DiscoveryStrategy`.
- **Parallel ingest**: change `pipeline()` to `parallel()` in Ingest if ordering is unimportant and budget allows.
- **Additional ingest validators**: add a post-ingest agent step in the pipeline to validate the source card schema.

---

## Four-Constraints Checklist

```
[x] No FS/shell access in script body — all file ops via python-backend-engineer agent
[x] Mode D phases trigger early return — N/A (no Mode D phases; guard handled at agent level)
[x] All reviewer agents use edit-less agentType — codebase-explorer (Mode A) for Plan/Discover
[x] No Date.now() / Math.random() / new Date() in script body — timestamp from args
[x] meta is a pure literal object
[x] phase() titles match meta.phases exactly: Plan, Discover, Dedup, Ingest
[x] Budget guard present in Ingest pipeline (budget.remaining() < 60_000 check)
[x] Implementation agent prompts include "Do NOT git add/commit/push/stash"
[x] args.dry_run handled (return { status: 'dry_run', parsed_args })
[x] args parsed at top (typeof args === 'string' ? JSON.parse : identity)
```
