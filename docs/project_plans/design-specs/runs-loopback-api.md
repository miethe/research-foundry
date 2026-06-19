---
title: "Design Spec: Runs Viewer — Live Loopback API (OQ-6 / FR-11)"
doc_type: design_spec
schema_version: 2
status: draft
maturity: idea
created: 2026-06-19
updated: 2026-06-19
feature_slug: runs-frontend
deferred_from: runs-frontend-v1
deferred_item_id: OQ-6
category: scope-cut
owner: nick
related_docs:
  - docs/dev/architecture/adr-runs-read-path.md
  - docs/dev/architecture/rf-run-export-schema.md
  - docs/project_plans/design-specs/runs-auth-lan.md
  - docs/project_plans/implementation_plans/features/runs-frontend-v1.md
---

# Design Spec: Runs Viewer — Live Loopback API (OQ-6 / FR-11)

> **Maturity: idea** — pre-commitment stub. No implementation has been
> scoped. Promote to `proposal` when the promotion trigger fires.

---

## Deferral Summary

| Field | Value |
|-------|-------|
| **Deferred from** | `runs-frontend-v1` (Phase 5, DOC-006) |
| **Reason** | Static-export cycle (`rf run export --json --all` pre-build) is sufficient for the current operator cadence. The "browse as runs land" JTBD — wanting the viewer to reflect a run that just completed without re-running export — has not been validated post-P2. Shipping a live API before validating the JTBD adds protocol and auth complexity without confirmed value. |
| **Promotion trigger** | Operator identifies a real "browse as runs land" JTBD where the static export rebuild cycle is too slow or too manual; **or** the run corpus grows to a size (100+ runs) where `--all` export time is materially disruptive to the operator's workflow. |
| **Target spec path** | `docs/project_plans/design-specs/runs-loopback-api.md` (this file) |

---

## Flag Status

The SPA fetch client is structured behind a **`RUNS_FRONTEND_LOOPBACK_API`**
environment variable (set at build time). When the flag is unset (default), the
SPA loads `run.json` files from a static directory. When the flag is set to a
base URL (e.g. `http://localhost:7432`), the same React Query hooks route
requests to the live API instead.

This means the component layer is **already decoupled** from the read path.
Implementing the loopback API requires:
1. A Python `rf serve` command (or `rf run serve`) that reads from disk on
   demand and applies the same sensitivity gate as the export service.
2. Client-layer wiring in `frontend/runs-viewer/src/api/` to switch from
   static-file URLs to `${RUNS_FRONTEND_LOOPBACK_API}/runs/…`.
3. No component-level changes.

---

## Scope (idea-stage)

When promoted, this spec would cover:

- **API surface** — minimal REST API for the runs viewer's data needs:
  `GET /runs` (index, same shape as `rf run list --json`),
  `GET /runs/:run_id` (full export, same shape as `run.json`).
  No mutation endpoints — read-only invariant preserved.
- **Sensitivity gate** — same threshold model as the export service; the API
  applies redaction at the response-serialization layer, not in the client.
- **Process model** — `rf serve --port PORT` as a long-running foreground
  process, or as a `systemd --user` service on `agentic-nuc`.
- **Hot-reload** — whether the API re-reads from disk on each request (simple,
  correct) or caches with a filesystem-watch invalidation.
- **Auth coordination** — this spec depends on OQ-4 (auth/LAN exposure) for
  any non-loopback deployment; design together.
- **Flag wiring** — finalize `RUNS_FRONTEND_LOOPBACK_API` semantics, including
  how `rf run export --json` and `rf serve` co-exist (export can still write
  `run.json` for offline use even when the API is running).

### v1 Invariant

In v1, `RUNS_FRONTEND_LOOPBACK_API` is always unset. The export service is the
only supported data path. The ADR (`adr-runs-read-path.md`) records this.

---

## Notes for Promotion

- The `RUNS_FRONTEND_LOOPBACK_API` flag is the seam — validate that it works
  before designing the server. The P2 data layer was built with this flag in
  mind.
- The frozen export schema (`rf-run-export-schema.md`) is the API's response
  contract; no new shape design needed — just HTTP transport on top.
- The loopback API should reuse `export_service.py` logic, not duplicate it.
  Consider `export_service.export_run(run_id) -> dict` as the shared core.
