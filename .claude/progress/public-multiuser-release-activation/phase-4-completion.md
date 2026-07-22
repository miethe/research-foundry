## Phase 4 Completion Note — DI-1 Audit + Enforcement Flip (WAVE-2 SCOPE)

**Status**: IN_PROGRESS — wave-2 subtasks done; ACT-403 (live-session regression, needs P2+P3) and ACT-406 (human Mode D sign-off) intentionally pending.
**Reviewer gates**: task-completion-validator APPROVED (wave-2 scope) · karen milestone CHANGES_REQUESTED → audit-doc must-fixes applied and re-verified. **Mode D human sign-off: NOT YET OBTAINED — gate remains fail-closed.**
**Committer**: orchestrator (Opus), Wave-2 commit.

### Done this wave
- ACT-401 — `docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md`: 54-endpoint enumeration (grep-reconciled, matches `@router.*` count exactly), documented method, per-surface verdicts, headline residual-risk section, `authorization_scope` (trusted-cohort-only) in frontmatter. Found+remediated a real cross-tenant leak: `GET /api/audit` (client-controlled workspace filter defaulting to all) and `GET /api/audit/{id}` (no workspace check) — `audit_service.py` / `routers/audit.py`, verified by `test_audit_rbac.py::TestAuditCrossTenantScoping`. `status: pending-human-signoff` (NOT accepted).
- ACT-402 — condition (d) wired into `Config.deployment_mode_validate()` (FR-13 two-part: `auth.di1_audit_acknowledged` AND artifact `status == accepted`); missing/malformed artifact fails closed; each half named independently.
- ACT-404 — condition-(d) gate tests (`TestAC3FullFourConditionSuite`).
- SERVICE_CONTRACT.md updated with the DI-1 gate contract.

### karen must-fixes applied to the audit doc (documentation-only)
1. Endpoint count reconciled 61→54 (removed the non-reproducing count that echoed the WKSP-304 failure).
2. Trusted-cohort scope boundary elevated to frontmatter + top of Scope Boundary Statement.
3. Rows 10–12 (runs/claims/evidence have NO workspace_id) promoted to headline residual risk; row 12 (writeback-approve) reclassified as cross-tenant ACTION.
4. Row 21 split: `verify_access_token` reachable+scoped (row 22) vs unwired write fns (row 23).
5. FR-12 audit attribution flagged spoofable until row 9 (client-supplied workspace_id) fixed.

### Deferred / surfaced for the human decision (NOT code-remediated this feature)
- Rows 10–12: runs/claims/evidence data model has no workspace_id → in multi_user any authenticated caller can read every run and dispatch writebacks cross-workspace. **Headline residual risk.**
- Row 9: `POST /agent-jobs` trusts client-supplied workspace_id.
These are legitimately deferrable per karen, but MUST be surfaced as the operator's explicit accept-or-block decision at Mode D sign-off.

### Remaining before P4 seals
- ACT-403 live-session regression (Wave 4, after P2+P3).
- ACT-406 human Mode D sign-off → only then may `status: accepted` be set on the audit artifact.
- karen P4-end review (after ACT-403).
