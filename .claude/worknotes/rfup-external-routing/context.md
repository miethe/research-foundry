---
type: context
doc_type: context
feature_slug: "rfup-external-routing"
prd: "rfup-external-routing"
title: "RFUP External-Routing Gap Closure - Development Context"
status: "active"
created: "2026-07-22"
updated: "2026-07-22"

critical_notes_count: 0
implementation_decisions_count: 0
active_gotchas_count: 0
agent_contributors: []

agents: []
---

# RFUP External-Routing Gap Closure - Development Context

**Status**: Active Development
**Created**: 2026-07-22
**Last Updated**: 2026-07-22

> **Purpose**: Shared worknotes for all agents working this feature. Add brief observations, decisions, gotchas, and implementation notes future agents should know.

---

## Quick Reference

**Agent Notes**: 0 notes from 0 agents
**Critical Items**: 0 items requiring attention
**Last Contribution**: none yet

---

## Orchestration Overview

This is a Tier 3 delta plan (~24-27 pts, 6 phases + 1 seam task) closing 4 still-open RFUP items plus a newly-discovered quote-fidelity gap. Execution runs in **4 waves**, per the parent plan's `wave_plan` frontmatter:

| Wave | Phases | Notes |
|------|--------|-------|
| Wave 1 | P1, P5 | Independent, no shared files. P1 = Path-B test hardening. P5 = native-adapter SPIKE/ADR-0008 verdict (eval-only). |
| Wave 2 | P2 | Solo, critical-path root. Pediatric evidence-card schema + hard-gate. Both P3 and P4 depend on this. |
| Wave 3 | P3, P4 | Both `depends_on: [P2]`, both extend `verification.py` on disjoint functions. Followed by SEAM-001 (seam regression, `integration_owner: python-backend-engineer`) once both land. **One consolidated `karen` milestone runs after Wave 3 (after SEAM-001 is green)** — not a separate pass at P2 or P4. |
| Wave 4 | P6 | Final. `depends_on: [P1, P3, P4, P5]`. CHANGELOG + deferred-item design-specs + context pointers + plan-frontmatter finalization. **End-of-feature `karen` pass runs after P6** — the second and final checkpoint. |

`task-completion-validator` is a mandatory per-phase gate, P1 through P6.

---

## Guardrails

- **Seam boundary**: only evidence→verified-claim logic goes upstream into `rf`; CDS-specific FHIR/rule-DSL/signing logic never crosses into `rf` in either direction. `rf` validates structural completeness of the `pediatric_cds` block only — it does not originate or interpret clinical semantics (age partitions, lab/method fields, threshold portability, lifecycle content), which remain authored/owned by `pediatric-anemia-site`.
- **P5 is EVAL-ONLY** (Hard Constraint 2): no install, no live external calls, no credentials. The ADR-0008 accept/reject/conditional verdict is the sole deliverable; any install is a separate future feature gated on this verdict.
- **This is a DELTA plan** (Hard Constraint 3): RFUP-1..5,7 already landed on `main` at commit `001a834`. Do not re-scope, re-litigate, or re-implement that work.
- **Karen milestone consolidation**: the decisions-block's per-phase exit-gate column lists `karen` at P2 and again at P4 individually — this is **overridden** by the parent plan's Reviewer Gates section, which consolidates the entire clinical-gate cluster's risk surface into a single `karen` pass after SEAM-001 is green. Do not add a standalone `karen` pass at P2 or mid-Wave-3.
- **PRD OQ-5 / ADR-0008 status transition**: this plan produces an rf-side verdict/install-plan artifact only. The actual ADR-0008 status transition happens in `pediatric-anemia-site` and is explicitly out of scope (cross-repo write restriction) — tracked as deferred item DF-RFUP-EXT-02, closed out via P6-003 (DOC-006b).
- **Haiku override**: `documentation-writer`/`changelog-generator` route on **sonnet** for P6 in this environment — haiku-model default agents hard-error here (project memory: `haiku-subagents-inaccessible`). This overrides the repo's standard haiku-default convention for doc-finalization phases.

---

## Implementation Decisions

> Key architectural and technical decisions made during development

(none logged yet — see parent plan frontmatter `decisions:` block for the pre-execution decisions already locked in)

---

## Gotchas & Observations

> Things that tripped us up or patterns discovered during implementation

(none logged yet)

---

## Integration Notes

> How components interact and connect

(none logged yet — SEAM-001 is the designated integration-proof point for P2/P3/P4 composing on `verification.py`)

---

## Performance Notes

(none logged yet)

---

## Agent Handoff Notes

(none logged yet)

---

## References

**Related Files**:
- PRD: `docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md`
- Parent Implementation Plan: `docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md`
- Decisions Block: `.claude/worknotes/rfup-external-routing/decisions-block.md`
- Scope Brief: `.claude/worknotes/rfup-external-routing/scope-brief.md`
- State Audit: `.claude/worknotes/rfup-external-routing/state-audit.md`
- Phase Files:
  - `docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/phase-1-pathb-tests.md`
  - `docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/phase-2-pediatric-schema-gate.md`
  - `docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/phase-3-4-clinical-gate-cluster.md`
  - `docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/phase-5-adapter-eval.md`
  - `docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/phase-6-docs-deferrals.md`
- Progress Files: `.claude/progress/rfup-external-routing/phase-{1,2,3-4,5,6}-progress.md`
