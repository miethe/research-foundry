---
type: progress
schema_version: 2
doc_type: progress
prd: external-research-report-interchange
feature_slug: external-research-report-interchange
phase: 4
title: Exact Resolution, Quarantine, and Promotion
status: completed
created: '2026-07-26'
updated: '2026-07-27'
prd_ref: docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
commit_refs: []
pr_refs: []
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
owners:
- python-backend-engineer
contributors:
- backend-architect
- task-completion-validator
- karen
execution_model: sequential
model_usage:
  primary: sonnet
  external:
  - gpt-5.6-sol
tasks:
- id: ERI-4.1
  description: 'Citation/source normalization: convert packet records and optional
    intake citation tuples into typed inert-data candidates, preserving packet IDs
    and namespaced extensions without control-surface promotion'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-2.4
  - ERI-3.6
  estimated_effort: 2 pts
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-26T00:00:00Z'
  completed: '2026-07-27T00:00:00Z'
  evidence:
  - test: tests/unit/test_source_acquisition_policy.py
  - test: tests/integration/test_external_research_resolution.py
  verified_by:
  - python-backend-engineer
- id: ERI-4.2
  description: 'SSRF-safe governed acquisition gate: authorization/sensitivity/rights
    first; reject unauthorized local/file/non-HTTP, embedded-credential, loopback/private/reserved/link-local/multicast/unspecified/metadata
    and encoded-host targets; validate every DNS answer, bind and verify the connected
    peer, cap/revalidate redirects, prohibit transport fallback before calling RFUP'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-4.1
  - ERI-1.5
  estimated_effort: 4 pts
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-26T00:00:00Z'
  completed: '2026-07-27T00:00:00Z'
  evidence:
  - test: tests/unit/test_source_acquisition_policy.py
  - test: tests/integration/test_external_research_resolution.py
  verified_by:
  - python-backend-engineer
- id: ERI-4.3
  description: 'Exact passage and quarantine resolver: resolve quote/selector against
    the bound edition; unique exact match advances, zero/multiple/drift/conflict/policy
    failures quarantine with safe reasons'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-4.2
  estimated_effort: 2 pts
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-26T00:00:00Z'
  completed: '2026-07-27T00:00:00Z'
  evidence:
  - test: tests/unit/test_source_acquisition_policy.py
  - test: tests/integration/test_external_research_resolution.py
  verified_by:
  - python-backend-engineer
- id: ERI-4.4
  description: 'Explicit promotion seam: stage passage-resolved candidates for existing
    RF verification/materialization; verified status requires accepted claim relationship
    and durable assertion refs'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-4.3
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-26T00:00:00Z'
  completed: '2026-07-27T00:00:00Z'
  evidence:
  - test: tests/unit/test_source_acquisition_policy.py
  - test: tests/integration/test_external_research_resolution.py
  verified_by:
  - python-backend-engineer
parallelization:
  batch_1:
  - ERI-4.1
  batch_2:
  - ERI-4.2
  batch_3:
  - ERI-4.3
  batch_4:
  - ERI-4.4
progress: 100
---

# Phase 4 — Exact Resolution, Quarantine, and Promotion

Highest-risk phase (9 pts). ERI-4.2 is the SSRF-safe acquisition gate and stays on primary
Claude (never offloaded), with a gpt-5.6 adversarial cross-model audit as the validation lens.

Owning surface: `src/research_foundry/services/external_research_resolution.py`,
`src/research_foundry/services/source_acquisition_policy.py`, `source_cards.py`,
`assertion_registry.py`, `tests/integration/test_external_research_resolution.py`.
