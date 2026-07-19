## Phase 3 Completion Note — UI Layer (Approve & Dispatch)

### Summary

Phase 3 adds the runs-viewer's "Approve & Dispatch" action to the existing Writeback tab.
`frontend/runs-viewer/src/api/client.ts` gains its first non-GET binding
(`approveAndDispatchWriteback`), typed against Phase 1's locked `ApproveDispatchResult` DTO
(`src/research_foundry/services/writeback.py`), with a `WritebackApprovalRejection` type +
`isWritebackApprovalRejection()` guard mirroring the existing `agentJobsClient.ts` governance-
rejection precedent. `RunDetailWorkspace.tsx` gains a single new action (`ApproveDispatchAction` +
`ApproveDispatchOutcomePanel`) inside `WritebackTabPanel`: button → confirm dialog → per-target
(meatywiki/skillmeat/ccdash) outcome rendering that degrades gracefully on missing/partial fields,
with governance-rejection vs. generic-error distinguished by response shape/status (never string-
matching). FR-13's pre-existing read-only surface (`WritebackGovernancePanel`,
`WritebackCandidateCard`) is byte-unchanged — verified both by diff inspection and by re-running
its dedicated regression test.

### Tasks

- [x] UI-001 → frontend-developer — typed POST binding `approveAndDispatchWriteback()` +
      `ApproveDispatchResult`/`WritebackGuardResult`/`WritebackViolation`/`WritebackApprovalRejection`
      types + `isWritebackApprovalRejection()` guard + `WritebackApiError` class, all in `client.ts`;
      loopback-gated (mutation-only, no static-mode path), reusing existing
      `isLoopbackEnabled`/`getLoopbackBase`/`getLoopbackAuthHeaders` exports.
- [x] UI-002 → ui-engineer-enhanced — `ApproveDispatchAction`: button gated on
      `run.report_draft != null && writebackAvailable`, local `isDispatching` state, inline confirm
      dialog (reuses existing `rv-modal-overlay`/`rv-modal` classes) before calling the endpoint.
- [x] UI-003 → ui-engineer-enhanced (same session/task as UI-002 — combined, same file owner) —
      `ApproveDispatchOutcomePanel`: renders `overall_status`, `guard_result.passed`, and per-target
      status for meatywiki/skillmeat/ccdash, all with `?? "unknown"`/`?? null` defensive fallbacks
      (R-P2 — no crash on partial/missing fields).
- [x] UI-004 → frontend-developer — verified the governance-rejection discrimination
      (`err instanceof WritebackApiError && isWritebackApprovalRejection(err.body)`) was already
      shape/status-based (no string-matching found); made a small copy/iconography polish pass
      (distinct glyph + wording + hint line per outcome kind so "blocked by policy" reads distinctly
      from "something broke" — PRD FR-12) — no change to the discrimination logic itself, which was
      already correct. Confirmed R7 regression guard: `WritebackGovernancePanel`/`WritebackCandidateCard`
      byte-unchanged; `fr13-writeback-review.test.tsx` run unmodified, 15/15 pass.
- [x] VAL-3 → task-completion-validator — **PASS**. One non-blocking note: the button stays
      visible-but-disabled during dispatch rather than disappearing (functionally prevents double-
      fire; a literal reading of "visible only when not mid-dispatch" would hide it instead). Not
      treated as a required fix.

### Validator Verdict

**PASS** (task-completion-validator, Mode E), zero required fixes, one non-blocking note (see above).
Verified via `git diff` scoped to the two phase-owned files, independent re-run of
`fr13-writeback-review.test.tsx` (15/15), `tsc -p tsconfig.app.json --noEmit` (exit 0), and
`eslint src/api/client.ts src/components/RunDetail/RunDetailWorkspace.tsx --max-warnings=0` (exit 0).

### Files Changed

- `frontend/runs-viewer/src/api/client.ts` — +153/-4 (deletions are header-comment wording updates
  reflecting the new non-GET-only status; no existing GET export modified). Adds
  `approveAndDispatchWriteback`, `ApproveDispatchRequest`, `ApproveDispatchResult`,
  `WritebackGuardResult`, `WritebackViolation`, `WritebackApprovalRejection`,
  `isWritebackApprovalRejection`, `WritebackApiError`.
- `frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx` — +243/-1 (deletion is the
  `useMemo` → `useMemo, useState` import line). Adds `ApproveDispatchAction`,
  `ApproveDispatchOutcomePanel`, `overallStatusChipClass`, `targetStatusChipClass`,
  `WRITEBACK_TARGET_ORDER`, `ApproveDispatchOutcome` type. `WritebackGovernancePanel` and
  `WritebackCandidateCard` are untouched (zero removed/modified lines in either function).

### Deviations & Risks

- None from the plan's Phase 3 scope. UI-002 and UI-003 were dispatched as one combined task to the
  same `ui-engineer-enhanced` session (both own the same file, tightly coupled — button/dialog +
  the outcome rendering it produces) per the batch-delegation file-ownership-first pattern, rather
  than two sequential re-spawns.
- Phase 2's live route is not yet merged into this worktree, so the new client binding and UI action
  have not been exercised against a running server — full end-to-end exercise is explicitly TEST-006
  (Phase 4), consistent with the plan's stated dependency (Phase 3 depends only on Phase 1's locked
  DTO, not Phase 2's live route).
- Full `pnpm test` run shows 2 pre-existing baseline failures (`src/test/provenance-correctness.test.ts`,
  `codegen/generate-types.contract.test.mjs`) unrelated to either touched file — confirmed via grep
  neither references `client.ts` or `RunDetailWorkspace.tsx`.

### Commits

None — this phase ran with **Isolation: none** (shared worktree, no nested worktree created). Per
the phase-owner contract, Opus is the single committer for this run; no commit was made by the
phase-owner. Working tree state at hand-off:
- `M .claude/progress/runs-writeback-approve-dispatch/phase-3-progress.md`
- `M frontend/runs-viewer/src/api/client.ts`
- `M frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx`
