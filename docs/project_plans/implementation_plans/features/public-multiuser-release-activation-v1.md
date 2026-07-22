---
title: "Public Multi-User Release Activation \u2014 Implementation Plan"
schema_version: 2
doc_type: implementation_plan
it_schema: 1
status: completed
created: '2026-07-22'
updated: '2026-07-22'
feature_slug: public-multiuser-release-activation
feature_version: v1
tier: 3
prd_ref: docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
plan_ref: null
scope: 'Activate the shipped public-multiuser-p5-auth-rbac substrate: compose its
  five independent config knobs into two fail-closed deployment-mode presets, add
  dynamic non-human principals (service accounts + user-scoped PATs) backed by a new
  SQLite token store, close the DI-1 repo-wide workspace-scoping audit as a hard pre-multi-tenant
  gate, and ship the admin UI to manage both.

  '
effort_estimate: ~52 points (bottom-up, see Estimation Sanity Check)
architecture_summary: "Sequential config\u2192identity\u2192admin-API spine (P1\u2192\
  P2\u2192P3\u2192P5) gates the UI last; the DI-1 audit (P4) is a largely independent\
  \ long pole run in parallel with P2, rejoining the gate stub (P1) and the live-session\
  \ regression (needs P2+P3) before end-of-feature testing/docs (P6).\n"
related_documents:
- docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
- docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md
- docs/project_plans/human-briefs/public-release-phase5-gap-closure.md
- docs/projects/research-foundry/SERVICE_CONTRACT.md
- .claude/worknotes/public-multiuser-release-activation/decisions-block.md
- .claude/findings/public-multiuser-release-activation-findings.md
- docs/dev/architecture/auth-rbac-operator-guide.md
references:
  user_docs: []
  context: []
  specs:
  - .claude/skills/planning/references/ac-schema.md
  - .claude/rules/delegation-modes.md
  related_prds:
  - docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
spike_ref: docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
adr_refs:
- ADR-001 (auth-provider port, SPIKE public-multiuser-p4p5-foundations)
charter_ref: null
changelog_ref: null
changelog_required: true
test_plan_ref: null
plan_structure: independent
progress_init: auto
deferred_items_spec_refs:
- docs/project_plans/design-specs/oidc-adapter-live-implementation.md
- docs/project_plans/design-specs/rbac-db-postgres-migration.md
- docs/project_plans/design-specs/service-account-fine-grained-scoping.md
- docs/project_plans/design-specs/runs-evidence-workspace-isolation.md
findings_doc_ref: .claude/findings/public-multiuser-release-activation-findings.md
owner: nick
contributors:
- opus-4-8
- implementation-planner
priority: high
risk_level: high
category: product-planning
tags:
- implementation
- planning
- phases
- auth
- rbac
- multi-user
- activation
- service-accounts
- pat
- di-1
milestone: public-multiuser-activation
commit_refs: ["60f40c8", "79daed5", "d243ab2", "1d53556", "3070945", "8fbe075"]
pr_refs: []
files_affected:
- src/research_foundry/config.py
- src/research_foundry/cli_commands.py
- src/research_foundry/services/rbac_store.py
- src/research_foundry/services/token_service.py
- src/research_foundry/services/audit_service.py
- src/research_foundry/services/agent_job_service.py
- src/research_foundry/api/middleware/auth.py
- src/research_foundry/api/auth/provider.py
- src/research_foundry/api/auth/scope.py
- src/research_foundry/api/routers/admin.py
- src/research_foundry/api/routers/agent_jobs.py
- frontend/runs-viewer/src/components/AdminSettings/RoleAssignmentPanel.tsx
- frontend/runs-viewer/src/components/AdminSettings/ServiceAccountsPanel.tsx
- frontend/runs-viewer/src/components/AdminSettings/PersonalAccessTokensPanel.tsx
- frontend/runs-viewer/src/auth/AuthContext.tsx
- docs/projects/research-foundry/SERVICE_CONTRACT.md
- docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md
- CHANGELOG.md
planning_maturity: shipped
open_questions:
- q: 'OQ-1: Should token_service.py live under services/ (peer to rbac_store.py/audit_service.py)
    or api/auth/?'
  owner: nick
  status: open
  recommendation: services/ for store-adjacency; confirm against existing layering
    in P2.
- q: "OQ-2: access_tokens.principal_id FK target differs by type (service_accounts.id\
    \ vs users.id) \u2014 nullable-pair or single polymorphic id + principal_type\
    \ discriminator?"
  owner: nick
  status: open
  recommendation: Discriminator + app-level integrity (SQLite has no partial FK);
    resolve in P2 (ACT-201).
- q: 'OQ-3: Confirm docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md
    is the canonical artifact FR-13''s status check reads.'
  owner: nick
  status: open
  recommendation: Confirm at P4 kickoff (ACT-401); path is already load-bearing in
    PRD files_affected.
- q: 'OQ-4: Does the composite middleware need a per-request last_used_at write on
    every token hit, or throttled/async?'
  owner: nick
  status: open
  recommendation: "Throttled/best-effort, fail-open like audit \u2014 resolve in P2\
    \ (ACT-202/ACT-203)."
decisions:
- decision: Public human auth = Clerk (wire/activate the shipped adapter; do NOT build
    a local human-user store).
  rationale: Clerk adapter already shipped under P5; building a parallel human-user
    store duplicates identity surface.
  status: accepted
- decision: Non-human principals = BOTH standalone service accounts (principal_type=service)
    AND user-scoped PATs (principal_type=user_pat).
  rationale: Machine callers (agents/CI/integrations) and delegated humans have distinct
    trust/revocation needs neither principal type alone covers.
  status: accepted
- decision: OIDC = deferred (seam/stub only; explicitly out of scope).
  rationale: oidc.py remains a registered, unimplemented seam; no live IdP integration
    work in this feature.
  status: accepted
- decision: Token store extends the existing SQLite rbac.db (no Postgres, no new datastore).
  rationale: Avoids a second source of truth for identity data; Postgres migration
    is an explicit future-scale item.
  status: accepted
- decision: multi_user's fail-closed gate checks auth.provider != 'none' (not a specific
    provider).
  rationale: Decouples the gate from Clerk procurement status; local_static already
    satisfies server-verifiable non-none identity for closed-beta deployments.
  status: accepted
decision_gates:
- gate: 'P4 DI-1 audit scope-boundary human sign-off (Mode D) before status: accepted'
  status: pending
- gate: karen milestone review after P2 (security-sensitive composite auth)
  status: pending
- gate: karen milestone review after P4 (DI-1 gate)
  status: pending
- gate: karen end-of-feature review (P6)
  status: pending
success_metrics:
- Operator selects deployment mode via one config key / --mode flag instead of tuning
  5 independent knobs.
- 100% of enumerated workspace-write surfaces have a DI-1 audit verdict (accepted
  or remediated) before multi_user is startable.
- Service accounts and PATs are issuable, listable, and revocable via admin API and
  admin UI with zero plaintext secrets persisted.
- 100% of agent_jobs launched under deployment_mode=multi_user resolve to a service-account
  execution identity in the audit log.
execution_mode: unassigned
agent_title: 'Activate public multi-user mode: deployment presets, non-human principals,
  DI-1 gate'
agent_summary: 'Compose the shipped P5 auth/RBAC/isolation knobs into a validated
  single_user|multi_user preset, add a dynamic service-account/PAT token store + admin
  API/UI, and close the DI-1 full-surface workspace-scoping audit as a hard gate before
  multi_user can start.

  '
wave_plan:
  serialization_barriers:
  - docs/projects/research-foundry/SERVICE_CONTRACT.md
  - CHANGELOG.md
  phases:
  - id: P1
    depends_on: []
    isolation: shared
    parallelizable: true
    owner_skills: []
    model: sonnet
    effort: adaptive
    files_affected:
    - src/research_foundry/config.py
    - src/research_foundry/cli_commands.py
  - id: P2
    depends_on:
    - P1
    isolation: worktree
    parallelizable: true
    owner_skills: []
    model: sonnet
    effort: extended
    files_affected:
    - src/research_foundry/services/rbac_store.py
    - src/research_foundry/services/token_service.py
    - src/research_foundry/api/middleware/auth.py
    - src/research_foundry/services/agent_job_service.py
  - id: P3
    depends_on:
    - P2
    isolation: shared
    parallelizable: false
    owner_skills: []
    model: sonnet
    effort: adaptive
    files_affected:
    - src/research_foundry/api/routers/admin.py
  - id: P4
    depends_on:
    - P1
    isolation: worktree
    parallelizable: true
    owner_skills: []
    model: sonnet
    effort: extended
    files_affected:
    - docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md
    - docs/projects/research-foundry/SERVICE_CONTRACT.md
    - src/research_foundry/config.py
  - id: P5
    depends_on:
    - P3
    isolation: shared
    parallelizable: false
    owner_skills: []
    model: sonnet
    effort: adaptive
    files_affected:
    - frontend/runs-viewer/src/components/AdminSettings/ServiceAccountsPanel.tsx
    - frontend/runs-viewer/src/components/AdminSettings/PersonalAccessTokensPanel.tsx
    - frontend/runs-viewer/src/auth/AuthContext.tsx
  - id: P6
    depends_on:
    - P2
    - P3
    - P4
    - P5
    isolation: shared
    parallelizable: false
    owner_skills: []
    model: sonnet
    effort: adaptive
    files_affected:
    - CHANGELOG.md
    - docs/projects/research-foundry/SERVICE_CONTRACT.md
  waves:
  - - P1
  - - P2
    - P4
  - - P3
  - - P5
  - - P6
---

# Implementation Plan: Public Multi-User Release Activation

**Plan ID**: `IMPL-2026-07-22-PUBLIC-MULTIUSER-RELEASE-ACTIVATION`
**Date**: 2026-07-22
**Author**: Opus 4.8 (decisions block) + implementation-planner expansion
**Human Brief**: `docs/project_plans/human-briefs/public-release-phase5-gap-closure.md` (existing gap-closure brief this plan executes against; a dedicated brief for this feature slug may be scaffolded separately if orchestration complexity warrants it during execution)
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md`
- **SPIKE**: `docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md` (ADR-001 `AuthProvider` port)
- **Decisions Block**: `.claude/worknotes/public-multiuser-release-activation/decisions-block.md`
- **Anchor feature**: `docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md` (47.25 pts, completed)

**Complexity**: Large (Tier 3)
**Total Estimated Effort**: ~52 points (bottom-up; see Estimation Sanity Check)
**Mode**: Mixed — standard delegation throughout, with **Mode D** (High-Risk Change, human sign-off required) specifically on the P4 DI-1 audit acceptance gate per `.claude/rules/delegation-modes.md`.

## Executive Summary

The public-multiuser-p5-auth-rbac substrate (auth port, RBAC, workspace isolation, audit log, admin API) shipped complete but inert — nothing composes its five knobs into a validated posture, and there is no non-human principal concept. This plan delivers a `deployment_mode` preset (`single_user`|`multi_user`), a dynamic service-account/PAT token store extending `rbac.db`, the admin API/UI to manage both, and closes the DI-1 repo-wide workspace-scoping audit as the hard startup gate `multi_user` cannot bypass. Delivery sequences config foundation (P1) before identity (P2), which gates the admin API (P3) and UI (P5, deliberately last); the DI-1 audit (P4) runs as an independent parallel long pole, rejoining the gate wiring after P1 and the live-session regression after P2+P3. `karen` reviews close P2 (security-sensitive composite auth), P4 (Mode D DI-1 gate), and end-of-feature (P6).

## Implementation Strategy

### Architecture Sequence

This feature composes existing layers rather than introducing new ones; the sequence below maps the six phases onto Research Foundry's layered pattern:

1. **Config Layer** (P1) — `deployment_mode` resolver + preset composition, `rf serve --mode`.
2. **Store + Service Layer** (P2) — `service_accounts`/`access_tokens` tables, `token_service.py`, composite auth chain, agent-job identity binding.
3. **API Layer** (P3) — Admin routes for issue/list/revoke/rotate, deployment-mode-status.
4. **Audit/Enforcement Layer** (P4) — Repo-wide DI-1 backward-trace, remediation, gate wiring. Runs parallel to P2/P3, not sequential to them.
5. **UI Layer** (P5) — Admin panels, `AuthContext.tsx` principal-type. Sequenced deliberately last (Risk: UI-ahead-of-backend).
6. **Testing & Docs** (P6) — Cross-phase E2E, CHANGELOG, docs, SERVICE_CONTRACT.md updates.

### Parallel Work Opportunities

**P4's DI-1 audit (ACT-401) is the long pole (8 pts) and is largely independent of the token store** — launch it in parallel with P2, both starting once P1's config foundation and gate stub exist. Its gate-wiring subtask (ACT-402) only needs P1's stub and can also run in this same window. Its live-session regression subtask (ACT-403) is the exception — it needs a working `multi_user` session (P2+P3) and therefore joins later, alongside P5.

### Critical Path

**P1 → P2 → P3 → P5 → P6**, with P4 forking off P1 and rejoining at two distinct points:

```
P1 ──┬─► P2 ──► P3 ──► P5 ──► P6
     └─► P4(audit, parallel) ──► P4(gate-wire, after P1) ──► P4(regression, after P2+P3) ──► P6
```

- P1 (config foundation) blocks P2's `multi_user`-gated behavior and P4's gate wiring.
- P2 (token service) blocks P3 (admin API calls the service) and FR-12 agent-job binding.
- P3 (admin API) blocks P5 (UI consumes the endpoints) — UI is sequenced last by design.
- P4's audit (ACT-401) runs parallel to P2; its regression subtask (ACT-403) needs P2+P3 and lands alongside P5.
- P6 gathers all phases; end-of-feature `karen` review closes the plan.

### Parallelization Batches

| Batch | Phases / Tasks | Rationale |
|-------|-----------------|-----------|
| `batch_1` | P1 (ACT-101, ACT-102) | No dependencies; config foundation everything else needs. |
| `batch_2` | P2 (ACT-201..206) **+** P4 audit (ACT-401) **+** P4 gate-wire (ACT-402) | P4's audit/gate-wire only need P1's stub; independent of the token store — run in parallel per decisions-block §5. |
| `batch_3` | P3 (ACT-301..303) **+** P4 startup-gate tests (ACT-404) | P3 needs P2 done; ACT-404 only needs ACT-402 + P1, ready as soon as batch_2 closes. |
| `batch_4` | P5 (ACT-501..503) **+** P4 regression (ACT-403) **+** Mode D sign-off (ACT-406) | Both need P2+P3 (a live multi_user-capable session); ACT-406 (human review of ACT-401's findings) also gates here before `multi_user` can be exercised end-to-end. |
| `batch_5` | P6 (ACT-601..609) | Cross-phase testing/docs; needs everything above sealed. |

**Env note**: haiku default agents hard-error in this environment — all `codebase-explorer`/exploration dispatches use `model="sonnet"`; P6 docs tasks also run on `sonnet` (not `haiku`) for the same reason.

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model(s) | Notes |
|-------|-------|----------|--------------------|----------|-------|
| P1 | Deployment-Mode Presets | 5 pts | python-backend-engineer; review: backend-architect | sonnet | Exit gate: FR-2 byte-identical regression test green. |
| P2 | Non-Human Principal Store + Auth Resolution | 14 pts | python-backend-engineer, data-layer-expert; review: backend-architect, senior-code-reviewer | sonnet (extended) | Exit gate: AC-2 (4 credential states) green; **karen milestone**. |
| P3 | Admin API | 8 pts | python-backend-engineer; review: senior-code-reviewer | sonnet | Exit gate: `require_role` sweep green; no raw secret leak. |
| P4 | DI-1 Audit + Enforcement Flip | 13 pts | codebase-explorer → python-backend-engineer; review: karen + human (Mode D) | sonnet (extended for audit) | Exit gate: **Mode D human sign-off**; **karen milestone**. |
| P5 | Admin UI | 6 pts | ui-engineer-enhanced; review: a11y-sheriff | sonnet | Exit gate: AC-1 green; a11y smoke. |
| P6 | Testing & Docs | 6 pts | python-backend-engineer, ui-engineer, documentation-writer, changelog-generator | sonnet | Exit gate: full suite green; **karen end-of-feature**; changelog present. |
| **Total** | — | **52 pts** | — | — | — |

Detailed phase breakdowns (task tables, structured ACs, reviewer gates) live in the linked phase files under [`Phase Breakdown`](#phase-breakdown) below.

### Estimation Sanity Check

**Noun count (H1)**: 2 new domain nouns (`service_accounts`, `access_tokens`), both CRUD-with-RBAC → ≥4 pt floor. P2 alone (14 pts) exceeds this floor; the excess reflects issuance/revocation/expiry logic beyond bare CRUD.

**Dual-impl multiplier (H2)**: N/A — Research Foundry has a single SQLite store (`rbac.db`); no local+enterprise repository split exists in this codebase's architecture. Not applied.

**Algorithmic flag (H3)**: Composite auth resolution (token-store-first → provider fallthrough) and PAT role-ceiling re-resolution both contain "resolution" — flagged. Budgeted at ACT-203 (2 pts) + ACT-204 (2 pts) + ACT-205 (2 pts, dedicated test suite covering the 4 credential states) = 6 pts, above the 3-pt floor. DI-1's backward-trace (ACT-401) is an enumeration/audit, not a solver, per decisions-block §3 — its 8-pt size is justified by Mode-D review overhead and repo-wide surface area, not algorithmic complexity.

**Bundle decomposition (H4)**:

| Capability Area | Independent Estimate | Notes |
|-----------------|----------------------|-------|
| Deployment-mode presets (P1) | 5 pts | Config composition + regression test |
| Non-human principal store + auth resolution (P2) | 14 pts | 2 new tables + issuance service + composite chain + agent-job binding |
| Admin API (P3) | 8 pts | 2 principal types × issue/list/revoke(+rotate) |
| DI-1 audit + enforcement flip (P4) | 13 pts | Repo-wide backward-trace + Mode D review overhead |
| Admin UI (P5) | 6 pts | 2 panels + auth-context extension |
| Testing & Docs (P6) | 6 pts | Cross-phase E2E + CHANGELOG + docs |
| **Σ** | **52 pts** | **floor for plan total** |

**Anchor (H5)**: `public-multiuser-p5-auth-rbac` cost 47.25 pts for the full substrate (auth port + RBAC + isolation migration + audit + rate limits + admin + FE). This plan's delta: (52 − 47.25) / 47.25 ≈ **+10%**. Justification: this is an activation layer on top of an already-shipped substrate, not a from-scratch build — but choosing "both" service accounts AND PATs (rather than one principal type) roughly doubles the issuance/revocation/admin-API/admin-UI surface relative to a single-principal-type design, and the DI-1 audit is a fresh 8-pt long pole with no direct P5 analog (P5's audit work was feature-scoped, not repo-wide). Within the ±30% tolerance.

**Plumbing budget (H6)**: DTOs, DI wiring, and audit-event logging are embedded directly in their owning phases (ACT-202 token DTOs, ACT-303 admin-API audit wiring, ACT-402 gate wiring) rather than lumped into P6, to avoid double-counting. P6's explicit plumbing line items are the ones decisions-block §4 named directly: CHANGELOG (ACT-603, 0.5 pt), `foundry.yaml`/admin-API/SERVICE_CONTRACT.md docs (ACT-604, 1 pt), and `rf` skill currency note (ACT-605, 0.5 pt) — ≈2 pts, ~4% of the 52-pt subtotal. This is deliberately lean because the bulk of "hidden plumbing" for this feature is schema/service/gate wiring already priced into P2–P4, not doc-layer plumbing.

**Huge-file touch (H7, advisory)**: `wc -l` check at planning time flags `src/research_foundry/cli_commands.py` at **2,755 lines** (>2K threshold) — touched by ACT-102 (`rf serve --mode` flag). Per H7 this would warrant a ≥2× multiplier; however, per this plan's explicit scope ("apply H1–H6"), the point estimate is held at the decisions-block-anchored value. The risk is carried operationally instead: ACT-102's task row (Phase 1 file) mandates the anti-blow guardrail (grep -n + sed only, no whole-file read, budget ≤40 tool uses) per `.claude/specs/workflows/large-file-refactor-decomposition-spec.md`. No other files in `files_affected` exceed 2K lines (next largest: `agent_job_service.py` at 1,190 lines).

**Bottom-up total**: 52 pts
**Top-down intuition**: ~50 pts (decisions-block §4 seed)
**Locked estimate**: 52 pts (bottom-up governs; matches decisions-block anchor within rounding)

## Deferred Items & In-Flight Findings Policy

### Deferred Items

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---------|----------|------------------|------------------------|-------------------|
| DF-001 | dependency-blocked | OIDC adapter (FU-2/FU-3) — `oidc.py` remains a registered, unimplemented seam; no live IdP integration in this feature per PRD §7 Out of Scope | An IdP procurement decision is made and a concrete tenant is available to validate against | `docs/project_plans/design-specs/oidc-adapter-live-implementation.md` |
| DF-002 | research-needed | Postgres migration of `rbac.db` (future scale item; PRD §7 Out of Scope, decisions-block token-store decision) | Token-store row volume or concurrent-write contention on SQLite becomes a measured problem | `docs/project_plans/design-specs/rbac-db-postgres-migration.md` |
| DF-003 | scope-cut | Fine-grained per-service-account tool/data-scope allowlists (PRD §7 Out of Scope, PRD OQ Q2 deferred) — service accounts get exactly one role from the existing 5-role model | A future feature needs narrower machine-scoping than "researcher" or "viewer" affords | `docs/project_plans/design-specs/service-account-fine-grained-scoping.md` |
| DF-004 | in-flight finding (load-bearing) | The DI-1 full-surface audit's headline residual risk (rows 10-12): runs/claims/source-cards/evidence bundles have no `workspace_id` concept, so under `multi_user` any authenticated caller can read/writeback-dispatch any run cross-workspace; plus row 9 (`POST /agent-jobs` trusts client-supplied `workspace_id`, spoofing FR-12 audit attribution). Explicitly accepted-as-deferred by the P4 Mode D human sign-off (trusted-cohort scope only) — see the audit's `signoff.residual_risk_acknowledged`. | Before any deployment moves from trusted-cohort `multi_user` to an adversarial/untrusted multi-tenant posture | `docs/project_plans/design-specs/runs-evidence-workspace-isolation.md` |

All four design specs are authored in P6 (ACT-606); `deferred_items_spec_refs` is populated with their paths — see `.claude/skills/planning/references/deferred-items-and-findings.md` for the authoring checklist. DF-003 shares the same target-spec authoring task. DF-004 was added during P6 execution per the lazy-creation/load-bearing-finding rule below (not identified at original planning time) — it is the tracked follow-up that would lift this feature's `multi_user` gate from trusted-cohort to genuinely adversarial multi-tenant isolation.

### In-Flight Findings

**Lazy-creation rule applied**: `.claude/findings/public-multiuser-release-activation-findings.md` was created in P6 (ACT-606) on the first real findings (P2's `senior-code-reviewer`/`karen` non-blocking follow-ups M1/M2 and the karen Low perf note, all carried forward per the phase-2 completion note; plus the DI-1 audit's load-bearing residual-risk cross-reference). `findings_doc_ref` and `related_documents` were updated accordingly; the one load-bearing finding (DI-1 rows 9-12) was promoted to DF-004 above with its spec path appended to `deferred_items_spec_refs`. `status: draft` pending P6's final-phase-sealing step (ACT-607) advancing it to `accepted`.

### Quality Gate

P6 (Testing & Docs) cannot be sealed until:
- [ ] DF-001, DF-002, DF-003 all have a design-spec path in `deferred_items_spec_refs`, or are marked N/A with rationale
- [ ] `findings_doc_ref` is populated and `status: accepted` (if any findings occurred) OR remains `null` (no findings occurred)

## Reviewer Gates Summary

| Gate | Trigger | Reviewer | Mode |
|------|---------|----------|------|
| Per-phase completion | Every phase P1–P6 | `task-completion-validator` | Mode E — Reviewer |
| Security-sensitive milestone | End of P2 (composite auth chain, token secret handling) | `karen` | Mode E — Reviewer |
| DI-1 audit acceptance | End of P4 | `karen` **+ human sign-off (Mode D)** | Mode D — High-Risk Change; no self-certification |
| End-of-feature | End of P6 | `karen` | Mode E — Reviewer |

The P4 DI-1 gate is the only **Mode D** checkpoint in this plan: per `.claude/rules/delegation-modes.md`, the executing agent explores, proposes the audit's scope-boundary statement, and **stops before setting `status: accepted`** on the audit artifact — an explicit human sign-off is required. This directly addresses the WKSP-304 AAR failure mode (a prior "100% coverage" claim on this exact surface was later found incomplete). See Phase 4 file for the full gate mechanics.

## Phase Breakdown

Detailed task tables, structured ACs, and reviewer-gate mechanics for each phase are split into linked files to stay within the 800-line-per-file budget:

| Phase | File |
|-------|------|
| P1 — Deployment-Mode Presets | [`phase-1-deployment-mode-presets.md`](./public-multiuser-release-activation-v1/phase-1-deployment-mode-presets.md) |
| P2 — Non-Human Principal Store + Auth Resolution | [`phase-2-principal-store-auth-resolution.md`](./public-multiuser-release-activation-v1/phase-2-principal-store-auth-resolution.md) |
| P3 — Admin API | [`phase-3-admin-api.md`](./public-multiuser-release-activation-v1/phase-3-admin-api.md) |
| P4 — DI-1 Audit + Enforcement Flip | [`phase-4-di1-audit-enforcement.md`](./public-multiuser-release-activation-v1/phase-4-di1-audit-enforcement.md) |
| P5 — Admin UI | [`phase-5-admin-ui.md`](./public-multiuser-release-activation-v1/phase-5-admin-ui.md) |
| P6 — Testing & Docs | [`phase-6-testing-docs.md`](./public-multiuser-release-activation-v1/phase-6-testing-docs.md) |

**Column conventions** (apply to every phase task table in the linked files):
- `Estimate` — story points. Reviewer-gate rows use `gate` and are excluded from the phase point subtotal.
- `Model` — `sonnet` throughout this plan (haiku hard-errors in this environment; no gemini/codex/nano-banana routing needed for this feature).
- `Effort` — `adaptive` (default) or `extended` (P2 identity/security-sensitive tasks, P4 audit enumeration).

## Risk Mitigation

### Technical Risks (from decisions-block §3, expanded)

| Risk | Severity | Impact | Likelihood | Mitigation |
|------|----------|--------|------------|-------------|
| `single_user` preset silently changes LAN/NUC default behavior | High | High | Medium | FR-2 byte-identical resolved-config regression test vs. pre-feature baseline; preset resolver additive-only. **This is the #1 acceptance gate for P1.** |
| DI-1 audit repeats prior false "100% coverage" claim (WKSP-304 AAR) | Critical | Critical | Medium | Mode D — human review of scope-boundary before `accepted`; FR-13 two-part gate (operator ack + machine-checkable artifact status) so self-certification alone cannot unlock `multi_user`. |
| Token secret leaks via logs/errors/audit rows | Critical | Critical | Low | Hash-at-rest, shown-once, credential-shape guards ported from `agent_job_service.py`'s existing pattern; `senior-code-reviewer` pass on P2/P3. |
| PAT privilege escalation after issuer role downgrade | High | High | Low | FR-9 role-ceiling re-checked at **resolution time**, not just issuance (ACT-202, verified by ACT-205). |
| Composite auth chain misorders → machine token bypasses Clerk or vice-versa | High | High | Low | AC-2 exhaustive 4-credential-state test; token-store-first is deterministic and adapter-agnostic (ACT-203, ACT-205). |
| Agent-job SA binding breaks existing `single_user` agent workflows | Medium | Medium | Low | FR-12 binding activates ONLY under `multi_user`; single_user identity resolution unchanged (AC-5, ACT-204). |
| `cli_commands.py` (2,755 lines) touched by ACT-102 | Medium | Medium | Low | Anti-blow guardrail prompt block (H7 advisory); grep -n + sed only, no whole-file read. |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|----------------------|
| P4's audit (8 pts) runs long and blocks the Mode D sign-off before P6 | High | Medium | Parallelize with P2 from the start (batch_2); do not wait for P2 to complete before starting the audit. |
| Admin UI (P5) starts before backend endpoints stabilize | Medium | Low | Sequenced last in Critical Path by design; P5 cannot start until P3 is sealed. |
| Human sign-off (Mode D, P4) becomes a scheduling bottleneck | Medium | Medium | Surface the audit artifact and scope-boundary statement to the human reviewer as soon as ACT-401's draft lands, not at the end of P4. |

## Resource Requirements

### Team Composition
- Backend/security-sensitive implementation: `python-backend-engineer` (P1–P4 primary), `data-layer-expert` (P2 schema)
- Architecture/design review: `backend-architect` (P1, P2), `senior-code-reviewer` (P2, P3)
- Audit enumeration: `codebase-explorer` (P4, dispatched with `model="sonnet"` — haiku hard-errors in this environment)
- Frontend: `ui-engineer-enhanced` (P5), `a11y-sheriff` (P5 review)
- Testing/docs: `python-backend-engineer`, `ui-engineer`, `documentation-writer`, `changelog-generator` (P6)
- Reviewers: `task-completion-validator` (per phase), `karen` (P2 end, P4 end, feature end)
- **Human**: Mode D sign-off on the DI-1 audit scope-boundary statement (P4) — cannot be delegated to any agent.

### Skill Requirements
- SQLite schema migration discipline (`CREATE TABLE IF NOT EXISTS`, idempotent per `rbac_store.py` convention)
- Constant-time credential comparison (`hmac.compare_digest`)
- FastAPI router/RBAC patterns (`require_role`, `ErrorResponse` envelope)
- React/TypeScript admin panel patterns matching existing `AdminSettings/RoleAssignmentPanel.tsx`
- WCAG 2.1 AA accessibility testing (`jest-axe`)

## Success Metrics

Carried directly from PRD §4 Success Metrics (measurement methods there); this plan's phase exit gates operationalize each:

- Deployment-mode knobs: 5 → 1 config key/flag, 2 validated presets (P1 exit gate)
- DI-1 audit coverage: feature-scoped → 100% of enumerated workspace-write surfaces have a recorded verdict (P4 exit gate)
- Non-human principal issuance: 0 → issuable/listable/revocable via admin API (P3 exit gate)
- Agent-job identity binding: human/static/None → 100% resolve to service-account identity under `multi_user` (P2 ACT-204, verified P6 ACT-601)
- Secret-at-rest exposure: N/A → 0 plaintext secrets persisted anywhere (P2/P3 static-scan test, ACT-205/ACT-601)

## Communication Plan

- Phase-completion status posted at each `task-completion-validator` gate.
- `karen` milestone reviews (P2, P4, end-of-feature) are explicit stop points — do not proceed past them without a passing review.
- Mode D sign-off (P4) requires an explicit human response; treat silence as a blocker, not a pass, per `.claude/rules/delegation-modes.md` and the "silent reviewer" gotcha (never treat silence as approval).

## Post-Implementation

- Regenerate `ai/symbols-api.json` post-implementation (new router/service symbols for `token_service.py`, admin routes).
- Monitor: `audit_event` row volume post-launch (issuance/revocation/rotation traffic under real `multi_user` usage).
- Follow-up: DF-001 (OIDC), DF-002 (Postgres migration), DF-003 (fine-grained SA scoping), DF-004 (runs/claims/evidence workspace isolation — the highest-priority follow-up; see its design spec) tracked via their design specs; revisit when their promotion triggers fire.

---

**Progress Tracking:**

See `.claude/progress/public-multiuser-release-activation/all-phases-progress.md` (created via `artifact-tracking` skill once this plan is approved).

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-07-22
