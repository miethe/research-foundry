---
title: "Feature Contract: rf backlog reconcile — run→backlog lifecycle writer"
schema_version: 2
doc_type: feature_contract
status: completed
created: 2026-06-23
updated: 2026-06-24
feature_slug: "backlog-reconcile-command"
category: "enhancements"
estimated_points: 4
tier: 1
owner: null
priority: medium
risk_level: low
changelog_required: true
related_documents:
  - docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md
  - docs/project_plans/reports/investigations/rf-writeback-and-backlog-reconcile-handoff.md
spike_ref: null
prd_ref: null
plan_ref: null
commit_refs:
  - 20b56c7
pr_refs: []
files_affected:
  - src/research_foundry/services/backlog_metadata.py
  - src/research_foundry/cli_commands.py
intenttree_node: node_01KVQZGHZ96CNQBCS70ZV4MXZR
---

# Feature Contract: rf backlog reconcile — run→backlog lifecycle writer

> This contract implements **Gap 2** of the 2026-06-22 harvest seam-fix handoff
> (`docs/project_plans/reports/investigations/rf-writeback-and-backlog-reconcile-handoff.md`).
> IntentTree atomic task: `node_01KVQZGHZ96CNQBCS70ZV4MXZR` (tagged `harvest-seam-fix`,
> under the research-foundry "Inbound: RF research-harvest outcomes (2026-06-22)" container).
> It is **independent** of Gap 1 (the decision-record writeback) and can run in parallel or after.

---

## 1. Goal

Add a run→backlog reconciler — `rf backlog reconcile [--dry-run|--write]` backed by
`reconcile_backlog()` in `services/backlog_metadata.py` — that scans completed run directories and
forward-advances each backlog idea's `status` and backfills its `links` block, so runs-on-disk and
backlog lifecycle marks stop drifting apart without any manual editing.

---

## 2. User / Actor

- **Primary user**: The research-foundry operator (Nick) maintaining `backlog/research_idea_backlog.yaml`
  as the durable record of which ideas have been researched, and which run produced each result.
- **Secondary users**: Downstream traceability/automation (IntentTree links, the completed-runs harvest)
  that read `links.run_id` / `status` to map a backlog idea to its run artifacts.

---

## 3. Job To Be Done

When **runs have completed on disk but the backlog still shows them as `proposed`/unlinked** (today: ~38–42
`runs/rf_run_*` dirs exist but only 18 ideas are marked `status: completed` with a non-null `links.run_id`),
the operator wants to **reconcile the backlog against the runs in one command**, so they can **trust the
backlog as the lifecycle source of truth and stop hand-editing status/links after every run**.

---

## 4. Scope

### In Scope

- A **writer** in `services/backlog_metadata.py`: `reconcile_backlog(dry_run: bool)` — currently this
  module is **read-only** (`load_backlog_index`, `lookup_metadata`); this adds the single inverse writer,
  keeping the module the one reader *and* writer of the backlog.
- Scan `runs/*/run.yaml` for `backlog_idea_ref`, map each back to its backlog idea, and:
  - **Advance `status` forward only** (e.g. `proposed`/`captured`/`planned` → `running`/`completed`); never
    regress a status that is already further along.
  - **Backfill `links.{run_id, intent_id, intenttree_node_id}` into null fields only** from the matching
    `run.yaml`; never overwrite a non-null link (preserve manual edits).
- A new CLI subcommand `rf backlog reconcile [--dry-run] [--write]`, registered in `cli_commands.py`
  following the existing flat `register(app)` pattern. The `rf backlog` namespace is **currently free/unused**.
- **Default to `--dry-run`**: print a per-idea diff of what *would* change (stale status, null links to fill)
  without writing.
- `--write`: apply the forward-advance + null-fill mutations, then persist the file (atomic write,
  preserving existing structure/ordering as far as practical).
- **Idempotency**: a second `--write` (or `--dry-run`) immediately after reports zero changes.
- **Optional inverse-drift flag** (report-only, both modes): surface backlog entries marked `completed`
  with no run dir, and run dirs whose `run.yaml` carries no `backlog_idea_ref` (so they can be captured/tagged).
- Unit tests over a fixture backlog + fixture run dirs covering: stale-advance, null-fill-only,
  no-regression, no-overwrite, idempotent re-run, and schema-validity of the written file.

### Out of Scope

- **Gap 1 (the decision-record writeback)** — separate contract, separate IntentTree node
  (`node_01KVQZGABG67QB66HXJWSC019Q`).
- The existing **backlog → run.yaml** direction: `scripts/backfill_run_metadata.py` already does that and
  **requires `links.run_id` to already be set**; this contract is its missing inverse and does not modify it.
- Editing `backlog/seed_swarm_runs.sh` (emits only `rf capture` lines; writes nothing to the backlog).
- Changing how `rf capture` / `services/planning.py::plan_run()` read the backlog (they copy fields onto the
  new run's `run.yaml`; making *them* write back is a larger, separate change and is **not** in scope —
  reconcile is the batch repair path).
- Any new status values, schema changes, or lifecycle redefinition — the lifecycle
  (`proposed → captured → planned → running → completed`) and `links` block already exist in
  `schemas/research_idea_backlog.schema.yaml`.
- Network, IntentTree API calls, or writeback emission.

---

## 5. UX / Behavior Requirements

- `rf backlog reconcile` (no flag) behaves as `--dry-run`: prints, per `runs/*/run.yaml` carrying a
  `backlog_idea_ref`, whether the matched idea's `status` and `links.run_id` are stale/missing — and writes
  nothing. Exit 0.
- `rf backlog reconcile --write` applies forward-advance + null-fill, persists the backlog, and prints a
  summary (counts of statuses advanced, links backfilled, entries unchanged). Exit 0.
- `--dry-run` and `--write` are mutually exclusive-by-intent; if neither given, default dry-run. (If both are
  passed, prefer the conservative behavior — treat as dry-run or error clearly; the executor may choose, and
  must note the choice.)
- Output is human-scannable (Rich, ASCII-compatible — no Unicode box-drawing, per project convention): one
  line per affected idea showing `RIB-NNN: status X→Y, links.run_id ∅→rf_run_…`.
- **Never regress**: an idea already at `completed` whose run maps to it is reported as "already current",
  not downgraded.
- **Never overwrite**: a non-null `links.intent_id` / `intenttree_node_id` is left as-is even if `run.yaml`
  carries a different value; only null fields are filled. (Surface a mismatch as a note if cheap, but do not mutate.)
- Inverse drift (optional) is printed in a clearly separate section labeled as advisory (e.g.
  "completed without run dir", "run dir without backlog_idea_ref"); it triggers no mutations.
- A clean run (no drift) prints "0 changes" and exits 0.

---

## 6. Data Requirements

- **Entities affected**:
  - `backlog/research_idea_backlog.yaml` — each idea's `status` field and `links` block
    (`raw_idea_id, intent_id, intenttree_node_id, run_id`) may be mutated under `--write`.
  - `runs/*/run.yaml` — **read only**; source of `backlog_idea_ref`, `run_id` (the run dir / run id),
    `intent_id`, `intenttree_node_id`.
- **New fields**: none. All target fields already exist in `schemas/research_idea_backlog.schema.yaml`.
- **State changes**: `status` advances **forward only** along
  `proposed → captured → planned → running → completed`; `links.*` null fields are filled. No deletions, no
  regressions, no overwrites of non-null links.
- **Storage implications**: in-place rewrite of one YAML file via atomic temp-file→rename. No new files,
  tables, or indexes. The written file must still validate against
  `schemas/research_idea_backlog.schema.yaml`.

---

## 7. API / Integration Requirements

**New or modified CLI surface:**
- `rf backlog reconcile [--dry-run] [--write]` — new subcommand under the previously-unused `rf backlog`
  namespace, registered via the existing flat `register(app)` pattern in
  `src/research_foundry/cli_commands.py`.

**External service calls**: none (fully file-backed; no network, no IntentTree/MeatyWiki/CCDash calls).

**Internal service dependencies:**
- `src/research_foundry/services/backlog_metadata.py` — extend with `reconcile_backlog(dry_run)` and any
  small write/persist helper; reuse the module's existing load path (`load_backlog_index`) as the reader.
- Run-discovery: glob `runs/*/run.yaml` (mirror whatever path/loader convention the codebase already uses
  for run YAML; the executor should follow the existing reader, not invent a new one).

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `src/research_foundry/services/backlog_metadata.py` — the single load/lookup accessor; the new writer lives
  here so the module stays the single point of backlog I/O.
- `src/research_foundry/cli_commands.py::register(app)` — flat command registration; mirror an existing
  subcommand's signature/flag wiring.
- Atomic file writes: temp dir → atomic move (per CLAUDE.md security pattern), preserving file structure.
- Rich CLI output, ASCII-compatible (no Unicode box-drawing — tests assert on output).
- Python 3.9+ with type hints; `from __future__ import annotations` where forward refs are used.

**Must not change** (protected areas):
- `scripts/backfill_run_metadata.py` (the backlog→run.yaml direction).
- `schemas/research_idea_backlog.schema.yaml` (no schema edits — the contract is to write valid data).
- The backlog lifecycle vocabulary and `links` block shape.
- `rf capture` / `services/planning.py::plan_run()` read-only backlog behavior.

**New dependencies:**
- Allowed? **No**
- *No new dependencies expected* — YAML load/dump and globbing are already in use in this package.

---

## 9. Acceptance Criteria

<!-- Reproduces the handoff's "Gap 2 → Acceptance criteria" faithfully. -->

- [ ] `rf backlog reconcile --dry-run` reports, for every `runs/*/run.yaml` with a `backlog_idea_ref`,
      whether the matching idea's `status` / `links.run_id` is stale, **without writing** any file.
- [ ] `rf backlog reconcile --write` advances stale `status` to `running`/`completed` and backfills
      `links.{run_id, intent_id, intenttree_node_id}` — **without** regressing any manually-advanced status or
      overwriting any non-null link.
- [ ] Running reconcile again immediately reports **zero changes** (idempotent), under both `--dry-run`
      and `--write`.
- [ ] After one `--write`, the `status: completed` count and the non-null `links.run_id` count both
      **reconcile** with the set of finished run dirs — the current 18-vs-(~38–42) gap closes or is explained
      per-run (via the optional inverse-drift report).
- [ ] The written `backlog/research_idea_backlog.yaml` still **validates** against
      `schemas/research_idea_backlog.schema.yaml`.
- [ ] `rf backlog reconcile` with no flag defaults to dry-run (no mutation).
- [ ] (Optional, if implemented) Inverse drift — `completed` ideas with no run dir, and run dirs with no
      `backlog_idea_ref` — is surfaced as an advisory report and triggers no mutation.

---

## 10. Validation Requirements

- [ ] **Typecheck** passes (`mypy src --ignore-missing-imports` for the touched modules)
- [ ] **Lint** passes (`flake8 src --select=E9,F63,F7,F82`; `black` formatting clean)
- [ ] **Tests** added: unit tests over fixture backlog + fixture run dirs (stale-advance, null-fill-only,
      no-regression, no-overwrite, idempotency, schema-validity)
- [ ] **Relevant tests pass** (run under the project venv: `./.venv/bin/python -m pytest` — NOT the pyenv
      shim, per the recurring "No module named research_foundry" gotcha; in a worktree use
      `PYTHONPATH=<worktree>/src <main>/.venv/bin/python -m pytest`)
- [ ] **Build** passes (`pytest` for the backlog/reconcile scope; avoid the non-isolated full-suite test that
      pollutes tracked real-run files — scope to the new tests + `services`/`cli` tests)
- [ ] **Docs updated**: CHANGELOG entry (`changelog_required: true`); note the new `rf backlog reconcile`
      command wherever the CLI surface is documented
- [ ] **No unrelated changes** introduced

---

## 11. Risk Areas

- **Manual-edit preservation**: the 18 hand-curated completed/linked entries must survive untouched. The
  null-fill-only + forward-only rules are the safety boundary — get the "is this field null?" and "is target
  status strictly ahead?" checks exactly right, and dry-run them against the real backlog before `--write`.
- **YAML round-trip fidelity**: dumping the backlog must not reorder/strip fields or mangle the file such that
  the schema fails or the human diff becomes noise. Prefer a structure-preserving dump; validate against the
  schema after write.
- **Run→idea mapping ambiguity**: multiple run dirs may reference the same `backlog_idea_ref`, or a
  `backlog_idea_ref` may not match any idea. Define a deterministic rule (e.g. most-advanced run wins for
  status; first/most-recent for links) and report unmatched refs rather than guessing.
- **Status-order definition**: there must be one canonical ordered lifecycle list to compare against;
  hard-coding it wrong (or diverging from the schema enum) would mis-advance. Derive/validate it against
  `schemas/research_idea_backlog.schema.yaml`.
- **Test isolation**: the known non-isolated full-suite test mutates tracked real-run files — keep new tests
  on fixtures in a tmp dir, and do not run the polluting suite as part of validation (revert if it runs).

---

## 12. Implementation Notes

**Suggested approach** (agent may improve):
- Step 1 — In `services/backlog_metadata.py`, add `reconcile_backlog(dry_run: bool) -> <diff/summary>`:
  load the backlog via the existing reader; glob `runs/*/run.yaml`; build a map `backlog_idea_ref → run.yaml`
  facts (`run_id`, `intent_id`, `intenttree_node_id`); for each matched idea compute the forward-only status
  target and the null-only link fills; collect a structured diff. If `dry_run`, return the diff only; else
  apply and atomic-write.
- Step 2 — Register `rf backlog reconcile` in `cli_commands.py` with `--dry-run/--write` (default dry-run),
  rendering the diff via Rich (ASCII).
- Step 3 — (Optional) compute inverse drift in the same scan pass and print it as an advisory section.
- Step 4 — Tests on fixtures; assert idempotency by running reconcile twice and checking the second diff is empty;
  validate the written fixture against the schema.

**Similar existing code**:
- Reference (reader to reuse): `src/research_foundry/services/backlog_metadata.py`
  (`load_backlog_index`, `lookup_metadata`).
- Reference (the inverse, for shape/field names): `scripts/backfill_run_metadata.py` — shows the
  backlog↔run.yaml field correspondence (`links.run_id`, `intent_id`, `intenttree_node_id`); this contract
  is its missing inverse.
- Reference (CLI wiring): existing subcommands registered in `src/research_foundry/cli_commands.py`.
- Reference (schema/vocab): `schemas/research_idea_backlog.schema.yaml` for the status enum and `links` shape.

**Known gotchas**:
- The `rf backlog` namespace is free today — registering it must not collide with existing commands (cf. the
  earlier `rf extract` Click collision fixed in `63228e0`).
- Run pytest under the venv interpreter, not the pyenv shim (the recurring "bag error").
- In a worktree, the editable install points at `main/src`; set `PYTHONPATH=<worktree>/src` so the new code
  under test is the worktree's.
- The current on-disk counts (~38–42 run dirs vs 18 completed) are the live drift this is meant to close —
  but the *exact* number that becomes `completed` depends on which runs carry a `backlog_idea_ref`; unmatched
  runs are expected and should be reported, not force-completed.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: List of all modified/new files with brief reason
- **Tests run**: What tests were added/updated and results
- **Validation results**: Table of all validation commands and their results (pass/fail/not applicable)
- **Deviations from contract**: Any material changes to the contract during implementation and why
- **Risks / Limitations**: Any remaining risks or known limitations (notably: how many runs reconciled vs.
  remained unmatched, and why)
- **Follow-up recommendations**: Suggested next steps (e.g. wiring `plan_run()`/`rf capture` to write
  `status: running` + `links.run_id` at creation time so reconcile becomes a rarely-needed repair tool)

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report template.

---

## Metadata & References

**Tier**: 1 (3–8 points) — estimated 4 pts

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase orchestration

**Reviewer**: `task-completion-validator` (mandatory)

**Related Documents**:
- `docs/project_plans/reports/investigations/rf-writeback-and-backlog-reconcile-handoff.md` — Gap 2 scope,
  grounded current behavior, implementation sketch, acceptance criteria
- `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md` — the harvest that
  surfaced the 18-vs-38 drift
- `src/research_foundry/services/backlog_metadata.py` — the read-only accessor this extends with a writer
- `scripts/backfill_run_metadata.py` — the existing backlog→run.yaml direction (the inverse of this work)
- `schemas/research_idea_backlog.schema.yaml` — lifecycle + `links` shape the written file must satisfy
- IntentTree node: `node_01KVQZGHZ96CNQBCS70ZV4MXZR` (harvest-seam-fix, Gap 2)

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass validation. If you find:

- **Scope ambiguity**: Ask one focused question or make a conservative assumption and note it in the Completion Report.
- **Impossible constraints**: Flag in the Completion Report before attempting workarounds.
- **Better implementation path**: Document the deviation in the Completion Report with justification.

Stay within scope. Avoid cleanup, refactors, or feature expansion beyond this contract (especially: do NOT
also implement Gap 1, and do NOT change the backlog→run.yaml backfill script). The reviewer will check for
scope drift.
