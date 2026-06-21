---
schema_version: 2
doc_type: report
report_category: plan_completion
title: "Plan Completion: Run Metadata Enrichment (v1)"
status: completed
created: 2026-06-21
updated: 2026-06-21
feature_slug: run-metadata-enrichment
feature_version: "v1"
plan_ref: docs/project_plans/implementation_plans/features/run-metadata-enrichment-v1.md
prd_ref: docs/project_plans/PRDs/features/run-metadata-enrichment-v1.md
tier: 3
merge_branch: main
---

# Plan Completion — Run Metadata Enrichment (v1)

Tier 3 feature executed end-to-end via `/dev:execute-plan` in an isolated worktree
(`feat/run-metadata-enrichment-v1`, branched from local `HEAD` 69b0960 so it carried the
just-committed plan), then squash-merged to `main`. Because this repo has no `phase-owner` agent,
Opus orchestrated directly and dispatched the plan's named implementer agents
(`python-backend-engineer`, `ui-engineer-enhanced`, `frontend-developer`, `documentation-writer`,
`changelog-generator`) through wave-scoped dynamic workflows, each phase gated by an adversarial
`task-completion-validator` with a ≤2-cycle remediation loop.

## Wave Execution Summary

| Wave | Phases | Outcome |
|------|--------|---------|
| Backend A | P1 schema+contract+TS types → [P2 backfill ∥ P3 creation] → P4 export+FE types | all passed, 0 remediation cycles |
| Frontend B | [P5 display ∥ P7-backend enrichment] → [P6 filtering ∥ P7-fe widgets] | all passed, 0 remediation cycles |
| Tests/Docs C | P8a python tests ∥ P8b FE smoke + a11y ∥ P8c docs ∥ P8d changelog | all passed |

Schedule note: the plan's `[P5,P7]` wave was internally serialized on `RunDetailWorkspace.tsx`
(the one wave-internal file overlap); the workflow split P7 into backend (export) and FE (widgets)
so `P5 ∥ P7-backend` then `P6 ∥ P7-fe` ran with disjoint file ownership.

## Final Validation (authoritative, post-remediation)

- Python: **534 pytest pass**, `ruff` clean. Includes a strict Draft7 schema-validation regression
  test (`test_export_run_passes_strict_json_schema_validation`) that validates a real `export_run()`
  output against `rf-run-export-schema.json` under `additionalProperties:false`.
- Frontend: `tsc -b` clean, `eslint --max-warnings=0` clean, **244 vitest pass** (incl. 35 render
  smoke tests across all surfaces with populated + null-metadata fixtures, and run-title regression
  guards).
- Backfill: **18 runs** carry `linked_projects`/`category`/`tags`/`backlog_idea_ref`(RIB-NNN)/
  `backlog_idea_id`; `run_index.yaml` derived from `run.yaml`; **0 schema-pattern violations**.

## Tier 3 Reviewer Gate (3 diverse lenses)

Round 1 → **CHANGES_REQUESTED**. The diverse-lens gate caught two real issues the per-phase
verifiers missed:
- **karen (blocker):** run-title regression — making Linked Projects primary had deleted the
  human-readable run title from the export contract and RunCard (cards showed raw slugs). Violated
  the plan's own EXP-002/DISP-002 AC.
- **architecture (blocker):** P2 backfill wrote `backlog_idea_ref` as the idea-id slug, violating
  the schema's `^RIB-\d+$` pattern across all 18 runs.

Remediation cycle 1 restored the title end-to-end + fixed `backlog_idea_ref` (RIB-NNN) and re-backfilled,
and closed reviewer-flagged gaps (`list_runs()` metadata, `plan_run()` run_index consistency,
`writebacks` emission, `_context_summary` allowlist hardening).

Round 2 → karen **APPROVED**; architecture found two follow-on contract-consistency blockers
(`writebacks` emitted as list vs the `RFRunWritebacksSummary` object expected by schema/TS/FE; schema
top-level missing `title`/`cost_usd`/`model_profiles`/`source_count_by_type` under
`additionalProperties:false`). Remediation cycle 2 aligned `writebacks` to the object shape, added the
missing schema fields + the strict-validation regression test, and broadened the FE
`schemaMismatch` guard to accept `1.2`.

Final → **karen ✅ · correctness ✅ · architecture ✅ (VERDICT: APPROVED)**.

## Commits (18, squashed to main)

P1 `b144147` · P3 `df91406` · P2 `dbd9ced` · P4 `9131b31` · gitignore `066dd98` ·
P7b `0d4defb` · P5 `32c7c79` · P6 `36b9be1` · P7f `7829a58` · changelog `f9da3d3` ·
schema docs `8cb4a99` · P8 py-tests `b3f7823` · P8 FE-tests `af55eaa` ·
fix title FE `f1ea43e` · fix export `7de8912` · fix types `b5943fa` ·
fix schema-version `58231e8` · fix writebacks/schema `27f04b7`.

Scope: 56 files, +5934/−617.

## Known Follow-ups (adjudicated NON-blocking)

1. `services/planning.py` reviewers-list `profile_key: None` mypy `[dict-item]` error is **pre-existing
   on main**, unrelated to this feature; left untouched (mypy is not a project quality gate).
2. `writebacks.targets[].status` is a presence-only signal (`"present"`), not a true success/failed
   status — coherent with ENR-004 scope; FE consumers should not infer success from it.
3. `_context_summary` uses explicit allowlists; extend the frozensets if `routing_decision.yaml` /
   `swarm_plan.yaml` schemas gain new fields.
4. `frontend/runs-viewer/src/lib/runs.ts` `KNOWN_VALID_SCHEMA_VERSIONS` must be updated on the next
   `schema_version` bump.
5. `public/data` is gitignored and rebuilt at deploy — a fresh `pnpm build:runs-viewer` (done by the
   node bootstrap) is required for the deployed bundle to carry the new metadata + enrichment fields.
6. Minor: `model_profiles.max_cost_usd` can duplicate `cost_usd` (harmless); no direct unit test on
   `summarizeRunAttention().schemaMismatch` (covered indirectly).

## Deviation from `/dev:execute-plan` defaults

- No `phase-owner` agent exists in this repo; Opus orchestrated and dispatched the plan's named
  implementer agents directly (consistent with the Opus-delegation principle and P15 plain-dispatch
  invariant — no Agent Teams primitives used).
- Per-phase `.claude/progress/*-progress.md` YAML was not generated; phase outcomes are captured by
  the workflow verdicts + this report + git history. Execution used dynamic workflow orchestration
  (ultracode) rather than per-phase progress-YAML polling.
