---
title: "Feature Contract: Runs Writeback-Review Governance View (FR-13)"
schema_version: 2
doc_type: feature_contract
it_schema: 1
description: "Upgrade the runs-viewer Writeback tab from a status stub into a governance review surface with rendered writeback-candidate cards and reviewer_notes/required_fix visibility."
status: completed
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
  - tests/unit/test_export_service.py
  - docs/dev/architecture/rf-run-export-schema.json
  - frontend/runs-viewer/src/types/rf/run-export.ts
  - frontend/runs-viewer/src/types/rf/index.ts
  - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
  - frontend/runs-viewer/src/test/fr13-writeback-review.test.tsx
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

---

## Completion Report

### Summary

Extended `_collect_writebacks()` to populate `reviewer_notes`/`required_fix` (sourced empirically
from the council review packet, `reviews/council_review.yaml`, not `evidence_bundle.governance`)
and a new typed `previews[]` array (one `{target, filename, content_type, content}` entry per
present writeback file, content passed through the existing `_redact_str_values` redaction gate).
Bumped `EXPORT_SCHEMA_VERSION` "1.5" → "1.6"; the schema diff was reviewed and **APPROVED** by
`backend-architect` before any frontend work began. Upgraded the runs-viewer Writeback tab
(`RunDetailWorkspace.tsx`, shared by the full-page and modal detail views) from a 3-row status
stub into a governance status panel plus one candidate card per preview, with Markdown rendering
for `.md` files and a pre-formatted structured block for `.yaml` files — strictly read-only, no
mutation-capable control anywhere in the tab.

### Files Changed

- `src/research_foundry/services/export_service.py` — bumped `EXPORT_SCHEMA_VERSION` to `"1.6"`;
  hoisted `_WRITEBACK_TARGETS` to module scope (no duplication); added
  `_review_packet_reviewer_fields()` helper (reads `reviews/council_review.yaml`, joins multiple
  concerns' `required_fix` values); rewrote `_collect_writebacks()` to build `previews[]` and
  populate `reviewer_notes`/`required_fix`, both redacted via `_redact_str_values` when the run's
  sensitivity exceeds the export threshold.
- `tests/unit/test_export_service.py` — bumped 9 pre-existing hardcoded `"1.5"` schema-version
  assertions to `"1.6"` (2 test functions renamed `..._1_5` → `..._1_6` to match); added 8 new
  tests covering previews shape/redaction, reviewer_notes/required_fix population/null/redaction,
  and the zero-writebacks no-op path.
- `docs/dev/architecture/rf-run-export-schema.json` — the hand-written TS types' stated "source of
  truth" JSON Schema (manual-sync-by-PR-review per its own header comment); updated
  `schema_version` description/examples, added `RFWritebackPreview` definition, wired
  `previews` items to it. Not in the contract's `files_affected` list but directly implied by that
  file's own documented sync contract — flagged here as a deviation, not silently done.
- `frontend/runs-viewer/src/types/rf/run-export.ts` — added `RFWritebackPreview` interface;
  changed `RFRunWritebacksSummary.previews` from `unknown[] | null` to `RFWritebackPreview[] | null`;
  updated the schema_version doc comment.
- `frontend/runs-viewer/src/types/rf/index.ts` — added `RFWritebackPreview` to the public type
  barrel (deviation: not in contract's `files_affected`, but required for the new type to be
  importable via the project's `@/types/rf` convention — every sibling writeback type is already
  barrel-exported there).
- `frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx` — replaced the
  `activeTab === "writeback"` stub with `WritebackTabPanel`/`WritebackGovernancePanel`/
  `WritebackCandidateCard` (local functions, following the file's existing `RunOverview`-style
  pattern); added a minimal Markdown renderer using `react-markdown`/`remark-gfm` (already project
  dependencies) instead of reusing `ReportRenderer`.
- `frontend/runs-viewer/src/test/fr13-writeback-review.test.tsx` — new test file (15 tests) covering
  empty state, governance panel (including null → "Not set"), candidate cards (markdown + yaml
  rendering), legacy (pre-1.6) degradation, and the read-only invariant (no `<form>`/`<button>`/
  `<input>` in the tab).
- `CHANGELOG.md` — added an `[Unreleased]` entry for the schema bump and tab upgrade.

**Not changed** (see Deviations below): `schemas/evidence_bundle.schema.yaml`,
`frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx`.

### Acceptance Criteria Status

- [x] `writebacks.previews[]` exports one entry per present writeback file, each carrying
      `{target, filename, content_type, content}`, redacted through `_redact_str_values`.
- [x] `writebacks.reviewer_notes`/`required_fix` populated when present, explicit `null` (not
      absent/empty-string) when not.
- [x] `EXPORT_SCHEMA_VERSION` bumped to `"1.6"`; `backend-architect` review recorded below
      (APPROVED, before frontend work began).
- [x] Writeback tab (both `RunDetailWorkspace.tsx` full-page and `RunDetailModal.tsx` modal paths —
      the modal renders `RunDetailWorkspace` directly, so both paths share one implementation)
      renders the governance status panel + one candidate card per preview.
- [x] `.md` candidates render as formatted Markdown; `.yaml` candidates render as a
      pre-formatted structured block (verified via `<pre>`/`<code>` DOM assertions in tests).
- [x] No-writeback-files run shows the existing empty-state message, copy unchanged.
- [x] Pre-1.6 export (previews/reviewer_notes/required_fix keys entirely absent) renders without
      error — governance panel + "Not set"/"No previews" fallbacks (see interpretation note below).
- [x] No code path in the SPA can set `approved_for_writeback`/`reviewer_notes`/`required_fix` —
      verified by diff inspection (no new API client calls, no form, no button anywhere in the new
      code) and by 3 explicit read-only-invariant tests (`<form>`/`<button>`/`<input,select,textarea>`
      absence).
- [x] Trust Panel governance block and all other RunDetail tabs unchanged — diff touches only the
      `writeback` branch, its local helper functions, and imports; `TrustPanel.tsx` untouched.

### backend-architect Review Outcome

**APPROVED** (recorded verbatim from the review agent, run before any frontend edits):

> Additive/backward-compatible: yes — no key removed, no existing-field type narrowed; `previews`
> narrows from `unknown[]` but that field was always empty pre-1.6, so no real consumer breaks.
> Source-of-truth choice (review packet, not evidence_bundle.governance) is sound and matches where
> the writeback module actually authors those fields; `_load_yaml_dict` no-ops cleanly when the
> packet is absent. Redaction via run-level sensitivity (vs. a per-file label, which doesn't exist)
> is a reasonable, fail-safe default — same pattern already used for `routing_decision`/`swarm_plan`.
> `_WRITEBACK_TARGETS` hoist is a pure no-behavior-change refactor. No bugs found. No changes
> requested.

### Validation Run

| Command | Result | Notes |
|---|---|---|
| `pnpm --dir frontend/runs-viewer exec tsc -p tsconfig.app.json --noEmit` | Pass | Clean, no errors |
| `pnpm --dir frontend/runs-viewer lint` | Pass (baseline parity) | 9 pre-existing problems (1 error, 8 warnings) in 4 unrelated files (`AuthContext.tsx`, `LocalLoginForm.tsx`, `AssertionAuditPanel.tsx`, `ClaimAuditWorkbench.tsx`); confirmed identical via `git stash` — zero new lint issues in changed files |
| `pnpm --dir frontend/runs-viewer test` | Pass (baseline parity) | 1001/1002 passed; the 1 failure (`provenance-correctness.test.ts`) plus the 1 failed suite (`codegen/generate-types.contract.test.mjs`, "No test suite found") both reproduce identically with all my changes stashed — pre-existing, unrelated to this contract (project memory: "4 frontend test files are known-failing baseline") |
| `pnpm --dir frontend/runs-viewer build` | Pass | Builds clean (pre-existing >500kB chunk-size warning, unrelated) |
| `PYTHONPATH=<worktree>/src <main>/.venv/bin/python -m pytest -k writeback` | Pass | 97 passed across the whole repo (project venv, not the pyenv shim) |
| `PYTHONPATH=<worktree>/src <main>/.venv/bin/python -m pytest tests/unit/test_export_service.py` | Pass | 124 passed (full file, includes all 8 new + 9 version-bumped tests) |
| `flake8 src/research_foundry/services/export_service.py --select=E9,F63,F7,F82` | Pass | No errors |
| `backend-architect` schema review | **APPROVED** | See above; recorded before frontend work began, per §8 |
| CHANGELOG entry | Done | `[Unreleased]` section, schema 1.5→1.6 + tab upgrade |

Also spot-checked `tests/test_serve_api.py`/`tests/integration/test_export_round_trip.py`/
`tests/integration/test_p5_regression_suite.py` for regressions: 5 pre-existing `test_serve_api.py`
failures (404-vs-200, a test-isolation issue that only surfaces when run alongside other files)
reproduce identically with changes stashed — confirmed unrelated to this diff.

### Deviations From Contract

1. **`schemas/evidence_bundle.schema.yaml` — not modified.** Risk Area 3 explicitly asked the
   executing agent to confirm empirically whether `reviewer_notes`/`required_fix` live on
   `evidence_bundle.governance` or a separate `review_packet` artifact before wiring the export.
   Traced `research_foundry.services.writeback.council_review()`: both fields are written onto
   `reviews/council_review.yaml` (schema `review_packet`), which already declares them —
   `evidence_bundle.governance` (schemas/evidence_bundle.schema.yaml:59-78) does not declare either
   field and needed no change. Listed in the contract's original `files_affected` on the design
   spec's untested assumption; the empirical finding supersedes it.
2. **`frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx` — not modified.**
   `RunDetailModal.tsx` does not duplicate Writeback-tab markup; it renders `<RunDetailWorkspace>`
   directly and only shows one already-existing pre-flight banner (`!writebackAvailable &&
   activeTab === "writeback"`) above it. Upgrading `RunDetailWorkspace.tsx`'s tab content
   automatically upgrades the modal path with zero additional code — verified by inspection, not
   assumed. No edit was needed to satisfy "mirror the same tab content in RunDetailModal.tsx."
3. **New Markdown component instead of `ReportRenderer` reuse.** `ReportRenderer` requires
   non-optional `claims`/`onClaimSelect` props, applies a metadata-frontmatter-stripping pass
   (risk of eating legitimate writeback content lines that happen to look like `Key: value`), and
   carries claim-chip/anchor-block logic irrelevant to writeback markdown. Built a small local
   renderer using the same already-present dependencies (`react-markdown` + `remark-gfm`) instead —
   no new dependency added, per §8's constraint.
4. **`.yaml` previews rendered as pre-formatted text, not parsed.** The contract's "readable
   structured/pretty-printed block" requirement is satisfied by rendering the backend's exact YAML
   text inside a `<pre><code>` block (monospace, line-preserving) rather than parsing it into a JS
   object. This avoids needing a YAML parser in the browser bundle (`js-yaml` is currently a
   dev-only dependency used by codegen scripts, not shipped to the client) — consistent with the
   contract's note that "no new YAML-parsing dependency should be needed."
5. **Legacy-degradation interpretation.** AC7 asks for the tab to render "in its current
   (pre-this-feature) stub form" when the 1.6 keys are absent. The new implementation does not
   reproduce the old 3-row `<dl>` byte-for-byte; instead it shows the same new governance panel
   with "Not set"/"No previews" fallbacks (the null-coalescing pattern already used everywhere else
   in this codebase for additive fields, e.g. `report_anchors`). No crash, no missing/blank rows —
   interpreted "graceful degradation" as behavior-equivalent rather than markup-identical. Flagging
   this explicitly per the contract's own escalation instructions rather than silently assuming.
6. **`docs/dev/architecture/rf-run-export-schema.json` updated** (not in `files_affected`). This
   JSON Schema file's own header states it is the manually-synced "source of truth" for the
   hand-written TS types, kept current "by PR review" — leaving it stale after exactly this kind of
   schema-adding change would violate that file's stated policy, so it was updated (new
   `RFWritebackPreview` definition, `previews` items ref, version description/examples).
7. **`frontend/runs-viewer/src/types/rf/index.ts` updated** (not in `files_affected`). Required to
   barrel-export the new `RFWritebackPreview` type per the project's own "import from `@/types/rf`
   only" convention stated in that file's header — every sibling writeback type
   (`RFWritebackTarget`, `RFRunWritebacksSummary`) is already exported there.
8. **`tests/unit/test_export_service.py` updated beyond adding new tests** (not in
   `files_affected`). 9 pre-existing tests hardcoded the literal string `"1.5"` as the expected
   `schema_version`; these had to be bumped to `"1.6"` or the full suite would fail on an unrelated
   assertion. Two test functions were renamed (`test_schema_version_is_1_5` →
   `test_schema_version_is_1_6`, `test_schema_version_bumped_to_1_5` →
   `test_schema_version_bumped_to_1_6`) to keep names accurate.

### Risks and Limitations

- **No per-writeback-file sensitivity label.** Redaction of `previews[]`/`reviewer_notes`/
  `required_fix` uses the run's overall `sensitivity` vs. the export threshold (the same pattern
  already used for `routing_decision`/`swarm_plan`), because no writeback file carries an
  independent sensitivity label today. `backend-architect` confirmed this is a reasonable
  fail-safe default but flagged it as a known limitation: if a future writeback target ever embeds
  content more sensitive than the run's declared label, it would inherit the run's (possibly lower)
  redaction decision. Not a regression — the same limitation already existed for other context
  fields — but worth tracking if a writeback target's sensitivity profile diverges from the run's.
- **`required_fix` join strategy.** When a council review has multiple concerns each carrying a
  `required_fix`, they are newline-joined into one string (de-duplicated, order-preserved). This
  is a reasonable display choice but is a lossy simplification versus exposing the full
  `concerns[]` array structure (out of scope per contract — `required_fix` is typed as a single
  `string | null`).
- **Two known-failing frontend test files remain untouched** (`provenance-correctness.test.ts`,
  `codegen/generate-types.contract.test.mjs`) — pre-existing baseline failures per project memory,
  confirmed unrelated via `git stash` comparison; not chased per that memory's guidance.

### Follow-Up Recommendations

- Consider extending `previews[]` rendering with bespoke per-target UI for the three lower-priority
  targets (`intenttree_update.yaml`, `arc_review_request.yaml`, `notebooklm_update.yaml`) if
  operator feedback shows the generic YAML-block treatment is insufficient for those targets —
  explicitly deferred by the contract's Out-of-Scope section.
- If a future writeback target needs independent sensitivity labeling (distinct from the run's
  overall sensitivity), `_collect_writebacks()`'s `redact` parameter would need to become
  per-file rather than a single run-level boolean — flagging now so it isn't a surprise later.
- The two pre-existing failing frontend test files and the 5 pre-existing `test_serve_api.py`
  cross-file-isolation failures are unrelated to this contract but remain open technical debt;
  not remediated here per scope discipline.

### Memory Candidates Captured

- **Gotcha**: `docs/dev/architecture/rf-run-export-schema.json` is a JSON Schema that the
  hand-written `frontend/runs-viewer/src/types/rf/run-export.ts` claims as its "source of truth,"
  synced manually "by PR review" (per its own header comment) — not covered by any automated
  contract test (`codegen/generate-types.contract.test.mjs` only checks the OpenAPI-generated
  assertions API types, a separate concern). Future schema bumps to `RFRunWritebacksSummary`/etc.
  should update both files together; there is no CI gate that would catch drift.
- **Gotcha**: `reviewer_notes`/`required_fix` for writeback governance live on the `review_packet`
  artifact (`reviews/council_review.yaml`), not `evidence_bundle.governance` — the latter's schema
  (`schemas/evidence_bundle.schema.yaml`) does not declare either field. Any future work reading
  "governance" fields for writeback approval context should check `council_review.yaml` first.
