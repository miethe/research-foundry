---
title: "Phase 1: Deployment-Mode Presets"
schema_version: 2
doc_type: phase_plan
it_schema: 1
status: draft
created: 2026-07-22
updated: 2026-07-22
feature_slug: public-multiuser-release-activation
phase: P1
phase_title: "Deployment-Mode Presets"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
entry_criteria:
  - "No dependencies — first phase; may start immediately."
exit_criteria:
  - "FR-2 byte-identical resolved-config regression test green."
  - "task-completion-validator pass."
---

# Phase 1: Deployment-Mode Presets

[← Back to main plan](../public-multiuser-release-activation-v1.md)

**Estimate**: 5 pts
**Dependencies**: None (Wave 1 / `batch_1`)
**Assigned Subagent(s)**: `python-backend-engineer` (primary); `backend-architect` (secondary — preset-composition design sanity)
**Model**: sonnet | **Effort**: adaptive
**Mode**: C — Autonomous Feature Sprint (bounded, low ambiguity; composition of existing knobs)

## Overview

Compose the five existing P5 config knobs (`auth.provider`, `auth.rbac_enforcement`, `workspace_isolation_enforcement`, `viewer.bind_host`, `auth.rate_limit.enabled`) into a single validated `deployment_mode` preset. This phase intentionally does **not** wire the DI-1 acknowledgment check yet (that lands in P4, ACT-402) — it ships a **gate stub** that P4 completes. The single highest-severity risk in this entire plan lives here: `single_user` must remain byte-identical to today's default behavior for the LAN/NUC deployment.

## Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|---------------|
| ACT-101 | Deployment-mode resolver | Add `Config.deployment_mode()` resolver (FR-1, default `single_user`); compose `single_user`/`multi_user` presets over the 5 existing per-knob resolvers per FR-2/FR-3 (presets set *defaults*, explicit overrides win). | FR-1, FR-2, FR-3 all satisfied; `single_user` preset produces identical resolved config to pre-feature default (see AC below). | 3 pts | python-backend-engineer | sonnet | adaptive | None |
| ACT-102 | `--mode` CLI flag + startup gate stub | Add `rf serve --mode single_user\|multi_user` flag (FR-5) mirroring `--auth-mode`/`--bind-host` conventions at `cli_commands.py:2601`; add `Config.deployment_mode_validate()` stub that checks FR-4 conditions (a)–(c) only — condition (d) (DI-1 ack) is wired in P4 (ACT-402). | FR-4 (partial: a–c), FR-5 satisfied; stub raises `ValueError` naming every unmet condition, not just the first. | 2 pts | python-backend-engineer | sonnet | adaptive | ACT-101 |
| REV-P1-001 | Reviewer gate: task-completion-validator | Mode E review of ACT-101/ACT-102 diff + regression test output before phase seal. | Validator confirms FR-1/2/3/5 + partial FR-4 satisfied; no edit authority. | gate | task-completion-validator | sonnet | adaptive | ACT-101, ACT-102 |

**Phase point subtotal**: 5 pts (reviewer-gate row excluded).

## Structured Acceptance Criteria

#### AC-3 (partial, P1 scope): `multi_user` startup gate is fail-closed on conditions (a)–(c)
- target_surfaces:
    - src/research_foundry/config.py
    - src/research_foundry/api/app.py
- propagation_contract: >
    `Config.deployment_mode_validate()` is called at API app startup and by `rf serve`; in P1 it
    evaluates FR-4 conditions (a) `auth.provider=="none"`, (b) RBAC cannot resolve to `enforced`,
    (c) workspace isolation cannot resolve to `enforced` — and raises `ValueError` naming every
    unmet condition. Condition (d) (DI-1 acknowledgment) is added by P4's ACT-402; this AC is
    re-verified in full at P4 exit (see Phase 4 AC-3).
- resilience: >
    If `deployment_mode` is unset in `foundry.yaml` and no `--mode` flag is passed, resolution
    falls through to `single_user` (today's default) — never to `multi_user` implicitly.
- visual_evidence_required: false
- verified_by:
    - ACT-102
    - ACT-404 (Phase 4, full 4-condition suite)

#### R-P2 guard: FR-2 regression AC (explicit, non-optional)
- target_surfaces:
    - src/research_foundry/config.py
- propagation_contract: >
    A dedicated regression test resolves the full config with no `deployment_mode` key set (today's
    shape) and asserts byte-identical output against the same resolution with
    `deployment_mode: single_user` explicitly set. Both must produce `auth.provider=none`, both
    enforcement flags `auto`, and unchanged `viewer.bind_host`/rate-limit defaults.
- resilience: >
    If any future preset-resolver change causes a divergence, the regression test fails loudly at
    CI/test time — it is the acceptance gate for shipping ACT-101 at all, not an optional nice-to-have.
- visual_evidence_required: false
- verified_by:
    - ACT-101

## Quality Gates

- [ ] `single_user` resolved config == pre-feature default resolved config (byte-identical regression test).
- [ ] `multi_user` preset resolves RBAC/isolation/rate-limit defaults per FR-3, with per-knob overrides still winning.
- [ ] `rf serve --mode` flag overrides config-file `deployment_mode` correctly.
- [ ] Gate stub raises `ValueError` naming every unmet condition (a)–(c), not just the first.
- [ ] `task-completion-validator` pass (REV-P1-001).

## Key Files & Integration Points

- `src/research_foundry/config.py` — new `deployment_mode()` + `deployment_mode_validate()` (stub).
- `src/research_foundry/cli_commands.py` (**2,755 lines — H7 high-friction surface**) — `--mode` flag wiring near existing `--auth-mode`/`--bind-host` handling at `cli_commands.py:2601`. **Guardrail**: do not read this file whole; use `grep -n "auth-mode\|bind-host\|--mode"` to locate the insertion point, edit via targeted `sed`/`Edit`, budget ≤40 tool uses, STOP-and-report-partial if exceeded.
- `src/research_foundry/api/app.py` — startup call site for `deployment_mode_validate()`.

## Integration Owner

Single specialty phase (python-backend-engineer only, with backend-architect as design-sanity reviewer, not a co-implementer) — no `integration_owner`/seam task required per R-P3 (no ≥2-owner-specialty file intersection).

---

[← Back to main plan](../public-multiuser-release-activation-v1.md) | [Next: Phase 2 →](./phase-2-principal-store-auth-resolution.md)
