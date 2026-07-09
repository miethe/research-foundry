---
schema_version: 1
doc_type: exit_gate_checklist
title: "WKSP-304 Phase 3 Exit-Gate: 100%-Coverage Checklist (TASK-3.6)"
feature_slug: wksp-304-workspace-isolation-enforcement
phase: 3
created: 2026-07-09
status: complete
coverage: "8/8 (100%)"
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1/phase-3-query-layer-scoping.md
progress_ref: .claude/progress/wksp-304-workspace-isolation-enforcement/phase-3-progress.md
---

# Phase 3 Exit-Gate Checklist — TASK-3.6

**Purpose**: Per the parent plan's Phase 4 `entry_criteria` and this plan's decisions block D4/Risk 1,
this checklist's 100% sign-off is the single non-negotiable precondition for any Phase 4 task to be
dispatched. It enumerates every method that actually exists in the three in-scope services (not the
plan's original assumed method list — see "Documented Deviations" below) and confirms, per method:

- **(a)** `identity: AuthIdentity | None = None` parameter is present
- **(b)** predicate is flag-gated (via `_isolation_active` / `resolve_workspace_isolation_enforced`) and parameterized (no string interpolation of values)
- **(c)** `identity=None` produces byte-identical behavior to the pre-WKSP-304 baseline, proven by a specific test
- **(d)** any JOIN/tombstone paths for that method are closed per TASK-3.4's audit

**Result: 8/8 methods (100%) checked off.** No open items block Phase 4 entry on the Phase 3 mandate
(query-layer WHERE-predicate/read scoping). One separate, non-blocking carry-forward item is flagged
at the end of this document per TASK-3.5's evidence note.

---

## Documented Deviations From the Plan's Assumed Method List (Intentional Exclusions)

The Phase 3 plan (`phase-3-query-layer-scoping.md`, AC-2 `target_surfaces`) assumed ~20-25 methods
across the 3 services. Re-derivation during TASK-3.1/3.2/3.3 (see `phase-3-progress.md` evidence
notes) confirmed the following named methods **do not exist as separate methods in the codebase** —
these are not gaps in this phase's coverage, they are corrections to the plan's method-name
assumptions, made once and carried forward here as the authoritative scope:

| Plan-assumed name | Service | Why excluded |
|---|---|---|
| `list_items` | `catalog_service.py` | Does not exist. `search()` is the only listing entry point (paginated, filtered) — there is no separate unfiltered `list_items`. |
| `count_items` | `catalog_service.py` | Does not exist. `search()`'s `total` field and `stats()` (aggregate-only, no per-record `workspace_id` exposure) cover this; no standalone `count_items` function. |
| `get_related_items` | `catalog_service.py` | Does not exist as a separate function. Related-item resolution (outgoing/incoming links, citing drafts) is inlined inside `get_item()` itself — see `get_item`'s row below. |
| `find_drafts` | `builder_service.py` | Does not exist. `list_drafts()` is the only draft-enumeration entry point; there is no separate search/find variant. |
| `list_jobs` | `agent_job_service.py` | Does not exist. `AgentJobService` has no directory-scan/listing method; `load_job()` is the only identity-bearing read method on this service. |

The real, in-scope surface is **8 methods** across the 3 services, confirmed by direct source
inspection (not by re-trusting the plan text): `search`, `get_item`, `get_draft_index`,
`list_draft_index` (`catalog_service.py`); `load_draft`, `list_drafts`, `export_markdown`
(`builder_service.py`); `load_job` (`agent_job_service.py`).

---

## Checklist: catalog_service.py (4 methods)

### 1. `search()`

| Criterion | Status | Evidence |
|---|---|---|
| (a) identity parameter | PASS | `src/research_foundry/services/catalog_service.py:1277` — `identity: AuthIdentity | None = None` |
| (b) flag-gated + parameterized | PASS | Line 1294: `workspace_scoped = identity is not None and _isolation_active(paths)`. Predicate `where.append("workspace_id = ?")` / `params.append(identity.workspace_id)` (line 1298-1300) — bound param, never interpolated into SQL text. Facet query (`_facets`) also receives `workspace_id=identity.workspace_id if workspace_scoped else None` (line 1362) so facet dropdowns cannot leak cross-workspace values (AC-4). |
| (c) identity=None byte-identical | PASS | `tests/unit/test_catalog_service.py::test_search_identity_none_is_byte_identical` (line 1304) |
| (d) JOIN/tombstone closed | PASS | `search()` has no JOIN of its own (facets/FTS are same-table); TASK-3.4's audit (progress evidence note) confirms catalog_service.py's JOIN-bearing surface is `get_item`/`get_draft_index`, both closed below. Additional coverage: `test_search_identity_active_scopes_to_workspace` (line 1317) and `test_search_identity_present_but_inactive_stays_unscoped` (line 1340) prove both the active-scoping and advisory-inert branches. |

### 2. `get_item()`

| Criterion | Status | Evidence |
|---|---|---|
| (a) identity parameter | PASS | `catalog_service.py:1473` — `identity: AuthIdentity | None = None` |
| (b) flag-gated + parameterized | PASS | Line 1491-1492: `workspace_scoped = identity is not None and _isolation_active(paths)`; `workspace_id = identity.workspace_id if workspace_scoped else None`. Primary-row query (line 1497-1502), outgoing-link JOIN (`outgoing_ws_clause` built line 1518, executed line 1524), incoming-link JOIN (executed line 1533, reusing `outgoing_ws_clause`/`outgoing_params`), and citing-drafts JOIN (`citing_ws_clause` built line 1552, executed line 1558) all bind `workspace_id` as a parameterized value (`outgoing_params`/`citing_params` tuples) — never f-string-interpolated into the predicate itself (only the *presence/absence* of the `AND ... = ?` clause fragment is conditionally built, the value is always bound). |
| (c) identity=None byte-identical | PASS | `tests/unit/test_catalog_service.py::test_get_item_identity_none_is_byte_identical` (line 1359) |
| (d) JOIN/tombstone closed | PASS | This is the exact TASK-3.4 audit subject. Docstring (line 1481-1487) states the predicate is applied to the JOINed side (`i.workspace_id`, `d.workspace_id`), not only the primary row — confirmed at lines 1518 (`outgoing_ws_clause`, reused for both outgoing at 1524 and incoming at 1533) and 1552 (`citing_ws_clause`, applied at 1558). Per TASK-3.4's evidence note, catalog_service's `get_item` outgoing/incoming/citing_drafts joins were "already closed in TASK-3.1." Additional coverage: `test_get_item_identity_active_hides_cross_workspace_item` (line 1370), `test_get_item_identity_present_but_inactive_stays_unscoped` (line 1385). |

### 3. `get_draft_index()`

| Criterion | Status | Evidence |
|---|---|---|
| (a) identity parameter | PASS | `catalog_service.py:1771` — `identity: AuthIdentity | None = None` |
| (b) flag-gated + parameterized | PASS | Line 1789: `workspace_scoped = identity is not None and _isolation_active(paths)`. Primary-row query (lines 1791-1799) and the `catalog_links` JOIN (lines 1806-1814) both bind `identity.workspace_id` as a parameter, not interpolated text. |
| (c) identity=None byte-identical | PASS | `tests/unit/test_catalog_service.py::test_get_draft_index_and_list_draft_index_workspace_scoping` (line 1396, assertion at line 1411: `svc.get_draft_index(tmp_foundry, draft_id, identity=None) == baseline_item`) |
| (d) JOIN/tombstone closed | PASS | **This is the one leak TASK-3.4 found and fixed** (progress evidence note: "get_draft_index links leak found+fixed"). Docstring (lines 1775-1786) explains the fix precisely: the pre-WKSP-304 `catalog_links` query never joined `catalog_items`, so the fix conditionally adds a JOIN to `catalog_items i` (`i.workspace_id = ?`) only on the actively-scoped branch (lines 1806-1814) — preserving `identity=None` byte-identity while closing the leak (a draft citing a cross-workspace catalog item would otherwise surface that item's id through `get_draft_index`'s `links` field). Dedicated regression test: `tests/unit/test_catalog_service.py::test_get_draft_index_closes_catalog_links_join_leak` (line 1428). |

### 4. `list_draft_index()`

| Criterion | Status | Evidence |
|---|---|---|
| (a) identity parameter | PASS | `catalog_service.py:1832` — `identity: AuthIdentity | None = None` |
| (b) flag-gated + parameterized | PASS | Line 1842: `workspace_scoped = identity is not None and _isolation_active(paths)`; predicate appended as `where.append("workspace_id = ?")` / `params.append(identity.workspace_id)` (lines 1845-1847) — parameterized. |
| (c) identity=None byte-identical | PASS | `tests/unit/test_catalog_service.py::test_get_draft_index_and_list_draft_index_workspace_scoping` (line 1396, assertion at line 1413: `svc.list_draft_index(tmp_foundry, identity=None) == baseline_list`) |
| (d) JOIN/tombstone closed | PASS | `list_draft_index()` queries only `catalog_report_drafts` directly — no JOIN surface. Per TASK-3.4's audit, the only JOIN leak in this file was `get_draft_index` (above); `list_draft_index` was never JOIN-bearing. |

---

## Checklist: builder_service.py (3 methods)

### 5. `load_draft()`

| Criterion | Status | Evidence |
|---|---|---|
| (a) identity parameter | PASS | `src/research_foundry/services/builder_service.py:303` — `identity: AuthIdentity | None = None` |
| (b) flag-gated (file-backed equivalent; no SQL, so "parameterized" is N/A) | PASS | Line 329: `if identity is not None and _isolation_active(paths):` then `if data.get("workspace_id") != identity.workspace_id: raise NotFoundError(...)`. No SQL predicate exists for this module (file-backed store, confirmed by TASK-3.4's audit: "builder_service.py=file-backed,no-SQL,no-JOIN-surface") — the gate is a flag-gated equality check on the loaded dict, structurally equivalent to a `WHERE workspace_id = ?` predicate for a single-file read; there is no string-interpolation surface to have a parameterization defect in. |
| (c) identity=None byte-identical | PASS | `tests/unit/test_builder_service.py::test_load_draft_identity_none_is_byte_identical` (line 600) |
| (d) JOIN/tombstone closed | PASS | No JOIN surface (file-backed). No tombstone/soft-delete state on drafts. TASK-3.4's audit already closed this file with no findings. Additional coverage: `test_load_draft_identity_active_hides_cross_workspace_draft` (line 608), `test_load_draft_identity_present_but_inactive_stays_unscoped` (line 621). |

### 6. `list_drafts()`

| Criterion | Status | Evidence |
|---|---|---|
| (a) identity parameter | PASS | `builder_service.py:373` — `identity: AuthIdentity | None = None` |
| (b) flag-gated | PASS | Docstring (lines 375-383) states the design explicitly: `identity` is threaded straight into `load_draft()` per-item (`load_draft(paths, d.name, identity=identity)`, line 395, inside the `sorted(root.iterdir())` loop), which already raises `NotFoundError` on a cross-workspace mismatch when isolation is active; this loop already treats `NotFoundError` as "skip." Single predicate lives in one place (`load_draft`), not duplicated — deliberately avoids a second, potentially-inconsistent gate implementation. |
| (c) identity=None byte-identical | PASS | `tests/unit/test_builder_service.py::test_list_drafts_scans_disk` covers the unscoped baseline; the identity-specific byte-identity assertion is in `test_list_drafts_workspace_scoping` (line 632, assertion at line 644: `{d["report_draft_id"] for d in bsvc.list_drafts(tmp_foundry, identity=None)} == baseline`). |
| (d) JOIN/tombstone closed | PASS | No JOIN surface — delegates entirely to `load_draft()`'s already-closed gate. No tombstone state. |

### 7. `export_markdown()`

| Criterion | Status | Evidence |
|---|---|---|
| (a) identity parameter | PASS | `builder_service.py:1098` — `identity: AuthIdentity | None = None` |
| (b) flag-gated | PASS | Docstring (lines 1108-1111): threaded straight into `load_draft(paths, report_draft_id, identity=identity)` (line 1112), which raises `NotFoundError` for a cross-workspace draft when isolation is active — same single-choke-point design as `list_drafts`. |
| (c) identity=None byte-identical | PASS | `tests/unit/test_builder_service.py::test_export_markdown_workspace_scoping` (line 656, assertion at line 663: `bsvc.export_markdown(tmp_foundry, draft_id, identity=None) == baseline`) |
| (d) JOIN/tombstone closed | PASS | No JOIN surface — delegates to `load_draft()`. No tombstone state. |

---

## Checklist: agent_job_service.py (1 method)

### 8. `load_job()`

| Criterion | Status | Evidence |
|---|---|---|
| (a) identity parameter | PASS | `src/research_foundry/services/agent_job_service.py:832` — `def load_job(self, job_id: str, *, identity: AuthIdentity | None = None) -> AgentJob:` |
| (b) flag-gated (file-backed equivalent; no SQL) | PASS | Line 876: `if identity is not None and self._isolation_active():` then `if job.workspace_id != identity.workspace_id: raise KeyError(...)`. Confirmed file-backed (JSON under `agent_job_dir(job_id)`, per docstring lines 840-850) — no SQL query, no string-interpolation surface. The router's existing `_load_job_or_404` (catches `ValueError`/`KeyError`) needs no change to produce an indistinguishable 404 once identity is threaded through in a later phase — docstring lines 848-850. |
| (c) identity=None byte-identical | PASS | `tests/unit/test_agent_job_service.py::test_load_job_identity_none_is_byte_identical` (line 68) |
| (d) JOIN/tombstone closed | PASS | No JOIN surface (single JSON file read). No tombstone state on agent jobs. TASK-3.4's audit already closed this file with no findings ("agent_job_service.py=file-backed,no-SQL,no-JOIN-surface"). Additional coverage: `test_load_job_identity_active_hides_cross_workspace_job` (line 76), `test_load_job_identity_present_but_inactive_stays_unscoped` (line 92), `test_load_job_identity_active_null_workspace_job_is_hidden` (line 105). |

---

## Coverage Summary

| Service | Methods in scope | Methods checked | Coverage |
|---|---|---|---|
| `catalog_service.py` | 4 (`search`, `get_item`, `get_draft_index`, `list_draft_index`) | 4 | 100% |
| `builder_service.py` | 3 (`load_draft`, `list_drafts`, `export_markdown`) | 3 | 100% |
| `agent_job_service.py` | 1 (`load_job`) | 1 | 100% |
| **Total** | **8** | **8** | **100%** |

All four criteria (a/b/c/d) pass for every one of the 8 methods. No open findings block Phase 4 entry
on the Phase 3 mandate (flag-gated, parameterized, byte-identical-when-`identity=None`,
JOIN/tombstone-closed query-layer scoping).

---

## Non-Blocking Carry-Forward Item for Phase 4 Entry Checklist

Per TASK-3.5's evidence note (backend-architect review): the shared gate-helper contract
(`require_workspace_scope` / the `_isolation_active` shape) is confirmed **stable** for Phase 4 to
consume without a rewrite. However, that review also surfaced a coverage gap outside this phase's
scope: **`require_workspace_scope` is currently wired at only 2 of 6 effective deny paths.** This is
explicitly **not** a Phase 3 blocker — Phase 3's mandate was WHERE-predicate/read-scoping coverage
across the 3 services (complete, 8/8, this document), not audit-log call-site uniformity for the
advisory-mode helper. It is flagged here so Phase 4's `entry_criteria`/task list picks it up as a
named carry-forward item rather than it being silently dropped between phases.

---

## Test Suite Confirmation (re-run at TASK-3.6 time)

Command: `/Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/ -q`

Result: **5 failed, 1673 passed, 1 skipped, 1 xfailed, 785 warnings in 62.70s**

All 5 failures are in `tests/test_serve_api.py` (`test_get_run_detail_known_run_returns_200`,
`test_get_claims_non_empty`, `test_get_claims_empty_ledger_returns_empty_list`,
`test_get_source_found`, `test_sensitivity_gate_parity_work_sensitive_claim`) — the same file and the
same failure count (5) previously confirmed in `phase-1-2-completion.md` as a **pre-existing baseline
cluster verified via `git stash`/`git stash pop` comparison against pre-change `main` HEAD**, i.e.
unrelated to any WKSP-304 change. No new regressions introduced by Phase 3's work.
