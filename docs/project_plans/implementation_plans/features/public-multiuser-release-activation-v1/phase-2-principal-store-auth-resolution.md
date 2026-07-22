---
title: "Phase 2: Non-Human Principal Store + Auth Resolution"
schema_version: 2
doc_type: phase_plan
it_schema: 1
status: draft
created: 2026-07-22
updated: 2026-07-22
feature_slug: public-multiuser-release-activation
phase: P2
phase_title: "Non-Human Principal Store + Auth Resolution"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
integration_owner: python-backend-engineer
entry_criteria:
  - "P1 (ACT-101) landed — deployment_mode resolver exists for gating agent-job binding."
exit_criteria:
  - "AC-2 (4 credential states) green."
  - "karen milestone review passed (security-sensitive)."
  - "task-completion-validator pass."
---

# Phase 2: Non-Human Principal Store + Auth Resolution

[← Back to main plan](../public-multiuser-release-activation-v1.md)

**Estimate**: 14 pts
**Dependencies**: P1 (ACT-101) — runs in `batch_2`, **parallel to P4's audit** (ACT-401/ACT-402)
**Assigned Subagent(s)**: `python-backend-engineer` + `data-layer-expert` (schema, ACT-201); `backend-architect` (composite-auth-chain design sanity); `senior-code-reviewer` (token secret handling)
**Model**: sonnet | **Effort**: extended (security-sensitive: token hashing, composite auth ordering)
**Mode**: D-adjacent — standard delegation with mandatory `senior-code-reviewer` + `karen` review before phase seal; no production secret-handling code ships without that review passing.

## Overview

This is the security-sensitive core of the feature: two new tables extending `rbac.db`, a token issuance/verification service with hash-at-rest and constant-time comparison, a composite auth-resolution chain that lets machine tokens and human (Clerk) sessions coexist without a new `auth.provider` enum value, and the agent-job identity binding that decouples a job's triggering caller from its execution identity under `multi_user`.

## Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|---------------|
| ACT-201 | Token store schema | Extend `rbac_store.py` with `service_accounts` (id, name, workspace_id, role, description, created_by, created_at, disabled_at) and `access_tokens` (id, principal_type, principal_id, workspace_id, role, token_hash, token_prefix, created_by, created_at, expires_at, revoked_at, last_used_at) tables, `CREATE TABLE IF NOT EXISTS` per existing idempotent-migration convention. Resolve OQ-2 (discriminator + app-level integrity, no partial FK on SQLite). | FR-6 satisfied; tables idempotent on repeated migration; OQ-2 resolved and documented in code comment. | 3 pts | data-layer-expert | sonnet | extended | ACT-101 |
| ACT-202 | Token issue/verify/revoke service | New `token_service.py` (resolve OQ-1: land under `services/`, peer to `rbac_store.py`/`audit_service.py`): opaque-secret generation (≥256 bits), salted hash-at-rest (`hashlib.sha256`/`hmac`), short non-secret prefix for lookup, constant-time verify, revoke (`revoked_at`), expiry (`expires_at`). PAT role-ceiling (FR-9) enforced at issuance AND re-checked at resolution time. | FR-7, FR-8, FR-9, FR-10 satisfied; zero plaintext secret ever logged or persisted (static-scan test). | 4 pts | python-backend-engineer | sonnet | extended | ACT-201 |
| ACT-203 | Composite auth chain | `AuthProviderMiddleware` resolves Bearer credentials by checking `access_tokens` first (indexed prefix lookup + constant-time hash compare, including dummy-hash compare on prefix-miss to close the timing side channel); on a hit, resolves identity directly; on a miss, falls through to the configured `auth.provider` adapter unchanged. | FR-11 satisfied; no new `auth.provider` enum value introduced; timing side-channel closed. | 2 pts | python-backend-engineer | sonnet | extended | ACT-202 |
| ACT-204 | Agent-job identity binding | `agent_job_service.py`: when `deployment_mode=multi_user`, resolve job execution identity from `agents.default_service_account_id` (new config key) instead of the triggering caller's identity; record BOTH triggering and executing identity in `audit_event`. Binding activates ONLY under `multi_user` — `single_user` agent-job launches keep today's identity resolution unchanged (Risk mitigation, decisions-block §3). | FR-12 satisfied; `single_user` regression assertion passes (AC-5 below). | 2 pts | python-backend-engineer | sonnet | extended | ACT-203, P1 (ACT-101) |
| ACT-205 | Composite-auth + resilience test suite | Unit + integration tests covering: (1) the 4 credential states in AC-2 — valid token / expired-or-revoked token / Clerk JWT / no credential; (2) AC-4 resilience — missing/expired token resolves as a normal 401, never a 500; (3) AC-5 — `single_user` agent-job launches assert identity resolution is byte-unchanged from pre-feature behavior. | AC-2, AC-4, AC-5 all green. | 2 pts | python-backend-engineer | sonnet | adaptive | ACT-202, ACT-203, ACT-204 |
| ACT-206 | [SEAM] Schema↔service integration verification | Integration-owner seam task (R-P3): verify every `token_service.py` CRUD call against `rbac_store.py`'s new helpers (`create_service_account`, `create_access_token`, `verify_access_token`, `revoke_token`, `list_tokens`) round-trips correctly end-to-end (issue → store → verify → revoke → verify-denied), closing the seam between the `data-layer-expert`-owned schema (ACT-201) and the `python-backend-engineer`-owned service (ACT-202). | Round-trip test passes for both `principal_type=service` and `principal_type=user_pat`. | 1 pt | python-backend-engineer + data-layer-expert | sonnet | adaptive | ACT-201, ACT-202 |
| REV-P2-001 | Reviewer gate: senior-code-reviewer | Mode E review of token secret handling (ACT-202) — hash-at-rest, constant-time compare, no plaintext leak paths. | Reviewer confirms no plaintext secret in any code path; approves before phase can proceed to REV-P2-002. | gate | senior-code-reviewer | sonnet | adaptive | ACT-202 |
| REV-P2-002 | Reviewer gate: karen milestone (security-sensitive) | Mode E review of the full composite-auth-chain + token-store design against the decisions-block risk hotspots (secret leaks, PAT escalation, chain misordering). | karen approves; treat silence as a blocker, not a pass. | gate | karen | opus | adaptive | ACT-205, REV-P2-001 |
| REV-P2-003 | Reviewer gate: task-completion-validator | Standard phase-completion review. | Validator confirms FR-6..FR-12 satisfied. | gate | task-completion-validator | sonnet | adaptive | REV-P2-002 |

**Phase point subtotal**: 14 pts (reviewer-gate rows excluded).

## Structured Acceptance Criteria

#### AC-2: Composite auth resolution chain resolves correctly under all four credential states
*(Reproduced from PRD §11; this is P2's primary exit-gate AC.)*
- target_surfaces:
    - src/research_foundry/api/middleware/auth.py
    - src/research_foundry/services/token_service.py
    - src/research_foundry/api/auth/adapters/clerk.py
- propagation_contract: >
    `AuthProviderMiddleware` checks the Bearer credential against `access_tokens` (prefix lookup +
    hash compare) before invoking the configured provider adapter; a hit short-circuits to
    token-store identity resolution, a miss delegates to the configured provider.
- resilience: >
    An expired or revoked token resolves as "no match" (falls through to the configured provider,
    which will also reject it) rather than raising — the request ends in a normal 401, not a 500.
    A malformed/absent Authorization header never reaches the token-store lookup and resolves
    `identity=None` exactly as today.
- visual_evidence_required: false
- verified_by:
    - ACT-205

#### AC-4 (R-P2 guard — implicit resilience AC): FE/consumer handles missing or expired token gracefully
- target_surfaces:
    - src/research_foundry/api/middleware/auth.py
    - src/research_foundry/services/agent_job_service.py
    - frontend/runs-viewer/src/api/client.ts
- propagation_contract: >
    A missing, malformed, expired, or revoked Bearer credential resolves to a standard 401 response
    from the middleware; the frontend API client's existing 401-handling path (session-expired
    redirect/prompt) applies unchanged — no new error shape is introduced for the token-store path.
    `agent_job_service.py` treats a failed service-account resolution the same way a failed human
    resolution is treated today (job launch refused, not silently retried under a different identity).
- resilience: >
    No 500s on this path under any of the four credential states; the client-side consumer never
    receives an ambiguous or novel error shape it doesn't already know how to handle.
- visual_evidence_required: false
- verified_by:
    - ACT-205
    - ACT-601 (Phase 6, cross-phase integration pass)

#### AC-5 (R-P2 guard — implicit resilience AC): `single_user` path unchanged by agent-job identity binding
- target_surfaces:
    - src/research_foundry/services/agent_job_service.py
    - src/research_foundry/config.py
- propagation_contract: >
    FR-12's service-account execution-identity binding is gated on `deployment_mode == "multi_user"`
    at the point `agent_job_service.py` resolves execution identity; when `deployment_mode ==
    "single_user"` (including the unset/default case), the binding branch is never entered and
    identity resolution follows the exact pre-feature code path.
- resilience: >
    A regression test asserts `single_user` agent-job launches (with `agents.enabled=true`) produce
    byte-identical resolved identity/audit-log shape to the pre-feature baseline — this is a
    non-negotiable acceptance gate for ACT-204, mirroring FR-2's treatment in Phase 1.
- visual_evidence_required: false
- verified_by:
    - ACT-205

## Quality Gates

- [ ] `service_accounts`/`access_tokens` tables idempotent per `rbac_store.py` migration discipline.
- [ ] Zero plaintext secret in any persisted row, log line, or `audit_event` payload (static-scan test).
- [ ] Constant-time comparison used for all token verification paths, including prefix-miss.
- [ ] AC-2 (4 credential states), AC-4 (resilience), AC-5 (single_user unchanged) all green.
- [ ] `senior-code-reviewer` pass (REV-P2-001).
- [ ] `karen` milestone pass (REV-P2-002) — do not proceed to P3 without this.
- [ ] `task-completion-validator` pass (REV-P2-003).

## Key Files & Integration Points

- `src/research_foundry/services/rbac_store.py` (392 lines) — new tables + CRUD helpers.
- `src/research_foundry/services/token_service.py` (new file) — issuance/verification/revocation logic.
- `src/research_foundry/api/middleware/auth.py` (192 lines) — composite-chain change.
- `src/research_foundry/services/agent_job_service.py` (1,190 lines) — execution-identity binding; sizable but under the 2K H7 threshold — standard editing discipline applies, no mandated guardrail.
- `src/research_foundry/api/auth/adapters/local_static.py` — reference pattern for constant-time comparison (do not modify; reuse the pattern).

## Integration Owner

**`python-backend-engineer`** is the declared `integration_owner` for this phase (R-P3): ≥2 owner specialties (`data-layer-expert` for schema, `python-backend-engineer` for service/middleware/agent-job) with overlapping `files_affected` (`rbac_store.py` touched by both the schema task and, transitively, every CRUD call the service makes). ACT-206 is the dedicated seam task verifying the propagation contract between the schema layer and the service layer holds end-to-end.

---

[← Phase 1](./phase-1-deployment-mode-presets.md) | [← Back to main plan](../public-multiuser-release-activation-v1.md) | [Next: Phase 3 →](./phase-3-admin-api.md)
