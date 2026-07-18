---
title: "Feature Contract: Runs Writeback-Review Governance View (FR-13)"
schema_version: 2
doc_type: feature_contract
it_schema: 1
description: "Upgrade the runs-viewer Writeback tab from a status stub into a governance review surface with rendered writeback-candidate cards and reviewer_notes/required_fix visibility."
status: draft
created: 2026-07-18
updated: 2026-07-18
feature_slug: "runs-writeback-review-view"
category: "features"
estimated_points: 6
tier: 1
owner: null
priority: medium
risk_level: medium
changelog_required: true
node_type: work_package
acceptance_criteria: []
definition_of_done: null
execution_mode: unassigned
agent_title: null
agent_summary: null
agent_context: null
open_questions: []
decisions: []
scores: {}
related_documents:
  - docs/project_plans/design-specs/runs-writeback-preview.md
  - docs/dev/architecture/rf-run-export-schema.md
  - docs/project_plans/implementation_plans/features/runs-frontend-v1.md
spike_ref: null
prd_ref: null
plan_ref: null
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/services/export_service.py
  - schemas/evidence_bundle.schema.yaml
  - frontend/runs-viewer/src/types/rf/run-export.ts
  - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
  - frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx
  - CHANGELOG.md
---

> **Promotion source:** `docs/project_plans/design-specs/runs-writeback-preview.md` (deferred from
> `runs-frontend-v1` Phase 5 / DOC-006, deferred item `FR-13`). Promotion trigger fired per
> `frontend/public-release-activation` theme prep: the viewer now needs a pre-writeback review
> surface, and code-truth grounding below shows the export/type scaffolding for this feature is
> already ~40% in place — this is a completion job, not a from-scratch build.

# Feature Contract: Runs Writeback-Review Governance View (FR-13)

## 1. Goal

Turn the runs-viewer's existing "Writeback" tab — today a minimal status stub — into a read-only
governance review surface that renders each writeback candidate's content (MeatyWiki page,
SkillBOM candidate, CCDash event) alongside the run's full governance verdict
(`approved_for_writeback`, `reviewer_notes`, `required_fix`), so an operator can review a run's
writeback candidates in the viewer before running `rf bundle --approve` on the CLI.

---

## 2. User / Actor

- **Primary user**: The RF operator reviewing a completed run before deciding whether to approve
  it for writeback — today they must open `runs/<id>/writebacks/*.md`/`*.yaml` in a text editor to
  see candidate content; this feature surfaces it in the viewer they're already using.
- **Secondary users**: A second reviewer validating a council `required_block`/`revise` decision
  who needs to see `reviewer_notes`/`required_fix` without shelling into the run directory.

---

## 3. Job To Be Done

When **a run has emitted writeback candidate files and the operator is deciding whether to
approve it for writeback**, the operator wants to **see each candidate's rendered content plus the
governance verdict in one place**, so they can **make an informed approve/revise decision without
leaving the viewer, while trusting that the viewer itself cannot change that verdict.**

---

## 4. Scope

### In Scope

**Export schema (backend, precondition — see §8 review gate):**
- Extend `_collect_writebacks()` in `src/research_foundry/services/export_service.py` to populate
  two fields that are **already declared in the TypeScript type
  (`RFRunWritebacksSummary` at `frontend/runs-viewer/src/types/rf/run-export.ts:296-302`) but never
  populated by the backend today**: `reviewer_notes` and `required_fix`. Source them from
  `evidence_bundle.governance` (`additionalProperties: true` in
  `schemas/evidence_bundle.schema.yaml:59-78` — confirm at implementation time whether
  `rf bundle --approve` / the council review path writes these directly onto
  `governance.{reviewer_notes,required_fix}` or onto a linked `review_packet` artifact
  (`schemas/review_packet.schema.yaml` already defines both fields under `output.concerns[]` and a
  top-level `reviewer_notes`); read from whichever is the actual source of truth).
- Add rendered content to the existing (currently `unknown[]`, always-empty) `previews` field on
  `RFRunWritebacksSummary`. Define a concrete shape,
  `{ target: string; filename: string; content_type: "markdown" | "yaml"; content: string }[]`, one
  entry per file already enumerated in `_WRITEBACK_TARGETS`
  (`meatywiki_writeback.md`, `skillbom_candidate.md`, `ccdash_event.yaml`, plus the three other
  known targets already mapped in that dict). Content **must** pass through the export's existing
  redaction path (`_redact_str_values`, `export_service.py:770`) — writeback file content is not
  exempt from the sensitivity gate applied to every other exported field.
- Bump `EXPORT_SCHEMA_VERSION` (currently `"1.5"`) to `"1.6"` — additive/populates-previously-null
  fields only, no key removal or type narrowing.
- Update `RFRunWritebacksSummary.previews` in `frontend/runs-viewer/src/types/rf/run-export.ts` from
  `unknown[] | null` to the concrete typed array above.

**Frontend — RunDetail Writeback tab (builds on the existing stub, does not create a new tab):**
- Upgrade the `activeTab === "writeback"` branch in
  `frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx` (~line 165-190) from its
  current single `<dl>` status block into:
  - A **governance status panel**: `approved_for_writeback` (existing), plus the two newly-exported
    `reviewer_notes` and `required_fix` fields (currently declared on the type but rendered
    nowhere in the codebase — confirmed via grep). Visually distinct from the existing Trust Panel
    governance block (`frontend/runs-viewer/src/components/TrustPanel/TrustPanel.tsx:139-151`) —
    that block stays as-is; this is a second, dedicated governance summary local to the Writeback
    tab.
  - **Writeback candidate cards**, one per `writebacks.previews[]` entry: render `.md` content
    (`meatywiki_writeback.md`, `skillbom_candidate.md`) via the existing Markdown renderer used by
    `ReportOverlay` (`frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx`) or an
    equivalent lightweight Markdown component if reuse proves awkward; render `.yaml` content
    (`ccdash_event.yaml`) as a structured/pretty-printed block, not raw Markdown.
  - **Empty-state handling**: when `run.writebacks` is null/absent (pre-bundle runs) or
    `previews` is empty, keep (and lightly restyle) the existing "Writeback preview is not exported
    for this run yet" message — do not regress the current no-writebacks case.
- Mirror the same tab content in `RunDetailModal.tsx` (`writebackAvailable` branch, ~line 177) —
  the modal and full-page workspace share the same tab content pattern elsewhere in this
  component family; keep that parity.

### Out of Scope

- **Any write path.** The viewer never sets `approved_for_writeback`, `reviewer_notes`, or
  `required_fix`. That remains exclusively a CLI operation (`rf bundle --approve`). No new API
  endpoint, no PATCH/POST on run state, no button that mutates governance fields. This is the
  hard invariant of this contract — see §5 and §8.
- Changing `rf bundle --approve` or any backend governance-decision logic — this contract only
  exports and renders existing decisions, it does not change how they're made.
- Redesigning the existing Trust Panel governance block
  (`TrustPanel.tsx:139-151`) — it stays exactly as-is; the new panel is additive, on a different tab.
- A dedicated writeback Markdown renderer component if the existing `ReportRenderer` reuse works
  cleanly — build one only if reuse proves genuinely awkward (note the decision either way in the
  Completion Report).
- The other three writeback targets already mapped in `_WRITEBACK_TARGETS`
  (`intenttree_update.yaml`, `arc_review_request.yaml`, `notebooklm_update.yaml`) — include them in
  `previews[]` using the same generic YAML-block rendering as `ccdash_event.yaml` (no bespoke
  per-target UI beyond the markdown-vs-yaml split), but do not add target-specific card treatments
  for them.
- Schema/type changes to `review_packet.schema.yaml` or `claim_ledger.schema.yaml` — read-only
  consumers of whatever those already declare.

---

## 5. UX / Behavior Requirements

- Opening the Writeback tab on a run with writeback files present shows: the governance status
  panel (approval state, reviewer notes, required fix — each rendering a clear "not set" state
  when null, never a blank/missing row) followed by one candidate card per exported preview.
- Opening the Writeback tab on a run with **no** writeback files shows the existing empty-state
  message unchanged in meaning (copy may be lightly reworded for the new layout).
- `.md` writeback candidates render as formatted Markdown (headings, links, code blocks legible);
  `.yaml` candidates render as a readable structured/pretty-printed block, not a single unwrapped
  text blob.
- There is **no button, form, or interactive control anywhere in this tab that can change
  `approved_for_writeback`, `reviewer_notes`, or `required_fix`.** The tab is read-only in the same
  sense the rest of the run detail view is read-only.
- The tab behaves identically whether the viewer is in static-export mode or loopback/live-API mode
  (per `RF_UI_LOOPBACK` — see project memory `runs-loopback-api`) — no new live-mode-only affordance.
- Pre-1.6-schema exports (missing `previews`/`reviewer_notes`/`required_fix` keys entirely, not just
  null) degrade gracefully to the current stub behavior — same pattern as the `report_anchors`
  D9 legacy-fallback precedent already used elsewhere in this codebase.

---

## 6. Data Requirements

- **Entities affected**: `run.json` export document (`writebacks` key only); no persisted database
  entities, no new tables.
- **New/populated fields** (all on `RFRunWritebacksSummary`, all already declared in the TS type,
  none newly invented):
  - `reviewer_notes: string | null` — now populated from governance data (currently always
    unset/absent).
  - `required_fix: string | null` — now populated from governance data (currently always
    unset/absent).
  - `previews: RFWritebackPreview[] | null` — new concrete element shape (see §4), replacing the
    always-empty `unknown[]`.
- **State changes**: none — this is read/export-time enrichment of existing on-disk data
  (`writebacks/*.md`/`*.yaml` files, `evidence_bundle.governance`), not a new state machine.
- **Storage implications**: none. No migration. Export-time computation only.

---

## 7. API / Integration Requirements

**Modified export surface (not a new endpoint):**
- `rf run export --json` / the export path backing `GET /api/runs/{id}` — `run.json`'s `writebacks`
  key gains populated `reviewer_notes`, `required_fix`, and typed `previews[]`. No new route.

**External service calls**: none.

**Internal service dependencies:**
- `src/research_foundry/services/export_service.py::_collect_writebacks()` — extension point.
- `src/research_foundry/services/export_service.py::_redact_str_values()` — reuse for preview
  content redaction; do not bypass.
- Frontend: `frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx` and
  `RunDetailModal.tsx` — the two Writeback-tab render sites; `ReportRenderer.tsx` — candidate Markdown
  rendering reuse target.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `export_service.py::_collect_writebacks()` — extend in place; keep the existing
  `_WRITEBACK_TARGETS` dict as the single source of filename→target mapping (do not duplicate it).
- `RFRunWritebacksSummary`/`RFGovernanceBlock` typed-interface conventions in
  `frontend/runs-viewer/src/types/rf/run-export.ts` — additive optional fields, matching the
  existing `report_anchors` "additive/nullable, key-absent-on-legacy-export" precedent (schema
  1.4/D9).
- The `writeback` `DetailTab` already exists (`detailTabs.ts`) and is already wired through URL
  query state, modal navigation (`DetailModal.tsx:536-538`), and settings defaults
  (`viewerSettings.ts`) — this contract upgrades the tab's *content*, it does not add tab-routing
  plumbing.

**Must not change** (protected areas):
- The read-only invariant: **no mutation path for `approved_for_writeback`, `reviewer_notes`, or
  `required_fix` anywhere in the SPA.** Approval stays CLI-only (`rf bundle --approve`). This is
  non-negotiable and must be explicitly checked in review — see the frozen-schema/precondition note
  below.
- `TrustPanel.tsx`'s existing governance block (lines 139-151) — unrelated, unchanged.
- The `_WRITEBACK_TARGETS` filename→target mapping — reuse, don't fork.
- Any other export field or schema version semantics beyond the additive `writebacks` fields above.

**Precondition — frozen-schema policy gate**: `run.json` is a frozen export schema
(`EXPORT_SCHEMA_VERSION`, currently `"1.5"`). Per project policy this contract's schema bump to
`"1.6"` requires an explicit `backend-architect` review of the `_collect_writebacks()` diff and the
`RFRunWritebacksSummary`/`RFWritebackPreview` type changes **before** the frontend candidate-card
work is merged. The executing agent should treat this as a checkpoint within the sprint (backend
change → flag for architecture review → proceed to frontend once the shape is confirmed stable),
not a separate contract.

**New dependencies:**
- Allowed? **No**, unless the existing Markdown renderer (`ReportRenderer.tsx`) proves unsuitable
  for reuse on writeback Markdown content — if so, justify the addition of a lightweight Markdown
  component in the Completion Report before adding it. No new YAML-parsing dependency should be
  needed (the backend already parses YAML for `_collect_writebacks()`'s existing `url` extraction).

---

## 9. Acceptance Criteria

- [ ] A run with writeback files present exports `writebacks.previews[]` with one entry per
      present writeback file, each carrying `{target, filename, content_type, content}`, and
      `content` has passed through the same redaction path as every other exported text field.
- [ ] A run's `writebacks.reviewer_notes` and `writebacks.required_fix` are populated from the
      governance/review data when present, and are explicitly `null` (not absent, not empty
      string) when not present.
- [ ] `EXPORT_SCHEMA_VERSION` is bumped to `"1.6"`, and a `backend-architect` review of the schema
      diff is recorded (approval note in the Completion Report) before frontend candidate-card
      rendering work merges.
- [ ] The runs-viewer Writeback tab (both `RunDetailWorkspace.tsx` full-page and
      `RunDetailModal.tsx` modal paths) renders a governance status panel showing approval state,
      reviewer notes, and required fix, plus one candidate card per `writebacks.previews[]` entry.
- [ ] `.md` writeback candidates render as formatted Markdown; `.yaml` candidates render as a
      readable structured block (not raw unwrapped text).
- [ ] A run with no writeback files shows the existing (or lightly restyled) empty-state message —
      current behavior is not regressed.
- [ ] A pre-1.6-schema export (missing the new keys entirely) renders the tab in its current
      (pre-this-feature) stub form without error — legacy-export graceful degradation confirmed.
- [ ] **No code path in the SPA — component, hook, or API client — can set
      `approved_for_writeback`, `reviewer_notes`, or `required_fix`.** Verified by the reviewer via
      diff inspection, not just by the Completion Report's claim.
- [ ] Existing Trust Panel governance block and all other existing RunDetail tabs are visually and
      behaviorally unchanged.

---

## 10. Validation Requirements

- [ ] **Typecheck** passes: `pnpm --dir frontend/runs-viewer exec tsc -p tsconfig.app.json --noEmit`
      (per project memory: the bare `npx tsc --noEmit` at repo root is a no-op — use this exact
      command).
- [ ] **Lint** passes: `pnpm --dir frontend/runs-viewer lint`.
- [ ] **Frontend tests** added/updated for the new Writeback tab content (candidate card rendering,
      governance panel rendering, empty-state, legacy-schema degradation) and pass:
      `pnpm --dir frontend/runs-viewer test`.
- [ ] **Backend tests** added/updated for `_collect_writebacks()` covering: populated
      `reviewer_notes`/`required_fix`, populated `previews[]` with redaction applied, and the
      zero-writebacks no-op path — run via `./.venv/bin/python -m pytest -k writeback` (project
      venv, never the pyenv shim).
- [ ] **flake8** passes on changed backend files:
      `flake8 src/research_foundry/services/export_service.py --select=E9,F63,F7,F82`.
- [ ] **Build** passes: `pnpm --dir frontend/runs-viewer build`.
- [ ] **`backend-architect` schema review** recorded (see §8 precondition) before frontend work is
      considered mergeable — this is a mandatory gate, not optional validation.
- [ ] **CHANGELOG**: `changelog_required: true` — add a CHANGELOG entry (export schema 1.5→1.6,
      Writeback tab upgrade).
- [ ] **No unrelated changes** — do not touch `TrustPanel.tsx`, `rf bundle --approve`, or any
      writeback-emission logic in `writeback.py`.

---

## 11. Risk Areas

- **Frozen-schema policy violation**: bumping `EXPORT_SCHEMA_VERSION` without the
  `backend-architect` review gate is the single highest risk on this contract — do not skip it even
  though the change is additive-only. Treat it as a hard stop, not a formality.
- **Read-only invariant drift**: it is easy, while building "candidate cards," to accidentally wire
  an approve/reject affordance into the UI (a natural-feeling but forbidden feature). The reviewer
  must explicitly check the diff for any new mutation-capable API call, form, or button in this
  scope — the acceptance criteria call this out separately from general test-passing for that reason.
- **`reviewer_notes`/`required_fix` source-of-truth ambiguity**: the design spec assumed these live
  directly on `evidence_bundle.governance`, but `schemas/review_packet.schema.yaml` also declares
  both fields on a separate `review_packet` artifact tied to council review runs. The executing
  agent must confirm empirically (trace `rf bundle --approve` and the council review path) which
  artifact actually carries these values for real runs before wiring the export — do not assume the
  design-spec's guess is correct without checking.
- **Redaction gaps in writeback content**: writeback files (especially `meatywiki_writeback.md`)
  may contain longer prose passages than other exported fields; confirm `_redact_str_values`
  correctly walks nested/long Markdown strings, not just short scalar fields — spot-check against a
  `client_sensitive` fixture run.
- **Markdown renderer reuse friction**: `ReportRenderer.tsx` may carry report-specific assumptions
  (claim-tag linking, anchor IDs) that don't apply to writeback Markdown — budget time to confirm
  clean reuse or fall back to a minimal renderer per §8's dependency note.

---

## 12. Implementation Notes

**Suggested approach** (agent may improve):
1. Backend first: extend `_collect_writebacks()` to populate `reviewer_notes`/`required_fix` and
   build the typed `previews[]` list, reusing `_WRITEBACK_TARGETS` and `_redact_str_values`. Bump
   `EXPORT_SCHEMA_VERSION`. Add/update backend tests. Flag for `backend-architect` review at this
   checkpoint.
2. Update the TS type (`RFRunWritebacksSummary.previews`) to match the new backend shape exactly.
3. Frontend: upgrade `RunDetailWorkspace.tsx`'s `writeback` tab branch first (it's the primary
   surface), then mirror in `RunDetailModal.tsx`.
4. Add tests for both the new export fields and the new render paths, including the legacy
   (pre-1.6) degradation case.

**Similar existing code**:
- Reference: `export_service.py`'s `report_anchors` field (schema 1.4) — closest precedent for
  "additive, nullable, key-absent-on-legacy-export" field design; mirror its comment style.
- Reference: `TrustPanel.tsx:139-151` — existing governance-block rendering pattern (badge/dl
  structure) to draw visual/structural inspiration from, without touching that file.
- Reference: `frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx` — Markdown
  rendering to reuse for `.md` candidates.

**Known gotchas**:
- `pnpm --dir frontend/runs-viewer exec tsc -p tsconfig.app.json --noEmit` is the real typecheck
  gate; the bare `npx tsc --noEmit` at repo root is a documented no-op.
- Run backend tests under the project venv (`./.venv/bin/python -m pytest`), never the pyenv shim.
- `RF_UI_LOOPBACK` build mode bakes the API token into the LAN bundle — no new behavior needed here,
  but be aware both static and live-API modes must render this tab identically per §5.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: List of all modified/new files with brief reason
- **Tests run**: What tests were added/updated and results
- **Validation results**: Table of all validation commands and their results (pass/fail/not applicable)
- **`backend-architect` review outcome**: explicit record of the schema-bump review (approved /
  changes requested / findings)
- **Deviations from contract**: Any material changes to the contract during implementation and why
  (especially the `reviewer_notes`/`required_fix` source-of-truth finding from Risk Area 3)
- **Risks / Limitations**: Any remaining risks or known limitations
- **Follow-up recommendations**: Suggested next steps (e.g., extending previews to the three
  lower-priority targets with bespoke rendering, if deferred)

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report template.

---

## Metadata & References

**Tier**: 1 (3–8 points) — estimated 6 pts.

**Execution Mode**: Autonomous Feature Sprint (Mode C), with a mandatory mid-sprint
`backend-architect` checkpoint after the export-schema change (see §8 precondition) before frontend
work proceeds.

**Reviewer**: `task-completion-validator` (mandatory, end of sprint) + `backend-architect`
(mandatory, schema-bump checkpoint).

**Related Documents**:
- `docs/project_plans/design-specs/runs-writeback-preview.md` — idea-stage source spec this
  contract promotes. Note: its "Export schema extension" scope section assumed the `writebacks` key
  did not yet exist; code-truth grounding at contract-authoring time (2026-07-18) found it already
  exists (`RFRunWritebacksSummary`, schema 1.5, `writeback` tab already wired) — this contract's
  actual scope is *completing* an already-started field/tab, not adding one from scratch.
- `docs/dev/architecture/rf-run-export-schema.md` — export schema reference.
- `docs/project_plans/implementation_plans/features/runs-frontend-v1.md` — parent plan FR-13 was
  deferred from.

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass validation. If you find:

- **Scope ambiguity**: Ask one focused question or make a conservative assumption and note it in the Completion Report.
- **Impossible constraints**: Flag in the Completion Report before attempting workarounds.
- **Better implementation path**: Document the deviation in the Completion Report with justification.

Stay within scope. The read-only invariant (§4, §8, §9) is the one boundary in this contract that
must never be crossed, even under scope-ambiguity pressure — when in doubt, render less, never add
a mutation path. The reviewer will check for scope drift and for any mutation-capable code path.
