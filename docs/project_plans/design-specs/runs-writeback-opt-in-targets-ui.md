---
title: "Design Spec: Runs Viewer — Opt-In Target Dispatch (intenttree/arc/notebooklm)"
doc_type: design_spec
schema_version: 2
status: draft
maturity: idea
created: 2026-07-18
updated: 2026-07-18
feature_slug: runs-writeback-approve-dispatch
deferred_from: runs-writeback-approve-dispatch-v1
deferred_item_id: DI-WBAD-1
category: backlog
owner: nick
prd_ref: docs/project_plans/PRDs/features/runs-writeback-approve-dispatch-v1.md
related_docs:
  - docs/project_plans/implementation_plans/features/runs-writeback-approve-dispatch-v1.md
  - src/research_foundry/services/writeback.py
---

# Design Spec: Runs Viewer — Opt-In Target Dispatch (intenttree/arc/notebooklm)

> **Maturity: idea** — pre-commitment stub. No implementation has been
> scoped. Promote to `proposal` when the promotion trigger fires.

---

## Deferral Summary

| Field | Value |
|-------|-------|
| **Deferred from** | `runs-writeback-approve-dispatch-v1` |
| **Reason** | UI dispatch of `intenttree`/`arc`/`notebooklm` targets is out of scope (PRD §7) — these are live-push targets with different retry/idempotency semantics than the 3 default local-file targets. |
| **Promotion trigger** | 3-target UI pattern has run in production for a period and an operator requests the opt-in targets in the viewer. |
| **Target spec path** | `docs/project_plans/design-specs/runs-writeback-opt-in-targets-ui.md` (this file) |

---

## Scope (idea-stage)

When promoted, this spec would cover:

- **Opt-in target selection UI** — extending the runs-viewer's approve+dispatch
  action to let an operator select one or more of `intenttree`, `arc`,
  `notebooklm` in addition to (or instead of) the 3 default local-file targets
  (MeatyWiki, SkillMeat, CCDash).
- **Live-push retry/idempotency semantics** — unlike the 3 default targets,
  which write local files and are naturally idempotent on re-invocation, the
  opt-in targets push to external live systems. This spec would need to define:
  - Retry policy on partial/network failure (distinct from local-file overwrite
    semantics).
  - Idempotency keys or dedup strategy so a re-dispatch does not create
    duplicate remote records.
  - Per-target error surfaces distinct from the existing per-target isolation
    model (PRD Risk R7 boundary).
- **RBAC/governance implications** — whether opt-in targets require elevated
  permissions or a separate governance gate given their externally-visible
  side effects.
- **Audit-row extension** — whether the existing audit-row-per-outcome model
  (4 outcome classes) needs new outcome classes for live-push-specific failure
  modes (e.g., remote-service-unavailable vs. local-write-failure).

### v1 Constraint

In v1, the approve+dispatch action in the runs-viewer only supports the 3
default local-file targets (MeatyWiki, SkillMeat, CCDash). Dispatch to
`intenttree`, `arc`, or `notebooklm` remains a CLI-only, out-of-viewer
operation. This is intentional — the PRD explicitly scopes v1 to the
lower-risk, idempotent local-file writeback chain.

---

## Notes for Promotion

- Coordinate with `src/research_foundry/services/writeback.py` to confirm
  whether the existing dispatch primitives can be extended in place or
  whether opt-in targets need their own service-layer entry point given the
  differing retry/idempotency contract.
- Consider whether this should ship as a single combined UI (all 6 targets
  selectable) or a clearly separated "advanced/live-push" section to avoid
  operator confusion about idempotency guarantees.
- Re-review RBAC scoping (see `docs/project_plans/implementation_plans/features/runs-writeback-approve-dispatch-v1.md`)
  before exposing live-push targets to any non-owner role.
