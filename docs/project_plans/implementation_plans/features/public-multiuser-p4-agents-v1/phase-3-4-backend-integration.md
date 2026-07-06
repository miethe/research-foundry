---
schema_version: 2
doc_type: phase_plan
title: "Phase 3–4: Backend Integration — First Adapter e2e + APIs/Streaming/Acceptance"
status: draft
created: 2026-07-06
phase: "P4.3-P4.4"
phase_title: "First provider adapter (claude_agent_sdk) e2e; Agent-job APIs + event streaming + acceptance"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
entry_criteria:
  - "P4.2 sealed (secret-scan, crash-safety, fingerprint gates passed; karen security review passed)"
exit_criteria:
  - "P4.3: governed job runs from a claim, streams, produces staged artifacts; Mode-D Gate #2 logged"
  - "P4.4: contract tests pass; no direct-write code path exists"
---

# Phase 3–4: Backend Integration

[← Back to plan summary](../public-multiuser-p4-agents-v1.md)

**Column conventions**: `Estimate` = story points. `Model`: `opus|sonnet|haiku|gpt-5.5-codex`. `Effort` (claude): `adaptive|extended`. `Provider` (only where offload applies): `claude|ica|codex`. See `.claude/skills/planning/references/multi-model-guidance.md`.

---

## Phase P4.3: First provider adapter (`claude_agent_sdk`) e2e

**Estimate**: 3 pts
**Dependencies**: P4.2 sealed
**Isolation**: shared
**Assigned Subagent(s)**: python-backend-engineer
**Agent Routing**: MUST-stay. Adapter wiring through the freshly-proven credential boundary; no offload while the first live-key run is pending Gate #2.

### Overview

Promote `adapters/claude_agent_sdk.py` from its degraded-mode stub (echoes intent, `degraded=True`) to real-mode execution, implemented against the `ResearchAgentProvider` Protocol from P4.1 and running inside the P4.2 isolation boundary. Wires in the existing Search Router (`search_router.router.run_search`/`extract_urls`) and source-card/claim extraction (`source_cards.ingest_source`/`create_source_card`) as job tools/stages (FR-17) — this phase composes existing services, it does not reimplement search.

### Mode-D Gate #2 (inside this phase, before any real-key run)

**Required before any task exercises real (non-test) provider keys.** Explicit human approval **before the first live job runs with real provider keys** (PRD AC-6.2). Test-double/mock credentials may be used for ADP-3.1/3.2 development; ADP-3.3's integration test must use test doubles until Gate #2 is logged, then a follow-up real-key run closes the gate.

### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------------------|----------|--------------|-------|--------|--------------|
| ADP-3.1 | Promote `claude_agent_sdk.py` to real mode | Implement the `ResearchAgentProvider` Protocol (`start_job`/`stream_events`/`cancel_job`/`list_artifacts`/`accept_artifacts`) against the Claude Agent SDK, replacing the degraded-mode stub's `degraded=True` echo path. | Real-mode execution reachable via the provider registry; degraded-mode path still exists as an explicit fallback (not silently removed). | 1.5 pt | python-backend-engineer | sonnet | adaptive | SEC-2.2, SEC-2.3 (isolation + firewall wired) |
| ADP-3.2 | Wire Search Router + source-card/claim extraction as job tools | Integrate `search_router.router.run_search`/`extract_urls` and `source_cards.ingest_source`/`create_source_card` as tools/stages the job's SDK loop can invoke (FR-17). | Job brief-building step composes these existing services; no search logic is duplicated. | 1 pt | python-backend-engineer | sonnet | adaptive | ADP-3.1 |
| ADP-3.3 | E2E integration test: full job lifecycle | Job launches from a selected claim/report gap, streams through the isolation + governance gates, produces staged artifacts (Goal 1 success criteria, decisions-block P4.3 success criteria). Uses test-double credentials until Gate #2 is logged. | Integration test covers queued→running→waiting_for_approval/completed→(staged, not yet accepted). Gate #2 logged before any real-key variant of this test runs. | 0.5 pt | python-backend-engineer | sonnet | adaptive | ADP-3.2 |

**Phase P4.3 Quality Gates:**
- [ ] Governed job runs from a claim, streams, produces staged artifacts (decisions-block success criteria).
- [ ] Mode-D Gate #2 logged (who approved, when, what reviewed) before any real-key job run.
- [ ] `task-completion-validator` review passed.

---

## Phase P4.4: Agent-job APIs + event streaming + acceptance

**Estimate**: 4 pts
**Dependencies**: P4.3 complete
**Isolation**: shared
**Assigned Subagent(s)**: python-backend-engineer (primary); **ICA Sonnet 4.6** (secondary, bounded endpoints only)
**Agent Routing**: Contract-clear CRUD/SSE endpoints (API-4.2, API-4.3) are offloadable to ICA Sonnet 4.6 (`~/ica-claude.sh`, `claude-sonnet-4-6[1m]`) **behind a `task-completion-validator` gate** — pipe long prompts via stdin (ICA gotcha). The launch-gate logic (API-4.1) and the accept write-path (API-4.5) are **MUST-stay** on the primary sonnet session: they carry the governance-gate and crown-jewel-write-path logic this whole feature exists to protect.
**Integration Owner (R-P3)**: python-backend-engineer owns the API contract this phase produces; P4.5 (frontend) is the consuming owner. See API-4.6 below (seam task).

### Overview

Spec §10 endpoints: launch, detail, event streaming (SSE), cancel, accept, artifact listing (FR-5 through FR-10). Acceptance (FR-9/FR-16) is the sole write path from job-scoped staging into `catalog_service`/`builder_service` — gated by the generalized `agent_job_output_requires_review` rule (exit-code-7 `HUMAN_REVIEW`). **OQ-A** (SSE transport: reuse existing runs-viewer streaming, or new endpoint) must be resolved at the start of API-4.3 by checking `api/` for existing SSE/websocket patterns.

### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Provider | Dependencies |
|---------|-----------|-------------|----------------------|----------|--------------|-------|--------|----------|--------------|
| API-4.1 | `POST /api/agent-jobs` launch endpoint | Validates `policy_snapshot`; runs governance `guard_check` before spawn — fails closed on rejection (FR-5, AC-1.2/AC-1.3). | Launch attempt with a rejecting `guard_check` result never spawns a subprocess; test asserts no-spawn on rejection. | 0.75 pt | python-backend-engineer | sonnet | adaptive | claude | ADP-3.3 |
| API-4.2 | `GET /api/agent-jobs/{id}` detail + `GET .../artifacts` list | Job detail/status (FR-6) + staged-artifacts list distinct from accepted (FR-10). Reuses `reports.py`'s identical-404-for-malformed-vs-missing-id discipline (non-regression on FU-4 partial, see Deferred Items). | 404 responses are indistinguishable for malformed vs. missing `agent_job_id`. | 0.5 pt | python-backend-engineer (delegate) | sonnet | adaptive | **ica** (behind `task-completion-validator` gate) | API-4.1 |
| API-4.3 | `GET /api/agent-jobs/{id}/events` SSE stream | Server-to-client only v1 (FR-7). Resolve **OQ-A** first: check `api/` for an existing SSE/websocket pattern before deciding new-endpoint vs. reuse. Every streamed event has passed the P4.2 write-time redaction guard (AC-2.1/AC-2.2). | SSE delivers stage-transition events within job lifetime; no unredacted payload reaches the wire. | 1 pt | python-backend-engineer (delegate) | sonnet | adaptive | **ica** (behind `task-completion-validator` gate) | API-4.1, SEC-2.3 |
| API-4.4 | `POST /api/agent-jobs/{id}/cancel` | Terminates the subprocess and guarantees credential-file cleanup, reusing SEC-2.2's crash-safe cleanup path (FR-8). | Cancel-mid-run leaves zero staged artifacts promoted (AC-3.4); credential temp file confirmed removed. | 0.5 pt | python-backend-engineer | sonnet | adaptive | claude | SEC-2.2, API-4.1 |
| API-4.5 | `POST /api/agent-jobs/{id}/accept` | Sole write path promoting staged artifacts into Catalog (existing `catalog_service` insert paths) or a report draft (existing `builder_service` block/claim-link APIs); gated by `agent_job_output_requires_review` (FR-9, FR-16). Code-path audit test asserts no other route/service writes directly from agent-job context (AC-3.1–AC-3.3). | Accepted items carry a resolvable `created_by_agent_job_id`; audit test finds zero alternate write paths. | 1 pt | python-backend-engineer | sonnet | extended | claude | API-4.2 |
| API-4.6 | **Seam task (R-P3)**: freeze API contract for FE consumption | Publish a typed fixture/mock of the job detail shape (incl. `policy_snapshot`), artifacts-list shape, and SSE event schema that P4.5 will build against; verify it satisfies the `propagation_contract` fields named in PRD AC-2.3/AC-3.5/AC-4.4/AC-4.5. This is the explicit cross-owner contract-verification task required by Plan Generator Rule R-P3 (FE+BE phases with overlapping consumption). | Fixture committed; each of the 4 referenced ACs' `propagation_contract` field is satisfied by the fixture shape (spot-checked against the PRD text). | 0.25 pt | python-backend-engineer | sonnet | adaptive | claude | API-4.2, API-4.3, API-4.5 |

*(FR-20 CLI parity `rf agent-job launch\|status\|events\|cancel\|accept` is a "Should" and is budgeted as plumbing in P4.7, task VAL-7.6, not here — keeps this phase focused on the API contract per the decisions-block scope.)*

**Phase P4.4 Quality Gates (phase exit gate, per decisions block):**
- [ ] Contract tests pass for all 5 endpoints.
- [ ] No direct-write code path exists from agent-job context into `catalog_service`/`builder_service` other than `POST .../accept` (audited).
- [ ] OQ-A resolved and documented (reuse vs. new SSE endpoint) before API-4.3 is marked done.
- [ ] Seam-task fixture (API-4.6) committed and available to P4.5.
- [ ] `task-completion-validator` review passed (ICA-delegated tasks reviewed with the same rigor as primary-authored tasks).

---

[← Back to plan summary](../public-multiuser-p4-agents-v1.md) | [← Phase 1–2](./phase-1-2-foundations.md) | [Next: Phase 5 →](./phase-5-frontend.md)
