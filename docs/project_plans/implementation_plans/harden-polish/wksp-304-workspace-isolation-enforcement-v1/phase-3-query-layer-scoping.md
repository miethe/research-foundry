---
schema_version: 2
doc_type: phase_plan
title: "WKSP-304 Phase 3: Query-Layer Scoping"
status: draft
created: 2026-07-08
phase: "P3"
phase_title: "Query-layer scoping (3 services) — the largest, single-owner phase"
prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
feature_slug: wksp-304-workspace-isolation-enforcement
entry_criteria: ["P1 complete (flag exists)", "P2 complete (identity reaches router boundary)"]
exit_criteria:
  - "All ~60-80 query points carry the flag-gated predicate; parameterized; existing suite green in advisory mode"
  - "AC-2/AC-4 code-review checklist (TASK-3.6) signs off: every AC-2 method scoped, every JOIN/tombstone closed"
  - "This checklist sign-off is the hard entry_criteria for Phase 4 — see decisions block D4 / Risk 1"
---

# Phase 3: Query-Layer Scoping (3 Services)

[Back to parent plan](../wksp-304-workspace-isolation-enforcement-v1.md) | [Previous: Phase 1-2](./phase-1-2-config-identity.md)

**Duration**: ~2-3 days (largest phase)
**Dependencies**: P1 + P2 complete
**Assigned Subagent(s)**: `data-layer-expert` (primary, SQL predicate correctness — single owner, do not fan across 3 agents by service), `backend-architect` (secondary, gate-helper contract review)

**Why single-owner**: The JOIN-leak reasoning and predicate-shape consistency across `catalog_service.py`, `builder_service.py`, and `agent_job_service.py` must be held in one context. Splitting this phase by service across 3 agents risks inconsistent predicate idioms and split-brain on leak coverage — explicitly called out in decisions block §2.

**Behavioral guarantee (D4)**: every predicate added in this phase is **flag-gated inert** — when `workspace_isolation_enforcement` resolves to advisory (the default state until Phase 4), these queries run exactly as they do today. This phase changes zero observable behavior; it only builds the machinery Phase 4 arms.

**Verifies**: AC-2 (Query-layer `workspace_id` scoping) and AC-4 (No join or tombstone leaks) — target_surfaces: `catalog_service.py` (`get_item`, `list_items`, `count_items`, `get_draft_index`, `list_draft_index`, `get_related_items`), `builder_service.py` (`get_draft`, `list_drafts`, `find_drafts`, `build_report_from_draft`), `agent_job_service.py` (`get_job`, `list_jobs`).

---

## Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------------------|----------|-------------|-------|--------|---------------|
| TASK-3.0 | Pre-work exploration: caller-set + backend-parameter-style confirmation | Two exploration line-items before any predicate is written: (1) **Risk-4 mitigation** — re-run `grep -rln "catalog_service\|builder_service\|agent_job_service" src/research_foundry/api/routers/*.py` to reconfirm the exact caller set (PRD assumption: 3 direct callers — `catalog.py`, `agent_jobs.py`, `reports.py`); any 4th caller found is a Risk-4 finding, escalate before proceeding. (2) **OQ-3 resolution** — confirm whether Research Foundry supports Postgres as a store backend in addition to SQLite. If Postgres is supported, predicates must use its native parameter style (`%s`/named) alongside SQLite's `?`; if SQLite-only, proceed with `?` placeholders exclusively. | Caller set reconfirmed and documented (matches PRD assumption or a Risk-4 finding is filed); backend parameter style determined and stated explicitly for TASK-3.1-3.4 to follow. | 0.2 pt | data-layer-expert | sonnet | extended | None |
| TASK-3.1 | Scope `catalog_service.py` (~10 query points) | Add `identity: AuthIdentity \| None = None` parameter to `get_item`, `list_items`, `count_items`, `get_draft_index`, `list_draft_index`, `get_related_items`. When `identity is not None` AND enforcement resolves active, add `AND workspace_id = :workspace_id` (parameterized per TASK-3.0's determined style) bound to `identity.workspace_id`. When `identity is None`, query is byte-identical to pre-WKSP-304. | Every listed method accepts the new parameter; predicate is flag-gated and parameterized; a query-text/query-plan diff test per method proves `identity=None` produces identical SQL to the pre-change baseline. | 1 pt | data-layer-expert | sonnet | extended | TASK-3.0 |
| TASK-3.2 | Scope `builder_service.py` (~4 query points) | Same pattern for `get_draft`, `list_drafts`, `find_drafts`, `build_report_from_draft`. | Same per-method acceptance criteria as TASK-3.1, scoped to this file. | 0.6 pt | data-layer-expert | sonnet | extended | TASK-3.0 |
| TASK-3.3 | Scope `agent_job_service.py` (~2 query points) | Same pattern for `get_job`, `list_jobs`. | Same per-method acceptance criteria as TASK-3.1, scoped to this file. | 0.4 pt | data-layer-expert | sonnet | extended | TASK-3.0 |
| TASK-3.4 | Close JOIN + tombstone leaks (AC-4) | For every LEFT JOIN or subselect in the 3 services that can surface rows from a table other than the primary `workspace_id`-scoped table (e.g., `catalog_items <- LEFT JOIN catalog_links`), apply the same flag-gated `workspace_id` predicate to the joined side, not only the primary side. Confirm soft-deleted/tombstoned rows retain their original `workspace_id` and remain subject to the predicate — deletion-state filtering must never bypass workspace scoping. | Every JOIN target and every tombstone/delete-state filter in the 3 services carries the same predicate as its primary-table counterpart; the code-review checklist item "does every JOIN target and every tombstone filter also carry workspace_id?" is answered yes for every instance found. | 0.5 pt | data-layer-expert | sonnet | extended | TASK-3.1, TASK-3.2 |
| TASK-3.5 | Gate-helper contract review | `backend-architect` reviews the shared predicate-construction helper (if one is introduced to avoid repeating the flag-check + bind-param logic across ~20-25 methods) for consistency with the eventual Phase 4 deny-consumption contract — i.e., confirm the helper's return shape will support Phase 4's `allowed=False` flip without a rewrite. This is a design-review task, not new query code. | Backend-architect signs off that the predicate-construction helper's contract is stable for Phase 4 to consume without modification. | 0.15 pt | backend-architect | sonnet | extended | TASK-3.1, TASK-3.2, TASK-3.3 |
| TASK-3.6 | **P3 exit-gate: 100%-coverage checklist (hard gate for Phase 4 entry)** | Enumerate every method in AC-2's target_surfaces list (all ~20-25 methods across the 3 services) in a checklist; for each, confirm: (a) `identity` parameter present, (b) predicate is flag-gated and parameterized, (c) `identity=None` produces byte-identical SQL, (d) any JOIN/tombstone paths for that method are closed per TASK-3.4. This checklist's sign-off is the **single non-negotiable precondition for Phase 4 to begin** (decisions block D4, Risk 1 — see parent plan's P4 `entry_criteria`). | 100% of enumerated methods checked off; checklist artifact reviewed and passed by `task-completion-validator` before any Phase 4 task is dispatched. | 0.15 pt | data-layer-expert | sonnet | extended | TASK-3.1, TASK-3.2, TASK-3.3, TASK-3.4, TASK-3.5 |

**Phase 3 total**: 3 pts (matches decisions block §4 estimation anchor).

---

## Quality Gates

- [ ] All ~60-80 query points across the 3 services carry the flag-gated predicate, parameterized (no string interpolation).
- [ ] `identity=None` produces byte-identical SQL for every touched method (verified per-method, not sampled).
- [ ] Every JOIN target and tombstone filter closed (AC-4).
- [ ] TASK-3.6 checklist is 100% complete and `task-completion-validator`-reviewed.
- [ ] Existing test suite passes unmodified in advisory mode (no behavior change yet — D4).
- [ ] TASK-2.4 seam verification (Phase 2's responsibility, completable once this phase's signatures exist) is closed before TASK-3.6 signs off.

## Key Files and Integration Points

- `src/research_foundry/services/catalog_service.py`
- `src/research_foundry/services/builder_service.py`
- `src/research_foundry/services/agent_job_service.py`
- **Seam with Phase 2**: router-passed `identity` argument must land on the `identity` parameter added here (TASK-2.4, closed jointly).
- **Handoff to Phase 4**: TASK-3.6's signed checklist is the literal artifact Phase 4's `entry_criteria` gates on.

---

[Back to parent plan](../wksp-304-workspace-isolation-enforcement-v1.md) | [Previous: Phase 1-2](./phase-1-2-config-identity.md) | [Next: Phase 4](./phase-4-enforcing-flip.md)
