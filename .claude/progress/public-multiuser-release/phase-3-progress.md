---
type: progress
schema_version: 2
doc_type: progress
prd: public-multiuser-release
feature_slug: public-multiuser-release
phase: 3
status: pending
created: 2026-07-06
updated: '2026-07-05'
prd_ref: null
plan_ref: docs/project_plans/implementation_plans/public-multiuser-p2p3-opus-handoff.md
branch: feat/public-multiuser-p3
commit_refs: []
pr_refs: []
owners:
- opus-4-8
contributors: []
tasks:
- id: WAVE-D
  title: Draft model + builder_service (file-canonical D10; rpt_ ids; block CRUD/revisions;
    D13 checks; catalog.db index v2; export-to-MD)
  status: completed
  assigned_to:
  - python-backend-engineer
  executor: sonnet-5 in-session (MUST-stay)
  dependencies: []
  started: 2026-07-06T00:00Z
  completed: 2026-07-06T02:00Z
  evidence:
  - test: tests/unit/test_builder_service.py
  - test: tests/unit/test_verification_draft.py
  - file: src/research_foundry/services/builder_service.py
  - commit: 41f72af
  verified_by:
  - python-backend-engineer
- id: WAVE-E
  title: Builder API + CLI (POST /api/reports, versions, block PATCH, claim-links,
    verify, publish-preview fail-closed; rf report draft *)
  status: pending
  assigned_to:
  - ica-sonnet-4-6
  executor: ICA behind review gate
  dependencies:
  - WAVE-D
- id: WAVE-F
  title: Builder UI (/builder route; mockup layout; catalog search + block editor
    + audit inspector + Claim Basket; publish gate). Fable visual-fidelity review.
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  - claude-fable-5
  executor: sonnet-5 in-session + Fable fidelity review
  dependencies:
  - WAVE-D
  - WAVE-E
- id: WAVE-R2
  title: Codex/in-session adversarial review + Opus adjudication + fix-loop + full
    validation + squash-merge to main; flip plan status; op story capture
  status: pending
  assigned_to:
  - opus-4-8
  executor: reviewer + Opus
  dependencies:
  - WAVE-D
  - WAVE-E
  - WAVE-F
parallelization:
  batch_1:
  - WAVE-D
  batch_2:
  - WAVE-E
  - WAVE-F
  batch_3:
  - WAVE-R2
total_tasks: 4
completed_tasks: 1
in_progress_tasks: 0
blocked_tasks: 0
progress: 25
---

# Phase 3 — Report Builder (PR 2) Progress

Bespoke wave routing per handoff §5 PR2. Built on merged P2 (main 8b9d8be). D10 durable-state
discipline: draft truth lives in files, never the rebuildable catalog.db. Fable earmarked for the
Wave F Builder-UI visual-fidelity review (operator directive).

## Validation harness (worktree)
```
PYTHONPATH=<wt>/src <main>/.venv/bin/python -m pytest ...
```

## Wave log
- (pending) WAVE-D dispatch
