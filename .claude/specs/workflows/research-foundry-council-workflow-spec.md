---
schema_version: 2
doc_type: spec
title: "research-foundry-council Workflow Spec — Offline Council Gate for RF Runs"
status: active
phase: 5
created: 2026-06-13
owner: nick
related_documents:
  - .claude/specs/workflows/workflow-authoring-spec.md
  - .claude/specs/workflows/review-council-workflow-spec.md
  - .claude/skills/research-foundry-swarm/SKILL.md
  - .claude/skills/research-foundry/SKILL.md
  - .claude/skills/council-review/SKILL.md
  - .claude/skills/dev-execution/orchestration/workflow-patterns.md
  - .claude/rules/delegation-modes.md
  - docs/projects/research-foundry/research-foundry-mvp-spec.md
  - docs/projects/research-foundry/SERVICE_CONTRACT.md
script: .claude/workflows/research-foundry-council.js
---

# research-foundry-council Workflow Spec

Per-workflow contract for `.claude/workflows/research-foundry-council.js`. Extends, never
contradicts, `workflow-authoring-spec.md`. Authors: read the master contract first, then the
`review-council-workflow-spec.md` for the structural analog in the code-review domain.

---

## Purpose

`research-foundry-council` is an **offline council gate** for Research Foundry runs — it does
not require an arc server or any running service. It gates the transition from a verified draft
report to a bundled evidence artifact by running four independent council reviewer agents
over the run's report and claim ledger, then adjudicating a single verdict.

The verdict is mapped to RF's `rf council` exit-code semantics:
- **Exit code 0**: approved — safe to proceed to `rf bundle`.
- **Exit code 7**: human review required — blocking or concern findings must be resolved before
  `rf bundle`. Opus must call `rf council approve <run_id>` after human resolution.

**Two trigger conditions**:

1. **`rf verify` exits 7**: the verify step determined that the report requires human council
   sign-off (e.g., sensitive claims, contested sources). The operator invokes this workflow.
2. **Operator-initiated governance gate**: any run that touches `work_approved` or
   `client_approved` data, or any run Opus flags for multi-lens review.

This workflow is **NOT a replacement for `rf verify`**. Run `rf verify --fail-on-unsupported`
first. This workflow handles the council sign-off gate that `rf verify` escalates to via exit 7.

**Relationship to `review-council`**: `review-council` is the code-review ARC wrapper;
`research-foundry-council` is the research-governance analog. They share the same parallel
reviewer fan-out pattern but apply different lenses (domain, correctness, architecture,
adversarial evaluation vs. code correctness, security, concurrency).

---

## `args` Contract

The script handles `args` arriving as a JSON string or object:
`const parsedArgs = typeof args === 'string' ? JSON.parse(args) : args`

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `run_id` | string | yes | RF run identifier. Must correspond to an initialized run under `runs/` with `reports/report_draft.md` and `claims/claim_ledger.yaml` present. |
| `timestamp` | string | yes | ISO 8601 timestamp set by Opus pre-flight. Never `Date.now()` in script. |
| `profile` | string | no | Key profile: `personal` \| `work_approved` \| `client_approved` \| `offline_only`. Defaults to `personal`. Injected into reviewer prompts for context. |
| `dry_run` | boolean | no | If `true`, return `{ status: 'dry_run', parsed_args }` without spawning agents. |

**Pre-flight invariant**: Opus confirms before invoking this workflow that:
- `runs/<run_id>/reports/report_draft.md` exists (draft produced by `rf synthesize`).
- `runs/<run_id>/claims/claim_ledger.yaml` exists (produced by `rf claim-map`).
- `rf verify` has been run (this workflow is the sign-off gate for exit code 7).

### Artifact paths (derived in script, not FS-read)

The script constructs these paths from `run_id` and passes them to agents as strings:

```
runs/<run_id>/reports/report_draft.md   — primary artifact under review
runs/<run_id>/claims/claim_ledger.yaml  — claim ledger (traceability authority)
runs/<run_id>/sources/                  — source cards (referenced by ledger)
runs/<run_id>/research_brief.md         — original research question (context for reviewers)
```

---

## Phases

Every `phase()` call below matches `meta.phases` exactly.

| Phase title | What happens |
|---|---|
| `Review` | Four parallel reviewer agents — `domain-research-reviewer`, `correctness-reviewer`, `architecture-reviewer`, `evaluator-reviewer` — each reads the report and claim ledger independently and returns `{ reviewer_role, vote, findings[], summary }`. All are edit-less. |
| `Adjudicate` | One `council-coordinator` agent (agentType: `task-completion-validator`) receives all reviewer outputs and synthesizes a single verdict (`approve` \| `concern` \| `block`) with deduped findings and required actions. Maps verdict to RF exit-code. |

---

## Agent Routing

**ALL agents in this workflow are edit-less.** This is a Mode E workflow.

| Reviewer role | agentType | Vote semantics | Focus |
|---|---|---|---|
| `domain-research-reviewer` | `senior-code-reviewer` | approve / concern / block | Source coverage, authority, domain accuracy, staleness |
| `correctness-reviewer` | `task-completion-validator` | approve / concern / block | Claim traceability, ledger completeness, label discipline, unsupported claims |
| `architecture-reviewer` | `code-reviewer` | approve / concern / block | Synthesis quality, report structure, internal consistency, scope alignment |
| `evaluator-reviewer` | `karen` | approve / concern / block | Adversarial pass: challenges key claims, surfaces overstatements and missing counter-evidence |
| `council-coordinator` (Adjudicate) | `task-completion-validator` | — | Synthesizes, deduplicates, assigns final verdict; maps to RF exit code |

**Why these agentTypes?**

- `senior-code-reviewer`: adversarial depth appropriate for domain accuracy assessment.
- `task-completion-validator`: systematic checklist approach appropriate for traceability and ledger correctness.
- `code-reviewer`: structural and consistency review appropriate for report architecture.
- `karen`: adversarial reviewer — purpose-built for challenging claims and surfacing weaknesses.

All four have `disallowedTools` preventing Write/Edit/MultiEdit in their agent definitions.
The workflow cannot enforce read-only at the script level; it is enforced by agent definition (constraint 3).

---

## Verdict Adjudication Rules

The council-coordinator applies these rules to synthesize the verdict:

| Condition | Verdict | RF exit code |
|---|---|---|
| Any reviewer votes "block" | block | 7 |
| Two or more reviewers vote "concern", no "block" | concern | 7 |
| All vote "approve", or at most one "concern" with no substantial findings | approve | 0 |

Vote overrides: if a "block" vote is clearly erroneous (reviewer misread the scope), the
coordinator may downgrade to "concern" with explicit rationale. This is the only override allowed.

Dissent is always recorded: if a voter's verdict is overridden, the rationale field explains why.

---

## RF Exit-Code Mapping

```
council_verdict: "approve" → rf_exit_code: 0  → council_status: "approved"
council_verdict: "concern" → rf_exit_code: 7  → council_status: "needs_review"
council_verdict: "block"   → rf_exit_code: 7  → council_status: "needs_review"
```

Both "concern" and "block" verdicts map to RF exit code 7 ("human review required").
The distinction matters for Opus post-run:

- **"concern"**: operator reviews concern findings, confirms they are addressed or acceptable,
  then runs `rf council approve <run_id>`.
- **"block"**: operator must resolve all `blocking_findings[].recommendation` actions before
  approving. This may require re-running `rf synthesize` or adding source cards.

---

## Mode D Handling

Not applicable. This is a Mode E (review-only) workflow with no implementation agents. No phase
executes writes to source files. The only data written is the agent return values (structured
objects in memory), not files on disk.

The agentType definitions carry `disallowedTools` blocking file writes; this is the enforcement
mechanism, not a `modeBoundary()` call.

---

## Dry-Run Mode

`args.dry_run === true` → return `{ status: 'dry_run', parsed_args: parsedArgs }` immediately.
No agents spawn. Used by Opus pre-flight to confirm args are valid before committing to a
full council run.

---

## Pre-conditions

- [ ] `runs/<run_id>/reports/report_draft.md` exists (produced by `rf synthesize`).
- [ ] `runs/<run_id>/claims/claim_ledger.yaml` exists (produced by `rf claim-map`).
- [ ] `rf verify --fail-on-unsupported` has been run (this workflow is the exit-7 escalation gate).
- [ ] `args.run_id` matches an existing initialized RF run.
- [ ] `args.timestamp` is set by Opus pre-flight (ISO 8601 string).
- [ ] Budget is sufficient: minimum `5 * ~25K = 125K` tokens (4 reviewers + 1 adjudicator).

---

## Post-conditions / Exit Gates

After the workflow returns, Opus verifies:

- [ ] `status === 'complete'` and `verdict.rf_exit_code === 0` before proceeding to `rf bundle`.
- [ ] If `verdict.rf_exit_code === 7`: review `verdict.blocking_findings` and `verdict.concern_findings`.
- [ ] If "block": all `verdict.required_actions` addressed before re-running verify + council.
- [ ] If "concern": operator confirms concerns are acceptable or addressed, then runs `rf council approve <run_id>`.
- [ ] At least 3 of 4 reviewers returned output (`report[0].reviewers_returned >= 3`).

**Follow-on commands**:

```bash
# On approve (rf_exit_code === 0):
rf bundle <run_id> --verify --out evidence_bundle.yaml
rf writeback <run_id> --targets meatywiki,skillmeat,ccdash --require-review

# On block/concern (rf_exit_code === 7):
# 1. Address required_actions from verdict
# 2. Re-run relevant rf commands (e.g., rf synthesize if report needs revision)
# 3. Re-run rf verify
# 4. Re-invoke this workflow OR run: rf council approve <run_id> after human confirmation
```

---

## Return Value

```js
{
  status: 'complete' | 'needs_opus' | 'blocked' | 'dry_run',
  run_id: string,
  timestamp: string,
  verdict: {
    council_verdict: 'approve' | 'concern' | 'block' | 'unknown',
    rf_exit_code: 0 | 7,
    council_status: 'approved' | 'needs_review',
    rationale: string,
    blocking_findings: FindingRef[],       // from block-voting reviewers
    concern_findings: FindingRef[],        // from concern-voting reviewers
    required_actions: string[],            // must resolve before bundling (block/concern)
    recommended_actions: string[],         // nice-to-have (any verdict)
    vote_summary: { approve: N, concern: N, block: N },
    reviewer_outputs: ReviewerOutput[],    // full outputs from all reviewers
    rf_council_commands: string[],         // ordered commands for Opus/operator
  },
  report: [
    { phase: 'Review', reviewers_dispatched: 4, reviewers_returned: N, votes: {...} },
    { phase: 'Adjudicate', verdict, blocking_count, concern_count, rf_exit_code },
  ],
}
```

| `status` | Meaning | Opus action |
|---|---|---|
| `complete` | rf_exit_code === 0; council approved | Proceed to `rf bundle` |
| `needs_opus` | rf_exit_code === 7; or reviewers failed | Review verdict; address findings; re-run or escalate |
| `blocked` | `run_id` missing | Fix `args.run_id` |
| `dry_run` | `args.dry_run === true` | Inspect `parsed_args`; no agents ran |

---

## Relationship to `review-council`

`research-foundry-council` and `review-council` are parallel governance workflows for different
domains:

| Dimension | `review-council` | `research-foundry-council` |
|---|---|---|
| Domain | Code quality & correctness | Research evidence quality |
| Primary artifacts | Git diff, code files | Report draft, claim ledger |
| Reviewer lenses | correctness, security, concurrency, performance, contract | domain-accuracy, claim-traceability, report-architecture, adversarial-evaluation |
| Output | ARC artifact set (6 files) | Council verdict + RF exit code |
| Nesting | Embedded in `execute-plan` as `review_intensity: council` | Standalone gate between `rf verify` and `rf bundle` |

Do NOT nest `research-foundry-council` inside `review-council` or `execute-plan`. It is always
invoked standalone.

---

## Patterns Used

- `parallel()` fan-out — four reviewers run concurrently in Phase 1 (Review); barrier ensures
  all results arrive before adjudication begins.
- No `pipeline()`, `waveFanout`, `modeBoundary`, `reviewerGate`, or `fixLoop` — not applicable
  to this two-phase review workflow shape.

---

## Extension Points

- **Add a fifth reviewer**: add a new thunk to `reviewerThunks` in Phase 1. Update `reviewers_dispatched` in the report. No other changes needed.
- **Add a source-integrity reviewer**: add a reviewer that cross-checks that every source_card path in the claim ledger actually exists in `runs/<run_id>/sources/` (useful for large runs).
- **Structured ARC artifacts**: add a Phase 3 agent (agentType: `task-completion-validator`) that writes the council verdict to `runs/<run_id>/council/verdict.yaml` for audit trail. Currently the verdict lives only in the return object.
- **Re-review after fix**: add a `rerun_after_fix: boolean` arg that skips Phase 1 for reviewers who voted "approve" and only re-runs the "block"/"concern" voters. Reduces cost on revision runs.

---

## Four-Constraints Checklist

```
[x] No FS/shell access in script body — no import fs, no exec, no shell
[x] Mode D phases trigger early return — N/A (Mode E workflow; no implementation phases)
[x] All reviewer agents use edit-less agentType — senior-code-reviewer, task-completion-validator,
    code-reviewer, karen — all carry disallowedTools in their definitions
[x] No Date.now() / Math.random() / new Date() in script body — timestamp from args
[x] meta is a pure literal object
[x] phase() titles match meta.phases exactly: Review, Adjudicate
[x] Budget guard — not required in this workflow (no while loops or loop-until-dry patterns);
    parallel() barriers and pipeline() have implicit N-agent cost bounded by candidateCount
[x] Implementation agent prompts include "Do NOT git add/commit/push/stash" (all reviewer prompts)
[x] args.dry_run handled (return { status: 'dry_run', parsed_args })
[x] args parsed at top (typeof args === 'string' ? JSON.parse : identity)
```
