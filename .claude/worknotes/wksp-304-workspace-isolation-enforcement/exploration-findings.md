# WKSP-304 Exploration Findings — Row-Level Workspace Isolation Enforcement

> Source: codebase-explorer scope discovery, 2026-07-08. Input for the PRD and Implementation Plan.
> This is a worknote (agent scratch context), not a deliverable. Verify file:line against runtime truth before editing code.

## 1. What WKSP-304 Is (and why it was deferred)

WKSP-304 is the **row-level workspace-isolation enforcement flip** deferred from the P5 (public multi-user / auth-RBAC) release.

- **Today**: isolation is by **separate filesystem roots per deployment** — NOT row-level `workspace_id` scoping.
- **P5.3 (commit `18b6c17`)** applied the workspace-isolation migration: legacy records were backfilled to `workspace_id = "default"`. Enforcement was **held** (advisory-only) to preserve backfill reversibility and separate the auth contract from enforcement wiring.
- **WKSP-304 flips advisory → enforcing**: mandatory `workspace_id` filtering at the query layer, fail-closed on cross-workspace access.
- **Blocking constraint**: *Must land before any shared-store multi-tenant deployment.* In shared-store mode, advisory-only isolation is a complete security failure — any authenticated user can read/list other workspaces' records. Single-operator deployments (today's default) are safe because all records are `workspace_id="default"` and there is one user.
- Requirement text anchor: P5 `plan-completion.md` line ~47.

## 2. Current Enforcement Architecture (advisory only)

`src/research_foundry/api/auth/scope.py` — `require_workspace_scope(identity, record, ...)`:
- `identity=None` → `"single_operator_trust"` (no check, no log) — the CLI / direct-service path.
- `identity.workspace_id == record.workspace_id` → `"workspace_match"` (allowed).
- mismatch OR `record.workspace_id is None` → logs an advisory event at WARNING, **returns `allowed=True`** (ADVISORY MODE).

Usage today (e.g. `catalog_service.py:~1415`, `builder_service.py`):
- Called **after** fetching from the DB — it is a post-hoc log, not a query filter.
- Passes `identity=None` because the service layer does not yet receive caller identity.
- The advisory telemetry already fed the P5.3 dry-run evaluation (complete).

## 3. The Gap: query-layer vs return-layer

| Layer | Current (P5.3) | Required (WKSP-304) |
|-------|----------------|---------------------|
| Router | Extracts identity from auth middleware | Pass identity down to service |
| Service read | `get_item(paths, id)` — no filtering | `get_item(paths, id, identity)` — add scope filter |
| Query result | Post-hoc advisory log | **Pre-return deny (404) if cross-workspace** |
| Multi-tenant risk | High (leaky) | Fail-closed (denied) |

SQL shape change (must stay parameterized):
```sql
-- current (leaky)
SELECT * FROM catalog_items WHERE catalog_item_id = ?
-- required
SELECT * FROM catalog_items WHERE catalog_item_id = ? AND workspace_id = ?
```

## 4. Scope — files & query points

**Service-layer read methods needing an identity/scope parameter (~20–25):**
| Service | Methods | Query points |
|---------|---------|--------------|
| `services/catalog_service.py` | `get_item`, `list_items`, `count_items`, `get_draft_index`, `list_draft_index`, `get_related_items` | ~10 |
| `services/builder_service.py` | `get_draft`, `list_drafts`, `find_drafts`, `build_report_from_draft` | ~4 |
| `services/agent_job_service.py` | `get_job`, `list_jobs` | ~2 |
| Routers (6 total) | all endpoints calling the above | ~30–40 endpoints |

- **SQL query points to scope**: ~60–80 scattered across the three services.
- **Files touched estimate**: ~12 (6 routers + 4 services + `auth/scope.py` + `config.py`).
- **Lines changed**: ~300–500.

## 5. Risk hotspots

1. **Visibility regressions** — a list endpoint accidentally exposing cross-workspace rows.
2. **Join leaks** — `catalog_items ← LEFT JOIN catalog_links` may surface linked rows from another workspace.
3. **Soft-delete / tombstone leaks** — archived/hidden rows leaking via query predicates.
4. **Single-operator fallback** — `identity=None` (CLI / direct-service) must NOT break; must remain fully functional.
5. **SQL injection** — new WHERE clauses must be parameterized, never string-interpolated.

## 6. Config gate (mirror the P5.6 RBAC pattern)

`src/research_foundry/config.py` already has `auth.rbac_enforcement` with two **fail-closed** invariants:
1. **Advisory forbidden on public bind**: if `rbac_enforcement=disabled` AND `bind_host` is not loopback (`127.0.0.1`/`::1`) → raise `ValueError` at startup.
2. **Enforcement defaults to `auto`**: `auth.provider != "none"` → enforcement required; `provider == "none"` (single-operator) → advisory allowed.

WKSP-304 adds a **parallel, orthogonal** flag `workspace_isolation_enforcement` with the same `auto|enabled|disabled` semantics and the same two fail-closed invariants. It is separate from RBAC enforcement (they are independent gates). Reuse the RBAC validation code path as the template.

## 7. Test regression surface

- **Existing**: `tests/**/test_workspace_migration_service.py` (backfill + advisory logging), `tests/**/test_p5_regression_suite.py` (multi-phase incl. isolation). Advisory path is covered; **enforcement path is untested**.
- **New tests needed (~40–50):**
  - 2 workspaces × {read, list, mutate} × {allowed, denied} ≈ 12 core scenarios.
  - Single-operator fallback (`identity=None`) ≈ 10.
  - Join / leak edge cases ≈ 15.
  - Config validation (loopback guard, `auto` logic) ≈ 5.

## 8. Complexity signals for estimation

- **Positive**: schema already migrated/backfilled; advisory infra exists (flag flip); RBAC enforcement is a copyable pattern; raw SQL (no ORM retrofit).
- **Risk**: service-layer identity threading across 4+ files / 20+ signatures; ~60–80 WHERE clauses; 30+ endpoints × 2 workspaces regression matrix; must prove `identity=None` still works.
- **Explorer estimate**: **8–10 pts, Tier 2**. No auth-core changes; service-layer threading + query scoping + regression-heavy.

## 9. Key files reference

| File | Role in WKSP-304 |
|------|------------------|
| `src/research_foundry/api/auth/scope.py` | Advisory enforcement (lines ~1–23, ~68–147). Wire the enforcement flag here; flip `allowed=True` → deny when enforcing. |
| `src/research_foundry/config.py` | Add `workspace_isolation_enforcement` mirroring `auth.rbac_enforcement` + loopback validation. |
| `src/research_foundry/services/catalog_service.py` | Primary target: ~10 query points; advisory call ~line 1415. |
| `src/research_foundry/services/builder_service.py` | ~4 query points; advisory call pattern. |
| `src/research_foundry/services/agent_job_service.py` | ~2 query points (jobs). |
| `docs/dev/architecture/workspace-migration-runbook.md` | Migration context (applied, not enforced); rollback procedure. |

## 10. Related planning docs (for `related_documents`)

- `docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-3-workspace-migration.md`
- `docs/project_plans/human-briefs/public-multiuser-p5-auth-rbac.md`
- P5 `plan-completion.md` (WKSP-304 deferral rationale, ~line 47)
