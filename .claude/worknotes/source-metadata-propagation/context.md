---
type: context
prd: source-metadata-propagation
feature_slug: source-metadata-propagation
plan_ref: docs/project_plans/implementation_plans/infrastructure/source-metadata-propagation-v1.md
prd_ref: docs/project_plans/PRDs/infrastructure/source-metadata-propagation-v1.md
title: "Source Metadata Propagation - Development Context"
status: "active"
created: "2026-08-02"
updated: "2026-08-02"

critical_notes_count: 0
implementation_decisions_count: 0
active_gotchas_count: 0
agent_contributors: []
agents: []
---

# source-metadata-propagation - Development Context

**Status**: Active Development (not yet started — tracking artifacts only)
**Created**: 2026-08-02
**Last Updated**: 2026-08-02

> **Purpose**: Shared worknotes for all agents working this plan. Add brief observations, decisions,
> gotchas, and implementation notes that future agents should know. This file is the sticky-note pad;
> the execution ledger (OQ resolutions, Mode-D approval records, deviation rationale) lives in
> `implementation-notes.md` in this same directory — do not duplicate that content here.

---

## Quick Reference

**Agent Notes**: 0 notes from 0 agents
**Critical Items**: 0 items requiring attention
**Last Contribution**: none yet

**Plan doctrine**: this is a Claude-5 plan — `routing_constraints` in the plan resolve model/agent
selection at dispatch time. Progress files in `.claude/progress/source-metadata-propagation/` deliberately
carry no `owners`/`assigned_to`/model pins; do not add them here either.

---

## Milestone map (M1→phase-1 .. M4→phase-4)

| Milestone | Progress file | Gate lens | Mode-D halt | Per-milestone karen |
|---|---|---|---|---|
| M1 — First-party source metadata is real, contract-versioned, and reaches the bundle | `.claude/progress/source-metadata-propagation/phase-1-progress.md` | security, validator (untrusted-input) | no | no |
| M2 — The attribution entity exists with a value-free, recompute-only mirror | `.claude/progress/source-metadata-propagation/phase-2-progress.md` | validator | no | no |
| M3 — The provenance boundary is structurally closed | `.claude/progress/source-metadata-propagation/phase-3-progress.md` | security, validator (authz-boundary) | **yes** — authorization boundary | no |
| M4 — Queryable, tri-state honest, and non-regressive | `.claude/progress/source-metadata-propagation/phase-4-progress.md` | security, validator (irreversible-outward) | **yes** — catalog schema migration | **yes** — C3 milestone |

Waves execute in the listed order (`wave_plan.waves: [["M1"],["M2"],["M3"],["M4"]]`), but **M1 → M2 is
merge-conflict hygiene, not a semantic dependency**: both milestones are additive under existing open
seams in the shared hot file `schemas/source_card.schema.yaml`, and M2 could land first if convenient — it
is sequenced only to keep two agents off one schema file. **M2 → M3 → M4 remain genuine semantic
dependencies** (M3 enforces a shape M2 defines; M4's columns and rollups consume both M1's hydration and
M2's records) — do not generalize the M1→M2 flexibility to those.

---

## Implementation Decisions

> Key architectural and technical decisions made during development

_None yet — see the plan's own `decisions:` frontmatter block for the six decisions already accepted at
plan-authoring time: owning entity is a new `source_attribution` top-level entity; propagation happens at
export time in `_resolve_source()`; no backfill — tri-state coverage ships with the first query surface;
rollups are monotone only; **OQ-3 is resolved** — `attribution_summary` carries `attribution_ids`, counts,
and monotone rollups ONLY, never a raw value, recompute-only from authoritative records; and provenance is
required **structurally** (schema shape), not by a second field-name allowlist — the name-based guard
(`no_agent_authored_attribution_value` / `_RIGHTS_GOVERNED_FIELDS`) is defence-in-depth only, per M3._

---

## Gotchas & Observations

> Things that tripped us up or patterns discovered during implementation

_None yet._

---

## Integration Notes

> How components interact and connect

_None yet._

---

## Performance Notes

> Performance considerations discovered during implementation

_None yet._

---

## Agent Handoff Notes

> Quick context for agents picking up work

_None yet — this is the initial tracking-artifact creation. Next agent picks up at M1 entry: resolve OQ-1
and OQ-4 (see `phase-1-progress.md` task `SMP-1.1`), record resolutions in `implementation-notes.md`._

---

## References

**Related Files**:
- Source plan: `docs/project_plans/implementation_plans/infrastructure/source-metadata-propagation-v1.md`
- PRD: `docs/project_plans/PRDs/infrastructure/source-metadata-propagation-v1.md`
- SPIKE charter: `docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-charter.md`
- Feasibility brief: `docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-feasibility-brief.md`
- Proposed ADR: `docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-proposed-adr.md`
- Anchor feature (merged pattern to copy): `docs/dev/architecture/adr-rights-entity-model.md`
- Human-orchestrator brief: `docs/project_plans/human-briefs/source-metadata-propagation.md`
- Execution ledger (OQ resolutions, Mode-D approvals, deviations): `.claude/worknotes/source-metadata-propagation/implementation-notes.md`
- Progress files: `.claude/progress/source-metadata-propagation/phase-{1,2,3,4}-progress.md`
