---
type: progress
schema_version: 2
doc_type: progress
prd: reusable-assertion-ledger
feature_slug: reusable-assertion-ledger
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-5-catalog-search-api.md
execution_model: sequential
phase: 5
title: P4 Catalog Search and API
status: complete
created: '2026-07-14T16:21:33Z'
started: '2026-07-14T16:05:45Z'
updated: '2026-07-14T17:50:43Z'
commit_refs:
- aa380acb076917de1bc7ccbd49f6027e691825f7
- a1927006ae589f135742ff528f5f9e5a73f859c4
- cb94f9962cfc2c296b25d163c9ec25d4a9ec60bc
- 35f3fc3d3b8f8f34e26d7a70fce69b7b53077aec
pr_refs: []
overall_progress: 100
completion_estimate: complete
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
owners:
- phase-5-terra-writer
contributors: []
model_usage:
  primary: gpt-5.6-terra
  external: []
tasks:
- id: P4-001
  description: Build a rebuildable workspace-qualified assertion projection with policy-first lexical filters, facets, deterministic bounded cursors, and safe aggregate semantics.
  status: completed
  assigned_to: [phase-5-terra-writer]
  dependencies: [P3-REVIEW]
  estimated_effort: 3 pts
  priority: high
  assigned_model: gpt-5.6-terra
  model_effort: high
  acceptance_criteria: [P4-PACKET]
  started: '2026-07-14T16:05:45Z'
  completed: '2026-07-14T16:20:55Z'
  evidence:
  - 'artifact: src/research_foundry/services/assertion_catalog.py'
  - 'test: tests/unit/test_assertion_catalog.py'
  - 'validation: focused Phase 5 and regression pytest suite passed 58 tests'
  verified_by: [P4-REVIEW]
- id: P4-002
  description: Add governed assertion search, detail packet, and lineage endpoints with fail-closed identity, workspace, rights, passage, and edition context.
  status: completed
  assigned_to: [phase-5-terra-writer]
  dependencies: [P4-001]
  estimated_effort: 3 pts
  priority: high
  assigned_model: gpt-5.6-terra
  model_effort: high
  acceptance_criteria: [P4-PACKET]
  started: '2026-07-14T16:05:45Z'
  completed: '2026-07-14T16:20:55Z'
  evidence:
  - 'artifact: src/research_foundry/api/routers/assertions.py'
  - 'artifact: src/research_foundry/api/app.py'
  - 'test: tests/integration/test_assertions_api.py'
  - 'validation: workspace and RBAC no-leak regressions passed'
  verified_by: [P4-REVIEW]
- id: P4-003
  description: Publish policy reason codes and optional packet fields through OpenAPI and generated TypeScript while preserving legacy missing-field behavior.
  status: completed
  assigned_to: [phase-5-terra-writer]
  dependencies: [P4-001, P4-002]
  estimated_effort: 2 pts
  priority: high
  assigned_model: gpt-5.6-terra
  model_effort: high
  acceptance_criteria: [P4-PACKET]
  started: '2026-07-14T16:05:45Z'
  completed: '2026-07-14T16:20:55Z'
  evidence:
  - 'artifact: src/research_foundry/api/openapi.json'
  - 'artifact: frontend/runs-viewer/codegen/generate-types.mjs'
  - 'artifact: frontend/runs-viewer/src/types/rf/assertions_api.generated.ts'
  - 'test: frontend/runs-viewer/codegen/generate-types.contract.test.mjs'
  - 'validation: live OpenAPI equality passed for assertion routes and DTOs'
  - 'validation: runs-viewer codegen check passed 27 of 27 schemas'
  - 'validation: runs-viewer TypeScript no-emit checks passed'
  - 'validation: Ruff, focused mypy, AC dry-check, and git diff --check passed'
  verified_by: [P4-REVIEW]
- id: P4-REVIEW
  description: Independent task-completion-validator review of P4-001 through P4-003 and AC P4-PACKET against the exact candidate tree.
  status: completed
  assigned_to: [task-completion-validator]
  dependencies: [P4-003]
  estimated_effort: review gate
  priority: critical
  assigned_model: gpt-5.6-terra
  model_effort: high
  acceptance_criteria: [P4-PACKET]
  started: '2026-07-14T16:23:13Z'
  completed: '2026-07-14T17:50:43Z'
  evidence:
  - 'reviewer_task: 019f6170-4abe-75c3-83e2-5e907367b0ef'
  - 'stale_approval_checkpoint: aa380acb076917de1bc7ccbd49f6027e691825f7'
  - 'stale_approval_tree: 583f3fc689ce0e795c6083eab49a76c8af586a9e'
  - 'stale_reason: Tier-3 reviewer 019f6197-3796-7853-93b8-14a47fd1bc06 rejected the later exact tree 19eaa7d7b6c2782882e4ee483741236a8d85962c for the missing OpenAPI-to-TypeScript assertion seam and app.py Ruff regression'
  - 'remediation_checkpoint: cb94f9962cfc2c296b25d163c9ec25d4a9ec60bc'
  - 'lint_followup_checkpoint: 35f3fc3d3b8f8f34e26d7a70fce69b7b53077aec'
  - 'reviewer_checkpoint: e573f7174f1908a821da29b6519ee82b0f6675a2'
  - 'reviewer_tree: 6aed821184ee9433e5a61b2b8b23374bbc2a1d40'
  - 'reviewer_verdict: Physical Phase 5 logical P4 APPROVE with no findings'
  verified_by: [019f6170-4abe-75c3-83e2-5e907367b0ef]
parallelization:
  batch_1: [P4-001]
  batch_2: [P4-002]
  batch_3: [P4-003]
  batch_4: [P4-REVIEW]
  critical_path: [P4-001, P4-002, P4-003, P4-REVIEW]
  estimated_total_time: 8 pts plus independent review
blockers:
- id: P4-BLOCKER-001
  title: Feature enablement remains prohibited by the conditional P0 evidence boundary
  severity: high
  blocking: [RF_ASSERTION_LEDGER_ENABLED, RF_ASSERTION_REUSE_ENABLED, RF_CANONICAL_CLAIMS_ENABLED]
  resolution: Preserve assertion-only and P0-conditional restrictions until the named corpus and upstream gates authorize enablement.
success_criteria:
- id: AC-P4-PACKET
  description: Authorized workspace and policy context are applied before query execution, while missing context returns typed denial without content, counts, candidates, or membership hints.
  status: completed
  maps_to: [P4-001, P4-002, P4-003, P4-REVIEW]
notes:
- Physical Phase 5 is logical P4; document and tracker numbering use the physical phase number.
- The projection is derived and rebuildable. Immutable ledger and run artifacts remain authoritative.
- Vector and graph retrieval are absent from the deployed path.
- No feature flag was enabled and no live, private-provider, writeback, canonical-claim, or Phase 6 path was exercised.
- The former approval at `aa380acb076917de1bc7ccbd49f6027e691825f7` is stale after the Tier-3 rejection on `19eaa7d7b6c2782882e4ee483741236a8d85962c`.
- Remediation commits `a1927006ae589f135742ff528f5f9e5a73f859c4` and `cb94f9962cfc2c296b25d163c9ec25d4a9ec60bc` add the OpenAPI-driven assertion TypeScript contract and normalize generated output.
- Reviewer `019f6170-4abe-75c3-83e2-5e907367b0ef` approved exact checkpoint `e573f7174f1908a821da29b6519ee82b0f6675a2` at tree `6aed821184ee9433e5a61b2b8b23374bbc2a1d40` with no findings.
files_modified:
- src/research_foundry/services/assertion_catalog.py
- src/research_foundry/api/routers/assertions.py
- src/research_foundry/api/app.py
- src/research_foundry/api/openapi.json
- tests/unit/test_assertion_catalog.py
- tests/integration/test_assertions_api.py
- frontend/runs-viewer/codegen/generate-types.mjs
- frontend/runs-viewer/codegen/generate-types.contract.test.mjs
- frontend/runs-viewer/package.json
- frontend/runs-viewer/src/types/rf/assertions_api.generated.ts
- frontend/runs-viewer/src/types/rf/generated.ts
---

# Reusable Assertion Ledger — Phase 5 (P4): Catalog, Search, and API

## Independent approval recorded

P4-001 through P4-003 remain implemented, with remediation ending at
`cb94f9962cfc2c296b25d163c9ec25d4a9ec60bc`. The candidate adds a
rebuildable, workspace-qualified assertion projection and
governed search, packet, and lineage endpoints. Identity, workspace, rights,
passage, and edition context are evaluated before content, candidates, counts,
facets, or membership signals are returned.

The prior approval became stale after Tier-3 findings. Those findings are
remediated, and reviewer task `019f6170-4abe-75c3-83e2-5e907367b0ef` approved
exact checkpoint `e573f7174f1908a821da29b6519ee82b0f6675a2` at tree
`6aed821184ee9433e5a61b2b8b23374bbc2a1d40` with no findings.

## Validation evidence

- Focused Phase 5 plus P3/P1/RBAC regression selection: 58 passed.
- Ruff and focused mypy passed.
- Live OpenAPI equality passed for all assertion routes and DTOs.
- Runs-viewer codegen check passed for 27 of 27 schemas.
- Runs-viewer TypeScript no-emit checks passed.
- AC dry-check and `git diff --check` passed.
- OpenAPI-driven assertion types and their committed-output contract test pass
  through the saved checkout dependency tree.

## Boundary

All assertion-ledger, reuse, and canonical-claim feature flags remain disabled.
The result preserves the assertion-only/P0-conditional contract and does not
claim live, private-provider, writeback, canonical-claim, or Phase 6 evidence.
