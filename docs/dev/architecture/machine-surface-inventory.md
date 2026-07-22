---
title: "Research Foundry — Machine Surface Inventory"
description: "Enumerates every machine-readable rf surface targeted for rf_schema_version stamping (PRD FR-4.1 / AC-RFUP4-1), its current stamped value, and which phase task stamps it."
audience: [ai-agents, developers]
created: 2026-07-18
status: draft
category: architecture
doc_type: architecture
related_documents:
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/dev/architecture/rf-run-export-schema.md
  - docs/dev/architecture/artifact-type-reference.md
---

# Research Foundry — Machine Surface Inventory

## Purpose

PRD FR-4.1 (`docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md`) requires a
single canonical `rf_schema_version` semver string, stamped as a top-level field on every
machine-readable `rf` surface, so downstream consumers (the runs-viewer, external tooling, future
RF API clients) can detect contract drift instead of guessing at shape from field presence. This
doc is the AC-RFUP4-2 artifact: it enumerates every surface in AC-RFUP4-1's scope, its state as of
this scaffold task (TASK-1.1), and the task that will wire the stamp in.

**Phase 1 status**: TASK-1.1 scaffolded this doc; TASK-1.2 (CLI `--json` outputs, exit-code contract
doc) and TASK-1.3 (verify output, run-export type, LAN API payloads) have both landed the stamp —
see the per-surface rows below. All changes are additive-only; no existing output shape changed.

## Canonical constant

`RF_SCHEMA_VERSION = "1.0.0"`, defined in `src/research_foundry/__init__.py:23` (see the constant's
docstring there for why it is distinct from the pre-existing, unused `SCHEMA_VERSION` and from
`EXPORT_SCHEMA_VERSION` in `services/export_service.py`, which versions the narrower run-export
document schema, currently `"1.5"`).

## Target surfaces (AC-RFUP4-1)

AC-RFUP4-1 as written in the PRD lists 6 items; the human-brief noun-count analysis
(`docs/project_plans/human-briefs/rf-upstream-evidence-foundry.md:81`) and the actual acceptance
text enumerate **7** distinct surfaces once `/api/runs`, `/api/reports`, and `/api/catalog` are
counted individually alongside the runs-viewer export type and the two CLI/verify surfaces. This
table lists all 7 — it supersedes the implementation-plan task table's stale count of 6.

| # | Surface | File | Current stamped value | Stamped by |
|---|---|---|---|---|
| 1 | Exit-code contract (`ExitCode` enum) | `src/research_foundry/errors.py` | N/A — no code change; `ExitCode` (0–7) has no `rf_schema_version` field and emits no JSON payload itself (it is a process-exit contract, not a payload). The FR-4.2 contract doc (api-designer, TASK-1.2) explicitly states the enum + YAML/JSON output *is* the stable machine contract. | TASK-1.2 (contract doc only) |
| 2 | CLI `--json` outputs | `src/research_foundry/cli_commands.py` | `1.0.0` — every dict-shaped `--json`/error-payload output now threads through a new `_stamp()` helper (`cli_commands.py`, added after `_fail`) that injects `"rf_schema_version": RF_SCHEMA_VERSION` as a top-level key, additive-only. Five array-root outputs (`rf run list`, `rf report draft list`, `rf rights list`, `rf rights validate`, `rf rights backfill` — bare `list[dict]`, no top-level key to attach to without a non-additive shape change) are deliberately left unstamped, flagged inline with a `NOTE:` comment at each site for TASK-1.4 to account for in the drift-test surface enumeration. | TASK-1.2 (done); rights-entity-model-v1 fix cycle (karen review) — `rf rights inspect` stamped (dict-root); `rf rights list`/`validate`/`backfill` added as array-root exclusions |
| 3 | Verify YAML/JSON output | `src/research_foundry/services/verification.py` (`verify_report`, `verify_draft`) | `1.0.0` — top-level key on the `record` dict persisted to `verification.yaml` / `<draft_dir>/verification.yaml` (both functions), and mirrored as a defaulted field on the `VerificationResult` dataclass itself so any `--json` serialization built from the returned object (TASK-1.2, `cli_commands.py`) carries it without further plumbing. **Phase 2 addition (RFUP-3):** `exact_passage_violations: list[str]` optional field added to `VerificationResult` (populated by exact-passage check when violations exist; empty list or omitted when zero violations, per AC-RFUP3-5 resilience). | TASK-1.3 (done); Phase 2 (exact_passage_violations field added) |
| 4 | Runs-viewer run-export schema | `src/research_foundry/services/export_service.py` (`export_run()`, the generator), mirrored by `frontend/runs-viewer/src/types/rf/run-export.ts` (the TS type declaration) | `1.0.0` on the actual `run.json` payload: `export_run()`'s return dict now carries `"rf_schema_version": RF_SCHEMA_VERSION` alongside `"schema_version": EXPORT_SCHEMA_VERSION` (~line 1108), so every `run.json` file written by `rf run export --all` (consumed by `frontend/runs-viewer/public/data/*.json`, the runs-viewer's static export build) is stamped, not just its TS type. `RFRunExport.rf_schema_version?: string` is the additive optional field on the TS side (`schema_version`/`EXPORT_SCHEMA_VERSION` unchanged at `"1.5"`). `RFVerification` intentionally does **not** get the field (see the type's doc-comment) — `export_service.py`'s verification sub-block is a derived subset (`present`/`passed`/`exit_code`/`checks`), not a mirror of `verification.yaml`, so row 3's new field is not threaded into it. **Phase 3 addition (RFUP-2):** source-card `extraction_status` field (`full_text|partial|locator_only` enum, defined on `SourceCard.frontmatter.extraction_status`) is now populated on all source cards and is available downstream (consumed by run-export where extraction details appear). **Phase 4 addition (RFUP-5/7):** `--seal` additive flag on `rf run export` writes an append-only `lineage.yaml` record to `<run>/lineage.yaml` for tamper-evidence; `RunPaths.lineage` property provides access. | TASK-1.3 (TS type only); TASK-1.5 fix cycle (actual generator); Phase 3 (extraction_status); Phase 4 (--seal/lineage) |
| 5 | `/api/runs` | `src/research_foundry/api/routers/runs.py` | `1.0.0` on every top-level `dict` response via a shared `stamp()` helper (`src/research_foundry/api/response_stamp.py`): `GET /runs/{run_id}`, `GET /runs/{run_id}/sources/{source_card_id}`, `GET /reports/{run_id}/anchors`, `POST /runs`. `GET /runs` and `GET /runs/{run_id}/claims` are array-shaped — N/A, no top-level object to stamp without a breaking shape change. `GET /runs/{run_id}/context` is intentionally excluded — its docstring states the response mirrors `run.json`'s `context` sub-object exactly. | TASK-1.3 (done) |
| 6 | `/api/reports` | `src/research_foundry/api/routers/reports.py` | `1.0.0` on every top-level `dict` response (create/get draft, revisions, block/claim-link/source-link CRUD, verify, publish-preview, export, share-links) via the same `stamp()` helper. `GET /reports` and `GET /reports/{id}/versions` are array-shaped — N/A. | TASK-1.3 (done) |
| 7 | `/api/catalog` | `src/research_foundry/api/routers/catalog.py` | `1.0.0` on `GET /catalog/stats`, `GET /catalog/search`, `GET /catalog/items/{id}`, `POST /catalog/import/run/{id}`, `POST /catalog/import` via the same `stamp()` helper. | TASK-1.3 (done) |

## Phase 2–4 field additions (additive to RFC_SCHEMA_VERSION 1.0.0)

**Phases 2–4 added new optional fields to existing surfaces without bumping `RF_SCHEMA_VERSION`** (all additions are backward-compatible additive changes):

- **Phase 2 (RFUP-3, exact-passage verification):** `exact_passage_violations: list[str]` field on verify output (row 3) — populated when exact-passage checks fail, omitted/empty when zero violations.
- **Phase 3 (RFUP-2, PDF extraction):** `extraction_status: str` field on source cards (`full_text|partial|locator_only` enum values) — indicates the level of text extraction from a source, used downstream in run-export and API responses for source details.
- **Phase 4 (RFUP-5/7, run sealing + council review):** `--seal` flag on `rf run export` (row 4) creates tamper-evidence lineage records; `CouncilVerdict` enum (`approve|concern|block`) available via `normalize_council_verdict()` in `adapters/arc_council.py` for council verdict normalization (CLI/YAML boundary only; does not affect run-export.ts schema per OQ-4).

## Non-goals for this task

- No output shape changes beyond the additive `rf_schema_version` key (TASK-1.2/1.3 done).
- No contract drift tests yet (TASK-1.4).
- ~~No decision on whether `/api/runs`, `/api/reports`, `/api/catalog` share one stamping helper~~ —
  resolved by TASK-1.3: a single shared `stamp()` helper (`src/research_foundry/api/response_stamp.py`),
  applied per-router rather than as `create_app()` middleware, because a middleware-level envelope
  would have to wrap **every** response uniformly — including the array-root endpoints
  (`GET /runs`, `GET /runs/{id}/claims`, `GET /reports`, `GET /reports/{id}/versions`) — which is not
  additive-safe for a JSON array (no top-level key namespace without changing the response from an
  array to an object, a breaking shape change for the runs-viewer client). Per-endpoint stamping at
  the router layer stamps every dict-shaped response while leaving array-shaped ones untouched.

## Verification checklist (fills in as later tasks land)

- [x] `rf_schema_version` present on surfaces 1–7 above (TASK-1.2, TASK-1.3; row 4's generator closed
      by the TASK-1.5 fix cycle) — surface 1's "N/A" entry is an intentional, documented exclusion,
      not a gap.
- [x] Contract drift tests assert presence/value on all 7 surfaces (TASK-1.4; row 4's generator
      closed by the TASK-1.5 fix cycle) — see `tests/test_contract_drift_rf_schema_version.py`: unit
      tests on the shared `_stamp()`/`stamp()` helpers (with a monkeypatch proving divergence is
      actually caught), a structural scan of every `_json.dumps(` call site in `cli_commands.py` (27
      stamped / 5 array-root exclusions / 4 unrelated field-echo sites — all accounted for; updated
      from 26/2/2 by the rights-entity-model-v1 fix cycle's `rf rights` command group, see row 2), a
      live `export_run()` presence+value smoke test, and live CLI/`verify`/API presence+value smoke
      tests.
- [x] Before/after key-diff on a fixture run shows zero renamed/removed keys (TASK-1.4; row 4's
      generator closed by the TASK-1.5 fix cycle) — raw service-layer output vs. stamped CLI/API
      output for catalog/runs/reports; `git show HEAD:<path>` vs. current source for
      `verification.py`'s persisted `record` dict, `export_service.py`'s `export_run()` return dict,
      `run-export.ts`'s `RFRunExport` interface, and `__init__.py`'s `__all__` — each confirms the only
      added key/field is `rf_schema_version`.
