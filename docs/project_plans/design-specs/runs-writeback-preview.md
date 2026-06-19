---
title: "Design Spec: Runs Viewer — Writeback-Review Governance View (FR-13)"
doc_type: design_spec
schema_version: 2
status: draft
maturity: idea
created: 2026-06-19
updated: 2026-06-19
feature_slug: runs-frontend
deferred_from: runs-frontend-v1
deferred_item_id: FR-13
category: backlog
owner: nick
related_docs:
  - docs/dev/architecture/rf-run-export-schema.md
  - docs/project_plans/implementation_plans/features/runs-frontend-v1.md
---

# Design Spec: Runs Viewer — Writeback-Review Governance View (FR-13)

> **Maturity: idea** — pre-commitment stub. No implementation has been
> scoped. Promote to `proposal` when the promotion trigger fires.

---

## Deferral Summary

| Field | Value |
|-------|-------|
| **Deferred from** | `runs-frontend-v1` (Phase 5, DOC-006) |
| **Reason** | Writeback preview cards (showing `writebacks/meatywiki_writeback.md`, `skillbom_candidate.md`, `ccdash_event.yaml` content in the viewer) have low traversal value for the current v1 operator workflow. The claim-audit W1 and verification-checklist W2 success metrics cover >80% of daily run-review use. The writeback governance fields (`approved_for_writeback`, `reviewer_notes`, `required_fix`) are visible in the trust panel's governance block — detailed preview is a secondary surface. |
| **Promotion trigger** | `runs-frontend-v1` ships and post-launch observation shows the claim-audit workflow covers >80% of daily use **and** operators report wanting a pre-writeback review surface in the viewer before running `rf writeback`. |
| **Target spec path** | `docs/project_plans/design-specs/runs-writeback-preview.md` (this file) |

---

## Scope (idea-stage)

When promoted, this spec would cover:

- **Writeback candidate cards** — a panel or tab in the run detail view showing:
  - `writebacks/meatywiki_writeback.md` rendered as Markdown (MeatyWiki page preview).
  - `writebacks/skillbom_candidate.md` or `skillbom_candidate.yaml` preview.
  - `writebacks/ccdash_event.yaml` structured view.
- **Governance status display** — surface `evidence_bundle.governance`:
  `approved_for_writeback`, `reviewer_notes`, `required_fix` in a structured
  review-status panel distinct from the current trust-panel governance block.
- **Read-only invariant** — this surface is a *preview*, not an editor. The
  `approved_for_writeback` flag is set by `rf bundle --approve` on disk; the
  viewer renders the current value but cannot change it.
- **Empty-state handling** — graceful empty state when no writeback artifacts
  exist (pre-bundle runs).
- **Export schema extension** — the `run.json` export would need a new
  `writebacks` key with rendered/previewed content. Requires a schema-version
  bump and `backend-architect` re-review per the frozen-schema policy.

### v1 Constraint

In v1, the viewer renders the `governance` block (approval status, reviewer
notes) within the trust panel. Writeback file content is not included in
`run.json` and is not rendered in the SPA. This is intentional — writeback
artifacts are consumed by `rf writeback`, not the viewer.

---

## Notes for Promotion

- The read-only invariant is absolute: even when this surface ships, the SPA
  must not provide a way to set `approved_for_writeback`. That remains a CLI
  operation (`rf bundle --approve`).
- Coordinate with the export schema freeze: adding `writebacks` to `run.json`
  is a breaking change (schema version bump). Plan for it as a v1.1 schema
  update, not a v1.0 patch.
- Consider whether MeatyWiki writeback Markdown renders well with the existing
  report-overlay component, or whether a separate writeback renderer is needed.
