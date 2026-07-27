---
schema_name: ccdash_document
schema_version: 2
doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans
id: BRIEF-wksp-304-catalog-stats-import-workspace-seams
title: "WKSP-304 Catalog Stats and Import Workspace Seams — Human Brief"
status: draft
category: human-briefs
feature_slug: wksp-304-catalog-stats-import-workspace-seams
feature_family: wksp-304-catalog-stats-import-workspace-seams
feature_version: v1
requirement_ids: [WKSP-304, P4]
prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-catalog-stats-import-workspace-seams-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-catalog-stats-import-workspace-seams-v1.md
intent_ref: null
epic_ref: null
related_documents:
  - docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
  - docs/project_plans/reports/audits/di-1-delta-reaudit-2026-07-26.md
  - docs/dev/architecture/adr-runs-workspace-isolation.md
  - .Codex/worknotes/wksp-304-catalog-stats-import-workspace-seams/context.md
owner: nick
contributors: [nick]
audience: [humans]
priority: critical
confidence: 0.85
created: 2026-07-26
updated: 2026-07-26
target_release: null
tags: [human-brief, wksp-304, catalog, identity, governance, mode-d]
---

# WKSP-304 Catalog Stats and Import Workspace Seams — Human Brief

> Human-orchestrator lens. Agents must not load this file unless explicitly instructed.
> Status: draft | Updated: 2026-07-26

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/harden-polish/wksp-304-catalog-stats-import-workspace-seams-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/harden-polish/wksp-304-catalog-stats-import-workspace-seams-v1.md`
- **Parent plan**: `docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md`
- **Current governance verdict**: `docs/project_plans/reports/audits/di-1-delta-reaudit-2026-07-26.md`
- **Decisions**: `.Codex/worknotes/wksp-304-catalog-stats-import-workspace-seams/context.md`

## 2. Estimation Sanity Check

**Bottom-up total**: 10 points.

**H1 — Noun count**: No new canonical CRUD noun. New catalog/import-log columns are disposable
projection plumbing, not new sources of truth.

**H2 — Dual implementation**: Not applied. Catalog SQL is owned directly by the SQLite service;
there is no local/enterprise repository pair in this surface.

**H3 — Algorithmic flag**: Concurrent delete/insert, retry, and snapshot behavior is the flagged
complexity. It receives 2 points and an explicit barrier-synchronized scenario list.

**H4 — Bundle decomposition**:

| Area | Estimate |
|---|---:|
| Catalog projection and migration | 2.0 |
| Identity-scoped reads/facets | 2.0 |
| Governance authorization/attribution | 2.5 |
| Concurrency/provenance proof | 2.0 |
| Plumbing/docs/reviews | 1.5 |
| **Total** | **10.0** |

**H5 — Anchors**: Original WKSP-304 was 10 points; the P5.3 migration package was 6 points; DF-004
is the closest ownership/public-visibility precedent. This addendum is narrower than original
WKSP-304 but adds migration, attribution, and concurrency proof.

**H6 — Hidden plumbing**: 1.5 points, approximately 17.6% of the implementation subtotal, covers
export threading, audit fields, schema/rebuild plumbing, changelog, and gates.

## 3. Wave and Orchestration Notes

**Critical path**: C1 projection contract/schema → C2 own-or-public reads and C3 owner-only imports →
composed migration/concurrency proof → documentation/governance review.

**Parallel opportunities**: Test design may proceed read-only, but all writes to
`catalog_service.py` are serialized under one implementation owner.

**Merge order**: Do not land public visibility without scoped stats/facets, and do not land
authenticated import threading before owner authorization and zero-write denial tests are in the
same candidate tree.

## 4. Open Questions Ledger

| ID | Question | Status | Resolution |
|---|---|---|---|
| OQ-1 | Can a foreign caller import a public run? | resolved | No. Public is read-only; owner workspace retains mutation authority. |
| OQ-2 | Is `last_import_at` global housekeeping data? | resolved | No in authenticated enforcing mode; scope it to own/public rows to remove the activity oracle. |
| OQ-3 | Which value stamps ownership? | resolved | Canonical run metadata; identity only authorizes and attributes. |
| OQ-4 | What is legacy absent visibility? | resolved | Workspace-private. |
| OQ-5 | Can tests close Mode D? | resolved | No. DI-1 and Mode-D decisions remain human-only. |
| OQ-6 | Is the catalog import log the audit authority? | resolved | No. `audit_service` is authoritative; the catalog DB holds only an idempotent transactional outbox/operational projection. |
| OQ-7 | What exactly is rollback? | resolved | Build a sibling DB, atomically swap after validation, retain a bounded prior DB, and restore or deterministically rebuild according to schema compatibility. |
| OQ-8 | Can rebuild discard an unflushed audit envelope? | resolved | No. Rebuild quiesces imports, flushes/acks pending stable IDs, and aborts before swap if the authoritative ledger is unavailable. |

## 5. Deferred Items Rationale

- **Adversarial multi-tenant certification**: outside repository implementation; requires a
  separate human Mode-D decision and re-audit.
- **Cross-workspace public write/import**: explicitly excluded because it changes ownership and
  governance semantics; requires a new design and authorization model.

## 6. Risk Narrative

- The most dangerous shortcut is stamping owner workspace from the authenticated caller. That
  turns reindexing into silent provenance reassignment.
- The easiest side channel to miss is not the item list but `last_import_at`, bulk error IDs, or
  a facet derived from an unscoped join.
- Sequential idempotency is not concurrency proof; the delete/insert midpoint must stay invisible.
- A derived-schema migration is safe only if it never writes back to canonical evidence.

## 7. What to Watch For

- One shared own-or-public predicate, not subtly different SQL per endpoint.
- Public visibility composed with sensitivity, never used as a sensitivity bypass.
- Authorization occurs before `BEGIN IMMEDIATE` and before every write.
- Rebuild never swaps while an audit envelope is pending; restart replay is idempotent.
- No invented historical actor fields during rebuild.
- No phase-complete claim based only on fixtures, LAN health, or repository readiness.

## 8. Expected Success Behaviors

- [ ] Workspace A stats and every facet include A-private plus public, never B-private.
- [ ] Public foreign detail is readable; private foreign detail is indistinguishable from missing.
- [ ] Foreign import of private or public runs produces zero catalog writes.
- [ ] Owner import retains canonical ownership and records truthful actor attribution.
- [ ] Existing identity-free CLI/rebuild behavior remains unchanged.
- [ ] Concurrent imports converge to a complete projection without duplicate/mixed rows.
- [ ] Canonical Markdown/YAML evidence hashes and mtimes remain unchanged.
- [ ] DI-1 remains blocked-external until a human Mode-D decision changes it.

## 9. Running Log

- [2026-07-26] Tier-2 addendum planned from the DI-1 stats/import seam findings. Original
  WKSP-304 completion remains untouched; public visibility is read-only across workspaces.
