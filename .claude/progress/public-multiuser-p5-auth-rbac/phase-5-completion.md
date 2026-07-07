## Phase 5 Completion Note

**Status**: PASS
**Validator verdict**: PASS — all 8 exit criteria satisfied; 6/6 mutation wiring confirmed, fail-open guarantee verified structurally + fault-injection tests, audit tables exclusively in rbac_store DDL, is_healthy_for_exposure correctly isolated, route ordering safe, durability test passes, flake8 clean.
**Isolation**: shared (main branch)

### Files Changed

- `src/research_foundry/services/audit_service.py` (new) — AuditEvent dataclass, MUTATION_TYPES frozenset (6 values), record_event (fail-open), list_events (cursor-paginated), get_event, AuditHealth dataclass, health_check, get_health_state, is_healthy_for_exposure
- `src/research_foundry/services/rbac_store.py` — schema v2: added audit_event and audit_health DDL tables; bumped RBAC_SCHEMA_VERSION 1→2
- `src/research_foundry/services/catalog_service.py` — record_event(catalog_mutation/import_run) at import_run():1108 after commit
- `src/research_foundry/services/builder_service.py` — record_event(report_edit/save_draft) at _save_draft():294; record_event(report_edit/delete_draft) at delete_draft():340
- `src/research_foundry/services/source_cards.py` — record_event(artifact_accepted/ingest_source) at ingest_source():299
- `src/research_foundry/api/routers/reports.py` — record_event(publish_preview) at publish_preview():700 (denied) + 726 (success)
- `src/research_foundry/services/writeback.py` — record_event(writeback) at writeback():1103 (success) + 1116 (RFError failure)
- `src/research_foundry/api/routers/agent_jobs.py` — record_event(agent_job_launched/launch_job) at:231 after spawn_job
- `src/research_foundry/api/routers/audit.py` (new) — GET /api/audit (cursor-paginated list), GET /api/audit/health (degraded-state visibility), GET /api/audit/{audit_event_id}
- `src/research_foundry/api/app.py` — import + include_router(audit_router); @app.on_event("startup") audit health probe
- `src/research_foundry/cli_commands.py` — audit_app Typer sub-app: rf audit list, rf audit show, rf audit health (Rich Panel on degraded, exit 1)
- `tests/unit/test_audit_service.py` (new) — 47 tests: record/list/get round-trips, cursor pagination, fault-injection, taxonomy completeness, idempotent schema, health-probe healthy/degraded/durability/exposure-gate

### Batch Summary

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | AUDIT-001 | completed | python-backend-engineer |
| 2 | AUDIT-002, AUDIT-003 | completed | python-backend-engineer (parallel) |
| 3 | AUDIT-004 | completed | python-backend-engineer |
| 4 | validator-gate | PASS | task-completion-validator |

### Deviations from Plan

- **agent_jobs.py exists**: Phase plan assumed `api/routers/agent_jobs.py` didn't exist (P4 N/A). P4 had already merged (`2550512`), so AUDIT-002 wired `agent_job_launched` at `agent_jobs.py:231` instead of documenting it as N/A. Result: **6/6 governed mutation types wired** (better than the plan's 5+N/A).
- **AUDIT-900**: Marked skipped/N/A per plan — this is a forward-referenced conditional AC for Phase 6/8 admin UI (task ID reserved, not renumbered).
- **cli.py not directly touched**: AUDIT-003 found that `cli.py` already uses `cli_commands.register(app)` via `_wire()` pattern, which auto-wires all sub-apps. No explicit `add_typer` call needed in `cli.py`.

### The 6 Governed Mutation Types (all wired)

| # | Mutation Type | Call-site | File |
|---|--------------|-----------|------|
| 1 | catalog_mutation | import_run():1108 | services/catalog_service.py |
| 2 | report_edit | _save_draft():294, delete_draft():340 | services/builder_service.py |
| 3 | agent_job_launched | launch job endpoint:231 | api/routers/agent_jobs.py |
| 4 | artifact_accepted | ingest_source():299 | services/source_cards.py |
| 5 | publish_preview | publish_preview():700+726 | api/routers/reports.py |
| 6 | writeback | writeback():1103+1116 | services/writeback.py |

### Commit Refs

- `742859e` — feat(audit): AUDIT-001 — audit_event schema + audit_service.py interface
- `7f5b566` — feat(audit): AUDIT-003 — rf audit list/show CLI + GET /api/audit read API
- `fa86609` — feat(audit): AUDIT-002 — wire audit_service.record_event into all 6 governed mutation types
- `298a72a` — feat(audit): AUDIT-004 — health-check probe, persisted state, startup warning, exposure gate

### Escalation Reason

N/A

### Follow-Up Recommendations

1. **P5.9 regression pass**: confirm `GET /api/audit*` gains `require_role("admin")` gate (flagged as TODO in audit.py, deferred pending P5.2 dependency). Also confirm P5.6 calls `audit_service.is_healthy_for_exposure()` before allowing shared/public exposure actions.
2. **P5.6 integration**: `audit_service.is_healthy_for_exposure(paths)` is built and tested here; P5.6 must wire it into its sharing/publish-preview decision point.
3. **agent_jobs.py accept endpoint**: The `POST /agent-jobs/{job_id}/accept` endpoint (artifact acceptance from staging into catalog/report) is a potential 7th governed mutation type that could warrant its own `artifact_accepted` audit row from the agent_jobs path. Not required by this phase but flag for P5.9/future review.
4. **AUDIT-900**: Phase 6 (P5.6) or Phase 8 (P5.8) must resolve this task (implement or N/A-with-rationale) when admin audit-log UI scope is decided. Task ID must not be renumbered.
