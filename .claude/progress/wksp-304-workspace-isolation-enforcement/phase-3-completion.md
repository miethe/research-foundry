## Phase 3 Completion Note

**Status**: PASS
**Validator verdict**: PASS — query-layer scoping genuinely implemented, byte-identical under `identity=None`/advisory mode (verified by direct test read and a fresh full-suite pytest run), fully parameterized, one real JOIN leak found and closed with a regression test.
**Isolation**: shared (worked directly on `main`, no worktree, per orchestration instructions)
**Branch**: main
**Worktree path**: N/A

### Files Changed
- `src/research_foundry/services/catalog_service.py` — added `identity: AuthIdentity | None = None` + flag-gated, parameterized `workspace_id` predicate to `search`, `get_item`, `get_draft_index`, `list_draft_index`; closed a JOIN leak in `get_draft_index`'s outgoing `catalog_links` query (no prior join to `catalog_items` at all — added a branched joined-side predicate that only applies when actively scoped, to preserve D4 byte-identical baseline)
- `src/research_foundry/services/builder_service.py` — same pattern for `load_draft`, `list_drafts`, `export_markdown` (file-canonical YAML store; fail-closed post-load check on workspace mismatch)
- `src/research_foundry/services/agent_job_service.py` — same pattern for `load_job` (file-canonical JSON store)
- `src/research_foundry/api/routers/catalog.py`, `agent_jobs.py`, `reports.py` — closed the TASK-2.4 forward-seam: replaced `# TODO(WKSP-304 P3): pass identity=identity once ... accepts it` markers with real `identity=identity` kwargs at every call site whose target method now accepts it; TODOs for methods not scoped in P3 (mutation/create/delete paths) relabeled `WKSP-304 P4` with an explicit "not a P3 scoping target" note so they aren't silently lost
- `tests/unit/test_catalog_service.py`, `tests/unit/test_builder_service.py` — extended with new tests
- `tests/unit/test_agent_job_service.py` — new file (no prior unit test existed for this service)
- `.claude/worknotes/wksp-304-workspace-isolation-enforcement/phase-3-exit-checklist.md` — new TASK-3.6 exit-gate artifact (100%-coverage checklist)
- `.claude/progress/wksp-304-workspace-isolation-enforcement/phase-1-2-progress.md` — TASK-2.4 marked completed (forward-seam closed)
- `.claude/progress/wksp-304-workspace-isolation-enforcement/phase-3-progress.md` — all Phase 3 tasks marked completed

### Important deviation from plan (documented, not a gap)
The plan's target_surfaces list assumed ~20-25 methods across the 3 services (including `list_items`,
`count_items`, `get_related_items` on catalog_service.py; `find_drafts` on builder_service.py;
`list_jobs` on agent_job_service.py). TASK-3.0's exploration and TASK-3.1-3.3's implementation confirmed
these methods **do not exist** in the current codebase — they were never implemented, or their
functionality is folded into other methods already scoped (e.g., `search()` combines list+count for
catalog; `get_item()` contains the "related items" outgoing/incoming link logic). The real in-scope
surface is 8 methods, all of which are covered 100% by TASK-3.6's checklist. This is recorded as an
intentional, reasoned exclusion in the checklist artifact, not a silent gap.

### Batch Summary
| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | TASK-3.0 | completed | data-layer-expert |
| 2 | TASK-3.1, TASK-3.2, TASK-3.3 | completed | data-layer-expert |
| 3 | TASK-3.4, TASK-3.5, TASK-2.4 (forward-seam, phase-1-2 progress file) | completed | data-layer-expert, backend-architect, python-backend-engineer |
| 4 | TASK-3.6 (exit gate) | completed | data-layer-expert |
| — | Phase exit validator gate | PASS | task-completion-validator |

### D4 Behavioral Invariant — Verified
- `resolve_workspace_isolation_enforced()` (Phase 1) was not modified anywhere in this phase's diff.
- Every new predicate/filter is gated behind `identity is not None and _isolation_active(...)`.
- With today's real default (`auth.provider == "none"` → advisory/inactive), every touched method
  produces byte-identical SQL/behavior to the pre-WKSP-304 baseline — proven per-method by dedicated
  tests (`test_*_identity_none_is_byte_identical`), not asserted in prose.
- All predicates parameterized (`?` SQLite placeholders); no string interpolation of `workspace_id`
  found anywhere in the 3 service files (validator re-confirmed via grep).
- Full suite: `pytest tests/ -q` → same pre-existing 5-failure cluster in `tests/test_serve_api.py`
  (confirmed unrelated to this change via `git stash` comparison against pre-change `main` HEAD, and
  re-confirmed independently by the validator's own pytest run). No new regressions.

### Forward-Seam Closure (TASK-2.4, phase-1-2 progress file)
Closed jointly per the plan's design. Router call sites in `catalog.py`, `agent_jobs.py`, `reports.py`
now pass `identity=identity` to every Phase-3-scoped service method. Remains inert under D4 (identity
flows through but the flag-gate stays advisory by default).

### Escalation Reason
N/A

### Follow-Up Recommendations (carried forward to Phase 4 entry criteria)
1. **`require_workspace_scope` coverage gap** (TASK-3.5 finding): the shared deny-path helper is wired
   at only 2 of 6 effective deny paths across the 3 services; the other 4 deny/filter directly via
   `KeyError`/`NotFoundError` or WHERE-omission with no audit-log emission. Phase 4 should explicitly
   decide whether to route all 6 through `require_workspace_scope` for uniform audit-logging, or
   document an exemption for WHERE-scoped list/get paths.
2. **Share-link identity semantics** (validator finding, new): `reports.py`'s `resolve_share_link`
   (public share-token endpoint) now threads the *caller's* identity into `load_draft`/`export_markdown`
   for methods it calls. This is inert today, but Phase 4 needs an explicit decision on whether a
   share-token viewer's own workspace identity should ever gate a shared draft that may belong to a
   *different* workspace — the "scope by viewer identity" semantic is not obviously correct for a link
   whose purpose is crossing workspace boundaries. Flag as a P4 entry-criteria item.
3. **Duplicated `_isolation_active()` helper** (TASK-3.5, non-blocking): the helper is intentionally
   duplicated identically across the 3 service files (single-owner-phase design choice to avoid a
   premature shared-module extraction). Worth revisiting for consolidation once Phase 4 adds more call
   sites and the contract is proven stable in production use.
4. TASK-3.6's checklist artifact (`.claude/worknotes/wksp-304-workspace-isolation-enforcement/phase-3-exit-checklist.md`)
   is the literal hard-gate artifact Phase 4's `entry_criteria` depends on — validator has reviewed and
   PASSED it; Phase 4 may proceed.

**Next step**: commit this phase to `main` (validated per git-workflow rule — tests green, validator
PASS), then Phase 4 (the enforcing flip) may begin.
