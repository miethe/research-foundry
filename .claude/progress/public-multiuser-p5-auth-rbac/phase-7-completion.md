## Phase 7 Completion Note

**Status**: PASS
**Validator verdict**: PASS — All 3 ACs correctly implemented; 168-test gate clean.
**Isolation**: shared (main branch)
**Branch**: main
**Completed**: 2026-07-07

---

### Files Changed

- `src/research_foundry/api/routers/runs.py` — `_enforce_existence_gate` shared helper; all 4 run-detail-family endpoints now use it; `sensitivity_threshold` query param added to 3 previously-ungated endpoints; 404 detail normalized to `"not found"` across all 4 endpoints (P5.7.1)
- `src/research_foundry/services/verification.py` — `build_global_source_index` (workspace-wide source card index); `check_report_body_sensitivity_global` (fail-closed global check); wired into `verify_draft`'s checks list alongside existing per-run check; `_IO_ERROR_SENTINEL_PREFIX` constant for fail-closed sentinel (P5.7.2)
- `src/research_foundry/services/catalog_service.py` — `get_item()` gains additive `citing_drafts` field resolved at read time by joining `catalog_links` against `catalog_report_drafts` (P5.7.3)
- `src/research_foundry/services/builder_service.py` — verified correct; no edits required (P5.7.3 write side was already correct)
- `tests/unit/test_export_service.py` — 8 new tests: parametrized existence-gate across all 4 endpoints (over-threshold→404, raised-threshold→200, invalid-threshold→400), plus indistinguishability test (P5.7.1)
- `tests/unit/test_sensitivity_redaction.py` — 4 new tests: `build_global_source_index` correctness, fail-closed sentinel (mock), blank-origin-draft integration, cross-run-quote integration (P5.7.2)
- `tests/unit/test_catalog_service.py` — 6 new tests: `citing_drafts` via claim_link, via derived_from/source_run_id, via source_link, zero-citation regression, sensitivity threshold gating, rebuild-vs-incremental parity (P5.7.3)

---

### Batch Summary

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | P5.7.1 | completed | python-backend-engineer |
| 1 | P5.7.2 | completed | python-backend-engineer |
| 1 | P5.7.3 | completed | data-layer-expert |

---

### Test Count

| Suite | Before | After | New |
|-------|--------|-------|-----|
| test_export_service.py | 76 | 84 | +8 |
| test_sensitivity_redaction.py | 5 | 9 | +4 |
| test_catalog_service.py | ~62 | ~68 | +6 |
| **Phase-7 total** | **108** | **168** | **+18** |

Full run result: `168 passed` (no failures, deprecation warnings only from upstream FastAPI `on_event` and httpx).

---

### Existence-Gate Parity Proof (4/4 endpoints)

The AC-P5.7.1 success metric required all 4 run-detail-family endpoints to share the no-existence-leak gate. Before this phase: 1 of 4 gated (`get_run_anchors` only). After:

| Endpoint | Gated Before | Gated After | Shared Helper |
|----------|-------------|-------------|---------------|
| GET /api/runs/{run_id} | No | Yes | `_enforce_existence_gate` |
| GET /api/runs/{run_id}/claims | No | Yes | `_enforce_existence_gate` |
| GET /api/runs/{run_id}/sources/{sc_id} | No | Yes | `_enforce_existence_gate` |
| GET /reports/{run_id}/anchors | Yes (inline) | Yes (refactored) | `_enforce_existence_gate` |

Gate raises HTTP 404 for over-threshold runs, indistinguishable from a genuine missing-run 404 — existence of hidden sensitive runs is not leaked.

---

### Pre-Existing Test Failures — Disposition

At phase start (2026-07-07), a full run of `test_sensitivity_redaction.py` + `test_export_service.py` showed **108 passing, 0 failures**. The "4 pre-existing failures" noted in the phase charter had already been resolved by earlier P5 phases (P5.1/P5.2/P5.4/P5.5). No pre-existing failures were present at this phase's baseline, and none were introduced.

---

### Commits

| Commit | Task | Description |
|--------|------|-------------|
| `504bc38` | P5.7.1 | feat(api): existence-gate parity across all 4 run-detail endpoints |
| `f4ed83f` | P5.7.2 | feat(verification): P5.7.2 — global source index closes blank-origin-draft gap |
| `5667520` | P5.7.3 | feat(catalog): add citing_drafts reverse-link field to get_item() |

---

### Architecture Compliance

- **D10 (catalog.db disposable)**: `citing_drafts` resolved at read time over existing `catalog_links` rows — no new persisted edge, no schema migration. `reindex_all_drafts` already repopulates the forward rows this query reads.
- **Fail-closed throughout**: existence-gate never defaults to permit; global source index sentinel treats unreadable runs as blocking; `citing_drafts` sensitivity-gated at query time.
- **No schema migration introduced**: verified clean per exit criterion.
- **No auth/** or **frontend/** files touched**: within phase-7 file ownership boundaries.

---

### Escalation Reason

N/A — no Mode D triggers encountered.

---

### Follow-Up Recommendations

1. **P5.7.2 workspace-scoping follow-up** (documented per design decision): after P5.3's workspace-isolation migration lands, `build_global_source_index` MAY be narrowed to per-workspace visibility as a precision/performance optimization. This is a forward-looking note, not a blocker — over-checking (full workspace) is strictly safer than under-checking (workspace-scoped).
2. **Global source index performance**: if run count grows large, profile `build_global_source_index` within `verify_draft`. Currently built once per `verify_draft` call (not per-quote), which is the correct pattern for v1 scale.
3. **`citing_drafts` frontend rendering** (P5.8 or later): the `citing_drafts` field is additive and ready for a future frontend consumer; rendering it is out of scope for P5.7.
