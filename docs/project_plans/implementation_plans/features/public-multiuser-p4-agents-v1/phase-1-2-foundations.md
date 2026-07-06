---
schema_version: 2
doc_type: phase_plan
title: "Phase 1–2: Foundations — Job Model + Credential Isolation"
status: draft
created: 2026-07-06
phase: "P4.1-P4.2"
phase_title: "Job model + ResearchAgentProvider port; Credential isolation + firewall (Mode D)"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
entry_criteria:
  - "PRD approved; decisions block locked (D1-D7)"
exit_criteria:
  - "P4.1: schema fixtures + registry round-trip pytest green"
  - "P4.2: secret-scan asserts 0 raw creds; fingerprint present; crash-safe cleanup tested; Mode-D Gate #1 logged before entry"
---

# Phase 1–2: Foundations

[← Back to plan summary](../public-multiuser-p4-agents-v1.md)

**Column conventions**: `Estimate` = story points (never in Effort). `Model`: `opus|sonnet|haiku|gpt-5.5-codex`. `Effort` (claude): `adaptive|extended`. See `.claude/skills/planning/references/multi-model-guidance.md`.

---

## Phase P4.1: Job model + `ResearchAgentProvider` port

**Estimate**: 3 pts
**Dependencies**: None (first phase)
**Isolation**: shared
**Assigned Subagent(s)**: backend-architect, python-backend-engineer
**Agent Routing**: MUST-stay — contract design happens on the primary Claude subscription, no offload. This phase's schemas and Protocol are the frozen contract every later phase (P4.2–P4.7) builds on; a routing/estimation error here compounds downstream.

### Overview

Define the `ResearchAgentProvider` Protocol + registry (mirroring `adapters/base.py`'s `Adapter` Protocol + `register`/`get_adapter`/`all_adapters` idiom) and the `agent_job*` schema family (FR-1, FR-3, FR-4). No provider implementation lands in this phase — that's P4.3. Job durable state resolves OQ-B: recommend a durable `agent_jobs/<agent_job_id>/` accessor on `FoundryPaths`, mirroring `report_draft_dir`'s discipline (agent outputs are user-facing pending acceptance, not a rebuildable cache).

### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------------------|----------|--------------|-------|--------|--------------|
| JOB-1.1 | `ResearchAgentProvider` Protocol + registry | New `services/agent_providers/base.py`: Protocol with `start_job`, `stream_events`, `cancel_job`, `list_artifacts`, `accept_artifacts`; `register`/`get_provider`/`all_providers` mirroring `adapters/base.py`. | Protocol validates against a stub implementation; registry round-trips register→get→list in a unit test. | 1 pt | backend-architect | sonnet | extended | None |
| JOB-1.2 | `agent_job` schema + durable store (OQ-B) | `agent_job` record (FR-3): `agent_job_id`, `workspace_id`/`created_by` nullable (D12/D7), `project_id`, `provider`, `model_profile`, `request_kind`, `input_claim_ids`/`input_source_ids`/`input_report_id`, `policy_snapshot{allowed_tools,data_scopes}`, `budget_usd`, `max_runtime_minutes`, `status` enum (`queued,running,waiting_for_approval,failed,canceled,completed,accepted`), timestamps. Add `FoundryPaths.agent_job_dir` accessor (durable, mirrors `report_draft_dir` — resolves OQ-B). | Schema validates via fixture; YAML round-trip test; `FoundryPaths.agent_job_dir` resolves under the workspace root, not `.rf_cache/`. | 1 pt | python-backend-engineer | sonnet | extended | JOB-1.1 |
| JOB-1.3 | `agent_job_event`/`artifact`/`tool_call`/`approval`/`acceptance` schemas | Child record schemas (FR-4): events carry `stage` (`plan/search/source_intake/extraction/claim_proposal/contradiction_check/verification/synthesis`), timestamp, redacted-payload field (redaction itself is P4.2's job). | Schemas validate independently; fixtures for each of the 5 record types. | 0.5 pt | python-backend-engineer | sonnet | adaptive | JOB-1.2 |
| JOB-1.4 | Job state machine | Transition validation for the `status` enum (queued→running→waiting_for_approval/failed/canceled/completed→accepted); illegal transitions raise. | Unit test enumerates all legal/illegal transition pairs. | 0.5 pt | backend-architect | sonnet | adaptive | JOB-1.2 |

**Phase P4.1 Quality Gates:**
- [ ] Schema fixtures for all 6 record types (`agent_job`, `agent_job_event`, `agent_job_artifact`, `agent_job_tool_call`, `agent_job_approval`, `agent_job_acceptance`) committed and validated.
- [ ] Registry round-trip (register→get→list) unit-tested.
- [ ] State machine transition matrix unit-tested (legal + illegal).
- [ ] No provider implementation exists yet — confirmed by grep (this phase's exit gate is contract-only).
- [ ] `task-completion-validator` review passed.

---

## Mode-D Gate #1 (between P4.1 and P4.2)

**Required before any task in P4.2 begins.** Explicit human approval **before any subprocess-spawn or credential-file code is written** (PRD AC-6.1). Log who approved, when, and what was reviewed (the JOB-1.* schemas + this phase's task list) before proceeding. Do not start SEC-2.1 without this logged.

---

## Phase P4.2: Credential isolation + firewall (Mode D)

**Estimate**: 5 pts
**Dependencies**: P4.1 complete + Mode-D Gate #1 logged
**Isolation**: **worktree** (Mode D trigger — credential/secret-rotation infrastructure per the Isolation Decision Aid). Commit before returning; Opus integrates explicitly before P4.3 starts.
**Assigned Subagent(s)**: python-backend-engineer (primary), backend-architect (secondary)
**Agent Routing**: **MUST-stay, no ICA/Codex for implementation.** This is the crown-jewel security layer (SPIKE ADR-002). Codex gpt-5.5 is used only as a *read-only adversarial reviewer* in P4.7 (VAL-7.2), never here.

### Overview

Build the SPIKE ADR-002 boundary: subprocess-per-agent-job spawn (FR-11), temp-file credential delivery with an explicit child-side load-once-then-unlink contract (FR-12), a **new** write-time redaction firewall — `redact_payload()`, additive to (not a light reuse of) `governance.py`'s existing string/path-only `scan_secrets`/`_redact` (FR-13, see SEC-2.3) — and salted-HMAC key fingerprinting (FR-14). FU-1 (spawn-latency benchmark) runs in parallel, non-blocking, per D3 — it does not gate this phase's exit.

**Scope correction (this is new security-API work, not light reuse)**: `governance.py` today only exposes `scan_secrets(text)` (flat-string post-hoc scan) and `_redact(secret)` (a private helper that truncates an *already-matched* secret substring for safe display in a violation message — it is not a payload sanitizer). Neither function walks a nested object graph. SEC-2.3 below adds a genuinely new, additive function (`redact_payload`), not an extension of `_redact`.

### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------------------|----------|--------------|-------|--------|--------------|
| SEC-2.1 | Subprocess-per-agent-job spawn model | One child process per SDK-class job (FR-11), holding only that job's resolved credential set; lifecycle management (spawn, monitor, terminate) in `agent_job_service.py`. Existing static adapters (`gpt_researcher`, `paperqa2`, `litellm_router`, `opencode`, `arc_council`, `notebooklm`) explicitly stay in-process — this task does not touch them. | Unit test spawns a dummy subprocess and asserts it does not inherit unrelated `os.environ` keys. | 1.5 pt | python-backend-engineer | sonnet | extended | JOB-1.4 + Gate #1 |
| SEC-2.2 | Credential temp-file delivery + child-side loading contract + crash-safe cleanup | Job-scoped temp file, mode `0600`, unique per-job path (FR-12) — never an env var. **Child-side loading contract (explicit)**: the child process's bootstrap reads the temp file's bytes exactly once into an in-memory credential value immediately on startup, unlinks the file, then passes the value directly into the Claude/OpenAI SDK client constructor argument (e.g. `api_key=`). The credential is NEVER written into the child's `os.environ` (so no tool-spawned grandchild inherits it via env) and NEVER persisted to any SDK-native config file the tool-use loop's tools could read (e.g. no on-disk `~/.config/<sdk>/credentials`). Crash-safe cleanup: kill the subprocess mid-run, assert the file does not survive; a reaper/janitor pass on job-store startup provides defense-in-depth if the child crashes before reaching the unlink step. | AC-5.2 (crash-safety test) and AC-5.3 (code-path audit: no `os.environ`/`subprocess env=` inheritance, and no SDK-config-file write containing the raw credential) both pass. | 1.5 pt | python-backend-engineer | sonnet | extended | SEC-2.1 |
| SEC-2.3 | Write-time redaction firewall (new security API — additive to `governance.py`, not a light reuse of `_redact`) | Add `redact_payload(obj) -> sanitized_obj` to `governance.py`: a **recursive** sanitizer that walks nested dicts/lists and redacts (or fails closed / raises on unredactable content) any matched secret pattern, unlike today's `scan_secrets`/`_redact` which only operate on a flat string or an already-matched substring. Wire it as a mandatory write-time guard at every relevant write site (FR-13): `agent_job_event` persistence, `agent_job_artifact` persistence, the SSE event-stream serializer (each chunk before it reaches the client), and the runs-viewer static-export writer — not only the existing post-hoc `scan_paths` scan. | AC-2.2 (every persisted/streamed event and artifact passed the guard), AC-5.1 (secret-scan test, 0 raw matches), and a new unit test asserting `redact_payload` recurses into nested dict/list structures (not just top-level string fields) all pass. | 1 pt | python-backend-engineer, backend-architect | sonnet | extended | JOB-1.3 |
| SEC-2.4 | Key fingerprint (salted-HMAC) | Salted-HMAC construction (server pepper via `foundry.yaml` key-profile env var, per D2 interim design — not a raw prefix hash), truncated ~12 hex chars; recorded in the run/job trace and CCDash telemetry alongside `key_profile_used` (FR-14). | AC-5.4 (fingerprint present + salted-HMAC construction, not reversible prefix) and AC-5.5 (fingerprint never matches `governance.yaml` `secret_patterns`) pass. | 0.5 pt | python-backend-engineer | sonnet | adaptive | SEC-2.3 |
| SEC-2.5 | FU-1: spawn-latency micro-benchmark (non-blocking) | Measure subprocess spawn latency for the job model against a dummy/stub payload; capture raw numbers (p50/p95/p99) feeding P4.7's writeup (VAL-7.4). Runs in parallel with SEC-2.1–2.4 per D3 — does **not** gate this phase's exit. | Benchmark script + raw output committed; no pass/fail assertion at this stage (interpretation happens in P4.7). | 0.5 pt | python-backend-engineer | sonnet | adaptive | SEC-2.1 (needs a spawnable stub) |

**Phase P4.2 Quality Gates (phase exit gate, per decisions block):**
- [ ] Secret-scan asserts 0 raw credential matches in artifacts/events (AC-5.1).
- [ ] Crash-safety test passes: killed subprocess leaves no surviving credential temp file (AC-5.2).
- [ ] Code-path audit confirms no env-var/`subprocess env=` credential inheritance AND no SDK-config-file write of the raw credential — child reads the temp file once into memory, then unlinks (AC-5.3).
- [ ] `redact_payload()` unit test confirms recursion into nested dicts/lists (not just top-level strings) and is wired at all four write sites: event persistence, artifact persistence, SSE stream serializer, static-export writer.
- [ ] Key fingerprint present, salted-HMAC, and never flaggable by `governance.yaml` `secret_patterns` (AC-5.4/AC-5.5).
- [ ] FU-1 benchmark numbers captured (non-blocking; interpretation deferred to P4.7 VAL-7.4).
- [ ] `task-completion-validator` **and** `karen` (security milestone) both passed — this is one of the plan's 3 mandatory `karen` gates.
- [ ] Worktree branch committed and merged back before P4.3 starts.

**FE resilience note (R-P2, forward pointer)**: `policy_snapshot` (with `allowed_tools`/`data_scopes`) is introduced in this phase's schema layer (JOB-1.2) but consumed by the frontend in P4.5. The implicit "FE handles missing `policy_snapshot`" AC is PRD AC-4.5 and is implemented/verified in `phase-5-frontend.md` (UI-5.7), not here — noted for traceability.

---

[← Back to plan summary](../public-multiuser-p4-agents-v1.md) | [Next: Phase 3–4 →](./phase-3-4-backend-integration.md)
