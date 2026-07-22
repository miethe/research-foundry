## Plan Completion Report — Public Multi-User Release Activation (Tier 3)

**Plan**: `docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md`
**Executed via**: `/dev:execute-plan` (wave-driven, direct-implementer orchestration — the phase-owner layer was unavailable because nested subagents lack the `Task` tool in this harness, so Opus dispatched specialists + reviewers directly).
**Worktree/branch**: `feat/public-multiuser-release-activation` (branched from local `main` 7b28842).
**Result**: All 6 phases complete; end-of-feature `karen` APPROVED; squash-merged to `main`.

### Per-wave summary

| Wave | Phase(s) | Commit | Gates |
|------|----------|--------|-------|
| 1 | P1 deployment-mode presets | 60f40c8 | validator APPROVED; FR-2 byte-identical regression green |
| 2 | P2 principal store + composite auth ‖ P4 DI-1 audit + gate | 79daed5 | validator + senior-code-reviewer APPROVED; **karen P2 milestone PASS**; karen flagged audit doc → fixed |
| — | **Mode D human sign-off (ACT-406)** | — | **Human ACCEPTED trusted-cohort scope** (recorded in audit `signoff:`) |
| 3 | P3 admin API | d243ab2 | validator + senior-code-reviewer (REV-P3-001) APPROVED |
| 4 | P5 admin UI ‖ P4 ACT-403 live regression + ACT-406 | 1d53556 | validator APPROVED; a11y-sheriff CHANGES_REQUESTED → fixed |
| 4b | P4 delta-audit (10 admin endpoints) + P5 a11y fix | 3070945 | karen P4-end FIX-REQUIRED → resolved (count 54→64, all CONFINED + regression tests) |
| 5 | P6 testing, docs, deferred specs | 8fbe075 | **karen end-of-feature APPROVED**; validator quality-gate MET (finalize items closed here) |

### Reviewer gates (all mandated gates satisfied)
- **karen P2 security milestone**: PASS (composite auth adversarially verified safe).
- **karen P4-end DI-1 milestone**: CHANGES_REQUESTED (count decay 54→64 + 10 untraced admin endpoints) → **resolved**: delta-audit traced all 10 CONFINED, +8 `TestCrossWorkspaceIsolation` tests, count reconciled to 64.
- **karen end-of-feature**: **APPROVED — clear to squash-merge** (success metrics met in code+tests, DI-1 gate reconciled, deferred items honestly tracked, Mode-D respected, only 8 known-baseline test failures).
- Per-phase `task-completion-validator`: APPROVED (P1, P2/P4-w2, P3, P5/P4-final); P6 quality-gate MET with the two finalize items (frontmatter + karen-recorded) closed at merge.

### Mode D outcome
Human operator accepted the DI-1 audit at **trusted-cohort `multi_user` scope** — NOT adversarial multi-tenant isolation. `multi_user` is startable only when both FR-13 halves hold (audit `status: accepted` + deploy-time `auth.di1_audit_acknowledged`). Gate fail-closed proven by 13 regression tests.

### Deferred items (tracked, not swept)
- **DF-001** OIDC adapter · **DF-002** rbac.db Postgres migration · **DF-003** fine-grained SA scoping · **DF-004** runs/evidence `workspace_id` tenant-isolation (the headline residual risk: runs/claims/evidence have no workspace_id → cross-workspace read + writeback under multi_user; + row 9 agent-jobs workspace spoofing). All 4 design-spec stubs authored; `deferred_items_spec_refs` populated.
- **Findings** (`findings_doc_ref`, accepted): M1 token miss-path timing-shape parity; M2 audit advisory-mode telemetry parity.

### Deploy-time seams / follow-ups
- **ACT-602** live-API browser smoke: documented deploy-time manual-QA seam (backend round-trip + FE component tests cover the logic).
- Operator must set `auth.di1_audit_acknowledged` on the target install for `multi_user` to start.
- Regenerate `ai/symbols-api.json` post-merge (new token_service/admin symbols).

### Validation
- Full backend suite: **2783 passed, 8 pre-existing-baseline failures, 0 new** (the 8 = test_serve_api.py sensitivity-gate ×5, test_assertion_rollout ×2, test_report_anchors ×1).
- Frontend: 1050/1051 (1 pre-existing); `tsc -p tsconfig.app.json` clean; a11y jest-axe + focus-restore green.
