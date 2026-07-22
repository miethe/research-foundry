---
title: "Phase 5: Native-Adapter SPIKE + ADR-0008 Verdict (Eval-Only)"
schema_version: 2
doc_type: phase_plan
status: draft
created: '2026-07-22'
updated: '2026-07-22'
feature_slug: rfup-external-routing
feature_version: v1
phase: 5
phase_title: "Native-adapter SPIKE + ADR-0008 verdict (eval-only)"
prd_ref: docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
entry_criteria: []
exit_criteria:
  - "Accept/reject verdict recorded with an install/wiring plan"
  - "0 live external calls, 0 credentials used during evaluation"
  - "task-completion-validator pass"
related_documents:
  - docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
spike_ref: null
adr_refs:
  - /Users/miethe/dev/homelab/development/pediatric-anemia-site/docs/adr/0008-pathb-hardening-vs-native-adapter.md
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: null
ui_touched: false
target_surfaces: []
seam_tasks: []
owner: null
contributors: []
priority: high
risk_level: medium
category: enhancements
tags: [phase-plan, spike, adapter-eval, adr-0008, litellm-router]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - .claude/worknotes/rfup-external-routing/litellm-router-eval.md
---

# Phase 5: Native-Adapter SPIKE + ADR-0008 Verdict (Eval-Only)

**Parent Plan**: [rfup-external-routing-v1.md](../rfup-external-routing-v1.md)
**Wave**: 1 (∥ P1, no shared files)
**Effort**: 5 pts
**Dependencies**: None
**Agents**: spike-writer (primary, opus, adaptive), search-specialist (secondary — prior-art, sonnet, adaptive)

## Phase Overview

This phase **is** the plan's Tier-3 SPIKE-equivalent (per Hard Constraint 2 / the PRD's "no fresh pre-PRD SPIKE" decision — items 1-3's design is already settled; item 4 is the one genuine research unknown, delivered *as* this phase). It evaluates `litellm_router` — the only one of the 6 non-`arc_council` adapters this plan evaluates — and produces an accept/reject verdict against ADR-0008 (`pediatric-anemia-site`, currently `proposed`).

**Hard Constraint 2 governs this entire phase**: EVAL-ONLY. No install, no live external calls, no credentials. The ADR-0008 accept/reject verdict is the sole deliverable. Any install is a separate future feature, gated on this verdict.

### Goals

- Resolve the evaluation method (parent plan decision: static-only — PyPI/GitHub metadata review + `pip download --no-deps` dependency-tree/code-surface inspection).
- Produce a citable, non-hand-wavy accept/reject verdict on ADR-0008.
- Produce an (unexecuted) install/wiring plan artifact, so a future feature can act on an "accept" verdict without re-deriving the plan.
- Zero live network calls beyond what PyPI/GitHub metadata review and `pip download` themselves require (both are read-only package-index operations, not credentialed or provider-API calls — see Security note below).

## Task Breakdown

| Task ID | Task Name | Description | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------|-------------|-------|--------|--------------|
| P5-001 | Static metadata review | PyPI/GitHub metadata review of `litellm`: maintainer activity, release cadence, CVE history (via public advisory databases, no auth), dependency count. | 1 pt | spike-writer, search-specialist | opus (spike-writer), sonnet (search-specialist) | adaptive | None |
| P5-002 | `pip download --no-deps` inspection | Run `pip download --no-deps litellm` to obtain the wheel/sdist without installing; inspect the package's declared dependency tree (`METADATA`/`requires.txt`) and top-level code surface (module list, no import/execution) to assess security posture and integration weight. | 1 pt | spike-writer | opus | adaptive | P5-001 |
| P5-003 | Cross-reference existing `litellm_router.py` adapter | Review the already-landed `litellm_router.py` (including the `2d198a8` ICA-provider mapping fix, pre-dates this branch) against the P5-001/P5-002 findings to assess integration weight if accepted (what's already wired vs. what installing `litellm` itself would newly expose). | 1 pt | spike-writer | opus | adaptive | P5-002 |
| P5-004 | Accept/reject verdict + install/wiring plan | Synthesize P5-001 through P5-003 into a working evaluation artifact recording: the accept/reject/conditional recommendation on ADR-0008, rationale, and an (unexecuted) install/wiring plan for a future feature to consume if accepted. | 2 pts | spike-writer | opus | adaptive | P5-003 |

## Detailed Task Specifications

### Task P5-001: Static metadata review

**Estimate**: 1 pt · **Dependencies**: None

**Acceptance Criteria**:
- [ ] AC-P5-1: Maintainer-activity signal recorded (commit cadence, issue/PR response pattern) from public GitHub metadata — no authenticated API calls.
- [ ] AC-P5-2: Release-cadence signal recorded from PyPI's public release history.
- [ ] AC-P5-3: CVE history recorded via a public advisory source (e.g. GitHub Security Advisories, OSV) — read-only lookup, no credentials.
- [ ] AC-P5-4: Dependency count recorded from PyPI's published metadata (not yet the deep inspection — that's P5-002).
- [ ] AC-P5-5: Zero credentials used, zero authenticated API calls made to produce any of the above.

**Files Involved**:
- `.claude/worknotes/rfup-external-routing/litellm-router-eval.md` (new, incrementally built across P5-001 through P5-004).

### Task P5-002: `pip download --no-deps` inspection

**Estimate**: 1 pt · **Dependencies**: P5-001

**Acceptance Criteria**:
- [ ] AC-P5-6: `pip download --no-deps litellm` executed in a scratch/temp location (not the project venv) — the package is downloaded, not installed; `import litellm` is never executed.
- [ ] AC-P5-7: Declared dependency tree extracted from the downloaded artifact's `METADATA`/`requires.txt` (or equivalent) — a full transitive dependency count/list recorded.
- [ ] AC-P5-8: Top-level code surface (module/file listing from the wheel/sdist) reviewed for anything that would materially expand the security review surface beyond what `litellm_router.py`'s existing docstring already documents (the module docstring already states `requires = ("litellm",)` and describes degraded-mode behavior).
- [ ] AC-P5-9: Zero live network calls beyond the `pip download` operation itself (a public package-index fetch, not a provider/completion call) and zero provider credentials touched.

**Files Involved**:
- `.claude/worknotes/rfup-external-routing/litellm-router-eval.md` (append).

### Task P5-003: Cross-reference existing adapter

**Estimate**: 1 pt · **Dependencies**: P5-002

**Acceptance Criteria**:
- [ ] AC-P5-10: Explicit comparison of "what `litellm_router.py` already does in degraded mode today" (deterministic first-preferred-entry fallback, per its module docstring) vs. "what would newly execute if `litellm` were installed and a provider key present" — this comparison is the basis for the security-posture judgment in P5-004, not a restatement of the existing docstring.
- [ ] AC-P5-11: The `2d198a8` ICA-provider mapping fix (already on `main`-side history, pre-dates this branch) is explicitly factored into the assessment — it is forward-compat correctness work for *when* `litellm` is later installed, not an activation of it now; the verdict should account for this existing groundwork rather than treating the adapter as a from-scratch install.

**Files Involved**:
- `.claude/worknotes/rfup-external-routing/litellm-router-eval.md` (append); read-only reference to `src/research_foundry/adapters/litellm_router.py`.

### Task P5-004: Accept/reject verdict + install/wiring plan

**Estimate**: 2 pts · **Dependencies**: P5-003

**Acceptance Criteria**:
- [ ] AC-P5-12: Verdict is one of `accept` / `reject` / `conditional`, stated explicitly and citing specific findings from P5-001 through P5-003 (not a restatement of ADR-0008's own framing without new evidence).
- [ ] AC-P5-13: Install/wiring plan is present regardless of verdict direction (even a `reject` verdict documents what an eventual install would require, so a future re-evaluation doesn't restart from zero) — but is explicitly marked **unexecuted**; no step in this plan or artifact triggers an actual install.
- [ ] AC-P5-14: Evaluation-method limitations are documented explicitly (the no-install/no-credentials constraint bounds how deep the security review can go — PRD Risks table) so a `karen`/downstream reviewer can judge confidence level, not just the conclusion.
- [ ] AC-P5-15: Zero live external calls and zero credentials used across the entire phase — this is the load-bearing exit criterion the parent plan's Hard Constraint 2 depends on; record this as an explicit statement in the artifact, not merely an absence.

**Files Involved**:
- `.claude/worknotes/rfup-external-routing/litellm-router-eval.md` (finalized). This working artifact feeds P6/DOC-006b, which formalizes the verdict into the durable design-spec at `docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md`.

## Quality Gates

This phase is complete when:

- [ ] **Functional**: Verdict + install/wiring plan present in the working eval artifact.
- [ ] **Security**: 0 live external calls (beyond public, unauthenticated PyPI/GitHub-metadata/advisory lookups and the `pip download` operation itself), 0 credentials used — explicitly confirmed, not merely absent by omission.
- [ ] **Mode-D avoidance**: No step in this phase installs, imports, or executes `litellm`; no provider key is read, referenced, or exercised.
- [ ] **Documentation**: Evaluation-method limitations stated explicitly for downstream reviewer confidence-calibration.

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| No-install/no-credentials constraint limits evaluation depth, producing a weak verdict | Medium | AC-P5-14 — document limitations explicitly rather than overstating confidence. |
| Scope creep into install / Mode-D territory | Medium | Hard Constraint 2 restated at phase-file level; AC-P5-6/AC-P5-9/AC-P5-15 are explicit negative-confirmation ACs. |

## Findings Captured This Phase

- [ ] No new findings this phase (default)

---

**Phase Version**: 1.0 · **Last Updated**: 2026-07-22

[Return to Parent Plan](../rfup-external-routing-v1.md)
