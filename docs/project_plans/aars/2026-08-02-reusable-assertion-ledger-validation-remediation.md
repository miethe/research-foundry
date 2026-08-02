---
title: "AAR: Reusable Assertion Ledger — completion validation & bookkeeping remediation"
doc_type: aar
status: review
date: 2026-08-02
created: 2026-08-02
updated: 2026-08-02
feature_slug: reusable-assertion-ledger
outcome: success
related_documents:
  - ../implementation_plans/features/reusable-assertion-ledger-v1.md
  - ../aars/2026-07-31-reusable-assertion-ledger-p9-closeout.md
  - ../aars/2026-07-14-reusable-assertion-ledger-p0-p5-execution.md
  - ../../../.claude/rules/plan-bookkeeping.md
---

# AAR: Reusable Assertion Ledger — validation & bookkeeping remediation

**Context.** Question asked: "validate if `reusable-assertion-ledger-v1.md` is already completed."
The plan self-declared `status: completed`. Four parallel read-only forensic legs (commit
provenance, phase status, flag drift, gate-vs-config exposure) plus direct verification established
that the **feature is genuinely complete** — and that its tracking artifacts had drifted in five
independent ways. Remediation landed as one squash on `main`.

## Answer to the question

Complete as **repository-readiness closeout**. All nine phases have real on-main commits, a 100%
tracker, and an independent `task-completion-validator` APPROVE (P0 also Karen), including genuine
reject→remediate→approve cycles (three rounds on P5 for concrete bugs). 393 assertion tests exit 0.
The sole open item is **P8-004** (live private-beta health evidence), operator-authorization-gated.
Two design specs are deferred by explicit decision.

## The five drift classes

1. **Codex-vs-Claude tracker split.** Phases P0–P5 were Codex-executed and tracked under
   `.codex/progress/reusable-assertion-ledger/`, not `.claude/progress/`. Nothing was deleted; the
   files were never created in the Claude location. The `70d7e02` closeout flipped the root plan and
   phase-9 and never revisited the six Codex-tracked siblings, leaving `draft`/`review` under a
   `completed` root.
2. **Uncitable `commit_refs`.** All three entries were invalid: two were pre-squash worktree commits
   unreachable from any ref, and the third was a git **tree** object — literally the tree of the
   entry above it, leaked from the project's `<commit> / <tree>` review-citation convention when the
   frontmatter was assembled. At least three such dangling pairs exist across this feature.
3. **Phantom feature flags.** `RF_ASSERTION_LEDGER_ENABLED` / `RF_ASSERTION_REUSE_ENABLED` /
   `RF_CANONICAL_CLAIMS_ENABLED` never existed in any form — `config.py` has zero `os.environ`
   reads. Drift entered undocumented at `f95585b`, which added the real `AssertionLedgerControls`
   *and* a correct doc section without removing the wrong one. 19 sites named the phantoms, including
   `assertion-ledger-contract.md`, which contradicted its own correct section in the same file.
4. **Sibling phase-id collision.** `reusable-assertion-ledger-v1` (P0–P8) and
   `assertion-ledger-activation-v1` (P1–P6) collide. The IntentTree node *and* a fresh forensic
   subagent both cross-credited the 07-17 activation commits to this plan.
5. **Governance record vs shipped config.** All three SPIKE verdicts were `conditional`, never `go`;
   the decisions-block ordered a flag false that never existed; `foundry.yaml` enabled all three
   capabilities. The `ba9e551` override was disclosed in the user doc but the plan body was never
   reconciled, so the plan silently contradicted the shipped state.

## Lessons (reusable)

1. **`git log -1 <sha>` succeeds on an orphaned commit.** It resolves the object, not a ref. Only
   `git merge-base --is-ancestor <sha> main` proves reachability. My first pass called two shas
   "real commits" on the strength of `git log` and had to correct it.
2. **Grade flag exposure by what the flag can change, not by which decision it violates.**
   `canonical_claims_enabled: true` violated a "mandatory false" but was **inert** (no production
   caller), so reverting cost nothing. `automated_reuse_enabled` cannot widen safety at all —
   `evaluate_reuse()` is a pure flag-independent function that denies every structural failure, and
   the capability is consulted only after, converting `allow`→`deny`. The real gap was never "unsafe
   reuse gets through" but "aggregate fidelity was never measured."
3. **"Gate receipts" with no code reading them are process, not enforcement.** Every capability read
   resolves straight from `foundry.yaml`. Verify a gate exists in code before treating its absence
   as a bypass — or its presence as protection.
4. **A locked decision naming an unbuilt mechanism is unenforceable.** "Keep
   `RF_ASSERTION_REUSE_ENABLED=false`" could never bind anything.
5. **Distrust a subagent's synthesis where it contradicts primary sources.** One leg concluded "no
   contradiction" between SPIKE verdicts and enabled flags; the verdict lines said the opposite
   verbatim. Another repeated the cross-attribution error. Both legs were otherwise excellent —
   spot-check conclusions, not just evidence.
6. **Check `HEAD` before editing.** The primary checkout was on another session's branch with dirty
   state at the start of this work, and `main` advanced twice mid-session. All edits went through a
   dedicated worktree; editing in place would have contaminated an unrelated branch.
7. **Attribute commits by files touched, not by the phase label in the subject.**

## What landed

Squash on `main`: 9/9 phase files `completed`; PRD + human brief `completed`; `commit_refs` replaced
with the verified 9-commit on-main chain; ~19 doc sites corrected to `foundry.assertion_ledger.*`
with historical records annotated rather than rewritten; `canonical_claims_enabled` → `false`;
dated single-operator-override addendum in the plan; `.claude/rules/plan-bookkeeping.md` added to
prevent recurrence. IntentTree node description corrected (status left `in_progress`/0.5 — accurate,
two deferrals open).

## Open / deferred

- **P8-004** live private-beta health evidence — operator-authorization-gated.
- **`automated_reuse_enabled`** stays `true` by operator decision; the historical-replay SPIKE's
  corpus-scale measurement (10–20 runs, 100–300 sources, 60-assertion audit) remains unrun.
- Two deferred design specs (public rights promotion, shared indexes) — parked by explicit decision.
