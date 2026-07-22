## Phase 2 Completion Note — Non-Human Principal Store + Auth Resolution

**Status**: COMPLETED
**Reviewer gates**: task-completion-validator APPROVED · senior-code-reviewer APPROVED (no blockers/high) · karen milestone PASS (P2 auth adversarially verified safe)
**Isolation**: none (shared worktree feat/public-multiuser-release-activation). **Committer**: orchestrator (Opus), Wave-2 commit.

### Tasks (ACT-201..206) — all completed
- ACT-201 schema: `service_accounts` + `access_tokens` tables (rbac.db v2→v3, idempotent CREATE IF NOT EXISTS). OQ-2 resolved: single id + `principal_type` discriminator (service | user_pat) + app-level integrity.
- ACT-202 `token_service.py` (under services/, OQ-1): issuance/verification/revocation; hash-at-rest (HMAC-SHA256), shown-once plaintext, `hmac.compare_digest`.
- ACT-203 composite auth chain in `middleware/auth.py`: token-store-first → provider fallthrough, fail-soft→fallthrough (never fail-open).
- ACT-204 FR-12 agent-job SA binding: activates ONLY under `multi_user`; single_user `created_by` byte-unchanged (verified).
- ACT-205 AC-2 four-credential-state suite + secret static-scan.
- ACT-206 OQ-4: `last_used_at` throttled/best-effort, fail-open.

### Security invariants (verified by senior-code-reviewer + karen)
- No plaintext secret persisted/logged/echoed (static-scan test enforces).
- Constant-time real-path compare + dummy compare on prefix miss.
- FR-9 PAT role-ceiling re-checked at every resolution (fail-closed, not cached).
- Composite chain cannot bypass provider or skip RBAC/isolation.

### Validation
- 84/84 across token_service/composite_auth/agent_job_identity/audit_rbac/deployment_mode (validator re-run).
- Full suite: only the 8 known pre-existing unrelated failures; zero regressions from merged P2+P4 state.

### Tracked follow-ups (non-blocking, from senior-code-reviewer)
- M1: equalize CPU work on token miss-path vs hit-path (residual timing gap; negligible under LAN + 256-bit entropy).
- M2: route audit scope check through `require_workspace_scope` for advisory-mode telemetry parity with other WKSP-304 consumers.
- karen Low: `verify_token` re-bootstraps schema per request (perf/lock-contention under load).
These are carried to P6 findings / follow-up, not blocking P2.
