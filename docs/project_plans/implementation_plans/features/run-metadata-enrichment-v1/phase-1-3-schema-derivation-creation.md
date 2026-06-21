---
schema_version: 2
doc_type: phase_plan
title: "Run Metadata Enrichment — Phases 1–3: Schema, Derivation & Creation"
status: draft
phase: "1-3"
phase_title: "Schema & Contract, Derivation & Backfill, Creation Path"
created: 2026-06-20
updated: 2026-06-20
feature_slug: run-metadata-enrichment
prd_ref: docs/project_plans/PRDs/features/run-metadata-enrichment-v1.md
plan_ref: docs/project_plans/implementation_plans/features/run-metadata-enrichment-v1.md
entry_criteria:
  - "PRD approved; decisions block reviewed"
  - "Backlog YAML at backlog/research_idea_backlog.yaml is the source of truth for links"
exit_criteria:
  - "P1: run.yaml YAML schema validates with new fields; codegen (if opted in) produces compiling types"
  - "P2: all runs that have backlog links carry linked_projects/category/tags/backlog_idea_ref; dry-run diff reviewed"
  - "P3: new run created by plan_run() carries all metadata fields end-to-end; rf capture --backlog-idea-ref works"
---

# Phases 1–3: Schema & Contract · Derivation & Backfill · Creation Path

**Parent plan**: [run-metadata-enrichment-v1.md](../run-metadata-enrichment-v1.md)
**Phases covered**: P1 (Schema & Contract), P2 (Derivation & Backfill), P3 (Creation Path)
**Critical path**: P1 → P2 (sequential); P3 can start after P1, parallel to P2

---

## Column conventions

| Column | Values |
|--------|--------|
| Estimate | story points |
| Model | `sonnet` \| `haiku` \| `opus` |
| Effort | `adaptive` \| `extended` (Claude only) |

---

## Phase 1: Schema & Contract

**Duration**: 1–2 days
**Dependencies**: None (first phase)
**Assigned Subagents**: data-layer-expert (schema), python-backend-engineer (codegen wiring)

### Overview

Extend `run.yaml` with the five new metadata fields, author a formal JSON schema for `rf-run-export`,
and set up optional TS codegen for `run-export.ts`. This phase establishes the contracts that every
downstream phase depends on.

### Source references (verified)
- `run.yaml` fields today: `project` already present (planning.py:~449-475).
- `RFRunExport` frozen at schema 1.1: `types/rf/run-export.ts`.
- No formal JSON schema file today; comment references `docs/dev/architecture/rf-run-export-schema.md`
  (epic brief §1.12).
- `backlog/research_idea_backlog.yaml`: idea fields include `pillar`, `tags[]`, `suggested_project`,
  and `links.run_id` (epic brief §1.11).

### Task table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| SCH-001 | Extend run.yaml schema | Add `linked_projects[]` (list of string slugs), `category` (string), `tags[]` (list of strings), `backlog_idea_ref` (string, e.g. RIB-NNN), `backlog_idea_id` (string, reverse slug). Document each field with an inline YAML comment. Treat all as optional (existing runs lack them). | `run.yaml` with the 5 new fields parses without errors; `pydantic`/schema validator (if any) accepts them; inline comments describe source | 1 pt | data-layer-expert | sonnet | adaptive | — |
| SCH-002 | Author formal rf-run-export JSON schema | Create `docs/dev/architecture/rf-run-export-schema.json` (JSON Schema draft-07). Covers all current `RFRunExport` fields (schema_version, run_id, intent_id, created_at, status_derived, status_raw, sensitivity, sensitivity_threshold, claim_counts, verification, governance, timeline, claims, artifact_schema_versions, report_draft, context, writebacks) PLUS the 5 new metadata fields. Bump `schema_version` to `1.2` in the schema. Mark all 5 new fields `nullable: true` for backwards compat. | Schema file exists and validates against at least one real `run.json` (use `ajv` or `jsonschema`); all existing required fields present; new fields have `nullable: true`; `schema_version` = `"1.2"` in the schema | 2 pts | python-backend-engineer | sonnet | adaptive | SCH-001 |
| SCH-003 | TS codegen setup (optional but recommended) | Evaluate `json-schema-to-typescript` (or `quicktype`) against the JSON schema from SCH-002 to generate `src/types/rf/run-export.generated.ts`. If codegen produces clean output: wire it into `prebuild-static-data.mjs` as a pre-step (run before export); update `run-export.ts` to re-export from the generated file or extend it. If codegen is too noisy: document why and keep hand-written types — but this decision MUST be recorded in a one-line comment at the top of `run-export.ts`. | Either (a) codegen runs as part of pnpm prebuild and generated types compile with `npx tsc --noEmit`, OR (b) a comment in `run-export.ts` explains "codegen evaluated, rejected because …" and types remain hand-written. Decision recorded in plan frontmatter `architecture_summary`. | 2 pts | python-backend-engineer | sonnet | adaptive | SCH-002 |
| SCH-004 | Update RFRunSummary preliminary stub | Add `linked_projects?: string[]`, `category?: string`, `tags?: string[]` to `RFRunSummary` in `run-export.ts` as optional fields (null-safe). These are stubs — P4 will populate them with real data from index.json. Mark with `// populated in P4` comment. | `RFRunSummary` interface compiles with the 3 new optional fields; no other code changes required yet | 1 pt | python-backend-engineer | sonnet | adaptive | SCH-001 |

**Phase 1 Quality Gates:**
- [ ] `run.yaml` with the 5 new fields parses without errors
- [ ] `rf-run-export-schema.json` exists, validates against a real run.json, schema_version = "1.2"
- [ ] TS stubs in `RFRunSummary` compile (`npx tsc --noEmit` clean)
- [ ] Codegen decision recorded (either wired or documented as rejected)
- [ ] All new fields marked optional/nullable (R-P2 contract)

---

## Phase 2: Derivation & Backfill

**Duration**: 1–2 days
**Dependencies**: Phase 1 complete (SCH-001 required for field names)
**Assigned Subagents**: python-backend-engineer

### Overview

Build an idempotent, dry-run-able migration script that inverts `backlog/research_idea_backlog.yaml`
`links.run_id` → `linked_projects`/`category`/`tags`/`backlog_idea_ref` onto existing run.yaml files.
Also update `registries/run_index.yaml`. Non-destructive: never overwrites already-set fields unless
`--force` is passed.

### Source references (verified)
- Backlog linkage: `backlog/research_idea_backlog.yaml` each idea has `links.run_id` (the run ID that
  executed this idea). This is the authoritative join key — NOT fuzzy title matching (risk H: backfill
  correctness; epic brief §1.11).
- `run_index.yaml` at `registries/run_index.yaml`: per-run summary index; should also be updated.
- Risk H: dual-write (run.yaml vs run_index.yaml). Mitigate: single writer (this migration); run_index
  derived from run.yaml; keep atomic file writes.

### Task table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| MIG-001 | Backlog inversion map | Write a Python utility (or inline in migration) that reads `backlog/research_idea_backlog.yaml`, builds a dict `run_id → {linked_projects: [idea.suggested_project], category: idea.pillar, tags: idea.tags, backlog_idea_ref: idea.id, backlog_idea_id: idea.id}`. For ideas with no `links.run_id`, skip. For multiple ideas linking the same run_id, merge (union tags, collect all suggested_projects into linked_projects list). | Given the real backlog file, inversion map covers all ideas that have `links.run_id` set; union logic correct; no KeyError on missing fields | 1 pt | python-backend-engineer | sonnet | adaptive | SCH-001 |
| MIG-002 | Backfill script (dry-run first) | Create `scripts/backfill_run_metadata.py` (CLI: `python scripts/backfill_run_metadata.py [--dry-run] [--force] [--run-id RUN_ID]`). For each run in `runs/*/run.yaml`: look up the inversion map from MIG-001; if match found AND field not already set (or `--force`): write new fields into `run.yaml` atomically (write to tmp, then rename). Default: `--dry-run` (print diff only; no writes). Without `--dry-run`: writes and prints summary. `--run-id` limits to a single run. | `--dry-run` output shows exactly which runs would be updated and what would change; actual write produces correct YAML in `run.yaml`; `run.yaml` YAML structure preserved (no field loss); idempotent (re-run produces no diff on already-updated runs) | 2 pts | python-backend-engineer | sonnet | adaptive | MIG-001 |
| MIG-003 | run_index.yaml update | Extend `MIG-002` (or a separate step in the script) to also update `registries/run_index.yaml` with `linked_projects`, `category`, `tags`, `backlog_idea_ref` for each updated run. Must be consistent with what was written to `run.yaml`. | After `backfill_run_metadata.py` (without `--dry-run`), `run_index.yaml` entries for updated runs contain the correct new fields; no other fields altered | 1 pt | python-backend-engineer | sonnet | adaptive | MIG-002 |
| MIG-004 | Reversibility / backup mechanism | Before writing any `run.yaml`, back up the original to `run.yaml.bak` (in the same directory) if `--backup` flag passed. Document in `--help` that `run.yaml.bak` can be used for rollback. Add a `--restore` mode that reads `.bak` files. | `--backup` creates `.bak` files; `--restore` restores them; `--help` documents both; migration risks noted in run-metadata-enrichment human brief | 1 pt | python-backend-engineer | sonnet | adaptive | MIG-002 |
| MIG-005 | Dry-run review task (human gate) | Run `python scripts/backfill_run_metadata.py --dry-run` and capture the diff output. Reviewer (human or karen) reviews for correctness: expected number of runs updated, no spurious overwrites, no missing backlog links. Gate: diff approved before `--no-dry-run` run. | Diff output reviewed and approved in PR comment or worknotes; actual migration only runs after approval | 0.5 pts | python-backend-engineer | sonnet | adaptive | MIG-004 |

**Phase 2 Quality Gates:**
- [ ] `backfill_run_metadata.py --dry-run` shows correct diff (all runs with backlog links)
- [ ] Actual run produces correct YAML in `run.yaml` for at least 3 sample runs (verified manually)
- [ ] `run_index.yaml` updated consistently
- [ ] Idempotent: re-run produces empty diff
- [ ] `--backup` / `--restore` modes documented and tested
- [ ] Human gate (MIG-005): dry-run diff reviewed before production run

---

## Phase 3: Creation Path

**Duration**: 1 day
**Dependencies**: Phase 1 complete (P1 field definitions); parallel to P2
**Assigned Subagents**: python-backend-engineer

### Overview

Wire new metadata fields into `services/planning.py:plan_run()` so future runs carry linkage from
birth. Update `seed_swarm_runs.sh` and `rf capture` CLI to accept `--backlog-idea-ref` argument.

### Source references (verified)
- `plan_run()` at `services/planning.py:~449-475`: sets `project` from explicit arg > intent.project >
  raw_idea.suggested_project > 'unassigned' (epic brief §1.12).
- `seed_swarm_runs.sh`: one `rf capture`/plan per idea; passes research_question, tags, sensitivity,
  governance; does NOT pass suggested_project (epic brief §1.11).

### Task table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| CRE-001 | plan_run() field population | Extend `plan_run()` in `services/planning.py` to populate `linked_projects`, `category`, `tags`, `backlog_idea_ref`, `backlog_idea_id` in the new `run.yaml`. Sources: (a) if `backlog_idea_ref` passed → look up backlog YAML → extract pillar (category), tags, suggested_project (→ linked_projects[0]); (b) else: use `run.yaml.project` for linked_projects (if non-'unassigned'), leave category/tags/backlog_idea_ref null. Write atomically to run.yaml. | A test run created via `plan_run(backlog_idea_ref='RIB-001')` has correct `linked_projects`, `category`, `tags`, `backlog_idea_ref` in `run.yaml`; a run created without the arg has linked_projects derived from project (or null) | 2 pts | python-backend-engineer | sonnet | adaptive | SCH-001 |
| CRE-002 | rf capture --backlog-idea-ref flag | Add `--backlog-idea-ref RIB-NNN` optional flag to `rf capture` CLI command. When provided, pass through to `plan_run()`. Validate that the RIB-NNN slug exists in the backlog before creating the run (with helpful error if not found). | `rf capture --backlog-idea-ref RIB-001 ...` creates a run with correct metadata in run.yaml; `rf capture --backlog-idea-ref RIB-999` (non-existent) exits with clear error message | 1 pt | python-backend-engineer | sonnet | adaptive | CRE-001 |
| CRE-003 | seed_swarm_runs.sh update | Update `scripts/seed_swarm_runs.sh` to pass `--backlog-idea-ref ${idea_id}` when calling `rf capture` for each idea. Ensures future seeded runs carry backlog linkage. | Running `seed_swarm_runs.sh` for a test idea creates a run with `backlog_idea_ref` set in run.yaml | 1 pt | python-backend-engineer | sonnet | adaptive | CRE-002 |
| CRE-004 | End-to-end creation smoke test | Write a pytest test (or extend existing) that: creates a run with `plan_run(backlog_idea_ref='RIB-001')` (using a mock or fixture if needed), verifies all 5 new fields in `run.yaml`, then runs the export to confirm the fields will appear in `run.json` (can stub export). | pytest passes; all 5 fields verified in run.yaml after creation; test is in the test suite and runs with `uv run pytest` | 0.5 pts | python-backend-engineer | sonnet | adaptive | CRE-001 |

**Phase 3 Quality Gates:**
- [ ] `plan_run()` populates all 5 new metadata fields when `backlog_idea_ref` provided
- [ ] `rf capture --backlog-idea-ref RIB-NNN` works end-to-end
- [ ] `seed_swarm_runs.sh` passes `--backlog-idea-ref` for each idea
- [ ] pytest for end-to-end creation passes (`uv run pytest`)
- [ ] Runs created without backlog ref degrade gracefully (fields null/absent)

---

## Integration note (P1 → P2 → P3 seam)

P2 and P3 both write to `run.yaml`. They use different paths (P2 = backfill existing; P3 = new runs)
and should NOT conflict. However, if a run was seeded via `seed_swarm_runs.sh` AFTER P3 ships but
BEFORE P2 runs backfill, the new run will already have correct fields — P2 must handle this gracefully
(idempotent: skip already-set fields unless `--force`). This is covered by MIG-002's idempotency AC.
