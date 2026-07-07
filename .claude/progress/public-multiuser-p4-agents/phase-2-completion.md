## Phase P4.2 Completion Note

**Status**: PASS
**Validator verdict**: PASS — all 5 tasks completed; 22+ tests passing; all ADR-002 invariants verified
**karen verdict**: PASS (after 1 remediation cycle) — 3 security hardening fixes applied; all items verified
**Isolation**: worktree
**Branch**: worktree-agent-ac7203ec3d84212a7
**Worktree path**: /Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/agent-ac7203ec3d84212a7

**Mode-D Gate #1**: Approved 2026-07-07 (nick) before any subprocess/credential code was written.
**Mode-D Gate #2 (real provider keys)**: NOT approved — all tests use synthetic credentials only.

### Files Changed

- `src/research_foundry/services/agent_job_service.py` — NEW: AgentJobService with subprocess spawn model, credential temp-file delivery (0600, PID-scoped), crash-safe cleanup, _safe_write_json chokepoint, _validate_path_component path sanitization
- `src/research_foundry/services/governance.py` — redact_payload() recursive sanitizer added to __all__; enforcement sentinel comment added
- `src/research_foundry/services/telemetry.py` — make_key_fingerprint() (salted HMAC, 12 hex chars); make_agent_job_telemetry_record(); RF_KEY_PROFILE_PEPPER env var support
- `tests/unit/test_credential_isolation.py` — NEW: 11 tests covering subprocess env isolation, cred file 0600 mode, crash-safe cleanup, redact_payload call chain, path traversal rejection
- `tests/security/test_secret_scan_agent_jobs.py` — NEW: 6 tests including zero-raw-creds assertions for AgentJobEvent/AgentJobArtifact shapes
- `tests/unit/test_key_fingerprint.py` — NEW: 5 tests verifying HMAC construction, determinism, non-reversibility, not flagged by governance patterns
- `tests/perf/test_spawn_latency_benchmark.py` — NEW: FU-1 spawn-latency micro-benchmark; p50≈1.6ms, p95≈3.2ms, p99≈3.7ms (macOS)
- `tests/security/__init__.py` — new (empty)
- `tests/perf/__init__.py` — new (empty)

### Batch Summary

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | SEC-2.3 | completed | python-backend-engineer |
| 2 | SEC-2.1+2.2 | completed | python-backend-engineer |
| 2 | SEC-2.4 | completed | python-backend-engineer |
| 3 | SEC-2.5 | completed | python-backend-engineer |
| remediation | karen fixes | completed | python-backend-engineer |

### Commits (c7a278c..HEAD)

- `22b5803` feat(security): add redact_payload write-time credential firewall (SEC-2.3)
- `e1e3dd3` feat(telemetry): add salted-HMAC key fingerprint (FR-14, SEC-2.4)
- `c8fd387` feat(sec): add AgentJobService subprocess spawn + credential isolation (SEC-2.1, SEC-2.2)
- `13d410c` perf(SEC-2.5): add spawn-latency micro-benchmark (FU-1)
- `94c1ce8` fix(security): karen P4.2 review — 3 credential-isolation hardening fixes

### ADR-002 Invariants at Phase Exit

- [x] subprocess-per-SDK-job (FR-11); static adapters stay in-process
- [x] credential delivered via 0600 temp file (PID-scoped); NEVER via env var (FR-12)
- [x] redact_payload() recursive firewall — wired at 2 of 4 write sites (persist_event, persist_artifact via _safe_write_json chokepoint); SSE and static-export deferred to P4.5/P4.6 — forward enforcement guarantee in place (FR-13)
- [x] salted-HMAC key_fingerprint (12 hex chars, server pepper) in telemetry (FR-14)
- [x] 0 raw credentials in job artifacts/events/logs — AC-5.1
- [x] crash-safe cleanup: killed subprocess leaves no credential temp file — AC-5.2
- [x] no env-var/subprocess env= credential inheritance; no SDK-config-file write — AC-5.3
- [x] fingerprint present, salted-HMAC, never flaggable by secret_patterns — AC-5.4/5.5
- [x] FU-1 benchmark numbers captured (p50≈1.6ms, p95≈3.2ms, p99≈3.7ms)

### Forward-Tracking Items (for P4.5 and P4.6 phase owners)

1. **P4.5**: Wire `redact_payload()` (via `_safe_write_json` or direct call) at the SSE event-stream serializer write site. Required: verify in P4.5 validator gate.
2. **P4.6**: Wire `redact_payload()` at the runs-viewer static-export writer. Required: verify in P4.6 validator gate.
3. **P5**: Enforce RF_KEY_PROFILE_PEPPER as required (fail-closed if unset) before public GA — the source-visible fallback constant makes fingerprints forgeable with repo access.

### Escalation Reason

N/A — no Mode-D escalation triggered. Mode-D Gate #1 was pre-approved; Gate #2 (real provider keys) remains ungated.

### Follow-Up Recommendations

1. karen recommended that the "4 write sites" quality gate item be propagated explicitly into the P4.5 and P4.6 phase plans as an exit criterion now, before those phases start.
2. The interim HMAC pepper constant (`_INTERIM_PEPPER`) in telemetry.py is clearly labeled NOT FOR PRODUCTION but should be tracked on the P5 milestone for mandatory env enforcement.
3. FU-1 latency data (p50/p95/p99) feeds VAL-7.4 in the P4.7 writeup — no action needed in this phase, forward pointer only.
