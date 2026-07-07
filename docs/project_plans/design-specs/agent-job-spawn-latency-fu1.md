---
schema_version: 2
doc_type: design-spec
title: "Agent Job Spawn Latency — FU-1 Follow-Up"
status: draft
maturity: shaping
created: 2026-07-07
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
deferred_from: "P4.2 (SEC-2.5): subprocess-per-job isolation latency benchmark"
---

# Agent Job Spawn Latency — FU-1 Follow-Up

## Background

The P4 agent-job feature implements a **subprocess-per-job isolation model** to enforce hard credential boundaries (SEC-2.1, SEC-2.2):

1. Each job spawn creates a temporary credential file (mode 0600) in the job's staging directory
2. A new subprocess is spawned via `subprocess.Popen` with isolated environment (`env={}`)
3. The child process inherits no parent environment variables, making credential leakage through env vars impossible
4. On job completion, the temp file is unlinked and the process is reaped

During P4.2 planning (SEC-2.5), we identified that this isolation model, while necessary for security, could potentially introduce overhead that might require an in-process fallback for high-frequency spawning scenarios (Decision D3). This spec documents the latency benchmark that closes this concern.

## Benchmark Results (P4.2 SEC-2.5)

The spawn latency of `AgentJobService.spawn_job()` was measured on the loopback path (no real provider connection, command_override to a fast dummy subprocess) over 20 iterations.

**Measurement Method:**
- Each iteration records wall-clock time (`time.perf_counter()`) spanning only the `spawn_job()` call itself
- Dummy child command: `python -c "import time; time.sleep(0.01)"` (ensures clean process lifecycle)
- No real provider SDK overhead; measures only the spawn infrastructure cost
- See: `tests/perf/test_spawn_latency_benchmark.py`

**Results (2026-07-07, M-series Mac, development environment):**

| Percentile | Latency |
|-----------|---------|
| p50       | 1.60 ms |
| p95       | 2.38 ms |
| p99       | 2.75 ms |

**Key observation:** Real agent job execution time (typical: 30 seconds to several minutes) vastly dominates the spawn overhead. For a 5-minute agent run, spawn latency represents < 0.01% of total job time.

## Verdict: GO — In-Process Fallback NOT Needed

**Decision**: The subprocess-per-job isolation model is **viable and performant**. Decision D3 ("in-process fallback if latency proves prohibitive") is hereby **closed as not needed**. No in-process fallback implementation is required for P4.

The benchmark demonstrates that:
- p50 spawn latency ≈ 1.6 ms is negligible
- p99 spawn latency ≈ 2.75 ms is well within acceptable bounds for typical workloads
- The latency budget (total job time = spawn overhead + actual agent execution) is dominated by agent execution time, not spawn overhead

## Rationale

### Security Wins vs. Negligible Latency Cost

The subprocess-per-job model provides:

1. **Hard credential boundary** (SEC-2.1): The child process cannot access parent environment variables or read parent memory
2. **Atomic credential delivery** (SEC-2.2): Credential passed via temp file (mode 0600), never via env dict or command-line arguments
3. **Guaranteed cleanup** (SEC-2.2): Temp file is unlinked after the child exits, even in crash scenarios (tested via SIGKILL in `test_credential_isolation.py`)

These guarantees **cannot be provided by in-process execution**, where credentials would necessarily be visible to parent process introspection.

### Workload Reality

The rate-limiting constraints documented in memory note `rf-run-execution-path-b.md` establish that:

> HARD LIMIT: one deep swarm at a time or carders get rate-limited

High-frequency job spawning (> 100 spawns/minute) is not a typical workload pattern. The typical case is a small number of sequential or loosely-parallel agents per research run, with execution times measured in seconds to minutes.

At this workload profile, 1.6–2.75 ms spawn latency is immeasurable to the user experience.

## Deferred Follow-Up (Gate #3)

**Mode-D Gate #3 is DEFERRED.** This gate requires verifying the **write-time redaction guard** (SEC-2.3) against a **REAL run trace**, which requires:

1. Mode-D Gate #2 approval (live provider API keys)
2. A real agent job run with live credentials
3. Audit of the persisted event and artifact traces to confirm no raw secrets appear on disk

This is a **post-merge operational step** that must be completed by the operator before exposing the `/agents` surface to non-loopback traffic.

In the interim, the VAL-7.1 regression suite covers redaction on synthetic credentials:
- `test_persist_event_redacts_secrets()`: verifies event payloads are redacted
- `test_persist_artifact_redacts_secrets()`: verifies artifact payloads are redacted
- `test_safe_write_json_calls_redact_payload()`: verifies the redaction chokepoint is always invoked

The test file `tests/security/test_credential_isolation_regression.py` includes a `pytest.mark.skip` stub (`test_redaction_guard_real_trace`) that the operator will enable and run after Gate #2 approval with real credentials.

Reference: `.claude/progress/public-multiuser-p4-agents/phase-7-progress.md` (Phase 7 Progress — Phase Overview section).

## Next Steps / Operationalization

### Immediate (Pre-Merge)
- No code changes required from this analysis
- Benchmark data is informational only — no pass/fail enforcement on spawn latency
- Regression suite passes synthetic-credential cases (VAL-7.1 status: `completed`)

### Post-Merge (Operator Responsibility)
- **Gate #3 completion**: Operator approves Gate #2 (live API keys), runs a real agent job, and executes the skip-marked redaction test with real credentials
- Operator confirms that persisted traces (events and artifacts) contain `[REDACTED]` placeholders, never raw secret material
- Only after Gate #3 passes can the `/agents` route be exposed to traffic beyond loopback

### Production Monitoring
- Monitor spawn latency in production if workloads shift to high-frequency patterns (> 100 spawns/minute)
- If p99 spawn latency ever exceeds 10 ms under production load, escalate to performance engineering
- No in-process fallback is planned or anticipated to be needed based on this analysis
