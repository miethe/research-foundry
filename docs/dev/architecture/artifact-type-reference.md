---
title: "Research Foundry — Artifact Type Reference"
description: "Complete reference for RF's artifact types — research-pipeline artifacts (YAML-schema-backed and DB-backed) plus the planning/doc artifacts used across the repo — with detection signals and usage patterns."
audience: [ai-agents, developers]
created: 2026-07-10
status: published
category: architecture
doc_type: architecture
related_documents:
  - docs/projects/research-foundry/SERVICE_CONTRACT.md
  - docs/project_plans/exploration/web-app-platform-evolution/current-state-and-direction.md
  - docs/project_plans/exploration/web-app-platform-evolution/discovery/01-cli-core.md
  - .claude/skills/artifact-tracking/schemas/SCHEMAS-INDEX.md
  - .claude/skills/artifact-tracking/schemas/field-reference.md
---

# Research Foundry — Artifact Type Reference

This is the reference `CLAUDE.md` has pointed to as
`docs/dev/architecture/artifact-type-reference.md` since the project's early days; the file did
not previously exist (a dangling pointer, flagged in
`docs/project_plans/exploration/web-app-platform-evolution/discovery/05-docs-intent.md` §6.3). It
fills that gap.

Research Foundry has two distinct artifact families that agents and developers should not
conflate:

1. **Research artifacts** — the pipeline's own domain objects (raw ideas, source cards, claims,
   evidence bundles, reports, telemetry, writebacks). Most are validated against JSON Schemas in
   the top-level `schemas/*.schema.yaml` directory via `research_foundry.schemas.validate()`.
   Some newer platform surfaces are DB-backed with no YAML schema counterpart (§3).
2. **Planning/doc artifacts** — the CCDash-aligned Markdown docs used to plan and track work on RF
   *itself* (PRDs, implementation plans, SPIKEs, progress files). These reuse the shared
   `artifact-tracking` schema set that ships with this repo's `.claude/` config; this doc does not
   redefine them, only indexes where to find them (§4).

## 1. Research artifacts — core pipeline (YAML-schema-backed)

Every artifact below is validated against `schemas/<name>.schema.yaml` via
`research_foundry.schemas.validate(obj, "<schema_name>")` at write time (`rf schema validate|list`
lets you check any instance by hand). Paths are relative to a run directory
(`runs/<run_id>/...`) unless noted otherwise.

| Artifact | What it is | Where it lives | Detection signal | Usage pattern |
|---|---|---|---|---|
| **raw_idea** | A captured idea prior to triage — the pipeline's entry point. | `inbox/raw_ideas/raw_*.md` (workspace-level, not per-run). | Filename prefix `raw_` + frontmatter `type: raw_idea` (schema: `schemas/raw_idea.schema.yaml`). | Produced by `rf capture`. Consumed by `rf triage` (→ `research_intent` + `ibom` + `intenttree_node`); the idea's `triage.status` flips to `converted_to_intent` in place. |
| **research_intent** / **ibom** | The intent (objective, governance, research questions) and its I-BOM (tool/model policy, security boundaries) derived from a triaged idea. | `intents/active/<intent_id>.yaml`, `iboms/active/<ibom_id>.yaml`. | Frontmatter `type: research_intent` / `type: ibom`; schemas `research_intent.schema.yaml`, `ibom.schema.yaml`. | Produced by `rf triage`. `rf plan` reads the intent (+ linked ibom) to seed a run's model profiles and governance. |
| **source_candidate(s)** | Unranked/ranked candidate sources discovered before ingestion — the pre-source-card stage. | `runs/<run>/source_candidates.yaml` (written by `rf swarm run`, aggregating adapter `AdapterResult.source_candidates`); also transiently returned as `normalized_results[]` inside the **search_run** record (`runs/<run>/search_run.yaml`) produced by `rf search`. | Top-level key `source_candidates:` (list); no dedicated JSON Schema — candidates are a loosely-typed dict list (`{url, title, provider, ...}`) until promoted. | Feeds `rf ingest`/`rf source-card create`, which converts an accepted candidate's locator into a schema-valid `source_card`. Discovery agents (`rf_source_scout`, `rf_domain_researcher`) rank candidates for the discovery lead; nothing here is claim-bearing yet. |
| **source_card** | A normalized, schema-valid record of one evidence source (provenance, trust, sensitivity, extracted points). | `runs/<run>/sources/src_*.md` (Markdown + YAML frontmatter). | Frontmatter `type: source_card`; schema `schemas/source_card.schema.yaml`. | Produced by `rf ingest` / `rf source-card create` / `rf fetch` (Search Router). Consumed by `rf extract`, which turns `extracted_points[]` into extraction-card facts. Sensitivity + `usage.*` flags gate which writeback targets may cite it (checked by `rf verify`'s sensitivity-leak check). |
| **extraction_card** | Deterministic per-source extraction of facts + contradictions/cautions. | `runs/<run>/extractions/ext_*.yaml`. | Frontmatter `type: extraction_card`; schema `schemas/extraction_card.schema.yaml`. | Produced by `rf extract` from a source card. Consumed by `rf claim-map`, which maps each extracted fact to one claim ledger entry. |
| **claim-ledger entry** | A single claim (text, `claim_type`, `materiality`, `status`, source links, `inference_basis` when applicable) inside the run's claim ledger — the pipeline's ground truth. | `runs/<run>/claims/claim_ledger.yaml` (`claims[]`); companion logs `contradiction_log.yaml`, `inference_log.yaml`. | `claim_id` matching `clm_\d+`; ledger frontmatter `verification_status`; schema `schemas/claim_ledger.schema.yaml`. | Built by `rf claim-map` (always `status: supported`, backed by an extraction). Cited by `[claim:<id>]` tags in a report body. `rf synthesize` may cite ONLY ids already in the ledger; `rf verify` is the authority that checks every citation resolves and every material sentence is tagged. |
| **evidence bundle** | The single durable artifact for a run — report + claim ledger + counts + governance + lineage, optionally gated on verification. | `runs/<run>/evidence_bundle.yaml`. | Frontmatter `type: evidence_bundle` (or top-level `id`/`status` fields); schema `schemas/evidence_bundle.schema.yaml`; `status` ∈ `draft\|verified\|published\|archived`. | Produced by `rf bundle` (optionally with `--verify`). Per the README: "the durable asset is the evidence bundle... the swarm that produced it is disposable and rerunnable." Consumed by `rf writeback`, `rf catalog import`, and `rf run export` (the runs-viewer data source). |
| **report / report-draft** | The synthesized research report — deterministic body by default (Findings/Inferences/Speculation/Open questions/Sources, each material sentence tagged `[claim:<id>]`). | `runs/<run>/reports/report_draft.md` (or `report_final.md`); frontmatter validated against `schemas/report_frontmatter.schema.yaml`. **Report Builder** drafts are a distinct, DB-adjacent variant — `<workspace>/reports/drafts/<report_draft_id>/draft.yaml`, schema `schemas/report_draft.schema.yaml`. | Markdown frontmatter `type: research_report`; Builder drafts: frontmatter `type: report_draft` + `report_draft_id`. | Produced by `rf synthesize` (deterministic; `--llm` only appends a note, never changes the body — `services/synthesis.py:210-220`) or authored incrementally via `rf report draft create/add-block/...` (Report Builder, `SERVICE_CONTRACT.md` §16). `rf verify` / `rf report draft verify` are the gate before either variant may publish. |
| **run trace / telemetry** | Best-effort append-only event log for every pipeline stage, plus token-cost and tool-call rollups. | `runs/<run>/telemetry/run_trace.jsonl`, `telemetry/token_costs.yaml`, `telemetry/tool_calls.yaml`. | JSONL lines with a `stage` key; schema-free (never blocks the pipeline on a trace-write error). | Appended by every service stage via `append_jsonl`. Aggregated by `rf ccdash summarize` into `ccdash/daily/<date>.yaml` + summary rollups — the only consumer that turns raw trace lines into a report. |
| **writeback event** (meatywiki / skillmeat / ccdash / intenttree / arc / notebooklm) | A rendered candidate (or, for live targets, an actually-pushed record) for one downstream system. | `runs/<run>/writebacks/<target>_writeback.{md,yaml}` + a workspace-level mirror: `meatywiki/sources/<slug>.md`, `skillmeat/skillboms/<id>.md`, `ccdash/events/<event_id>.yaml`, plus opt-in `intenttree_update.yaml` / `arc_review_request.yaml` / `notebooklm_update.yaml`. | Filename pattern `<target>_writeback.*`/`<target>_update.yaml`; each has its own schema (`ccdash_event.schema.yaml`, `meatywiki_writeback.schema.yaml`, `skillbom_candidate.schema.yaml`, `intenttree_update.schema.yaml`, `arc_review_request.schema.yaml`, `notebooklm_update.schema.yaml`). | Produced by `rf writeback --targets ...`. MeatyWiki/SkillMeat/CCDash are **file-mirror, always-write, proven live**; IntentTree/ARC/NotebookLM are **opt-in, always write the candidate, but the live push has never been exercised from this repo** (verified via disk search across 41 run dirs — see `current-state-and-direction.md` §4). |

## 2. Research artifacts — supporting / routing types

These round out the pipeline but are not claim-bearing themselves:

| Artifact | What it is | Where it lives | Schema |
|---|---|---|---|
| `research_brief` | The planning brief a run is executed against (questions, depth, audience, budget). | `runs/<run>/research_brief.md` | `schemas/research_brief.schema.yaml` |
| `swarm_plan` | Agent roster + model profiles + budget for a run's swarm. | `runs/<run>/swarm_plan.yaml` | `schemas/swarm_plan.schema.yaml` |
| `routing_decision` | Selected posture chain, tools, validation, writebacks, human-required flag for a run. | `runs/<run>/routing_decision.yaml` | `schemas/routing_decision.schema.yaml` |
| `search_run` | The Search Router's own run record (request, provider chain, normalized results). | `runs/<run>/search_run.yaml` | `schemas/search_run.schema.yaml` |
| `search_request` | Validated input to `rf search`/`rf fetch`/`rf-mcp`. | in-memory / embedded in `search_run.request` | `schemas/search_request.schema.yaml` |
| `intenttree_node` | The IntentTree L4 node created for a triaged intent. | `intenttree/nodes/<node_id>.yaml` | `schemas/intenttree_node.schema.yaml` |
| `review_packet` (council review) | Deterministic council verdicts (approve/concern/block per role). | `runs/<run>/reviews/council_review.yaml`; `reviews/verification.yaml` is the sibling verifier output (schema-free). | `schemas/review_packet.schema.yaml` |
| `foundry` config | The workspace's own `foundry.yaml` (governance, auth, agents, viewer config). | `<workspace>/foundry.yaml` | `schemas/foundry.schema.yaml` |
| `tool_profile` / `research_idea_backlog` | Named model-routing profiles; the backlog of raw-idea → run lifecycle links. | `config/model_profiles.yaml`; workspace-level backlog file | `schemas/tool_profile.schema.yaml`, `schemas/research_idea_backlog.schema.yaml` |

## 3. Platform artifacts — DB-backed, no YAML schema counterpart

These are newer (public-multiuser-release-era) platform types that live in `catalog.db`/service
state rather than as standalone on-disk YAML instances. They are real artifact types agents will
encounter via the HTTP API or CLI, but they have no `schemas/*.schema.yaml` file to validate
against — their shape is defined by the owning service's dataclasses/Pydantic models instead. Full
signatures: `docs/projects/research-foundry/SERVICE_CONTRACT.md` §14-19.

| Artifact | What it is | Where it lives | Detection signal | Usage pattern |
|---|---|---|---|---|
| **draft** (Report Builder, DB-index dual) | A Report Builder draft's authoritative state is the `draft.yaml` file (§1 table); `catalog.db`'s `catalog_report_drafts` table is a **derived, rebuildable index only** — never the source of truth. | File: `<workspace>/reports/drafts/<id>/draft.yaml`. Index: `catalog.db`. | `report_draft_id` matching the file-canonical id. | Mutated via `services/builder_service.py` (`create_draft`, `add_block`, `add_claim_link`, ...); read via `rf catalog search`/`GET /api/catalog/*` for the derived view. |
| **agent_job** | A launched (or launchable) agent research job — subprocess-spawning, credential-isolated, flag-gated (`agents.enabled=false` default). | In-memory/DB state managed by `AgentJobService`; staged artifacts under a job-scoped directory until `accept`ed. | `job_id`; `POST /api/agent-jobs` response body. | Launched via `rf agent-job launch` or `POST /api/agent-jobs` (guard-checked before subprocess spawn). Staged output only becomes durable via `rf agent-job accept` / `POST /agent-jobs/{id}/accept`. |
| **catalog_item** | One row in the evidence catalog's SQLite+FTS5 derived read model (a claim, inference, source, report summary, reusable output, or writeback record). | `catalog.db` (rebuildable via `rf catalog rebuild`; never canonical). | `item_id` (`_make_item_id(item_type, run_id, local_ref)`); `item_type`. | Populated by `rf catalog import`; queried by `rf catalog search/show/stats`; sensitivity-gated fail-closed at read time. |
| **audit_log** (event) | A record of a governed mutation (Report Builder write, catalog import, workspace migration, agent job) for after-the-fact review. | `catalog.db` `audit_event` table. | `audit_event_id` (UUID4); `mutation_type`. | Written fail-open by `record_event()` as a side effect of the mutation it audits (never itself the primary write path). Read via `rf audit list/show/health` or `GET /api/audit*` (RBAC-gated). |
| **workspace** | A tenant boundary — today, one filesystem root per deployment; row-level `workspace_id` scoping exists (WKSP-304) but is advisory-by-default and not yet a true shared multi-tenant store. | `foundry.yaml: workspace.*` config + `workspace_id` columns on scoped tables/files once migrated. | `workspace_id` string. | Backfilled/rolled back via `rf workspace migrate-dry-run|migrate|rollback` (`SERVICE_CONTRACT.md` §18). Enforcement toggle: `resolve_workspace_isolation_enforced()`. |
| **auth identity** | The resolved `{user_id, workspace_id, roles}` for an authenticated request. | Resolved per-request by `AuthProviderMiddleware`; not persisted as a file. | `request.state.identity`; providers: `none`/`local_static`/`clerk` (`oidc` recognized in vocab, not implemented). | Read by `require_role()` (RBAC gate) and threaded into workspace-scoped service calls (`identity=` kwarg on `builder_service`/`catalog_service` functions). |

## 4. Planning/doc artifacts (reference only — schemas live in `artifact-tracking`)

These are the Markdown planning documents used to run RF's *own* development, not RF's research
domain objects. They are **not redefined here** — the artifact-tracking skill owns their schemas
and field semantics:

- **Schema files**: `.claude/skills/artifact-tracking/schemas/*.schema.yaml`
  (`prd.schema.yaml`, `implementation-plan.schema.yaml`, `phase-plan.schema.yaml`,
  `spike.schema.yaml`, `report.schema.yaml`, `feature-contract.schema.yaml`,
  `meta-plan.schema.yaml`, `quick-feature.schema.yaml`, `progress.schema.yaml`,
  `context.schema.yaml`, `design-spec.schema.yaml`, `bug-fix.schema.yaml`,
  `observation.schema.yaml`, `envelope.schema.yaml`).
- **Field-level reference**: `.claude/skills/artifact-tracking/schemas/field-reference.md`
  (per-`doc_type` required/optional field tables, e.g. `prd`, `implementation_plan`,
  `phase_plan`, `spike`, `quick_feature`, `report`, `feature_contract`, `human_brief`).
- **Index**: `.claude/skills/artifact-tracking/schemas/SCHEMAS-INDEX.md`.

| Type (`doc_type`) | Canonical location in this repo |
|---|---|
| `prd` | `docs/project_plans/PRDs/**` |
| `implementation_plan` | `docs/project_plans/implementation_plans/**` |
| `phase_plan` | `.claude/progress/[prd]/phase-N-progress.md` (one per phase) |
| `spike` | `docs/project_plans/SPIKEs/**` |
| `report` (investigation/status) | `docs/project_plans/exploration/**`, `docs/dev/architecture/**` (this doc's own siblings), or the `report` schema's generic location |
| `design_spec` | `docs/project_plans/design-specs/**` |
| `meta_plan` | used for cross-feature/epic-level plans; see `meta-plan.schema.yaml` |
| `feature_contract` | `docs/project_plans/feature_contracts/[category]/[feature-slug].md` (Tier 1, 3-8 pts) |
| `exploration_charter` | `docs/project_plans/exploration/**` (SPIKE-adjacent charter documents, e.g. this doc's own source legs under `web-app-platform-evolution/`) |
| `progress` | `.claude/progress/[prd]/phase-N-progress.md` — same file family as `phase_plan`; the `progress.schema.yaml` schema governs the status/task-tracking fields specifically |

**One rule that applies to all of these and does not apply to §1-3 above**: per this repo's
`CLAUDE.md` Documentation Policy, there is exactly **ONE** progress file per phase and **ONE**
context/worknotes file per PRD — do not create a second file for a status update; update the
existing one via the artifact-tracking CLI scripts
(`.claude/skills/artifact-tracking/scripts/update-status.py`).

## 5. How to use this doc

- **Validating an instance by hand**: `rf schema validate <path> [--schema <name>]` infers the
  schema name from `type`/filename when `--schema` is omitted (`cli/__init__.py:92`).
- **Listing all known schemas**: `rf schema list`.
- **Grounding a claim about maturity**: cross-reference the capability maturity map in
  `docs/project_plans/exploration/web-app-platform-evolution/current-state-and-direction.md` §2
  before asserting that any artifact type's producing pipeline is "live" — several of the
  writeback/bidirectional types in §1's last row are implemented but unexercised against a real
  remote system from this repo.
