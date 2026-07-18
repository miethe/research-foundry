---
type: context
prd: "rf-upstream-evidence-foundry"
title: "rf Upstream Evidence Foundry - Development Context"
status: "active"
created: "2026-07-18"
updated: "2026-07-18"
critical_notes_count: 0
implementation_decisions_count: 4
active_gotchas_count: 0
agent_contributors: []
---

# rf Upstream Evidence Foundry - Development Context

**Status**: Active Development
**Created**: 2026-07-18
**Last Updated**: 2026-07-18

> **Purpose**: Shared worknotes for all AI agents working on RFUP (rf Upstream Evidence Foundry). This is the sticky-note pad documenting key decisions, gotchas, and integration patterns discovered during development.

---

## Quick Reference

**Plan ID**: IMPL-2026-07-18-RF-UPSTREAM-EVIDENCE-FOUNDRY
**Total Effort**: 29 pts across 6 phases
**Timeline**: ~4-5 weeks (single-track sequential-plus-parallel)
**Phases**: P1 (schema versioning) → P2 (verify gating) → P3 (PDF adapter) → P4 (council + lineage) → P5 (workflow params) → P6 (validation/docs)
**Wave Structure**: [P1] → [P2, P3, P4] → [P5] → [P6]

**Related Documents**:
- PRD: `docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md`
- Decisions Block: `.claude/worknotes/rf-upstream-evidence-foundry/decisions-block.md`
- Current State: `.claude/worknotes/rf-upstream-evidence-foundry/current-state.md`
- Human Brief: `docs/project_plans/human-briefs/rf-upstream-evidence-foundry.md`

---

## Implementation Decisions

### 2026-07-18 - Opus - RFUP-6 explicitly deferred

**Decision**: Native discovery adapters (RFUP-6) are NOT part of this implementation. They are explicitly deferred pending a measured value/security gap.

**Rationale**: Per IntentTree node text: only evaluate after measuring actual value/security impact. Today 0/6 live non-`arc_council` adapters are installed. Path-B (RFUP-1, in scope) is the proven live-discovery lane.

**Location**: Implementation plan §Decisions, Phase 6 TASK-6.4

**Impact**: Phase 6 includes a design-spec authoring task that documents the defer-until trigger and adapter shortlist. No code changes for RFUP-6.

---

### 2026-07-18 - Opus - verify.exact_passage defaults to `warn`, not `strict`

**Decision**: The `verify.exact_passage` config key defaults to `warn` mode, NOT `strict`. Strict is opt-in per run/profile.

**Rationale**: HIGH risk hotspot — strict mode could regress the 2,835-assertion real corpus if enabled by default. Risk mitigation via TASK-2.3: real-corpus regression test in default mode asserts zero new failures.

**Location**: Phase 2 TASK-2.1, Risk Mitigation table

**Impact**: Evidence Foundry (downstream consumer) opts into strict per-run/profile. Default behavior is backward-compatible.

---

### 2026-07-18 - Opus - Hard seam boundary: FHIR/DSL/signing stay downstream

**Decision**: FHIR mapping, clinical rule DSL, and claim/bundle signing remain DOWNSTREAM in pediatric-anemia-site. Research Foundry owns only "evidence → verified claim".

**Rationale**: Clear scope boundary. RF controls evidence (verify, fetch, seal). CDS converter controls verified claim → executable rule → signed release.

**Location**: Implementation plan §Decisions

**Impact**: No auth/sign/FHIR logic in rf code. Pipeline stays evidence-focused.

---

### 2026-07-18 - Opus - Phase 1 machine contract FIRST

**Decision**: Phase order is P1 (machine contract) → P2-P4 → P5 → P6. P1 lands first so P2-4 emit new fields under an already-stamped schema.

**Rationale**: Avoids re-stamping fields added before the version constant exists. Simplifies schema evolution.

**Location**: Implementation plan §Architecture Sequence, wave_plan

**Impact**: P1 must complete in wave 1 before P2-4 start in wave 2.

---

## Critical Implementation Notes

### Phase 1: Machine Contract (RFUP-4)

**Key Surface**: The `RF_SCHEMA_VERSION` constant is the single source of truth. It must be stamped on:
1. CLI `--json` outputs
2. Verify output YAML/JSON
3. LAN API payloads (`/api/runs`, `/api/reports`, `/api/catalog`)
4. Run export (check `run-export.ts` dual-update rule)

**No Behavior Change**: Phase 1 is pure stamping — verify/fetch/council behavior unchanged until Phase 2-4.

---

### Phase 2: Verify Gating (RFUP-3)

**High-Risk**: The `verify.exact_passage: warn|strict` flag is BOTH config default AND run-level CLI override. Run-level wins on conflict.

**Regression Test Critical**: TASK-2.3 must run default-mode verify over 2,835 assertions + prior runs and assert **zero new failures**.

---

### Phase 3: PDF Extraction (RFUP-2)

**Optional Extra**: `pypdf` installed as `research-foundry[pdf]`. No PDF dependency in `pyproject.toml` today.

**Graceful Degrade**: When `pdf` extra absent OR extraction fails, degrade to `locator_only` (not exception). The `extraction_status: full_text|partial|locator_only` field replaces the implicit `degraded` boolean.

**Governance Gate Ordering**: PDF extraction runs BEFORE sensitivity + secret-scan gate. TASK-3.4 must verify and add synthetic-secret test.

---

### Phase 4: Council + Lineage (RFUP-5, RFUP-7)

**4a (Council Normalization)**: Free-form `verdict` → enum `approve|concern|block`. Unparseable → `concern` + `normalization_confidence: low`. Raw text ALWAYS retained (non-destructive).

**4b (Run Lineage)**: Seal trigger is additive flag on existing finalize/export path (not new `rf seal` command unless exploration finds no attach point). Append-only by design. Reuses `services/assertion_registry.py`'s atomic-write pattern.

---

### Phase 5: Workflow Parameterization (RFUP-1)

**Current State**: `.claude/workflows/rf-run-execute.js` has hard-coded paths (lines 18-20). Phase 5 replaces with configurable args, defaulting to current behavior.

**Date Stamp**: Line 21 bakes `20260613` into `source_card_id` generation. TASK-5.2 replaces with run-date computed at invocation.

**Four-Constraints Checklist**: Re-run workflow-authoring checklist post-refactor. Preserve TMP→cp write-safety pattern unchanged.

---

### Phase 6: Validation & Docs

**Quality Gate Chain**: Phase 6 cannot be sealed until:
1. TASK-6.4 (deferred items) completed
2. AND (`findings_doc_ref` remains null OR findings doc has `status: accepted`)

**Validator Gates**: `task-completion-validator` every phase + `karen` milestone after Phase 3 and Phase 6.

---

## Known Gotchas

### Serialization Note: P1 & P2 both touch services/verification.py

**Solution**: Not a hard conflict. P1 completes in wave 1 BEFORE P2 starts in wave 2. Phase 2 rebases on P1's stamped schema.

---

### runs-viewer Dual-Update Rule (Phase 1)

**Expected Outcome**: Phase 1 expects NO new field addition to output structure (only version stamped on existing fields), so **no 1.6 bump expected**.

---

### OQ-2 Fallback Path (Phase 4)

**Fallback**: If no clean existing attach point for seal trigger, fall back to new `rf seal` command. Flag deviation in TASK-4.2 Completion Report.

---

## References

**Commands**:
```bash
# Phase 1 contract tests
./.venv/bin/python -m pytest -k contract_drift

# Phase 2 exact-passage tests
./.venv/bin/python -m pytest -k exact_passage

# Phase 3 PDF tests
./.venv/bin/python -m pytest -k pdf_extraction

# Phase 4 council/seal tests
./.venv/bin/python -m pytest -k "run_seal or council_verdict"

# Phase 5 JS validation
node --check .claude/workflows/rf-run-execute.js

# Full regression (Phase 6)
./.venv/bin/python -m pytest
```

---

**Last Updated**: 2026-07-18
