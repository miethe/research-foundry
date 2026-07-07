## Phase 2 Completion Note

**Status**: PASS
**Validator verdict**: PASS — all 156 tests pass; all primary ACs met; one remediation cycle (rf source-card create gap in CLI surface classification)
**Isolation**: shared (ran on main directly; worktree-agent-a12d4bf6fba1dd656 branch present but phase ran on main)
**Commits**: d72b542 (main implementation), eb6b1bb (remediation fix)

---

### Mutation-Route Inventory (RBAC-901 route-sweep result)

19 total mutation routes across 3 existing HTTP surfaces — 0 ungated:

| Router | Method | Path | Role set |
|--------|--------|------|----------|
| catalog | POST | `/catalog/import/run/{run_id}` | owner, admin, researcher |
| catalog | POST | `/catalog/import` | owner, admin, researcher |
| reports | POST | `/reports` | owner, admin, researcher |
| reports | DELETE | `/reports/{id}` | owner, admin |
| reports | POST | `/reports/{id}/versions` | owner, admin, researcher |
| reports | POST | `/reports/{id}/versions/{vid}/restore` | owner, admin |
| reports | POST/PATCH/DELETE | blocks (3 routes) | owner, admin, researcher / owner, admin |
| reports | POST/DELETE | claim-links (2 routes) | owner, admin, researcher |
| reports | POST/DELETE | source-links (2 routes) | owner, admin, researcher |
| reports | POST | `/verify` | owner, admin, researcher |
| reports | POST | `/publish-preview` | owner, admin |
| agent_jobs | POST | `/agent-jobs` | owner, admin |
| agent_jobs | POST | `/agent-jobs/{id}/cancel` | owner, admin |
| agent_jobs | POST | `/agent-jobs/{id}/accept` | owner, admin |
| runs | — | (0 mutation routes — audit documented in runs.py comment) | N/A |

`agent_jobs.py` — **deviation from plan**: this router already existed from P4 (plan stated N/A-until-P4). Applied `require_role(owner, admin)` to all 3 POST routes rather than leaving a forward-compat note only. This is strictly better than the plan's N/A path.

---

### Files Changed

| File | Purpose |
|------|---------|
| `src/research_foundry/api/auth/rbac.py` (NEW) | `ROLE_PERMISSIONS` capability matrix + `require_role()` dependency factory + CLI surface classification docstring |
| `src/research_foundry/api/auth/provider.py` | Additive JSON serialization note on `AuthIdentity.roles` (no behavioral change) |
| `src/research_foundry/api/routers/catalog.py` | `require_role` on 2 POST mutation routes |
| `src/research_foundry/api/routers/reports.py` | `require_role` on 14 mutation routes |
| `src/research_foundry/api/routers/runs.py` | RBAC-005 audit comment (0 mutations confirmed, documented explicitly) |
| `src/research_foundry/api/routers/agent_jobs.py` | `require_role(owner, admin)` on 3 POST routes (P4 router existed) |
| `tests/unit/test_rbac.py` (NEW) | require_role unit tests — all 5 roles × allow/deny matrix; RBAC-900 contract |
| `tests/unit/test_rbac_catalog.py` (NEW) | Per-route 403/200 tests for catalog.py mutations |
| `tests/unit/test_rbac_reports.py` (NEW) | Per-route 403/200 tests for reports.py mutations |
| `tests/unit/test_rbac_route_sweep.py` (NEW) | RBAC-901 programmatic route-sweep assertion |
| `tests/unit/test_cli_mutation_surface.py` (NEW) | RBAC-006 CLI/service mutation-surface classification contract test |

---

### Batch Summary

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | RBAC-001 | completed | python-backend-engineer |
| 2 | RBAC-002, RBAC-900 | completed | python-backend-engineer |
| 3 | RBAC-003, RBAC-004, RBAC-005 | completed | python-backend-engineer |
| 4 | RBAC-901, RBAC-006 | completed | python-backend-engineer |
| R1 (remediation) | RBAC-006 gap (rf source-card create) | completed | python-backend-engineer |

**Total tests**: 156 (155 post-main-implementation + 1 remediation)

---

### Validator History

- **Round 1**: FAIL (low) — `rf source-card create` absent from rbac.py docstring and test_cli_mutation_surface.py (AC RBAC-P2.2 gap). All other ACs: PASS.
- **Round 2 (post-remediation)**: PASS — 156 tests, 0 failures, all primary ACs met.

---

### Escalation Reason

N/A — no Mode D triggers hit. `agent_jobs.py` existing from P4 was a plan deviation handled in-phase (strictly better outcome: gated immediately rather than left as a forward-compat stub).

---

### Human Gate #2

**PENDING** — RBAC-before-exposure sign-off (Human Gate #2 per decisions block §1) is required before any public/shared-LAN exposure of this phase's work. Technical completion is confirmed (task-completion-validator PASS); exposure gate is a human decision, not a task gate.

Preconditions for requesting sign-off are now met:
- RBAC-901 green — 0 ungated mutation routes across all existing HTTP surfaces
- RBAC-006 green — CLI surface classified admin-only/single-operator-trust, no HTTP bypass
- task-completion-validator signed off (Round 2 PASS)

---

### Follow-Up Recommendations

1. **Human Gate #2**: Request sign-off before any public/LAN exposure. The route-sweep result (19 routes, 0 ungated) and CLI surface classification test are the evidence base for the sign-off conversation.
2. **P5.3 (workspace isolation)**: When it lands, `require_role` enforcement composes with workspace scoping — no changes needed to rbac.py, only additive work in P5.3's router layer.
3. **P5.6 (sharing/publish gates)**: `reports.py publish_preview` carries `require_role(owner, admin)` from this phase; P5.6 adds D13 sensitivity checks on top — confirm they compose correctly (role gate fires before D13 check, per the locked design).
4. **Symbols update**: Run `/analyze:symbols:symbols-update` after P5.2 — 5 new test files and 1 new auth module added.
