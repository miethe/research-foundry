# Changelog

All notable changes to Research Foundry will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

#### **Runs Viewer — Run Context Panels (FR-14)**

- **Run context panels** — four collapsed, read-only panels in the run detail view: Routing
  Decision, Research Brief, Swarm Plan, and Upstream Entities. Operators can now inspect why a
  particular model profile was chosen, what research brief was given, which adapters ran and in
  what sequence, and which upstream organizational intent triggered the run — without switching
  to the CLI.
- **`run.json` schema 1.3 `context` block** — `rf run export --json` now embeds a top-level
  `context` object containing `routing_decision` (allowlist-filtered from `routing_decision.yaml`),
  `research_brief_md` (verbatim Markdown from `research_brief.md`), `swarm_plan` (allowlist-filtered
  from `swarm_plan.yaml`), and `upstream_entities` (`intent_id`, `ibom_id`, `intenttree_node_id`
  from `run.yaml` and `routing_decision.yaml`). Each field is `null` when its source artifact is
  absent; `context` itself is `null` on pre-1.3 runs. Additive and fully backwards-compatible.
- **Context sensitivity redaction** — the R9 export-time sensitivity gate is extended to
  `context.*` fields: string values in `routing_decision` and `swarm_plan` are redacted when they
  exceed the active threshold; `research_brief_md` is redacted in full when its frontmatter
  `sensitivity:` key exceeds the threshold. No governed content enters `run.json`.

#### **Loopback API — Live Runs without Static Export**

- **`rf serve` command** — Read-only FastAPI server for runs-viewer live data (loopback mode, 
  default port 7432). Serves run summaries, claim ledgers, and source cards directly from 
  on-disk runs without pre-export; enables SPA-to-backend polling for live updates.
- **Loopback API mode** — SPA can read live runs without static export via 
  `VITE_RUNS_FRONTEND_LOOPBACK_API` environment variable. When enabled, `RFRunSummary` and 
  claim queries fetch from the loopback API instead of bundled `index.json`.
- **Gated LAN exposure** — `rf serve --bind-host 0.0.0.0` requires `--auth-mode token` and a 
  configured token; fails closed without one. Prevents accidental unauthenticated exposure of 
  sensitive research data across network boundaries.

#### **Runs Viewer — Swarm, Policies & Library tabs** (enable-disabled-viewer-tabs epic, Wave 2)

- **Swarm tab** — Per-run view (`/runs/:runId/swarm`) visualizing the run's swarm plan
  (swarm, agents, adapters) and routing decision, with a graceful empty state for runs exported
  before metadata enrichment.
- **Policies tab** — Top-level governance view (`/policies`) with a Global Governance Panel
  (key profiles and policy rules from `config/governance.yaml`) and a Per-Run Governance table
  (sensitivity, writeback approval, allowed writebacks, human-review requirement).
- **Library tab** — Top-level index (`/library`) of reusable-output candidates and writeback
  artifacts across runs; stale run references degrade to plain text rather than broken links.
- With these three tabs, all six previously-disabled navigation tabs (Settings, Help, Alerts,
  Swarm, Policies, Library) are now enabled — no dead nav items remain in the viewer.

#### **`decision_record` Writeback — Close the RF→Project Harvest Seam (Gap 1)**

- **`decision_record` writeback** — `rf writeback` now emits an additive `meatywiki/decisions/<slug>.md`
  alongside the existing `source_note` whenever a completed run's claim ledger contains at least one
  `status: inference` claim (typically a `claim_type: recommendation`). The rendered file carries a
  populated **Decision** section (primary inference claim text), **Rationale** (reasoning summaries from
  all inference claims), and **Links** back to the source claim IDs (`inference_basis.from_claims`).
  Recommendation-typed claims appear first. Deterministic-only runs (zero inference claims) silently
  skip the file — no error, no empty record.
- **`rf writeback --decision-record-only --run <id>`** — new flag re-renders only the
  `decision_record_writeback.md` for an existing run without disturbing the run's other writeback
  files. Used for the backfill path over already-completed runs.
- **`scripts/backfill_decision_record_writebacks.py`** — bulk backfill helper that re-renders
  decision records over all runs with inference claims (`--dry-run` by default; `--write` to apply;
  `--run-id` to target a single run).
- **`services/planning.py::_WRITEBACKS`** now declares `{meatywiki: [source_note, decision_record],
  skillmeat: skillbom_candidate, ccdash: execution_event}` so the run contract reflects the full
  writeback set.

#### **Run Metadata Enrichment (v1)** — Linked Projects, Category, and Tags

- **Linked Projects, Category, and Tags on every run** — Research Foundry runs now carry structured
  metadata derived from the research backlog. Each run links to zero or more research ideas via
  `linked_projects[]`, carries a single `category` (from backlog), and inherits a `tags[]` array.
  18 existing runs have been backfilled; new runs created via `rf capture --backlog-idea-ref` or
  `plan_run()` automatically populate these fields at creation time.
- **Portfolio filtering by project, category, and tag** — `FilterTabs.tsx` extends filter controls
  to expose three new sections: "Project" (checkbox list of all linked projects across the
  portfolio), "Category" (checkbox list of categories), and "Tags" (checkbox list of tags). Filters
  use AND-logic; selecting multiple projects/categories/tags narrows results. Empty-state gracefully
  renders when no runs match.
- **Metadata display across all viewer surfaces** — Linked Projects appear as a primary column in
  the RunList portfolio table; RunCard badges display the project (primary) and category; RunDetail
  Overview and RunDetailModal headers show project, category, and tag chips. ClaimAuditWorkbench and
  LineageDetailPanel reference tags in their inspection panes. All surfaces gracefully omit metadata
  when fields are null (pre-migration runs).
- **Enrichment-extra fields** — Export schema bumped to v1.2; `rf run export --json` now includes
  additional run metadata: `cost_usd` (execution cost), `model_profiles` (object with extraction,
  synthesis, and verification model names and budgets), `source_count_by_type` (breakdown of web,
  document, and other source types), and threading of `context.routing_decision` and
  `context.swarm_plan` for downstream swarm analysis. Each field is optional and null-safe.
- **Enrichment overview widgets** — RunDetailWorkspace Overview tab now shows a second "Enrichment"
  section (below the P5 Run Metadata section) with widgets for Cost (formatted USD), Model Profiles
  (compact model-by-model table), Source Count by Type (counts grouped by type), Claim Distribution
  (stacked progress bars for supported/inference/speculation/contradicted/unsupported claims), and
  Writeback Targets (name and status). Each widget renders only when its field is non-null;
  pre-enrichment runs omit the entire section.
- **Backfill script and creation path** — `scripts/backfill_run_metadata.py` idempotently derives
  metadata from the backlog and writes to existing `run.yaml` files (with `--dry-run` support);
  `plan_run()` in the Python core wires metadata at creation; `rf capture --backlog-idea-ref ID`
  captures a new research run tied to a backlog idea.

#### runs-viewer v2.2 — Nav, Titles, and Lineage Fixes

- **Run titles on all list surfaces**: `RunCard` and `StatusLane` buttons now display a human-readable run title derived from the report frontmatter `title:` key, with a slug-humanized fallback (e.g., `rf_run_20260613_roots_wave` → "Roots Wave"). Raw `run_id` slugs no longer appear as the primary display string.
- **`title` field in export**: `export_service.py:export_run()` now derives and includes a `title` field in `run.json`; `prebuild-static-data.mjs` copies it into `index.json`; `RFRunSummary` type updated with `title?: string`.
- **Lineage graph edges render**: `LineageFlow.tsx` now registers `SmoothStepEdge` from `@xyflow/react` as `edgeTypes` at module scope and passes `edgeTypes={edgeTypes}` to `<ReactFlow>`. Edges (connector lines between nodes) now appear in the Lineage tab graph view. Edges carry `className='rv-lineage-edge'` for CSS targeting.

### Fixed

#### runs-viewer v2.2

- **Run-click → modal + aligned nav**: StatusLane buttons previously called `setSelectedRunId` without opening `RunDetailModal`. Now calls `setSelectedRunId(runId)` and `setModalRunId(runId)` consistently, so every card click opens the modal and the Runs nav item stays aligned.
- **Default detail tab is Overview**: `coerceDetailTab` fallback changed from `'trust'` to `'overview'` so `/runs/:runId` with no `?tab=` param defaults to the Overview tab. The `'audit'→'ledger'` alias and all other valid tab values are unchanged.

#### `rf run` sub-commands (Python CLI — `runs-frontend-v1` Phase 1)

- **`rf run export --json`** — export a single run's full denormalized claim
  graph to `<run_dir>/run.json`. The export joins `claim_ledger.yaml` →
  `source_card/*.md` → `extracted_points[].quote` in Python; no LLM is on the
  recall path. Sensitivity redaction is applied at export time (default threshold:
  `public`; configurable via `foundry.yaml → viewer.sensitivity_threshold` or
  `--sensitivity-threshold LEVEL`). All file reads go through
  `FoundryPaths.discover()` — stored absolute paths are never used for I/O.
- **`rf run export --json --all`** — batch-export every discovered run
  (recursive `runs/**/run.yaml` discovery, depth ≤ 3; catches nested
  `runs/runs/<id>/` layouts).
- **`rf run export --json --stdout`** — emit the JSON to stdout instead of
  writing `run.json`; useful for piping to `jq` or CI scripts.
- **`rf run list --json`** — JSON array of run summaries, each with a
  `status_derived` field computed from on-disk artifacts (never the stale
  `run.yaml.status`). Derived-status enum: `planned → sources_ingested →
  extracted → claim_mapped → synthesized → verified → published`.

#### Runs viewer SPA (`frontend/runs-viewer/` — `runs-frontend-v1` Phases 2–4)

- **Run-corpus portfolio view** — browse all discovered RF runs as a filterable
  card grid. Filter tabs: `verified`, `needs-review`, `failed`, `planned`.
  Schema-mismatch badge shown when a run's `schema_version` diverges from the
  current export contract.
- **Verification checklist panel** — per-run trust panel renders all named
  checks from `reviews/verification.yaml` with pass/warn/fail indicators and
  deep-link anchors to the relevant claim (`clm_NNN`). No CLI call required.
- **Claim ledger table** — full paginated claim ledger with facet filters by
  status, materiality, claim type, and confidence. Color-coded status badges
  (`supported`, `inference`, `speculation`, `contradicted`, `unsupported`).
- **Claim provenance two-click drill-down** — clicking any claim row opens a
  provenance modal that resolves `claim → sources[] → verbatim evidence quote`
  in one additional click. Inference chains (`from_claims`) are shown with their
  basis; empty-basis inferences (the RIB-018 class) are flagged with a warning
  badge.
- **Sensitivity-gated source cards** — source card bodies render `quote` and
  `summary` only when the export threshold permits; redacted fields display
  `[redacted:sensitivity]`. No governed content is present in `run.json` at
  render time (R9 invariant).
- **Report overlay with live claim chips** — renders `reports/report_draft.md`
  Markdown with `[claim:clm_NNN]` tags converted to clickable chips. `Inference:`
  and `Speculation:` sentences are color-coded. A composition sidebar shows
  percentage breakdown of supported/inference/speculation with click-to-filter.

### Architecture

- **ADR `adr-runs-read-path`** — records static `rf run export --json` as the
  primary (and sole v1) read path; documents the four load-bearing invariants
  (R9 sensitivity gate, read-only SPA, path-safety, no LLM on recall path); and
  describes the deferred loopback API path behind `RUNS_FRONTEND_LOOPBACK_API`.
- **Export schema v1.0** frozen at
  `docs/dev/architecture/rf-run-export-schema.md`; `backend-architect` review
  approved.

---
