## Phase 3 Completion Note — Governed URL/PDF extraction adapter (RFUP-2)

### Summary

Phase 3 adds governed PDF text extraction to the `rf fetch` pipeline. A new standalone,
dependency-lazy module (`services/extractors/pdf_extractor.py`, gated behind the
`research-foundry[pdf]` optional extra / `pypdf>=3.0.0`) computes a tri-state extraction outcome
(`full_text`/`partial`/`locator_only`) and never raises. `extract_urls()` in
`services/search_router/router.py` detects `.pdf`-suffixed URLs, downloads bytes, and routes them
through the new extractor instead of the jina/firecrawl chain, with graceful degrade on any
failure. `services/source_cards.py` gained an explicit `ExtractionStatus` enum and
`extraction_status` field (front-matter + registry + `IngestResult`), replacing the previously
implicit `degraded` boolean while preserving it for backward compatibility. One required fix cycle
corrected a gap where the `partial` (truncation) status was computed but never threaded from the
router into the written source card.

### Tasks

- [x] TASK-3.1 → python-backend-engineer — PDF extraction adapter created (`pdf_extractor.py`), `pdf` optional extra added to `pyproject.toml`, pypdf 6.14.2 installed in the shared venv. 4/4 unit tests pass.
- [x] TASK-3.2 → python-backend-engineer — PDF-URL detection + extraction wired into `extract_urls()`; non-PDF path unchanged (regression-tested). 3 new + 16 existing tests pass.
- [x] TASK-3.3 → python-backend-engineer — `ExtractionStatus` enum + `extraction_status` field added to `source_cards.py` (`IngestResult`, front-matter, `SOURCE_INDEX` registry), with an explicit-override kwarg seam for future callers. 5 new + 16 existing tests pass.
- [x] TASK-3.4 → python-backend-engineer — Governance-gate ordering confirmed correct-by-construction (file write precedes any scan); secret-scan regression test added. Surfaced a pre-existing, out-of-scope finding (see Deviations & Risks). 2 new tests pass.
- [x] TASK-3.5 → python-backend-engineer — End-to-end PDF fixture suite (`test_pdf_fixture_suite.py`): text-layer, no-text-layer, corrupted, missing-extra scenarios, all exercising the full `extract_urls()` pipeline. 4 scenarios pass (34 tests total across all Phase 3 files at this point).
- [x] TASK-3.6 → task-completion-validator — **FIX-REQUIRED** on first pass (blocking: `partial` status not threaded from `router.py` into `create_source_card()`); fix dispatched to python-backend-engineer (1 cycle); re-review → **PASS**, 35/35 tests.
- [x] TASK-3.7 → karen (opus) — Tier 3 milestone checkpoint over Phases 1-3 → **PASS**. No unresolved blast-radius findings; Phase 4/5 cleared to proceed.

### Validator Verdict

`task-completion-validator`: **FIX-REQUIRED → PASS** (1 fix cycle). Blocking finding: PDF truncation (`partial`) status was computed by `pdf_extractor.py` but never forwarded from `router.py`'s `extract_urls()` into `create_source_card()`, silently mislabeling truncated extractions as `full_text`. Fixed by threading `extraction_status=pdf_extraction_status` into the PDF-branch call site (`router.py`), plus a new end-to-end regression test (`test_pdf_truncated_by_size_guard_surfaces_partial_end_to_end`). Re-review confirmed the fix and 35/35 tests passing, zero regressions.

`karen` (opus, Tier 3 milestone): **PASS**. Independently re-verified all 35 tests, traced the governance-gate and assertion-ledger claims rather than trusting the validator's summary, and confirmed the pre-existing assertion-ledger secret-scan gap (see below) does not widen under Phase 3 because the PDF path never supplies `assertion_registry_workspace_id` (ledger write is triple-gated and denied by default on this path). Verdict: no unresolved blast-radius findings; Phase 4/5 may proceed.

### Files Changed

- `pyproject.toml` — added `pdf = ["pypdf>=3.0.0"]` optional extra (TASK-3.1)
- `src/research_foundry/services/extractors/__init__.py` — new package (TASK-3.1)
- `src/research_foundry/services/extractors/pdf_extractor.py` — new PDF extraction module (TASK-3.1)
- `src/research_foundry/services/search_router/router.py` — PDF-URL detection + extraction wiring into `extract_urls()`; `pdf_extraction_status` threaded into `create_source_card()` (TASK-3.2, fix cycle 1)
- `src/research_foundry/services/source_cards.py` — `ExtractionStatus` enum, `extraction_status` field on `IngestResult`/front-matter/registry, explicit-override kwarg (TASK-3.3)
- `tests/test_pdf_extractor.py` — unit tests for the extractor module (TASK-3.1)
- `tests/test_search_router_pdf_wiring.py` — router wiring tests (TASK-3.2)
- `tests/test_source_cards_extraction_status.py` — `extraction_status` field tests (TASK-3.3)
- `tests/test_pdf_secret_scan_governance.py` — secret-scan regression test (TASK-3.4)
- `tests/test_pdf_fixture_suite.py` — end-to-end PDF fixture suite, including the `partial`-status regression added in fix cycle 1 (TASK-3.5 + fix cycle)

Total: 35 tests across 6 test files (5 new files + `test_search_router_router.py` regression baseline), all passing. One trivial `ruff` style nit (`UP042`, suggesting `enum.StrEnum` over `class ExtractionStatus(str, Enum)`) — the implemented pattern matches the plan's Implementation Notes verbatim; non-blocking.

Not touched (owned by concurrently-running Phase 2 in the same worktree): `src/research_foundry/cli_commands.py`, `src/research_foundry/services/verification.py`.

### Deviations & Risks

- **Assertion-ledger secret-scan coverage gap (pre-existing, non-blocking, tracked)**: `governance.py::_collect_run_artifacts()` only globs the run directory (`*.md`/`*.yaml`/`*.yml`), so when `ingest_source()`'s optional assertion-ledger write path fires, the copied content lands in `assertion_ledger/workspaces/<id>/` outside that scan surface. This is a pre-existing architectural gap, not introduced by Phase 3, and out of this wave's file-ownership scope to fix (would require touching `governance.py`'s `GuardContext`/artifact-collection). Both `task-completion-validator` and `karen` independently judged it non-blocking for Phase 3 — karen additionally confirmed the PDF path never supplies `assertion_registry_workspace_id`, so the ledger write is denied by default and Phase 3 does not widen this blast radius. **Follow-up recommended**: create a findings doc (`findings_doc_ref` is currently `null` in the plan frontmatter) capturing this before the Phase 6 feature-level seal gate.
- **`rf fetch --json`/CLI surface not modified**: the plan's dev-setup notes reference `rf fetch ... --json | jq '.extraction_status'`, but `services/search_router/cli.py`'s `fetch` command has no `--json` flag today (out of this wave's explicit file-ownership grant, which named only `router.py`/`source_cards.py`/`pyproject.toml`). `extraction_status` is fully machine-readable via the written source-card frontmatter and `SOURCE_INDEX` registry regardless; CLI JSON convenience is a documentation-vs-implementation gap, not a functional gap. Recommend the orchestrator sequence a small follow-up task if the `--json` ergonomics are wanted.

### Commits (worktree runs)

None — per the dispatch instructions for this run, this phase-owner does not commit; the orchestrator commits at wave boundaries. Working tree is otherwise clean of any TASK-ID work outside the granted file-ownership slots (`router.py`, `source_cards.py`, `pyproject.toml`, plus new files under `services/extractors/` and `tests/`).
