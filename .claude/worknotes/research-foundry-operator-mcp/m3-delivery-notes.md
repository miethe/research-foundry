---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: in_progress
created: '2026-07-31'
updated: '2026-07-31'
---

# M3 delivery notes — one exact tree satisfies AC OPM-1..7

Running capture for the M3 delivery report + AAR. Continues the M2 pattern (`m2-delivery-notes.md`).

## Setup

- Branch `worktree-operator-mcp-v1` @ `a4e320e` (M2 close, pushed, PR #7). ITT node
  `node_01KY5SHNM6JVMCCKYXP44GRSDR` already `in_progress` (since M2 start) — milestone-start sync
  satisfied, no state change needed.
- Provisioning gate: same single non-fatal gap as M2 (`skill:delegation-router` overlay refused by
  SkillMeat enterprise; skill live at user scope). Non-blocking.
- Baseline recon (orchestrator, pre-dispatch): `tests/integration/test_operator_mcp_workspace_isolation.py`
  (AC OPM-2's named command) **does not exist** — real gap, assigned to Leg A. Closed-dispatch `rg`
  scan hits are docstrings/comments only. One **order-dependent flake** found:
  `test_job_resume_wrong_workspace_indistinguishable_from_missing_dry_run` failed 1/5 full
  adapter-batch runs (message-dict mismatch), passes alone and in 4/5 batch runs — assigned to
  Leg B (D7).
- Contract: `m3-implementer-contract.md` (D1–D8). Routing resolved + audit-logged via
  delegation-router resolver (8 RoutingRecords).

## Routing (delegation-router resolved, logged)

| Leg | Work | Route |
|---|---|---|
| A | OPM-6.2/6.3 adversarial matrices + receipt per-property attack | claude-primary Sonnet 5 xhigh (authorization surface — MUST-stay) |
| B | OPM-6.4 lifecycle matrix + OPM-6.1 fixtures + D7 flake | claude-primary Sonnet 5 high |
| C | OPM-6.5..6.8 evidence reconciliation (read-only report) | ICA sonnet-5[1m] free lane |
| D | OPM-6.9 docs + CHANGELOG + 2 shaping specs | Codex gpt-5.6-terra (workspace-write) |
| Pre-gate | two diverse cheap lenses on M3 delta | gpt-5.6-terra (high) + ICA sonnet-5[1m] |
| Gate | validator (fresh context) | claude Sonnet 5 |
| Gate | Karen — final exact tree only | claude Opus-class, fresh context |

## Observations for the AAR

- **O-0 — M2's paid-for lessons paid out immediately, twice, before wave 1 even dispatched.**
  (a) The M3-start whole-suite baseline read 23 failed and the M2 record said "16 known-failing"
  in older notes — the M2 O-9 *set* record (4691/23, 13 files) resolved it in one diff: byte-for-
  byte the same set, zero drift. Diffing sets, not counts, took minutes. (b) The "flake" found in
  pre-dispatch recon (`test_job_resume_wrong_workspace_indistinguishable_from_missing_dry_run`,
  1/5 batch runs) is M2 O-7's exact mechanism — the orchestrator (me) ran two pytest invocations
  concurrently in one message during recon. Self-inflicted, resolved by reading the prior
  milestone's notes instead of dispatching a root-cause leg (which the original D7 had already
  budgeted). Carry-in for the AAR: the delivery-notes discipline has measurable compound value;
  reading the prior milestone's observations before scoping legs is cheaper than re-deriving.
  Standing mitigation added to the contract: mkdir-lock around every pytest invocation while
  parallel legs share the worktree.

- **O-1 — Registry drift in the router.** `~/.claude/config/model-registry.yaml` still maps ICA
  sonnet to `claude-sonnet-4-5[1m]` while ICA has served Sonnet 5 since 2026-07-08; the audit-log
  entries carry the stale id. Non-blocking (the ica-delegate alias remap covers it) but the
  registry should be bumped — follow-up candidate.

- **O-2 — The reconciliation leg (ICA, read-only) earned its lane: 1 VACUOUS + 3 INCOMPLETE
  matrix rows + 15 unattacked receipt properties found for free-tier tokens.** The vacuous row
  (`M1 retry/cancel idempotency`: `-k "retry or cancel or resume or duplicate"` selects **0/33**
  in the named file) is the VAL-1 defect class hitting the *plan document itself* — the evidence
  matrix carried a command that proves nothing, through two closed milestones. Also: the AC lint
  command (`flake8`) cannot run in the project venv (only `ruff` is installed) — replaced with
  `./.venv/bin/ruff check src/research_foundry --select E9,F63,F7,F82` (verified: exit 0).
  Carry-in: collect-only audits of every `-k` filter belong in milestone *authoring*, not just
  execution — the audit costs seconds per row.
- **O-3 — The reconciliation leg independently rediscovered the concurrent-suite hazard** (its
  self-launched full-suite run picked up a spurious operator-surface failure while Legs A/B ran
  under the pytest lock it did not use for that run, at 94% system swap). Its 23-node list with
  one operator-surface entry is thereby explained; the orchestrator's earlier single-tenant
  baseline (byte-identical to the M2 O-9 set) stands as the honest pre-M3 baseline. Two
  milestones in a row this hazard has cost a measurement — it is now a standing contract rule
  (D7 mkdir-lock), but off-contract runs (the ICA leg ran pytest outside its task's collect-only
  scope) still slip through. Sharper carry-in: read-only legs get "collect-only ONLY; never
  execute the suite" as an explicit prohibition, not an implication.

## Follow-ups (ITT candidates)

- Model-registry ICA sonnet id bump (see O-1).
- Plan AC-matrix row repairs (vacuous/incomplete filters, lint command) — done in-branch this
  milestone; upstream lesson for planning skill: collect-only audit at authoring time.
