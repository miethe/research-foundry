---
title: "Phase 9: Regression + E2E + Docs + Migration Runbook"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-07-06
updated: 2026-07-06
feature_slug: public-multiuser-p5-auth-rbac
feature_version: "v1"
phase: 9
phase_title: "Regression + E2E + Docs + Migration Runbook"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
entry_criteria:
  - "All of P5.5, P5.6, P5.7, P5.8 complete"
exit_criteria:
  - "Full regression + E2E green in both static and live modes"
  - "CHANGELOG entry present matching this feature"
  - "auth/RBAC docs + migration runbook published"
  - "FU-2 design-spec authored (or explicit blocker if not)"
  - "FU-3 documented N/A"
  - "Codex adversarial review complete with findings triaged (fixed-now or filed as follow-ups)"
  - "karen end-of-feature sign-off"
  - "task-completion-validator sign-off"
related_documents:
  - docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
  - .claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md
  - docs/project_plans/design-specs/oidc-byo-adapter-implementation.md
spike_ref: docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
adr_refs:
  - "ADR-001 (auth-provider port, SPIKE public-multiuser-p4p5-foundations)"
  - "ADR-002 (P4 agent-job credential isolation, composed not re-implemented)"
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: python-backend-engineer
ui_touched: true
target_surfaces:
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/api/routers/catalog.py
  - src/research_foundry/api/routers/reports.py
  - src/research_foundry/api/auth/provider.py
  - src/research_foundry/services/verification.py
  - src/research_foundry/services/export_service.py
  - src/research_foundry/services/audit_service.py
  - src/research_foundry/services/governance.py
  - src/research_foundry/cli_commands.py
  - tests/unit/test_cli_mutation_surface.py
  - frontend/runs-viewer/e2e/p5-auth-rbac.spec.ts
  - frontend/runs-viewer/e2e/w1-claim-audit.spec.ts
  - frontend/runs-viewer/e2e/w3-report-chip-navigation.spec.ts
  - frontend/runs-viewer/src/auth/AuthContext.tsx
  - frontend/runs-viewer/src/app/AppShell.tsx
  - frontend/runs-viewer/src/api/client.ts
seam_tasks:
  - TEST-002
owner: nick
contributors: [python-backend-engineer, documentation-writer, codex-gpt-5.5]
priority: high
risk_level: high
category: "product-planning"
tags: [phase-plan, implementation, auth, rbac, security, public-multiuser, phase-5, regression, e2e, docs, adversarial-review]
milestone: "public-multiuser-p5"
commit_refs: []
pr_refs: []
files_affected:
  - tests/integration/test_p5_regression_suite.py
  - frontend/runs-viewer/e2e/p5-auth-rbac.spec.ts
  - frontend/runs-viewer/e2e/w1-claim-audit.spec.ts
  - frontend/runs-viewer/e2e/w3-report-chip-navigation.spec.ts
  - CHANGELOG.md
  - foundry.yaml
  - docs/dev/architecture/auth-rbac-operator-guide.md
  - docs/dev/architecture/workspace-migration-runbook.md
  - docs/project_plans/design-specs/oidc-byo-adapter-implementation.md
---

# Phase 9: Regression + E2E + Docs + Migration Runbook

**Parent Plan**: [Public Multi-User P5 — Auth/RBAC/Isolation/Audit Hardening](../public-multiuser-p5-auth-rbac-v1.md)
**Duration**: ~3-4 days
**Effort**: 4 story points
**Dependencies**: All of P5.5 (Audit Log), P5.6 (Rate Limits + Admin + Sharing), P5.7 (Deferred Sensitivity), and P5.8 (Auth-Context UI) complete
**Team Members**: `python-backend-engineer` (regression + E2E), `documentation-writer` (docs), Codex gpt-5.5 (read-only adversarial review), `task-completion-validator`, `karen`

---

## Phase Overview

Phase 9 is the **final phase of the 9-phase, 46-point Tier-3 P5 plan**. It does not add new
product surface — it closes the feature out. Three separate concerns converge here, and they
must stay separated in execution and in review:

1. **Regression + E2E** (`TEST-`): prove the whole P5 surface (auth-provider port, RBAC,
   workspace isolation, Clerk, audit, rate limits/sharing, deferred-sensitivity closes, frontend
   auth-context) holds together under a full regression sweep and a real browser E2E pass, in
   both static-export and live-API modes.
2. **Docs** (`DOC-`): the operator/admin-facing surface of everything shipped in P5.1-P5.8, plus
   the two required deferred-item actions (FU-2 design-spec, FU-3 N/A note).
3. **Adversarial review** (`REVIEW-`): a single Codex gpt-5.5 read-only pass over RBAC
   completeness, migration safety, and sensitivity fail-closed guarantees — findings only, never
   implementation.

This phase closes all three Mode-D human gates' downstream verification, both `karen` milestones
already passed (P5.3 isolation, P5.6 public-exposure), and fires the **third and final `karen`
milestone: end-of-feature**.

### Goals

- Prove the P5.1-P5.8 surface is regression-safe across auth providers (`local_static`, `clerk`)
  and both static/live modes.
- Ship full E2E coverage for login, role-bounded catalog/builder actions, and sharing, extending
  (never replacing) the existing `w1`/`w3` specs.
- Close the mandatory documentation set: CHANGELOG, auth/RBAC operator guide, migration runbook,
  FU-2 design-spec (or blocker), FU-3 N/A note.
- Run one read-only adversarial review of the feature's three highest-risk guarantees (RBAC
  completeness, migration safety, sensitivity fail-closed) and triage its findings — fix now or
  file as follow-ups, never silently patched by the reviewer itself.

### Architecture Focus

This phase implements the **Testing → Documentation** layers of Research Foundry's layered
architecture, plus a review gate:

- **Layer**: Testing, Documentation (no Database/Repository/Service/API/UI code is authored here
  beyond test fixtures and doc content)
- **Patterns**: pytest parametrization (provider × mode matrix), Playwright spec extension
  (never rewrite existing specs — P2/P3 precedent), Keep a Changelog `[Unreleased]` entries,
  design-spec `maturity: idea` scaffolding
- **Standards**: R-P4 runtime-smoke gate (this phase's E2E task doubles as the runtime-smoke
  verification for P5.8's `ui_touched` surfaces); the parent plan's Deferred Items & In-Flight
  Findings Policy quality gate (FU-2/FU-3 closure)

### PRD §11 "Documentation Acceptance" Checklist (reproduced verbatim)

- [ ] `foundry.yaml` documents `auth.provider` and its 4 values with the same care as the existing
      `viewer.sensitivity_threshold` comment block.
- [ ] Admin/operator guide for enabling Clerk (prerequisites: outbound internet, public domain,
      paid-plan custom roles).
- [ ] CHANGELOG `[Unreleased]` entry (this feature is user-facing — `changelog_required: true`).
- [ ] ADR-001 and ADR-002 references retained in this PRD's `related_documents`/`spike_ref`; no
      separate ADR file duplication needed unless a future revision changes the decision.

---

## Task Breakdown

### Epic: P5.9 — Regression, E2E, Docs, Adversarial Review

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|-------|--------|--------------|
| TEST-001 | Regression suite (sensitivity/catalog-visibility/job-permission/writeback-approval) | Parametrized regression across auth providers (`local_static`, `clerk`) and static/live modes; job-permission tests compose with P4's ADR-002 credential firewall | See Detailed Spec — reproduces PRD AC-3 verbatim | 1.25 pts | python-backend-engineer | sonnet | adaptive | Phase entry criteria only |
| TEST-002 | Full E2E suite (static + live modes) | New `p5-auth-rbac.spec.ts`; extend (not rewrite) `w1-claim-audit.spec.ts` and `w3-report-chip-navigation.spec.ts` for an authenticated context; doubles as R-P4 runtime-smoke for P5.8 | See Detailed Spec — reproduces PRD AC-4 verbatim | 1.25 pts | python-backend-engineer | sonnet | adaptive | Phase entry criteria only (parallel with TEST-001) |
| DOC-001 | CHANGELOG `[Unreleased]` entry | Mandatory (`changelog_required: true`) — summarize the full P5 feature across Added/Changed/Security sections | Entry present, categorized per `.claude/specs/changelog-spec.md`, references this feature | 0.25 pts | changelog-generator | haiku | adaptive | TEST-001, TEST-002 (summarize what actually shipped/passed) |
| DOC-002 | Auth/RBAC operator & admin guide | Document `foundry.yaml: auth.provider` (4 values) with the same care as `viewer.sensitivity_threshold`; admin guide for enabling Clerk (prerequisites: outbound internet, public domain, paid-plan custom roles) | New guide published; `foundry.yaml` comment block updated | 0.25 pts | documentation-writer | haiku | adaptive | Phase entry criteria only |
| DOC-003 | Workspace-migration operator runbook | Polished operator-facing doc for the Phase 3 dry-run/enforce/rollback procedure — distinct from, and references, Phase 3's internal rollback-runbook task | New runbook published, cross-references Phase 3 | 0.25 pts | documentation-writer | haiku | adaptive | Phase entry criteria only |
| DOC-004 | FU-2 design-spec (OIDC/BYO adapter) + FU-3 N/A note | Author `maturity: idea` design-spec for the concrete OIDC/BYO adapter (FU-2); explicitly mark FU-3 (Clerk paid-plan procurement) N/A for design-spec authoring (operator/procurement action, not an engineering deferred item — mirrors parent plan rationale, not re-litigated) | Design-spec file exists at correct path with correct frontmatter; FU-3 N/A note recorded; follow-up flagged (see AC) | 0.25 pts | documentation-writer | haiku | adaptive | Phase entry criteria only |
| REVIEW-001 | Codex adversarial review: RBAC completeness (incl. CLI/service classification), migration safety, audit exposure-gating, sensitivity fail-closed | Read-only review scoped to Phase 2 `target_surfaces` (RBAC, incl. RBAC-006's CLI/service classification), Phase 3 migration (safety), Phase 5 audit degraded-health/exposure-gating (AUDIT-004 + P5.6 wiring), Phase 7 sensitivity closes + ongoing P2/P3 regression suite (fail-closed) | Findings list produced; each finding triaged fixed-now or filed as a follow-up task — Codex never implements | 0.5 pts | Codex gpt-5.5 (external, read-only) | gpt-5.5-codex | high | TEST-001, TEST-002 |
| **Total** | — | — | — | **4.0 pts** | — | — | — | — |

**Model Selection Guidance**: Sonnet (`python-backend-engineer`) for regression/E2E authoring;
haiku (`documentation-writer`, `changelog-generator`) for all `DOC-` tasks; Codex gpt-5.5 at
`high` effort (adversarial review of this scope warrants the top of the codex effort vocabulary:
`none`/`low`/`medium`/`high`/`xhigh`) for `REVIEW-001`, read-only, never implementation.

---

## Detailed Task Specifications

### Task TEST-001: Regression suite (sensitivity/catalog-visibility/job-permission/writeback-approval)

**Estimate**: 1.25 points
**Assigned Subagent(s)**: python-backend-engineer
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: None (blocked only by phase entry criteria)
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Add/extend a regression suite covering sensitive report text, catalog visibility, job
permissions, and writeback approvals — parametrized across both auth providers (`local_static`,
`clerk`) and both static/live modes. New suite lands at
`tests/integration/test_p5_regression_suite.py`; extends existing sensitivity coverage in
`tests/unit/test_sensitivity_redaction.py` where the P2/P3 suite already lives (do not duplicate,
extend). Job-permission tests compose with P4's ADR-002 credential firewall — this task is the
verification point for PRD AC-3. Coverage is not limited to HTTP routes and UI: this task also
confirms (a) P5.2's `tests/unit/test_cli_mutation_surface.py` (RBAC-006) is still green — the
CLI/service-direct mutation surface's classification hasn't silently regressed — and (b) P5.6 has
actually wired P5.5's `audit_service.is_healthy_for_exposure()` (AUDIT-004) into its sharing/
publish-preview flow, per the coordination note flagged in both those phase files.

#### Structured AC (reproduced verbatim from PRD §11 AC-3)

##### AC-3: Agent credentials never reach browser payloads
- target_surfaces:
    - src/research_foundry/services/audit_service.py
    - src/research_foundry/services/governance.py
- propagation_contract: >
    Composes with P4's ADR-002 (subprocess-per-agent-job, temp-file credential delivery). P5 adds
    the write-time redaction guard (`governance.py::scan_secrets`/`_redact` applied at write time,
    not only post-hoc) and the salted-HMAC key-fingerprint convention to the audit trail.
- resilience: >
    If P4 has not shipped by P5's validation gate, this AC is verified via a stub contract test
    asserting the redaction guard rejects a synthetic credential-shaped payload; full regression
    once P4 lands (OQ-2).
- visual_evidence_required: false
- verified_by:
    - credential-firewall-composition-test

**Acceptance Criteria**:
- [ ] Sensitivity regression (report text) green across both providers and both modes.
- [ ] Catalog-visibility regression (cross-workspace isolation, RBAC route sweep) green across
      both providers and both modes.
- [ ] Job-permission / credential-firewall regression: **check P4 ship status at execution time**
      — if `public-multiuser-p4-agents-v1` has landed, run the full composition regression against
      the real ADR-002 firewall; if it has not, run the stub contract test (synthetic
      credential-shaped payload rejected by the redaction guard) and record which mode was used in
      the Completion Report, per AC-3's resilience note above.
- [ ] Writeback-approval regression green across both providers and both modes.
- [ ] `tests/unit/test_cli_mutation_surface.py` (P5.2 RBAC-006) is confirmed still green as part of
      this suite's run — the CLI/service-direct mutation surface remains correctly classified and
      free of an ungated HTTP bypass.
- [ ] A dedicated assertion confirms `is_healthy_for_exposure()` (P5.5 AUDIT-004) is actually called
      by P5.6's sharing/publish-preview flow before allowing exposure (e.g., a forced-degraded audit
      fixture makes the sharing/publish flow fail closed) — closing the coordination note P5.5
      flagged as pending confirmation by this phase.
- [ ] All regression subsuites pass under `PYTHONPATH`-correct venv invocation (see project memory
      note: `./.venv/bin/python -m pytest`, never the pyenv shim).
- [ ] Existing P2/P3 sensitivity regression suite (`tests/unit/test_sensitivity_redaction.py`,
      `tests/unit/test_export_service.py`) remains green — no regression introduced by P5's
      RBAC/migration refactor (Risk 3 mitigation from decisions-block §3).

**Implementation Notes**:
- Reuse the provider-parametrization pattern already established in P5.1's auth-header tests
  (`frontend/runs-viewer/src/test/p5-auth-header.test.ts` is the frontend precedent; the backend
  equivalent should parametrize via pytest fixtures, not hand-duplicated test functions).
- Job-permission stub-vs-full branching must be an explicit, loud decision in the test file
  (a skip-reason string or a clearly named `test_job_permission_stub_mode` vs
  `test_job_permission_full_mode`), not a silent no-op.
- Do not touch `tests/unit/test_export_service.py` or `tests/unit/test_sensitivity_redaction.py`
  contents beyond what's needed to confirm they still pass — these are pre-existing P2/P3 suites,
  not this phase's deliverable.

**Files Involved**:
- `tests/integration/test_p5_regression_suite.py` - new regression suite (sensitivity, catalog
  visibility, job permissions, writeback approvals; provider × mode matrix); includes the
  audit-exposure-gate cross-check (AUDIT-004/P5.6 wiring confirmation)
- `tests/unit/test_sensitivity_redaction.py` - verify still green (no edits expected)
- `tests/unit/test_export_service.py` - verify still green (no edits expected)
- `tests/unit/test_cli_mutation_surface.py` - verify still green (P5.2 RBAC-006, no edits expected)

---

### Task TEST-002: Full E2E suite (static + live modes)

**Estimate**: 1.25 points
**Assigned Subagent(s)**: python-backend-engineer
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: None (blocked only by phase entry criteria; runs in parallel with TEST-001)
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Add `frontend/runs-viewer/e2e/p5-auth-rbac.spec.ts` covering login-per-provider, role-bounded
catalog/builder actions, and a sharing scenario, in **both** static-export and live-API modes.
Extend (never rewrite) the existing `w1-claim-audit.spec.ts` and
`w3-report-chip-navigation.spec.ts` to exercise an authenticated context. This task is the
verification point for PRD AC-4, and — because it exercises `AuthContext.tsx`/`AppShell.tsx`/
`client.ts` end-to-end — it doubles as the **R-P4 runtime-smoke task** for P5.8's UI-touching
surfaces (this phase's `ui_touched: true` / `seam_tasks: [TEST-002]` frontmatter fields point
here).

#### Structured AC (reproduced verbatim from PRD §11 AC-4)

##### AC-4: Catalog, builder, and agent workflows have E2E coverage
- target_surfaces:
    - frontend/runs-viewer/e2e/p5-auth-rbac.spec.ts
    - frontend/runs-viewer/e2e/w1-claim-audit.spec.ts
    - frontend/runs-viewer/e2e/w3-report-chip-navigation.spec.ts
    - tests/unit/test_cli_mutation_surface.py
    - src/research_foundry/services/audit_service.py
- propagation_contract: >
    New `p5-auth-rbac.spec.ts` covers login (per provider), role-bounded catalog/builder actions,
    and a sharing scenario, in both static-export and live-API modes; existing `w1`/`w3` specs are
    extended (not rewritten) to exercise an authenticated context. Coverage is not limited to the
    browser: the CLI/service-direct mutation surface is covered by P5.2's static contract test
    (`tests/unit/test_cli_mutation_surface.py`, not a Playwright spec — the CLI has no browser to
    drive), and audit-event emission (`audit_service.py`) for each exercised workflow is asserted as
    part of TEST-001's regression suite, not only the E2E flow.
- resilience: >
    Static-export mode has no server; auth-gated scenarios in static mode assert the read-only
    public degradation instead of a login flow.
- visual_evidence_required: false
- verified_by:
    - e2e-static-mode-run
    - e2e-live-mode-run
    - cli-mutation-surface-contract-test

**Acceptance Criteria**:
- [ ] `p5-auth-rbac.spec.ts` exists and covers: login per provider (`local_static`, `clerk`),
      role-bounded catalog/builder actions (at least one allowed + one denied action per role
      tier), and a sharing scenario (fail-closed on sensitivity, per AC-2).
- [ ] `w1-claim-audit.spec.ts` extended (diff-only, not rewritten) to run its existing scenarios
      under an authenticated context.
- [ ] `w3-report-chip-navigation.spec.ts` extended (diff-only, not rewritten) to run its existing
      scenarios under an authenticated context.
- [ ] Static-export mode: auth-gated scenarios assert read-only public degradation (no login flow
      attempted) per AC-4's resilience note.
- [ ] Live-API mode: full login → role-bounded action → sharing scenario flow passes for both
      providers.
- [ ] Runtime-smoke evidence captured for AC-5's three provider states (`clerk`, `local_static`,
      `none`) at desktop ≥1440px, per PRD AC-5 `visual_evidence_required`; screenshots saved to
      `.claude/evidence/phase-9/` (R-P4 gate — this satisfies P5.8's smoke requirement from this
      verification phase, since a clean unit-test pass alone is not a substitute per R-P4).
- [ ] `npm run build` (or project-equivalent) succeeds before the Playwright run.

**Implementation Notes**:
- "Extend, never rewrite" is a hard constraint carried from P2/P3 precedent (see PRD FR-17 note)
  — diff the existing spec files, do not replace their contents wholesale.
- The sharing scenario should reuse P5.6's read-only sensitivity-scoped share link, not a
  speculative new sharing surface.
- The CLI/service-direct mutation surface is **not** in this task's own scope — it has no browser to
  drive a Playwright spec against. This task cross-references `tests/unit/test_cli_mutation_surface.py`
  (P5.2 RBAC-006) only for AC-4's target_surfaces completeness; re-verifying that test stays green is
  TEST-001's job, not this one's.
- Screenshot evidence path convention: `.claude/evidence/phase-9/auth-context-<provider>.png`
  (one per provider state: `clerk`, `local-static`, `none`).

**Files Involved**:
- `frontend/runs-viewer/e2e/p5-auth-rbac.spec.ts` - new E2E spec (login, role-bounded actions,
  sharing, both modes)
- `frontend/runs-viewer/e2e/w1-claim-audit.spec.ts` - extend for authenticated context
- `frontend/runs-viewer/e2e/w3-report-chip-navigation.spec.ts` - extend for authenticated context

---

### Task DOC-001: CHANGELOG `[Unreleased]` entry

**Estimate**: 0.25 points
**Assigned Subagent(s)**: changelog-generator
**Model**: haiku
**Effort**: adaptive
**Dependencies**: TEST-001, TEST-002 (entry should reflect what actually shipped/passed, not a
speculative pre-write)
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
This feature has `changelog_required: true` in the parent plan's frontmatter — this task is
**mandatory, not optional**. Add a `CHANGELOG.md` `[Unreleased]` entry summarizing the P5 feature:
`AuthProvider` port (local_static/Clerk/OIDC seam), server-side 5-role RBAC, workspace isolation
migration, audit log, rate limits, admin settings, fail-closed sharing, and frontend auth-context.
Categorize per `.claude/specs/changelog-spec.md` (likely spans **Added** for new capability and
**Security** for the RBAC/isolation/audit guarantees).

**Acceptance Criteria**:
- [ ] `[Unreleased]` section in `CHANGELOG.md` contains an entry (or entry group) for this
      feature, following the bold-title + em-dash + user-perspective-sentence convention.
- [ ] Categorized correctly: new capability (auth provider, RBAC, audit, sharing) → **Added**;
      any behavior change to previously-open routes (e.g., existence-gate parity) →
      **Fixed**/**Security** as appropriate.
- [ ] Does not include implementation-only details (file/function names) per the changelog spec's
      entry conventions.

**Implementation Notes**:
- Use `.claude/specs/changelog-spec.md` categorization table directly — do not invent a new
  section ordering.
- Reference examples in that spec's "Security" section (RLS/key-storage entries) as the closest
  precedent for how to phrase the RBAC/isolation/audit entries.

**Files Involved**:
- `CHANGELOG.md` - add `[Unreleased]` entry/entries for the P5 feature

---

### Task DOC-002: Auth/RBAC operator & admin guide

**Estimate**: 0.25 points
**Assigned Subagent(s)**: documentation-writer
**Model**: haiku
**Effort**: adaptive
**Dependencies**: None (blocked only by phase entry criteria)
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Document `foundry.yaml: auth.provider` and its 4 values (`none`, `local_static`, `clerk`, `oidc`)
with the same level of care as the existing `viewer.sensitivity_threshold` comment block
(`foundry.yaml:22-40` — note its fail-closed-default rationale narrative as the bar to match, not
just a one-line description per value). Also author an admin guide for enabling Clerk, covering
its three prerequisites: outbound internet, a public domain, and a paid Clerk plan for custom
roles (FU-3).

**Acceptance Criteria**:
- [ ] `foundry.yaml`'s `auth.provider` block gets a comment describing all 4 values, each
      adapter's requirements (`local_static`: zero-dependency, air-gapped default; `clerk`:
      outbound internet + paid plan for custom roles; `oidc`: seam only, concrete impl may not
      exist yet), and the fail-closed default rationale — matching the density of the
      `viewer.sensitivity_threshold` block.
- [ ] New guide at `docs/dev/architecture/auth-rbac-operator-guide.md` covers: role model (5
      roles + capability matrix), enabling Clerk (3 prerequisites above), and where audit/rate-
      limit config lives.
- [ ] Guide cross-references PRD (`public-multiuser-p5-auth-rbac-v1.md`) and SPIKE ADR-001/ADR-002.

**Implementation Notes**:
- Read `foundry.yaml`'s existing `viewer.sensitivity_threshold` comment block directly for the
  tone/density bar (it includes a rationale narrative, not just a value list) before drafting the
  `auth.provider` block.
- Keep this doc operator-facing (config + prerequisites + role model), not an implementation
  walkthrough — implementation detail belongs in code comments / the plan's phase files, not here.

**Files Involved**:
- `foundry.yaml` - extend `auth.provider` comment block
- `docs/dev/architecture/auth-rbac-operator-guide.md` - new operator/admin guide

---

### Task DOC-003: Workspace-migration operator runbook

**Estimate**: 0.25 points
**Assigned Subagent(s)**: documentation-writer
**Model**: haiku
**Effort**: adaptive
**Dependencies**: None (blocked only by phase entry criteria)
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Author the **operator-facing** version of the Phase 3 workspace-migration dry-run/enforce/
rollback procedure. This is distinct from, and references, Phase 3's internal rollback-runbook
task (the implementation-level rollback procedure authored as part of `phase-3-workspace-
migration.md` — exact internal task ID to be confirmed once that phase file is authored; this
DOC-003 task is the polished, operator-consumable version of that internal artifact, not a
duplicate of it).

**Acceptance Criteria**:
- [ ] New runbook at `docs/dev/architecture/workspace-migration-runbook.md` covers: what the
      migration does (backfills `workspace_id`/`created_by` to a single synthetic `default`
      workspace per OQ-B), how to run the dry-run, how to review dry-run output (this is the
      artifact Human Gate #1 approval is based on), how to flip enforcement on, and the rollback
      procedure if enforcement needs to be reversed.
- [ ] Runbook explicitly cross-references Phase 3's internal rollback-runbook task by relative
      path (`./phase-3-workspace-migration.md`), rather than re-deriving the procedure from
      scratch.
- [ ] Runbook is operator-facing (assumes no prior context on the migration's implementation),
      consistent with the "polished operator-facing version" framing above.

**Implementation Notes**:
- Do not re-litigate the migration's implementation details here — link to Phase 3's phase file
  for the technical procedure; this doc's job is operator usability (when to run it, what the
  output means, when it's safe to flip enforcement, how to back out).
- If Phase 3's phase file does not yet exist on disk at the time this task executes, note the
  cross-reference as "pending — see parent plan §Phase Boundaries P5.3" rather than inventing a
  broken link.

**Files Involved**:
- `docs/dev/architecture/workspace-migration-runbook.md` - new operator-facing migration runbook

---

### Task DOC-004: FU-2 design-spec (OIDC/BYO adapter) + FU-3 N/A note

**Estimate**: 0.25 points
**Assigned Subagent(s)**: documentation-writer
**Model**: haiku
**Effort**: adaptive
**Dependencies**: None (blocked only by phase entry criteria)
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Author a `design_spec` at `docs/project_plans/design-specs/oidc-byo-adapter-implementation.md`
for FU-2 (concrete OIDC/BYO adapter implementation) with `maturity: idea` — this deferred item
needs research into on-prem-IdP-consumer demand before it can be shaped further; only the seam/
Protocol lands in P5.1/P5.4 (ADR-001), not a concrete implementation. Set `prd_ref` to this
feature's PRD path. FU-3 (Clerk paid-plan procurement) is explicitly **N/A** for design-spec
authoring in this same task — it is an operator/procurement action, not an engineering deferred
item (this mirrors the parent plan's Deferred Items Triage Table rationale verbatim; do not
re-litigate it here, just execute the N/A by recording it in this task's evidence).

**Acceptance Criteria**:
- [ ] `docs/project_plans/design-specs/oidc-byo-adapter-implementation.md` exists with frontmatter:
      `schema_version: 2`, `doc_type: design_spec`, `maturity: idea`,
      `feature_slug: oidc-byo-adapter-implementation`,
      `prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md`, and
      `open_questions` capturing at minimum "does an on-prem-IdP consumer exist yet?" as the
      promotion trigger (per the parent plan's Deferred Items Triage Table).
- [ ] FU-3 N/A note recorded in this task's completion evidence (a short note referencing the
      parent plan's Deferred Items Triage Table row for FU-3 — no new file created for FU-3).
- [ ] **Follow-up action flagged (not performed by this task)**: after this phase completes, the
      **parent plan's** (`docs/project_plans/implementation_plans/features/public-multiuser-p5-
      auth-rbac-v1.md`) `deferred_items_spec_refs` frontmatter list must be updated by the
      orchestrator to append this design-spec's path. This edit is out of scope for this task
      (it targets the parent plan's frontmatter, not this phase file) — it is called out here as a
      required downstream step, not silently assumed to happen.

**Implementation Notes**:
- Follow the design_spec frontmatter schema exactly (see planning skill's design_spec examples) —
  `maturity: idea` is mandatory, not `shaping` or `ready`, since no on-prem-IdP consumer exists yet.
- Keep the design-spec itself light — it documents the *absence* of present demand and the shape
  of the seam already defined by ADR-001, not a speculative full OIDC implementation plan.
- Do not touch the parent plan's frontmatter as part of this task (see the flagged follow-up
  action above) — this task authors the design-spec file only.

**Files Involved**:
- `docs/project_plans/design-specs/oidc-byo-adapter-implementation.md` - new design-spec,
  `maturity: idea`

---

### Task REVIEW-001: Codex adversarial review — RBAC completeness, migration safety, sensitivity fail-closed

**Estimate**: 0.5 points
**Assigned Subagent(s)**: Codex gpt-5.5 (external, read-only)
**Model**: gpt-5.5-codex
**Effort**: high
**Dependencies**: TEST-001, TEST-002
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
One read-only adversarial review, scoped to four surfaces: **Phase 2's** `target_surfaces`
(RBAC completeness — every HTTP mutation route across catalog/reports/builder/(agent-jobs) enforces
`require_role`, **and** the CLI/service-direct mutation surface is genuinely classified
admin-only/single-operator-trust with no undocumented HTTP bypass — RBAC-006), **Phase 3's**
migration (safety — dry-run/enforce/rollback correctness, backfill completeness for the synthetic
`default` workspace), **Phase 5's** audit-store degraded-health handling (AUDIT-004 — the health
probe/degraded state is real, not cosmetic, and P5.6 actually gates shared/public exposure on
`is_healthy_for_exposure()` rather than the check existing unused), and **Phase 7's**
deferred-sensitivity closes plus the ongoing P2/P3 regression suite (fail-closed guarantees —
existence-gate parity, global source index, no sensitivity fail-open regression introduced by this
feature's refactor). This is **read-only**: Codex proposes findings, it does not implement fixes.
Effort is set to `high` — the top of the codex effort vocabulary (`none`/`low`/`medium`/`high`/
`xhigh`) short of `xhigh` — because adversarial review of RBAC/migration/audit/sensitivity
completeness across an entire Tier-3 feature warrants a high reasoning budget, but this is a review
pass, not a debug-escalation scenario that would justify `xhigh`.

**Acceptance Criteria**:
- [ ] Review report covers all four scoped surfaces (RBAC completeness including the CLI/service
      classification, migration safety, audit degraded-health/exposure-gating, sensitivity
      fail-closed) with explicit findings, not a general narrative.
- [ ] Every finding is triaged: either **fixed-now** (a small, targeted follow-up commit made by
      a Claude agent, never by Codex itself) or **filed as a follow-up task** (new task, not
      silently absorbed into this phase's scope).
- [ ] Codex made zero code edits — verify via `git diff` / `git status` showing no changes
      attributable to the Codex session.
- [ ] Review explicitly checks the RBAC route-sweep completeness (every mutation route across
      catalog/reports/builder/agent-jobs has a `require_role` dependency — R-P1 target-surfaces
      enumeration from Phase 2), the CLI/service mutation-surface classification's honesty (RBAC-006
      — is the "no HTTP bypass" claim actually enumerated and tested, or asserted without proof?),
      the migration's `default`-workspace backfill completeness (OQ-B), whether P5.6 genuinely calls
      `is_healthy_for_exposure()` before exposure or merely built the check without wiring it
      (AUDIT-004), and existence-gate parity across all 4 run-detail-family endpoints (FR-13).

**Implementation Notes**:
- Route this task to Codex gpt-5.5 in **read-only mode** — no write/edit tool access. If the
  orchestrating harness cannot enforce this at the tool-permission level, enforce it at the
  prompt level and verify post-hoc via `git status`.
- Findings that require code changes become **new tasks**, tracked outside this phase file (this
  phase does not spawn its own dynamically-numbered follow-up tasks at planning time — that is an
  execution-time artifact, e.g. a findings doc or a fast-follow plan).
- Never route Mode-D-adjacent findings (auth core, RBAC, migration) to Codex for fixing — Codex
  is review-only for this entire feature per the decisions block §6 model routing notes.

**Files Involved**:
- None (read-only review; no files are edited by this task)

---

## Quality Gates

This phase is complete when:

- [ ] **Functional**: Full regression suite (TEST-001) and full E2E suite (TEST-002) both green,
      in both static-export and live-API modes, across both auth providers.
- [ ] **Testing**: Job-permission/credential-firewall regression explicitly records stub-vs-full
      mode used (per AC-3 resilience note); AC-5's 3 provider-state screenshots captured.
- [ ] **Performance**: N/A for this phase (no new runtime surface; performance budgets were set in
      P5.1/P5.6).
- [ ] **Security**: Codex adversarial review (REVIEW-001) complete; every finding triaged
      fixed-now or filed as a follow-up — none silently dropped.
- [ ] **Documentation**: DOC-001 through DOC-004 all complete — CHANGELOG entry present, auth/RBAC
      operator guide + migration runbook published, FU-2 design-spec authored, FU-3 N/A note
      recorded.
- [ ] **Code Quality**: New test files (`test_p5_regression_suite.py`, `p5-auth-rbac.spec.ts`)
      pass lint (`flake8`/`eslint` as applicable); no lint regressions in extended `w1`/`w3` specs.
- [ ] **Architecture**: Test/doc-only phase — confirms, does not alter, the layered architecture
      established in P5.1-P5.8.
- [ ] **Seam verification** (`integration_owner: python-backend-engineer` set): `seam_tasks:
      [TEST-002]` completed and its `verified_by` references populated (R-P3) — TEST-002 is the
      cross-owner (backend identity/RBAC contract + frontend auth-context) verification point.
- [ ] **Runtime smoke** (`ui_touched: true`): screenshot evidence in `.claude/evidence/phase-9/`
      for all 3 AC-5 provider states (`clerk`, `local_static`, `none`) at desktop ≥1440px — a
      clean unit-test pass alone is not a substitute (R-P4).
- [ ] **Deferred Items Quality Gate** (parent plan's Deferred Items & In-Flight Findings Policy):
      FU-2 has a design-spec path ready to be appended to the parent plan's
      `deferred_items_spec_refs`; FU-3 is documented N/A with rationale; if a findings doc was
      created during execution (`findings_doc_ref` populated), it is finalized (`draft` →
      `accepted`) before this phase seals.

### Reviewer Gates (all required — end-of-feature gate)

- **`task-completion-validator`** — mandatory, as at every prior P5 phase.
- **`karen`** — **end-of-feature milestone**, the third and final `karen` sign-off in this plan
  (alongside the P5.3 isolation milestone and P5.6 public-exposure milestone already passed).
- **Codex adversarial pass (REVIEW-001)** — itself a reviewer gate, not just a task; this phase
  cannot seal until REVIEW-001's findings are triaged, independent of `karen`'s sign-off.

None of these three gates substitute for another — all three must clear before this phase (and the
feature) is marked complete.

---

## Integration Points

### External Systems

- **Codex gpt-5.5** (`REVIEW-001`): external, read-only adversarial review. No write access; no
  production dependency — a review-time-only integration.
- **Clerk** (indirect, via TEST-001/TEST-002 provider parametrization): tests exercise the
  `clerk` adapter's contract surface, not a live Clerk tenant — no new external dependency
  introduced by this phase.

### Internal Systems

- **P4 Embedded Agent Research** (`public-multiuser-p4-agents-v1`): TEST-001's job-permission
  regression composes with P4's ADR-002 credential firewall if it has shipped by this gate;
  degrades to a stub contract test otherwise (AC-3).
- **P5.1-P5.8 (all prior P5 phases)**: this phase is the closing verification/documentation layer
  over all of them — no new backend/frontend capability is introduced here.
- **Parent plan's Deferred Items & In-Flight Findings Policy**: DOC-004 produces the FU-2
  design-spec this policy's quality gate requires; the parent plan's frontmatter update itself
  is a flagged follow-up, not part of this phase's task set.

---

## Key Files Modified

| File Path | Lines | Purpose | Subagent |
|-----------|-------|---------|----------|
| `tests/integration/test_p5_regression_suite.py` | new file | Provider × mode regression suite (sensitivity, catalog visibility, job permissions, writeback approvals) | python-backend-engineer |
| `frontend/runs-viewer/e2e/p5-auth-rbac.spec.ts` | new file | Login/role-bounded/sharing E2E, static + live modes | python-backend-engineer |
| `frontend/runs-viewer/e2e/w1-claim-audit.spec.ts` | extend | Add authenticated-context scenarios | python-backend-engineer |
| `frontend/runs-viewer/e2e/w3-report-chip-navigation.spec.ts` | extend | Add authenticated-context scenarios | python-backend-engineer |
| `CHANGELOG.md` | `[Unreleased]` section | Mandatory P5 feature entry | changelog-generator |
| `foundry.yaml` | `auth.provider` comment block | Document 4 provider values | documentation-writer |
| `docs/dev/architecture/auth-rbac-operator-guide.md` | new file | Operator/admin guide (roles, Clerk prerequisites) | documentation-writer |
| `docs/dev/architecture/workspace-migration-runbook.md` | new file | Operator-facing migration dry-run/enforce/rollback runbook | documentation-writer |
| `docs/project_plans/design-specs/oidc-byo-adapter-implementation.md` | new file | FU-2 design-spec, `maturity: idea` | documentation-writer |

---

## Testing Strategy

### Unit Tests

- No new unit tests beyond what TEST-001 introduces at the integration level; existing
  `tests/unit/test_sensitivity_redaction.py` and `tests/unit/test_export_service.py` are verified
  green, not modified.

### Integration Tests

- `tests/integration/test_p5_regression_suite.py`: the provider × mode matrix (2 providers × 2
  modes = 4 combinations minimum) across sensitivity, catalog-visibility, job-permission, and
  writeback-approval scenarios.
- Job-permission composition test against P4's ADR-002 (full or stub, per ship status at
  execution time).

### E2E Tests

- `p5-auth-rbac.spec.ts`: login per provider, role-bounded catalog/builder actions, sharing
  scenario — both static-export and live-API modes.
- Extended `w1-claim-audit.spec.ts` and `w3-report-chip-navigation.spec.ts`: existing scenarios
  re-run under an authenticated context.
- Runtime-smoke screenshots for AC-5's 3 provider states, satisfying R-P4 for P5.8's UI surfaces.

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| P4 has not shipped by this gate, leaving AC-3 unverifiable in full | Medium | Stub contract test path is pre-defined (not improvised at execution time); Completion Report must state explicitly which mode (stub/full) validated AC-3, per OQ-2. |
| Codex adversarial review surfaces a Mode-D-adjacent finding (auth core/RBAC/migration) that looks urgent | High | Findings are triaged, never auto-fixed by Codex; any fix that touches Mode-D territory (P5.1-P5.4 scope) requires the same human-gate discipline as the original phase, even as a "fast follow." |
| `w1`/`w3` spec extension accidentally becomes a rewrite, breaking pre-existing coverage | Medium | AC explicitly requires diff-only extension; review diffs before merge to confirm no wholesale replacement. |
| DOC-004's parent-plan frontmatter follow-up is silently forgotten after this phase closes | Medium | Explicitly flagged as a required downstream action in this task's AC and in this phase's Quality Gates section — not left implicit. |
| Regression suite passes on `local_static` but silently skips `clerk` parametrization (partial coverage reported as full) | High | AC requires explicit assertion that both providers ran, not just that the suite exited 0 (a skipped-parametrization false green is the failure mode R-P1/R-P2 discipline exists to catch). |

---

## Success Metrics

- **Completion**: All 7 tasks (TEST-001, TEST-002, DOC-001-004, REVIEW-001) checked off.
- **Quality**: All Quality Gates passed, including seam verification and runtime smoke.
- **Performance**: N/A — no new runtime surface introduced this phase.
- **Testing**: Full regression + E2E green in both static and live modes, across both providers,
  per this phase's exit criteria.

---

## Notes

### Implementation Approach

Run `TEST-001` and `TEST-002` in parallel (no shared files, no dependency between them) alongside
`DOC-002`/`DOC-003`/`DOC-004` (also independent of the test tasks and of each other). `DOC-001`
(CHANGELOG) should be authored last among the doc tasks since it summarizes what actually shipped
and passed — sequence it after TEST-001/TEST-002 land, even though it has no hard file-level
dependency. `REVIEW-001` runs last, after the regression/E2E evidence exists for it to review
against.

### Gotchas

- **pytest interpreter**: regression suite must run under `./.venv/bin/python -m pytest` (or
  `uv run pytest`) — the recurring "No module named research_foundry" failure is a wrong-
  interpreter problem, not a code bug (project memory: pytest-must-run-under-venv).
- **Worktree PYTHONPATH**: if this phase executes in a worktree, validating against worktree code
  needs `PYTHONPATH=<worktree>/src <main-repo>/.venv/bin/python`, since the editable install
  points at the main checkout (project memory: rf-test-suite-gotchas).
- **Full pytest pollution**: running the entire suite (not scoped to the new regression file) can
  pollute tracked real-run fixture files; scope test runs to the new/relevant files during
  iteration.
- **Codex read-only enforcement**: if the harness cannot hard-block Codex's write access, verify
  post-hoc with `git status`/`git diff` that REVIEW-001 made zero edits before accepting its
  findings as review-only.

### Learnings

_Capture as phase progresses — not populated at planning time._

### Findings Captured This Phase

- [x] No new findings this phase (default) — findings doc (`findings_doc_ref`) is not
      pre-created and remains `null` until a real finding occurs during execution, per
      `.claude/skills/planning/references/deferred-items-and-findings.md` and the parent plan's
      §Deferred Items & In-Flight Findings Policy.

---

**Phase Version**: 1.0
**Last Updated**: 2026-07-06

[Return to Parent Plan](../public-multiuser-p5-auth-rbac-v1.md)
