---
doc_type: design_plan
title: NotebookLM Integration — Sourcing, Reports, Extended Runs, Upload-Back
status: implemented (offline; live-unvalidated)
created: 2026-06-13
author: Nick Miethe
related_documents:
  - docs/projects/research-foundry/bidirectional-integrations-plan.md
  - docs/projects/research-foundry/research-foundry-mvp-spec.md
source_docs:
  - src/research_foundry/adapters/base.py
  - src/research_foundry/integrations/base.py
  - src/research_foundry/services/writeback.py
  - src/research_foundry/services/intake.py
  - src/research_foundry/services/source_cards.py
  - config/governance.yaml
  - .claude/skills/notebooklm/SKILL.md
  - .claude/skills/notebooklm-sync/SKILL.md
  - .claude/specs/workflows/workflow-authoring-spec.md
---

# NotebookLM Integration — Sourcing, Reports, Extended Runs, Upload-Back

## 1. Overview

Google NotebookLM (NLM) is a grounded, source-attached research engine with three
already-deployed Claude Code skills in this repo:

- `notebooklm` — the `notebooklm-py` CLI (v0.3.2): notebook/source/artifact ops, OAuth,
  `--json` machine output (`.claude/skills/notebooklm/SKILL.md`).
- `notebooklm-skill` — Playwright browser automation for `ask_question`,
  `notebook_manager` (list/add/search/activate), `auth_manager`.
- `notebooklm-sync` — a `PostToolUse` hook + batch scripts that auto-sync `.md` files
  into a notebook, tracking a `{project}-sources.json` mapping
  (`.claude/skills/notebooklm-sync/SKILL.md`).

NLM is a **cloud, online-only, non-deterministic** engine. RF is **offline-first,
deterministic-by-default, claim-ledger-authoritative**. The integration philosophy is
therefore identical to the existing ARC and IntentTree bidirectional work
(`bidirectional-integrations-plan.md`): **always write a deterministic on-disk artifact
first; gate the live network call behind `available()`; degrade silently; never let NLM
break the pipeline; never let NLM-authored prose enter a report body without a claim id.**

This plan maps the four requested use cases onto RF's four existing seam types:

| Seam type | RF contract | What it gives us |
|-----------|-------------|------------------|
| **Adapter** | `adapters/base.py` `Adapter` Protocol → `AdapterResult` | discovery legs that emit `source_candidates` + non-authoritative `artifacts` |
| **Integration client** | `integrations/base.py` `IntegrationClient` + `services/writeback.py` / `services/intake.py` | fail-soft bidirectional push/pull behind `available()` |
| **Service hook** | `services/source_cards.py::ingest_source()`, `services/extraction.py` | new `source_type` branch / enrichment inside a pipeline stage |
| **Workflow** | `.claude/workflows/*.js` + four hard constraints | Opus-orchestrated NLM sub-flows woven into swarm/council |
| **Hook-sync** | `notebooklm-sync` `PostToolUse` hook + `batch.py` | zero-code auto-mirror of report/source `.md` files into a notebook |

The **claim ledger remains the sole authority**. NLM output is one of two things and never
a third: (a) a **source** (gets a `source_card`, an `[claim:<id>]`-eligible evidence trail,
and a `degraded`/`requires_network` flag because it is non-reproducible), or (b) an
**artifact** (audio/video/briefing-doc/study-guide) that rides in
`AdapterResult.artifacts` / the evidence bundle but is **never spliced into the report body
as an untagged material claim** (`synthesis.py` guard at line ~219). Gemini-synthesized
insight that has no source card is labeled `**Inference:**` or `**Speculation:**`, exactly
as the verifier (`services/verification.py`, exit code 4) already requires.

---

## 2. Capability Inventory

| NLM capability | Command (skill `notebooklm`) | Sync? | RF use case | Reliability |
|----------------|------------------------------|-------|-------------|-------------|
| Create notebook | `notebooklm create "Title" --json` -> id | sync | upload-back, extended | reliable |
| Add source (URL/file/YouTube) | `notebooklm source add "<loc>" --json` -> source_id | sync | upload-back, sourcing | reliable |
| Grounded web research | `notebooklm source add-research "query" --mode [fast\|deep]` | 2-5 min (deep) | sourcing | reliable, blocks |
| Wait for indexing | `notebooklm source wait <id> -n <nb> --timeout 600` | blocks | extended | reliable |
| Chat / ask (cited) | `notebooklm ask "Q" [-s <src>] --json -n <nb>` -> answer+references | sync | sourcing | reliable |
| Source fulltext | `notebooklm source fulltext <id> --json` | sync | sourcing (quote-level) | reliable |
| Generate report | `notebooklm generate report --format [briefing-doc\|study-guide\|blog-post\|custom] --json` -> task_id | 5-15 min | running-reports | reliable |
| Generate mind-map | `notebooklm generate mind-map` (`.json`) | instant | running-reports | reliable |
| Generate data-table | `notebooklm generate data-table "desc"` (`.csv`) | 5-15 min | running-reports | reliable |
| Generate audio | `notebooklm generate audio "instr" --format [deep-dive\|brief\|critique\|debate] --length [...] --json` -> task_id | 10-20 min | running-reports, extended | rate-limited |
| Generate video | `notebooklm generate video ... --json` -> task_id | 15-45 min | extended | rate-limited |
| Generate quiz/flashcards/slide-deck/infographic | `notebooklm generate <type> ...` | 5-15 min | running-reports | rate-limited |
| Poll artifact | `notebooklm artifact list --json`; `artifact wait <id> -n <nb> --timeout <s>` (0=ok, 2=timeout) | blocks | extended | reliable |
| Download artifact | `notebooklm download <type> ./path [-a <id>] [-n <nb>] [--format ...]` | sync | running-reports, extended | reliable |
| Auto-sync `.md` -> notebook | hook -> `scripts/notebooklm_sync/update.py`; `batch.py [--stale-only]` | hook | upload-back/sync | reliable |
| Sync status / map | `scripts/notebooklm_sync/status.py [--json]` | n/a | sync | reliable |

**Reliable** (per findings): notebooks, sources, chat, mind-map, report, data-table.
**Rate-limited / "may fail"**: audio, video, quiz, flashcards, infographic, slide-deck —
wrap with `--retry N` and a degrade path.

---

## 3. Use-Case Method Designs

### 3.1 SOURCING — NLM notebooks / grounded research -> RF source cards

**Mechanism: `adapter` (primary) + `service-hook` (secondary).**

**Primary — `NotebookLMAdapter` (discovery leg).** New module
`src/research_foundry/adapters/notebooklm.py` implementing the `Adapter` Protocol
(`adapters/base.py:73`): `id="notebooklm"`, `requires=()` (CLI/skill, not a python import,
so use a PATH/auth check in `available()` instead of `module_available`), `available()`,
`run(request)`. Register by adding `"notebooklm"` to `_CONCRETE` in
`adapters/__init__.py:17`. It is then invoked exactly like every other adapter through
`rf swarm run <RUN_ID> --adapters notebooklm` (`cli_commands.py:259-267` loops
`get_adapter(aid).run({"brief": brief, "profile": profile})`).

`run(request)` extracts questions from `brief.questions.primary/secondary` (or
`research_questions`), then:

1. Resolves a notebook id from `request["notebook_id"]` (new optional `--notebook` CLI
   affordance) or, if `add-research` mode, calls
   `notebooklm source add-research "<question>" --mode [fast|deep] --json`.
2. For each question, `notebooklm ask "<q>" --json -n <nb>` -> captures
   `answer` + `references` (citations). For quote-level evidence,
   `notebooklm source fulltext <src> --json`.
3. Maps each NLM reference into a `source_candidates` dict matching the contract
   (`gpt_researcher.py:76-87` shape): `candidate_id`, `title`,
   `source_type="notebook"`, `locator={"url": ...}`, `discovery_method="notebook_knowledge"`,
   `label`, `notes`. Gemini's synthesized `answer` text goes into
   `AdapterResult.artifacts["notebook_synthesis"]` (telemetry only, **never** the report).
4. Returns `AdapterResult(degraded=False, source_candidates=[...], artifacts={...},
   cost_usd=..., tokens=...)`. On missing auth/CLI -> `_degraded()` with notes (mirror
   `gpt_researcher.py:67-101`), never raises, never hits network.

Downstream, `cli_commands.py:266` dumps `source_candidates` -> `rp.source_candidates`, then
`rf ingest <locator> --run <RUN_ID> --source-type notebooklm` turns each into a
`sources/<id>.md` source card.

**Secondary — `source_cards.ingest_source()` branch.** Add a `source_type == "notebooklm"`
branch in `services/source_cards.py::ingest_source()` (around the type dispatch near line
150). When the locator is an NLM source/notebook reference, optionally call
`notebooklm source fulltext <id> --json` to populate `extracted_points`
(`evidence_id/locator/summary/quote`) with real quote-level evidence rather than a
locator-only degrade. Tag every NLM-derived card in front matter with
`trust.reliability_notes: "NotebookLM-grounded; non-reproducible (online)"` and a
`usage.requires_network: true` flag so downstream consumers know reproducibility depends on
NLM availability (offline-first invariant).

NLM commands: `source add-research`, `ask`, `source fulltext`, `source list`.
**Effort: M** — adapter scaffold + degrade fixtures are mechanical; the `extracted_points`
mapping (NLM references -> RF evidence shape) and the `requires_network` flag are the real
work.

### 3.2 RUNNING REPORTS — drive NLM artifact generation from an RF run

**Mechanism: `workflow` (primary) + `service-hook` (artifact persistence).**

New workflow `.claude/workflows/notebooklm-report.js` (authored via the
`workflow-authoring` skill, registered in `.claude/specs/workflows/workflow-registry.md`).
It sits **between `rf synthesize` (stage 7) and `rf verify` (stage 8)** — Opus invokes it
after the report draft exists. Three phases (titles must match `meta.phases` exactly):

- **Prepare** — `codebase-explorer` (Mode A) confirms `reports/report_draft.md` and
  `claims/claim_ledger.yaml` exist; resolves the run's notebook id (creating one via
  `notebooklm create` if absent and the source set is already uploaded — see 3.4).
- **Generate** — `python-backend-engineer` calls
  `notebooklm generate report --format briefing-doc --json -n <nb>` (and/or `mind-map`,
  `data-table`) -> captures `task_id`. Audio/video deferred to the extended-run workflow
  (3.3) because of their latency/rate-limits.
- **Integrate** — after the artifact completes, `notebooklm download report ./... -a <id>`;
  the markdown is attached to the run as a **non-authoritative artifact** (written under
  `runs/<run>/telemetry/` or a new `runs/<run>/nlm_artifacts/` dir), recorded in
  `evidence_bundle.yaml` under a new `artifacts.notebooklm_report` key. It is **not**
  merged into `report_draft.md`; if any of its prose is to be cited, it must first become a
  source card (3.1) and earn a `[claim:<id>]`.

The four hard constraints are honored: no FS/shell in the script body (the
`python-backend-engineer` agent runs `notebooklm`/`rf`), no `Date.now()`/`Math.random()`
(timestamp from `args`), reviewers are edit-less by `agentType`, and any sensitivity
escalation is a workflow boundary (return `{status:'blocked'}`), not a silent skip.

NLM commands: `generate report|mind-map|data-table`, `artifact wait`, `download`.
**Effort: M** — one new workflow + spec + registry row; persistence is additive to the
bundle. Reuses the existing `python-backend-engineer` + budget-guard patterns from
`research-foundry-swarm.js`.

### 3.3 EXTENDED RUNS — async/long generation, polling, batched multi-notebook

**Mechanism: `workflow` with `pipeline()` + subagent background polling.**

New workflow `.claude/workflows/notebooklm-extended.js`. This is the home for the
**long-latency, rate-limited** artifacts (audio 10-20 min, video 15-45 min) and for
**batched multi-notebook** runs woven into a swarm.

Pattern (from `workflow-patterns.md` `pipeline()` + the swarm's background-polling note):

1. **Fan-out generation** — `pipeline(notebooks, ...)` over N notebook ids (one per topic /
   per swarm leg). For each: `notebooklm generate audio "<instr>" --format deep-dive
   --json -n <nb>` -> `task_id`. `pipeline()` has no inter-item barrier, so all kick off
   without blocking each other.
2. **Background poll** — per task, a subagent (where `wait` commands auto-run per the NLM
   autonomy rules) calls `notebooklm artifact wait <task_id> -n <nb> --timeout 2700`
   (exit 0=done, 2=timeout) then `notebooklm download audio ./... -a <task_id> -n <nb>`.
   Budget-guarded: skip generation when `budget.remaining() < 60_000` (audio leg ~ 60K).
3. **Collect** — completed artifacts attach to each leg's run bundle as in 3.2;
   per-notebook results merge back into the parent swarm's manifest.

Multi-notebook safety (findings): always pass explicit full-UUID `-n <NOTEBOOK_ID>` on
every `wait`/`download`/`generate`; never partial ids. Per-agent isolation via
`NOTEBOOKLM_HOME` for concurrent accounts. Rate-limit handling: `--retry N` with backoff,
and on persistent failure degrade the leg (record `status: skipped_rate_limited`) rather
than failing the run.

NLM commands: `generate audio|video|slide-deck|infographic`, `artifact list`,
`artifact wait`, `download`.
**Effort: L** — async polling, multi-notebook orchestration, rate-limit backoff, and
checkpoint/resume (so Opus can resume without re-generating a non-deterministic audio) are
the heaviest pieces. Needs an explicit `nlm_task_id` checkpoint persisted to the run so
re-entry reuses the in-flight artifact instead of regenerating.

### 3.4 UPLOAD-BACK — push RF reports / source cards / verified output -> NLM sources

**Mechanism: `integration` + `writeback` service (primary); `hook-sync` (optional).**

**Primary — `NotebookLMClient` + `writeback` target.** This is the exact mirror of the
ARC/IntentTree outbound seam.

- New `src/research_foundry/integrations/notebooklm.py`: `NotebookLMClient(IntegrationClient)`
  (`integrations/base.py:25`) with `from_config()`, `available()`, and methods
  `create_notebook(title) -> dict|None`, `add_source(notebook_id, locator) -> dict|None`,
  `get_notebook(notebook_id) -> dict|None`. Because NLM has no documented REST API, the
  client **wraps the `notebooklm` CLI** (subprocess `--json`) behind the same
  `available()`-gated, returns-`None`-on-error contract — so the rest of RF treats it like
  any other integration. Add a lazy singleton `get_notebooklm_client()` to
  `integrations/__init__.py`.
- New `_render_notebooklm()` in `services/writeback.py` (mirror `_render_intenttree_update`
  at line 423 / `_render_arc_council` at line 541). It **always** writes the deterministic
  candidate `runs/<run>/writebacks/notebooklm_writeback.yaml` with a `push_status` enum
  `[proposed, pushed, skipped_offline, skipped_requires_review, skipped_no_notebook]`. Live
  push only when `client.available()` AND `profile not in offline profiles` AND NOT
  `requires_review`: `create_notebook(title)` (or reuse the bundle's recorded notebook id),
  then `add_source(nb, <report path>)` + `add_source(nb, <each source card>)`.
- Wire it into `writeback(run, targets=...)` (line 642): add `"notebooklm"` to the targets
  branch checks (alongside the existing `if "intenttree" in targets:` blocks), and surface
  it in the `--targets` help and the `doctor` reachability output.
- `RunPaths` (`paths.py:216`): add a `notebooklm_writeback` property ->
  `self.writebacks / "notebooklm_writeback.yaml"`.
- New schema `schemas/notebooklm_writeback.schema.yaml` (copy
  `schemas/intenttree_update.schema.yaml`): `notebook_id`, `run_id`,
  `evidence_bundle_id`, `pushed_source_ids[]`, `pushed_notebook_id`, `artifact_links`,
  `push_status`.
- **Loop-closing back-reference**: on successful push, `_render_notebooklm()` records the
  notebook id and source mapping into `evidence_bundle.yaml` under
  `lineage.notebooklm_notebook_id` and `lineage.notebooklm_source_ids:
  [{nlm_source_id, rf_source_card_id}]`, so a later run can append to the existing notebook
  rather than creating a new one (and so 3.1 sourcing can detect a self-reference cycle).

**Optional — `hook-sync` (zero-code).** For continuous mirroring of a project's `.md`
corpus, run `python .claude/skills/notebooklm-sync/scripts/install.py --project-name
research-foundry --notebook-title "RF — <project>" --include-dirs runs --root-files ...`.
Thereafter any `Write`/`Edit` of a scoped `.md` (e.g. `report_final.md`) auto-uploads via
the `PostToolUse` hook; `batch.py --stale-only` resyncs. **Caveat (findings):** the current
`state.json` still has `project_slug: skillmeat`; the install/`init.py` step must be re-run
with `--force` so the mapping and config point at RF, not the copied SkillMeat defaults.

**Governance** (both paths): register `notebooklm` in `config/governance.yaml`
`writeback_targets` with `permitted_profiles: [personal, work_approved, client_approved]`
and `requires_review_for: [work_sensitive, client_sensitive]`, and add a policy rule
`notebooklm_writeback_requires_review` (condition: `writeback.target contains notebooklm AND
source.sensitivity in [work_sensitive, client_sensitive]`), exactly mirroring the existing
`intenttree_writeback_requires_review` / `arc_writeback_requires_review` rules at
governance.yaml lines 78-85. `writeback()` already computes
`requires_review = require_review or sensitivity in _WORK_SENSITIVITIES` (line 670), so the
hook-sync auto-upload of a `work_sensitive` report must be **excluded from sync scope** (do
not add work-sensitive run dirs to `--include-dirs`) since the silent hook bypasses the
review gate.

NLM commands: `create`, `source add`, `source wait`; sync `install.py`, `batch.py`,
`status.py`, `update.py`.
**Effort: L** — client + writeback target + schema + governance + bundle lineage fields +
the sync state-file re-init. Largest blast radius because it touches `writeback.py`,
`governance.yaml`, `paths.py`, and the bundle schema.

---

## Notebook Correlation

The implemented integration resolves *which* notebook a given run, project, or file maps to
through a single deterministic service —
`src/research_foundry/services/notebook_correlation.py` — backed by an on-disk registry. All
three seams (sourcing, upload-back, sync) call into this one resolver rather than each
inventing its own mapping, so there is exactly one source of truth for the run↔notebook link
and the cycle semantics are unambiguous.

### Correlation modes

`correlation_mode(*, paths=None) -> str` reads
`foundry.yaml` → `integrations.notebooklm.correlation_mode` and returns one of three modes
(default `"project"`):

| Mode | Meaning | When the notebook is shared |
|------|---------|-----------------------------|
| `project` (default) | All runs under a project slug resolve to **one shared notebook** — the project's persistent knowledge base. | Across every run of the project. |
| `run` | Each run gets (or creates) its **own** notebook, isolated from sibling runs. | Never shared; one notebook per run. |
| `explicit` | The caller supplies the notebook id directly (`--notebook-id` / `notebook_id=` argument); no slug-based inference. | Wherever the caller points it. |

The mode can be overridden per-invocation by the `mode=` argument to `resolve_notebook(...)`
or the `--notebook-mode project|run|explicit` CLI flag; absent an override, the
config default applies.

### Resolver API (canonical)

`src/research_foundry/services/notebook_correlation.py` exports:

- `resolve_notebook(run_id, *, project=None, mode=None, create=False, client=None, paths=None) -> dict | None`
  — the central entry point. Returns
  `{notebook_id, notebook_title, project, run_id, mode}` (or `None` when no notebook can be
  resolved and `create=False`, or when offline and creation was requested). When
  `create=True` and a notebook is needed, it uses the supplied/lazily-fetched
  `NotebookLMClient` to `create_notebook(title)` behind the same `available()` gate; if the
  client is unavailable it degrades to `None` rather than raising.
- `record_run_notebook(run_id, notebook_id, *, project=None, notebook_title=None, paths=None) -> None`
  — persists a run↔notebook binding (and the project↔notebook binding in `project` mode) into
  the registry. Used after a successful resolve/create so subsequent runs reuse the notebook.
- `notebook_for_run(run_id, *, paths=None) -> str | None`
  — fast read-only lookup of a previously-recorded notebook id for a run (no creation, no
  network).
- `notebook_for_path(file_path, *, paths=None) -> str | None`
  — maps any path under `runs/<run_id>/...` to that run's resolved notebook by parsing the
  `run_id` out of the path, then delegating to `notebook_for_run`. This is the hook the
  sync layer uses to answer "what notebook does *this file* belong to?".
- `correlation_mode(*, paths=None) -> str`
  — returns the configured mode (default `"project"`).

### Registry shape

The correlation registry lives at `registries/notebooklm/notebooks.yaml`
(written/read via `yamlio.dump_yaml`/`load_yaml`, so ordering is deterministic; created
lazily on first write). Its shape:

```yaml
projects:
  <slug>:
    notebook_id: <nlm-notebook-uuid>
    notebook_title: "RF — <slug>"
    runs:
      - <run_id>
      - <run_id>
runs:
  <run_id>:
    notebook_id: <nlm-notebook-uuid>
    notebook_title: "RF — <slug>"
    project: <slug>
    created_at: <iso8601>
```

The `projects` block holds the shared-notebook bindings (project mode) and the membership
list of runs; the `runs` block holds the per-run resolution record (including `run` and
`explicit` mode bindings, which have no project-level shared notebook).

### Config

`foundry.yaml` → `integrations.notebooklm`:

```yaml
integrations:
  notebooklm:
    correlation_mode: project              # project | run | explicit
    notebook_title_template: "RF — {project}"
    base_url: null                          # null → CLI-backed client (no HTTP base)
```

`notebook_title_template` is interpolated with the project slug to title freshly-created
notebooks. `base_url: null` signals the CLI-backed client path (NLM has no public REST API);
see Open Question 1 resolution below.

### How the three seams resolve through correlation

- **Sourcing** (`adapters/notebooklm.py`, `NotebookLMAdapter`): the adapter calls
  `resolve_notebook(run_id, project=..., mode=..., create=...)` to find the notebook to
  query (`ask` / `source fulltext`), so discovery reads from the *same* notebook the run is
  bound to. In `project` mode that is the shared project knowledge base; cross-run
  accumulation is the intended behavior.
- **Upload-back** (`services/writeback.py`, `_render_notebooklm_update`): the writeback
  target resolves the run's notebook (creating it on first push when permitted), then
  `add_source`s the report/source cards into it and `record_run_notebook(...)`s the binding.
  Because both sourcing and upload-back resolve the *same* notebook in project mode, the
  "source from Y then write to Y" path is a deliberate **append to the shared knowledge
  base**, not a self-citation hazard (the claim ledger still gates which NLM prose may enter
  a report body — correlation only governs notebook identity).
- **Sync** (`notebooklm-sync` hook + `rf notebooklm sync`): the hook/CLI uses
  `notebook_for_path(file_path)` to route a written `.md` under `runs/<run_id>/` to that
  run's resolved notebook, so auto-mirrored files land in the correct notebook without a
  separate `{project}-sources.json` mapping drifting out of sync.

### Implemented surface

The following real files/identifiers ship in this integration (offline; live-unvalidated —
see §6 and the memory note):

- **Correlation service** — `src/research_foundry/services/notebook_correlation.py`
  (`resolve_notebook`, `record_run_notebook`, `notebook_for_run`, `notebook_for_path`,
  `correlation_mode`), registry at `registries/notebooklm/notebooks.yaml`.
- **Integration client** — `src/research_foundry/integrations/notebooklm.py`,
  `class NotebookLMClient(IntegrationClient)` with `from_config() -> NotebookLMClient`,
  `available(timeout=2.0) -> bool`, `create_notebook(title) -> dict | None`,
  `add_source(notebook_id, locator, *, title=None) -> dict | None`,
  `get_notebook(notebook_id) -> dict | None`; lazy singleton
  `get_notebooklm_client() -> NotebookLMClient` in `integrations/__init__.py`.
- **Adapter** — `src/research_foundry/adapters/notebooklm.py`,
  `class NotebookLMAdapter` (`id="notebooklm"`, `requires=()`), registered by adding
  `"notebooklm"` to `_CONCRETE` in `adapters/__init__.py`.
- **Writeback target** — `_render_notebooklm_update(...)` in `services/writeback.py`;
  `RunPaths.notebooklm_update -> writebacks/notebooklm_update.yaml`;
  `WritebackResult.notebooklm_update_path: Path | None`; schema
  `schemas/notebooklm_update.schema.yaml`; `push_status` enum
  `proposed | pushed | skipped_offline | skipped_requires_review | skipped_no_notebook`.
- **Governance rule** — `governance.yaml` → `writeback_targets.notebooklm`
  (`permitted_profiles: [personal, work_approved, client_approved]`,
  `requires_review_for: [work_sensitive, client_sensitive]`) and policy rule id
  `notebooklm_writeback_requires_review` (mirrors `arc_writeback_requires_review`).
- **Intake** — `intake_from_notebooklm(notebook_id, *, project=None, paths=None)` in
  `services/intake.py`; CLI `rf intake notebooklm <notebook_id>`.
- **CLI** — `rf swarm run --project <slug> [--notebook-mode project|run|explicit] [--notebook-id <id>]`;
  `rf writeback --targets notebooklm`; `rf notebooklm resolve|status|sync` subcommands.
- **Configurable sync** — `rf notebooklm sync` resolves through
  `notebook_for_path`/`notebook_for_run` so the auto-mirror honors the correlation mode.
- **Three workflows** — `.claude/workflows/notebooklm-sourcing.js`,
  `.claude/workflows/notebooklm-report.js`, `.claude/workflows/notebooklm-extended.js`.

---

## 4. Phased Implementation Plan (additive-first)

Each phase is shippable and reversible; nothing before Phase 4 touches the core
`rf synthesize`/`verify`/`writeback` flow.

**Phase 0 — Design + fixtures + sync re-init (this doc).**
Land this plan. Re-run `notebooklm-sync` `install.py --force` so `state.json` /
`{project}-sources.json` reference `research-foundry`, not the inherited SkillMeat slug.
Add degrade fixtures (stub NLM responses) for CI. No core code touched. **Effort: S.**

**Phase 1 — Workflows first (no `src/` changes).**
Author `notebooklm-report.js` (3.2) and `notebooklm-extended.js` (3.3) under
`.claude/workflows/`, with per-workflow specs and registry rows. These call existing
`notebooklm` skill commands via agents and persist artifacts beside the run — they exercise
the integration end-to-end without modifying the Python pipeline. Validate against the
four-constraints + durability checklists; dry-run with `args.dry_run=true`. **Effort: M.**

**Phase 2 — Sourcing adapter (`adapters/`).**
Add `adapters/notebooklm.py` + register in `_CONCRETE`; add the optional `--notebook` CLI
affordance to `rf swarm run`. Adapter is purely additive (opt-in via `--adapters
notebooklm`) and degrades when offline. Add the `source_type=="notebooklm"` enrichment
branch in `source_cards.ingest_source()`. **Effort: M.**

**Phase 3 — Upload-back integration (`integrations/` + `writeback`).**
Add `integrations/notebooklm.py` (`NotebookLMClient`), `_render_notebooklm()` in
`writeback.py`, the `notebooklm` target wiring, `schemas/notebooklm_writeback.schema.yaml`,
`RunPaths.notebooklm_writeback`, the `governance.yaml` target + policy rule, and the
`evidence_bundle.yaml` `lineage.notebooklm_*` fields. This is the first phase that edits the
core writeback flow — gated entirely behind `--targets notebooklm` and `available()`, so the
default `rf writeback` behavior is unchanged. **Effort: L.**

**Phase 4 — Inbound intake (optional, symmetric with IntentTree).**
Add `rf intake notebooklm <notebook_id>` (copy the `intake_from_intenttree` pattern in
`services/intake.py:220`) for pulling an existing notebook's sources/synthesis into RF as a
new captured idea, with `intenttree_node_ref`-style back-link to the notebook. Only build
this if a real "notebook-as-inbox" need appears. **Effort: M.**

**Phase 5 — Live validation + memory note.**
First real NLM-authenticated run end-to-end; record reachability in `doctor`; update the
memory note (alongside the existing "ARC/IntentTree integrations untested live" entry) that
NLM CLI shapes were validated against a live session. **Effort: S.**

Recommended order: **0 -> 1 -> 2 -> 3 -> 4 -> 5** (workflows before core edits; sourcing
before upload-back so the back-reference cycle in 3.4 is already detectable).

---

## 5. Governance & Claim-Ledger Notes

1. **Claim authority is unchanged.** Every material claim in an RF report still resolves to
   a `claim_id` in `claims/claim_ledger.yaml` or carries `**Inference:**`/`**Speculation:**`
   (verifier exit code 4). NLM-generated prose enters the ledger **only** through a source
   card (3.1) — it cannot be pasted into `report_draft.md` directly. `synthesis.py`'s
   "LLM path may not introduce untagged material claims" guard covers the adapter route.
2. **NLM output is non-reproducible.** All NLM-derived source cards carry
   `usage.requires_network: true` and a reliability note; this signals downstream consumers
   (and any re-run) that determinism is conditional on NLM availability — preserving the
   offline-first invariant by making the exception explicit rather than silent.
3. **Sensitivity gates the upload.** `work_sensitive`/`client_sensitive` runs set
   `requires_review` and never auto-upload; the `notebooklm_writeback.yaml` candidate is
   written with `push_status: skipped_requires_review`. The silent `notebooklm-sync` hook
   must **not** be scoped over work-sensitive run dirs, because it bypasses the review gate.
4. **Cost attribution.** NLM `ask`/`generate` costs are metered into the adapter's
   `AdapterResult.cost_usd`/`tokens` and the run's `ccdash_event` cost field, same as other
   adapters.
5. **Fail-soft everywhere.** Every NLM call (adapter, client, workflow agent) wraps in the
   degrade-or-`None` pattern; a missing session or rate-limit never fails the RF pipeline —
   it leaves the deterministic candidate/source as the source of truth.

---

## 6. Open Questions

1. **No documented NLM REST API.** ✅ **Resolved.** `NotebookLMClient` subclasses
   `IntegrationClient` and **overrides** the HTTP-shaped methods to wrap the `notebooklm`
   CLI as a `--json` subprocess (with `base_url: null` in config), keeping the same
   `available()`-gated, returns-`None`-on-error contract. No separate CLI-backed base class
   was needed — the subclass override absorbs the shape difference, so the rest of RF treats
   it like any other integration client.
2. **Quote-level extraction fidelity.** Does `notebooklm source fulltext --json` yield
   quote spans good enough to populate `extracted_points[].quote`, or only summaries? This
   gates whether 3.1 produces real evidence or locator-only degrades.
3. **Auth bridge — ⏳ remaining (the only blocker to "live-validated").** The skill uses a
   persistent Playwright profile + injected `state.json` cookies; the CLI uses
   `NOTEBOOKLM_HOME`/`NOTEBOOKLM_AUTH_JSON`. The build environment has **no NLM auth**, so
   the entire integration is implemented and tested **offline only** — the
   `notebooklm` CLI command shapes are inferred from `.claude/skills/notebooklm/SKILL.md`,
   exactly as the ARC/IntentTree clients were inferred from their skill docs. The remaining
   validation step is a single first live run: `notebooklm login` out-of-band, then a real
   `rf swarm run`/`rf writeback --targets notebooklm`/`rf notebooklm resolve` against an
   authenticated session, adjusting the client subprocess shapes if the live CLI output
   differs. Document the session as a precondition like ARC/IntentTree reachability. See the
   memory note `notebooklm-integration-offline`.
4. **Reproducibility of non-deterministic artifacts.** Workflow constraint 4 forbids
   `Math.random()`, but audio/video gen is inherently non-deterministic. The
   `notebooklm-extended.js` checkpoint must persist `nlm_task_id` so resume reuses the
   in-flight artifact — confirm `artifact wait`/`download` can re-attach to a prior task id
   after a workflow restart.
5. **Bidirectional cycle semantics.** ✅ **Resolved by Notebook Correlation.** In the
   default `project` correlation mode the run's notebook *is* the shared project knowledge
   base: sourcing and upload-back both resolve the **same** notebook through
   `resolve_notebook(...)`, so "source from Y then write to Y" is a deliberate **append** to
   that shared base. There is no self-citation hazard because the claim ledger — not the
   notebook — gates which NLM prose may enter a report body; correlation only governs
   notebook identity. (`run` mode isolates per run; `explicit` mode hands identity to the
   caller.)
6. **Sync state hygiene.** `state.json` currently says `project_slug: skillmeat`. Confirm
   `install.py --force --update` cleanly re-points the mapping, and that RF dev envs have
   `jq` on PATH (the `notebooklm-sync-hook.sh` requires it).
7. **Workflow nesting.** Master contract allows one level of nesting; should
   `notebooklm-report`/`notebooklm-extended` be standalone workflows invoked via
   `workflow()` from swarm/council, or inlined embedded patterns? Affects budget accounting.
8. **Execution-Report schema fit.** The NLM research workflows don't map cleanly onto the
   standard `waves/phases/tasks` `ExecutionReport` shape (same gap as
   `research-foundry-swarm.js`'s custom return). Reuse the swarm's custom-return precedent or
   extend the schema?

**Resolution status:** OQ1 (CLI-backed client = `IntegrationClient` subclass override) and
OQ5 (cycle semantics — the project notebook is the shared knowledge base, resolved via
Notebook Correlation) are **resolved**. OQ3 (**live auth validation**) is the **only**
remaining step before this integration can be marked live-validated; the rest of the surface
ships offline and degrades fail-soft. OQ2/OQ4/OQ6/OQ7/OQ8 are implementation-detail
refinements that the offline build already takes a default position on and that a live run
will confirm or tune.
