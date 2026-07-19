# Phase 5 Completion Note — Parameterize Path-B workflow (RFUP-1)

## Summary

Phase 5 parameterized `.claude/workflows/rf-run-execute.js`, replacing its four hard-coded
machine constants (`RF`, `REPO`, `TMP`, `STAMP`) with args-driven values (`A.rf_bin`, `A.repo`,
`A.tmp_dir`, `A.timestamp`), each falling back to the original literal to preserve current
behavior on this machine. A `dry_run` short-circuit was added (matching the sibling
`research-foundry-swarm.js`/`research-foundry-council.js` pattern), and the workflow was
registered in `.claude/specs/workflows/workflow-registry.md` for the first time (previously
only mentioned in prose as "the `rf-run-execute` tail"). TASK-5.1/5.2/5.3 were combined into a
single delegation (same file, same owner, hard sequential dependency) per the batch-autonomy
guidance; TASK-5.4 (validator gate) ran as a separate delegation and required one fix cycle.

## Tasks

- [x] TASK-5.1 → ai-artifacts-engineer — hard-coded paths replaced with `A.rf_bin`/`A.repo`/`A.tmp_dir`, default = original literal, relative values resolved via new `resolvePath()` against `process.cwd()`.
- [x] TASK-5.2 → ai-artifacts-engineer — `STAMP` now derives from `A.timestamp` (ISO-8601, new `stampFromTimestamp()` regex helper) rather than `new Date()`, correcting the plan doc's own suggested pseudocode which would have violated the workflow-authoring four-constraints checklist ("no Date.now()/Math.random()/argless new Date() in script body" — `.claude/specs/workflows/workflow-authoring-spec.md` §5). Falls back to the original literal `20260613` when `A.timestamp` is absent.
- [x] TASK-5.3 → ai-artifacts-engineer — validation run (syntax-check-helper + vm-based dry-run harness with two distinct `A.timestamp` values) plus registry row added at `.claude/specs/workflows/workflow-registry.md:39`.
- [x] TASK-5.4 → task-completion-validator — gate ran, found one required fix, re-checked, PASS.

## Validator Verdict

**PASS** (after 1 fix cycle). First pass: FIX-REQUIRED — the new `rf-run-execute` registry row
set `Status: active` while its `Spec` column had no spec file on disk, violating the registry's
own documented invariant ("a row may only claim `active` if its Script and Spec both exist on
disk"). Fixed by changing `Status` to `draft` (matching the `notebooklm-report` precedent for an
unspecced-but-built workflow). Re-check confirmed the fix and returned a final PASS for SC-5.

The validator separately adjudicated a design tension the implementer flagged proactively (see
Deviations below) and accepted it as satisfying SC-3's intent.

The validator also flagged one **non-blocking** quality concern for a follow-up: `resolvePath()`'s
`process.cwd()` call has no precedent elsewhere in `.claude/workflows/*.js`, and the
`workflow-authoring` SKILL.md's documented runtime-injected symbol list doesn't include `process`
— so whether the production Workflow runtime actually exposes Node's `process` global is
unconfirmed. This does not affect any of SC-1..SC-5 (the default path is absolute and short-circuits
before `process.cwd()` is ever called), so it did not block the gate, but it is a real open question
before any caller passes a *relative* `A.repo`/`A.tmp_dir`/`A.rf_bin` override in production.

## Files Changed

- `.claude/workflows/rf-run-execute.js` — 4 hard-coded constants parameterized; `dry_run`
  short-circuit added; `resolvePath()`/`stampFromTimestamp()` helpers added. All ~20 downstream
  template usages of `RF`/`REPO`/`TMP`/`STAMP` needed no changes (same identifiers).
- `.claude/specs/workflows/workflow-registry.md` — new `rf-run-execute` row (Status: `draft`,
  Spec: none-yet-authored) documenting the new config surface; `updated:` frontmatter bumped.

## Deviations & Risks

- **SC-3 wording tension (adjudicated, accepted).** SC-3 reads "No literal absolute machine paths
  remain (grep-verifiable)." A literal `grep -n "'/Users/"` still returns 3 matches — the fallback
  defaults inside `A.x || '/Users/...'` expressions. A zero-match grep is mathematically
  incompatible with the phase's own, equally explicit requirement that "all args have sensible
  defaults (current behavior on this machine)" and the plan's Risk Mitigation section
  ("backward-compat default config reproduces current behavior on this machine") — no orchestrator
  update landed in this phase to make callers always pass the new args, so dropping the defaults
  would break existing production usage today. The validator judged SC-3 satisfied in spirit: no
  *unconditional* hard-coded path remains; all three literals live only inside documented
  fallback-default expressions. Flagged here for visibility rather than treated as silently
  resolved.
- **Follow-up (non-blocking):** confirm whether the Workflow runtime exposes Node's `process`
  global before any caller relies on `resolvePath()`'s relative-path branch (`process.cwd()`) in
  production — see Validator Verdict above. No action taken this phase; recorded as an open item.
- No scope changes. No Mode D triggers encountered.

## Commits

- None from this phase owner. Per this run's dispatch (`Isolation: none` — session runs inside an
  already-established worktree/branch), the orchestrator commits at wave boundaries, not the
  phase-owner. Working-tree changes are left uncommitted on the current branch for the orchestrator
  to pick up: `.claude/workflows/rf-run-execute.js`, `.claude/specs/workflows/workflow-registry.md`,
  `.claude/progress/rf-upstream-evidence-foundry/phase-5-progress.md`, this completion note.
