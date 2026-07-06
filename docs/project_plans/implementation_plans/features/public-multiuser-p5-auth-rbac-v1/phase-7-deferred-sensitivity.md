---
title: "Phase 7: Deferred Sensitivity Closes (FU-4)"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-07-06
updated: 2026-07-06
feature_slug: public-multiuser-p5-auth-rbac
feature_version: v1
phase: 7
phase_title: "Deferred Sensitivity Closes (FU-4)"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
entry_criteria:
  - "P5.1 identity contract exists (for the auth-adjacent parts of existence-gate parity, though this phase is largely auth-independent)"
exit_criteria:
  - "Over-threshold run returns 404 across all 4 run-detail-family endpoints (existence-gate parity)"
  - "unlinked sensitive quote is caught by the global source index (not silently passed)"
  - "reverse links resolve correctly"
  - "sensitivity regression suite green"
  - "task-completion-validator sign-off"
related_documents:
  - docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
  - docs/project_plans/implementation_plans/public-multiuser-p2p3-opus-handoff.md
  - docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md
spike_ref: docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
adr_refs: []
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: null
ui_touched: false
target_surfaces:
  - src/research_foundry/api/routers/runs.py
  - src/research_foundry/services/verification.py
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/builder_service.py
seam_tasks: []
owner: python-backend-engineer
contributors: [data-layer-expert, "ICA Sonnet 4.6", task-completion-validator]
priority: high
risk_level: medium
category: "product-planning"
tags: [phase-plan, implementation, sensitivity, security, fu-4, public-multiuser]
milestone: "public-multiuser-p5"
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/api/routers/runs.py
  - src/research_foundry/services/verification.py
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/builder_service.py
  - tests/unit/test_sensitivity_redaction.py
  - tests/unit/test_export_service.py
---

# Phase 7: Deferred Sensitivity Closes (FU-4)

**Parent Plan**: [Public Multi-User P5 — Auth/RBAC/Isolation/Audit Hardening](../public-multiuser-p5-auth-rbac-v1.md)
**Duration**: 3-4 days
**Effort**: 5 story points
**Dependencies**: P5.1 (auth-provider port + durable identity contract) for the identity-adjacent framing of the existence gate; otherwise this phase's three closes do not require RBAC, workspace isolation, or Clerk to exist.
**Team Members**: `python-backend-engineer`, `data-layer-expert`, ICA Sonnet 4.6 (offload wave), `task-completion-validator` (mandatory gate)

---

## Phase Overview

This phase closes the three deferred sensitivity gaps carried forward from P2/P3 as SPIKE FU-4
(`docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md`, "Open follow-ups"). **This
is in-scope P5 work, not a deferred item itself** — FU-4 was deferred *relative to* P2/P3, but all
three items are fully scoped, estimated, and resolved here in P5.7. Do not treat this phase as
optional or best-effort.

**Parallelization note (from the decisions block)**: P5.7 is explicitly called out as "largely
independent of auth" in the P5 decisions block (`.claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md`
§1 Boundary Rationale, §5 Dependency Map). None of the three closes require RBAC enforcement
(P5.2), workspace-isolation migration (P5.3), or the Clerk adapter (P5.4) to exist first. Once
P5.1 lands (the auth-provider port + durable identity contract), **P5.7 runs in parallel with
P5.4 (Clerk adapter) and P5.5 (audit log)** — three distinct, non-overlapping file sets
(`api/auth/adapters/clerk.py` + frontend auth-context vs. `services/audit_service.py` vs. this
phase's `routers/runs.py` / `services/verification.py` / `services/catalog_service.py`). Schedule
accordingly: do not serialize this phase behind P5.2/P5.3 on the critical path.

### Goals

- **Close FU-4 #1**: Give all four run-detail-family endpoints the same no-existence-leak
  contract. Today only `get_run_anchors` has it; the three siblings do not (confirmed code-truth
  gap, PRD §2 "Confirmed code-truth gaps", and [[runs-api-no-sensitivity-existence-gate]]).
- **Close FU-4 #2**: Stop a report-body quote sourced from a run outside the draft's declared
  origin set from silently passing the D13 sensitivity check (the P3 blank-origin-draft residual).
- **Close FU-4 #3**: Make catalog navigation for a run or claim surface which report drafts cite
  it — the write-side link already exists; the read side silently drops it.

### Architecture Focus

- **Layer**: API (routers) + Service (verification, catalog). No Database schema migration is
  required for this phase — all three closes are additive: new query logic, a new in-process
  index, and a new read-time resolution path over existing `catalog_links` rows.
- **Patterns**: fail-closed sensitivity gating (mirrors `export_service.py`'s
  `DEFAULT_THRESHOLD`/`SENSITIVITY_ORDER` precedent); no-existence-leak convention (landmine #4,
  already proven in `get_run_anchors`); D10 constraint — `catalog.db` is disposable
  (drop+rebuild on `user_version` mismatch), so FU-4 #3 must resolve reverse links **at read
  time** over existing rows, not via a new persisted/duplicated edge that a rebuild could silently
  drop or double-write.
- **Standards**: extend the existing P2/P3 sensitivity regression suite
  (`tests/unit/test_sensitivity_redaction.py`, `tests/unit/test_export_service.py`) — this phase
  **adds** the existence-gate and global-source-index test cases to that suite; it does not
  replace or fork it.

### Model & Offload Routing (mandatory labeling — one of only 3 phases with an ICA wave)

| What | Owner | Rationale |
|------|-------|-----------|
| Contract design for the global source index (Task 2): what "outside the caller's visible/reachable set" means precisely, and the fail-closed semantics when the index can't be built | **Claude (sonnet, adaptive)** — `python-backend-engineer` / `data-layer-expert` judgment call | Requires reasoning about workspace-visibility semantics ahead of P5.3's workspace isolation; the wrong call here reopens a silent-pass gap under a different name. |
| Reverse-link schema decision for Task 3: read-time UNION resolution vs. a new persisted edge, and where the result surfaces in the API response shape | **Claude (sonnet, adaptive)** — `data-layer-expert` judgment call | D10 (catalog.db disposability) and "don't silently break existing `get_item()` consumers" are architectural constraints only a design pass can resolve safely. |
| Mechanical implementation of Task 1 (existence-gate parity) once the shared-helper pattern is specified — the pattern is already proven in `get_run_anchors` | **ICA Sonnet 4.6**, behind review | Bounded, contract-clear: apply an existing, working pattern to 3 more call sites. |
| Mechanical implementation of Task 2 once the index-building contract is written down | **ICA Sonnet 4.6**, behind review | Index-building and check-wiring are bounded once the semantics (above) are fixed. |
| Mechanical implementation of Task 3 once the reverse-link schema decision is written down | **ICA Sonnet 4.6**, behind review | Query-writing against a fixed schema decision is bounded. |
| **Validator gate** | `task-completion-validator` **MUST** review every ICA-produced wave before it is accepted into this phase | Non-negotiable per the decisions block's model-routing note — ICA output never merges without this gate. |

---

## Task Breakdown

### Epic: FU-4 Deferred Sensitivity Closure

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|------------------------|-------|--------|--------------|
| P5.7.1 | Existence-gate parity (FU-4 #1) | Add the no-existence-leak gate to `get_run_detail`, `get_run_claims`, `get_source_card` (`runs.py:68-133`), matching `get_run_anchors` (`runs.py:136-188`) | AC-P5.7.1 | 2 pts | python-backend-engineer / ICA Sonnet 4.6 | sonnet | adaptive | None |
| P5.7.2 | Global source index (FU-4 #2) | Build a workspace-wide source index so an unlinked-run quote in a report body is caught by `verify_draft`/D13 checks | AC-P5.7.2 | 2 pts | python-backend-engineer, data-layer-expert / ICA Sonnet 4.6 | sonnet | adaptive | None |
| P5.7.3 | Reverse catalog links (FU-4 #3) | Surface draft→run/claim reverse links so catalog navigation shows citing drafts | AC-P5.7.3 | 1 pt | data-layer-expert / ICA Sonnet 4.6 | sonnet | adaptive | None |

**Model Selection Guidance**: `.claude/config/multi-model.toml` for valid model values. Every task
in this phase splits into a Claude-sonnet **design** sub-step and an ICA-Sonnet-4.6 **mechanical**
sub-step (see "Model & Offload Routing" above) — the table above shows the task-level assignment;
the design/offload split is called out per-task below.

**Effort Policy**: `adaptive` throughout — none of these three closes require `extended` reasoning
once the design decision (documented per task below) is fixed.

---

## Detailed Task Specifications

### Task P5.7.1: Existence-gate parity across the run-detail endpoint family

**Estimate**: 2 points
**Assigned Subagent(s)**: python-backend-engineer (design + review); ICA Sonnet 4.6 (mechanical apply, behind `task-completion-validator` gate)
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: None
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:

`GET /api/runs/{run_id}`, `GET /api/runs/{run_id}/claims`, and
`GET /api/runs/{run_id}/sources/{source_card_id}` (`api/routers/runs.py:68-133`) rely **only** on
`export_run`'s field-level redaction — they have **no run-level existence gate**. This is a
confirmed code-truth gap (PRD §2, and cited in the docstring of `get_run_anchors` itself,
`runs.py:152-161`): "Sibling run-detail endpoints (`get_run_detail` / `get_run_claims` /
`get_source_card`) do NOT apply this existence gate; they rely solely on `export_run`'s
field-level redaction." An over-threshold run is fully retrievable through these three endpoints
today, with only its content redacted — not its existence.

`get_run_anchors` (`runs.py:136-188`) already implements the correct pattern:

```python
threshold = resolve_threshold(paths, sensitivity_threshold)   # raises ExportError -> 400
threshold_rank = SENSITIVITY_ORDER[threshold]
data = export_run(paths, run_id, sensitivity_threshold=threshold)  # raises ExportError -> 404
run_sensitivity = data.get("sensitivity") or "public"
run_rank = SENSITIVITY_ORDER.get(str(run_sensitivity), len(SENSITIVITY_ORDER))
if run_rank > threshold_rank:
    raise HTTPException(status_code=404, detail="not found")
```

**Implementation approach**: extract this comparison into a small, shared helper (e.g.
`_enforce_existence_gate(paths, run_id, sensitivity_threshold) -> dict` in `runs.py`, or a
function in `export_service.py` if a future caller outside this router needs it) so the gate logic
is written once, not copy-pasted four times. Apply the helper to all three sibling endpoints. Add
the same optional `sensitivity_threshold` query parameter that `get_run_anchors` already exposes,
for parity (today only `get_run_anchors` accepts it).

**Acceptance Criteria**: see AC-P5.7.1 below (structured format).

**Implementation Notes**:
- Reuse the exact `SENSITIVITY_ORDER`/`resolve_threshold` comparison already proven in
  `get_run_anchors` — do not reimplement the rank comparison; an off-by-one here would either
  regress currently-working under-threshold requests or reopen the existence leak.
- `get_run_claims` and `get_source_card` both already call `export_run(...)` once per request
  (`runs.py:97`, `runs.py:124`) — the gate must reuse that same `export_run` call's returned
  `sensitivity` field rather than issuing a second lookup.
- Preserve the existing 404 message convention (`"not found"` / `"run not found"` — check current
  call sites for consistency and normalize if the two differ) so the gated and ungated 404 paths
  are indistinguishable to a caller.

**Files Involved**:
- `src/research_foundry/api/routers/runs.py:68-133` — add the existence gate to the 3 endpoints; extract shared helper.

---

### Task P5.7.2: Global source index closing the blank-origin-draft residual

**Estimate**: 2 points
**Assigned Subagent(s)**: python-backend-engineer, data-layer-expert (design — **stays on Claude**); ICA Sonnet 4.6 (mechanical implementation once the index contract is fixed, behind `task-completion-validator` gate)
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: None
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:

`check_report_body_sensitivity` (`services/verification.py:873-966`) is the D13 check that scans a
report draft's body text for raw quotes lifted from sensitive source cards. It builds its
candidate `run_ids` (`verification.py:907-917`) from exactly three places: the draft's own
`source_run_id`, its `source_links[].run_id`, and its `claim_links[].source_run_id` — i.e., **only
runs the draft itself already declares**. It then globs source cards from each of those runs'
`sources/` dirs (`verification.py:920-947`) and flags a leak if a raw quote from a sensitive card
appears in the body.

**Confirmed gap**: if `run_ids` is empty — a "blank-origin-draft" with no origin run and no
source/claim links — the scan loop never executes and the check **passes unconditionally**,
regardless of what sensitive text is pasted into the body. The same blind spot applies to a quote
manually pasted from a run genuinely different from any of the draft's three declared sources: it
is invisible to this scan by construction. There is currently no fallback to "every run in the
workspace," and no existing function builds a workspace-wide `source_card_id -> (run_id,
sensitivity)` index — `_index_source_cards` (`verification.py:245-270`) is per-run only, used by
a different function (`verify_report`).

**Design decision required (this is the judgment call that stays on Claude, not ICA)**: what does
"outside the caller's visible/reachable set" mean precisely for this check?

- **Option A — full-workspace index (recommended for this phase)**: build a workspace-wide map of
  `source_card_id -> (run_id, sensitivity)` by scanning every run's `sources/` dir once (mirroring
  the shape of `_index_source_cards` but workspace-scoped instead of per-run), then check *every*
  quote in the body against *any* run's source cards — not just the draft's three declared
  sources. This fully closes the gap and requires no ordering dependency on later phases.
- **Option B — caller/workspace-scoped index**: once P5.3's workspace-isolation migration lands,
  scope the index to runs within the caller's `workspace_id`, rather than literally every run on
  disk. More "correct" post-P5.3, but introduces a hard dependency this phase should not take on,
  given P5.7 is explicitly meant to run in parallel with (not after) P5.2/P5.3.

**Recommendation**: ship **Option A now**. A workspace-scoped index (Option B) is a strict subset
of the full-workspace index's checks — it can never be *less* safe to over-check now and narrow
later. Record this as an explicit forward-looking note (not a blocker): a follow-up pass after
P5.3 lands MAY narrow the index to per-workspace visibility as a precision/perf optimization, not
a correctness fix. Do not gate this task on P5.3.

**Fail-closed requirement**: if the global index cannot be built for some subset of runs (I/O
error, corrupt `sources/` dir), those runs must be treated as sensitivity-unknown/blocking for the
purposes of this check — never silently skipped. Silently skipping a run whose index failed to
build would reintroduce exactly the kind of silent-pass gap this task exists to close.

**Acceptance Criteria**: see AC-P5.7.2 below (structured format).

**Implementation Notes**:
- New function, e.g. `build_global_source_index(paths: FoundryPaths) -> dict[str, tuple[str, str]]`
  (source_card_id -> (run_id, sensitivity)) in `verification.py`, reusing the per-run scan shape
  already proven in `_index_source_cards` (`verification.py:245-270`) but iterating every run.
- Wire the new check into `verify_draft`'s existing checks list (`verification.py:1004-1016`) as
  either an extension of `check_report_body_sensitivity` or a new sibling
  `check_report_body_sensitivity_global` — do not silently replace the existing per-run check; the
  existing behavior for properly-linked drafts must be unchanged (no regression).
- `verify_draft` writes `<draft_dir>/verification.yaml` (`verification.py:1038-1039`) — the new
  check's `CheckResult` (id/severity/status/detail/locations, `verification.py:125-133`) must
  follow the existing shape so downstream consumers of that YAML are unaffected.

**Files Involved**:
- `src/research_foundry/services/verification.py:873-1048` — new index-building function; extend or add a check function; wire into `verify_draft`'s checks list.

---

### Task P5.7.3: Draft→run/claim reverse catalog links

**Estimate**: 1 point
**Assigned Subagent(s)**: data-layer-expert (design — **stays on Claude**); ICA Sonnet 4.6 (mechanical query implementation once the schema decision is fixed, behind `task-completion-validator` gate)
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: None
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:

The **write side already exists**: `builder_service._sync_catalog_index`
(`builder_service.py:1058-1091`) reads a draft's `source_run_id`, `claim_links[].catalog_item_id`,
and `source_links[].catalog_item_id`, and calls `catalog_service.index_draft`
(`catalog_service.py:1519-1587`), which persists `catalog_links` rows with `from_item_id =
report_draft_id` (using a `"draft:<id>"` sentinel `run_id` scope, `catalog_service.py:1483-1495`)
and relation `"cites"` / `"derived_from"`. This runs on every draft mutation via `_save_draft`
(`builder_service.py:282-291`) and in bulk via `reindex_all_drafts`
(`builder_service.py:1094-1117`, `catalog_service.py:1145-1149`).

**The read side silently drops these edges.** `get_item()` (`catalog_service.py:1375-1429`)
resolves `outgoing` (1405-1413) and `incoming` (1414-1422) edges via `INNER JOIN catalog_items i
ON i.catalog_item_id = l.{to,from}_item_id`. A `report_draft_id` is **never** a row in
`catalog_items` (`ITEM_TYPES`, `catalog_service.py:95-102` — `report_draft` is not in this enum;
drafts live in the separate `catalog_report_drafts` table, `catalog_service.py:175-194`). So every
`catalog_links` row whose `from_item_id` is a draft — exactly the edges `index_draft` already
writes — is invisible to `get_item()`'s `incoming` query today. The edge exists in the raw table;
navigating to the cited run or claim's catalog record shows nothing.

**Design decision required (stays on Claude)**: how should the reverse link surface?

- **Recommended**: add a **new, separate field** to `get_item()`'s response — e.g.
  `citing_drafts: list[dict]` — populated by a read-time query that joins `catalog_links` against
  `catalog_report_drafts` (not `catalog_items`) for rows where `to_item_id` matches and the
  `from_item_id`/`run_id` sentinel indicates a draft origin. **Do not** mix draft entries into the
  existing `incoming`/`outgoing` lists inline: those lists have an established, narrower shape
  (`ITEM_TYPES`-typed catalog items) that other consumers (including the frontend catalog graph,
  out of scope for this backend-only phase) already assume. A new, additive field is the resilient
  choice — existing consumers of `incoming`/`outgoing` see no shape change; a future frontend task
  (P5.8 or later) can opt into rendering `citing_drafts` when ready.
- Resolve this **at read time** over the existing `catalog_links` rows — do not add a persisted,
  duplicated reverse-edge row. `catalog.db` is disposable (D10: drop+rebuild on `user_version`
  mismatch) — a persisted duplicate is a rebuild/consistency footgun the read-time UNION approach
  avoids entirely, since `reindex_all_drafts` already repopulates the forward rows this query reads.

**Acceptance Criteria**: see AC-P5.7.3 below (structured format).

**Implementation Notes**:
- Read-time query only; no schema migration required for this task.
- If a schema change is chosen instead of the recommended read-time UNION, it must be idempotent
  under the existing rebuild-on-`user_version`-mismatch mechanism (never assume additive state
  survives a `catalog.db` rebuild without being explicitly re-derived by `reindex_all_drafts`).
- Verify `reindex_all_drafts` (bulk rebuild path) produces identical `citing_drafts` results to the
  incremental `_save_draft` path — both write through the same `index_draft` call, but confirm the
  read-time query doesn't accidentally depend on ordering or a field only the incremental path sets.

**Files Involved**:
- `src/research_foundry/services/catalog_service.py:1375-1429` — extend `get_item()` with the new `citing_drafts` read.
- `src/research_foundry/services/builder_service.py:1058-1091` — confirm/no-op; write side already correct (context only, no edit expected unless a discriminator field is missing on the written rows).

---

## Structured Acceptance Criteria

#### AC-P5.7.1: All 4 run-detail-family endpoints share one existence-gate contract
- target_surfaces:
    - src/research_foundry/api/routers/runs.py::get_run_detail (GET /api/runs/{run_id})
    - src/research_foundry/api/routers/runs.py::get_run_claims (GET /api/runs/{run_id}/claims)
    - src/research_foundry/api/routers/runs.py::get_source_card (GET /api/runs/{run_id}/sources/{source_card_id})
    - src/research_foundry/api/routers/runs.py::get_run_anchors (GET /reports/{run_id}/anchors) — reference pattern, already gated
- propagation_contract: >
    Each of the 3 previously-ungated endpoints resolves `sensitivity_threshold` via
    `resolve_threshold(paths, sensitivity_threshold)` and compares the run's resolved sensitivity
    rank against the threshold rank using the identical `SENSITIVITY_ORDER` comparison already
    proven in `get_run_anchors`, raising HTTP 404 when the run exceeds threshold — reusing a single
    shared helper rather than 3 independent inline copies.
- resilience: >
    An invalid `sensitivity_threshold` query value continues to raise the existing 400 (via
    `resolve_threshold`'s `ExportError`) unchanged; the new existence-gate 404 is indistinguishable
    from the existing "run not found" 404 raised for a genuinely nonexistent `run_id`.
- visual_evidence_required: false
- verified_by:
    - existence-gate-parity-regression-test

#### AC-P5.7.2: Unlinked / blank-origin sensitive quotes are caught, never silently passed
- target_surfaces:
    - src/research_foundry/services/verification.py::check_report_body_sensitivity (existing per-run-linked scan, lines 873-966)
    - src/research_foundry/services/verification.py::verify_draft (D13 check pipeline, lines 969-1048)
- propagation_contract: >
    A new workspace-wide `source_card_id -> (run_id, sensitivity)` index is built once and consulted
    by an extended or sibling check appended to `verify_draft`'s checks list, so a quote sourced from
    any run in the workspace — not only the draft's declared `source_run_id`/`source_links`/
    `claim_links` — is evaluated against that source's actual sensitivity.
- resilience: >
    If the global index cannot be built for a given run (I/O error, corrupt `sources/` dir), that
    run is treated as sensitivity-unknown/blocking for this check rather than silently omitted —
    fail-closed, matching the project's established sensitivity-gating precedent
    (`export_service.py` `DEFAULT_THRESHOLD`). The existing per-run-linked check's passing behavior
    for properly-linked drafts is unchanged (no regression).
- visual_evidence_required: false
- verified_by:
    - blank-origin-draft-sensitivity-regression-test
    - global-source-index-build-unit-test

#### AC-P5.7.3: Catalog navigation surfaces which drafts cite a run or claim
- target_surfaces:
    - src/research_foundry/services/catalog_service.py::get_item (incoming/outgoing edge resolution, lines 1375-1429)
    - src/research_foundry/services/builder_service.py::_sync_catalog_index (draft-citation write side, lines 1058-1091 — context/verification only)
- propagation_contract: >
    `get_item()` gains a new, additive `citing_drafts` field resolved at read time by joining
    existing `catalog_links` rows (already written by `index_draft` on every draft save) against
    `catalog_report_drafts` for edges whose origin is a draft rather than a `catalog_items` row.
    No new persisted edge is written; `reindex_all_drafts`'s existing rebuild path already repopulates
    the rows this query reads.
- resilience: >
    A run or claim with zero citing drafts returns an empty `citing_drafts` list — no regression to
    existing `incoming`/`outgoing` shapes or values for any existing consumer, since the new data
    lands in a new field rather than being mixed into those established lists.
- visual_evidence_required: false
- verified_by:
    - reverse-catalog-link-resolution-test
    - catalog-rebuild-citing-drafts-parity-test

---

## Quality Gates

This phase is complete when:

- [ ] **Functional**: all three FU-4 closes implemented per AC-P5.7.1/2/3.
- [ ] **Testing**: existence-gate parametrized test covers all 4 run-detail-family endpoints;
      blank-origin-draft + cross-run-quote fixtures added to the sensitivity regression suite;
      reverse-link resolution test covers both incremental (`_save_draft`) and bulk
      (`reindex_all_drafts`) write paths.
- [ ] **Performance**: global source index build is not re-scanned per-quote inside the loop (build
      once per `verify_draft` call at minimum); no unbounded per-request full-workspace scan
      introduced without a documented follow-up if run count grows large (see Risk Mitigation).
- [ ] **Security**: fail-closed behavior confirmed for all 3 closes — an existence-gate helper
      failure, an unbuildable index entry, or an unresolvable reverse-link query must never default
      to "permit"/"silently omit."
- [ ] **Documentation**: PRD FR-13/FR-14/FR-15 and "FU-4 closure acceptance" checklist items marked
      resolved; no separate doc deliverable required for this phase (docs finalize in P5.9).
- [ ] **Code Quality**: `flake8`/`mypy` clean on touched files; no duplicated existence-gate
      comparison logic (must reuse the shared helper across the 3 endpoints).
- [ ] **Architecture**: no schema migration introduced (D10-compliant: catalog reverse-links resolved
      read-time, not persisted-duplicate).
- [ ] **Offload validation**: `task-completion-validator` has reviewed and signed off the ICA
      Sonnet 4.6-produced implementation wave for each of the 3 tasks before merge.
- [ ] **Sensitivity regression suite green**: the existing P2/P3 fail-closed regression suite
      (`tests/unit/test_sensitivity_redaction.py`, `tests/unit/test_export_service.py`) passes with
      this phase's new existence-gate and global-source-index test cases **added to it**, not
      replacing it.
- [ ] **Seam verification**: N/A — `integration_owner` is null; no cross-owner-specialty file
      intersection in this phase (all 3 tasks are backend-only, non-overlapping file sets).
- [ ] **Runtime smoke**: N/A — `ui_touched: false`; no `*.tsx` files in scope for this phase.

---

## Integration Points

### External Systems

- None — this phase is entirely internal to the Research Foundry backend service layer.

### Internal Systems

- **`export_service.py`**: the `SENSITIVITY_ORDER`/`resolve_threshold`/`DEFAULT_THRESHOLD`
  fail-closed precedent this phase's existence gate and global source index both extend.
- **`builder_service.py`**: the write side of the draft citation graph (`_sync_catalog_index`,
  `_save_draft`, `reindex_all_drafts`) that Task P5.7.3 reads from but does not modify.
- **P5.1 (Auth-provider port)**: not a hard dependency for this phase's mechanics, but the PRD frames
  existence-gate closure as occurring "under the enforced-identity path" (SPIKE ADR-001) — confirm
  at execution time whether `request.state.identity` is available yet for any future RBAC-aware
  extension; this phase's gate itself does not require it.
- **P5.3 (Workspace isolation)**: no hard dependency, but Task P5.7.2's design explicitly documents
  a forward-looking narrowing opportunity once workspace scoping lands (see Task P5.7.2 Option B).
- **P5.8 (Frontend auth-context + admin UI)**: no FE task in this phase; Task P5.7.3's `citing_drafts`
  field is additive and ready for a future frontend consumer, but rendering it is out of scope here.

---

## Key Files Modified

| File Path | Lines | Purpose | Subagent |
|-----------|-------|---------|----------|
| `src/research_foundry/api/routers/runs.py` | 68-133 (+ new helper) | Existence-gate parity across 3 sibling endpoints | python-backend-engineer / ICA Sonnet 4.6 |
| `src/research_foundry/services/verification.py` | 873-1048 (+ new index function) | Global source index + wired-in D13 check | python-backend-engineer, data-layer-expert / ICA Sonnet 4.6 |
| `src/research_foundry/services/catalog_service.py` | 1375-1429 | `get_item()` gains `citing_drafts` read-time resolution | data-layer-expert / ICA Sonnet 4.6 |
| `src/research_foundry/services/builder_service.py` | 1058-1091 | Verification only — confirm write-side edges are sufficient for the new read | data-layer-expert |
| `tests/unit/test_sensitivity_redaction.py` | new cases | Blank-origin-draft + cross-run-quote fixtures | python-backend-engineer |
| `tests/unit/test_export_service.py` | new cases | Existence-gate parametrized across 4 endpoints | python-backend-engineer |

---

## Testing Strategy

### Unit Tests

- Existence-gate comparison helper: parametrized across all 4 run-detail-family endpoints, over-
  and under-threshold fixture runs, and the invalid-threshold-value 400 path.
- `build_global_source_index`: correct `source_card_id -> (run_id, sensitivity)` mapping across
  multiple runs; fail-closed behavior when one run's `sources/` dir is unreadable.
- `get_item()` `citing_drafts` resolution: draft citing a run/claim via each of `source_run_id`,
  `claim_links`, and `source_links` all surface correctly; zero-citation case returns `[]`.

### Integration Tests

- Full `verify_draft` pipeline against a blank-origin-draft fixture (no `source_run_id`, no
  `source_links`, no `claim_links`) with a raw sensitive quote pasted into the body — must fail.
- Full `verify_draft` pipeline against a draft whose body quotes a source card from a run
  genuinely different from any of its declared links — must fail.
- Catalog rebuild (`reindex_all_drafts`) followed by `get_item()` on the cited run/claim — confirm
  `citing_drafts` parity between the incremental (`_save_draft`) and bulk-rebuild write paths.

### E2E Tests

- Not required for this phase (backend-only, no `*.tsx` in scope). Existence-gate and sensitivity
  behavior are already covered by the project's static+live sensitivity regression suite at the
  API level; no new Playwright spec is needed here.

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Sensitivity fail-open regression during this refactor (decisions-block Risk 3 — this phase sits directly in that risk's blast radius) | High | Reuse proven comparison logic verbatim (no reimplementation); add new tests to the existing P2/P3 regression suite rather than a parallel one; explicit fail-closed requirement documented per task. |
| Full-workspace source index becomes a performance bottleneck as run count grows (Task P5.7.2 scans every run's `sources/` dir) | Medium | Build the index once per `verify_draft` call (not per-quote); document as a named follow-up if profiling later shows it's hot — RF workspaces are typically local/small at v1 scale, so this is not a blocking concern now. |
| Mixing heterogeneous item shapes into `get_item()`'s existing `incoming`/`outgoing` lists breaks an undiscovered frontend consumer | Medium | Rejected in favor of a new, additive `citing_drafts` field (see Task P5.7.3 design decision) — existing consumers see no shape change. |
| Existence-gate helper introduces an off-by-one vs. the proven `get_run_anchors` comparison | High | Extract the exact comparison into one shared helper reused by all 4 endpoints; do not hand-reimplement the `SENSITIVITY_ORDER` rank check 3 times. |
| A persisted (rather than read-time) reverse-link implementation is chosen and silently lost on the next `catalog.db` rebuild (D10) | Medium | Design decision explicitly recommends read-time resolution; if a schema change is chosen instead, it must be verified idempotent under `reindex_all_drafts`. |

---

## Success Metrics

- **Completion**: all 3 tasks (P5.7.1/2/3) checked off; all 3 structured ACs verified.
- **Quality**: sensitivity regression suite green with the new existence-gate and global-source-
  index cases added; `task-completion-validator` sign-off recorded for the ICA-produced wave.
- **Security**: 0 of 4 run-detail-family endpoints missing the existence gate (down from 3 of 4);
  0 silent passes on a blank-origin-draft or cross-run-quote sensitivity test.
- **Coverage**: reverse catalog links resolve correctly for both the incremental and bulk-rebuild
  write paths.

---

## Notes

### Implementation Approach

Each of the three closes follows the same two-step pattern: (1) a Claude-sonnet design pass that
fixes the precise contract/schema decision (documented per task above, not left to the
implementer's discretion at execution time), then (2) an ICA Sonnet 4.6 mechanical-implementation
pass applying that fixed contract, gated by mandatory `task-completion-validator` review before
acceptance. Do not skip step (1) and hand a task straight to ICA — the offload note above exists
specifically because these three closes have one non-mechanical judgment call each (existence-gate
helper extraction pattern is the exception — it's already fully proven in `get_run_anchors`, so
Task P5.7.1's design step is comparatively thin).

### Gotchas

- `get_run_claims` and `get_source_card` already call `export_run(...)` once — do not add a second
  redundant call when wiring the existence gate; reuse the sensitivity field from the existing call.
- `report_draft` is not in `ITEM_TYPES` (`catalog_service.py:95-102`) — any code assuming
  `catalog_items` contains every citable entity will silently mis-resolve draft-origin edges. This
  is exactly the bug Task P5.7.3 closes; don't reintroduce it elsewhere in the same change.
- `catalog.db` is disposable (D10) — never persist a new piece of durable-feeling state into it
  without confirming it survives (or is correctly re-derived on) a `user_version`-mismatch rebuild.

### Learnings

*Populate during execution.*

### Findings Captured This Phase

- [ ] No new findings this phase (default)

---

**Phase Version**: 1.0
**Last Updated**: 2026-07-06

[Return to Parent Plan](../public-multiuser-p5-auth-rbac-v1.md)
