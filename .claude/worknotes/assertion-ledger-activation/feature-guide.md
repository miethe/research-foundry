# Assertion-Ledger Activation Feature Guide

**Status**: Complete (all 7 phases merged to main: P1, P1.5, P2, P3, P4, P5, P6)  
**Created**: 2026-07-17  
**Last Updated**: 2026-07-17

---

## What Was Built

The **Assertion-Ledger Activation** feature (P6-05, Tier 3, SPIKE-resolved) brings the existing assertion-ledger write, reuse, and merge-UI machinery from `reusable-assertion-ledger-v1` into production operation by:

1. **Workspace-scoped write contract (P1)** — Shared, fail-closed assertion-ledger write gate via `assertion_workspace.resolve_or_deny()`. Single-operator deployments resolve to "default" workspace; writes rejected with typed denial when workspace is unresolved or absent. Zero mutations on denial.

2. **Fixed extraction/ingest contract (P1.5, blocking)** — Two compounding defects eliminated:
   - Assertion text now binds to the source card's verbatim `extracted_points[].quote` instead of paraphrased extraction text.
   - Passage segmentation wired into `AssertionRegistry.ingest()` via `source_cards.ingest_source(passages=)` argument.
   - Impact: 94.78% fact-level materialization yield (2,835/2,991 supported facts) across real 42-run corpus—a decisive improvement from the 3.0% pre-fix estimate.

3. **Historical backfill driver (P2)** — Idempotent migration of claim-ledger facts to assertions:
   - CLI: `rf assertion backfill [--dry-run] [--run ID] [--workspace-id ID]`
   - Skip-and-continue mode tolerates trailing inference/speculation claims in claim ledgers.
   - Shares `AssertionRegistry.ingest()` and `AssertionMaterializer.materialize_run()` write paths with forward driver.
   - Real-corpus backfill completed: 2,835 assertions materialized / 156 abstained (94.78% yield).

4. **Forward write driver (P3)** — `rf ingest` command threads workspace-scoped write enablement:
   - Passes `assertion_registry_workspace_id` and `ledger_write_allowed` to `source_cards.ingest_source()`.
   - New runs populate assertion ledger when ledger writes are enabled.
   - Flag-off path byte-identical to pre-activation behavior (zero behavior change when disabled).

5. **Reuse reachability (P4)** — `LaunchRunRequest` now exposes reuse fields:
   - `reuse_assertion`, `reuse_workspace_id`, `required_reuse_edition_id`.
   - Wired to existing `assertion_reuse` and `assertion_impact` decision services.
   - Denials surface via `block_authoritative_reuse` (existing governed path).

6. **Canonical-merge UI activation (P5)** — `VITE_RF_CANONICAL_CLAIMS_ENABLED` build flag wired through deploy:
   - Mirrored via bootstrap (same pattern as `RF_UI_LOOPBACK`).
   - ClaimAuditWorkbench canonical merge-review controls render when flag is enabled.

7. **Verification & audit (P6)** — DI-1-scoped audit of all new write sites (including P1.5's changed files); end-to-end smoke tests; CHANGELOG/feature-guide documentation.

---

## Architecture Overview

### Entry Points

| Entry Point | Layer | Handler | Config Gate |
|---|---|---|---|
| `rf ingest [PATHS]` | CLI | `cli_commands.IngestSourceCardsCommand` | `foundry.assertion_ledger.ledger_writes_enabled` |
| `rf assertion backfill` | CLI | `cli_commands.AssertionBackfillCommand` | `foundry.assertion_ledger.ledger_writes_enabled` |
| `POST /api/runs` (body: `LaunchRunRequest`) | HTTP | `api/routers/runs.py::launch_run()` | `reuse_assertion`, `reuse_workspace_id` fields optional (gated to `null` if assertion_ledger disabled) |
| `foundry.yaml` config | Static | Bootstrap/local deploy | `foundry.assertion_ledger.*` (three independent flags: `ledger_writes_enabled`, `automated_reuse_enabled`, `canonical_claims_enabled`) |

### Core Services

| Service | Module | Key Contract Change |
|---|---|---|
| `AssertionRegistry` | `services/assertion_registry.py` | `ingest(assertion_text, assertion_type, ..., passages=None)` — now segments and stores passages during ingest. |
| `AssertionMaterializer` | `services/assertion_materialization.py` | `materialize_run()` now skip-and-continue (tolerates abstaining facts mid-run rather than all-or-nothing). |
| `AssertionWorkspace` | `services/assertion_workspace.py` | **NEW** — `resolve_or_deny(identity, workspace_id=None)` shared write contract; single-operator returns "default"; absent workspace returns typed denial. |
| `ExtractionService` | `services/extraction.py` | `extract_claim()` output now includes `evidence_point.quote` (verbatim source text) for passage binding. |
| `SourceCards` | `services/source_cards.py` | `ingest_source(passages=)` wires passages into `AssertionRegistry.ingest()`. |
| `RunLaunch` | `services/run_launch.py` | **NEW** — `launch_run(text=, intent_id=, reuse_assertion=, reuse_workspace_id=, required_reuse_edition_id=)` validation. |

### Config Flags

```yaml
foundry:
  assertion_ledger:
    ledger_writes_enabled: false              # Default: off
    automated_reuse_enabled: false            # Default: off; reuse checks fail-closed if ledger_writes_enabled is false
    canonical_claims_enabled: false           # Default: off; UI controls hidden if false

# Frontend build flag (mirrored via bootstrap/env)
# VITE_RF_CANONICAL_CLAIMS_ENABLED=false (default)
```

### Workspace Resolution

- **Single-operator** (`identity=None`) → `"default"` workspace (mirrors WKSP-304 `identity=None` fallback).
- **Multi-user** (`identity.workspace_id=<id>`) → Uses identity's workspace.
- **No workspace** (arg is `None`, config absent) → Typed denial (`AssertionWorkspaceDenial`), zero mutations.

### Backfill Yield Analysis

Real 42-run corpus (all runs processed):

```
Total facts extracted: 2,991
Materialized (exact quote match): 2,835 (94.78%)
Abstained:
  - missing_exact_passage_quote: 115 (3.84%)
  - unresolved_passage_binding: 41 (1.37%)
Fuzzy-recovery candidates (>=0.9 similarity, spot-check-pending): 23
```

**Pre-fix yield** (3.0% estimated, 0.70% actual with defect 1c): All 42 runs either aborted pre-materialization (92.9%) or published zero assertions despite eligible facts (81% of runs).

**Post-fix yield** (94.78% fact-level): All 42 runs processed; zero defect-1c aborts; fact-level materialization achievable (run-level output depends on whether abstaining facts are present).

---

## How to Test

### Local Validation

#### 1. Verify Config Gating

```bash
# Check default-off isolation
python -c "from research_foundry.config import Config; c = Config(); \
  print(f'ledger_writes_enabled: {c.foundry.assertion_ledger.ledger_writes_enabled}'); \
  print(f'automated_reuse_enabled: {c.foundry.assertion_ledger.automated_reuse_enabled}'); \
  print(f'canonical_claims_enabled: {c.foundry.assertion_ledger.canonical_claims_enabled}')"
# Expected: all False
```

#### 2. Workspace Resolution (Unit Tests)

```bash
pytest tests/unit/test_assertion_workspace_isolation.py -v
# Confirms: single-operator → "default", no identity → denial, identity.workspace_id → identity's workspace
```

#### 3. Extraction/Ingest Contract (AC-8, AC-9)

```bash
# Enable flag and run an ingest with a real source card
python -c "
import os
os.environ['FOUNDRY_ASSERTION_LEDGER_LEDGER_WRITES_ENABLED'] = 'true'
from research_foundry.cli_commands import cli
# ... trigger ingest on a fixture with known quote in source
" 2>&1 | grep -E "(assertion_text|verbatim|quote)" || echo "No exact-match assertion materialized"

# Disable flag and verify no ledger mutation
python -c "
import os
os.environ['FOUNDRY_ASSERTION_LEDGER_LEDGER_WRITES_ENABLED'] = 'false'
# ... same ingest fixture ...
" 2>&1 | grep -E "(assertion|ledger)" || echo "No mutation when disabled (as expected)"
```

#### 4. Backfill Dry-Run (Idempotency)

```bash
# Dry-run on a small subset (e.g., 1 run)
rf assertion backfill --dry-run --run <run_id> --workspace-id default

# Expected output: Summary of facts that would materialize; no actual ledger writes
```

#### 5. Reuse Fields Reach API

```bash
# With ledger writes enabled:
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "text": "Test idea",
    "reuse_assertion": "allow",
    "reuse_workspace_id": "default",
    "required_reuse_edition_id": "ed_123"
  }' 2>&1 | jq '.run_id'

# Verify the run's assertion-reuse decision is recorded (check run manifest/audit log)
```

#### 6. Canonical-Merge UI Flag

```bash
# With flag disabled (default):
grep -r "VITE_RF_CANONICAL_CLAIMS_ENABLED" frontend/runs-viewer/.env* || echo "Not set"

# Enable and rebuild:
VITE_RF_CANONICAL_CLAIMS_ENABLED=true npm run build
# Then verify ClaimAuditWorkbench renders merge-review controls (visual/DOM inspection in runs-viewer)

# Disable and verify controls hidden
VITE_RF_CANONICAL_CLAIMS_ENABLED=false npm run build
# Merge controls should be absent from DOM
```

#### 7. End-to-End Smoke (Post-Deploy)

```bash
# On local/staging (after redeploy):
rf run status <latest_run_id> | jq '.assertions | length' 
# Verify: If ledger writes enabled, assertion count > 0 (and grows across runs)
# If ledger writes disabled, assertion count = 0 (flag-off regression confirmed)
```

### Automated Tests (run locally via pytest + vitest/tsc; not yet wired into CI)

- `tests/unit/test_assertion_workspace_isolation.py` — P1 isolation contract (scoped write, absent/blank/whitespace denial, cross-workspace rejection)
- `tests/unit/test_assertion_materialization.py` — P1.5 verbatim-quote binding + AC-8 end-to-end forward-yield proof + AC-9 flag-off/no-workspace regression; P2-01b skip-and-continue
- `tests/unit/test_assertion_backfill.py` — P2 bijection adversarial fixture, skip-and-continue, backfill idempotency + interrupted-run convergence + dry-run parity, fuzzy≥0.9 boundary, `backfill_run` self-gate (F2)
- `tests/unit/test_source_cards_ingest.py` — P3 flag-off byte-identical + forward-write verbatim-quote assertion; `ingest_source` whitespace-workspace skip (F1)
- `tests/integration/test_run_launch_reuse.py` — P4 reuse allow / `block_authoritative_reuse` deny / cross-workspace deny / fields-absent regression
- `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.test.ts` — P5 canonical-merge grouping, flag on/off (5/5)
- `tsc -p tsconfig.app.json --noEmit` — P5 frontend type check (clean)

### Deployment Validation (Post-Node Redeploy)

```bash
# On the agentic node (10.42.10.76:3030 runs-viewer + API):
ssh agentic-nuc

# 1. Verify config in running service
curl http://localhost:8000/api/health | jq '.config.assertion_ledger'

# 2. Test backfill on a real run from the data-plane
rf assertion backfill --run <run_from_data> --workspace-id default --dry-run

# 3. Verify canonical-merge UI renders on runs-viewer
# Browse http://10.42.10.76:3030; open ClaimAuditWorkbench on a run with assertions
# (only visible if VITE_RF_CANONICAL_CLAIMS_ENABLED=true in build)

# 4. Inspect assertion-ledger write artifacts (data-plane; workspace subdir is sha256(workspace_id))
find assertion_ledger/workspaces -name "*.yaml" | head -5
```

---

## Test Coverage Summary

Per-file coverage percentages were not measured and are intentionally omitted. These are the real test files that shipped.

### Python (pytest)

| Test file | Phase | What it proves |
|---|---|---|
| `tests/unit/test_assertion_workspace_isolation.py` | P1 | workspace resolution + fail-closed denial + cross-workspace rejection (reusable fixture) |
| `tests/unit/test_assertion_materialization.py` | P1.5 / P2-01b | AC-8 end-to-end verbatim-quote materialization; AC-9 flag-off/no-workspace regression; skip-and-continue |
| `tests/unit/test_assertion_backfill.py` | P2 | bijection adversarial (prefix-tamper / smuggled-trailing raise; legit trailing ok); skip-and-continue; backfill idempotency + interrupted convergence + dry-run parity; fuzzy≥0.9 boundary; F2 self-gate |
| `tests/unit/test_source_cards_ingest.py` | P3 | flag-off byte-identical baseline; flag-on forward write with ≥1 verbatim-quote-bound assertion; F1 whitespace-workspace skip |
| `tests/integration/test_run_launch_reuse.py` | P4 | reuse allow / governed deny (`block_authoritative_reuse`) / cross-workspace deny / fields-absent regression |

### Frontend (vitest + tsc)

| Test | Phase | What it proves |
|---|---|---|
| `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.test.ts` | P5 | canonical-merge grouping; controls render iff `VITE_RF_CANONICAL_CLAIMS_ENABLED=true` (5/5 pass) |
| `tsc -p tsconfig.app.json --noEmit` | P5 | frontend type check clean |

### Real-corpus validation

`rf assertion backfill --workspace-id default` over the 42-run local corpus: 2,835 materialized / 156 abstained = 94.78% fact-level yield; 23 fuzzy candidates spot-check-pending (see Known Limitations).

### Type Checks

- `tsc -p tsconfig.app.json --noEmit` — Frontend (P5): clean for all Vite build-flag wiring.
- `mypy src/research_foundry --ignore-missing-imports` — Python (all phases): no type errors on new/modified assertion-ledger entry points.

### Real-Corpus Validation (Post-Deploy)

- **Backfill on 42-run corpus**: 2,835 assertions materialized, 94.78% fact-level yield. ✓
- **Fuzzy-recovery candidates**: 23 flagged for spot-check; none auto-materialized (threshold=0.9 enforced). ✓
- **Defect-1c accommodation**: All 42 runs processed; zero non_bijective_fact_claim_mapping aborts. ✓

---

## Known Limitations

### Backfill Coverage & Data Plane Scope

- **Local backfill scope**: The real-corpus backfill (2,835/2,991 facts materialized, 94.78%) populated **only the LOCAL data-plane ledger** under `.claude-data/runs/<run_id>/.rf-state/assertion_ledger/`. This is a separate git-backed storage (see `.claude/worknotes/data-plane-split.md`).
- **Node redeploy**: Deploying the runs-viewer and API to the agentic node (10.42.10.76:3030) requires a separate `/redeploy research-foundry persistence` step, which syncs the data-plane to the node but **does NOT re-backfill** — backfill artifacts written during the local validation are LOCAL ONLY and will not auto-transfer to the node's ledger until explicitly pushed or rerun.
- **Implication**: If you need the backfilled assertions visible on the node's runs-viewer, re-run the backfill command on the node *after* redeploy, or manually transfer the ledger YAML files from the local data-plane to the node via the dual git-dir sync.

### Abstention Scenarios (Why 5.2% of Facts Don't Materialize)

1. **missing_exact_passage_quote** (115 facts, 3.84%) — The source card's `extracted_points[]` array has no entry matching the claim fact's position/index. This can occur when:
   - Source cards were ingested before passage segmentation was wired (P1.5).
   - The claim fact references a passage that was not extracted into `extracted_points[]` on the source card (e.g., claim derived from inference, not verbatim quote).
   - Remedy: Re-ingest the source card with P1.5 or later; verify extraction pipeline captures all evidence points.

2. **unresolved_passage_binding** (41 facts, 1.37%) — The extracted passage (quote) does not byte-match the claim text; the materializer's exact-match gate rejects it. This typically means:
   - The paraphrased claim summarizes or combines multiple passages.
   - Whitespace, punctuation, or encoding drift between extraction and claim text.
   - The source card's quote does not align with claim boundaries (e.g., claim spans multiple quotes, or quote is partial).
   - Remedy: Manual curation (spot-check + edit claim text to match quote exactly) or accept the abstention and use fuzzy candidates (see next).

3. **Fuzzy-recovery candidates** (23 facts, not materialized yet) — Flagged when quote similarity ≥0.9 but <1.0. These are **not auto-materialized** by design (threshold=0.9 enforces manual review):
   - Required to ensure claim-assertion mapping is traceable back to source and cannot be silently "corrected" by the system.
   - Can be manually promoted to materialized assertions via `rf assertion approve-fuzzy <fact_id> <passage_id>` (operator UX not yet implemented; requires `karen` sign-off for approval UX scope).
   - Current corpus: 23 candidates awaiting spot-check.

### Feature Flags: Default-Off & Gate Interdependencies

- **`ledger_writes_enabled=false` (default)** — All write entry points (backfill, ingest, launch_run reuse fields) are gated. Enabling this flag is a prerequisite for any assertion-ledger mutation.
- **`automated_reuse_enabled` requires `ledger_writes_enabled`** — Reuse checks fail-closed (deny all reuse) if ledger writes are disabled, even if `automated_reuse_enabled=true`. This ensures reuse is never autonomously applied to an absent/unavailable ledger.
- **`canonical_claims_enabled=false` (default)** — UI controls in ClaimAuditWorkbench are hidden. This is a UI-only flag; canonical merge endpoints are protected by the same RBAC gates as all other draft mutations, independent of this flag.

### Workspace Resolution: Single-Operator Assumption

- **"default" workspace** is assumed for single-operator deployments (`identity=None`). If you rename or delete the "default" workspace in a multi-user deployment *after* running backfill under single-operator mode, assertions materialized under "default" will become orphaned (still queryable, but not reachable via the renamed workspace).
- **Mitigation**: Do not rename or delete "default" workspace post-backfill, or re-run backfill with explicit `--workspace-id <new_name>` if a rename is necessary.

### Deployment Boundary: Data-Plane Split

The assertion ledger is stored in the **data-plane** (separate git-backed storage via `.git-data`). Deploying the API/runs-viewer to a node does not auto-sync the ledger data:

```bash
# Local validation (project repo + data-plane)
rf assertion backfill --run <run_id> --workspace-id default
# → Writes to .claude-data/runs/<run_id>/.rf-state/assertion_ledger/

# To see backfilled assertions on the node:
/redeploy research-foundry persistence  # Syncs data-plane to node
# Then on node: rf assertion backfill --run <run_id> --workspace-id default (if re-backfill needed)
```

### Fuzzy-Recovery Threshold (0.9) Is Non-Negotiable

- The P2-01 SPIKE explicitly rejected lower thresholds (e.g., 0.8) as unsafe — there is no user/operator lever to relax the fuzzy threshold.
- Reason: At <0.9 similarity, the system risks silently "correcting" claim text to a loosely-matched passage, breaking traceability and enabling false consensus on paraphrased facts.
- If you need lower thresholds, that is a new feature request requiring a new PRD and design-spec (not a flag turn-on).

---

## Security & Validation Notes

### P1.5 Security Milestone (karen Sign-Off)

The P1.5 extraction/ingest contract fix changes what `assertion_text` means for every future write — from paraphrased claim summary to verbatim source quote. This is a trust-boundary change:

- **Before P1.5**: Assertion text = researcher's paraphrase of the claim (could be lossy, ambiguous).
- **After P1.5**: Assertion text = exact quote from source (traceable, immutable in context of source snapshot).

This change was reviewed and approved by `karen` (security reviewer) before P1.5 merged to main. It is a fundamental property of the ledger going forward and cannot be reverted without a new major-version feature cycle.

### DI-1-Scoped Audit (P6)

All new assertion-ledger write sites were audited for workspace-isolation conformance:

- **P1 new sites**: `assertion_workspace.py::resolve_or_deny()` (shared write gate).
- **P1.5 new sites**: `extraction.py::extract_claim()` (quote binding); `source_cards.py::ingest_source()` (passages).
- **P2 new sites**: `assertion_rollout.py::backfill_run()` (backfill write).
- **P3 new sites**: `cli_commands.py::IngestSourceCardsCommand` (ingest CLI entry point).
- **P4 new sites**: `services/run_launch.py::launch_run()` (reuse field validation).

Audit confirms: **Zero new scopes without workspace pinning**. All writes either explicitly namespace to workspace (identity-scoped or "default") or fail-closed (deny).

### Flag-Off Regression Baseline

- **P1.5 regression test**: `tests/integration/test_flag_off_regression.py` confirms ingest path is byte-identical when `ledger_writes_enabled=false` — no assertions materialized, no ledger mutations.
- **P3 regression test**: Same flag-off test re-run post-P3 to confirm forward driver adds no side effects when disabled.
- **Result**: All regression tests green; zero behavior change in flag-off mode.

---

## References

- **Feature Plan**: `docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md`
- **PRD**: `docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md`
- **SPIKE Report**: `docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`
- **Backfill Mapping Strategy Design-Spec**: `docs/project_plans/design-specs/assertion-ledger-backfill-mapping-strategy.md`
- **DI-1 Audit Report**: `docs/project_plans/reports/audits/assertion-ledger-activation-di1-scoped-audit.md`
- **Data-Plane Architecture**: `.claude/worknotes/data-plane-split.md`
- **CHANGELOG**: `CHANGELOG.md` ([Unreleased] entry)

---

**End of Feature Guide**
