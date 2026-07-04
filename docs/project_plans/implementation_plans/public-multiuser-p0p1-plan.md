---
title: "Public Multi-User Release — Phase 0 + Phase 1 Implementation Plan"
doc_type: implementation_plan
status: active
created: 2026-07-04
feature_slug: public-multiuser-release
feature_version: v1
phases_covered: [0, 1]
source_spec: docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md
branch: feat/public-multiuser-p0p1
owner: nick
orchestrator: fable-5
---

# Public Multi-User Release — Phase 0 + Phase 1 Plan

Scope: Phase 0 (route/IA cleanup) + Phase 1 (shared evidence catalog read model)
from the handoff spec. Per spec §15: do NOT attempt later phases. Preserve
current run-viewer behavior, `run.json` semantics, and the no-LLM-on-recall-path
constraint. Mockup target: `assets/public-multiuser-release/mockup-evidence-catalog.png`.

## Frozen Design Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Catalog store = stdlib `sqlite3` + FTS5 at `<workspace>/.rf_cache/catalog.db` (already gitignored). Derived, rebuildable read model; `PRAGMA user_version = 1`; on version mismatch drop + rebuild. No new runtime dependency, no migration framework. | Files stay canonical; DB is derived (AOS constraint 2). 38 runs / ~3.3k claims is trivially in FTS5 range. |
| D2 | Import runs through `export_service.export_run()` live (NOT by reading stale `run.json` files), with `threshold="client_sensitive"` (max permissive) at import; sensitivity is gated at READ time in `catalog_service` reusing `SENSITIVITY_ORDER` / `resolve_threshold` semantics (fail-closed on unknown labels). Over-threshold items are EXCLUDED from search/list; source quotes/summaries inside payloads are redacted with `REDACTION_MARKER`. | Mirrors the export layer's store-raw/gate-on-read model; server-side enforcement per spec §11. |
| D3 | `/library` → redirect to `/catalog`. Nav item Library replaced by Catalog. Builder + Agents added as `disabled` nav entries with `disabledReason` (existing `NavState` pattern). Reusable outputs / reports / writebacks become catalog tabs, so no capability is lost. | Spec §5: don't keep overlapping top-level concepts; no false affordances. |
| D4 | Frontend catalog is dual-mode like every other data path: loopback mode calls `/api/catalog/*`; static mode builds the SAME index client-side in `src/lib/catalog.ts` from batch-loaded run exports (existing `useQueries` pattern from LibraryScreen). Shared pure functions keep semantics identical and unit-testable. | Static mode is the default deployment; catalog must work there. |
| D5 | Deterministic IDs: `catalog_item_id = "ci_" + sha1("{item_type}:{run_id}:{local_ref}").hexdigest()[:12]`. `run_id` + `local_ref` preserved as alias columns/fields (spec §6 requires run-local IDs preserved as aliases). Re-import of a run is delete-then-insert in one transaction → idempotent. | Stable across imports, debuggable via alias fields. |
| D6 | No auth/RBAC/workspace tables in this pass (Phase 5, Mode-D). `workspace_id` is NOT added yet; the item model keeps `project` (from `linked_projects[0]`/`category`) for filtering. | Spec phases it later; auth is an open question (§14). |

## Item mapping (import contract)

From `export_run(rp, threshold="client_sensitive")` output:

| Export field | item_type | Notes |
|---|---|---|
| `claims[]` with empty/absent `inference_basis.from_claims` | `claim` | title = claim text (truncate 160); status = claim `status`; confidence = `confidence`; trust_label = status. |
| `claims[]` with non-empty `inference_basis.from_claims` | `inference` | same fields; links `inference → from_claim` recorded. |
| `claims[*].sources[]` where `resolved && !dangling`, deduped by `source_card_id` | `source` | title/source_type/url/trust/usage/sensitivity from resolved source; payload holds evidence points seen (locator/summary/quote per claim-use). |
| `report_draft != null` | `report` | one per run; title = run title; summary = first non-heading paragraph; payload = report_draft + writebacks summary + claim_counts. |
| `reusable_output_candidates[]` | `reusable_output` | as-is. |
| `writebacks.targets[]` | `writeback` | status normalized like LibraryScreen's `normalizeWritebackStatus`. |

Item `sensitivity`: source item → its own effective label (max of card/point rank);
claim/inference → max(run sensitivity, max source effective sensitivity);
report / reusable_output / writeback → run sensitivity. Unknown labels rank as
strictest (fail-closed, same as export layer).

Links table rows: `claim → source` (`supports`), `inference → claim`
(`inferred_from`), `report → claim` (`contains`, from claims with
`report_locations` non-empty).

## Backend deliverables (Wave B)

Files (new unless noted):

- `src/research_foundry/services/catalog_service.py` — schema DDL, `import_run(paths, run_id)`, `import_all(paths)`, `search(paths, query: CatalogQuery)`, `get_item(paths, catalog_item_id)`, `stats(paths)`, threshold gating, FTS5 (external-content or contentless; MATCH on title+summary+body with bm25 ranking; graceful LIKE fallback if FTS5 unavailable).
- `src/research_foundry/paths.py` (edit) — `catalog_db` property under `.rf_cache/`.
- `src/research_foundry/api/routers/catalog.py` — mirror `runs.py` conventions (`get_paths` DI, raw dicts, R1 invariant: all data via `catalog_service`):
  - `GET /api/catalog/stats` → `{counts: {claim,source,inference,report,reusable_output,writeback}, runs_indexed, last_import_at}`
  - `GET /api/catalog/search?q=&item_type=&project=&status=&sensitivity=&run_id=&sort=&page=&page_size=` → `{items: CatalogItemSummary[], total, page, page_size, facets:{projects,statuses,sensitivities}}` (page_size default 25 max 200; sort ∈ updated|title|confidence)
  - `GET /api/catalog/items/{catalog_item_id}` → summary fields + `payload` + `links` (404 unknown id or over-threshold)
  - `POST /api/catalog/import/run/{run_id}` and `POST /api/catalog/import` (all runs) → `{imported:{runs,items}}`
- `src/research_foundry/api/app.py` (edit) — mount catalog router.
- `src/research_foundry/cli_commands.py` (edit) — `catalog_app` Typer group: `rf catalog import [RUN_ID|--all]`, `rf catalog search`, `rf catalog show <id>`, `rf catalog stats`, `rf catalog rebuild`. Thin bodies, lazy service import, `_fail(RFError)` on usage errors, `--json` output flags per existing convention.
- Tests: `tests/unit/test_catalog_service.py` (import determinism + idempotency incl. double-import, ID stability, mapping per table above, sensitivity exclusion fail-closed incl. unknown label, FTS search, rebuild-on-user_version-mismatch) and `tests/test_serve_catalog.py` (TestClient + `dependency_overrides[get_paths]` + `tmp_foundry`-style workspace: stats/search/detail/import endpoints, threshold enforcement, 404s). Deterministic + offline, fixed-clock compatible.

CatalogItemSummary fields: `catalog_item_id, item_type, title, summary, run_id,
local_ref, project, status, sensitivity, trust_label, confidence, source_count,
created_at, updated_at`.

## Phase 0 deliverables (Wave A — frontend IA cleanup, own commit, lands FIRST)

- `src/app/AppShell.tsx` — `NAV_ITEMS`: Library→`{label:"Catalog", short:"CT", target:/catalog}`; insert after Catalog: `{label:"Builder", short:"BD", state:"disabled", disabledReason:"Planned — report composition workspace (Phase 3)"}` and `{label:"Agents", short:"AG", state:"disabled", disabledReason:"Planned — governed agent research (Phase 4)"}`. Update `isActiveNav` (Catalog active on `/catalog` and `/library`).
- `src/app/App.tsx` — `/catalog` renders existing `LibraryScreen` (temporary until Wave C); `/library` → `<Navigate to="/catalog" replace/>`.
- `src/app/routes.tsx` — rename `library` route entry to `catalog`; check all `RouteName` usages.
- `src/test/g4-library.test.tsx` — update nav/route expectations (Catalog label, /catalog path, redirect, Builder/Agents disabled with `aria-disabled`).
- Gate: `pnpm --dir frontend/runs-viewer test && lint && build` green. Do NOT touch anything else.

## Phase 1 frontend deliverables (Wave C — after Wave A commit)

- `src/types/rf/catalog.ts` — `CatalogItemType`, `CatalogItemSummary`, `CatalogItemDetail`, `CatalogSearchParams`, `CatalogSearchResult`, `CatalogStats` (mirror backend contract above exactly).
- `src/lib/catalog.ts` — pure: `buildCatalogIndex(runs: RFRunExport[]): CatalogIndex` implementing the SAME item mapping table as the backend importer (including inference rule + sensitivity derivation + dedupe), `searchCatalog(index, params)` (case-insensitive substring match over title/summary/body; same filter semantics), `catalogStats(index)`.
- `src/api/client.ts` (edit) — `fetchCatalogStats()`, `fetchCatalogSearch(params)`, `fetchCatalogItem(id)`: loopback mode → `/api/catalog/*`; static mode → build index from `fetchRunList` + all `fetchRunDetail` (cache the built index in module/queryClient).
- `src/hooks/` — `useCatalogSearch`, `useCatalogStats`, `useCatalogItem` React Query wrappers.
- `src/screens/CatalogScreen.tsx` (replaces LibraryScreen at `/catalog`; delete `LibraryScreen.tsx` + `library.css` after content absorbed) — per mockup:
  - Header: "Evidence Catalog" + subtitle.
  - Tab strip with live counts: Claims / Sources / Inferences / Reports / Report-ready (report-ready = reusable_output + writeback items).
  - Filter row: Project, Trust/Status, Sensitivity, Status selects + free-text search input; result count + sort control.
  - Results table: ID (local_ref), title/summary, trust chip (`it-chip` green/amber/red by status: supported→green, partially→amber/orange, refuted→red, else neutral), sensitivity chip, status pill, project, updated. Row click selects.
  - Right rail selected-item inspector: title, status chip, provenance chain strip (Source Card → Extraction → Inference → Report → Writeback presence), source cards via existing `SourceCard` component, inference basis block, usage policy chips; actions "Add to Report" + "Run Follow-up Research" rendered DISABLED with title tooltips ("Planned — Phase 3/4").
  - Reports tab rows: published-report entries (from Library §Published Reports semantics); Report-ready tab: reusable outputs + writeback artifacts with status badges. Open-run action opens `RunDetailModal` (existing pattern).
  - Empty/loading states via `EmptyState`.
- `src/styles/catalog.css` — token-driven, `rv-catalog*` BEM, registered in `styles/index.css`.
- Tests: replace `g4-library.test.tsx` with catalog suite (nav + redirect kept; tab counts, filtering, tab switching, selection inspector, disabled actions, static-mode index building via fixtures) + `src/lib/catalog.test.ts` unit tests for mapping/search parity rules.
- Gate: `pnpm --dir frontend/runs-viewer test && lint && build` green.

## Validation (run before PR)

```sh
pnpm --dir frontend/runs-viewer test && pnpm --dir frontend/runs-viewer lint && pnpm --dir frontend/runs-viewer build
uv run --extra serve --extra dev pytest -q
uv run --extra serve --extra dev python -m research_foundry catalog import --all && uv run --extra serve --extra dev python -m research_foundry catalog stats
```

## Commit / PR protocol

Worktree `.claude/worktrees/public-multiuser-p0p1`, branch `feat/public-multiuser-p0p1`,
base `main`. One commit per wave (plan, Phase 0, backend, frontend, review fixes).
Draft PR to `main`; squash-merge only on approval.
