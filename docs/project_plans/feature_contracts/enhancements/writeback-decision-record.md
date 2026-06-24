---
title: "Feature Contract: decision_record Writeback (close the RF→project harvest seam)"
schema_version: 2
doc_type: feature_contract
status: draft
created: 2026-06-23
updated: 2026-06-23
feature_slug: "writeback-decision-record"
category: "enhancements"
estimated_points: 4
tier: 1
owner: null
priority: high
risk_level: low
changelog_required: true
related_documents:
  - docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md
  - docs/project_plans/reports/investigations/rf-writeback-and-backlog-reconcile-handoff.md
spike_ref: null
prd_ref: null
plan_ref: null
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/services/writeback.py
  - src/research_foundry/services/planning.py
  - templates/meatywiki_decision_record.md
  - schemas/meatywiki_writeback.schema.yaml
---

> **IntentTree:** maps to node `node_01KVQZGABG67QB66HXJWSC019Q` (`harvest-seam-fix`,
> RIB-024-adjacent), under the research-foundry "Inbound: RF research-harvest outcomes (2026-06-22)"
> container (`node_01KVQYD2BC6184CCF5QBDEAWJ1`). This is **Gap 1** of the two-seam harvest handoff;
> do it first — it stops the bleeding so future completed runs self-harvest.

# Feature Contract: decision_record Writeback (close the RF→project harvest seam)

## 1. Goal

Make `rf writeback` emit an **additive** `decision_record` writeback that carries each run's actual
engineering recommendation (its inference claims), instead of dropping the decision at the RF→project
boundary where only a generic `source_note` survives today.

---

## 2. User / Actor

- **Primary user**: The downstream-project maintainer who consumes RF writebacks — they need "here is
  what to build / decide," not just "here is a source note," when a completed run lands in their work graph.
- **Secondary users**: The RF operator running harvest review (each completed run now self-harvests its
  decision, turning a fan-out review into a quick scan); downstream MeatyWiki ingestion (decision_record
  is already a legal `writeback_type` in its vault contract).

---

## 3. Job To Be Done

When **an RF run finishes synthesis with inference/recommendation claims**, the operator wants to
**emit a decision-record writeback that carries the run's Decision + Rationale (with provenance back to
the source claims)**, so they can **route the run's actual decision into a project's work graph without
hand-harvesting it from prose**.

---

## 4. Scope

### In Scope

- New `writeback.py::_render_decision_record(ledger, ...)` that selects claims where
  `status == "inference"` (surfacing `claim_type == "recommendation"` first) and populates the existing
  dead `templates/meatywiki_decision_record.md` template (Context / Decision / Rationale / Consequences /
  Links) from each claim's `inference_basis.{reasoning_summary, from_claims}`.
- Emit the rendered file as `writebacks/meatywiki_decision_record.md` with front-matter
  `writeback_type: decision_record`.
- Wire the new render into the `writeback.py::writeback()` target dispatch, **keeping the existing
  `source_note` render unchanged and additive** (both are emitted for the `meatywiki` target).
- Add a `decision_record` entry to the expected-writebacks declaration
  `services/planning.py::_WRITEBACKS` so a run's contract becomes
  `{meatywiki: [source_note, decision_record], skillmeat: skillbom_candidate, ccdash: execution_event}`.
- Graceful no-op: a deterministic-only run (ledger with zero `status: inference` claims) emits **no**
  decision-record file and does **not** error.
- One-time backfill path over the **18 already-completed runs**: a `rf writeback --decision-record-only
  --run <id>` flag (or an equivalent small backfill script) that renders only the decision-record for an
  existing run without re-emitting/disturbing its other writebacks.
- Unit test over a fixture ledger (≥1 recommendation claim) asserting decision-record content, plus
  schema validation of the emitted file against `schemas/meatywiki_writeback.schema.yaml`.

### Out of Scope

- **Gap 2** (`rf backlog reconcile` / backlog status+links lifecycle) — separate, independent Tier-1
  contract (`node_01KVQZGHZ96CNQBCS70ZV4MXZR`).
- Making `skillbom_candidate` non-static (handoff sketch step 3) — explicitly deferred; this contract
  keeps `_render_skillbom()` unchanged to stay within the harvest-seam scope.
- Changing the `source_note` render's content or selection logic (it stays exactly as-is).
- Any schema change to `meatywiki_writeback.schema.yaml` or `claim_ledger.schema.yaml` — the
  `decision_record` enum value, `claim_type: recommendation`, and `inference_basis` are **already present**
  and schema-legal; this work only makes the code use them.
- New decision-record templates or ADR-shape redesign — reuse the existing template as-is.

---

## 5. UX / Behavior Requirements

- `rf writeback --run <id>` on a run whose ledger contains ≥1 `status: inference` claim emits
  `writebacks/meatywiki_decision_record.md` **in addition to** the existing `meatywiki_writeback.md`
  (`source_note`), `skillbom_candidate.md`, and the ccdash event.
- The emitted decision-record's `Decision` and `Rationale` sections are populated from the inference
  claims' `inference_basis.reasoning_summary`; `Links` references back to the source claim IDs (from
  `inference_basis.from_claims`). `recommendation`-typed claims appear first.
- `rf writeback --run <id>` on a deterministic-only run (zero inference claims) behaves exactly as today:
  no decision-record file, exit 0, no error/warning noise beyond the normal output.
- `rf writeback --decision-record-only --run <id>` renders **only** the decision-record for an existing
  run, leaving the run's other writeback files untouched (used for the 18-run backfill).
- Existing `rf writeback` output (the three current files) is byte-for-byte unchanged when the
  decision-record is additive; the only difference is the presence of the new file when inference claims exist.

---

## 6. Data Requirements

- **Entities affected**: writeback artifacts under `runs/<id>/writebacks/`; the run's expected-writebacks
  contract emitted via `services/planning.py::_WRITEBACKS`.
- **Data read (existing, no schema change)**:
  - `runs/<id>/claims/claim_ledger.yaml` — claims with `status: inference`, optional
    `claim_type: recommendation`, and `inference_basis: {from_claims: [...], reasoning_summary: "..."}`
    (schema `schemas/claim_ledger.schema.yaml`, already defines these).
  - `templates/meatywiki_decision_record.md` — existing dead template (Context / Decision / Rationale /
    Consequences / Links).
- **New fields**: none. No schema migration. `writeback_type: decision_record` is already in the
  `meatywiki_writeback.schema.yaml` enum (`[source_note, concept_update, decision_record, pattern,
  project_update, insight]`).
- **State changes**: adds one new output file (`meatywiki_decision_record.md`) per run that has inference
  claims; appends a `decision_record` row to the run's `_WRITEBACKS` contract.
- **Storage implications**: none beyond the additional markdown file per qualifying run.

---

## 7. API / Integration Requirements

**New or modified CLI surface:**
- `rf writeback --run <id>` — modified: now also dispatches the decision-record render (additive).
- `rf writeback --decision-record-only --run <id>` — new flag: renders only the decision-record for an
  existing run (backfill path). (Equivalently, a small `scripts/` backfill helper iterating the 18 runs —
  agent may choose whichever is cleaner, but the per-run flag is preferred for reuse.)

**External service calls**: none. Render is deterministic and file-backed (no model calls).

**Internal service dependencies:**
- `services/writeback.py::writeback()` — the `rf writeback` command at `cli_commands.py:414`; the dispatch
  point the new render wires into. (Not `bundle` or `synthesize`.)
- `services/synthesis.py::_build_body()` — already routes `status == "inference"` claims into the report's
  `## Inferences` section; **reuse its selection logic** for the decision-record render.
- `services/planning.py::_WRITEBACKS` (≈ lines 110–114) — expected-writebacks declaration to extend.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `src/research_foundry/services/writeback.py` — mirror the structure of `_render_meatywiki()`
  (≈ lines 272–339) and `_render_skillbom()` (≈ lines 342–421) for the new `_render_decision_record()`;
  follow the same template-load + front-matter-emit + atomic-write conventions.
- `src/research_foundry/services/synthesis.py::_build_body()` — reuse its `status == "inference"` claim
  selection rather than re-deriving it.
- `cli_commands.py::register(app)` flat registration pattern for the new `--decision-record-only` flag on
  the existing `writeback` command.

**Must not change** (protected areas):
- The `source_note` render (`_render_meatywiki()`) — its hard-coded `writeback_type="source_note"`
  (line ~301) and its `_supported_claims(ledger)` selection stay exactly as-is. The decision-record is
  additive, never a replacement.
- `_render_skillbom()` — left unchanged (out of scope this contract).
- `schemas/meatywiki_writeback.schema.yaml` and `schemas/claim_ledger.schema.yaml` — no schema edits.

**New dependencies:**
- Allowed? **No.** *No new dependencies expected* — all scaffolding (template, schema enum, claim data,
  render reference) already exists; this is selection logic + wiring + tests.

---

## 9. Acceptance Criteria

<!-- Reproduced faithfully from the handoff "Gap 1 → Acceptance criteria", plus the unit-test and
     schema-validation requirements. -->

- [ ] A run whose ledger contains `status: inference` / `claim_type: recommendation` claims emits a
      `writebacks/meatywiki_decision_record.md` with front-matter `writeback_type: decision_record`,
      a populated **Decision** + **Rationale** sourced from `inference_basis`, and a **Links** section
      referencing back to the source claims (`inference_basis.from_claims`).
- [ ] `recommendation`-typed inference claims are surfaced first in the rendered decision-record.
- [ ] The existing `source_note` writeback (`meatywiki_writeback.md`) is unchanged — the decision-record
      is additive, not a replacement.
- [ ] A deterministic-only run (no `status: inference` claims) emits **no** decision-record file and does
      **not** error.
- [ ] `services/planning.py::_WRITEBACKS` now declares the `decision_record` writeback so the run contract
      reads `{meatywiki: [source_note, decision_record], skillmeat: skillbom_candidate, ccdash: execution_event}`.
- [ ] A `rf writeback --decision-record-only --run <id>` path (or backfill script) re-renders the
      decision-record over the **18 already-completed runs** without disturbing their other writeback files.
- [ ] A unit test over a fixture ledger with ≥1 recommendation claim asserts the decision-record content
      (Decision/Rationale populated from `inference_basis`, Links to source claims).
- [ ] The emitted decision-record **schema-validates** against `schemas/meatywiki_writeback.schema.yaml`.

---

## 10. Validation Requirements

- [ ] **Typecheck / lint** passes: `flake8 src/research_foundry/services/writeback.py
      src/research_foundry/services/planning.py --select=E9,F63,F7,F82` (and `mypy --ignore-missing-imports`
      on the changed modules if clean today).
- [ ] **Tests added**: unit test over a fixture claim ledger exercising both the populated-decision-record
      path (≥1 recommendation claim) and the deterministic-only no-op path.
- [ ] **Schema validation**: test asserts the emitted decision-record validates against
      `schemas/meatywiki_writeback.schema.yaml`.
- [ ] **Relevant tests pass**: run the writeback test module via the project venv
      (`./.venv/bin/python -m pytest tests/ -k writeback` or `uv run pytest -k writeback`), **not** the
      pyenv shim — see the "pytest must run under venv" gotcha.
- [ ] **Full suite (changed scope)**: `./.venv/bin/python -m pytest` passes for the writeback/planning
      scope before squash-merge.
- [ ] **Docs / CHANGELOG**: `changelog_required: true` — add a CHANGELOG entry for the new decision_record
      writeback. Update writeback-related docs only if an existing doc enumerates the emitted writeback set.
- [ ] **No unrelated changes** introduced (no skillbom changes, no schema edits, no source_note edits).

---

## 11. Risk Areas

- **Empty/malformed `inference_basis`**: LLM-augmented synthesis populates `inference_basis`, but the
  deterministic `claim_mapping.py::build_claim_ledger()` stubs it empty. The render **must** treat a missing
  or empty `inference_basis` / zero inference claims as a clean no-op (no file, no error). This is the
  primary correctness risk — test it explicitly.
- **Additive-not-replacement regression**: care that wiring the new render into `writeback()` dispatch does
  not alter the existing `source_note`/`skillbom`/ccdash outputs. Assert the three existing files are
  unchanged when the decision-record is added.
- **Backfill side effects**: `--decision-record-only` over the 18 runs must not re-emit or mutate the
  runs' other writeback files (idempotent, decision-record-only). Verify on a copy or dry-run before a
  real backfill.
- **Test-fixture realism**: the fixture ledger must carry a realistic `inference_basis` shape
  (`{from_claims, reasoning_summary}`) so the schema-validation assertion is meaningful.

---

## 12. Implementation Notes

**Suggested approach** (agent may improve):
- Start by reading `_render_meatywiki()` and `_render_skillbom()` in
  `src/research_foundry/services/writeback.py` to copy the load-template → build-context →
  emit-front-matter → atomic-write shape.
- Add `_render_decision_record(ledger, ...)`: select `status == "inference"` claims (reuse
  `synthesis.py::_build_body()` selection), order `claim_type == "recommendation"` first, map each claim's
  `inference_basis.reasoning_summary` into **Decision/Rationale** and `inference_basis.from_claims` into
  **Links**, render via `templates/meatywiki_decision_record.md`, emit `writeback_type: decision_record`.
- Wire into `writeback()` target dispatch (additive to the meatywiki target); add the `decision_record`
  row to `planning.py::_WRITEBACKS`.
- Add the `--decision-record-only` flag to the `writeback` command in `cli_commands.py`.
- Guard the zero-inference no-op before any file write.

**Similar existing code**:
- Reference: `src/research_foundry/services/writeback.py::_render_meatywiki()` (≈ lines 272–339) — mirror
  its template/front-matter/write conventions.
- Reference: `src/research_foundry/services/synthesis.py::_build_body()` — reuse its `status == "inference"`
  selection logic so report and decision-record agree on what counts as an inference.
- Reason: keeps the new render consistent with the two existing emit paths and with how the report itself
  selects inferences.

**Known gotchas**:
- The decision content only exists on the **LLM-augmented synthesis path**; deterministic-only runs stub
  `inference_basis` empty — the no-op path is the common case for many runs, so it must be the first thing
  the render checks.
- Run pytest under the project venv (`./.venv/bin/python -m pytest` / `uv run pytest`), never the pyenv
  shim, or you'll hit the recurring "No module named research_foundry" failure.
- The schema enum and `claim_type: recommendation` already exist — do **not** "add" them; only use them.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: List of all modified/new files with brief reason
- **Tests run**: What tests were added/updated and results
- **Validation results**: Table of all validation commands and their results (pass/fail/not applicable)
- **Deviations from contract**: Any material changes to the contract during implementation and why
- **Risks / Limitations**: Any remaining risks or known limitations (incl. backfill outcome over the 18 runs)
- **Follow-up recommendations**: Suggested next steps (e.g., Gap 2 `rf backlog reconcile`; deferred
  skillbom_candidate enrichment)

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report template.

---

## Metadata & References

**Tier**: 1 (3–8 points) — estimated 4 pts.

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase orchestration.

**Reviewer**: `task-completion-validator` (mandatory).

**Related Documents**:
- `docs/project_plans/reports/investigations/rf-writeback-and-backlog-reconcile-handoff.md` — authoritative
  scope source (Gap 1 problem statement, grounded current behavior, implementation sketch, acceptance criteria).
- `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md` — the 2026-06-22 harvest
  that surfaced the seam (18 completed runs whose decisions never reached a project work graph).
- IntentTree: `node_01KVQZGABG67QB66HXJWSC019Q` (`harvest-seam-fix`, RIB-024-adjacent).

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass validation. If you find:

- **Scope ambiguity**: Ask one focused question or make a conservative assumption and note it in the Completion Report.
- **Impossible constraints**: Flag in the Completion Report before attempting workarounds.
- **Better implementation path**: Document the deviation in the Completion Report with justification.

Stay within scope. Keep the decision-record **additive** — do not touch `source_note`, `skillbom_candidate`,
or any schema. The reviewer will check for scope drift.
