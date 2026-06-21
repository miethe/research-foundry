---
title: "Feature Contract: Viewer Un-Redact (LAN)"
schema_version: 2
doc_type: feature_contract
status: completed
created: 2026-06-20
updated: 2026-06-21
feature_slug: "viewer-unredact-lan"
category: "harden-polish"
estimated_points: 4
tier: 1
owner: nick
priority: high
risk_level: low
changelog_required: true
audience: [ai-agents, developers]
related_documents:
  - docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
spike_ref: null
prd_ref: docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
plan_ref: null
commit_refs:
  - bbf6341
pr_refs: []
files_affected:
  - foundry.yaml
  - frontend/runs-viewer/src/types/rf/run-export.ts
  - frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx
  - frontend/runs-viewer/.env (or .env.local, optional VITE_SHOW_ALL bypass)
  - frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx
  - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
  - frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx
  - frontend/runs-viewer/src/components/ReportOverlay/ReportOverlay.tsx
  - frontend/runs-viewer/src/test/p4-components.test.tsx
---

# Feature Contract: Viewer Un-Redact (LAN)

## 1. Goal

Remove all `[redacted:sensitivity]` markers from the personal LAN-only runs-viewer by raising the
export sensitivity threshold to `client_sensitive`, re-exporting all runs, and aligning the
frontend display gate so it does not re-mask already-unredacted content.

---

## 2. User / Actor

- **Primary user**: Nick Miethe — operator running the personal Research Foundry instance on a
  private LAN at `10.42.10.76:3030`. This is the operator's own data; no third-party exposure
  exists. The change is explicitly authorized and non-Mode-D.
- **Secondary users**: None — viewer is single-operator, LAN-only, read-only.

---

## 3. Job To Be Done

When **reviewing research run results on the LAN viewer**, the operator wants to **read the full
verbatim source quotes and summaries without redaction placeholders**, so they can **evaluate
evidence quality, verify claims, and spot citation issues without switching to the raw
`runs/*/sources/*.md` files**.

---

## 4. Scope

### In Scope

1. **Config change**: set `foundry.yaml` `viewer.sensitivity_threshold: client_sensitive`
   (currently `public`, line 28). This raises the backend export threshold so all sensitivity
   levels (public, personal, work_sensitive, client_sensitive) are emitted as full text.
2. **Re-export all runs**: run `rf run export --all` so every `runs/<id>/run.json` is rebuilt
   with the full `quote` and `summary` fields. Include this as an explicit operator task with
   a pre-flight verification step.
3. **Rebuild static viewer data**: run `pnpm --filter runs-viewer build` (which executes
   `prebuild-static-data.mjs`, re-running `rf run export --all` and copying outputs to
   `public/data/`), then restart `research-foundry-ui.service`.
4. **FE display-gate alignment**: `SourceCard.tsx` `isRedacted()` (lines 28–35) currently falls
   back to threshold `personal` when `sensitivityThreshold` prop is absent. Pass the active
   threshold (`client_sensitive`) through to the SourceCard so the defense-in-depth gate does
   not re-mask content that the export already emitted unredacted. Also add an optional
   `VITE_SHOW_ALL=1` env bypass in `SourceCard.isRedacted()` that returns `false` unconditionally
   when set, as a belt-and-suspenders override.
5. **Type drift fix**: add `redacted?: boolean` to `RFResolvedSource` interface in
   `frontend/runs-viewer/src/types/rf/run-export.ts` (currently missing; the backend writes
   this field via `export_service.py:_resolve_source()` ~lines 277–295). The field is optional
   so pre-existing exports without it remain valid.
6. **Pre-flight verification task**: before re-exporting, confirm that at least one run's
   `runs/<id>/sources/*.md` file contains a non-empty `extracted_points[].quote` (i.e., the
   unredacted truth exists on disk). Document result in the completion report.
7. **Deployment**: restart the viewer service after rebuild (manual path: `pnpm build` +
   `systemctl --user restart research-foundry-ui.service`).

### Out of Scope

- **Author-time governance / secret-scanning**: `governance.py`, key profiles, and policy rules
  are unchanged. These govern what can be extracted and written back, not what the viewer
  displays. The `[redacted:sensitivity]` replacement by `_resolve_source()` is a viewer-display
  decision, not a governance gate.
- **Making the viewer writeable**: viewer stays read-only.
- **Changing the export schema version**: this change does not alter the schema shape beyond
  adding the already-emitted `redacted` field to the TS type. No schema_version bump required.
- **Per-run sensitivity overrides**: threshold is global (foundry.yaml). Per-run override is a
  future concern (F5 or G5 Settings tab).
- **Redaction of new runs at author-time**: `_resolve_source()` in `export_service.py` continues
  to evaluate sensitivity; with `client_sensitive` threshold, all content passes. Governance
  (secret-scanning, key_profile_allowed) is unaffected.

---

## 5. UX / Behavior Requirements

1. After re-export and rebuild, **no `[redacted:sensitivity]` placeholder text appears** in any
   source quote or summary field visible in the viewer.
2. `SourceCard` renders the full `quote` (in the expandable quote section) and `summary` for all
   sources regardless of their `sensitivity` value, because both the export and the FE gate now
   treat `client_sensitive` as the threshold.
3. If `VITE_SHOW_ALL=1` is set in the build environment, `isRedacted()` returns `false`
   unconditionally, bypassing the threshold comparison entirely. This is a build-time bypass; it
   does not appear in the UI.
4. **Pre-change runs** (exported before this config change) will still show `[redacted:sensitivity]`
   markers until they are re-exported. This is expected and documented behavior — it is not a bug.
   The completion report must note this explicitly.
5. **`redacted: true` field** on a source (written by the backend when the source was above threshold
   at export time) is now optional in the TS type. The FE should treat absent `redacted` as
   `false` (no special behavior change needed beyond the type fix).
6. The sensitivity threshold displayed in any viewer UI (currently none; G5 will add a Settings
   tab) is out of scope for this contract.

---

## 6. Data Requirements

- **Config field changed**: `foundry.yaml` `viewer.sensitivity_threshold` from `"public"` to
  `"client_sensitive"` (line 28).
- **`run.json` shape (post re-export)**: `claims[].sources[].quote` and `claims[].sources[].summary`
  will contain full text (previously `"[redacted:sensitivity]"` for sensitive sources).
  `claims[].sources[].redacted` will be `false` (or absent) for all sources.
- **No new fields added to the export schema** — `redacted` was already emitted by the backend;
  this change only adds it to the TS type.
- **`RFResolvedSource` interface change**:
  - Add: `redacted?: boolean` after the `dangling` field (run-export.ts, after line 86).
  - No other interface changes needed.
- **SourceCard props**: `sensitivityThreshold` prop (already present, line 83 of SourceCard.tsx)
  must be wired correctly from parent components. Verify the prop is passed through
  `ProvenanceModal` and `ClaimInspector` call sites. If it is currently `undefined`, the
  fallback is `personal` — this is the gap that causes re-masking.
- **Static data artifacts**: after `pnpm build`, `public/data/<id>/run.json` and
  `public/data/index.json` are regenerated. The old files are overwritten atomically (safe;
  `prebuild-static-data.mjs` copies from `runs/<id>/run.json` after re-exporting).
- **Source of truth for recovery**: `runs/<id>/sources/*.md` frontmatter
  (`extracted_points[].quote` / `.summary`) always holds the unredacted values regardless of
  export threshold. Recovery is always possible by re-exporting with any threshold.

---

## 7. API / Integration Requirements

**No new endpoints.** The viewer is a static SPA with no backend API in the data path for normal
reads. The optional loopback API (`api/client.ts`) is unused for this feature.

**CLI commands (operator tasks, not code changes):**

```bash
# 1. Confirm unredacted truth exists on disk (pre-flight)
grep -r "quote:" runs/*/sources/*.md | head -20

# 2. Re-export all runs with the new threshold
rf run export --all

# 3. Rebuild static viewer data and redeploy
cd frontend/runs-viewer && pnpm build
# or via bootstrap: bash bootstrap-agentic-node.sh services persistence
systemctl --user restart research-foundry-ui.service
```

**Internal service dependencies (build time only):**

- `export_service.py:export_run()` — reads `foundry.yaml viewer.sensitivity_threshold` via
  `config.py` `viewer` property. No code change needed; config change is sufficient.
- `prebuild-static-data.mjs` — runs `rf run export --all` then copies outputs. Triggers
  automatically during `pnpm build`.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**

- `foundry.yaml` viewer block (lines 22–28) — YAML config, no new format needed.
- `SourceCard.tsx` sensitivity gate pattern (`isRedacted()`, lines 28–35) — extend in-place, do
  not refactor the gate. The `VITE_SHOW_ALL` bypass is additive (check env var first, return
  false early).
- `RFResolvedSource` in `run-export.ts` — hand-written TS interface; add `redacted?: boolean`
  in the existing source-level fields block (after `dangling`, before card-level fields). Do not
  generate or codegen this file.
- Static export discipline (epic §0.1): all data changes require re-export + rebuild. Do not
  skip this step.

**Must not change (protected areas):**

- `governance.py`, key profiles, policy rules, secret-scanning — author-time governance is out
  of scope.
- `export_service.py` logic: no code change required. `_resolve_source()` already writes
  `redacted=True/False`; raising the config threshold causes it to emit `redacted=False` for all
  sources without code change.
- `run-export.ts` schema_version comment ("Bound to schema_version '1.0'") — this is a TS type
  file, not a version-bumped artifact. Leave the comment accurate.
- The `SENSITIVITY_ORDER` constant in `SourceCard.tsx` (lines 20–25) — do not reorder or add
  values; `client_sensitive` is already the highest rank (3).

**New dependencies:**

- Allowed? **No** — no new npm packages or Python dependencies.
- The `VITE_SHOW_ALL` env var is a Vite build-time env var, no new dependency.

---

## 9. Acceptance Criteria

#### AC F4-001: Config threshold raised

- **Description**: `foundry.yaml viewer.sensitivity_threshold` is set to `client_sensitive`.
- Verify: `grep sensitivity_threshold foundry.yaml` returns `client_sensitive`.

#### AC F4-002: Unredacted truth verified pre-flight

- **Description**: At least one `runs/<id>/sources/*.md` file contains a non-empty `quote` value
  under `extracted_points`, confirming unredacted source-of-truth exists before re-export.
- Verify: grep or manual spot-check. Document result in completion report.

#### AC F4-003: No redaction markers in viewer after re-export

- target_surfaces:
    - frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx (ClaimInspector pane)
    - frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx
- propagation_contract: `foundry.yaml` threshold change → `export_service._resolve_source()` emits
  full `quote`/`summary` → `run.json` → `public/data/<id>/run.json` after `pnpm build` →
  `SourceCard` renders quote/summary text → `ClaimInspector` (which embeds SourceCard) shows full
  text → `ProvenanceModal` (which shows SourceCard) shows full text.
- resilience: See AC F4-005 for pre-change exports. For post-export runs with `sensitivity:
  client_sensitive`, `isRedacted(source.sensitivity, 'client_sensitive')` returns `false`
  (level 3 is NOT > threshold level 3) → content renders.
- visual_evidence_required: Screenshot of at least one SourceCard with a non-empty quote (the
  expandable quote section open), from a run whose source was previously redacted.
- verified_by: [F4-VAL-001, F4-SMOKE-001]

#### AC F4-004: FE display gate aligned — threshold prop wired

- target_surfaces:
    - frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx (ClaimInspector pane)
    - frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx
- propagation_contract: `sensitivityThreshold` prop on `SourceCard` receives the active threshold
  (`client_sensitive` or equivalent) from its parent render context in all three surfaces. Verify
  by tracing the prop through ProvenanceModal and ClaimInspector call sites.
- resilience: If `sensitivityThreshold` prop is absent (undefined), `isRedacted()` currently
  defaults to `personal` threshold (line 32 of SourceCard.tsx), which would re-mask
  `work_sensitive` and `client_sensitive` content even after re-export. This must be fixed: either
  pass the active threshold explicitly, or change the default to `client_sensitive` for the
  LAN-only build. Document the chosen approach in the completion report.
- visual_evidence_required: false (covered by AC F4-003 screenshot)
- verified_by: [F4-VAL-001]

#### AC F4-005: Resilience — pre-change exports retain markers (documented)

- target_surfaces:
    - frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx
- propagation_contract: A run exported before this config change will have `[redacted:sensitivity]`
  in `run.json quote/summary` fields. The viewer correctly shows these markers (it renders the
  string as-is). This is expected — NOT a regression.
- resilience: Document this behavior in the completion report with wording such as: "Runs exported
  before the threshold change will continue to display redaction markers. Run `rf run export --all`
  to refresh all runs. Individual runs can be re-exported with `rf run export <run_id>`."
- visual_evidence_required: false
- verified_by: [F4-VAL-001]

#### AC F4-006: `redacted?: boolean` added to `RFResolvedSource`

- **Description**: `run-export.ts` `RFResolvedSource` interface includes `redacted?: boolean` as an
  optional field. TypeScript compiles without error.
- Verify: `npx tsc --noEmit` passes; field is visible in the interface definition.
- resilience: Field is optional (`?`); existing code that does not reference `redacted` is
  unaffected. No runtime behavior change — this is a type-only fix.
- verified_by: [F4-VAL-002]

#### AC F4-007: VITE_SHOW_ALL bypass works (optional)

- **Description**: When `VITE_SHOW_ALL=1` is set at build time, `SourceCard.isRedacted()` returns
  `false` for all sources regardless of sensitivity level or threshold.
- Verify: unit test or manual build with env var set. (This is P1 / nice-to-have; implement only
  if time permits and after the core ACs pass.)
- resilience: When `VITE_SHOW_ALL` is absent or not `"1"`, behavior is identical to the current
  codebase (no regression).
- verified_by: [F4-VAL-003]

#### AC F4-008: Build and deployment succeed

- **Description**: `pnpm --filter runs-viewer build` succeeds with zero TypeScript errors and zero
  build warnings related to this change. `research-foundry-ui.service` restarts cleanly.
- Verify: build log (no TS errors); `systemctl --user status research-foundry-ui.service` shows
  active (running).
- verified_by: [F4-VAL-002]

---

## 10. Validation Requirements

- [ ] **Typecheck** passes: `npx tsc --noEmit` in `frontend/runs-viewer` with zero errors
      introduced by this change (pre-existing test errors in `__tests__/a11y/` are excluded per
      lsp-diagnostics rule).
- [ ] **Lint** passes: `eslint` on changed files.
- [ ] **Build** passes: `pnpm --filter runs-viewer build` exits 0.
- [ ] **Pre-flight check** completed: unredacted source truth verified on disk (AC F4-002).
- [ ] **Re-export completed**: `rf run export --all` run successfully after config change.
- [ ] **Runtime smoke** (F4-SMOKE-001): deploy viewer to `10.42.10.76:3030` (or local dev server)
      and confirm at least one SourceCard renders a non-empty quote with no `[redacted:sensitivity]`
      text visible in SourceCard.tsx, ClaimInspector, and ProvenanceModal surfaces.
- [ ] **Type-only unit test** (F4-VAL-002): `run-export.ts` compiles; `RFResolvedSource` accepts
      `{ ..., redacted: false }` and `{ ..., redacted: undefined }` without TS error.
- [ ] **No unrelated changes** introduced.
- [ ] **Completion report** includes: pre-flight verification result, re-export command run, files
      changed, notes on prop-wiring approach chosen, and the pre-change-run resilience note (AC
      F4-005 wording).

**Validation task index:**

| ID | Task | Type |
|----|------|------|
| F4-VAL-001 | Confirm no redaction markers in SourceCard/ClaimInspector/ProvenanceModal surfaces | manual + screenshot |
| F4-VAL-002 | `tsc --noEmit` + build pass | automated |
| F4-VAL-003 | VITE_SHOW_ALL bypass unit test (optional) | unit test |
| F4-SMOKE-001 | Runtime smoke — open deployed viewer, open a run, navigate to a source with previously-redacted content | runtime |

---

## 11. Risk Areas

- **Re-export overwrites run.json atomically** (low risk): `prebuild-static-data.mjs` copies
  `runs/<id>/run.json` to `public/data/<id>/run.json`. Source-of-truth (`runs/<id>/sources/*.md`)
  is never touched. Recovery is always possible by re-exporting at any threshold. This is NOT
  Mode D; it is the operator's own data, explicitly authorized.

- **FE gate default threshold mismatch** (medium risk, mitigated by AC F4-004): If
  `sensitivityThreshold` is not passed to SourceCard from ProvenanceModal or ClaimInspector, the
  default `personal` threshold re-masks `work_sensitive` and `client_sensitive` content even after
  re-export. The implementer must trace every SourceCard call site and ensure the prop is threaded
  correctly. Fallback: `VITE_SHOW_ALL=1` bypasses the gate entirely, providing a belt-and-suspenders
  guarantee for the LAN build.

- **Future export at lower threshold** (low risk, process concern): If the operator later runs
  `rf run export --all` with a lower threshold (e.g., for a different deployment), run.json files
  will be re-redacted. This is reversible and expected. Document in the README or viewer docs.

- **No runs with sensitive sources in the dataset**: If all existing runs only have `public`
  sensitivity sources, the pre-flight verification (AC F4-002) and the smoke test (F4-SMOKE-001)
  may not find a meaningful test case. The implementer should note this in the completion report
  and verify by inspecting `runs/*/sources/*.md` sensitivity fields directly.

---

## 12. Implementation Notes

**Suggested approach:**

1. **Config first**: edit `foundry.yaml` line 28: `public` → `client_sensitive`.
2. **Type fix**: add `redacted?: boolean` to `RFResolvedSource` after `dangling: boolean`
   (run-export.ts line 86). Run `tsc --noEmit` to confirm.
3. **FE gate alignment**: trace `sensitivityThreshold` prop from ProvenanceModal and
   ClaimInspector call sites. Simplest fix — combine (b) + (c):
   - (b) Change `isRedacted()` fallback default (line 32) from `personal` to `client_sensitive`.
   - (c) Add `VITE_SHOW_ALL` early-return:
     ```typescript
     if (import.meta.env.VITE_SHOW_ALL === '1') return false;
     ```
   Document chosen approach in completion report.
4. **Pre-flight**: `grep -r "quote:" runs/*/sources/*.md | head -20` to confirm unredacted
   truth exists before re-export.
5. **Re-export + rebuild**: `rf run export --all` then `pnpm --filter runs-viewer build`.
6. **Smoke test**: open viewer, navigate to a source — confirm non-empty quote, no redaction marker.
7. **Deploy**: `systemctl --user restart research-foundry-ui.service`.

**Known gotchas:**

- `isRedacted()` default is `personal` (SourceCard.tsx:32) — this is the re-masking source.
- `VITE_SHOW_ALL` must be prefixed `VITE_` for Vite `import.meta.env` access.
- `pnpm build` re-runs the export internally via `prebuild-static-data.mjs`; a separate
  `rf run export --all` first is redundant but useful as a pre-flight verification step.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: list with brief reason for each.
- **Pre-flight result**: output of quote check (AC F4-002).
- **Re-export result**: `rf run export --all` confirmed; runs refreshed count.
- **FE gate approach**: which option (a/b/c) chosen and why.
- **Validation results**: table of F4-VAL-001 through F4-SMOKE-001 (pass/fail).
- **Pre-change-run resilience note**: include AC F4-005 wording verbatim.
- **Deviations**: any material changes and justification.
- **Follow-up**: e.g., thread threshold prop more robustly; add G5 Settings toggle.

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion
Report template.

---

## Metadata & References

**Tier**: 1 (4 points)

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase
orchestration. Note: this is the operator's own LAN data, explicitly authorized. NOT Mode D.

**Reviewer**: `task-completion-validator` (mandatory) — must verify ACs F4-001 through F4-006
and the completion report pre-change-run resilience note before Opus commits.

**Related Documents**:
- `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md` — parent epic
- Epic brief intel §1.8 — redaction backend/FE details (source of truth for this contract)
- `src/research_foundry/services/export_service.py` — `_resolve_source()` ~lines 277–295
- `foundry.yaml` lines 22–28 — viewer config block
- `frontend/runs-viewer/src/types/rf/run-export.ts` — `RFResolvedSource` interface
- `frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx` — `isRedacted()` gate

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass
validation. Key decisions needed during implementation:

- **Threshold prop wiring** (AC F4-004): choose and document approach (a), (b), or (c) from
  §12. Option (c) + (b) together is the lowest-diff path.
- **VITE_SHOW_ALL** (AC F4-007): implement only if time permits after core ACs pass. It is
  belt-and-suspenders, not required for correctness.
- **No backend code changes needed**: `export_service.py` works correctly once `foundry.yaml`
  is updated. Do not modify it.
- **Scope discipline**: do not refactor `SourceCard` beyond the gate fix; do not touch
  `governance.py`; do not add sensitivity UI controls (G5 scope).

Stay within scope. The reviewer will check for scope drift.
