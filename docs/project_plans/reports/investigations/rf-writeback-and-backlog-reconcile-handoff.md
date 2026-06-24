---
schema_version: 2
doc_type: report
report_category: investigation
title: "Handoff — RF Writeback-Contract Depth + Backlog Reconcile (close the harvest seams)"
status: planned
source: agent
created: 2026-06-22
updated: 2026-06-23
feature_slug: rf-writeback-and-backlog-reconcile
description: >
  Engineering handoff for the two structural gaps surfaced by the 2026-06-22 completed-runs
  outcome harvest: (1) RF's writeback contract emits only generic source-notes, dropping each
  run's decision at the RF→project boundary; (2) the backlog status/links lifecycle is
  hand-maintained, so runs-on-disk and backlog completion marks have drifted. Both are bounded
  Tier-1 fixes with most scaffolding already present.
related_documents:
  - docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md
  - backlog/research_idea_backlog.yaml
tags: [research-foundry, writeback, backlog, traceability, seam-fix, handoff]
---

# Handoff — Close the two RF harvest seams

> **Planning status (2026-06-23):** Both gaps are now scoped as Tier-1 Feature Contracts —
> Gap 1 → [`writeback-decision-record`](../../feature_contracts/enhancements/writeback-decision-record.md),
> Gap 2 → [`backlog-reconcile-command`](../../feature_contracts/enhancements/backlog-reconcile-command.md).
> Execute each via `/dev:execute-contract <path>`. See the
> [planning index](./rf-harvest-rf-items-planning-index.md) for sequencing (Gap 1 first).

## Why this exists

The [completed-runs outcome harvest](./rf-completed-runs-outcomes-harvest.md) found that all 18
completed runs had verified `report_deterministic.md` outputs, but **their decisions never reached
any project's work graph** — they had to be harvested by hand. Two RF-side defects caused that.
This handoff scopes both as discrete, bounded fixes. They are independent; do **Gap 1 first** (it
stops the bleeding — future runs self-harvest), then **Gap 2** (it repairs traceability drift).

All paths below are relative to `/Users/miethe/dev/homelab/development/research-foundry`. The CLI is
registered flat in `src/research_foundry/cli_commands.py::register(app)`.

---

## Gap 1 — Writeback contract is too shallow (the RF→project seam)

### Problem (observed)
`rf writeback` emits three files per run under `writebacks/`, but the two markdown ones are generic:
- `meatywiki_writeback.md` is always a **`source_note`** built **only from supported claims** — it
  never carries the engineering recommendation.
- `skillbom_candidate.md` is a static `research_swarm_v0` stub, identical across runs.

So the run's actual decision — which lives in its **inference/recommendation claims** — is dropped at
the boundary. Every downstream project sees a source-note, not "here is what to build."

### Current behavior (grounded)
- Emitter: `src/research_foundry/services/writeback.py::writeback()` (the `rf writeback` command at
  `cli_commands.py:414`; **not** `bundle` or `synthesize`).
- `writeback.py::_render_meatywiki()` (≈ lines 272–339) **hard-codes `writeback_type="source_note"`**
  (line ~301) and selects content **only** via `_supported_claims(ledger)` (`status == "supported"`).
  Inference/recommendation claims are never read.
- `writeback.py::_render_skillbom()` (≈ lines 342–421) writes a fixed `research_swarm_v0` front-matter
  stub; only `id`/`name`/`ccdash_event_id` vary.
- The decision content already exists: `runs/<id>/claims/claim_ledger.yaml` holds claims with
  `status: inference` and `claim_type: recommendation` (schema `schemas/claim_ledger.schema.yaml`),
  each carrying **`inference_basis: {from_claims: [...], reasoning_summary: "..."}`** — the
  from-claims provenance + the rationale that *is* the decision. (These are produced on the
  LLM-augmented synthesis path; the deterministic `claim_mapping.py::build_claim_ledger()` stubs them
  empty, so a decision-record render must no-op gracefully when there are zero inference claims.)
- Render reference: `services/synthesis.py::_build_body()` already routes `status == "inference"`
  claims into the report's `## Inferences` section — reuse its selection logic.

### The fix has a head start (reuse, don't build)
These already exist and are **schema-legal today** — only the code refuses to use them:
- **Template:** `templates/meatywiki_decision_record.md` (full ADR shape: Context / Decision /
  Rationale / Consequences / Links) — currently **dead code**, nothing references it.
- **Schema enum:** `schemas/meatywiki_writeback.schema.yaml` already allows
  `writeback_type: decision_record` (the enum is `[source_note, concept_update, decision_record,
  pattern, project_update, insight]`).
- **Claim type:** `claim_ledger.schema.yaml` already includes `claim_type: recommendation`.

### Implementation sketch
1. Add `writeback.py::_render_decision_record(ledger, ...)`: select claims where
   `status == "inference"` (and surface `claim_type == "recommendation"` first), pulling
   `inference_basis.reasoning_summary` + `from_claims` into the Decision/Rationale sections of
   `templates/meatywiki_decision_record.md`; emit front-matter `writeback_type: decision_record`.
2. Wire it into `writeback.py::writeback()` target dispatch and into the expected-writebacks
   declaration `services/planning.py::_WRITEBACKS` (≈ lines 110–114) so a run's contract becomes
   `{meatywiki: [source_note, decision_record], skillmeat: skillbom_candidate, ccdash: execution_event}`.
   Keep the source-note (it's still useful); the decision-record is **additive**.
3. Make `skillbom_candidate` non-static where cheap: at minimum populate `purpose` and
   `known_failure_modes` from the run's recommendation/inference claims rather than the fixed stub.
4. No-op cleanly when the ledger has zero inference claims (deterministic-only runs) — emit nothing
   rather than an empty decision-record.

### Acceptance criteria
- A run whose ledger contains `status: inference` / `claim_type: recommendation` claims emits a
  `writebacks/meatywiki_decision_record.md` with `writeback_type: decision_record`, populated
  Decision + Rationale from `inference_basis`, and `Links` back to the source claims.
- The existing `source_note` writeback is unchanged (additive, not a replacement).
- A deterministic-only run (no inference claims) emits no decision-record and does not error.
- Unit test over a fixture ledger with ≥1 recommendation claim asserts the decision-record content;
  schema-validates against `meatywiki_writeback.schema.yaml`.

### One-time backfill
Re-run the decision-record render over the **18 already-completed runs** so their harvested outcomes
land as proper `decision_record` writebacks (the harvest doc currently holds them only as prose).
Add a `rf writeback --decision-record-only --run <id>` path or a small backfill script.

### Effort / tier
Tier 1 (Feature Contract), ~3–5 pts. Most of the surface (template, enum, claim data, render
reference) already exists; the work is selection logic + wiring + tests.

---

## Gap 2 — Backlog status/links lifecycle is hand-maintained (traceability drift)

### Problem (observed, quantified)
`backlog/research_idea_backlog.yaml` declares a lifecycle (`proposed → captured → planned → running →
completed`) and a `links` block (`raw_idea_id, intent_id, intenttree_node_id, run_id`), but **nothing
in code ever writes them.** Result: **38 `runs/rf_run_*` dirs on disk, but only 18 ideas marked
`status: completed` and only 18 with a non-null `links.run_id`; 37 entries sit at `proposed` and never
advanced; ~20 runs are unlinked.** The 18 completed/linked entries were hand-edited.

### Current behavior (grounded)
- The backlog is **read-only from code.** Single accessor:
  `src/research_foundry/services/backlog_metadata.py` (`load_backlog_index`, `lookup_metadata`) — loads,
  never writes.
- `rf capture --backlog-idea-ref RIB-NNN` and `rf plan` → `services/planning.py::plan_run()` only
  **read** the backlog entry to copy fields onto the new run's `run.yaml`; neither writes `status` or
  `links.run_id` back.
- `backlog/seed_swarm_runs.sh` only emits `rf capture` lines; it writes nothing to the backlog.
- The only backfill, `scripts/backfill_run_metadata.py`, runs **backlog → run.yaml** and **requires
  `links.run_id` to already be set** (it skips ideas without it). There is **no** inverse, and no
  `rf reconcile` / `rf backlog` command (that CLI namespace is currently free).

### Implementation sketch
1. Add a **run → backlog** writer. Make `services/backlog_metadata.py` the single *writer* too (it is
   already the single reader): a `reconcile_backlog(dry_run=bool)` that scans `runs/*/run.yaml` for
   `backlog_idea_ref`, maps each back to its idea, and sets `status` (`completed`/`running`) +
   `links.run_id` (plus `intent_id`, `intenttree_node_id` from `run.yaml`). Idempotent; preserve manual
   edits (only fill nulls / advance status forward, never regress).
2. Expose as a new CLI subcommand `rf backlog reconcile [--dry-run] [--write]`, registered alongside the
   existing `register()` pattern in `cli_commands.py`. Default to `--dry-run` printing the diff.
3. Optionally also flag the inverse drift: backlog entries marked `completed` with no run dir, and run
   dirs with no `backlog_idea_ref` (so they can be tagged or captured).

### Acceptance criteria
- `rf backlog reconcile --dry-run` reports, for every `runs/*/run.yaml` with a `backlog_idea_ref`,
  whether the matching idea's `status`/`links.run_id` is stale, without writing.
- `rf backlog reconcile --write` advances stale `status` to `completed`/`running` and backfills
  `links.{run_id,intent_id,intenttree_node_id}`, **without** regressing any manually-advanced status or
  overwriting non-null links.
- Re-running immediately reports zero changes (idempotent).
- After one `--write`, `status: completed` count and non-null `links.run_id` count both reconcile with
  the set of finished run dirs (the current 18-vs-38 gap closes or is explained per-run).
- The schema (`schemas/research_idea_backlog.schema.yaml`) still validates the written file.

### Effort / tier
Tier 1 (Feature Contract), ~3–5 pts. New command + writer + dry-run + idempotency + tests; small,
self-contained, no cross-module ripple.

---

## Sequencing, ownership, and routing

| # | Fix | Owner | Tier | Depends on |
|---|-----|-------|------|------------|
| 1 | Decision-record writeback (depth) | research-foundry | T1 (~3–5 pts) | none (scaffolding exists) |
| 2 | `rf backlog reconcile` (lifecycle) | research-foundry | T1 (~3–5 pts) | none |

Do **Gap 1 first** — it is the higher-leverage, "stop the bleeding" fix: once the deterministic tail
emits decision-records, future completed runs harvest themselves and this whole manual review becomes a
quick scan instead of a fan-out. Gap 2 is independent and can run in parallel or right after.

**Connection to the broader harvest:** Gap 1 is itself the seam-fix that harvest outcome **RIB-024**
(adopt the per-seam pattern map) is about — the RF→vault write seam currently emits a lossy artifact.
Worth cross-referencing when RIB-024 is picked up.

**IntentTree:** these two fixes are routed as `atomic_task`s tagged `harvest-seam-fix` under the
research-foundry "Inbound: RF research-harvest outcomes (2026-06-22)" container
(`node_01KVQYD2BC6184CCF5QBDEAWJ1`):

| Fix | IntentTree node | Priority |
|-----|-----------------|----------|
| Gap 1 — decision_record writeback | `node_01KVQZGABG67QB66HXJWSC019Q` | high |
| Gap 2 — `rf backlog reconcile` | `node_01KVQZGHZ96CNQBCS70ZV4MXZR` | medium |
