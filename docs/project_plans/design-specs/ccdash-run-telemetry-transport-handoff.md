---
schema_version: 2
doc_type: report
report_category: handoff
title: "RF Transport Handoff Addendum — emit_ccdash_event → CCDash POST"
status: draft
created: 2026-07-20
updated: 2026-07-20
feature_slug: research-foundry-run-telemetry
target_repo: research-foundry
exploration_charter_ref: docs/project_plans/exploration/research-foundry-run-telemetry/research-foundry-run-telemetry-charter.md
related_documents:
- docs/project_plans/exploration/research-foundry-run-telemetry/research-foundry-run-telemetry-feasibility-brief.md
- docs/project_plans/exploration/research-foundry-run-telemetry/research-foundry-run-telemetry-proposed-adr.md
---

# RF Transport Handoff Addendum

**For the `research-foundry` repo.** CCDash is building a receiving contract
(`POST /api/v1/ingest/rf-events`). This addendum specifies the one small, additive RF-side change
that wires the already-shipped `ccdash_event` to actually reach CCDash. ~2–3 pts.

## Change

At the end of `emit_ccdash_event()`
(`src/research_foundry/services/telemetry.py:254-258`, immediately after the local YAML mirror is
written), add a **best-effort HTTP POST** of the same event dict to CCDash's ingest endpoint. Model
it on the existing `push_status()` pattern (`telemetry.py:510-561`): never raise, return a bool.
**Keep the local YAML writeback exactly as-is** — it remains RF's durable source-of-truth and replay
log; the POST is a secondary, best-effort emit.

## Endpoint & auth

- **Target**: `POST {CCDASH_BASE_URL}/api/v1/ingest/rf-events`, `Content-Type: application/json`
  (single event) or NDJSON (batch). CCDash accepts RF's event near-verbatim
  (`ccdash_event.schema.yaml` is `additionalProperties: true`; no field-stripping needed).
- **Auth**: `Authorization: Bearer {CCDASH_INGEST_TOKEN}` — a CCDash workspace-scoped token
  (ADR-008 pattern), owner-provisioned once, mirrored into RF's config alongside the base URL.
- **Config-gated**: emit only when both `CCDASH_BASE_URL` and `CCDASH_INGEST_TOKEN` are set
  (unset ⇒ skip the POST silently, YAML mirror unaffected). LAN-local when RF (`:7432`) and CCDash
  share the node.

## Field mapping (`execution_event` → `rf_events`)

CCDash stores the event flat; RF ids are display-only strings on the CCDash side (never join keys).

| RF `ccdash_event` field | CCDash `rf_events` column | Notes |
|---|---|---|
| `event_id` | `event_id` (dedup key) | idempotency key for `(workspace_id, event_id)` dedup |
| `run_id` (§11.2 `search_run.run_id`) | `run_id` | **emit a UUID4 if available** — the only field with a shot at correlation; else CCDash mints one |
| `intent_id` | `intent_id` (string attr) | opaque display attribute |
| `task_node_id` | `task_node_id` (string attr) | opaque display attribute |
| `occurred_at` / run timestamp | `occurred_at` | ISO-8601 |
| `search_mode` | `search_mode` | per-mode is the honest analytics grain |
| `selected_providers: [...]` | `providers_json` | provider **list** (no per-provider split available) |
| `estimated_cost_usd` | `estimated_cost_usd` | run-level aggregate |
| `useful_source_rate` / `duplicate_rate` / `extraction_failure_rate` | matching columns | run-level aggregates |
| `latency_ms` | `latency_ms` | |
| everything else | `payload_json` | full event retained verbatim for forward-compat |

## Failure behavior

- Fail-open: any POST error (timeout, non-2xx, unreachable) is caught, logged at warn, POST returns
  `False` — the run **never blocks or fails** because of CCDash. YAML mirror is already durable, so
  CCDash can replay from it later if needed.
- No retry loop in the hot path; a dropped POST is acceptable (CCDash treats absence as a contract
  state, and the FS mirror is the backstop). Optional: mint `writebacks.ccdash_posted: bool` for
  observability.

## FS-watch fallback note

If RF cannot take this change, CCDash's fallback is a filesystem-watch adapter over RF's
`ccdash/events/` tree — **that path needs no RF change at all**. The HTTP POST is preferred
(cleaner boundary, auth, no shared-host assumption), but RF is not blocked either way.
