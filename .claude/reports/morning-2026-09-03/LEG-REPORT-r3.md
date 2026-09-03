# LEG-REPORT — R3 primary-checkout deploy (2026-09-03)

Codex leg ran in the primary `research-foundry` checkout (not this worktree) and deployed all 10
drift agent rows via `skillmeat deploy … --overwrite`. This session independently re-verified the
claims from the leg's transcript and the primary checkout's own ledger/git state; nothing here is
copied from the leg's unverified self-report.

## Verified

- **10/10 agents**: each deployed file's `sha256sum` matches the Enterprise ledger `content_hash`
  in `research-foundry/.claude/.skillmeat-deployed.toml` (all deployed `2026-09-03T16:36:4x/5x`).
  All 10 deploy calls exited 0; no `#6` baseline-guard refusal.
- **Reconcile**: `181/34/24/17` (pre) → `181/34/24/16` (post; expected/present/gaps/drift, exit 2)
  — drift down by 1.
- **`delegation-router`**: untouched — `git status --short` in the primary checkout carries no
  delegation-router entry.

## Correction to the leg's claim

The leg reported **six** `source_store_stale` warnings. Re-parsing its own captured deploy output
found **seven**: backend-architect, changelog-generator, data-layer-expert, documentation-expert,
documentation-writer, feature-sprint-executor, search-specialist. Only a11y-sheriff and
task-completion-validator deployed with no warning.

## Remains open

5 no-ledger skill drift rows, 9 context/spec type-mapping rows, 14 genuine catalog gaps, the
dev-execution merge-selection decision, and now a catalog-refresh decision for the 7 (not 6)
source-store-stale rows.

## Sandbox limitation

The Codex leg's sandbox refused writes outside the primary checkout, so it could not append to
this worktree's reports — this file and the close-report addendum were written here instead, from
the leg's transcript, independently reverified.
