---
schema_version: 2
doc_type: progress
prd: public-multiuser-p4-agents
feature_slug: public-multiuser-p4-agents
phase: 2
phase_title: 'P4.2: Credential isolation + firewall (Mode D)'
status: completed
created: 2026-07-07
updated: '2026-07-07'
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
phase_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1/phase-1-2-foundations.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
- backend-architect
contributors: []
tasks:
- id: SEC-2.1
  title: Subprocess-per-agent-job spawn model
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/services/agent_job_service.py
  dependencies:
  - JOB-1.4
  started: null
  completed: null
  verified_by: []
  evidence: []
- id: SEC-2.2
  title: Credential temp-file delivery + child-side loading contract + crash-safe
    cleanup
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/services/agent_job_service.py
  - tests/unit/test_credential_isolation.py
  dependencies:
  - SEC-2.1
  started: null
  completed: null
  verified_by: []
  evidence: []
- id: SEC-2.3
  title: Write-time redaction firewall
  status: completed
  assigned_to:
  - python-backend-engineer
  - backend-architect
  files_affected:
  - src/research_foundry/services/governance.py
  - config/governance.yaml
  - tests/security/test_secret_scan_agent_jobs.py
  dependencies:
  - JOB-1.3
  started: null
  completed: null
  verified_by: []
  evidence: []
- id: SEC-2.4
  title: Key fingerprint (salted-HMAC)
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/services/telemetry.py
  dependencies:
  - SEC-2.3
  started: null
  completed: null
  verified_by: []
  evidence: []
- id: SEC-2.5
  title: FU-1 spawn-latency micro-benchmark
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - tests/perf/test_spawn_latency_benchmark.py
  dependencies:
  - SEC-2.1
  started: '2026-07-07T00:00:00Z'
  completed: '2026-07-07T00:00:00Z'
  verified_by: []
  evidence:
  - file: tests/perf/test_spawn_latency_benchmark.py
parallelization:
  batch_1:
  - SEC-2.3
  batch_2:
  - SEC-2.1
  - SEC-2.2
  - SEC-2.4
  batch_3:
  - SEC-2.5
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# P4.2 Progress — Credential Isolation + Firewall

**Phase**: P4.2 | **Mode**: Mode D (Gate #1 approved 2026-07-07) | **Isolation**: worktree

## Batch Execution Plan

### Batch 1 — Redaction Firewall Foundation (SEC-2.3)
Run first so `redact_payload()` exists in governance.py before agent_job_service.py is written.

- SEC-2.3: Add `redact_payload()` recursive sanitizer to `governance.py`; update `config/governance.yaml`; write `tests/security/test_secret_scan_agent_jobs.py`

### Batch 2 — Subprocess Spawn + Credential Delivery + Telemetry (parallel)
Run after Batch 1 (governance.py has redact_payload available).

- SEC-2.1 + SEC-2.2 (combined): Create `agent_job_service.py` with subprocess spawn, credential temp-file delivery, crash-safe cleanup; write `tests/unit/test_credential_isolation.py`
- SEC-2.4: Add salted-HMAC key fingerprint to `telemetry.py`

### Batch 3 — Benchmark (SEC-2.5)
Run after Batch 2 (needs spawnable stub from SEC-2.1).

- SEC-2.5: Spawn-latency micro-benchmark script

## ADR-002 Invariants (all must hold at phase exit)

- [ ] subprocess-per-SDK-job (FR-11)
- [ ] credential delivered via 0600 temp file, child unlinks immediately after reading (FR-12)
- [ ] redact_payload() recursive firewall wired at all 4 write sites (FR-13)
- [ ] salted-HMAC key_fingerprint (~12 hex chars) in telemetry (FR-14)
- [ ] 0 raw credentials in job artifacts/events/logs (AC-5.1)
- [ ] crash-safe cleanup: killed subprocess leaves no credential temp file (AC-5.2)
- [ ] no env-var/subprocess env= credential inheritance; no SDK-config-file write (AC-5.3)
- [ ] fingerprint present, salted-HMAC, never flaggable by secret_patterns (AC-5.4/AC-5.5)
