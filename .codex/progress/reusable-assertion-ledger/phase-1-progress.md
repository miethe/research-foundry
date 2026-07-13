---
type: progress
schema_version: 2
doc_type: progress
prd: reusable-assertion-ledger
feature_slug: reusable-assertion-ledger
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
execution_model: sequential
phase: 1
title: P0 Research Gates
status: complete
started: '2026-07-13'
completed: '2026-07-13T14:56:38Z'
updated: '2026-07-13'
commit_refs: []
pr_refs: []
overall_progress: 100
completion_estimate: complete
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
owners:
- phase-0-sole-writer
contributors:
- task-completion-validator
- karen
model_usage:
  primary: sonnet
  external: []
tasks:
- id: P0-001
  description: Publish frozen local replay fixture result, exact denominators, and
    conditional corpus-access boundary.
  status: completed
  assigned_to:
  - phase-0-sole-writer
  dependencies: []
  estimated_effort: 3 pts
  priority: high
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-13T00:00:00Z'
  completed: '2026-07-13T04:28:31Z'
  evidence:
  - test: tests/test_reusable_assertion_ledger_phase0.py
  - artifact: docs/project_plans/SPIKEs/reusable-assertion-ledger-historical-replay-results.md
  verified_by:
  - P0-004
- id: P0-002
  description: Publish deterministic identity/lineage and merge-fallback result using
    the frozen fixture contract.
  status: completed
  assigned_to:
  - phase-0-sole-writer
  dependencies: []
  estimated_effort: 3 pts
  priority: high
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-13T00:00:00Z'
  completed: '2026-07-13T04:28:31Z'
  evidence:
  - test: tests/test_reusable_assertion_ledger_phase0.py
  - artifact: docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-results.md
  verified_by:
  - P0-004
- id: P0-003
  description: Publish local dependency-graph propagation result with complete enumeration
    and idempotence checks.
  status: completed
  assigned_to:
  - phase-0-sole-writer
  dependencies:
  - P0-002
  estimated_effort: 1 pt
  priority: high
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-13T00:00:00Z'
  completed: '2026-07-13T04:28:31Z'
  evidence:
  - test: tests/test_reusable_assertion_ledger_phase0.py
  - artifact: docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-results.md
  verified_by:
  - P0-004
- id: P0-004
  description: Reconcile all Phase 0 results into P1-P5 restrictions, flags, fallback
    scope, and stop conditions.
  status: completed
  assigned_to:
  - phase-0-sole-writer
  dependencies:
  - P0-001
  - P0-002
  - P0-003
  estimated_effort: 1 pt
  priority: high
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-13T00:00:00Z'
  completed: '2026-07-13T04:28:31Z'
  evidence:
  - artifact: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-1-research-gates.md
  - test: tests/test_reusable_assertion_ledger_phase0.py
  - artifact: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-1-research-gates.md
  verified_by:
  - P0-GATES
- id: P0-GATES
  description: Independent task-completion-validator and Karen review of AC P0-GATES;
    not self-approved by the writer.
  status: completed
  assigned_to:
  - task-completion-validator
  - karen
  dependencies:
  - P0-004
  estimated_effort: review gate
  priority: critical
  assigned_model: sonnet
  model_effort: extended
  acceptance_criteria:
  - P0-GATES
  started: '2026-07-13T14:56:38Z'
  completed: '2026-07-13T14:56:38Z'
  evidence:
  - review: Luna task-completion-validator Extra High APPROVE; thread 019f5be0-927b-7aa2-9381-d5dbff8d8df3; tree a2831f8d641703dd92e7dbf88a7bf14e172f015d
  - review: Karen Tier-3 Terra Extra High APPROVE; thread 019f5be0-96d9-7f50-8ffe-4bc3ff3d1619; tree a2831f8d641703dd92e7dbf88a7bf14e172f015d
  verified_by:
  - task-completion-validator
  - karen
parallelization:
  batch_1:
  - P0-001
  - P0-002
  batch_2:
  - P0-003
  batch_3:
  - P0-004
  batch_4:
  - P0-GATES
  critical_path:
  - P0-002
  - P0-003
  - P0-004
  - P0-GATES
  estimated_total_time: 8 pts plus independent review
blockers:
- id: P0-BLOCKER-001
  title: Representative private-corpus and concluded upstream-contract evidence unavailable for empirical go and feature enablement
  severity: high
  blocking:
  - empirical-go
  - RF_ASSERTION_LEDGER_ENABLED
  - RF_ASSERTION_REUSE_ENABLED
  - RF_CANONICAL_CLAIMS_ENABLED
  resolution: Run approved read-only replay and consume concluded citation, segmentation, and contradiction contracts before feature enablement; this does not prevent reviewers from approving the bounded conditional P0 result and reduced assertion-only scope.
success_criteria:
- id: AC-P0-GATES
  description: Each result records fixture, method, observed thresholds, verdict,
    unresolved risks, and P1-P5 restrictions.
  status: completed
  maps_to:
  - P0-001
  - P0-002
  - P0-003
  - P0-004
  - P0-GATES
files_modified:
- tests/fixtures/assertion_ledger/phase0_fixture_manifest.json
- tests/fixtures/assertion_ledger/phase0_rf_evidence_source.md
- tests/fixtures/assertion_ledger/phase0_rf_metrics_source.md
- tests/fixtures/assertion_ledger/phase0_propagation_expected_manifest.json
- tests/fixtures/assertion_ledger/enrich_phase0_rf_source_cards.py
- tests/fixtures/assertion_ledger/run_phase0_rf_evidence.sh
- tests/fixtures/assertion_ledger/rf_phase0_evidence_snapshot/
- tests/test_reusable_assertion_ledger_phase0.py
- docs/project_plans/SPIKEs/reusable-assertion-ledger-historical-replay-results.md
- docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-results.md
- docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-results.md
- docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-1-research-gates.md
progress: 100
---

# Reusable Assertion Ledger — Phase 1 (P0): Research Gates

Phase 0 is complete following independent reviewer approval. The tracked task
IDs intentionally remain `P0-*` because the governing phase plan declares
`phase: 1`, `phase_id: P0`.

## Evidence and review state

- The fixture harness is deterministic and local-only; it has no production,
  shared-data, network, or connector side effect.
- P0-001 through P0-004 are complete with recorded local evidence.
- `P0-GATES` is complete: both independent reviewers approved the exact
  candidate tree recorded below.
- Missing representative private-corpus and concluded upstream-contract evidence
  blocks empirical `go` and feature-flag enablement only. It does not reopen or
  block this completed bounded conditional P0 result and reduced assertion-only
  scope.

## Independent review closeout

- **Luna, task-completion-validator, Extra High:** `APPROVE` on tree
  `a2831f8d641703dd92e7dbf88a7bf14e172f015d`; thread
  `019f5be0-927b-7aa2-9381-d5dbff8d8df3`.
- **Karen, Tier-3 Terra, Extra High:** `APPROVE` on tree
  `a2831f8d641703dd92e7dbf88a7bf14e172f015d`; thread
  `019f5be0-96d9-7f50-8ffe-4bc3ff3d1619`.

## Validation record

| Command | Result |
|---|---|
| `./.venv/bin/python tests/test_reusable_assertion_ledger_phase0.py` | Deterministic summary: 12 runs, 120 inputs, 36/144 safe fixture reuse, 36/36 provenance, 1,440 identity comparisons, 120/120 impact objects. |
| `./.venv/bin/python -m pytest tests/test_reusable_assertion_ledger_phase0.py -q` | Passed: 4 tests. |
| `./.venv/bin/python -m ruff check tests/test_reusable_assertion_ledger_phase0.py` | Passed. |
| `./.venv/bin/python -m mypy --ignore-missing-imports tests/test_reusable_assertion_ledger_phase0.py` | Passed: no issues in 1 source file. |
| Six-file regression slice for pipeline, verifier, writebacks, export round-trip, and workspace isolation | Passed: 103 tests (with existing FastAPI/TestClient deprecation warnings). |
| Artifact validation and P0 AC coverage | Passed for this tracker and the three result reports; `P0-GATES -> P0-004` coverage is complete. |
| `./.venv/bin/python -m pytest -q` | Not green: rerun with `-x` stops at existing API surface failure `tests/test_serve_api.py::test_get_run_detail_known_run_returns_200` (expected 200, observed 404). Not changed in this research-scoped phase. |

## RF local evidence record

**Committed snapshot path:**
`tests/fixtures/assertion_ledger/rf_phase0_evidence_snapshot/`.
It contains the two successful local RF source cards, the 16-supported-claim
ledger (`claims/claim_ledger.yaml`), deterministic 16-tag report
(`reports/report_draft.md`), and passing verification record
(`reviews/verification.yaml`, `exit_code: 0`). The ignored `runs/` directory is
only the local rebuild location; the checked-in fixture snapshot is the durable
review evidence.

| Step | Exact command / result |
|---|---|
| Governance | `./.venv/bin/rf guard check --profile default` — exit 0. |
| Initial stop | First local script attempt used invalid `--source-type fixture`; `rf ingest` stopped with source-card schema validation before extract, claim-map, synthesize, or verify. It was corrected to `personal_note`. |
| Successful local rebuild | `zsh tests/fixtures/assertion_ledger/run_phase0_rf_evidence.sh` — guard 0; ingest 2 local source cards; run `enrich_phase0_rf_source_cards.py` before extraction to add three synthetic/private-corpus/merge-safety limitations to each card; extract 2 cards; claim-map 16 supported claims; deterministic synthesize 16 tags; verify 0. |
| Verification | `./.venv/bin/rf verify rf_run_reusable_assertion_ledger_p0_fixture_v1 --fail-on-unsupported` — exit 0. No `rf verify` invocation exited nonzero. |
| Explicit skips | No `rf replay` command exists. `rf swarm run`, `rf fetch`, `rf bundle`, publish, `rf writeback`, and CCDash telemetry were skipped; no external action or telemetry artifact remains. |

All material fixture quantities in the P0 results map to the snapshot source
cards and claim ledger (`clm_001`–`clm_016`) or to the deterministic harness and
independently authored propagation expected manifest; calculated rates/deltas
and collision observations are explicitly labeled inference, and quality
regression is explicitly unmeasured. The result stays `conditional`, with `RF_ASSERTION_LEDGER_ENABLED`,
`RF_ASSERTION_REUSE_ENABLED`, and `RF_CANONICAL_CLAIMS_ENABLED` disabled.
