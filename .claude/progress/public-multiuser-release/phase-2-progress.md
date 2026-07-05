---
type: progress
schema_version: 2
doc_type: progress
prd: public-multiuser-release
feature_slug: public-multiuser-release
phase: 2
status: pending
created: 2026-07-05
updated: '2026-07-05'
prd_ref: null
plan_ref: docs/project_plans/implementation_plans/public-multiuser-p2p3-opus-handoff.md
branch: feat/public-multiuser-p2
commit_refs: []
pr_refs: []
owners:
- opus-4-8
contributors: []
tasks:
- id: WAVE-A
  title: Anchor model + AST extraction (markdown-it-py; report_anchors in export_service;
    schema bump; drift tests)
  status: completed
  assigned_to:
  - python-backend-engineer
  executor: sonnet-5 in-session (MUST-stay)
  dependencies: []
  started: 2026-07-05T20:10Z
  completed: 2026-07-05T20:35Z
  evidence:
  - commit: 1ea859c
- id: WAVE-B
  title: API + CLI + catalog surfacing (anchors endpoint; _build_links real anchors;
    rf report anchors; threshold parity)
  status: completed
  assigned_to:
  - python-backend-engineer
  executor: claude-sonnet-4-6 in-session
  dependencies:
  - WAVE-A
  completed: 2026-07-05T21:05Z
  evidence:
  - files:
    - src/research_foundry/api/routers/runs.py
    - src/research_foundry/services/catalog_service.py
    - src/research_foundry/cli_commands.py
    - frontend/runs-viewer/src/types/rf/run-export.ts
    - frontend/runs-viewer/src/lib/catalog.ts
    - frontend/runs-viewer/src/lib/catalog.test.ts
    - tests/unit/test_catalog_anchors.py
  - tests: 181 Python + 54 TS all pass
  - commit: b4b543a
  started: 2026-07-05T20:35Z
- id: WAVE-C
  title: Frontend audit upgrade (consume report_anchors; paragraph+span highlight;
    coverage strip; filters; static parity)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  executor: sonnet-5 in-session
  dependencies:
  - WAVE-A
  started: 2026-07-05T20:35Z
  completed: 2026-07-05T21:25Z
  evidence:
  - commit: bf8c1a2
- id: WAVE-R1
  title: Codex adversarial review + Opus adjudication + fix-loop + full validation
    + squash-merge to main
  status: pending
  assigned_to:
  - codex-gpt-5.5
  - opus-4-8
  executor: Codex read-only + Opus
  dependencies:
  - WAVE-A
  - WAVE-B
  - WAVE-C
parallelization:
  batch_1:
  - WAVE-A
  batch_2:
  - WAVE-B
  - WAVE-C
  batch_3:
  - WAVE-R1
total_tasks: 4
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
progress: 75
---

# Phase 2 — Granular Report Audit (PR 1) Progress

Bespoke wave routing per handoff §5. Opus orchestrates directly; MUST-stay waves (A) stay
in-session, bounded wave (B) offloads to ICA behind a reviewer gate, review gate (R1) uses Codex.

## Validation harness (worktree)
```
PYTHONPATH=<wt>/src <main>/.venv/bin/python -m pytest ...   # editable install points at main
```
Pre-existing failures to distinguish from regressions: `tests/unit/test_export_service.py`,
`tests/unit/test_sensitivity_redaction.py` (4 failures per RF test-suite gotchas memo).

## Wave log
- (pending) WAVE-A dispatch
