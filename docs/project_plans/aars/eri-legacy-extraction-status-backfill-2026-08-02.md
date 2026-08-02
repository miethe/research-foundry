---
doc_type: report
report_category: aar
title: "AAR — ERI legacy extraction_status backfill (M1+M2 shipped, M3 failed)"
feature_slug: eri-legacy-extraction-status-backfill
status: completed
created: 2026-08-02
updated: 2026-08-02
plan_ref: docs/project_plans/implementation_plans/enhancements/eri-legacy-extraction-status-backfill-v1.md
merge_commit: e3ca9ba
merge_branch: main
intenttree_node: node_01KYWX69SRH981ZGE419GM31EE
---

# AAR — ERI legacy extraction_status backfill

Tier 2, 13 pts, `risk_level: high`, Mode-D. Landed as squash `e3ca9ba` on `main`.
**M1 and M2 complete and verified on live data. M3 failed.**

## Outcome

| Milestone | Result |
|---|---|
| M1 — recomputable status, dry-run only | **AC met.** 35 eligible / 452 ineligible / 16 already-set; 34 full_text + 1 partial; `authoritative_data_mutated: false` |
| M2 — atomic apply + rollback (Mode-D) | **AC met on live data.** 35 applied; 70 files changed (35 records + 35 provenance); 35/35 bindings verify; 452+16 byte-identical; no `content.bin` touched |
| M3 — live re-prove | **FAILED.** AC vacuous as written; `verification_failed` still 4, unchanged |

## The two real defects caught

**1. Truncation-indistinguishability (M1).** `extract_bytes` marks `partial` on strict
`> _MAX_EXTRACT_CHARS` *and truncates with `text[:_MAX_EXTRACT_CHARS]`*. So stored text of exactly the
limit is byte-identical whether it came from a genuinely 100,000-char document or a longer one
truncated to it. The first implementation reasoned by symmetry with `extract_bytes` and classified the
100,232-byte edition (exactly 100,000 decoded chars) as `full_text`. Its stored text is cut mid-word,
proving truncation. Recompute must therefore be **strictly more conservative than forward extraction**
— fail closed at `>=`. Without the fix, the backfill would have stamped `full_text` provenance onto a
demonstrably truncated document: fabricated fidelity metadata on an immutable evidence record, the
exact class `7e2c1e1` exists to prevent.

**Lesson:** a predicate that recomputes state cannot be assumed symmetric with the predicate that
produced it, when the producer is lossy. Ask what the producer *destroyed*.

**2. Approval-scope drift, three times (M2).** Each round fixed the instance and left the sibling:

| Round | Where scope was unenforced |
|---|---|
| `fb77395` | Apply re-derived eligibility with no link to the approval at all |
| `3a00e5e` | Link existed, but `_check_pinned_scope`'s return was discarded and the loop re-globbed |
| `d8f89e5` | Eligible loop constrained — the sibling `already_set` repair loop was not |

Two of the three were introduced or left in place by the orchestrator's own fix instructions. The
third round triggered the same-class stop rule, and the response was a **re-scope, not a fourth
guard**: delete the repair-on-apply path (never in M2's AC; added mid-execution in response to a
review finding; the state it repaired is already recoverable by re-running the same rollback receipt).
Result — exactly one write loop, iterating the approved set, so touching an unapproved edition is
*structurally impossible* rather than *checked*.

**Lesson:** guarding an entry point without enumerating its siblings reproduces the defect one layer
over. When two consecutive rounds find one class, reduce the number of surfaces instead of adding a
check to each.

## Gate economics — the lenses disagreed, and each was necessary

| Lens | M2 verdicts | What only it found |
|---|---|---|
| validator | APPROVED, APPROVED | Nothing wrong — correctly confirmed the code does what it claims |
| gpt-5.6 (cross-model) | REJECT, REJECT | Non-durable receipt (rollback impossible after mid-loop failure); unguarded rollback entry point; no path validation; the unapproved `already_set` write |
| security | CHANGES_REQUESTED ×2, then APPROVED | **Approval-scope drift (B2)** — the governance boundary; stale-snapshot repair race |

**The validator kept approving because the code did what it claimed; every failure was in what it did
not claim.** A suite asserting correct behaviour on success cannot see a rollback that can't run, a
second entry point that skips the gate, or a scope check the writes outrun. "69 tests green" and "B2
not closed" were simultaneously true.

The cross-model lens earned its cost *on the milestone where it mattered* — and only after its
invocation was fixed (see below). The security lens found the one defect neither other lens looked
for, because it was the only one briefed on the Mode-D boundary.

## Process failures worth more than the milestones

**Five tools failed while reporting success.** Every one exited 0 with plausible output:

1. `op context pack` on macOS returned a **Linux node path** and wrote nothing.
2. `codex exec "$(cat f)"` sent the prompt to **stdin**; the entire transcript was one line.
3. Corrected `codex exec` obeyed *this repo's own* "delegate everything" CLAUDE.md, tried to spawn
   reviewer subagents, and died on collab-spawn limits — twice, without a verdict.
4. A bad `--workspace-root` returned an **all-zero receipt at exit 0** (fixed during the round).
5. **The first M3 run was inert.** Run with cwd in the git worktree, `FoundryPaths.discover()`
   resolved to the worktree root, so it created a fresh empty ledger there, fresh-acquired 16 sources
   into it, and never touched the backfilled live data — while reporting the *correct* packet digest
   and a plausible receipt.

**Lesson:** exit code is not evidence. Grep for the specific artifact you demanded (a verdict token, a
count, a path that exists). #5 is the sharpest: M3 exists to catch changes that never reach
production, and M3 itself never reached production.

**Codex works here, but only in one shape.** Main checkout (not a worktree — trusted-dir and
`.agents/skills` overrides are hostile), prompt via `- < file`, code inlined so it never explores
files and never trips the delegate-everything directive, and a demanded terminal `VERDICT:` token
grepped with `grep -c '^VERDICT:'`.

**Dry-run does not predict the live import.** Same packet, workspace, and target against the live
ledger: `--dry-run` reported `{locator_only: 15, passage_resolved: 4, source_resolved: 4}` / 23
completed; the real run gave `{source_resolved: 16}` / 16 completed / 22 quarantined /
`passage_resolved: 0`. Confirmed not a receipt replay (a fresh target run id produced a new receipt
and the same live numbers). This is a regression of the property `1f982a7` established. A preview that
disagrees with the run it previews is worse than no preview — it was the basis on which M3 briefly
looked like a pass.

## Why M3 failed — and the plan-internal contradiction

Two separate problems:

1. **The AC is vacuous as written.** It reads `by_completeness_tier.verification_failed < 4`, but that
   map tallies only *completed* actions — every quarantined action carries `completeness_tier: null`
   (verified: 16 tiered, 22 null). `verification_failed` can never appear there for a quarantined
   candidate, so the AC is satisfied by construction. Reading 0 from it proves nothing.
2. **On the authoritative per-action reason codes**, `verification_failed` is **still 4** — unchanged
   (with 12 `citation_unresolved`, 3 `source_unavailable`, 3 `citation_ambiguous`; 22 quarantined).
   The backfill did not move the number M3 exists to move.

**Leading hypothesis, unconfirmed:** the 4 candidates bind to editions in the **452**
`assertion_rollout` population that M2 excludes *permanently* by accepted decision ("a quote-join has
no honest full_text to recompute"). If so, **M3's AC was never achievable under M2's own scope** — a
contradiction between two sections of the same plan, which should have been caught at planning time
rather than after a Mode-D mutation of live evidence records. Confirming needs a
candidate → source → edition trace; quarantined candidate effects carry `canonical_refs: {}`, so they
quarantine before binding.

**Lesson for planning:** when a plan permanently excludes a population in one milestone, check that no
later milestone's AC depends on that population. And state ACs against the field that actually carries
the signal — an AC pointed at a field that cannot hold the failing value is unfalsifiable.

## What made the Mode-D apply safe

Worth keeping as the template: an **out-of-band snapshot before anything** (70MB `cp -a`, 503 editions
verified, plus a 16,873-file sha256 baseline manifest) so rollback never depended on the new code
being correct; proving apply *and* rollback on a full-fidelity copy before touching live; negative
controls fired against the live path to confirm guards raise *pre-write*; and a full-tree manifest diff
as the acceptance evidence rather than the tool's own self-report.

The snapshot also caught a false alarm honestly: a refused apply left a zero-byte `.apply.lock` in the
evidence tree, which tripped the integrity check. Lock-before-check ordering is correct and must stay
(the pinned check reads live state); the missing cleanup-on-refusal was the bug.

## Follow-ups

| Item | Priority |
|---|---|
| Decide M3: confirm whether the 4 candidates bind to the excluded 452; if so, rewrite the AC or re-scope | P1 — blocks plan completion |
| Fix M3's AC to read the per-action reason codes, not `by_completeness_tier` | P1 |
| Investigate dry-run over-reporting resolution vs the real import (regression of `1f982a7`) | P2 |
| Ledger-integrity checks must exclude `backfill_operations/.apply.lock` | P3 |
| `op context pack` returns a Linux node path on macOS and writes nothing | P2 — silent, affects every delegation |
