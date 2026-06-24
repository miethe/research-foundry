---
title: "Design Spec: Runs Viewer — Context Panels Lazy-Load (DFR-001, v2)"
doc_type: design_spec
schema_version: 2
status: draft
maturity: shaping
created: 2026-06-24
updated: 2026-06-24
feature_slug: runs-context-panels-lazy-load
deferred_from: runs-context-panels-v1
deferred_item_id: DFR-001
category: backlog
owner: nick
prd_ref: docs/project_plans/PRDs/features/runs-context-panels-v1.md
related_docs:
  - docs/dev/architecture/rf-run-export-schema.md
  - docs/project_plans/PRDs/features/runs-loopback-api-v1.md
  - docs/project_plans/design-specs/runs-context-panels.md
  - docs/project_plans/implementation_plans/features/runs-context-panels-v1.md
---

# Design Spec: Runs Viewer — Context Panels Lazy-Load (DFR-001)

> **Maturity: shaping** — the v1 embed approach is shipped and working. This
> spec captures the v2 lazy-load optimization as a well-understood option for
> when (or if) the trigger condition fires. No implementation has been scoped.

---

## Deferral Summary

| Field | Value |
|-------|-------|
| **Deferred from** | `runs-context-panels-v1` (OQ-1 resolution; see `decisions-block.md`) |
| **Deferred item** | `DFR-001` — lazy-load via loopback API |
| **Reason deferred** | OQ-1 resolved to Option A (embed in `run.json`). The static-export offline invariant (NFR-CP-1) made embedding the correct v1 choice: context is always available without `rf serve`, redaction is deterministic at export time, and the SPA requires no live backend. Lazy-load is additive overhead with no v1 benefit. |
| **Trigger condition** | `run.json` median size exceeds ~500 KB across the active run corpus, OR operator feedback explicitly requests live-refresh of context data (e.g., to reflect post-export changes to `research_brief.md` or `swarm_plan.yaml` without a full re-export). |
| **Target spec path** | `docs/project_plans/design-specs/runs-context-panels-lazy-load-v2.md` (this file) |

---

## Problem Statement (v2 context)

The v1 delivery embeds `context` in `run.json` at export time. This is correct
for offline use and keeps the read path deterministic, but carries two
trade-offs that may become relevant at scale:

1. **File size.** `research_brief_md` and `swarm_plan.yaml` can each be several
   hundred KB for research-heavy runs. At ~500 KB `run.json` median, the static
   export corpus becomes impractical to serve efficiently (slow load, large
   prebuild bundle).

2. **Staleness.** `run.json` is a snapshot. If `research_brief.md` is revised
   after export (e.g. to correct a brief), the viewer shows stale content until
   the operator runs `rf run export --json` again. For most runs this is
   acceptable; for actively-iterated runs it may be friction.

Neither trade-off justifies lazy-load in the v1 operator context. This spec
is authoritative when the trigger condition fires.

---

## Proposed v2 Approach: Hybrid Embed + Lazy-Load

The key insight is that lazy-load **must not break the offline invariant**. The
SPA is explicitly designed to work without `rf serve` running. Any v2 approach
must degrade gracefully to embedded context when the API is unreachable.

### Delivery Mechanism

**Primary path (online):** When `rf serve` is running and reachable at the
configured loopback URL, the SPA fetches context on demand via:

```
GET /api/runs/{run_id}/context
```

This endpoint returns the same `context` object shape as the `run.json`
top-level `context` key (schema 1.3 contract, §9 of `rf-run-export-schema.md`).
The response is sensitivity-gated at the same threshold as the static export.

**Fallback path (offline / API unreachable):** The SPA falls back to
`run.context` embedded in `run.json`. This means `run.json` must continue to
carry the `context` block — lazy-load is a *supplement*, not a replacement for
embed. The hybrid model is:

```
context = await loopbackGet(`/api/runs/${runId}/context`)
  .catch(() => run.context)  // fall back to embedded
```

The panel renders from whichever source resolves first. If neither is available
(`context` is null and the API is unreachable), panels show the existing
"Context not available for this run" empty-state — unchanged behavior.

### New Loopback Endpoint

A new route is added to the `rf serve` FastAPI router (see `runs-loopback-api-v1`):

```
GET /api/runs/{run_id}/context
```

**Response shape:** matches `run.json → context` exactly (same TypeScript
`RFRunContextSummary` type). Returns `null` (HTTP 200 with JSON `null`) when
the run has no context artifacts.

**Sensitivity gate:** applies the same `_context_summary()` + redaction pass
as the static export. The active threshold comes from `foundry.yaml →
viewer.sensitivity_threshold` or the `--sensitivity-threshold` flag passed to
`rf serve`.

**Error behavior:** returns HTTP 404 `{ "error": "run_not_found" }` when the
run ID does not resolve. Returns HTTP 200 `null` when the run exists but has
no context artifacts.

**No new auth surface:** the endpoint is gated by the same `Authorization:
Bearer` token as the existing `GET /api/runs/{run_id}` endpoint.

### Trigger: Size Threshold

The lazy-load path is activated per-run, not globally. The SPA checks the
embedded `context` size at page load:

- If `run.context` is present **and** estimated size < 200 KB (heuristic:
  `JSON.stringify(run.context).length`): use embedded, skip API call.
- If `run.context` is present **and** size ≥ 200 KB, OR `rf serve` is
  reachable regardless of size: prefer API fetch (fresher data); fall back to
  embedded if fetch fails.
- If `run.context` is null: attempt API fetch; show empty-state if unreachable.

The operator-level trigger (500 KB median `run.json`) is a signal to consider
*removing* the embed from `run.json` entirely and relying on the API path
exclusively for large runs. That is a further optimization beyond this spec.

### Offline Fallback Semantics

The hybrid approach preserves the offline invariant as follows:

| Scenario | Behavior |
|----------|----------|
| `rf serve` running, `context` embedded | SPA fetches live context from API (fresher); ignores embedded on success. |
| `rf serve` not running, `context` embedded | SPA falls back to embedded context. All four panels populate normally. |
| `rf serve` not running, `context` null | Panels show "Context not available for this run" empty-state. No error. |
| `rf serve` running, `context` null | SPA fetches from API; populates panels from live response. |
| API fetch times out (2 s timeout) | SPA falls back to embedded context (or empty-state if null). Panel render is never blocked. |

The 2-second timeout is the same heuristic used by the existing loopback mode
for `GET /api/runs` — fail fast and degrade, never block the UI.

### Frozen-Schema Implications

This v2 approach is **additive** to the schema 1.3 contract:

- `run.json` retains the `context` key (no schema break for offline consumers).
- The new `GET /api/runs/{run_id}/context` endpoint returns the identical shape.
- No schema version bump is required for the SPA-side hybrid behavior change;
  it is a delivery optimization, not a contract change.
- If a future v2 decides to *remove* `context` from `run.json` (to reduce file
  size), that is a schema 1.4 breaking change requiring backend-architect
  re-review and a frontend migration to API-only delivery.

---

## Scope (shaping stage)

When promoted to implementation, this spec would cover:

1. **New `GET /api/runs/{run_id}/context` loopback endpoint** in
   `src/research_foundry/api/router.py` (or equivalent).
2. **SPA hybrid client logic** — size heuristic check + API fetch + embedded
   fallback in `frontend/runs-viewer/src/hooks/useRunContext.ts` (new hook,
   or extension of the existing data-fetching layer).
3. **Panel component wiring** — panels consume the `useRunContext` hook output
   rather than `run.context` directly; the hook abstracts the embed/API choice.
4. **Timeout and error handling** — 2-second API timeout; error logged to
   console; fallback to embedded triggered silently.
5. **Tests** — unit test for the hybrid fallback logic; endpoint contract test
   for the new route; offline smoke test (panels load from embedded when API
   unreachable).

### Out of scope for this spec

- Removing `context` from `run.json` (schema 1.4 change — separate decision).
- Live polling / WebSocket updates to context panels during an active session.
- Invalidation or cache-busting strategies (v2 is best-effort fresh; not
  guaranteed consistent with simultaneous CLI writes).
- Per-field lazy-loading (e.g., fetch only `research_brief_md` when that panel
  is opened) — the endpoint returns the full `context` block for simplicity.

---

## Notes for Promotion

- Verify that `GET /api/runs/{run_id}` already returns the full `run.json`
  shape (including `context`). If it does, the new `/context` sub-route is
  merely a convenience endpoint that avoids transmitting the full claims graph
  just to get context. Confirm with the loopback API engineer before scoping.
- The size heuristic (200 KB / 500 KB) should be validated against real run
  corpus data before implementation. The numbers here are order-of-magnitude
  estimates from the P1 planning analysis.
- Consider whether `research_brief_md` alone drives most of the size pressure.
  If so, a simpler v2 might lazy-load only `research_brief_md` while keeping
  the other three fields embedded — avoiding the full hybrid complexity.
- The 2-second API timeout matches existing loopback behavior and is conservative.
  Profile panel expansion latency on a local `rf serve` instance before
  committing; a 500 ms timeout may be more appropriate for LAN use.
