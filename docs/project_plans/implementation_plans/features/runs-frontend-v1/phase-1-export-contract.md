---
schema_version: 2
doc_type: phase_plan
title: "Phase 1: Export Contract (Upstream Gate)"
status: draft
created: 2026-06-19
updated: 2026-06-19
phase: 1
phase_title: "Export Contract (Upstream Gate)"
feature_slug: runs-frontend
prd_ref: docs/project_plans/PRDs/features/runs-frontend-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-frontend-v1.md
entry_criteria:
  - No prior phase dependencies (Phase 1 is the root)
exit_criteria:
  - rf run export --json produces valid run.json for rf_run_20260613_* real run
  - Export schema frozen + documented at docs/dev/architecture/rf-run-export-schema.md and merged
  - Sensitivity redaction confirmed by synthetic fixture test
  - Integration round-trip test green
  - backend-architect schema review sign-off recorded
  - task-completion-validator phase review passed
---

# Phase 1: Export Contract (Upstream Gate)

**Parent Plan**: [runs-frontend-v1.md](../runs-frontend-v1.md)
**Duration**: ~3–4 days
**Primary Subagent**: `python-backend-engineer` | Model: `sonnet` | Effort: `extended`
**Secondary Subagent**: `backend-architect` (schema-freeze review only) | Model: `sonnet` | Effort: `adaptive`

> This is the **hard upstream gate**. No Phase 2+ task may begin until the P1 gate is fully cleared and the export schema is merged.

---

## Phase Overview

Phase 1 is Python-only. It creates the deterministic `rf run export --json` contract that is the frontend's sole data source. The export service joins the claim graph (claim → source_card → evidence quote) without LLM invocation, redacts sensitive content at the export layer, and re-derives all file paths via `FoundryPaths.discover()`. The schema is frozen and documented before any TypeScript work begins. The H3 algorithmic flag fires for the claim-graph join + status derivation service — this is the highest-leverage correctness work in the feature.

**Resolves in this phase**: OQ-1 (schema freeze), OQ-2 (derived-status enum), OQ-3 (sensitivity threshold config).

---

## Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P1-SCHEMA-FREEZE | Freeze export schema | Author `docs/dev/architecture/rf-run-export-schema.md` with the denormalized claim-graph shape: `run.json` top-level fields, `claims[]` array with embedded `sources[]` and `evidence_quotes[]`, `status_derived` enum, `sensitivity` metadata. Resolve OQ-1. Submit for `backend-architect` review before merge. | Schema doc exists at `docs/dev/architecture/rf-run-export-schema.md`; shape is denormalized (claim carries resolved sources[]); OQ-1 closed; `backend-architect` has reviewed; doc is merged | 0.5 pts | python-backend-engineer + backend-architect | sonnet | adaptive | None — first task |
| P1-STATUS-001 | Derived-status enum | Resolve OQ-2: define the effective status enum (planned → sources_ingested → extracted → claim_mapped → synthesized → verified → published) derived from `evidence_bundle.status` + `verification.passed` + artifact presence. Encode in the export schema (P1-SCHEMA-FREEZE) and implement in export service. | Derived-status enum defined and encoded in schema doc; export service computes correct status for: (a) a run with `run.yaml.status: planned` but `verification.passed: true` (must return `verified`, not `planned`), (b) a run with partial artifact presence | 0.5 pts | python-backend-engineer | sonnet | extended | P1-SCHEMA-FREEZE |
| P1-SENS-CONFIG | Sensitivity threshold config | Resolve OQ-3: default sensitivity threshold = `public`-only; higher levels redacted at export. Add `viewer.sensitivity_threshold` key to `foundry.yaml` schema. Export service reads this key (defaulting to `public` when absent). | `foundry.yaml` supports `viewer.sensitivity_threshold`; export service reads it; default is `public`; export JSON omits/redacts fields with `sensitivity` above threshold | 0.5 pts | python-backend-engineer | sonnet | adaptive | P1-SCHEMA-FREEZE |
| P1-EXPORT-SVC | Export service core | Implement `src/research_foundry/services/export_service.py`. File walk via `FoundryPaths.discover()` (never trusted stored paths). Claim-graph join: for each `clm_NNN` entry, resolve `source_card_id` → source card YAML, extract `extracted_points[].quote` + locator + trust/usage flags. Join `evidence_bundle.yaml` for counts + governance. Join `verification.yaml` for check list. Join `telemetry/run_trace.jsonl` for timeline events. Apply sensitivity filter (P1-SENS-CONFIG) before writing JSON. | Export service produces valid `run.json` matching frozen schema; claim → source → quote chain correct (verified manually for 3 representative claims); no LLM calls anywhere in the call chain; `FoundryPaths.discover()` used for all file reads; no hardcoded absolute paths | 2 pts | python-backend-engineer | sonnet | extended | P1-STATUS-001, P1-SENS-CONFIG |

#### AC P1-EXPORT-SVC-1: No Absolute Paths
- target_surfaces:
    - src/research_foundry/services/export_service.py
- propagation_contract: All file reads must be derived from `FoundryPaths.discover(workspace_root, run_id)`; `run_index.yaml` and `verification.yaml` stored path fields are never used for actual file I/O
- resilience: If `FoundryPaths.discover()` fails (foundry.yaml not found), export exits non-zero with structured stderr JSON
- visual_evidence_required: false
- verified_by: [P1-TEST-PATHS]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P1-CLI-EXPORT | rf run export CLI command | Implement `rf run export --json [--run-id RUN_ID \| --all]` sub-command in `src/research_foundry/cli_commands.py`. Calls `export_service.export_run()`. Writes `run.json` to `<run_dir>/run.json` or stdout with `--stdout`. Exits 0 on success; non-zero with structured stderr JSON on malformed artifact. | `rf run export --json --run-id rf_run_20260613_*` produces `run.json`; exits 0; `rf run export --json --all` runs recursive discovery; malformed artifact → non-zero exit + stderr JSON line `{error, run_id, artifact_path}` | 0.5 pts | python-backend-engineer | sonnet | adaptive | P1-EXPORT-SVC |
| P1-CLI-LIST | rf run list CLI command | Implement `rf run list --json` sub-command. Recursive `runs/**/run.yaml` discovery (depth ≤ 3; catches nested `runs/runs/` anomaly). Returns JSON array of run summaries: `{run_id, status_derived, sensitivity, claim_counts, verification_passed, governance_verdict}`. Reads from `evidence_bundle.yaml` + `verification.yaml`, not from `run_index.yaml` absolute paths or stale `run.yaml.status`. | `rf run list --json` returns JSON array including the 4 nested `runs/runs/` runs; `status_derived` is correct (not `run.yaml.status`) for a known stale-status run; `run_index.yaml` not used for any file I/O | 0.5 pts | python-backend-engineer | sonnet | adaptive | P1-EXPORT-SVC |
| P1-TEST-PATHS | Path derivation unit test | Unit test: assert that no field from `run_index.yaml` or `verification.yaml` is used as a file path in export service; all file reads are derived from `FoundryPaths.discover()`. | Test passes; asserts `run_index.yaml` path fields never passed to `open()` or any file-read call; at least 5 file-read assertions covered | 0.5 pts | python-backend-engineer | sonnet | adaptive | P1-EXPORT-SVC |
| P1-SENS-001 | Sensitivity redaction test | Synthetic sensitivity fixture: create a minimal `src_SYNTH001.md` source card YAML with `sensitivity: work_sensitive` in `extracted_points[].sensitivity`. Run export service. Assert that the `extracted_points[].quote` for `work_sensitive` entries is absent or replaced with a redaction marker in the output `run.json`. | Test passes; `work_sensitive` quote content does not appear in export JSON; `public` content does appear; test is repeatable in CI | 0.5 pts | python-backend-engineer | sonnet | extended | P1-EXPORT-SVC, P1-SENS-CONFIG |

#### AC P1-SENS-001-1: Sensitivity Gate (R9 High-Severity)
- target_surfaces:
    - src/research_foundry/services/export_service.py
    - tests/unit/test_sensitivity_redaction.py
- propagation_contract: Sensitivity filter applied during export_service.export_run() before writing JSON; no component in the frontend can bypass it because the sensitive content never reaches the JSON
- resilience: If `sensitivity` field absent on a quote entry, treat as `public` (safe default — renders, not redacted)
- visual_evidence_required: false
- verified_by: [P1-SENS-001, P4-SENS-001]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P1-TEST-UNIT | Export service unit tests | Unit tests for: claim-graph join correctness (claim resolves to source → quote), status derivation (stale-status case), sensitivity filter (P1-SENS-001 covered separately), path derivation (P1-TEST-PATHS covered separately). Test against synthetic YAML fixtures (not real run data). | Unit test coverage > 80% for `export_service.py`; claim-graph join, status derivation, and sensitivity filter each have dedicated test cases; test suite runs in CI without network | 1 pt | python-backend-engineer | sonnet | extended | P1-EXPORT-SVC, P1-STATUS-001 |
| P1-INT-TEST | Integration round-trip test | Integration test: run `rf run export --json --run-id rf_run_20260613_*` against the real run. Assert: (a) every `[claim:clm_NNN]` tag present in `report_draft.md` has a corresponding entry in the export JSON `claims[]`; (b) at least 3 randomly sampled claims have non-null `sources[]` with non-empty `quote`; (c) export exits 0; (d) `run.json` validates against the frozen schema. | Integration test passes on `rf_run_20260613_*`; claim→source→quote chain correct for sampled claims; schema validation passes | 0.5 pts | python-backend-engineer | sonnet | extended | P1-TEST-UNIT, P1-CLI-EXPORT, P1-SCHEMA-FREEZE |

---

## Phase 1 Dependency Graph

```
P1-SCHEMA-FREEZE
     ├── P1-STATUS-001 ──┐
     └── P1-SENS-CONFIG ─┤
                         ├── P1-EXPORT-SVC
                         │        ├── P1-CLI-EXPORT ──┐
                         │        ├── P1-CLI-LIST     │
                         │        ├── P1-TEST-PATHS   ├── P1-TEST-UNIT ── P1-INT-TEST
                         │        └── P1-SENS-001 ────┘
                         └── (backend-architect reviews P1-SCHEMA-FREEZE before merge)
```

**Gate clearance**: P1-INT-TEST green + backend-architect schema review + `task-completion-validator` review → P1 gate cleared → P2 may begin.

---

## Key Files Affected

- `src/research_foundry/services/export_service.py` (new)
- `src/research_foundry/cli_commands.py` (adds `rf run export`, `rf run list` sub-commands)
- `docs/dev/architecture/rf-run-export-schema.md` (new — schema freeze doc; explicit dependency of every P2 task)
- `tests/unit/test_export_service.py` (new)
- `tests/unit/test_sensitivity_redaction.py` (new)
- `tests/integration/test_export_round_trip.py` (new)
- `foundry.yaml` (schema addition: `viewer.sensitivity_threshold`)

---

## Phase 1 Notes

- **H3 algorithmic flag**: The claim-graph join (claim → source_card_id → source YAML → extracted_points[].quote + locator) and the derived-status computation both fire the H3 flag. `effort: extended` for the core export service tasks reflects this.
- **OQ-1 resolution sequence**: P1-SCHEMA-FREEZE must be the first task authored. The denormalized shape decision (claim carries resolved `sources[]`, not just IDs) is load-bearing for all downstream TypeScript types.
- **Sensitivity default**: OQ-3 is resolved as `public`-only default. Any `sensitivity` value other than `public` (i.e., `work_sensitive`, `client_sensitive`) is redacted from `extracted_points[].quote` in the export JSON. This invariant is recorded in the ADR authored in Phase 5.
