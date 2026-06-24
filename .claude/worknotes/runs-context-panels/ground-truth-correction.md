# Ground-Truth Correction — runs-context-panels-v1 execution

> Authored by Opus orchestrator at execution start (2026-06-24). The implementation
> plan and progress files were authored against ASSUMED paths/structure that diverge
> from the real codebase. This doc is the authoritative file map + reconciliation for
> every phase. All dispatched agents (native + ICA) consume it.

## Corrected file map (plan path → reality)

| Plan / progress path (WRONG) | Real path |
|---|---|
| `src/research_foundry/schemas/run_export.py` (RunContext dataclass) | **No such file/dataclass.** Export is plain-dict in `src/research_foundry/services/export_service.py` |
| `src/runs_viewer/types/run.ts` | `frontend/runs-viewer/src/types/rf/run-export.ts` (hand-written `RFRunExport`) |
| `src/runs_viewer/components/RunDetail/*Panel.tsx` | `frontend/runs-viewer/src/components/RunDetail/*Panel.tsx` |
| `src/runs_viewer/components/RunDetail/RunDetailWorkspace.tsx` | `frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx` |
| `ReportMarkdownRenderer` | `frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx` |
| "lineage-graph collapsible" visual ref | `frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx` |

## Pre-existing code (CRITICAL — do NOT build from scratch)

### Backend (`src/research_foundry/services/export_service.py`)
- `EXPORT_SCHEMA_VERSION = "1.2"` at line ~36 → **bump to `"1.3"`**. Stamped into output at line ~638.
- **`_context_summary(rp, *, run_id)` ALREADY EXISTS** (line ~426) and is **already wired** into `export_run()` (assigned line ~623, emitted as `"context": context_summary` at line ~658).
  - It already emits `routing_decision` + `swarm_plan` sub-objects, filtered through `_ROUTING_DECISION_ALLOWLIST` (~L400) and `_SWARM_PLAN_ALLOWLIST` (~L412).
  - It returns `None` when both source files absent (pre-v2 safety).
  - **Missing sub-objects to ADD: `research_brief_md` (verbatim from `research_brief.md`) and `upstream_entities`.**
  - **DO NOT create a separate `_build_context()` — EXTEND `_context_summary()` instead** (the plan's `_build_context` name describes the same function; avoid duplication).
- **Redaction does NOT yet cover the `context` block.** `_sensitivity_rank()` (~L120), `REDACTION_MARKER` (~L51), threshold via `resolve_threshold`. Redaction is currently applied to claim quote/summary only (~L277–294). P2 must add a pass that redacts sensitive text inside `context.*`.
- `RunPaths` (`src/research_foundry/paths.py`) already exposes `.routing_decision`, `.research_brief`, `.swarm_plan` properties. Read via these — no stored absolute paths.

### Upstream entity IDs (for `context.upstream_entities`)
- `intent_id`: in `run.yaml`, already exported top-level.
- `ibom_id`: in `run.yaml`, NOT yet exported — read `run_meta.get("ibom_id")`.
- `intenttree_node_id`: NOT in run.yaml — it's `active_node_id` in `routing_decision.yaml` (also `intenttree_node_id` nested in `evidence_bundle.yaml` governance). Degrade gracefully if absent.

### Frontend (`frontend/runs-viewer/`)
- TS run type: `src/types/rf/run-export.ts` → `interface RFRunExport` (line ~259), `schema_version: string` (~L260). **Hand-written** (re-exported via `types/rf/index.ts`). Add `RFRunContext` + `context?: RFRunContext | null` here. Generated sub-types exist and can be reused: `types/rf/routing_decision.generated.ts`, `types/rf/swarm_plan.generated.ts`, `types/rf/research_brief.generated.ts`.
- `RunDetailWorkspace.tsx` receives `run: RFRunExport` prop (line ~19); already uses optional chaining (`run.governance?`, `run.writebacks?`). Panels mount here.
- **`SwarmPane.tsx` already exists** in `components/RunDetail/` — inspect it before building `SwarmPlanPanel`; reuse/extend its rendering rather than duplicating swarm visualization where sensible.
- MD renderer to reuse for ResearchBriefPanel: `components/ReportOverlay/ReportRenderer.tsx`.
- Tests: `vitest` (`pnpm test` in `frontend/runs-viewer/`), `tsc --noEmit` via `pnpm exec tsc -b --noEmit` or `pnpm build` (tsc -b + vite). Example unit test: `components/RunDetail/detailTabs.test.ts`.

## Commands (run from worktree root unless noted)
- Python tests: `./.venv/bin/python -m pytest` from main checkout with `PYTHONPATH=<worktree>/src`, OR `uv run pytest` — pyproject sets `pythonpath = ["src"]`. (See memory: editable install points at main; for worktree use `PYTHONPATH=<wt>/src <main>/.venv/bin/python -m pytest`.)
- FE: `cd frontend/runs-viewer && pnpm install && pnpm test` and `pnpm build` (= `tsc -b && vite build`).

## P3 APPROACH DECISION (user-approved 2026-06-24): RECONCILE — extend existing

The feature is ~60% shipped. TS context types (`RFRunContextSummary`, 4 sub-objects) are
already fully defined; `SwarmPane.tsx` (the "Swarm" tab) already renders Routing Decision +
Swarm Plan via `RoutingDecisionCard` + `SwarmPlanSection` (from `@/screens/SwarmScreen`) +
`AgentsList`, with graceful empty state. Only `research_brief_md` + `upstream_entities` are
unrendered.

**Do NOT build 4 standalone panels from scratch. Do NOT duplicate routing/swarm rendering.**
Instead, evolve the existing Swarm tab into a consolidated **"Context"** presentation with
4 collapsible sections (collapsed by default), in this order:
1. **Routing Decision** — reuse existing `RoutingDecisionCard` (wrap in a collapsible section).
2. **Research Brief** — NEW; reuse `components/ReportOverlay/ReportRenderer.tsx` (pass
   `run.context.research_brief_md`; ReportRenderer already strips frontmatter via
   `stripReportMetadata`). Pass `claims={[]}` + no-op `onClaimSelect` if claim chips aren't wanted.
3. **Swarm Plan** — reuse existing `SwarmPlanSection` (+ `AgentsList`) wrapped collapsible.
4. **Upstream Entities** — NEW; render `intent_id`/`ibom_id`/`intenttree_node_id` as badge
   links (online) / plain-text badges (offline, best-effort ping never blocks), following the
   `LineageList.tsx` expand/`Set<string>` + chevron pattern for any tree structure.

Collapse state: new `src/hooks/useCollapseState.ts` hook, key `rf:context-panel:${runId}:${panelId}`
(panelId ∈ routing_decision|research_brief|swarm_plan|upstream_entities), sessionStorage, reset to
collapsed on reload. Wire into `RunDetailWorkspace` (the Swarm tab becomes "Context"; keep the
existing graceful empty state when `run.context` absent → schema guard for pre-1.3 runs).
Reuse existing test fixtures in `src/test/fixtures/` (`run.json`, `scaffold-run.json`); extend
fixtures with research_brief_md + upstream_entities sample data.

This satisfies the design spec ("design them together, not as four independent features";
"likely as tabs"). Plan ACs (each context surface renders + per-field resilience) are met by
the 4 collapsible sections.

## P4 cleanup carried forward (from P1 governance gate, non-blocking)
- `docs/dev/architecture/rf-run-export-schema.md` §14 and §15 prose still say "1.2" — update to 1.3 in P4-003 (schema doc finalize).
- Backward-compat test (`test_export_service.py` ~L1255) tests Python dict access only, not a JSON round-trip — add a round-trip assertion in P4-001 (BE test hardening).
- GOVERNANCE (from P2 gate): at the production threshold (`foundry.yaml viewer.sensitivity_threshold: client_sensitive`, rank 3), `work_sensitive` (rank 2) context content passes through UNREDACTED — this is intentional (operator chose client_sensitive). Add a self-documenting test in P4-001: `test_context_work_sensitive_not_redacted_at_production_threshold` (asserts pass-through at production threshold, catching accidental future tightening). karen feature-end gate will scrutinize redaction coverage — this test pre-empts it.

## Reconciliation summary of plan scope
- P1: bump version 1.2→1.3; extend `_context_summary` to emit all 4 keys (2 new as `null` placeholders to freeze shape); add `RFRunContext` TS type; schema doc §9 stub; backward-compat test; backend-architect gate.
- P2: populate `research_brief_md` + `upstream_entities`; null-fill semantics; redaction pass over `context.*`; export integration test; serialization-barrier check.
- P3: 4 panels in `frontend/runs-viewer/src/components/RunDetail/`; wire into `RunDetailWorkspace`; sessionStorage collapse; schema guard; smoke.
- P4: BE+FE test hardening; schema doc finalize; CHANGELOG; DFR-001 spec; karen gate.
