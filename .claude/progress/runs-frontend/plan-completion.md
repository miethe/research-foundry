# Plan Completion Report — Research Foundry Runs Frontend v1

**Plan:** `docs/project_plans/implementation_plans/features/runs-frontend-v1.md`
**Branch:** `feat/runs-frontend-v1` (based on `main@e6dc5c3`)
**Status:** COMPLETE — final reviewer (karen) APPROVED; squash-merged to `main`
**Date:** 2026-06-19
**Tier:** 2 (13 pts, 5 phases)

## Execution Model

Wave-driven sequential execution (`wave_plan.waves = [[P1],[P2],[P3],[P4],[P5]]`), orchestrated
in-session with per-phase delegation. P1 was the hard upstream gate blocking all frontend work.
Implementation was cost-shifted to ICA free-tier (`opus-4-8[1m]` / `sonnet-4-6[1m]`) where the work
was bounded/mechanical (P1 export, P2 fork+data-layer, attempted P5); taste-sensitive UI (P3 read
surfaces, P4 flagship) and all remediation ran in-session via `ui-engineer-enhanced`. P5 pivoted to
in-session execution when the ICA team budget was exhausted mid-phase. Every delegated result had its
authoritative gate (pytest / tsc / vitest / playwright / build) re-run in-session before commit.

## Per-Wave Summary

| Wave | Phase | Executor | Commit(s) | Gate result |
|------|-------|----------|-----------|-------------|
| 1 | P1 Export contract (hard gate) | ICA opus-4-8[1m] + in-session reviewers | `14bc23c`, `4b29e80` | pytest 464; export_service 91% cov; backend-architect + task-completion-validator APPROVED |
| 2 | P2 Fork + data layer | ICA sonnet-4-6[1m] | `e4045de`, `f7c9617` | tsc clean; vitest 18; vite build |
| 3 | P3 Run list + trust panel | in-session ui-engineer-enhanced | `3e31706`, `c3725ff` | tsc clean; vitest 74 |
| 4 | P4 Flagship ledger + provenance modal | in-session ui-engineer-enhanced | `db97783`, `b4f579d` | tsc clean; vitest 146; caught+fixed a real regex bug |
| 5 | P5 E2E + build + docs | in-session (docs-writer ‖ ui-engineer-enhanced) | `52b896f`, `6499297` | tsc clean; vitest 153; playwright 15/15; build over 38 runs |
| — | karen remediation (W1+W3 blockers) | in-session backend + ui-engineer-enhanced | `da59cac` | pytest 469; tsc clean; vitest 155; playwright 15/15 |

## Reviewer Gates

- **P1 schema freeze:** backend-architect APPROVED (one required redaction fix applied + threshold fail-closed hardening).
- **P1 completion:** task-completion-validator APPROVED (all 10 ACs, no superficial passes).
- **Feature-level (karen):** initial verdict CHANGES_REQUESTED — two blocking gaps that fixture-green
  tests structurally could not catch:
  1. **W3 corpus not wired** — static client read one bundled fixture, ignoring the generated 38-run
     `public/data/index.json` (showed 1 of 38 runs).
  2. **W1 report stub** — the frozen export contract omitted the report body, so the Report tab
     rendered a hardcoded stub instead of the real report.
  Both remediated in `da59cac` (report_draft added to contract @ schema 1.1 with backend-architect
  re-review APPROVED; client wired to the corpus). **karen re-review: both blockers CLOSED, APPROVED to merge.**

## Success Metrics (final)

- **W1 (claim audit ≤2 clicks):** HOLDS — ledger row → ProvenanceModal → verbatim quote; report-tab
  chip → modal now runs on the real report. RIB-018 inference false-pass class guarded + tested.
- **W2 (verification visible, no CLI):** HOLDS — TrustPanel renders checklist/donut/timeline from static export.
- **W3 (run corpus as portfolio):** HOLDS — 38-run portfolio from `public/data/index.json`.

## Invariants verified

- **R9 sensitivity:** two-layer (export redaction default `public`, fail-closed on unknown threshold;
  SourceCard defense-in-depth) — secret-absence asserted in both pytest and vitest DOM tests. Report
  body scope boundary documented in the ADR §8.
- **Read-only:** GET-only; zero mutations/forms.
- **Path-safety:** all reads via `FoundryPaths.discover()`; adversarial poison test proves no stored
  absolute path is used for I/O.

## Deferred items

Four design specs authored with promotion triggers (plan `deferred_items_spec_refs`): `runs-auth-lan.md`
(OQ-4), `runs-loopback-api.md` (OQ-6), `runs-writeback-preview.md` (FR-13), `runs-context-panels.md` (FR-14).

## Non-blocking follow-ups (tracked, not blocking v1)

- R9 residual: `claim.text` / `inference_basis.reasoning_summary` are not redacted (documented as an
  authoring-convention boundary in the ADR; out of export-layer scope).
- OQ-7 `schema_version_mismatch` badge renders correctly but nothing computes the boolean yet (forward-compat).
- W3 E2E stops at modal-open for the report-chip path; the ledger E2E covers the full quote reveal.

## Deviations from plan

- Per-phase worktree isolation was not used (plan `isolation: shared`); the whole plan ran on one
  feature branch per the user directive ("operate in branch, squash-merge to main").
- ICA was used for implementation cost-shifting where bounded; P5 + P3/P4 ran in-session (taste / budget).

## Commits (11, squashed to main)

`14bc23c` `4b29e80` `e4045de` `f7c9617` `3e31706` `c3725ff` `db97783` `b4f579d` `52b896f` `6499297` `da59cac`
