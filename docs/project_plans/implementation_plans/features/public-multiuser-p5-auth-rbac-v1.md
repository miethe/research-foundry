---
schema_version: 2
doc_type: implementation_plan
title: "Public Multi-User P5 — Auth/RBAC/Isolation/Audit Hardening — Implementation Plan"
status: draft
created: 2026-07-06
updated: 2026-07-06
feature_slug: public-multiuser-p5-auth-rbac
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
spike_ref: docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
plan_ref: null
risk_level: high
changelog_required: true
deferred_items_spec_refs: []
findings_doc_ref: null
effort_estimate: "47.25 points"
it_schema: 1
tier: 3
feature_version: "v1"
scope: >
  Turn Research Foundry from single-trusted-operator into a governed multi-user system: swappable
  AuthProvider port (local_static default, Clerk opt-in, OIDC/BYO seam), server-side 5-role RBAC,
  enforced workspace isolation via real data migration, full audit log, rate limits, admin settings,
  fail-closed public sharing, frontend auth-context UI, and closure of 3 deferred sensitivity gaps.
architecture_summary: >
  Sequential auth-foundation spine (auth port -> RBAC -> workspace migration) gates a parallel slice
  (Clerk adapter, audit log, deferred-sensitivity closes), converging on public-exposure gates
  (rate limits/admin/sharing), frontend auth-context UI, and a final regression/E2E/docs phase.
related_documents:
  - docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md
  - docs/project_plans/implementation_plans/public-multiuser-p2p3-opus-handoff.md
  - .claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md
references:
  user_docs: []
  context: []
  specs:
    - .claude/skills/planning/references/ac-schema.md
  related_prds:
    - docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
adr_refs:
  - "ADR-001 (auth-provider port, SPIKE public-multiuser-p4p5-foundations)"
  - "ADR-002 (P4 agent-job credential isolation, composed not re-implemented)"
charter_ref: null
changelog_ref: null
test_plan_ref: null
plan_structure: independent
progress_init: auto
owner: nick
contributors: [opus-4-8, implementation-planner]
priority: high
category: "product-planning"
tags: [implementation, planning, phases, auth, rbac, security, public-multiuser, phase-5]
milestone: "public-multiuser-p5"
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/api/auth/provider.py
  - src/research_foundry/api/auth/adapters/local_static.py
  - src/research_foundry/api/auth/adapters/clerk.py
  - src/research_foundry/api/auth/adapters/oidc.py
  - src/research_foundry/services/rbac_store.py
  - src/research_foundry/services/audit_service.py
  - src/research_foundry/api/middleware/auth.py
  - src/research_foundry/api/app.py
  - src/research_foundry/api/routers/runs.py
  - src/research_foundry/api/routers/catalog.py
  - src/research_foundry/api/routers/reports.py
  - src/research_foundry/api/routers/agent_jobs.py
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/services/export_service.py
  - src/research_foundry/services/verification.py
  - src/research_foundry/services/governance.py
  - src/research_foundry/config.py
  - foundry.yaml
  - frontend/runs-viewer/src/auth/AuthContext.tsx
  - frontend/runs-viewer/src/app/AppShell.tsx
  - frontend/runs-viewer/src/api/client.ts
  - frontend/runs-viewer/src/test/p5-auth-header.test.ts
  - frontend/runs-viewer/e2e/p5-auth-rbac.spec.ts
  - src/research_foundry/cli.py
  - src/research_foundry/cli_commands.py
  - CHANGELOG.md
planning_maturity: scoped
open_questions: []
decisions:
  - {decision: "AuthProvider port: local_static DEFAULT + Clerk OPT-IN + OIDC/BYO seam (ADR-001)", rationale: "Clerk has no self-hosted mode (SPIKE F5); abstraction is the deliverable, Clerk an adapter", status: locked}
  - {decision: "RBAC/user/workspace/membership/audit tables live in a NEW durable store <workspace>/.rf_state/rbac.db, never catalog.db", rationale: "catalog.db drops+rebuilds on user_version mismatch; identity/audit must survive a cache rebuild", status: locked}
  - {decision: "local_static gets a multi-token -> role mapping table, not a single shared bearer", rationale: "Required to generalize TokenAuthMiddleware and support >1 concurrent human identity air-gapped", status: locked}
  - {decision: "P5 sequences AFTER P4; AC-3 validates against P4 real ADR-002 firewall, contract-test fallback if P4 slips", rationale: "User directive P4-then-P5; P5 composes with ADR-002, does not re-implement it", status: locked}
  - {decision: "Public-sharing v1 = read-only sensitivity-scoped share links; defer general public URLs", rationale: "Ships governed-sharing primitive without productizing external URLs; bounded blast radius", status: locked}
  - {decision: "Rate limiting = per-identity + per-route sliding window, config-driven in foundry.yaml", rationale: "Global budget too coarse for multi-user; per-identity is the enforceable unit", status: locked}
  - {decision: "D12 nullable workspace_id/created_by become ENFORCED via a real data migration (dry-run + rollback); schema state is mixed — catalog_items lacks the column and gets it added first", rationale: "Fields exist from P2/P3 forward-compat only on builder_service.py draft records + catalog_service.py's derived catalog_report_drafts index; catalog_items never got them. P5's job is a schema add (catalog_items) plus migration+enforcement everywhere else — not schema design from scratch", status: locked}
  - {decision: "OQ-A: RBAC enforcement wraps routers via a single shared FastAPI dependency require_role(...), not per-route decorators", rationale: "Uniformity for R-P1 target_surfaces enumeration + testability (route-sweep test)", status: locked}
  - {decision: "OQ-B: migration backfill uses one synthetic default workspace for all legacy unscoped records", rationale: "Simplest reversible backfill; revisit only if multi-tenant import is needed later", status: locked}
decision_gates:
  - {gate: "Human gate #1 — P5.3 workspace-migration dry-run reviewed + approved before enforcement", status: pending}
  - {gate: "Human gate #2 — P5.2 RBAC-before-exposure sign-off before any public-facing exposure", status: pending}
  - {gate: "Human gate #3 — P5.4 Clerk secrets handling sign-off before real secrets/production JWKS", status: pending}
success_metrics:
  - "2 auth providers shipped (local_static, clerk) + 1 documented BYO seam (oidc), zero call-site branching on provider identity"
  - "100% of HTTP-routed catalog/report(/agent-job) mutation routes enforce server-side RBAC (0 UI-only gates); CLI/service-direct mutation surface classified admin-only/single-operator-trust and covered by a static contract test (P5.2 RBAC-006)"
  - "4 of 4 run-detail-family endpoints share the no-existence-leak gate (up from 1 of 4)"
  - "100% of 6 governed mutation types produce an audit_event row"
  - "0 cross-workspace leaks in the isolation regression suite"
  - "0 sensitivity regressions in the fail-closed suite across static + live modes"
acceptance_criteria:
  - "AC-1: non-admin cannot view/mutate another workspace's private records (verified_by: cross-workspace-isolation-regression-suite, rbac-route-sweep-test)"
  - "AC-2: public report export fails closed on sensitivity violations (verified_by: publish-preview-fail-closed-regression, blank-origin-draft-sensitivity-regression)"
  - "AC-3: agent credentials never reach browser payloads (verified_by: credential-firewall-composition-test; stub or full depending on P4 ship status)"
  - "AC-4: catalog/builder/agent workflows have E2E coverage (verified_by: e2e-static-mode-run, e2e-live-mode-run)"
  - "AC-5: frontend auth-context abstraction degrades correctly per provider/mode (verified_by: p5-auth-header-test-extended, frontend-auth-context-runtime-smoke)"
execution_mode: hybrid
agent_title: "P5 — Auth/RBAC/Isolation/Audit hardening implementation plan"
agent_summary: >
  9-phase, 47.25-point Tier-3 plan: auth-provider port -> RBAC enforcement -> workspace migration
  (highest-risk, human-gated) -> {Clerk, audit, deferred-sensitivity} in parallel -> rate
  limits/admin/sharing gates -> frontend auth-context UI -> regression/E2E/docs.
contributors_note: null
scores: {}
wave_plan:
  phases:
    - id: P5.1
      depends_on: []
      isolation: worktree
      parallelizable: false
      model: sonnet
      effort: extended
    - id: P5.2
      depends_on: [P5.1]
      isolation: worktree
      parallelizable: false
      model: sonnet
      effort: extended
    - id: P5.3
      depends_on: [P5.2]
      isolation: worktree
      parallelizable: false
      model: sonnet
      effort: extended
    - id: P5.4
      depends_on: [P5.1]
      isolation: worktree
      parallelizable: true
      model: sonnet
      effort: extended
    - id: P5.5
      depends_on: [P5.1]
      isolation: shared
      parallelizable: true
      model: sonnet
      effort: adaptive
    - id: P5.6
      depends_on: [P5.3]
      isolation: shared
      parallelizable: false
      model: sonnet
      effort: adaptive
    - id: P5.7
      depends_on: [P5.1]
      isolation: shared
      parallelizable: true
      model: sonnet
      effort: adaptive
    - id: P5.8
      depends_on: [P5.1, P5.4]
      isolation: shared
      parallelizable: true
      model: sonnet
      effort: adaptive
    - id: P5.9
      depends_on: [P5.5, P5.6, P5.7, P5.8]
      isolation: shared
      parallelizable: false
      model: sonnet
      effort: adaptive
---

# Implementation Plan: Public Multi-User P5 — Auth/RBAC/Isolation/Audit Hardening

**Plan ID**: `IMPL-2026-07-06-PUBLIC-MULTIUSER-P5`
**Date**: 2026-07-06
**Author**: Opus 4.8 (decisions block) + implementation-planner (Sonnet 5, phase expansion)
**Human Brief**: `docs/project_plans/human-briefs/public-multiuser-p5-auth-rbac.md` (to be created next)
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md`
- **SPIKE**: `docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md` — ADR-001 (auth-provider port, binding), ADR-002 (P4 agent-job credential isolation — composed here, not re-implemented)
- **Decisions Block**: `.claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md`

**Complexity**: XL (Tier 3)
**Total Estimated Effort**: 47.25 points
**Sequencing**: after Phase 4 (`public-multiuser-p4-agents-v1`) lands; P5.2's `agent_jobs.py` target surface and P5's AC-3 (credential firewall) compose with P4's ADR-002 once it ships (contract-test fallback if P4 slips).

---

## Executive Summary

Phase 5 converts Research Foundry from a single-trusted-operator tool into a governed multi-user
system: a swappable `AuthProvider` port (local_static default, Clerk opt-in, OIDC/BYO seam),
server-side 5-role RBAC enforced across every mutation route, a real data migration that adds the
`workspace_id` column where it's still missing (`catalog_service.py`'s `catalog_items` table) and
turns P2/P3's unenforced `workspace_id`/`created_by` fields into an isolation boundary everywhere
else, a full audit log, rate limits, admin settings, fail-closed public sharing, and a frontend auth-context
abstraction — while closing the 3 deferred sensitivity gaps carried from P2/P3 (SPIKE FU-4). The
plan is a serial auth-foundation spine (P5.1→P5.2→P5.3) gating a parallel capability slice
(P5.4/P5.5/P5.7), converging on public-exposure gates (P5.6), frontend UI (P5.8), and a final
regression/E2E/docs phase (P5.9). Three Mode-D human sign-off gates block phase exit at the
highest-risk points (migration enforcement, RBAC-before-exposure, Clerk secrets).

---

## Implementation Strategy

### Architecture Sequence

This is a hardening feature, not a fresh CRUD build — the sequence is auth-foundation-first, not
the standard DB→Repo→Service→API→UI layering:

1. **Auth foundation** — `AuthProvider` port + durable RBAC store (P5.1)
2. **RBAC enforcement** — 5-role capability matrix over existing routers (P5.2)
3. **Workspace isolation** — real migration, highest risk, human-gated (P5.3)
4. **Parallel capability slice** (all depend only on P5.1) — Clerk adapter (P5.4), audit log (P5.5),
   deferred-sensitivity closes (P5.7)
5. **Public-exposure gates** — rate limits, admin settings, sharing/publish-preview (P5.6)
6. **Frontend auth-context UI** — consumes P5.2/P5.3/P5.6 backend contracts (P5.8)
7. **Regression + E2E + docs + migration runbook** (P5.9)

### Parallel Work Opportunities

After P5.1 lands (identity contract frozen — `AuthIdentity{user_id, workspace_id, roles}`),
{P5.4 Clerk, P5.5 audit, P5.7 deferred-sensitivity} proceed in parallel — no shared owner, no
file-overlap. P5.8 (frontend) begins once P5.1 and P5.4 contracts stabilize, though its full
seam verification depends on P5.2/P5.3/P5.6 ACs (cross-referenced by task ID in each phase file).

### Critical Path

**P5.1 → P5.2 → P5.3 → P5.6 → P5.9** (auth foundation → RBAC → isolation → public-exposure gates →
validation). This serial spine carries 27.5 of 47.25 points (6+6.5+6+5+4). P5.3 is the single highest-risk
node: an irreversible data migration, human-gated, with its own `karen` milestone review.

### Phase Summary

| Phase | Name | Points | Primary Agent(s) | Secondary Agent(s) | Model/Effort | Offload | Gate |
|-------|------|--------|-------------------|---------------------|--------------|---------|------|
| P5.1 | Auth-provider port + local_static + durable RBAC store | 6 | backend-architect, data-layer-expert | — | sonnet / extended | **MUST-stay — no offload (Mode D)** | task-completion-validator |
| P5.2 | RBAC enforcement (5 roles, server-side) | 6.5 | python-backend-engineer | backend-architect | sonnet / extended | **MUST-stay — no offload (Mode D)** | task-completion-validator + **Human gate #2** |
| P5.3 | Workspace isolation + migration | 6 | data-layer-expert, backend-architect | — | sonnet / extended | **MUST-stay — no offload (Mode D)** | **Human gate #1** + task-completion-validator + **karen** (isolation milestone) |
| P5.4 | Clerk adapter + OIDC/BYO seam | 5 | backend-architect | ui-engineer-enhanced | sonnet / extended | **MUST-stay — no offload (Mode D)** | **Human gate #3** + task-completion-validator |
| P5.5 | Audit log (incl. degraded-health probe + exposure gate, AUDIT-004) | 4.75 | python-backend-engineer | ICA Sonnet 4.6 (offload wave) | sonnet / adaptive | ICA offload, gated behind validator (AUDIT-004 Claude-only) | task-completion-validator |
| P5.6 | Rate limits + admin settings + sharing/publish-preview gates | 5 | python-backend-engineer | ui-engineer | sonnet / adaptive | none | task-completion-validator + **karen** (public-exposure milestone) |
| P5.7 | Deferred sensitivity closes (FU-4) | 5 | python-backend-engineer, data-layer-expert | ICA Sonnet 4.6 (offload wave) | sonnet / adaptive | ICA offload, gated behind validator | task-completion-validator |
| P5.8 | Frontend auth-context + admin UI + role-gated affordances | 5 | ui-engineer-enhanced | ICA Sonnet 4.6 (subcomponents only) | sonnet / adaptive | ICA subcomponents only, gated behind validator | task-completion-validator |
| P5.9 | Regression + E2E + docs + migration runbook | 4 | python-backend-engineer (tests), documentation-writer (docs) | Codex gpt-5.5 (adversarial review, read-only) | sonnet+haiku / adaptive | Codex read-only review only, never implementation | task-completion-validator + **karen** (end-of-feature) + Codex adversarial pass |
| **Total** | — | **47.25** | — | — | — | — | — |

> Estimation rationale and anchors live in the decisions block (§4) and will be carried into the
> Human Brief. This table is the canonical orchestration index — keep synced with phase files.

**Phase files**:
- [Phase 1 — Auth-Provider Port](./public-multiuser-p5-auth-rbac-v1/phase-1-auth-provider-port.md)
- [Phase 2 — RBAC Enforcement](./public-multiuser-p5-auth-rbac-v1/phase-2-rbac-enforcement.md)
- [Phase 3 — Workspace Migration](./public-multiuser-p5-auth-rbac-v1/phase-3-workspace-migration.md)
- [Phase 4 — Clerk Adapter](./public-multiuser-p5-auth-rbac-v1/phase-4-clerk-adapter.md)
- [Phase 5 — Audit Log](./public-multiuser-p5-auth-rbac-v1/phase-5-audit-log.md)
- [Phase 6 — Rate Limits + Admin + Sharing](./public-multiuser-p5-auth-rbac-v1/phase-6-rate-limits-admin-sharing.md)
- [Phase 7 — Deferred Sensitivity](./public-multiuser-p5-auth-rbac-v1/phase-7-deferred-sensitivity.md)
- [Phase 8 — Auth-Context UI](./public-multiuser-p5-auth-rbac-v1/phase-8-auth-context-ui.md)
- [Phase 9 — Regression + E2E + Docs](./public-multiuser-p5-auth-rbac-v1/phase-9-regression-e2e-docs.md)

---

## Human Gates (block phase exit, not just task completion)

| Gate | Phase | Trigger | Approver |
|------|-------|---------|----------|
| **#1** | P5.3 | Workspace-migration dry-run output reviewed and approved, before enforcement is flipped on | Human (operator) |
| **#2** | P5.2 | Server-side RBAC (not UI hiding) confirmed enforcing catalog/report/(agent-job) visibility, before any public-facing exposure | Human (operator) |
| **#3** | P5.4 | Clerk secrets handling reviewed and approved, before the Clerk adapter is wired to real secrets/production JWKS | Human (operator) |

## Reviewer Gates

- `task-completion-validator` at the end of **every** phase (P5.1–P5.9) — mandatory, no exceptions.
- `karen` at three milestones: **P5.3** (isolation milestone), **P5.6** (public-exposure milestone),
  and **end-of-feature** (P5.9, alongside the Codex adversarial pass).
- Codex gpt-5.5 (read-only, P5.9 only) — adversarial review of RBAC enforcement completeness,
  workspace-migration safety, and sensitivity fail-closed guarantees. Never used for implementation.

---

## Risk Mitigation (summary — full detail in decisions block §3)

| Risk | Severity | Mitigation |
|------|----------|------------|
| Workspace migration breaks working single-operator deployments | High | Dry-run + rollback runbook; single-`default`-workspace backfill (OQ-B, locked); Human gate #1; karen isolation milestone; reversible migration |
| Server-side RBAC gaps (UI-only enforcement leak, incl. the CLI/service-direct mutation surface `require_role` structurally cannot reach) | High | R-P1 enumerated router `target_surfaces`; per-route `require_role` sweep test; RBAC-006's CLI/service mutation-surface classification + static contract test; Human gate #2; Codex adversarial pass |
| Sensitivity fail-open regressions during the refactor | High | P2/P3 sensitivity regression suite gates every phase; new existence-gate + global-source-index tests (P5.7) |
| Audit store degrades silently, undermining the audit guarantee with no visible signal | Medium-High | AUDIT-004: durable degraded-health state + startup/on-demand probe + admin warning + public-exposure gate (`is_healthy_for_exposure()`) required before shared/public exposure; individual writes stay fail-open |

---

## Deferred Items & In-Flight Findings Policy

### Deferred Items Triage Table

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---------|----------|------------------|------------------------|-------------------|
| FU-4 (3 sensitivity closes: runs-API existence-gate parity, global source index, draft→run/claim reverse links) | **not deferred — in scope** | N/A — resolved in P5.7 of this plan | N/A | N/A (implemented, not spec'd) |
| FU-2 (concrete OIDC/BYO adapter implementation) | research-needed / dependency-blocked | Only the seam/Protocol lands in P5.1/P5.4 (ADR-001); local_static + Clerk cover the v1 need; no on-prem-IdP consumer exists at ship | An on-prem-IdP consumer emerges | `docs/project_plans/design-specs/oidc-byo-adapter-implementation.md` (authored in P5.9) |
| FU-3 (Clerk paid-plan procurement) | dependency-blocked (operator action) | Custom-role production support requires a paid Clerk plan; this is a human/procurement action, not an engineering task | Operator completes procurement | N/A — assumption row, not a design-spec candidate; Clerk adapter code (P5.4) ships dark-by-default behind a config flag until procurement completes |

**Note on FU-4**: unlike FU-2/FU-3, FU-4 is explicitly **not** a deferred item under this plan — the
decisions block and PRD both scope it as in-plan work closed in P5.7. It appears in this table only
for completeness (it was a deferred item *relative to P2/P3*, not relative to P5). No design-spec
authoring task applies to it; `verified_by` the sensitivity regression suite in P5.7/P5.9 instead.

### In-Flight Findings

Findings doc is NOT pre-created (`findings_doc_ref: null`). Create lazily at
`.claude/findings/public-multiuser-p5-auth-rbac-findings.md` on the first real finding, per
`.claude/skills/planning/references/deferred-items-and-findings.md`.

### Quality Gate

P5.9 (final phase) cannot be sealed until: FU-2 has a design-spec path in
`deferred_items_spec_refs`; FU-3 is documented N/A with rationale (above); and, if
`findings_doc_ref` is populated, the findings doc is finalized (`draft` → `accepted`).

---

## Model & Offload Routing (verbatim from decisions-block §6)

- **P5.1–P5.4**: `sonnet` / `extended`, **MUST-stay — no ICA/Codex offload (Mode D: auth core, RBAC,
  migration, Clerk)**.
- **P5.5**: `sonnet` / `adaptive` — primary `python-backend-engineer`, **offload wave to ICA Sonnet
  4.6** (bounded/contract-clear), gated behind `task-completion-validator`.
- **P5.6**: `sonnet` / `adaptive` — `python-backend-engineer` + `ui-engineer`, no offload.
- **P5.7**: `sonnet` / `adaptive` — `python-backend-engineer`/`data-layer-expert`, **offload wave to
  ICA Sonnet 4.6**, gated behind `task-completion-validator`.
- **P5.8**: `sonnet` / `adaptive` — `ui-engineer-enhanced` primary, **ICA Sonnet 4.6 for
  subcomponents only**, gated behind `task-completion-validator`.
- **P5.9**: tests `sonnet`/`adaptive` (`python-backend-engineer`), docs `haiku`/`adaptive`
  (`documentation-writer`), **Codex gpt-5.5 read-only adversarial review** of RBAC completeness +
  migration safety + sensitivity fail-closed — never for implementation, review only.

---

**Progress Tracking**: `.claude/progress/public-multiuser-p5-auth-rbac/phase-N-progress.md`
(created per phase during execution, not at planning time).

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-07-06
