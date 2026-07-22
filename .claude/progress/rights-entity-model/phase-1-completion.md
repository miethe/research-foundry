## Phase 1 Completion Note — Evidence Taxonomy (C2)

### Summary

Added an evidence-quality taxonomy (`evidence_item_type`, `judgment_basis`) to
`schemas/source_assertion.schema.yaml` as a required `extensions.evidence_taxonomy`
sibling block — fully independent of `rights_extension` per the locked §9.1
adjudication. Backed by a positive non-reachability guard, an `other`-extensibility
test (OQ-RF-2), and a new AST-based no-derivation static guard enforcing the FR-8
three-axes invariant (`evidence_item_type` / `judgment_basis` / `component_type`
must never be computed from one another).

### Tasks

- [x] P1-1 → data-layer-expert — added `extensions.evidence_taxonomy.evidence_item_type`
  (8-member enum incl. `other`), sibling of `rights_extension`; positive
  non-reachability guard test; valid-instance + missing-field-fails tests.
- [x] P1-2 → data-layer-expert — added `judgment_basis` (5-member enum incl.
  `unassessed`) alongside `evidence_item_type` in the same block; fail-closed
  absence contract documented in schema `description:` (repo has no `default:`
  keyword convention).
- [x] P1-3 → python-backend-engineer — `tests/test_no_derivation_guard.py`, an
  AST walker parametrized over every file in `src/research_foundry/` (118 items)
  that flags any function assigning one axis field from an expression referencing
  a different axis field. Passes clean on the current (derivation-free) codebase.
- [x] P1-4 → data-layer-expert — `other`-extensibility test: full valid instance
  with `evidence_item_type: other`; schema description asserts extensibility
  contract (extension point / specialize / not a closed clinical list).

### Validator Verdict

`task-completion-validator`: **PASS** (0 fix cycles). Verified independence of
axes, non-vacuousness of the no-derivation guard, completeness of the
extensibility test, and correct sibling (non-nested) placement relative to
`rights_extension`. Full command run: `pytest tests/test_schema_validation.py
tests/test_no_derivation_guard.py tests/test_reusable_assertion_ledger_phase1.py -q`
→ 226 passed, 0 failed.

Reviewer noted one non-blocking cosmetic nit: the progress file's
`success_criteria[].status` fields (P1-SC1–SC3) remain `pending` in frontmatter
despite `status: completed` / `progress: 100`. Left as-is — the artifact-tracking
CLI (`update-field.py`/`update-status.py`) has no safe nested-list item setter for
`success_criteria`, and a blunt `--set` risks overwriting the whole list; direct
YAML edits are prohibited by `.claude/rules/progress-cli-only.md`. Flagging for
Opus/tooling follow-up rather than risking corruption.

### Files Changed

- `schemas/source_assertion.schema.yaml` — added required `extensions.evidence_taxonomy`
  block (`evidence_item_type`, `judgment_basis`) — data-layer-expert (P1-1, P1-2).
- `tests/test_schema_validation.py` — added/extended tests for both new fields,
  non-reachability guards, and the `other`-extensibility contract — data-layer-expert
  (P1-1, P1-2, P1-4).
- `tests/test_reusable_assertion_ledger_phase1.py` — fixture updated to remain
  valid under the two newly required fields — data-layer-expert (P1-2).
- `tests/test_no_derivation_guard.py` (new) — AST-based three-axes derivation
  guard — python-backend-engineer (P1-3).

### Deviations & Risks

- **Expected, out-of-scope breakage (not a Phase 1 defect):** making
  `evidence_item_type`/`judgment_basis` required now breaks
  `tests/unit/test_assertion_materialization.py` (10 failures),
  `tests/unit/test_assertion_backfill.py` (10 failures), and
  `tests/api/test_assertions_api.py` (17 failures) — these production write
  paths don't yet populate the new fields. The plan explicitly defers this
  wiring to the capture-time-emission milestone (Phase 3/4, "fail-closed by
  construction" — plan line ~196); Phase 1's scope was schema-only. Confirmed
  by the validator as correctly out of scope here. **Must be resolved before
  Phase 3/4 exits**, not before Phase 1.
- No other deviations. All four tasks completed within their planned
  file-ownership boundary (`schemas/source_assertion.schema.yaml` +
  new/updated test files only).

### Commits (this worktree)

- `e32f554` — feat(rights): P1 — source_assertion foundation extension
