# Changelog

All notable changes to Research Foundry will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

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
