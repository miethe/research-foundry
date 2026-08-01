---
type: progress
schema_version: 2
doc_type: progress
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
phase: 1
status: completed
created: '2026-07-28'
updated: '2026-07-29'
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
commit_refs:
- 41bcafb
- f1bfa39
- f16059f
- e4c76b9
- d43a1ff
- fce17e1
pr_refs:
- '7'
owners:
- backend-architect
contributors:
- api-designer
- python-backend-engineer
- task-completion-validator
- karen
tasks:
- id: OPM-1.1
  status: completed
  assigned_to:
  - api-designer
  dependencies:
  - RPC-1.G
  - KMCP-1.G
  estimate: 1 pt
- id: OPM-1.2
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - OPM-1.1
  estimate: 1 pt
- id: OPM-1.3
  status: completed
  assigned_to:
  - backend-architect
  - python-backend-engineer
  dependencies:
  - OPM-1.2
  estimate: 1 pt
- id: OPM-1.4
  status: completed
  assigned_to:
  - api-designer
  dependencies:
  - OPM-1.1
  estimate: 1 pt
- id: OPM-1.G
  status: pending
  assigned_to:
  - task-completion-validator
  - karen
  dependencies:
  - OPM-1.2
  - OPM-1.3
  - OPM-1.4
  estimate: gate
parallelization:
  batch_1:
  - OPM-1.1
  batch_2:
  - OPM-1.2
  - OPM-1.4
  batch_3:
  - OPM-1.3
  batch_4:
  - OPM-1.G
total_tasks: 5
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 80
---

# Phase 1 Progress — Contract, Identity, and Confirmation

**Dependencies**: Research Provenance Continuity `RPC-1.G` and Knowledge MCP `KMCP-1.G` approved exact-tree contracts.
**Integration owner**: backend-architect.
**Exit state**: effect writers have stable schemas, trusted identity inputs, policy order, confirmation semantics, limits, and safe errors.

| Task ID | Task | Acceptance criteria | Estimate |
|---|---|---|---:|
| OPM-1.1 | Operation and tool contract | Positive/negative fixtures validate; unknown/wildcard operations reject | 1 pt |
| OPM-1.2 | Identity and sensitivity contract | Missing/wrong identity and two-workspace fixtures return one safe denial | 1 pt |
| OPM-1.3 | Guard/preflight and confirmation | Expired/replayed/mismatched token matrix produces zero manifest/effects | 1 pt |
| OPM-1.4 | Receipt and bounded-error schemas | Golden/negative schemas reject unbounded/raw exception and unauthorized fields | 1 pt |
| OPM-1.G | Tier-3 contract gate | task-completion-validator then Karen APPROVE the same exact tree; material changes invalidate both verdicts | gate |

Quality gate (per plan): OPM-OQ-1..4 resolved or defaults explicitly approved; security reviewer verifies authorization-before-lookup and token binding; `task-completion-validator` then Karen approve the same exact schemas/examples/threat-matrix tree; no effect adapter or MCP server exists yet.

---

## OPM-1.G gate history (as of 2026-07-29)

`status` remains **blocked**: OPM-1.G has not been APPROVED. Tasks OPM-1.1–1.4 are implemented; the
gate is what is outstanding.

| Round | Verdict | Blocking findings | Remediation commit |
|---|---|---|---|
| R1 | CHANGES_REQUESTED | 6 | (round-1/2 cycle) |
| R2 | CHANGES_REQUESTED | 13 | `f1bfa39` |
| R3 | CHANGES_REQUESTED | 6 (NEW-18/19/20/21/22/23) | `f16059f` |
| R4 | CHANGES_REQUESTED | 9 (BLOCK-1…9) | `e4c76b9` |
| R5 | CHANGES_REQUESTED | 4 (R5-BLOCK-1…4) | in flight |
| Karen | FIX-REQUIRED | 4 adjudications returned (1 ratify, 2 ratify/accept-with-conditions, 1 amend) | see `FIND-P1-KAREN` |

**Round-5 state.** All nine round-4 findings independently re-verified CLOSED, eight of nine
mutation-verified as regression-detecting. The four new findings are each ADJACENT to a fix made
correctly — the recurring "the field next to the one that was fixed" shape. Blocking-finding count is
trending down (6 → 9 → 4).

**Karen's outstanding item that no agent can close:** Adjudication 1 condition (3) requires the human
**integration owner's acknowledgement** of the `governance.py` serialization-barrier write. A reviewer
can ratify the content of a barrier-file write; only the declared file owner can waive the ownership
barrier. This is a human sign-off, not an agent task.

**Deferred with named owners** (from the NB triage in the findings ledger): NB-2 → P5 entry gate
(`check_tool_name` must be wired with an artifact that fails if unwired); NB-4, NB-11 → P2;
`OPM-DF-preflight` → P2 (`governance.preflight()` must be wired once a run exists — see the amended
decisions-block line 30).

**Process lesson (Karen, for `op story capture`):** move mutation verification into the FIX step, not
the next REVIEW round. A remediation is not submitted until each fix has been reverted and shown to
break a named test. Rounds 4 and 5 exist largely because closure was asserted rather than demonstrated.

---

## CLOSEOUT — OPM-1.G closed by OWNER ACCEPTANCE (2026-07-29)

`status` is now `completed`. **To be precise about what that means: OPM-1.G was NOT gate-APPROVED.**
The last machine verdict is `CHANGES_REQUESTED` (round 5). P1 is closed by an explicit **human owner
decision** to defer the round-6 re-gate and accept tree `fce17e1` so P2 can proceed. Full record:
`FIND-P1-CLOSEOUT` in `.claude/findings/research-foundry-operator-mcp-findings.md`.

**Owner approvals recorded:** round-6 re-gate DEFERRED (`OPM-DF-regate`); `governance.py`
serialization-barrier write ACKNOWLEDGED by the integration owner (Karen Adjudication 1 condition 3 —
the one item no agent could close); `audit_service.py` / auth-package / `config.py` writes
ACKNOWLEDGED; P1 accepted and P2 unblocked.

**Residual risk accepted (named, not hidden):** the round-6 re-gate is deferred and `fce17e1` was never
adversarially re-attacked (base rate suggests 1–3 further findings); `operator_mcp_receipt.schema.yaml`
has yielded a finding in EVERY round it was examined and its final systematic sweep is itself
un-reviewed — treat as still under-reviewed; NB-7 means ~100 tests patch the identity-derivation seam,
so P2's first live run is the first substantial exercise of real derivation; NB-9 is a deliberate
availability tradeoff (unconditional audit probe → possible spurious `audit_unhealthy` under
contention); P1 has zero production callers by design.

**Carried to later phases:** NB-2 → P5 (with a failing-if-unwired artifact); NB-4, NB-11,
`OPM-DF-preflight`, R5-NB-1…7 → P2.

**P2 must adopt before execution:** mutation verification moves INTO the fix step — a remediation is not
submitted until each fix has been reverted in place and shown to break a NAMED test. Pre-P2 optimization
handoff: `op story` record **`806e4667-acd6-4ec4-9883-130ae95ec08a`**.
