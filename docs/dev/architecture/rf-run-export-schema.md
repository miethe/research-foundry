---
title: "RF Run Export Schema (run.json)"
description: "Frozen denormalized claim-graph contract emitted by `rf run export --json`; the sole data source for the read-only runs viewer."
status: stable
schema_version: "1.4"
doc_type: architecture
created: 2026-06-19
updated: 2026-07-05
feature_slug: runs-context-panels-v1
phase: "8"
owners: ["python-backend-engineer", "backend-architect", "documentation-writer"]
resolves: ["OQ-1", "OQ-2", "OQ-3"]
source_of_truth: src/research_foundry/services/export_service.py
reviewed_by: backend-architect
review_verdict: approved
review_date: 2026-06-21
changelog_ref: "CHANGELOG.md → [Unreleased] Added → Run Metadata Enrichment"
---

# RF Run Export Schema (`run.json`)

> **Stable contract (v1.4).** This schema is bound to schema-version strings
> in `run.json` documents. Every TypeScript type and React Query hook binds to
> this shape. Changes require a schema-version bump and `backend-architect`
> re-review. See [Changelog](#changelog) for version history and migration notes.

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
  "schema_version": "1.4",            // export contract version (this doc)
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
  "report_draft": "# Report\n\n...",  // see §8 — verbatim markdown, null if absent
  "report_anchors": [ { ... } ],      // see §16 — v1.4 AST-derived block/claim anchors, null if absent
  "context": { ... },                 // see §9 — v2 optional context stack, null if absent
  "writebacks": { ... },              // see §10 — v2 optional writeback summary, null if absent

  // ── Run Metadata Enrichment (v1.2 — schema 1.2) ────────────────────────────
  // All fields below are optional/nullable — absent on pre-migration runs (v1.0/1.1).
  // Populated in P2 (backfill migration) and P3 (creation path). Consumers use optional access (?.).
  
  "linked_projects": ["research-foundry"],  // null on pre-migration runs
  "category": "AI Engineering",             // null on pre-migration runs
  "tags": ["agent-design", "research"],     // null on pre-migration runs
  "backlog_idea_ref": "RIB-042",            // null when not from backlog
  "backlog_idea_id": "agentic_research",    // null when backlog_idea_ref is null

  // ── Enrichment Extras (v1.2 — schema 1.2, P7) ─────────────────────────────
  // Sourced from run.yaml.profile, source cards, and claim aggregation.
  // All null/absent on pre-enrichment runs. Consumers use optional access (?.).

  "cost_usd": 2.47,                         // null when no profile present
  "model_profiles": {                       // null when no profile present
    "max_cost_usd": 5.0,
    "extraction_model_profile": "rf_extract_cheap",
    "synthesis_model_profile": "rf_synthesize_deep",
    "verification_model_profile": "rf_verify_standard",
    "max_runtime_minutes": 120,
    "freshness_days": 90
  },
  "source_count_by_type": {                 // null when no source cards present
    "official_doc": 3,
    "paper": 1,
    "repo": 2,
    "blog": 1
  }
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

## 9. `context` — Run Context Block (v1.3)

Optional context block introduced in schema 1.2; shape finalized and fully
populated in schema 1.3. Absent (null) in schema 1.0/1.1 exports and on any
run where no source artifact (`routing_decision.yaml`, `research_brief.md`,
`swarm_plan.yaml`) is present.

When non-null (schema ≥ 1.3), the block always contains all four keys. Each
key is `null` when its backing artifact is absent; the block structure is never
key-omitted:

```jsonc
{
  "routing_decision": {
    "decision": "Use sonnet for synthesis",   // selected_abstraction_level
    "rationale": "Fast iteration needed for research scope",
    // additional allowlisted fields from routing_decision.yaml
  },
  "swarm_plan": {
    "swarm": "rf_research_standard",          // swarm id
    "agents": ["sonnet-extractor", "sonnet-synthesizer"],
    "adapters": ["claim-mapper", "report-critic"],
    // additional allowlisted fields from swarm_plan.yaml
  },
  "research_brief_md": "---\ntitle: ...\n---\n\n# Research Brief\n...", // verbatim research_brief.md
  "upstream_entities": {
    "intent_id": "intent_research_agentic_design",   // from run.yaml (already top-level)
    "ibom_id": "ibom_core_research_skills",          // from run.yaml; null when absent
    "intenttree_node_id": "node_rf_agentic_research" // from routing_decision.yaml active_node_id;
                                                     // falls back to evidence_bundle.yaml governance;
                                                     // null when both absent
  }
}
```

### Field contracts

| Field | Type | Source artifact | Nullable |
|---|---|---|---|
| `routing_decision` | object \| null | `routing_decision.yaml` (allowlist-filtered) | Yes — null when file absent |
| `swarm_plan` | object \| null | `swarm_plan.yaml` (allowlist-filtered) | Yes — null when file absent |
| `research_brief_md` | string \| null | `research_brief.md` read verbatim (including any YAML frontmatter) | Yes — null when file absent |
| `upstream_entities` | object \| null | `run.yaml` (`intent_id`, `ibom_id`) + `routing_decision.yaml` (`active_node_id` → `intenttree_node_id`) | Yes — null when all three IDs are absent |

**`upstream_entities` sub-field sources:**

| Sub-field | Source | Fallback |
|---|---|---|
| `intent_id` | `run.yaml` top-level (already emitted as top-level `run.json` field) | `null` |
| `ibom_id` | `run.yaml` top-level `ibom_id` key | `null` |
| `intenttree_node_id` | `routing_decision.yaml → active_node_id`; also in `evidence_bundle.yaml → governance.intenttree_node_id` | `null` (both absent) |

**Null semantics:**

- **All fields nullable:** each context element is `null` when its source artifact is absent or unreadable.
- **Shape always complete (schema ≥ 1.3):** when `context` is non-null, all four keys are present.
- **`context` itself is null** when none of the file-based source artifacts (`routing_decision.yaml`, `research_brief.md`, `swarm_plan.yaml`) is present. Upstream entity IDs in `run.yaml` alone do not cause `context` to be emitted.
- **Graceful degradation:** frontend uses optional access (`context?.routing_decision`, `context?.research_brief_md`) throughout; hard destructuring of `context` is forbidden per NFR-CP-4.

### Sensitivity redaction of `context.*`

The R9 sensitivity gate (§4) is extended to cover `context.*` fields. Redaction
uses the same `_sensitivity_rank` / `REDACTION_MARKER` / `resolve_threshold`
model as `claims[].sources[].quote` — no separate mechanism.

**Field-level redaction behavior:**

| Field | Redaction rule |
|---|---|
| `routing_decision` | String values within the allowlisted dict are scanned; values tagged `sensitivity > threshold` are replaced with `"[redacted:sensitivity]"`. |
| `swarm_plan` | Same as `routing_decision` — string values in the allowlisted dict are scanned per field sensitivity. |
| `research_brief_md` | The entire string is replaced with `"[redacted:sensitivity]"` when the brief's YAML frontmatter `sensitivity:` key exceeds the active threshold. |
| `upstream_entities` | Entity IDs are opaque keys, not governed text — **not redacted**. |

**Default threshold behavior:** The production default in `foundry.yaml` is
`viewer.sensitivity_threshold: client_sensitive` (rank 3). At this threshold,
`work_sensitive` content (rank 2) passes through **unredacted** — this is
deliberate operator configuration, not a gap. To suppress `work_sensitive`
context content, set `viewer.sensitivity_threshold: work_sensitive` or use
`rf run export --sensitivity-threshold work_sensitive`.

## 10. `writebacks` — Optional v2 Writeback Summary

Optional writeback target summary when the run has been published or targeted for
publication. Absent in schema 1.0/1.1 exports. When present, contains:

```jsonc
{
  "targets": [
    {
      "name": "MeatyWiki",
      "destination": "concepts/research-foundry",
      "status": "published",
      "url": "https://meatywiki.local/concepts/research-foundry",
      ...                             // additional target fields
    },
    {
      "name": "SkillMeat",
      "destination": "skillboms/claim-verification",
      "status": "pending_review",
      "url": null,
      ...
    }
  ],
  "approved_for_writeback": true,
  "reviewer_notes": "Approved for all targets",
  "required_fix": null,
  "previews": [ ... ]                 // optional preview artifacts
}
```

- **Targets array:** each target carries name, destination, status, and URL.
- **Nullable fields:** `targets`, `reviewer_notes`, `required_fix`, `previews` may be `null`.
- **Graceful degradation:** frontend gates writeback affordances on `writebacks?.targets?.length > 0`.

## 11. Run Metadata Enrichment Fields (v1.2 — New in schema 1.2)

Schema 1.2 adds five run-metadata fields, derived from the research backlog. All are optional/nullable
for backwards compatibility with pre-migration runs (schema 1.0/1.1). Consumers MUST use optional access
(`run?.linked_projects`, etc.) throughout.

### 11.1 `linked_projects` — Array of Project Slugs

```json
"linked_projects": ["research-foundry", "skillmeat"]
```

**Type:** `string[] | null`

**Source:** Derived from backlog `idea.suggested_project[]` at run creation (P3) or via backfill
migration (P2). When a run is created from `--backlog-idea-ref RIB-NNN`, the corresponding idea's
`suggested_project` field(s) populate this array.

**Nullable:** `null` on pre-migration runs (schema < 1.2).

**Semantics:** Indicates which projects/epics this run's findings should be linked to or published
within. Used for portfolio filtering (section §13.2) and downstream integration with project
management systems.

**Frontend usage:** Display as project badges on RunCard, filter portfolio by selected projects,
include in RunDetail header breadcrumb.

### 11.2 `category` — Research Pillar / Category String

```json
"category": "AI Engineering"
```

**Type:** `string | null`

**Source:** Derived from backlog `idea.pillar` at run creation (P3) or via backfill migration (P2).
Represents the research domain or knowledge pillar.

**Nullable:** `null` on pre-migration runs.

**Examples:** "AI Engineering", "Frontend Tooling", "Database Systems", "Security", "DevOps",
"Research Infrastructure".

**Frontend usage:** Display as category chip in RunCard and RunDetail, filter portfolio by
selected categories, use for visual grouping in Lineage view.

### 11.3 `tags` — Array of Topic Tags

```json
"tags": ["agent-design", "research-methodology", "agentic-os"]
```

**Type:** `string[] | null`

**Source:** Derived from backlog `idea.tags[]` at run creation (P3) or via backfill migration (P2).
User-defined topic tags for run classification and discovery.

**Nullable:** `null` on pre-migration runs.

**Frontend usage:** Display as tag chips in RunCard, RunDetail Overview, and claim ledger (tags
reference linked claims), filter portfolio by selected tags, enable tag-based discovery workflows.

### 11.4 `backlog_idea_ref` — Backlog Idea ID

```json
"backlog_idea_ref": "RIB-042"
```

**Type:** `string | null` (pattern: `^RIB-\d+$`)

**Source:** The backlog idea ID in RIB-NNN format when the run was created from a research idea
backlog entry. Null when the run was created outside the backlog (manual capture, imported, etc.).

**Nullable:** `null` when the run is not linked to a backlog idea.

**Semantics:** Provides a human-friendly reference to the idea that triggered the run. Used for
traceability back to the idea in `research_idea_backlog.yaml`.

**Frontend usage:** Display as a breadcrumb link in RunDetail header, enable jump-to-idea
navigation, use for backlog↔run linkage visualization.

### 11.5 `backlog_idea_id` — Backlog Idea Slug

```json
"backlog_idea_id": "agentic_research"
```

**Type:** `string | null`

**Source:** Reverse slug of the backlog idea (matches `idea.id` field in the backlog YAML). Null
when `backlog_idea_ref` is null.

**Nullable:** `null` when the run is not linked to a backlog idea.

**Semantics:** Stable machine-friendly reference (slug) for the backlog idea. Enables consistent
cross-referencing even if the RIB-NNN numbering changes due to backlog reordering.

**Frontend usage:** Use as a stable key for idea↔run linking, enable URL routes like
`/backlog/{idea_id}/run/{run_id}`.

### 11.6 Backfill Migration for Pre-Migration Runs

Pre-migration runs (created before P2/P3 implementation) carry `null` values for all five fields
above. The backfill migration (P2 task `MIG-001`/`MIG-002`) idempotently populates these fields
by inverting the backlog's `idea.links.run_id` → `run_metadata` map:

1. **Inversion:** For each backlog idea with `links.run_id: [list of run_ids]`, the migration
   creates a backward map: `run_id → {linked_projects, category, tags, backlog_idea_ref, backlog_idea_id}`.
2. **Idempotency:** Re-running the migration on an already-populated run.yaml produces no diff
   (safe to re-run on updated backlog).
3. **Dry-run:** `--dry-run` flag produces a diff without writing (for review before commit).
4. **Merge logic:** When multiple backlog ideas link to the same run, the migration unions
   `tags` and collects all `linked_projects` (later ideas override category if conflict).

**Runtime command:**
```bash
scripts/backfill_run_metadata.py --dry-run  # Preview changes
scripts/backfill_run_metadata.py --commit   # Write changes to run.yaml files
```

## 12. Enrichment Extras (v1.2 — New in schema 1.2, Phase 7)

Schema 1.2 also adds three enrichment-extras fields, sourced from run profiles and aggregated
from source cards. All are optional/nullable for backwards compatibility. These fields unlock
downstream tabs (Swarm, Policies, Library) in future phases.

### 12.1 `cost_usd` — Actual or Budgeted Run Cost

```json
"cost_usd": 2.47
```

**Type:** `number | null`

**Source:** Sourced from `run.yaml → profile → max_cost_usd` (the budgeted cost for the run).

**Nullable:** `null` when no profile block is present (pre-enrichment runs).

**Semantics:** The actual or maximum budgeted cost of running this research in USD. Used to
track research expenditure and implement cost-aware filtering/sorting.

**Frontend usage:** Display in RunCard cost badge, RunDetail enrichment widget (formatted as
`$2.47`), sort/filter portfolio by cost range, aggregate costs in run dashboards.

### 12.2 `model_profiles` — Resource Allocation Profile

```jsonc
{
  "max_cost_usd": 5.0,
  "extraction_model_profile": "rf_extract_cheap",
  "synthesis_model_profile": "rf_synthesize_deep",
  "verification_model_profile": "rf_verify_standard",
  "max_runtime_minutes": 120,
  "freshness_days": 90
}
```

**Type:** `object | null` (object has optional properties; see structure above)

**Source:** Sourced from `run.yaml → profile` (the complete resource allocation config).

**Nullable:** `null` when no profile block is present.

**Fields:**
- `max_cost_usd`: Maximum allowed spend (matched with actual `cost_usd`).
- `extraction_model_profile`: Named extraction profile (e.g., `rf_extract_cheap`, `rf_extract_deep`).
- `synthesis_model_profile`: Named synthesis profile (e.g., `rf_synthesize_deep`).
- `verification_model_profile`: Named verification profile (e.g., `rf_verify_standard`).
- `max_runtime_minutes`: Maximum wall-clock runtime budget.
- `freshness_days`: Maximum acceptable age of sources (freshness constraint).

**Semantics:** Fully describes the resource tier and model routing for the run. Useful for
understanding why certain models were selected and for comparing research cost/quality
trade-offs across runs.

**Frontend usage:** Display in RunDetail enrichment widget as a compact table, use profile
names for sorting/filtering, show freshness constraint in run details.

### 12.3 `source_count_by_type` — Source Card Aggregation

```jsonc
{
  "official_doc": 3,
  "paper": 1,
  "repo": 2,
  "blog": 1,
  "other": 2
}
```

**Type:** `Record<string, number> | null` (keys are source type names from RFSourceType enum)

**Source:** Aggregated from all source cards in the run's `sources/*.md` files by reading each
card's `source_type` field.

**Nullable:** `null` when no source cards are present.

**Valid keys:** `official_doc`, `paper`, `standard`, `repo`, `news`, `blog`, `book`,
`personal_note`, `internal_doc`, `other`.

**Semantics:** Provides a quick summary of source diversity and coverage without loading the
full claim graph. Used to assess evidence quality and identify gaps in source type coverage.

**Frontend usage:** Display as a mini bar chart or key-value table in RunDetail enrichment
widget, use for sorting/filtering portfolio by source diversity, show in run summary cards.

### 12.4 Distribution Aggregates (From `claim_counts`)

The following distribution aggregates are already captured in `claim_counts` (not new in 1.2):

- **Confidence distribution:** `claim_counts.low`, `claim_counts.medium`, `claim_counts.high`
- **Materiality distribution:** `claim_counts.core`, `claim_counts.background`, `claim_counts.style`
- **Status distribution:** `claim_counts.supported`, `claim_counts.mixed`, `claim_counts.contradicted`,
  `claim_counts.inference`, `claim_counts.speculation`, `claim_counts.unsupported`

The frontend Enrichment widget renders these as progress bars / distribution charts in the
RunDetail Overview.

## 13. Frontend Display and Filtering

### 13.1 Display Surfaces (Run Metadata Fields)

Schema 1.2 adds visual display of run metadata across multiple surfaces:

| Surface | Fields displayed | Component |
|---------|------------------|-----------|
| **RunList table** | `linked_projects` (primary) | RunList.tsx columns |
| **RunCard** | `linked_projects` (badges), `tags` (chips), `category` (hint) | RunCard.tsx |
| **RunCard hover** | `backlog_idea_ref` (reference link) | RunCard tooltip |
| **RunDetail Overview** | All metadata fields + enrichment widget section | RunDetailWorkspace.tsx |
| **RunDetailModal header** | `linked_projects`, `tags` reference chips | RunDetailModal.tsx |
| **ClaimLedger inspector** | `tags` reference chips | ClaimAuditWorkbench.tsx |
| **LineageGraph panel** | `tags` reference chips in header | LineageDetailPanel.tsx |

### 13.2 Filtering / Faceting (Portfolio Level)

Portfolio filtering is implemented in `FilterTabs.tsx` and `RunList.tsx`:

**Filter controls:**
- **Project filter:** Checkbox list derived from all unique `linked_projects[]` across runs.
- **Category filter:** Checkbox list derived from all unique `category` values.
- **Tags filter:** Checkbox list derived from all unique `tags[]` values.

**Filter logic (AND semantics):**
```
run passes if:
  (run.linked_projects intersects activeProjects OR activeProjects empty) AND
  (run.category in activeCategories OR activeCategories empty) AND
  (run.tags intersects activeTags OR activeTags empty)
```

**Null handling:** Runs with `null` metadata fields are correctly excluded when the corresponding
filter is active (they have no matching values). A run with `tags: null` will not appear in results
if "Tags: researcher" filter is active.

**Empty state:** When all runs are filtered out, show "No runs match the selected filters" with a
[Clear filters] button.

## 14. Backwards Compatibility Notes

Schema 1.4 is **fully backwards compatible** with all prior schema versions (1.0-1.3):

- All fields introduced in 1.2, 1.3, and 1.4 are **optional/nullable**.
- Pre-migration runs (v1.0/1.1) carry `null` values or omit these fields entirely.
- Frontend components use **optional access** (`run?.linked_projects`, `run?.context`,
  `run?.report_anchors`, etc.) and gracefully degrade when fields are absent.
- Static data rebuild (`rf run export --all`) automatically includes 1.4 fields for all runs;
  context and report_anchors are populated when the source artifacts are present on disk.

**Version detection:** Always check `schema_version` to determine which fields are available:
- Schema `1.0`: no metadata, no enrichment, no context, no writebacks.
- Schema `1.1`: adds `report_draft`.
- Schema `1.2`: adds run metadata (5 fields), enrichment extras (3 fields), `context` stub (routing_decision + swarm_plan only), and writebacks.
- Schema `1.3`: `context` fully populated — adds `research_brief_md` and `upstream_entities`; redaction extended to `context.*`.
- Schema `1.4`: adds `report_anchors` (§16) — AST-derived report block/paragraph anchors + claim spans. Absent (key omitted) on schema < 1.4; the frontend falls back to legacy client-side regex chip parsing in that case.

**Migration note (for developers):** When upgrading from v1.0/v1.1 exports to 1.3:
1. Runs with metadata/enrichment fields will appear after backfill (P2) + re-export.
2. Pre-migration runs remain queryable with `schema_version < "1.2"`.
3. Frontend can show "[Metadata pending backfill]" or "[Pre-enrichment run]" labels for old runs.
4. Context panels in the viewer display empty-states for runs where `context` is null (pre-1.3 exports or runs with no source artifacts).

## 15. CLI Surface Changes (v1.2-v1.4)

The export command remains stable; all v1.2-v1.4 fields are included in `--json` output:

```bash
# Export with all fields (schema 1.4)
rf run export --json --run-id rf_run_20260613_...

# Export all (includes backfill metadata and context where artifacts are present)
rf run export --json --all

# Export with a specific sensitivity threshold (controls context.* redaction)
rf run export --json --run-id rf_run_20260613_... --sensitivity-threshold work_sensitive

# List all runs with metadata stubs in RFRunSummary
rf run list --json
```

Schema version is automatically set to `"1.4"` in all exports produced by the current
`export_service.py`. Pre-migration `run.json` files generated by earlier versions retain their
original `schema_version` value until re-exported.

## 16. `report_anchors` — Report Anchor Model (v1.4 — New in schema 1.4)

Added for the Granular Report Audit feature (public multi-user release, Phase 2 Wave A;
design decisions D7/D8). Backend owns anchor derivation — the frontend **consumes**
`report_anchors`, it never re-derives it from markdown at render time.

```jsonc
"report_anchors": [
  {
    "block_id": "0f1a2b3c4d5e",          // sha1(section_id + normalized_text + ordinal)[:12]
    "section_id": "findings",             // nearest preceding h2/h3 slug; null before first heading
    "paragraph_ordinal": 2,               // 0-based index of this paragraph within its section
    "text_hash": "9a8b7c6d5e4f",          // sha1(normalized_text)[:12] — drift-detection hash
    "claim_links": [
      {
        "claim_id": "clm_043",
        "span_start": 42,                 // offset into the *normalized* block text
        "span_end": 55,
        "relation": "supports",           // supports | contradicts | inferred_from | context | null
        "link_status": "linked"           // linked | stale | missing_claim
      }
    ]
  }
]
```

- **Source:** parsed from `report_draft` (§8) via `markdown-it-py` (CommonMark AST) — never
  regex over rendered output, per spec §7 ("Avoid regex-only report rewriting for anything
  that affects persisted anchors").
- **Null when `report_draft` is null.** Absent entirely (key omitted) on pre-1.4 exports; the
  frontend treats a missing/null `report_anchors` as *legacy mode* and falls back to today's
  client-side regex chip parsing (D8) — `"legacy"` is a frontend-only fallback concept and is
  never a value the backend writes into `link_status`.
- **Scope (v1.4):** only **top-level paragraphs** are anchored — paragraphs nested inside a
  list item or blockquote are not yet anchored. Report prose from the synthesis service is
  flat headings+paragraphs today, so this covers the material case; list/blockquote paragraph
  anchoring is a documented gap for a later wave.
- **`section_id`** is computed with the *exact* same slugify + duplicate-suffix algorithm as
  `frontend/runs-viewer/src/components/ReportOverlay/reportOutlineUtils.ts::slugify` /
  `extractHeadings` (lowercase, strip non-word/space/hyphen chars, collapse hyphens, `-2`/`-3`
  suffix on repeated headings), so it matches the heading `id` the viewer already renders —
  only h2/h3 headings count as section boundaries (h1 is the run title; h4+ do not reset the
  counter), matching the existing outline behavior exactly.
- **`text_hash`** is computed over `" ".join(raw.split())` — whitespace-collapsed, trimmed
  paragraph source text (the same normalization `span_start`/`span_end` are measured against).
- **`claim_links[].relation`** is inferred from the *linked claim's* `status` at export time
  (a bare `[claim:...]` tag carries no relation of its own): `supported`/`mixed` → `supports`,
  `contradicted` → `contradicts`, `inference`/`speculation` → `inferred_from`, anything else →
  `context`. `null` only when `link_status` is `missing_claim`.
- **`claim_links[].link_status`:** `"missing_claim"` when the tagged id does not resolve in the
  current `claims[]` list (dangling `[claim:]` tag); otherwise `"linked"` in `export_run()`
  output today. `"stale"` is a capability of the underlying `derive_report_anchors()` function
  (hash-drift detection against a previously-derived anchor set) that `export_run()` does not
  yet wire up — see the function's docstring in `export_service.py`. No verification check
  currently consumes it; that lands with D13 in a later wave.
- **No new redaction surface:** anchors carry only hashes, slugs, and integer offsets — never
  paragraph prose — so the R9 sensitivity gate (§4) is unaffected. This field cannot leak
  governed quote text.

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-19 | Initial frozen contract (Phase 1 exit gate). |
| 1.1 | 2026-06-19 | **Additive post-freeze change** — added `report_draft: string \| null` top-level field to unblock the "read report → click claim chip → see quote" frontend journey. |
| 1.2 | 2026-06-21 | **Run Metadata Enrichment** — added 5 metadata fields (`linked_projects`, `category`, `tags`, `backlog_idea_ref`, `backlog_idea_id`), 3 enrichment extras (`cost_usd`, `model_profiles`, `source_count_by_type`), and 2 v2 context fields (`context`, `writebacks`). All are optional/nullable for backwards compatibility. Includes backfill migration (P2) for pre-migration runs and idempotent re-export threading (P4). Frontend filtering, display, and enrichment widgets are enabled in P5–P7. |
| 1.4 | 2026-07-05 | **Report Anchors (P2 Wave A, D7/D8)** — added `report_anchors: RFReportAnchorBlock[] \| null`, AST-derived (`markdown-it-py`) block/paragraph anchors with `[claim:]` span extraction. Additive/nullable; absent entirely on pre-1.4 exports (frontend legacy-regex fallback). No sensitivity-redaction impact (carries no prose). |
| 1.3 | 2026-06-24 | **Context block fully populated** — `research_brief_md` (verbatim `research_brief.md`, including YAML frontmatter) and `upstream_entities` (`intent_id` from `run.yaml`, `ibom_id` from `run.yaml`, `intenttree_node_id` from `routing_decision.yaml → active_node_id` with `evidence_bundle.yaml` fallback) are now populated. `context` is non-null whenever at least one file-based source artifact is present; `context` itself is null only when all three YAML/Markdown source files are absent. R9 sensitivity redaction extended to `context.routing_decision`, `context.swarm_plan`, and `context.research_brief_md`. Four context panels (Routing Decision, Research Brief, Swarm Plan, Upstream Entities) ship in the runs-viewer run detail view. Additive and backwards-compatible: schema 1.2 consumers using optional access are unaffected. |
