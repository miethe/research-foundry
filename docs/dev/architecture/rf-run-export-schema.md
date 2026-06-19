---
title: "RF Run Export Schema (run.json)"
description: "Frozen denormalized claim-graph contract emitted by `rf run export --json`; the sole data source for the read-only runs viewer."
status: frozen
schema_version: "1.1"
doc_type: architecture
created: 2026-06-19
updated: 2026-06-19
feature_slug: runs-frontend
phase: 1
owners: ["python-backend-engineer", "backend-architect"]
resolves: ["OQ-1", "OQ-2", "OQ-3"]
source_of_truth: src/research_foundry/services/export_service.py
reviewed_by: backend-architect
review_verdict: approved
review_date: 2026-06-19
---

# RF Run Export Schema (`run.json`)

> **Frozen contract.** This is the P1 exit gate. Every Phase-2+ TypeScript type
> and React Query hook binds to this shape. Changes after freeze require a
> schema-version bump and `backend-architect` re-review.

## 1. Purpose & Invariants (OQ-1 resolution)

`rf run export --json` emits a **single denormalized JSON document per run** —
the frontend's only data source. The shape is a **denormalized claim graph**:
each claim carries its *resolved* sources (title, URL, trust, usage, evidence
quote), so the UI never re-joins the graph at render time.

**Decision (OQ-1):** the export is a denormalized claim graph, **not** a flat
artifact map. Rationale: re-joining `claim -> source_card -> evidence` in the
browser would be slow, error-prone, and would place join logic on the recall
path. The join happens once, deterministically, in Python.

Load-bearing invariants:

| Invariant | Enforcement |
|-----------|-------------|
| **No LLM on the recall path** | `export_service` is pure file-walk + dict assembly; zero model calls. |
| **Path re-derivation** | All reads go through `FoundryPaths`/`RunPaths`. Stored absolute paths (`run_index.yaml.run_dir`, `verification.yaml.report_path`/`claim_ledger_path`) are **never** used for I/O. |
| **Sensitivity redaction at export** | Quotes/summaries above the viewer threshold are dropped before serialization (R9). Components cannot leak what never reaches the JSON. |
| **Derived status** | `status_derived` is computed from artifacts + verification, never the (stale) `run.yaml.status`. |
| **Determinism** | Same inputs -> byte-identical JSON (insertion-ordered, atomic temp->move write). |

## 2. Top-Level Object

```jsonc
{
  "schema_version": "1.1",            // export contract version (this doc)
  "run_id": "rf_run_20260613_...",    // canonical id
  "intent_id": "intent_research_...", // nullable
  "created_at": "2026-06-13T22:46:23-04:00", // from run.yaml, nullable
  "status_derived": "published",      // see §3 — computed, authoritative
  "status_raw": "planned",            // run.yaml.status verbatim (may be stale)
  "sensitivity": "personal",          // run-level (run.yaml | bundle.governance)
  "sensitivity_threshold": "public",  // active viewer threshold (§4)
  "claim_counts": { "total": 91, "supported": 69, "inference": 20, ... },
  "verification": { ... },            // see §5
  "governance": { ... },              // evidence_bundle.governance verbatim
  "timeline": [ { ... } ],            // telemetry/run_trace.jsonl events
  "claims": [ { ... } ],              // see §6 — the denormalized graph
  "artifact_schema_versions": {       // OQ-7: per-artifact schema_version pins
    "run": "0.1", "evidence_bundle": "0.1", "claim_ledger": "0.1"
  },
  "report_draft": "# Report\n\n..."   // see §8 — verbatim markdown, null if absent
}
```

Only `schema_version`, `run_id`, `status_derived`, `claims` are guaranteed
non-null. All others (including `report_draft`) may be `null`/empty when the
underlying artifact is absent (per-artifact graceful degradation; consumers use
optional access).

## 3. Derived Status Enum (OQ-2 resolution)

`status_derived` is the **highest rung reached**, computed from on-disk
artifacts — **not** `run.yaml.status` (which is frequently stale; the reference
run carries `planned` while it is fully verified and written back).

| Rung | Promotion condition |
|------|---------------------|
| `planned` | default (run exists) |
| `sources_ingested` | `sources/*.md` present |
| `extracted` | `extractions/*.yaml`\|`*.md` present |
| `claim_mapped` | `claims/claim_ledger.yaml` has a non-empty `claims[]` |
| `synthesized` | `reports/report_draft.md` or `report_final.md` present |
| `verified` | `reviews/verification.yaml` `passed: true` |
| `published` | `verified` **and** (`evidence_bundle.governance.approved_for_writeback` **or** any `writebacks/*`) |

Computation is monotonic: a higher rung's condition overwrites a lower one, so a
run with `run.yaml.status: planned` + `verification.passed: true` resolves to
`verified` (or `published`).

## 4. Sensitivity Model (OQ-3 resolution)

Ordering (least -> most sensitive):

```
public (0) < personal (1) < work_sensitive (2) < client_sensitive (3)
```

- **Threshold source:** explicit `--sensitivity-threshold` override >
  `foundry.yaml` `viewer.sensitivity_threshold` > **default `public`**.
- **Effective sensitivity** of an evidence point = `max(card.sensitivity,
  extracted_point.sensitivity)`.
- A point's `quote` **and** `summary` are replaced with `"[redacted:sensitivity]"`
  when effective rank **>** threshold rank. The claim and its source linkage
  remain; only the governed text is dropped.
- **Absent** sensitivity -> treated as `public` (safe to render).
- **Unrecognized** sensitivity label -> treated as stricter than any known
  threshold (fail-closed; never leaks).

This is the **R9 gate**: governed content never enters `run.json`, so no
frontend component can surface it.

## 5. `verification` Block

```jsonc
{
  "present": true,
  "passed": true,
  "exit_code": 0,
  "checks": [
    { "id": "all_claim_ids_exist", "severity": "error",
      "status": "pass", "detail": "...", "locations": [] }
  ]
}
```

When `reviews/verification.yaml` is absent: `{ "present": false, "passed": null,
"exit_code": null, "checks": [] }`.

## 6. `claims[]` — the Denormalized Graph

```jsonc
{
  "claim_id": "clm_043",
  "text": "The latest released version of claude-agent-sdk is 0.2.101 ...",
  "materiality": "core",            // core | background | ...
  "claim_type": "factual",          // factual | inference | speculation
  "status": "supported",            // supported | mixed | contradicted |
                                    //   inference | speculation | unsupported
  "confidence": "medium",
  "report_locations": [],
  "inference_basis": {
    "from_claims": ["clm_001"],     // [] for factual claims
    "reasoning_summary": "..."      // nullable
  },
  "sources": [ /* §6.1 */ ]
}
```

### 6.1 Resolved `sources[]` entry

Each entry joins a claim's `source_card_id` + `evidence_id` to the source-card
YAML and the matching `extracted_points[]` quote:

```jsonc
{
  "source_card_id": "src_20260613_rib008_08",
  "evidence_id": "ev_001",
  "relation": "supports",
  "locator": "Available hooks (hook events table)", // ledger-cited locator
  "resolved": true,                 // false if the card/evidence is missing
  "dangling": false,                // true when the reference does not resolve
  "title": "claude-agent-sdk - PyPI",
  "source_type": "repo",
  "url": "https://pypi.org/project/claude-agent-sdk/",
  "trust": { "source_rank": "primary", ... },     // card trust block
  "usage": { "allowed_for_public_output": false, ... },
  "sensitivity": "personal",        // card-level label
  "evidence_locator": "Page header (release banner)",
  "summary": "...",                 // or "[redacted:sensitivity]"
  "quote": "claude-agent-sdk 0.2.101 ..."          // or "[redacted:sensitivity]"
}
```

A **dangling** reference (source card or evidence id not found) is surfaced
honestly with `resolved: false, dangling: true` and null content — never
silently dropped, so the UI can flag empty-basis / broken-provenance cases
(e.g. the RIB-018 inference-without-basis class).

## 7. CLI Surface

| Command | Behavior |
|---------|----------|
| `rf run export --json --run-id RUN_ID` | Writes `<run_dir>/run.json` (atomic). |
| `rf run export --json --run-id RUN_ID --stdout` | Emits JSON to stdout. |
| `rf run export --json --all` | Exports every discovered run to its own `run.json`. |
| `rf run export --sensitivity-threshold LEVEL ...` | Overrides the viewer threshold. |
| `rf run list --json` | JSON array of run summaries with `status_derived`. |

**Discovery:** recursive `runs/**/run.yaml` to depth <= 3 (catches the nested
`runs/runs/<id>/` anomaly). **Errors:** a malformed artifact exits non-zero with
a structured stderr JSON line `{ "error", "run_id", "artifact_path" }`.

## 8. `report_draft` — Verbatim Report Markdown

`report_draft` carries the verbatim Markdown of the run's synthesized report so
the frontend can render the full narrative and wire `[claim:clm_NNN]` chip
interactions without a second round-trip.

```
"report_draft": "# Report\n\nThe latest released version … [claim:clm_043] …"
```

- **Source:** `reports/report_draft.md`, falling back to `reports/report_final.md`
  (both paths derived via `RunPaths`; no stored absolute path is used).
- **Value is `null`** when neither report file exists (graceful degradation; the
  frontend's "read report" affordance is gated on `report_draft !== null`).
- **No sensitivity redaction** is applied to the report body — it contains claim
  IDs (`[claim:clm_NNN]`) that reference governed evidence, not raw quotes. The
  R9 gate operates at the `claims[].sources[].quote/summary` level.
  - **Scoping note (R9 boundary):** this relies on the convention that report
    prose cites governed evidence via `[claim:clm_NNN]` chip references rather
    than inlining raw quotes verbatim. If a report author breaks this convention,
    the prose would carry uncensored text. Enforcement of this convention is out
    of scope for the export layer; it belongs to the report-authoring workflow.
- **No LLM transformation** — the file is read verbatim; no truncation, no
  per-sentence processing.

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-19 | Initial frozen contract (Phase 1 exit gate). |
| 1.1 | 2026-06-19 | **Additive post-freeze change** — added `report_draft: string \| null` top-level field to unblock the "read report → click claim chip → see quote" frontend journey. Requires `backend-architect` re-review (`review_verdict: pending-rereview`). |
