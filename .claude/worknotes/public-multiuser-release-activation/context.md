---
type: context
schema_version: 2
doc_type: context
feature_slug: public-multiuser-release-activation
prd: public-multiuser-release-activation
title: "Public Multi-User Release Activation - Development Context"
prd_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
status: "active"
created: 2026-07-22
updated: 2026-07-22

critical_notes_count: 0
implementation_decisions_count: 0
active_gotchas_count: 0
agent_contributors: []

agents: []
---

# Public Multi-User Release Activation - Development Context

**Status**: Active Development (Planning complete; execution not yet started)
**Created**: 2026-07-22
**Last Updated**: 2026-07-22

> **Purpose**: Shared worknotes for all agents working this PRD. Add brief observations, decisions,
> gotchas, and implementation notes future agents should know. See `decisions-block.md` in this same
> directory for the Opus decisions scaffold this plan was expanded from — do not overwrite it.

---

## Quick Reference

- **PRD**: `docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md`
- **Phase files**: `docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1/phase-{1..6}-*.md`
- **Decisions Block** (do not overwrite): `.claude/worknotes/public-multiuser-release-activation/decisions-block.md`
- **Progress files**: `.claude/progress/public-multiuser-release-activation/phase-{1..6}-progress.md`
- **Anchor feature**: `public-multiuser-p5-auth-rbac` (shipped 2026-07-08, 47.25 pts — the substrate this plan activates)
- **Tier**: 3 | **Total estimate**: ~52 pts | **Mode**: Mixed, standard delegation + one Mode D checkpoint (Phase 4)

---

## Six-Phase Map

| Phase | Title | Estimate | Primary Owner(s) | Progress File |
|-------|-------|----------|--------------------|----------------|
| P1 | Deployment-Mode Presets | 5 pts | python-backend-engineer | `phase-1-progress.md` |
| P2 | Non-Human Principal Store + Auth Resolution | 14 pts | python-backend-engineer, data-layer-expert | `phase-2-progress.md` |
| P3 | Admin API | 8 pts | python-backend-engineer | `phase-3-progress.md` |
| P4 | DI-1 Audit + Enforcement Flip | 13 pts | codebase-explorer -> python-backend-engineer | `phase-4-progress.md` |
| P5 | Admin UI | 6 pts | ui-engineer-enhanced | `phase-5-progress.md` |
| P6 | Testing & Docs | 6 pts | python-backend-engineer, ui-engineer, documentation-writer, changelog-generator | `phase-6-progress.md` |

## Critical Path

**P1 -> P2 -> P3 -> P5 -> P6**, with P4 forking off P1 and rejoining at two distinct points:

```
P1 ──┬─► P2 ──► P3 ──► P5 ──► P6
     └─► P4(audit, parallel) ──► P4(gate-wire, after P1) ──► P4(regression, after P2+P3) ──► P6
```

- P1 (config foundation) blocks P2's `multi_user`-gated behavior and P4's gate wiring.
- P2 (token service) blocks P3 (admin API calls the service) and FR-12 agent-job binding.
- P3 (admin API) blocks P5 (UI consumes the endpoints) — UI is sequenced last by design.
- P4's audit (ACT-401) runs parallel to P2; its regression subtask (ACT-403) needs P2+P3 and lands alongside P5.
- P6 gathers all phases; end-of-feature `karen` review closes the plan.

**P4 is the schedule long pole** (8-pt audit enumeration) — parallelize with P2 from the start; do not wait for P2 to complete before starting the audit.

---

## Confirmed Product Decisions (user sign-off 2026-07-22)

- **Public human auth = Clerk** — wire/activate the shipped adapter; do NOT build a local human-user store.
- **Non-human principals = BOTH** standalone service accounts (`principal_type=service`) AND user-scoped PATs (`principal_type=user_pat`) — machine callers and delegated humans have distinct trust/revocation needs neither type alone covers.
- **OIDC = deferred** — `oidc.py` remains a registered, unimplemented seam; no live IdP integration work in this feature (tracked as DF-001).
- **Token store extends the existing SQLite `rbac.db`** — no Postgres, no new datastore (Postgres migration tracked as DF-002).
- **`multi_user`'s fail-closed gate checks `auth.provider != "none"`** (not a specific provider) — decouples the gate from Clerk procurement status.

---

## Mode-D DI-1 Sign-Off (Phase 4, ACT-406)

This is the **only Mode D checkpoint** in the plan. Per `.claude/rules/delegation-modes.md`:

- ACT-401 through ACT-404 (audit enumeration, remediation, gate-wiring, test suite) proceed under standard delegation.
- The single act of setting the DI-1 audit artifact's `status` field to `accepted` is **reserved for a human** (Nick) — no agent may self-certify this transition.
- This directly closes the WKSP-304 AAR failure mode: a prior "100% coverage" claim on this exact workspace-scoping surface was later found incomplete twice (two Mode-D leaks discovered post-hoc: `create_draft_from_run`/`create_draft_from_collection`, `catalog_service.get_item`).
- Treat silence from the human reviewer as a blocker, never as a pass.
- `multi_user` cannot start until this sign-off is recorded — the runtime gate (ACT-402) reads the artifact's `status` field at every startup.

Reviewer gates overall: `task-completion-validator` per phase (Mode E); `karen` milestone after P2 (security-sensitive) and after P4 (DI-1 gate); `karen` end-of-feature after P6.

---

## References

- PRD: `docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md`
- Implementation Plan: `docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md`
- SPIKE (ADR-001 AuthProvider port): `docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md`
- Anchor feature (shipped substrate): `docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md`
- Decisions Block (Opus scaffold, pre-existing — do not overwrite): `.claude/worknotes/public-multiuser-release-activation/decisions-block.md`
