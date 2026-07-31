---
title: "AAR: Reusable Assertion Ledger P9 Closeout (reconcile-not-rebuild)"
doc_type: aar
status: review
date: 2026-07-31
created: 2026-07-31
updated: 2026-07-31
feature_slug: reusable-assertion-ledger
outcome: success
related_documents:
  - ../implementation_plans/features/reusable-assertion-ledger-v1.md
  - ../implementation_plans/features/reusable-assertion-ledger-v1/phase-9-docs-private-rollout.md
  - ../aars/2026-07-14-reusable-assertion-ledger-p0-p5-execution.md
---

# AAR: Reusable Assertion Ledger P9 Closeout

**Context.** `/dev:execute-phase reusable-assertion-ledger-v1 → node …CZ43C P9. Squash to main.`
The command framed P9 ("Documentation and Private Rollout", the final phase) as unstarted work to
build and land. It wasn't. Landed as squash `70d7e02` on `main` after a reconciliation, not a build.

## What happened

- No `phase-9-progress.md` existed and several codex worktrees for the feature were present, which
  *looked* like "phase not started, work stranded on branches."
- The codex `p7-evaluation` branch diffed against its **merge-base** showed a full P7+P8 implementation
  (1766 insertions) — reinforcing "the work lives on the branch, not main."
- Diffing against **`main` HEAD** inverted the picture: main was **59 commits ahead**, the branch **4
  behind-and-superseded**, and P9 was **~95% already merged** incrementally. The branch's files were
  smaller/older than main's.
- Real remaining delta was tiny: 2 red rollout tests + a governance contradiction, not missing docs.

## Lessons (reusable)

1. **"Execute" can mean reconcile, not rebuild.** Before dispatching implementers for a phase that
   looks unstarted, verify what is *actually on `main` HEAD*. **Diff against HEAD, not the merge-base**
   — a merge-base diff of a stale branch reads as a superset and will send you to rebuild landed work.
2. **Surface contradictions; ask; never paper over.** Two genuine forks — shipped `foundry.yaml`
   enables all three ledger flags (single-operator opt-in) while AC P8-ROLLOUT demands default-off, and
   P8-004 live health-evidence is operator-authorization-gated — were resolved by asking the operator
   (bookkeeping+gate; document-the-deviation), not by flipping status to a false green.
3. **Closeout gates need explicit framing.** A reviewer told "verify this phase" on a mostly-already-
   landed diff will false-fail on "implementation missing." Framing it as *bookkeeping closeout of
   incrementally-landed work* (with spot-checks that the deliverables exist on main) got honest PASS /
   APPROVED verdicts from task-completion-validator and Karen.
4. **`manage-plan-status.py` reflows the whole YAML frontmatter** (quotes, flow→block lists, quoted
   dates, reflowed `wave_plan`): a 1-field `status` flip churned 231 lines. Use a **surgical `Edit`**
   for plan/PRD/phase status flips; reserve the CLI for `.claude/progress/*` where formatting is moot.
5. **A `completed` status must not silently contradict its own `exit_criteria`.** Karen's caveat: the
   phase listed "private-beta health evidence pass" as an exit item while being marked completed with
   that item deferred. Annotate the deferred criterion in-place so status and criteria agree in retro.

## What landed

Squash `70d7e02` (6 files, +154): 2 rollout tests decoupled to assert the code-level default-off
contract (11/11 green); single-operator opt-in caveats in the user doc + readiness runbook; phase-9 +
root plan `review→completed`; `phase-9-progress.md`; closeout note. IntentTree node `…CZ43C` P9 child →
completed. Stale codex branch + worktree removed.

## Open / deferred

- **P8-004 live private-beta health evidence** — sole open item; operator-authorization-gated
  (`scripts/assertion_ledger_readiness.py` in an authorized private workspace). Rollout sequence steps
  2-6 remain operator-run.
- Root plan `commit_refs` still lists 3 orphaned codex SHAs (`f5ce6ae`/`9cf7e6b`/`26e8f77`) not on main
  — pre-existing, low-priority cleanup.
