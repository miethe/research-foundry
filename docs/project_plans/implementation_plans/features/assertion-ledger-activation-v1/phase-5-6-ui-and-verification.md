---
title: "Phase 5-6: Canonical-Merge UI Activation & Verification/Audit/Docs"
schema_version: 2
doc_type: phase_plan
it_schema: 1
status: draft
created: 2026-07-15
phase: P5-P6
phase_title: "Canonical-merge UI activation; verification, DI-1-scoped audit, docs"
feature_slug: assertion-ledger-activation
prd_ref: docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md
entry_criteria: ["P5: none (independent)", "P6: P1.5, P2, P3, P4, P5 all complete"]
exit_criteria: ["P5: merge UI renders against populated ledger on :3030, tsc clean", "P6: karen feature-end sign-off, DI-1-scoped audit artifact accepted"]
---

# Phase 5: Canonical-Merge UI Activation & Phase 6: Verification, DI-1-Scoped Audit, Docs

[<- Back to parent plan](../assertion-ledger-activation-v1.md)

---

## Phase 5: Canonical-Merge UI Activation (2 pts)

Frontend-only. Not Mode-D (no workspace-write surface -- this phase only activates a build-time flag and verifies existing UI).

**Duration**: ~1-2 days
**Dependencies**: None (wave 1, independent of P1-P4)
**Assigned Subagent(s)**: ui-engineer
**Model default**: sonnet | **Effort default**: adaptive

### R-P4 Check (UI-touching phase)

`files_affected` includes `.tsx` (`ClaimAuditWorkbench.tsx`). **R-P4 triggers** -- the runtime smoke task lives in the verification phase (P6-02 below), referencing this phase's `target_surfaces`.

### OQ-4 Resolution

Resolved inline (not deferred to a standalone design-spec): verify against **real backfilled data when P2 has landed** (post-P2, populated ledger); if P2's mapping-strategy decision (P2-01) yields a low real-data volume before this phase executes, a **synthetic fixture is acceptable** for the build-flag activation check itself (P5-02's first half), but the AC-6 `visual_evidence_required` screenshots must still be captured against whatever data is available at execution time, with the source (real vs. fixture) stated explicitly in the screenshot caption/PR description.

### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P5-01 | Wire `VITE_RF_CANONICAL_CLAIMS_ENABLED` into deploy | Set `VITE_RF_CANONICAL_CLAIMS_ENABLED=true` through the standard deploy/bootstrap path, mirroring the existing `RF_UI_LOOPBACK` pattern. Note: the actual bootstrap script lives outside this repo (agentic-node deploy tooling); this task lands the env-var name/plumbing convention here and coordinates the bootstrap-side edit as a linked follow-up, documented in P6-05. | Deploy flag documented alongside `RF_UI_LOOPBACK`; build picks up the flag when set. | 1 pt | ui-engineer | sonnet | adaptive | None |
| P5-02 | Build + verify merge-review controls | Build runs-viewer with the flag on; verify merge-review controls render against populated ledger data (real if P2 has landed by this point, else a documented synthetic fixture per the OQ-4 resolution above). Capture desktop >=1440px screenshots with flag on (populated) and flag off (absent), per AC-6's `visual_evidence_required`. | AC-6 target_surfaces: [frontend/runs-viewer/src/lib/canonicalClaimsFlag.ts, frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx]. propagation_contract: with the flag true (set via P5-01), merge-review controls render against a populated ledger on :3030. resilience: with the flag false/unset, merge controls are absent (matches v1's existing behavior). visual_evidence_required: "Desktop >=1440px screenshot, flag on (populated) and flag off (absent)." verified_by: [P5-02, P6-02]. | 1 pt | ui-engineer | sonnet | adaptive | P5-01 |

**Phase 5 total: 2 pts.**

### Quality Gates

- [x] `tsc -p tsconfig.app.json --noEmit` clean. Re-verified 2026-07-17 after the
      P5-02 merge-review control landed.
- [x] Screenshots captured (flag on/off) per AC-6. Desktop 1440x900, run
      `rf_run_20260613_what_is_the_current_release_state` with a documented
      synthetic canonical-grouping fixture (3 claims, `ccl_fixture_p5_merge_demo`)
      patched into the gitignored `public/data/` local static copy (per OQ-4's
      permitted-fixture resolution — real backfill data does not exist yet;
      P2/Wave 2 has not landed). See
      `docs/project_plans/design-specs/assets/assertion-ledger-activation-v1/verification-p5-canonical-claims-flag-on.png`
      and `verification-p5-canonical-claims-flag-off.png`.
- [x] Deploy-flag documentation drafted (finalized in P6-05). See
      `frontend/runs-viewer/README.md` ("Canonical-claim merge review" +
      "Deploy-flag wiring (agentic-node bootstrap)" sections). The bootstrap-side
      mirror of `RF_UI_LOOPBACK` (in `agentic_meta_dev/infra/agentic-node/bootstrap-agentic-node.sh`,
      a separate repo) is explicitly NOT landed by this phase — tracked as a
      cross-repo follow-up for P6-05, not silently assumed done.
- [ ] `task-completion-validator` passes P5. Not yet run — do not treat the three
      checked items above as a substitute for this separate reviewer gate.

### P5-02 implementation note (2026-07-17)

The merge-review control did not previously exist anywhere in
`ClaimAuditWorkbench.tsx` (confirmed via `git log --all -- <the two target
files>`; the last touch to both was `b0e923b`, the prior reviewer-experience
feature, not this one). This pass added it: `ClaimInspector` now renders a
"Canonical Claim" section (chip + ID/version + sibling-claim list) when
`isCanonicalClaimsEnabled()` is true AND the selected claim's
`persistent_references.canonical_claim_id` is present; sibling claims are
derived client-side from the already-loaded `run.claims` (no new API/fetch).
Absent otherwise — never a disabled/empty control, per
`reusable-assertion-ledger-reviewer-experience-v1.md` §7. Covered by a unit
test for the pure `deriveCanonicalMergeGroup()` helper
(`ClaimAuditWorkbench.test.ts`) and the two screenshots above.

### Key Files

`frontend/runs-viewer/src/lib/canonicalClaimsFlag.ts`, `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx`, `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.test.ts` (new), `frontend/runs-viewer/README.md`.

---

## Phase 6: Verification, DI-1-Scoped Audit, Docs (3 pts)

**karen feature-end gate.** Not itself Mode-D (no new writes), but gates the Mode-D phases (P1-P4) closed.

**Duration**: ~2 days
**Dependencies**: P2, P3, P4, P5 all complete
**Assigned Subagent(s)**: senior-code-reviewer, task-completion-validator, karen, ui-engineer, documentation-writer, changelog-generator
**Model default**: sonnet (haiku for docs; karen on opus) | **Effort default**: adaptive

### R-P3 Check

Reviewer/validator/karen agents overlap on the audit artifact conceptually, but none of them are "builders" with overlapping `files_affected` in the R-P3 sense (they read diffs and produce a review, not a co-authored source file). documentation-writer and changelog-generator both touch `CHANGELOG.md`/docs but sequentially, not concurrently (P6-05 is one task). **R-P3 does not trigger a distinct `integration_owner`** beyond what P2/P4 already declared.

### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P6-01 | DI-1-scoped audit of new write sites | Enumerate every write call site introduced by P1.5/P2/P3/P4 (`assertion_materialization.py`, `extraction.py`, `assertion_rollout.py`, `source_cards.py`, `run_launch.py`) against the WKSP-304 confinement/fail-closed contract from P1. Produce `docs/project_plans/reports/audits/assertion-ledger-activation-di1-scoped-audit.md`. The artifact MUST state its scope boundary explicitly -- this feature's new-write-site delta only, not a full-project DI-1 closure claim (avoid repeating the WKSP-304 AAR's false-completeness incident). Additionally confirm P1.5's contract-fix change does not itself introduce an unscoped write path (it changes what gets written, not where -- but this must be verified, not assumed). | AC-7 target_surfaces: [src/research_foundry/services/assertion_materialization.py, src/research_foundry/services/extraction.py, src/research_foundry/services/assertion_rollout.py, src/research_foundry/services/source_cards.py, src/research_foundry/services/run_launch.py]. propagation_contract: every write call site introduced by P1.5/P2/P3/P4 is enumerated and reviewed against the confinement/fail-closed contract. resilience: audit artifact states its scope boundary explicitly. visual_evidence_required: false. verified_by: [P6-01, P6-04]. | 1 pt | senior-code-reviewer | sonnet | extended | P1.5, P2, P3, P4 complete |
| P6-02 | Runtime smoke (R-P4 requirement) | End-to-end smoke test on the deployed runs-viewer: the Catalog "Source assertions" default tab renders backfilled + forward-written data; the canonical-merge UI renders/hides correctly per the flag. References every `target_surfaces` entry from Phase 5's AC-6. | AC-6 (see P5-02); this task is AC-6's second `verified_by` anchor -- runtime, not just build-time, verification. target_surfaces: [frontend/runs-viewer/src/lib/canonicalClaimsFlag.ts, frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx] plus the Catalog default-tab surface. | 0.5 pt | ui-engineer | sonnet | adaptive | P5, P2/P3 complete (for populated data) |
| P6-03 | task-completion-validator pass across P1-P5 (incl. P1.5) | Aggregate review of completion evidence across all six prior phases (P1, P1.5, P2, P3, P4, P5) before the karen feature-end gate. | All six phases' quality-gate checklists confirmed complete or explicitly N/A with rationale. | 0.5 pt | task-completion-validator | sonnet | adaptive | P1-P5 (incl. P1.5) complete |
| P6-04 | karen feature-end gate | Sign off on AC-1 through AC-9 evidence, the DI-1-scoped audit (P6-01, now including P1.5), the P2-01 SPIKE decision record, and -- specifically -- P1.5's yield-reconciliation note (does Phase 2's actual measured backfill yield match, exceed, or fall short of the SPIKE's ~6.8% estimate, and was that reported transparently). Do not summarize a non-clean result as a pass. | karen recommendation posted verbatim; feature is not "done" until this gate clears. | 0.5 pt | karen | opus | adaptive | P6-01, P6-02, P6-03 |
| P6-05 | CHANGELOG + docs | `[Unreleased]` CHANGELOG entry (per `.claude/specs/changelog-spec.md`); operator command docs for `rf assertion backfill` (usage, flags, idempotency guarantee, and the documented exact-match-eligible coverage caveat from P2-01); `VITE_RF_CANONICAL_CLAIMS_ENABLED` deploy doc alongside the existing `RF_UI_LOOPBACK` doc, including the cross-repo bootstrap-script coordination note from P5-01. | Doc Acceptance checklist items in the PRD §11 all checked; `changelog_ref` frontmatter set to `CHANGELOG.md`. | 0.5 pt | changelog-generator, documentation-writer | haiku | adaptive | P6-04 |

**Phase 6 total: 3 pts.**

### Quality Gates

- [ ] DI-1-scoped audit artifact exists, scope-bounded explicitly, covers P1.5's write-binding change, and is linked from the parent plan.
- [ ] Runtime smoke green (Catalog default tab + merge UI, both flag states).
- [ ] `task-completion-validator` aggregate pass across P1-P5 (incl. P1.5).
- [ ] **karen** feature-end sign-off recorded verbatim, including explicit disposition of P1.5's yield-reconciliation note.
- [ ] CHANGELOG `[Unreleased]` entry present.
- [ ] Deploy-flag doc updated alongside `RF_UI_LOOPBACK`.
- [ ] `deferred_items_spec_refs` and `findings_doc_ref` frontmatter in the parent plan finalized per the Deferred Items & In-Flight Findings quality gate.

### Key Files

`CHANGELOG.md`, `docs/project_plans/reports/audits/assertion-ledger-activation-di1-scoped-audit.md` (new), plus any user/dev docs touched by P6-05.
