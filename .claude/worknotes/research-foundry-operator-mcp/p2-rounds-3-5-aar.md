---
title: "Operator MCP P2 — rounds 3–5 After-Action Review"
date: 2026-07-30
phase: P2 (Operator MCP v1)
outcome: CLOSED — both required lenses APPROVED
branch: worktree-operator-mcp-v1
commits: 9df464b (K4 fix), 5a13848 (closure)
gate_record: FIND-P2-REGATE-R4R5
---

# Operator MCP P2 — rounds 3–5 After-Action Review

## What happened

P2 entered round 3 needing one thing: the APPROVED verdict its progress artifact could not be
signed without. Three adversarial rounds and two fix waves later it got two.

| Round | Lens | Tree | Verdict |
|---|---|---|---|
| 3 | Security (AC-mandated), Opus | `be6ba96` | **APPROVED** — AC OPM-2 MET, AC OPM-3 MET |
| 3 | Karen, Opus | `be6ba96` | CHANGES_REQUESTED — K3-BLOCK-1 |
| 4 | Karen, Opus | `4e3e62f` | CHANGES_REQUESTED — K4-BLOCK-1 |
| 5 | Karen, Opus | `ad7d461` | **APPROVED** |

P2 is the first phase in this workstream to close on real machine verdicts. P1 closed by owner
acceptance with a `CHANGES_REQUESTED` still standing — `completed` there did not mean gate-approved.
That distinction is the point of the exercise and should stay visible in the record.

## Lesson 1 (primary) — a defect that is a property of a PATTERN must be enumerated in round 1

K3-BLOCK-1 (`record_confirmation`), K4-BLOCK-1 (`load_operation`), and K4-NB-1
(`operator_receipt_service.py`) are **one defect**: an unguarded `_ensure_schema` on a shared SQLite
file, which takes a RESERVED lock on cold start and leaks a raw `sqlite3.OperationalError` across a
governed module boundary.

Each gate round closed the instance directly in front of it, and the next sweep found the next
instance. Three full adversarial rounds — each one an Opus reviewer, a fix wave, and a re-validation
— were spent on a single pattern that a five-second `grep _ensure_schema` would have enumerated up
front.

**Rule:** when a finding's root cause is a *shape of code* rather than a *site*, do not fix the
site. Grep the shape, enumerate every occurrence, and fix them as a set in one wave — then let the
gate confirm the set. Reviewers should likewise be asked to report the pattern's full extent, not
the first instance they can prove.

This is the eighth instance of the layer-below/sibling defect class in this workstream. The class is
now well-enough evidenced that it deserves to be a standing checklist item at fix time, not a lesson
re-learned per phase.

## Lesson 2 — do not fold a transient failure into an existing permanent-failure contract

The tempting fix for the store-unavailable case was to raise the `KeyError` the callers already
handle. That would have been wrong: both callers map `KeyError` → `not_found`, so a *transient* lock
would have been reported as a *permanent* "does not exist", and callers would correctly stop
retrying. Worse than the raw leak it replaced.

The fix uses a distinct bounded type (`OperationStoreUnavailableError`) → `internal_error`. Karen
verified empirically that the distinct code leaks no existence information: five inputs including a
real row produced byte-identical messages and indistinguishable latency (SQLite locks whole files,
so `SQLITE_BUSY` cannot be differential by bound value).

**Rule:** before reusing an existing error contract, check what the *callers* do with it. Retryability
is part of the contract even when it is not part of the type.

## Lesson 3 — test vacuity has a specific shape in this class

`_ensure_schema` is gated on `PRAGMA user_version`. With a **warm** schema it no-ops, and the method
under test degenerates to a pure reader that a RESERVED lock does not block — so a contention test
that pre-creates the store **passes vacuously**. The real window is schema-ABSENT plus a concurrent
writer, which requires the blocker to hold its DDL in an *uncommitted* transaction so `user_version`
stays 0.

Two of my first K4 tests failed with "DID NOT RAISE" for exactly this reason, which is the good
outcome; the bad outcome is the version of those tests that passes.

**Rule:** for any guard on lazily-initialized shared state, ask what makes the initializer a no-op
and assert the test does not accidentally arrange it.

## Lesson 4 — mutation-verify inside the FIX step, and mutate the plausible wrong fix

Carried forward from P1 and re-confirmed. The load-bearing mutant here was not "delete the guard" —
it was "fold it into the `KeyError` contract", i.e. the plausible-but-wrong implementation a
reasonable engineer would actually write. A test suite that only rejects the guard's *absence*
proves much less than one that rejects the wrong *presence*.

Still true, still costly: purge `__pycache__` and set `PYTHONDONTWRITEBYTECODE=1` every iteration,
or successive mutations sharing a file-size delta will silently false-green.

## Lesson 5 (process) — never gate a tree another agent is rewriting

A second agent was running the P3 receipt-identity refactor in the **same worktree**, mid-flight, on
the same files. Symptoms: the Edit tool reporting "file modified on disk", and ~20 half-applied
Pyright call-signature errors that belonged to neither agent's intended state.

Recovery was to surgically reverse-edit my own uncommitted changes out — explicitly *not*
`git checkout`, which would have destroyed the other agent's in-flight work — then
`git worktree add <new> -b <branch> <base-commit>`, do the work isolated, and `git merge --squash`
back once the other agent had committed.

**Rule:** worktree isolation is per-agent, not per-phase. Before validating or gating, confirm the
tree has one writer. Reviewers (read-only) are unaffected, which is why the round-3 security gate
was unharmed by this.

Related, re-confirmed: a background session that `cd`s into a worktree can edit inline, but its
**subagents** cannot write, and `EnterWorktree` refuses when cwd already *is* the target. Fully
specified fixes therefore have to be applied inline in that configuration.

## Carried obligation — K4-NB-1 (High, OPEN)

`operator_receipt_service.py` has **zero** `OperationalError` handlers across all **7**
`_ensure_schema` sites. Karen *reproduced* raw leaks from `load_terminal_receipt`, `load_checkpoint`,
and `resolve_resume_point`, all reachable from the same two governed APIs
(`operator_cancel_resume_service.py:940/:949/:1126/:1130`).

It is pre-existing and untouched by the P2 delta, so blocking a narrow re-gate on it would have been
manufacturing a blocker — but it is the same defect as lessons 1 and 2, and it has now been deferred
as "adjacent" twice. It is assigned to the live P3 wave and must not be deferred a third time.

## What to change

1. Add "grep the pattern, fix the set" to the fix-wave checklist — before writing the fix, not after
   the next gate.
2. Ask reviewers for a pattern's full extent, not its first provable instance.
3. Add "what makes this initializer a no-op?" to the test-review checklist for lazily-initialized
   shared state.
4. Add a single-writer check to the pre-gate validation step.
