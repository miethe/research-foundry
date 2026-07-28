---
type: progress
schema_version: 2
doc_type: progress
prd: external-research-report-interchange
feature_slug: external-research-report-interchange
phase: 6
title: Hardening, Documentation, and Exact-Tree Closeout
status: pending
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
total_tasks: 5
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
owners:
- python-backend-engineer
contributors:
- documentation-writer
- changelog-generator
- task-completion-validator
- karen
execution_model: sequential
model_usage:
  primary: sonnet
  external:
  - gpt-5.6-sol
tasks:
- id: ERI-6.1
  description: 'Cross-profile contracts and compatibility: five profile round-trips,
    schema golden/negative tests, legacy run/source/assertion reads, duplicate-authority
    and tree scan'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-5.G
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-27T14:38:22Z'
  completed: '2026-07-27T14:38:22Z'
  evidence:
  - test: tests/integration/test_external_research_cross_profile_compat.py
  - test: tests/unit/test_external_research_caller_authorization.py
- id: ERI-6.2
  description: 'Adversarial trust matrix: unsafe members, all SSRF/address/DNS/redirect/
    rebinding cases, injection-shaped vendor fields, policy denials, drift, ambiguity,
    mismatch, partial basis, verification failure, replay conflict, redaction'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-6.1
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-27T14:38:22Z'
  completed: '2026-07-27T14:38:22Z'
  evidence:
  - test: tests/integration/test_external_research_adversarial_matrix.py
- id: ERI-6.3
  description: 'Large-report resume and limits: boundary/fault tests across batches
    and publication points; record representative elapsed/memory evidence without
    production claims'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-6.2
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-27T14:38:22Z'
  completed: '2026-07-27T14:38:22Z'
  evidence:
  - test: tests/integration/test_external_research_large_report_resume.py
- id: ERI-6.4
  description: 'Docs, skill, CHANGELOG, and deferred specs: update architecture/user
    guide, README command inventory, Research Foundry skill route, CHANGELOG, examples,
    findings, and promotable deferred specs (ERI-DF-1..4)'
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - ERI-6.3
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-27T14:38:22Z'
  completed: '2026-07-27T14:38:22Z'
  evidence:
  - doc: docs/user/external-research-interchange.md
  - doc: CHANGELOG.md
- id: ERI-6.5
  description: 'AC evidence and final reviewers: map ERI-AC-1..7 to exact results,
    run focused/full relevant gates, verify docs/runtime parity, obtain exact-tree
    task-completion-validator then Karen passes'
  status: pending
  assigned_to:
  - task-completion-validator
  - karen
  dependencies:
  - ERI-6.4
  estimated_effort: 1 pt
  assigned_model: opus
  model_effort: extended
parallelization:
  batch_1:
  - ERI-6.1
  batch_2:
  - ERI-6.2
  - ERI-6.3
  batch_3:
  - ERI-6.4
  batch_4:
  - ERI-6.5
progress: 80
---

# Phase 6 — Hardening, Documentation, and Exact-Tree Closeout

Adversarial validation across all five producer profiles and the full SSRF/injection trust
matrix, large-packet resume evidence, user/architecture docs, CHANGELOG, deferred design
specs, and the final exact-tree reviewer gate.
