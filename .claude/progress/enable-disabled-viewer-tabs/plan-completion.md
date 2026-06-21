---
type: report
schema_version: 2
doc_type: report
report_category: plan-completion
feature_slug: enable-disabled-viewer-tabs
status: completed
created: 2026-06-21
updated: 2026-06-21
prd_ref: docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
commit_refs: [0235b47, 6c2060c, 9acd360]
pr_refs: []
---

# Plan Completion — Enable Disabled Viewer Tabs (Wave 2)

## Summary

The remaining three Feature Contracts of the `enable-disabled-viewer-tabs` sub-epic
(Wave 2) were executed as sequential Tier-1 autonomous sprints, each validated, reviewed,
and squash-committed to `main`. With Wave 1 (Settings/Help/Alerts) already shipped, **all six
previously-disabled navigation tabs are now enabled** — zero `'not implemented'` guards remain
in `AppShell.tsx NAV_ITEMS`.

## Per-Contract Results

| Tab | Contract | Route | Commit | Reviewer | New tests |
|-----|----------|-------|--------|----------|-----------|
| G1 Swarm | viewer-tab-swarm.md | `/runs/:runId/swarm` (contextual) | `0235b47` | APPROVED (1st pass) | 23 |
| G2 Policies | viewer-tab-policies.md | `/policies` | `6c2060c` | APPROVED (1st pass) | 26 |
| G4 Library | viewer-tab-library.md | `/library` | `9acd360` | CHANGES_REQUESTED → fixed → APPROVED | 33 |

Test suite grew 433 → 515 (+82). Each commit: `tsc -b` clean, `vitest run` green,
`eslint --max-warnings=0` clean.

## Execution Notes

- **Sequential, not parallel.** All three contracts touch the shared files `AppShell.tsx`
  (NAV_ITEMS) and `app/routes.tsx` / `app/App.tsx`. Running them sequentially (each executor
  inheriting the prior's committed shared-file edits) satisfied the epic's locked "single
  coordination per wave" intent while also meeting the directive to squash-commit each contract
  to `main` independently. No merge conflicts; final integrated tree compiles with all routes
  registered.
- **G2 vertical slice.** The Policies contract intentionally included a minimal backend/build
  touch per its `files_affected` + AC-4: `export_service.py` threads `allowed_writebacks` /
  `requires_human_review` from `run.yaml` governance (guarded, additive), and
  `prebuild-static-data.mjs` emits `public/data/governance.json`. Python export round-trip +
  schema-validation tests pass with the new keys.
- **G4 remediation.** Reviewer caught an AC G4-7 gap (reusable-output run links rendered without
  the stale-run `inIndex` guard). Sent back to the same executor (context preserved); fix added
  the guard across all three sections + a stale-run test, then re-validated.

## Known / Pre-existing Issues (not introduced by this work)

- **Sensitivity redaction (pre-existing).** 4 tests in `tests/unit/test_sensitivity_redaction.py`
  + `test_export_service.py` fail identically on unmodified `main` (secret quotes not redacted at
  the default `public` threshold). Unrelated to these contracts (redaction logic untouched);
  flagged for separate triage.
- **PoliciesScreen `useQuery`-in-`.map()`** — contract-permitted and an established sibling
  pattern; recommended follow-up to migrate to `useQueries` for rules-of-hooks robustness.
- **Static bundle not re-exported.** Per the Wave-2 Unblock Gate, the live `public/data` bundle
  must be regenerated (F5 re-export) for Swarm/Policies to show real (vs empty-state) data. All
  three tabs degrade gracefully until then; re-export is a deploy-time operator step.

## Reviewer Gate

Each contract passed its Tier-1 `task-completion-validator` gate (Mode E). A separate epic-level
`karen` pass was not run — the epic is an index of independently-reviewed Tier-1 features, and a
cross-cutting integration sanity check (all nav enabled, integrated `tsc`/`vitest`/`lint` green)
was performed in its place.
