# Feature Guide — Run Context Panels (FR-14)

> Runs-viewer feature: surface a run's upstream context (routing decision, research
> brief, swarm plan, upstream entities) directly in the run-detail view, sourced from
> an additive `context` block in `run.json` (schema 1.3). Shipped 2026-06-24.

## What was built

**Backend** (`src/research_foundry/services/export_service.py`)
- `EXPORT_SCHEMA_VERSION = "1.3"` (was 1.2; additive + backward-compatible).
- `_context_summary()` emits a `context` block with 4 keys:
  - `routing_decision` — allowlisted fields from `routing_decision.yaml`.
  - `swarm_plan` — allowlisted fields from `swarm_plan.yaml`.
  - `research_brief_md` — verbatim Markdown from `research_brief.md`.
  - `upstream_entities` — `{ intent_id, ibom_id, intenttree_node_id }` (run.yaml + routing `active_node_id`, evidence_bundle fallback).
  - Each field is `null` when its source artifact is absent; the whole `context` is `null` on pre-v2 runs.
- `_redact_str_values()` extends the existing sensitivity redaction to `context.*`, reusing the threshold model (`_sensitivity_rank` / `REDACTION_MARKER` / `resolve_threshold`). Redacts when effective sensitivity exceeds the active viewer threshold.

**Frontend** (`frontend/runs-viewer/`)
- A consolidated **"Context" tab** (replaces the old "Swarm" tab; legacy `swarm` deep-links aliased to `context`).
- `components/RunDetail/ContextPane.tsx` — 4 collapsible sections, collapsed by default, optional-chaining throughout (no hard destructuring of `run.context`):
  1. **Routing Decision** — reuses `RoutingDecisionCard`; adds cost/budget/sensitivity tier from the open record.
  2. **Research Brief** — reuses `ReportOverlay/ReportRenderer` (strips YAML frontmatter).
  3. **Swarm Plan** — `SwarmPlanTree` two-level tree (depth-cap 3) + "Show raw" JSON escape hatch (OQ-3).
  4. **Upstream Entities** — static, offline-safe ID badges (no network call).
  - Each section degrades to its own empty-state when its field is null. Schema guard: `<1.3` or absent context → "Context not available for this run".
- `hooks/useCollapseState.ts` — sessionStorage collapse state, key `rf:context-panel:${runId}:${panelId}`; collapsed on reload.

## Architecture (contract → producer → consumer)
`run.json` schema 1.3 `context` block is the contract (`docs/dev/architecture/rf-run-export-schema.md` §9). The export service is the producer; `ContextPane` is the consumer. The viewer is a **static-export SPA** — everything works offline from `run.json` alone; no `rf serve` required.

## How to test it
1. Export a run with context artifacts: `rf run export <run_id> --json` (or the FE prebuild `pnpm build:runs-viewer` which runs `rf run export --all`). Confirm `run.json` has `schema_version: "1.3"` and a populated `context` block.
2. Open the viewer, navigate to that run's detail → **Context** tab. Expand each section.
3. Backend tests: `PYTHONPATH=src <venv>/python -m pytest tests/unit/test_export_service.py -k context`.
4. FE tests: `cd frontend/runs-viewer && pnpm test` (see `src/test/fr14-context-pane.test.tsx`).
5. Offline invariant: `pnpm build` then serve `dist/` statically — panels must render from `run.json` with no backend.

## Test coverage
- Backend: 14+ `test_context_*` cases — all-present, each-absent-independently (all 4), all-absent→null, node-id bundle fallback, redaction (routing/swarm/brief), threshold pass-through, full pipeline round-trip, backward-compat (schema 1.2 no-context), production-threshold governance.
- Frontend: 38 tests (FE-001..006) across all 4 sections — populated render, per-field empty-states, frontmatter strip, swarm tree expand + raw toggle, badge accessibility, RunDetailWorkspace integration, schema guard.

## Known limitations
- **Upstream entity links are non-navigable** (static badges). Live reachability/navigation was deferred to keep the offline-static invariant; see DFR-001.
- **Lazy-load via loopback API** (`GET /runs/{run_id}/context`) deferred to v2 — design spec `docs/project_plans/design-specs/runs-context-panels-lazy-load-v2.md`. v1 embeds context in `run.json`.
- At the distribution default threshold (`client_sensitive`), `work_sensitive` context content is **not** redacted (deliberate operator config; self-documented by a dedicated test).
- `SwarmPane.tsx` is now unwired (superseded by `ContextPane`); left for a future cleanup.
