---
type: progress
schema_version: 2
doc_type: progress
prd: reusable-assertion-ledger
feature_slug: reusable-assertion-ledger
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-8-evaluation-hardening.md
execution_model: sequential
phase: 8
title: P7 Evaluation and Hardening
status: completed
created: '2026-07-14T00:00:00Z'
started: '2026-07-14T00:00:00Z'
updated: '2026-07-15T03:00:00Z'
completed: '2026-07-15T03:00:00Z'
commit_refs:
- f5ce6ae004b7a83970320e4ec6f992cb1e8ed68a
- d6f3fe1ad01b53907aab6ad949941fe0a62f7673
pr_refs: []
overall_progress: 100
completion_estimate: completed
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
owners:
- codex-p7-writer
contributors: []
model_usage:
  primary: gpt-5
  external: []
tasks:
- id: P7-001
  description: Gold-set compatibility coverage for exact assertion identity, grounding,
    qualifier preservation, legacy optional fields, and packet completeness.
  status: completed
  assigned_to:
  - codex-p7-writer
  dependencies:
  - P5-REVIEW
  - P6-REVIEW
  estimated_effort: 3 pts
  priority: critical
  acceptance_criteria:
  - RAL-PACKET
  - P7-SMOKE
  evidence:
  - tests/integration/test_assertion_ledger_evaluation.py
  - test: tests/integration/test_assertion_ledger_evaluation.py
  started: '2026-07-14T00:00:00Z'
  completed: '2026-07-14T01:00:00Z'
  verified_by:
  - Terra-Tier-3
- id: P7-002
  description: Isolation coverage proves denial payloads contain no candidate-derived
    signals and prompt-shaped source text cannot alter governed reuse decisions.
  status: completed
  assigned_to:
  - codex-p7-writer
  dependencies:
  - P7-001
  estimated_effort: 2 pts
  priority: critical
  acceptance_criteria:
  - RAL-ISOLATION
  evidence:
  - tests/integration/test_assertion_ledger_evaluation.py
  - test: tests/integration/test_assertion_ledger_evaluation.py
  started: '2026-07-14T01:00:00Z'
  completed: '2026-07-14T02:00:00Z'
  verified_by:
  - Terra-Tier-3
- id: P7-003
  description: Deterministic local p95 search budget, projection rebuild, interruption/resume,
    and reuse-off recovery are rehearsed with no external writeback.
  status: completed
  assigned_to:
  - codex-p7-writer
  dependencies:
  - P7-001
  estimated_effort: 2 pts
  priority: high
  acceptance_criteria:
  - RAL-LIFECYCLE
  evidence:
  - tests/integration/test_assertion_ledger_evaluation.py
  - tests/integration/test_assertion_reuse.py
  - test: tests/integration/test_assertion_ledger_evaluation.py
  started: '2026-07-14T01:00:00Z'
  completed: '2026-07-14T03:00:00Z'
  verified_by:
  - Terra-Tier-3
- id: P7-004
  description: Local synthetic production API/viewer smoke covers Catalog, Claim Audit,
    Provenance, Lineage, and Run Detail at desktop width, with legacy-missing, denied,
    stale, and assertion-only fixtures.
  status: completed
  assigned_to:
  - codex-p7-writer
  dependencies:
  - P7-001
  - P7-002
  - P7-003
  estimated_effort: 1 pt
  priority: critical
  acceptance_criteria:
  - P7-SMOKE
  - RAL-ISOLATION
  - RAL-PACKET
  evidence:
  - tests/fixtures/assertion_ledger/prepare_p7_runtime_fixture.py
  - frontend/runs-viewer/e2e/p7-runtime-smoke.mjs
  - tests/fixtures/assertion_ledger/p7_runtime_evidence/runtime-results.json
  - test: tests/fixtures/assertion_ledger/p7_runtime_evidence/runtime-results.json
  started: '2026-07-14T03:00:00Z'
  completed: '2026-07-14T04:00:00Z'
  verified_by:
  - Terra-Tier-3
- id: P7-REVIEW
  description: Independent exact-tree review by task-completion-validator and Karen
    is required before phase completion.
  status: completed
  assigned_to:
  - task-completion-validator
  - karen
  dependencies:
  - P7-001
  - P7-002
  - P7-003
  - P7-004
  estimated_effort: review gate
  priority: critical
  acceptance_criteria:
  - P7-SMOKE
  - RAL-ISOLATION
  - RAL-PACKET
  - RAL-LIFECYCLE
  completed: '2026-07-15T03:00:00Z'
  verified_by:
  - Terra-Tier-3
  - Sol-final-high-risk-review
  evidence:
  - review: Terra Tier-3 APPROVE at f5ce6ae004b7a83970320e4ec6f992cb1e8ed68a / d6f3fe1ad01b53907aab6ad949941fe0a62f7673
  - review: Sol final high-risk feature review APPROVE at 9cf7e6b8f12cb16d8f755eb50bf8be0d513c0ee1
      / 26e8f77afc2f8fb079f8e49cf2f760844a51214d
  - review: f5ce6ae004b7a83970320e4ec6f992cb1e8ed68a/d6f3fe1ad01b53907aab6ad949941fe0a62f7673
  started: '2026-07-15T02:59:00Z'
parallelization:
  batch_1:
  - P7-001
  batch_2:
  - P7-002
  - P7-003
  batch_3:
  - P7-004
  batch_4:
  - P7-REVIEW
  critical_path:
  - P7-001
  - P7-002
  - P7-004
  - P7-REVIEW
  estimated_total_time: 8 pts plus independent review
blockers: []
success_criteria:
- id: AC-P7-SMOKE
  description: Runtime harness names every P6 target surface and requires authorized
    full, legacy-missing, denied, stale, and assertion-only fixtures.
  status: completed
- id: AC-RAL-ISOLATION
  description: Search and reuse tests deny unauthorized content and derived signals
    before query-derived output exists.
  status: completed
- id: AC-RAL-PACKET
  description: Gold-set packet tests retain exact identity and optional-field compatibility
    without inventing values.
  status: completed
- id: AC-RAL-LIFECYCLE
  description: Projection rebuild and reuse-off recovery remain deterministic and
    preserve the external-writeback denial boundary.
  status: completed
files_modified:
- tests/integration/test_assertion_ledger_evaluation.py
- frontend/runs-viewer/e2e/p7-runtime-smoke.mjs
- tests/fixtures/assertion_ledger/p7_runtime_evidence/
- src/research_foundry/api/__init__.py
runtime_smoke:
  status: synthetic_local_passed
  fixture: tests/fixtures/assertion_ledger/prepare_p7_runtime_fixture.py
  harness: frontend/runs-viewer/e2e/p7-runtime-smoke.mjs
  evidence: tests/fixtures/assertion_ledger/p7_runtime_evidence/runtime-results.json
  browser: system Google Chrome via Playwright
  viewport: 1440x900
  scenarios:
  - full_packet
  - legacy_missing_qualifier_extensions
  - denied_zero_candidate_rows
  - stale_packet
  - assertion_only_lineage
  - provenance_dialog_keyboard_focus
  owner_private_status: not_executed
  command: P7_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google
    Chrome' node e2e/p7-runtime-smoke.mjs /tmp/ral-p7-runtime/p7-runtime-manifest.json
    ../../tests/fixtures/assertion_ledger/p7_runtime_evidence
  prohibited_claims:
  - live_private_approval
  - external_writeback_execution
  - feature_enablement
progress: 100
---

# Reusable Assertion Ledger — Phase 8 (P7): Evaluation and Hardening

The automated gold, isolation, lifecycle, and local synthetic runtime checks
are implemented. Terra approved the exact Phase 8 behavior tree at
`f5ce6ae004b7a83970320e4ec6f992cb1e8ed68a` /
`d6f3fe1ad01b53907aab6ad949941fe0a62f7673`. The smoke uses synthetic local data only;
owner/private authorization and external writeback remain `not_executed`.

## Runtime-smoke handoff

Reproduce the committed local synthetic smoke:

```bash
<saved-python> tests/fixtures/assertion_ledger/prepare_p7_runtime_fixture.py --root /tmp/ral-p7-runtime
# start the production API and two token-configured Vite viewers, then:
cd frontend/runs-viewer
P7_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \\
node e2e/p7-runtime-smoke.mjs /tmp/ral-p7-runtime/p7-runtime-manifest.json \\
  ../../tests/fixtures/assertion_ledger/p7_runtime_evidence
```

The runner writes desktop screenshots and keyboard/focus evidence under the
fixture evidence path. It must not be used to infer approval for a live/private
source, a real writeback, or flag enablement.
