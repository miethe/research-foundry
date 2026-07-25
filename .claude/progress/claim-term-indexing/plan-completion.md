---
type: progress
schema_version: 2
doc_type: progress
prd: claim-term-indexing
feature_slug: claim-term-indexing
phase: 0
title: "Plan Completion Report: Claim Term Indexing v1"
status: completed
created: '2026-07-25'
updated: '2026-07-25'
prd_ref: docs/project_plans/PRDs/features/claim-term-indexing-v1.md
plan_ref: docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md
commit_refs:
- ab282f2
- 42ddf40
- 335a014
- 1df4fa8
pr_refs: []
owners:
- opus-orchestrator
contributors:
- ica-executor
- task-completion-validator
- karen
execution_model: wave-driven
model_usage:
  primary: opus-5
  external:
  - claude-sonnet-5[1m] (ICA)
tasks: []
parallelization: {}
---

# Plan Completion Report — Claim Term Indexing v1

**Plan**: `docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md`
**Tier**: 2 · **Effort**: 12 pts · **Phases**: 5 across 4 waves
**Branch**: `worktree-claim-term-indexing` (4 commits on `feab7de`)
**Diff**: 58 files, +4329 / −162

## Wave Summary

| Wave | Phases | Leaves | Gate | Verdict |
|------|--------|--------|------|---------|
| 1 | P1 write-path core | 1 ICA leaf + 1 remediation | task-completion-validator | APPROVED |
| 2 | P2 read-model propagation | 3 ICA leaves (P2a ∥ P2b, then P2c) + 1 remediation | task-completion-validator | APPROVED |
| 3 | P3 ∥ P4 (disjoint files) | 2 ICA leaves + 2 remediations | task-completion-validator ×2 | APPROVED ×2 |
| 4 | P5 finalization | 1 ICA leaf | karen (end-of-feature) | see GATE-001 |

## Routing

Per the operator directive and `delegation-router`, all implementation leaves resolved to
`ica-executor` on `claude-sonnet-5[1m]`; every verdict-class gate was **force-overridden to `claude`**
by the MUST-stay rule even when ICA was explicitly requested — confirming reviewer gates cannot be
offloaded. RoutingRecords audit-logged to `.claude/logs/routing-decisions.jsonl`.

The `execute-plan` workflow shell cannot reach ICA in this repo (no `ica-executor` in the RF roster),
so Opus drove the wave sequence directly, dispatching `timeout -k`-guarded headless leaves and acting
as the single committer. No leaf performed any git operation.

## Validation

- **Backend**: full suite at **16 failures = exactly the pre-existing worktree baseline, zero new**,
  re-verified after every wave. Baseline = pediatric-CDS bundle fixtures needing gitignored data
  (data-plane split), five `test_serve_api.py` 404s from a known default-public threshold issue, and a
  stale `test_report_anchors.py` assertion.
- **Frontend**: `tsc -p tsconfig.app.json --noEmit` exit 0 (the plain form is a no-op in this repo);
  vitest 1056/1057, the 2 failing files pre-existing/environmental.

## Plan/repo drift corrected during execution

The plan carried four stale paths and three generated-artifact seams it did not name:

| Item | Plan said | Reality |
|---|---|---|
| claim ledger schema | `src/research_foundry/schemas/claim_ledger.schema.yaml` | repo-root `schemas/` |
| report frontmatter schema | `src/research_foundry/schemas/report_frontmatter.schema.yaml` | repo-root `schemas/` |
| fingerprint module | `services/assertion_identity.py` | `src/research_foundry/assertion_identity.py` |
| viewer exporter | `frontend/runs-viewer/src/lib/run-export.ts` | `src/types/rf/run-export.ts` (only one exists) |
| TS codegen seam | not mentioned | schema edits require `pnpm codegen`; `codegen:check` enforces |
| export version literals | not mentioned | 8 tests hardcode the schema version; a bump breaks them |
| OpenAPI seam | not mentioned | router param changes require `scripts/generate_openapi.py` |

## Defects caught by gates, not by implementing leaves

Consistent with this repo's documented history, several real issues surfaced only under review:

1. **Schema-registry regression** (P1) — a new schema file broke `test_registry_lists_all_schemas`; the
   leaf never reported it (it produced no report at all).
2. **Backend facet gap** (P4) — `_facets()` computed no terms facet, leaving the chip-row permanently
   empty in loopback mode. Closed with a `catalog_terms`→`catalog_items` JOIN applying **both** the
   sensitivity-threshold and the WKSP-304 `workspace_id` predicates — `catalog_terms` has no
   `workspace_id`, so a naive query would have crossed workspace boundaries.
3. **Near-vacuous deep-link test** (P4) — the `?term=` tests asserted only that the *matching* claim
   rendered, so they would have passed with term filtering entirely disabled. The implied control was
   an inference-type item rendering in a different tab and could never have served as one. Fixed with a
   proper control and **empirically proven** to fail when the filter is disabled.
4. **Guard-test vacuity risk** (P1) — the byte-inertness guard compared check lists without asserting
   non-emptiness. Probed empirically (17 checks in both fixtures) and pinned with an explicit assertion.

## Known gaps (recorded, not silently accepted)

| Gap | Status |
|---|---|
| **AC-8 visual evidence** — no runtime browser smoke, no ≥1440px screenshot | **UNMET**; jsdom/vitest substituted. Needs a follow-up with browser automation. |
| **TASK-3.3 real-corpus validation** — 7 pediatric-CDS bundles unreachable (private gitignored data repo) | **UNMET**; dry-run exercised against fixtures. No fake bundle fabricated. Follow-up: run dry-run then wet-run against the real 87-claim ledger where the data exists. |
| **TASK-4.1 surface deviation** — chip-row in `CatalogScreen.tsx`, not `AssertionCatalogPane.tsx` | Justified by two independent reviewers: that pane is source-assertion-ledger-backed with no `catalog_terms` relationship. Plan inaccuracy, not an implementation gap. |
| **Non-atomic ledger writes** — `yamlio.dump_yaml` uses `write_text`, no temp+rename | Pre-existing shared infra inherited from the `rights_backfill.py` pattern. Follow-up against `yamlio` generally. |
| **DOC-005 symbol-graph regen** | N/A — `ai/` is gitignored (`.gitignore:91`); untracked local artifacts. |
| `_facets()` `roles` facet has no frontend consumer | Noted, not a defect. |
| `--term` matching is exact-lowercase-canonical (`cbc` matches, `CBC` does not) | Documented in SERVICE_CONTRACT §17; mirrors the existing `--item_type`/`--project` convention. |

## Deferred items

All four have design specs at their triage-table paths and are listed in the plan's
`deferred_items_spec_refs`: model-assisted usage roles (PRD-OQ-2), strict-schema extension (PRD-OQ-3),
controlled-vocabulary import (PRD-OQ-1 residual), and `search_text` term aliasing (design-spec OQ-B —
which explicitly names the sensitivity-leak risk that must be resolved before it is attempted).

## GATE-001 (karen) — two CHANGES_REQUESTED cycles before approval

The end-of-feature gate did what the per-phase gates could not, and found a **sixth fail-open** of the
same species as CARP C3's five: an ambiguous signal resolving toward the stronger, more load-bearing
label, with tests written *around* the defect rather than at it.

**Round 1 — `threshold` over-labeling (High).** `classify_usage_role()` scanned the entire claim text
and `_THRESHOLD_CONTEXT` carried a bare `\d`, so any stray digit promoted every matched term to
`threshold` ("ordered at the 12-month visit", "described in 1937", "Guidelines from 2024"). Separately,
a single structured `pediatric_cds` hit promoted *every* term in the claim. On a real clinical corpus
nearly every badge would have read `threshold` — maximizing the derived-vs-attested namespace collision
the PRD's own risk row exists to prevent, and making `--role threshold` a near-no-op facet. It survived
three prior reviews because the sole `background` fixture was hand-picked with zero digits.
Also found: the delivery record failed the repo's own `validate-phase-completion.py` (the exact
"batch-flip completion" class that gate exists to block), a CHANGELOG naming a non-existent command,
and an undocumented catalog-wipe-on-deploy.

**Round 2 — mitigation is not closure.** The first fix added a ±15-char window and locator-keyed the
structured signal, but kept the bare `\d`, so the *bias direction* was unchanged. karen measured it on
a hand-labeled corpus: precision moved only **0.33 → 0.43** — 8 of 14 `threshold` labels still wrong —
and the narrow window introduced a new false-negative class (thresholds with an intervening clause).
The ±15 constant was an honest comment about an n=3 inference.

**Resolution.** Comparator **AND** digit now both required in-window; comparator set widened; window
re-derived by measurement (50 chars). Final: **precision 0.80, recall 1.00** against a 22-fixture
hand-labeled corpus checked into `tests/test_term_index.py`, guarded numerically by
`test_classify_usage_role_threshold_precision_recall_meets_target` so a regression surfaces as a number.
Two residual false positives (a term sharing a window with an unrelated comparator+digit; a temporal
"over 4 weeks") are documented as a Known limitation, counted in the metric, and deferred to the
already-planned semantic pass (PRD-OQ-2).

**The lesson worth carrying:** the dangerous surfaces of this feature — identity hashing, verification
inertness, per-row sensitivity, backfill safety, determinism — were done well and verified clean. The
*cheap* surface was done sloppily, and only an adversarial end-of-feature gate that measured rather
than read caught it.

## Process notes

- Two ICA leaves (P1, P3) completed their work but their sessions truncated before emitting a report —
  consistent with the documented long-ICA-session instability. Splitting P2 into three shorter leaves
  avoided the same failure in the highest-risk phase. Disk state and authoritative test runs were used
  in place of the missing reports; no orphaned processes were found in the worktree.
- Claude-native gates hit repeated transient 500s mid-run and were re-dispatched; verdict work was
  never offloaded to ICA to route around the outage.
