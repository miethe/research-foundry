---
type: progress
schema_version: 2
doc_type: progress
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
phase: 2
status: in_progress
created: '2026-07-28'
updated: '2026-07-29'
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
contributors:
- data-layer-expert
tasks:
- id: OPM-2.1
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-1.G
  estimate: 1.5 pts
  started: 2026-07-30T00:20Z
  completed: 2026-07-30T01:15Z
  evidence:
  - test: tests/unit/test_operator_operation_service.py
  - validation: 257 passed exit 0 (orchestrator-independent re-run)
- id: OPM-2.2
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-2.1
  estimate: 1.5 pts
  started: 2026-07-30T01:35Z
  completed: 2026-07-30T02:05Z
  evidence:
  - test: tests/unit/test_operator_attempt_adapter.py
  - validation: 319 passed 0 failures exit 0 (orchestrator-independent re-run)
- id: OPM-2.3
  status: completed
  assigned_to:
  - python-backend-engineer
  - data-layer-expert
  dependencies:
  - OPM-2.2
  estimate: 1 pt
  started: 2026-07-30T02:30Z
  completed: 2026-07-30T03:10Z
  evidence:
  - test: tests/unit/test_operator_receipt_service.py
  - validation: 585 dots 0F 0E 0skip exit 0 (orchestrator-independent)
- id: OPM-2.4
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-2.3
  estimate: 1 pt
  started: 2026-07-30T03:15Z
  completed: 2026-07-30T03:55Z
  evidence:
  - test: tests/unit/test_operator_cancel_resume_service.py
  - validation: 600 dots 0F 0E 0skip exit 0 (orchestrator-independent)
parallelization:
  batch_1:
  - OPM-2.1
  batch_2:
  - OPM-2.2
  batch_3:
  - OPM-2.3
  batch_4:
  - OPM-2.4
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 2 Progress — Durable Operation Coordinator

**Dependencies**: `OPM-1.G` approved on the exact current tree.
**Integration owner**: python-backend-engineer.
**Exit state**: stable operation manifests coordinate AgentJob attempts and converge through retry/cancel/resume.

| Task ID | Task | Acceptance criteria | Estimate |
|---|---|---|---:|
| OPM-2.1 | Immutable operation store | Exact manifest replay resolves same operation; changed manifest conflicts | 1.5 pts |
| OPM-2.2 | AgentJob attempt adapter | Legacy AgentJob reads pass; wrong-workspace attempts are indistinguishable from missing | 1.5 pts |
| OPM-2.3 | Effect/checkpoint/terminal receipts | Truncated/extra/duplicate/reordered/mismatched receipt fixtures deny | 1 pt |
| OPM-2.4 | Cancel and resume state machine | H3 ten-scenario matrix converges with uninterrupted effects | 1 pt |

Quality gate (per plan): process-loss, exact-retry, conflict, cancel, resume, policy-change, and reconciliation fixtures pass; operation receipt is primary (audit-service failure is explicit and cannot erase effect truth); `task-completion-validator` and `karen` approve the exact lifecycle candidate.

## Carried deferrals P6 must read (do not treat AC OPM-2/OPM-3 as evidenced over these)

Recorded here because `OPM-6.3`/`OPM-6.4` read this file, and a deferral recorded only in a source
docstring is a silent gap (Karen K3-NB-4, round 3).

| Id | Deferral | Lands |
|---|---|---|
| `P2S-NB-1` | **Read-path sensitivity threshold.** The execution-time sensitivity gate holds upstream in `operator_mcp_policy._check_guard`, but the receipt//operation **read** paths do not apply a sensitivity threshold. AC OPM-2 is MET for workspace scoping; the sensitivity half of the read path is deferred. | `OPM-5.4` |
| `P2S-NB-9` | **Bounded attempts.** No `max_attempt`/`attempt_limit` exists anywhere yet (verified by grep). AC OPM-3's "bounded" clause is not evidenced by P2. | `OPM-3.4` |
| `REGATE-NB-4` | The four receipt writers authorize against a caller-supplied **workspace string**, not an `AuthIdentity` (the reads use identity). Closes the hole; leaves a weaker attacker bar ("know the workspace name"). | P3 |
| `K3-NB-5` | Nothing binds `action_id` to `action_index`, so an in-workspace caller writing the next contiguous index out of turn is accepted immutably and the real action is silently **skipped**. | P3 |

## Gate record

| Round | Lens | Tree | Verdict |
|---|---|---|---|
| 2 | Security (AC-mandated) | `2806ea5` | CHANGES_REQUESTED |
| 2 | Karen | `2806ea5` | CHANGES_REQUESTED |
| 3 | Security (AC-mandated) | `be6ba96` | **APPROVED** (AC OPM-2 MET, AC OPM-3 MET) |
| 3 | Karen | `be6ba96` | CHANGES_REQUESTED — K3-BLOCK-1 |

Detail: `.claude/findings/research-foundry-operator-mcp-findings.md` §`FIND-P2-REGATE-R3`.

### Gate record (final)

| Round | Lens | Tree | Verdict |
|---|---|---|---|
| 4 | Karen | `4e3e62f` | CHANGES_REQUESTED — K4-BLOCK-1 |
| 5 | Karen | `ad7d461` | **APPROVED** |

Security lens APPROVED on `be6ba96`; `be6ba96..ad7d461` is guard-strengthening + tests only.
Carried to P3 as a **High** obligation: `K4-NB-1` — `operator_receipt_service.py` leaks raw
`sqlite3.OperationalError` from `load_terminal_receipt`/`load_checkpoint`/`resolve_resume_point`
(reproduced), reachable from the same two governed APIs. Detail: `FIND-P2-REGATE-R4R5`.
