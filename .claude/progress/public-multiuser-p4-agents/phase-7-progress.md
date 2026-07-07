---
type: progress
schema_version: 2
doc_type: progress
prd: public-multiuser-p4-agents
feature_slug: public-multiuser-p4-agents
phase: 7
status: pending
created: '2026-07-07'
updated: '2026-07-07'
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1/phase-6-7-second-adapter-validation.md
commit_refs:
- 8cdc0f3
pr_refs: []
owners:
- python-backend-engineer
- documentation-writer
contributors:
- changelog-generator
tasks:
- id: VAL-7.1
  title: 'Credential-firewall regression suite (Mode-D Gate #3)'
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - tests/security/test_credential_isolation_regression.py
  dependencies:
  - SEC-2.4
  - API-4.5
  notes: "Synthetic fixtures only \u2014 Gate #2/real keys NOT approved. Gate #3 (real\
    \ trace) is DEFERRED post-merge operational step."
  started: '2026-07-07T00:00:00Z'
  completed: '2026-07-07T00:30:00Z'
  evidence:
  - test: tests/security/test_credential_isolation_regression.py
  verified_by:
  - VAL-7.1
- id: VAL-7.2
  title: Codex adversarial review of credential firewall
  status: deferred
  assigned_to:
  - orchestrator-external-codex
  files_affected: []
  dependencies:
  - VAL-7.1
  notes: Orchestrator runs codex exec externally. Findings to be supplied in completion
    note under 'Codex findings (orchestrator-supplied)' section.
- id: VAL-7.3
  title: E2E static+loopback parity suite
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - tests/e2e/test_agents_static_loopback_parity.py
  dependencies:
  - ADP-6.3
  - UI-5.9
  started: '2026-07-07T00:00:00Z'
  completed: '2026-07-07T00:00:00Z'
  evidence:
  - commit: 8cdc0f3
  verified_by:
  - pytest:tests/e2e/test_agents_static_loopback_parity.py
- id: VAL-7.4
  title: FU-1 benchmark writeup + design spec (DOC-006 pattern)
  status: completed
  assigned_to:
  - documentation-writer
  files_affected:
  - docs/project_plans/design-specs/agent-job-spawn-latency-fu1.md
  dependencies:
  - SEC-2.5
  notes: "GO verdict: p50\u22481.6ms, p99\u22483.7ms. In-process fallback NOT needed.\
    \ Cite benchmark test."
  evidence:
  - file: docs/project_plans/design-specs/agent-job-spawn-latency-fu1.md
- id: VAL-7.5
  title: 'Pepper-storage decision doc (Mode-D Gate #4)'
  status: completed
  assigned_to:
  - documentation-writer
  files_affected:
  - docs/project_plans/design-specs/agent-job-pepper-storage-decision.md
  dependencies:
  - SEC-2.4
  notes: 'Mode-D Gate #4. Leave sign-off block empty for operator. DO NOT self-approve.'
- id: VAL-7.6
  title: CLI parity (FR-20) + type-hardening annotation fix
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/cli/commands/agent_job.py
  - src/research_foundry/adapters/claude_agent_sdk.py
  - src/research_foundry/adapters/openai_agents.py
  dependencies:
  - API-4.5
  notes: 'launch/list/stream/accept subcommands mirroring rf catalog/rf report draft
    conventions. Type-hardening: change requires = (''...'',) to requires: tuple[str,
    ...] = (''...'',) in both adapters. Annotation-only.'
- id: VAL-7.7
  title: Documentation finalization bundle
  status: completed
  assigned_to:
  - changelog-generator
  - documentation-writer
  files_affected:
  - CHANGELOG.md
  dependencies:
  - VAL-7.1
  - VAL-7.3
  - VAL-7.4
  - VAL-7.5
  - VAL-7.6
  notes: CHANGELOG [Unreleased] entry for /agents route; plan frontmatter finalization.
parallelization:
  batch_1:
  - VAL-7.1
  - VAL-7.3
  - VAL-7.6
  batch_2:
  - VAL-7.4
  - VAL-7.5
  batch_3:
  - VAL-7.7
total_tasks: 7
completed_tasks: 6
in_progress_tasks: 0
blocked_tasks: 0
progress: 85
completion_ref: .claude/progress/public-multiuser-p4-agents/phase-7-completion.md
---

# Phase 7 Progress — P4.7: Testing, Benchmark, Docs

## Phase Overview

Closes the P4 feature: credential-firewall regression suite, E2E parity tests,
FU-1 benchmark writeup, pepper-storage decision doc (Mode-D Gate #4), CLI
parity (FR-20), and documentation finalization (CHANGELOG + plan frontmatter).

**Note on Mode-D Gate #3**: Run-time redaction verification against a REAL run
trace is DEFERRED — it requires Gate #2 (live provider keys), which is not yet
approved. This is documented explicitly in both the FU-1 spec and the
completion note.

**Note on VAL-7.2 (Codex adversarial review)**: Orchestrator runs `codex exec`
externally. Phase completion note will include a "Codex findings
(orchestrator-supplied)" section for the operator to fill.

## Task Status

| Task | Title | Status | Agent |
|------|-------|--------|-------|
| VAL-7.1 | Credential-firewall regression suite | pending | python-backend-engineer |
| VAL-7.2 | Codex adversarial review | deferred (orchestrator) | orchestrator-external |
| VAL-7.3 | E2E static+loopback parity | pending | python-backend-engineer |
| VAL-7.4 | FU-1 benchmark design spec | pending | documentation-writer |
| VAL-7.5 | Pepper-storage decision doc | pending | documentation-writer |
| VAL-7.6 | CLI parity + type-hardening | pending | python-backend-engineer |
| VAL-7.7 | Documentation finalization | pending | changelog-generator, documentation-writer |
