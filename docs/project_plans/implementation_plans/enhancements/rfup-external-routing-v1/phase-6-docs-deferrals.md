---
title: "Phase 6: Docs / Deferrals Finalization"
schema_version: 2
doc_type: phase_plan
status: draft
created: '2026-07-22'
updated: '2026-07-22'
feature_slug: rfup-external-routing
feature_version: v1
phase: 6
phase_title: "Docs / deferrals finalization (DOC-006)"
prd_ref: docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
entry_criteria:
  - "P1, P3, P4 (incl. SEAM-001), and P5 all complete"
exit_criteria:
  - "CHANGELOG [Unreleased] entry present"
  - "Both deferred-items triage-table rows have an authored design-spec (deferred_items_spec_refs populated)"
  - "task-completion-validator pass, then end-of-feature karen pass"
related_documents:
  - docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
spike_ref: null
adr_refs:
  - /Users/miethe/dev/homelab/development/pediatric-anemia-site/docs/adr/0008-pathb-hardening-vs-native-adapter.md
charter_ref: null
changelog_ref: CHANGELOG.md
test_plan_ref: null
integration_owner: null
ui_touched: false
target_surfaces: []
seam_tasks: []
owner: null
contributors: []
priority: high
risk_level: low
category: enhancements
tags: [phase-plan, docs, changelog, deferred-items, design-spec]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - CHANGELOG.md
  - docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md
  - docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md
---

# Phase 6: Docs / Deferrals Finalization

**Parent Plan**: [rfup-external-routing-v1.md](../rfup-external-routing-v1.md)
**Wave**: 4 (final — `depends_on: [P1, P3, P4, P5]`)
**Effort**: 3 pts
**Dependencies**: P1, P3, P4 (incl. SEAM-001), P5 all complete
**Agents**: changelog-generator, documentation-writer — **both routed on sonnet, not haiku**

## Phase Overview

**Haiku override (explicit)**: this repo's standard Documentation Finalization phase routes `changelog-generator`/`documentation-writer` on haiku by default (per the implementation-plan-template.md). That default does **not** apply here: haiku-model default agents hard-error in this environment (project memory: `haiku-subagents-inaccessible`). **Every task in this phase routes on sonnet.**

This phase closes out the plan: a CHANGELOG entry covering all five preceding phases' operator-facing changes, and the two deferred-item design-specs required by the Deferred Items Triage Table in the parent plan (DF-RFUP-EXT-01, DF-RFUP-EXT-02).

### Goals

- CHANGELOG `[Unreleased]` entry lands, categorized per `.claude/specs/changelog-spec.md`.
- `docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md` updated **in place** (not replaced) with the P5 verdict and reaffirmed defer-until triggers for the remaining 5 unevaluated adapters.
- New design-spec authored for the ADR-0008 rf-side verdict artifact (PRD OQ-5 resolution).
- Context-file pointers added where P2/P3/P4 change agent-relevant `rf verify` behavior.
- `deferred_items_spec_refs` frontmatter on the parent plan populated with both resulting paths.

## Task Breakdown

| Task ID | Task Name | Description | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------|-------------|-------|--------|--------------|
| P6-001 | CHANGELOG `[Unreleased]` entry | Add an entry covering P1 (test coverage), P2 (schema hard-gate), P3 (auto-strict eligibility default), P4 (new quote-fidelity check), P5 (ADR-0008 verdict) — categorized per `.claude/specs/changelog-spec.md`. | 0.5 pts | changelog-generator | sonnet | adaptive | P1, P3, P4, P5 |
| P6-002 (DOC-006a) | Update `rfup-6-native-discovery-adapters.md` | Update the existing design-spec **in place** with the P5 verdict on `litellm_router` and reaffirmed defer-until triggers for the remaining 5 adapters (`gpt_researcher`, `notebooklm`, `openai_agents`, `paperqa2`, `opencode`) — one shared task covering all 5 in a single update, per parent plan's Deferred Items row DF-RFUP-EXT-01. | 1 pt | documentation-writer | sonnet | adaptive | P5-004 |
| P6-003 (DOC-006b) | Author ADR-0008 verdict design-spec | New `design_spec` at `docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md`, `maturity: shaping`, documenting P5's verdict + install/wiring plan as the durable rf-side artifact — explicitly states the actual ADR-0008 status transition in `pediatric-anemia-site` is out of scope here (seam boundary), per parent plan's Deferred Items row DF-RFUP-EXT-02. | 1 pt | documentation-writer | sonnet | adaptive | P5-004 |
| P6-004 | Context-file pointers | Add ≤3-line CLAUDE.md/key-context pointers for the new `rf verify` gate behavior introduced by P2/P3/P4 (schema hard-gate, eligibility default, fidelity check) — progressive disclosure (pointer only, detail stays in this plan/phase files). | 0.5 pts | documentation-writer | sonnet | adaptive | P3, P4 |
| P6-005 | Finalize plan frontmatter | Set parent plan `status: completed`, populate `commit_refs`/`files_affected`/`updated`, append both DOC-006a/DOC-006b spec paths to `deferred_items_spec_refs`. | 0.5 pts | documentation-writer | sonnet | adaptive | P6-001, P6-002, P6-003, P6-004 |

## Detailed Task Specifications

### Task P6-001: CHANGELOG `[Unreleased]` entry

**Estimate**: 0.5 pts · **Dependencies**: P1, P3, P4, P5

**Acceptance Criteria**:
- [ ] AC-P6-1: Entry exists under `[Unreleased]` with correct categorization per `.claude/specs/changelog-spec.md`.
- [ ] AC-P6-2: Entry covers all five phases' operator-facing behavior (new default-strict passage mode for eligible claims and the new pediatric_cds/quote-fidelity gates are both user-visible `rf verify` behavior changes — call these out explicitly, not just "various improvements").
- [ ] AC-P6-3: `changelog_ref` frontmatter on the parent plan is set to `CHANGELOG.md`.

**Files Involved**:
- `CHANGELOG.md`.

### Task P6-002 (DOC-006a): Update `rfup-6-native-discovery-adapters.md`

**Estimate**: 1 pt · **Dependencies**: P5-004

**Acceptance Criteria**:
- [ ] AC-P6-4: Existing design-spec is **updated in place**, not replaced — its `maturity: idea` framing for the 5 unevaluated adapters is retained/reaffirmed (P5 evaluated only `litellm_router`; this task does not promote the other 5).
- [ ] AC-P6-5: `litellm_router`'s row in the adapter shortlist table (§2 of the existing spec) is updated to reflect P5's verdict, replacing or annotating its current "deferred, no evaluation on file" framing.
- [ ] AC-P6-6: The defer-until trigger (§1 of the existing spec — measured value gap OR security/governance gap) is explicitly reaffirmed as still governing the remaining 5 adapters, unchanged by this plan.
- [ ] AC-P6-7: Resulting path appended to the parent plan's `deferred_items_spec_refs` (satisfies DF-RFUP-EXT-01's Target Spec Path).

**Files Involved**:
- `docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md`.

### Task P6-003 (DOC-006b): Author ADR-0008 verdict design-spec

**Estimate**: 1 pt · **Dependencies**: P5-004

**Acceptance Criteria**:
- [ ] AC-P6-8: New file at `docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md` with `doc_type: design_spec`, `maturity: shaping`, `prd_ref` set to this feature's PRD, `feature_slug: rfup-external-routing`.
- [ ] AC-P6-9: Body documents P5's accept/reject/conditional verdict, rationale, and install/wiring plan (sourced from `.claude/worknotes/rfup-external-routing/litellm-router-eval.md`).
- [ ] AC-P6-10: Explicitly states the rf-side/cross-repo boundary: this artifact is the sole rf-side deliverable; the actual ADR-0008 status transition in `pediatric-anemia-site` is out of scope for this plan (seam boundary + cross-repo write restriction) and is tracked as DF-RFUP-EXT-02 in the parent plan's Deferred Items table.
- [ ] AC-P6-11: Resulting path appended to the parent plan's `deferred_items_spec_refs` (satisfies DF-RFUP-EXT-02's Target Spec Path).

**Files Involved**:
- `docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md` (new).

### Task P6-004: Context-file pointers

**Estimate**: 0.5 pts · **Dependencies**: P3, P4

**Acceptance Criteria**:
- [ ] AC-P6-12: CLAUDE.md (or the relevant key-context file) gains a ≤3-line pointer for the new `pediatric_cds` schema hard-gate, the eligibility-driven strict-passage default, and the quote-fidelity check — pointer only, detail stays in this plan.

**Files Involved**:
- Project CLAUDE.md or `.claude/context/key-context/` (target file at task-executor's discretion, following existing progressive-disclosure convention).

### Task P6-005: Finalize plan frontmatter

**Estimate**: 0.5 pts · **Dependencies**: P6-001, P6-002, P6-003, P6-004

**Acceptance Criteria**:
- [ ] AC-P6-13: Parent plan frontmatter: `status: completed`, `commit_refs` populated, `files_affected` reconciled against what actually changed, `updated` bumped.
- [ ] AC-P6-14: `deferred_items_spec_refs` on the parent plan contains both `docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md` and `docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md`.
- [ ] AC-P6-15: Deferred Items Triage Table in the parent plan: both rows' status reflects the now-authored spec paths (no row left with an unresolved `Target Spec Path` placeholder).

**Files Involved**:
- `docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md` (frontmatter only).

## Quality Gates

This phase — and the feature — is complete when:

- [ ] **Documentation**: CHANGELOG entry present and correctly categorized.
- [ ] **Deferred Items Quality Gate**: both triage-table rows have authored design-specs; `deferred_items_spec_refs` populated.
- [ ] **Findings Gate**: `findings_doc_ref` remains `null` (no findings occurred) OR, if populated during execution, the findings doc is finalized to `status: accepted`.
- [ ] **Reviewer gate**: `task-completion-validator` passes this phase, then the **end-of-feature `karen` pass** runs (parent plan Reviewer Gates — this is the second and final `karen` checkpoint for the whole feature).

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Haiku-routed doc agents hard-error in this environment | Low (already mitigated) | All tasks in this phase explicitly route on sonnet — see phase overview. |
| DOC-006a accidentally promotes the 5 unevaluated adapters out of `idea` maturity | Low | AC-P6-4/AC-P6-6 explicitly require retaining/reaffirming their deferred status. |

## Findings Captured This Phase

- [ ] No new findings this phase (default)

---

**Phase Version**: 1.0 · **Last Updated**: 2026-07-22

[Return to Parent Plan](../rfup-external-routing-v1.md)
