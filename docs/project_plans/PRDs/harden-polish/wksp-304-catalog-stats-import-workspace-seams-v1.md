---
schema_version: 2
doc_type: prd
title: "PRD: WKSP-304 Catalog Stats and Import Workspace Seams"
description: "Close identity, ownership, visibility, attribution, and non-leakage gaps in catalog statistics and import operations."
status: draft
created: 2026-07-26
updated: 2026-07-26
feature_slug: wksp-304-catalog-stats-import-workspace-seams
feature_version: v1
tier: 2
effort_estimate: 10 pts
requirement_ids: [WKSP-304, P4]
priority: critical
risk_level: high
owner: nick
contributors: []
prd_ref: null
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-catalog-stats-import-workspace-seams-v1.md
human_brief_ref: docs/project_plans/human-briefs/wksp-304-catalog-stats-import-workspace-seams.md
related_documents:
  - docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
  - docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
  - docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md
  - docs/project_plans/reports/audits/di-1-delta-reaudit-2026-07-26.md
  - docs/dev/architecture/adr-runs-workspace-isolation.md
  - docs/project_plans/design-specs/runs-evidence-workspace-isolation.md
  - .Codex/worknotes/wksp-304-catalog-stats-import-workspace-seams/context.md
changelog_required: true
files_affected:
  - src/research_foundry/api/routers/catalog.py
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/export_service.py
  - src/research_foundry/services/audit_service.py
  - tests/unit/test_catalog_service.py
  - tests/unit/test_catalog_terms.py
  - tests/unit/test_rbac_catalog.py
  - tests/test_workspace_isolation_enforcement.py
  - tests/test_serve_catalog.py
  - tests/unit/test_catalog_concurrency.py
  - docs/dev/architecture/auth-rbac-operator-guide.md
  - CHANGELOG.md
tags: [wksp-304, catalog, identity, governance, workspace-isolation, mode-d]
---

# WKSP-304 Catalog Stats and Import Workspace Seams

## 1. Executive Summary

The original WKSP-304 implementation made catalog search and item reads workspace-aware, but the
later DI-1 full-surface audit found two uncovered seams: catalog statistics still aggregate across
all workspaces, and catalog import endpoints capture but discard authenticated identity.
`catalog_service` also stamps every imported row as workspace `"default"` and records no importer
attribution.

This addendum makes the catalog a faithful, derived projection of canonical run ownership and
visibility. It preserves the existing `identity=None` single-user path, keeps Markdown/YAML
evidence bundles and claim provenance authoritative, and does not reopen the completed parent
WKSP-304 plan.

## 2. Problem Statement

In enforcing multi-user mode today:

- `GET /api/catalog/stats` can reveal foreign-private counts, run activity, and import timing;
- authenticated callers can trigger import/re-import without an owner-workspace check;
- imported rows are assigned `"default"` rather than the canonical run workspace;
- catalog rows cannot express public run visibility;
- import audit events omit authenticated actor and workspace attribution;
- sequential idempotency is tested, but concurrent delete-then-insert behavior is not.

These are security and governance gaps. Passing repository tests or serving a healthy endpoint is
not proof of adversarial multi-tenant safety.

## 3. Goals

1. Derive catalog ownership and visibility from canonical run metadata, never caller input.
2. Make own-workspace plus public rows visible across stats, search, detail, links, and facets.
3. Keep public foreign rows read-only to non-owners; public visibility does not confer import
   authority.
4. Deny foreign import attempts before writes with an existence-hiding response.
5. Attribute authenticated imports and denials without fabricating historical actors.
6. Preserve byte-compatible single-user and advisory behavior.
7. Prove rebuild, rollback, and concurrent-write safety without mutating canonical evidence.
8. Keep DI-1 `blocked-external` and every Mode-D signoff human-only.

## 4. Non-Goals

- No shared-store adversarial multi-tenant certification.
- No automated DI-1 acceptance or Mode-D signoff.
- No ownership transfer, public-write capability, cross-workspace admin override, or sharing UI.
- No canonical run/source/claim/evidence migration from catalog data.
- No hosted-service release, deployment, owner-data qualification, or clinical validation claim.

## 5. Binding Product Decisions

### 5.1 Ownership and attribution

- `catalog_items.workspace_id` inherits canonical `run.yaml.workspace_id` through the export
  contract.
- Identity authorizes the operation and supplies actor attribution; it cannot set ownership.
- Missing canonical ownership denies under active isolation.
- `identity=None` preserves the legacy `"default"` behavior.

### 5.2 Public visibility

- Catalog reads use `workspace_id = caller.workspace_id OR visibility = 'public'`.
- Public foreign items are readable and appear in stats/facets.
- Foreign callers cannot import or re-import a public run.
- Sensitivity and visibility remain independent gates; a row must pass both.

### 5.3 Import behavior

- Owner-workspace import is allowed and attributed.
- Foreign private/public and missing-owner targets deny before catalog mutation.
- `import_all(identity=...)` discovers owner-workspace runs only.
- Unauthorized runs contribute no IDs, errors, counts, or timestamps to the response.

## 6. Functional Requirements

| ID | Requirement |
|---|---|
| FR-1 | Thread optional `AuthIdentity` from all three catalog stats/import routes into the service layer. |
| FR-2 | Extend the canonical export projection with immutable run `workspace_id` and normalized `visibility`. |
| FR-3 | Store projected ownership and visibility on every catalog item; remove authenticated-path hardcoding to `"default"`. |
| FR-4 | Apply the own-or-public predicate to stats counts, `runs_indexed`, and `last_import_at`. |
| FR-5 | Apply the same predicate to search, detail, outgoing/incoming links, citing drafts, and project/status/sensitivity/term/role facets. |
| FR-6 | Authorize import against canonical run owner before `BEGIN IMMEDIATE`, delete, insert, FTS, links, terms, or import-log writes. |
| FR-7 | Keep foreign public runs readable but owner-only for import/re-import. |
| FR-8 | Scope bulk discovery to owner runs and prevent unauthorized-run disclosure in summaries/errors. |
| FR-9 | Record authenticated actor ID, actor workspace, canonical owner workspace, action, result, and safe target reference. |
| FR-10 | Bump and rebuild the disposable catalog schema; default absent visibility to workspace-private and never invent historical actor attribution. |
| FR-11 | Preserve `identity=None` and inactive-enforcement behavior for CLI, rebuild, service, and API consumers. |
| FR-12 | Provide bounded SQLite contention handling or a typed bounded failure proven by concurrent-write tests. |

## 7. Requirement Traceability

`P4` is the requested requirement ID, not an execution phase. The implementation plan therefore
uses phase IDs `C1` through `C5`.

| Requirement ID | Product scope | Functional requirements | Acceptance criteria | Execution phases |
|---|---|---|---|---|
| WKSP-304 | Workspace isolation compatibility and enforcement | FR-1–FR-12 | AC-1–AC-12 | C1–C5 |
| P4 | Catalog stats/import seam closure | FR-1–FR-12, with emphasis on FR-4–FR-10 | AC-1–AC-10 | C1–C4 |

## 8. Non-Functional Requirements

- SQL predicates are parameterized and shared from one helper/contract to prevent drift.
- Readers observe a complete old or new import snapshot, never a delete/insert midpoint.
- Item, term, link, FTS, and import-log rows converge in one transaction.
- Run YAML, source-card Markdown, claim ledger, evidence bundles, reports, and anchors remain
  byte-identical across import, rebuild, rollback, interruption, and races.
- Denial is indistinguishable from absence to the caller and auditable server-side.

## 9. Structured Acceptance Criteria

| ID | Acceptance criterion |
|---|---|
| AC-1 | With enforcement active, workspace A stats contain A-private plus public data only; B-private rows do not change counts, run count, facets, or import timestamp. |
| AC-2 | A public foreign item is visible in search/detail/stats/facets; a foreign private item is absent/404. |
| AC-3 | Project, status, sensitivity, term, and role facets contain own/public values and no foreign-private values, including empty-result cases. |
| AC-4 | Owner import succeeds; canonical owner/visibility is projected and importer identity cannot spoof or transfer ownership. |
| AC-5 | Foreign private and foreign public imports return the same external denial as absence and execute zero catalog writes. |
| AC-6 | Bulk import processes only owner runs; errors and totals disclose no unauthorized runs. |
| AC-7 | `audit_service` is the authoritative append-only ledger; success uses an idempotent transactional outbox/event handoff, denial writes no catalog rows, restart replays by stable ID without duplicates, and migration creates no fictional actor history. |
| AC-8 | `identity=None` and inactive enforcement retain existing counts, IDs, payloads, CLI behavior, and `"default"` fallback. |
| AC-9 | Schema mismatch rebuild and rollback preserve deterministic item IDs and byte-identical canonical provenance artifacts. |
| AC-10 | Barrier-synchronized same-run, owner-vs-foreign, import-all-vs-import-run, import-vs-rebuild, reader-vs-import, and audit-pending-vs-restart/swap tests converge without partial, duplicate-attribution, or mixed ownership state. |
| AC-11 | Phase reviewers pass the exact candidate tree; feature-end Karen review passes or returns changes required. |
| AC-12 | No automated artifact or test changes DI-1/Mode-D human status or claims adversarial safety/deployment readiness. |

## 10. Test Scenarios

- own/private, foreign/private, and foreign/public rows under enforcing, advisory, and
  `identity=None` modes;
- foreign-only counts, facets, errors, and timestamps as side-channel probes;
- owner and foreign import attempts with SQL spies proving zero writes on denial;
- spoofed identity workspace versus canonical run owner;
- legacy schema rebuild with absent workspace/visibility;
- failure after delete but before insert and transaction rollback;
- audit append failure → typed `audit_pending` → restart/replay/ack with stable-ID duplicate
  suppression;
- rebuild/swap aborts while any pending audit envelope cannot be flushed;
- interruption before temp-database build, during build, before atomic swap, and after swap with
  valid rollback backup;
- two same-owner imports of one run;
- owner import racing denied foreign import;
- `import_all` racing `import_run` and rebuild;
- stats/search readers held at the transaction barrier;
- complete item/link/term/FTS/import-log convergence;
- hashes and mtimes of canonical Markdown/YAML evidence before and after.

## 11. Dependencies and Gates

- The accepted run ownership/public-visibility ADR is the behavioral precedent.
- The 2026-07-26 DI-1 delta re-audit is the current safety statement.
- DI-1 is `blocked-external`; human Mode-D decision remains pending.
- Tier-2 execution requires `task-completion-validator` at each phase and Karen at feature end.
- Progress artifacts are created only when execution starts through `artifact-tracking`.

## 12. Definition of Done

All AC-1 through AC-12 are covered by executable tests and exact-tree review. Documentation
describes the behavior and its limitations. “Done” means the repository behavior is planned and,
after later execution, technically verified; it never means public deployment, adversarial
multi-tenant certification, owner-data qualification, clinical validation, or hosted release.
