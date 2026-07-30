---
title: "P2 Durable Operation Coordinator — delivery-report notes"
schema_version: 2
doc_type: report
report_category: execution_notes
status: in_progress
created: 2026-07-29
updated: 2026-07-29
feature_slug: research-foundry-operator-mcp
feature_version: v1
phase: 2
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
progress_ref: .claude/progress/research-foundry-operator-mcp/phase-2-progress.md
source: dev:execute-phase P2
---

# P2 execution notes (for the end-of-plan delivery report)

Running capture during execution — **not** reconstructed afterwards. Raw material for the
`delivery-report` skill (`feature` route at end-of-plan, `phase` route for the P2 recap).

## Baseline

- Worktree `.claude/worktrees/operator-mcp-v1`, branch `worktree-operator-mcp-v1`, head at P2 start
  `e5a2e6e` (P1 close-by-owner-acceptance), based on main `65d658d`. Draft PR #7.
- Worktree has **no `.venv`**. All validation uses main's interpreter:
  `PYTHONPATH=$PWD/src /Users/…/research-foundry/.venv/bin/python -m pytest … --color=no`
- Baseline before any P2 change: `tests/unit/test_operator_mcp_policy.py` +
  `test_operator_mcp_schemas.py` green (206 tests).
- Pre-existing, not chased: `tests/test_verification_pediatric_cds.py` and
  `test_verification_seam001_gate_composition.py` fail to COLLECT under `-k` filtering
  (sibling `import test_claim_verifier`); present on base `65d658d`.

## Routing decisions (delegation-router)

The router's MUST-stay classes cover the gates but not the leaf implementation tasks, so the split
below is a deliberate risk judgment, recorded for audit.

| Node | Provider / model | Rationale |
|---|---|---|
| OPM-2.1 immutable operation store | primary Claude, `python-backend-engineer` (sonnet) | DUR-1 atomicity is the AC-mandated **security** property; the plan warns a read-then-write CAS passes every P1 test. Not offloaded. |
| OPM-2.2 AgentJob attempt adapter | ICA `claude-sonnet-5[1m]` | Bounded, contract-clear adapter wrapping. Cost-shift target. |
| OPM-2.3 receipts persistence | ICA `claude-sonnet-5[1m]` | Schema-driven persistence against a frozen schema. |
| OPM-2.4 cancel/resume state machine | primary Claude | H3 ten-scenario convergence logic; correctness-dense. |
| Cheap pre-gate sweep | sonnet (~30k) | Plan-mandated fail-open / layer-below sweep **before** any Opus lens. |
| P2 security gate (AC-mandated) | primary Claude — MUST-stay (verdict) | Revised post-P1 gate structure: security-with-AC-mandate, then Karen. |
| Karen gate | primary Claude — MUST-stay (verdict) | Durability/atomicity adjudication. |

- **ICA verified live** on `claude-sonnet-5[1m]` before dispatch (smoke returned `ICA_OK`).
- **gpt-5.6 / Codex**: the plan records `codex exec` refusing this workstream's adversarial
  security-audit framing under its safety classifier — a policy refusal, not config. Not retried for
  the security lens. One bounded attempt planned as a **non-security-framed** engineering review of
  the SQLite concurrency/atomicity code (pure correctness framing), which is a different classifier
  surface. Outcome recorded below.
- No ITT binding exists on this plan (`intenttree_tree` absent), so the dev-execution SDLC sync
  hooks are a silent no-op. Follow-up nodes are therefore created explicitly.

## Inherited obligations carried into P2

From the P1 findings ledger (147k, read via delegated digest — never loaded into orchestrator
context):

| Item | Statement | P2 disposition |
|---|---|---|
| `OPM-DF-regate` | Round-6 security re-gate **deferred**; last machine verdict was `CHANGES_REQUESTED` (R5). The remediated tree was never re-attacked. | Re-verify, do not treat as clean. |
| `NB-4` | Public `now=` clock seam; named abuse is "P2 threading a request-supplied timestamp". | **Closed in P2** — see F2 below. |
| `NB-11` | Receipt-shape gaps: `checkpoint` lacks `workspace_id`; `operation_receipt.status: denied` has no reason field. | OPM-2.3 owns the decision. |
| `OPM-DF-preflight` | `governance.preflight()` is named in the frozen decisions block but has **zero call sites**. | Run-layer wiring → follow-up node; P2 closes the authorization-binding half (F1). |
| `NB-9` | Audit-health probe does INSERT+SELECT+DELETE on the authorization hot path; under DUR-1 concurrency this can surface as spurious `audit_unhealthy` denial / lock contention. | Honored: `authorize_operation` is computed **outside** `BEGIN IMMEDIATE`. |
| `NB-7` | ~100 tests monkeypatch `resolve_operator_identity`; real derivation is barely covered. | First live run is the first real exercise — budget for surprises. |
| Receipt schema | Yielded a finding in **every** round examined (NEW-20/21, BLOCK-2/3, R5-BLOCK-1/3), three of them *sibling-field* misses. The R5 per-property sweep is itself unreviewed. | Re-attack before building durable persistence on it (OPM-2.3). |

## OPM-2.1 — Immutable operation store

**Design decision (load-bearing).** DUR-1 requires the confirmation CAS and the manifest write in
one durable transaction. That is only possible if both live in the **same** SQLite database, so P2
owns a new `confirmations` table alongside `operations` — P1 never persisted confirmations
(`mint_confirmation`/`consume_confirmation` are pure). Store is
`FoundryPaths.operator_operations_db` under `.rf_state/` (durable, not gitignored; `.rf_cache` is
disposable and would have been wrong). Follows the `rbac_store._connect` idiom:
`isolation_level=None` + explicit `BEGIN IMMEDIATE`, `row_factory`, `PRAGMA foreign_keys=ON`,
additive `PRAGMA user_version`, explicit 15s `busy_timeout`.

**Defects found by orchestrator review of the first implementation** (all four verified against the
exact tree before dispatching the fix — none were self-reported):

| ID | Class | Defect |
|---|---|---|
| F1 | fail-open + **layer-below** | `consume_and_create_operation` is a public method on the durable effect boundary whose only authorization guard was a **docstring** ("callers MUST have already obtained an `allowed` decision"). Structurally identical to P1's round-2 critical defect, where a docstring steered callers to the weaker door. Fixed by making authorization a data dependency: a `PolicyDecision` bound to this `ctx` via `ctx.canonical_digest()`; absent ⇒ deny. |
| F2 | fail-open (`NB-4`) | Public `now=` param documented "TEST-ONLY" but unenforced ⇒ request-threadable expiry bypass. Replaced with the repo's canonical injectable clock `research_foundry.ids.now()` / `set_clock()`. |
| F3 | fail-open on security-relevant field | `record_confirmation` defaulted a missing `status` to `"issued"` (the one value permitting consumption) and a missing `issued_at` to *now* (maximizing the expiry clamp). Also kept **two sources of truth** for status — SQL column (tested by the CAS `WHERE`) vs `record_json` (tested by `consume_confirmation`) — the same sibling-divergence class that bit the receipt schema three rounds. |
| F4 | unbounded error | Raw `RuntimeError` crossing the boundary; `operator_mcp_error.schema.yaml` requires internal errors redacted and capped. |

**Process note that earned its keep:** the first implementation passed 249 tests, exit 0, with a
credible four-row mutation table — and still contained a docstring-only authorization guard on the
effect boundary. A green suite plus a self-reported mutation table is not gate evidence. All four
defects came from orchestrator review of the actual diff.

## Open items / follow-ups (→ ITT nodes)

Populated as execution proceeds; see the Next Actions table in the final response.
