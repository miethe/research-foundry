---
schema_version: 2
doc_type: spike
report_category: feasibility
title: "Runs Frontend — Technical Leg: Run Entity Model + Read-Path Feasibility"
status: completed
created: 2026-06-19
completed_date: 2026-06-19
feature_slug: runs-frontend
leg: tech
exploration_charter_ref: docs/project_plans/exploration/runs-frontend/runs-frontend-charter.md
verdict: feasible-with-constraints
verdict_confidence: 0.82
---

# Tech Leg — Run Entity Model + Read-Path Feasibility (CORE)

## Executive Summary

The complete RF run entity model **is derivable deterministically** from on-disk artifacts. Every entity is authored as JSON Schema (Draft 2020-12) under `schemas/*.schema.yaml` — the literal source of truth — and materializes as Markdown/YAML/JSONL files under `runs/rf_run_*/`. The package's `RunPaths` dataclass (`src/research_foundry/paths.py:129-214`) is a machine-readable manifest of every file a run can contain. A faithful read-only viewer is feasible **without** any always-on backend service and **without** any LLM on the recall path. The recommended read path is a **build-time static export** (a thin `rf run export --json` command that walks `RunPaths` + reads YAML/Markdown) feeding a static SPA, with an optional loopback dev API for live browsing. The one constraint: **no machine-readable run-aggregate export contract exists today** — it must be authored. That is small, deterministic, no-LLM glue code, so the charter deal-killer does **not** fire.

**Verdict: `feasible-with-constraints`** — the constraint is "author a deterministic `rf run export --json` (or equivalent file-walk) first."

---

## Evidence Base (what was inspected)

- Schema registry + the canonical schema set: `src/research_foundry/schemas.py`, `schemas/` (20 schemas).
- Per-run path manifest: `src/research_foundry/paths.py` (`FoundryPaths` + `RunPaths` + `RunPaths` properties).
- A real, representative run end-to-end: `runs/rf_run_20260613_what_is_the_minimum_viable_architecture/` (all files opened).
- Corpus shape across all 40+ runs: 779 `.md`, 776 `.yaml`, 42 `.jsonl` (`runs/`).
- CLI surface (Typer): `src/research_foundry/cli.py`, `src/research_foundry/cli_commands.py` (every `@app.command`/`add_typer` enumerated).
- Governance/secret-scan hooks: `src/research_foundry/validators/scan_artifact.py`, `services/governance.py`.
- Upstream entities: `inbox/raw_ideas/raw_*.md`, `intents/active/intent_*.yaml`, `iboms/active/ibom_*.yaml`.
- Prior-art stack: `website/mkdocs.yml` (MkDocs Material).

---

## Run Directory Layout (ground truth)

From `RunPaths` (`paths.py:129-214`) and a real run on disk:

```
runs/rf_run_<date>_<slug>/
├── run.yaml                     # run header / profile / lineage ids
├── routing_decision.yaml        # abstraction level, posture chain, tools, planned writebacks
├── research_brief.md            # MD + YAML frontmatter (questions, source strategy)
├── swarm_plan.yaml              # agent roster, budget, required_outputs
├── source_candidates.yaml       # (DECLARED in RunPaths + required_outputs; OPTIONAL on disk — absent in tailed runs)
├── sources/                     # source_card_*.md  (1..N, MD + YAML frontmatter)
├── extractions/                 # ext_*.yaml         (1..N, one per source card)
├── claims/
│   ├── claim_ledger.yaml        # clm_NNN entries (the authority)
│   ├── contradiction_log.yaml   # usually [] 
│   └── inference_log.yaml       # usually []
├── reports/
│   ├── report_draft.md          # MD + frontmatter, claims tagged [claim:clm_NNN]
│   └── report_final.md          # (DECLARED; optional — absent in tailed runs)
├── reviews/
│   ├── verification.yaml        # claim-verify gate output (always present)
│   ├── critic_review.yaml       # (DECLARED; optional)
│   ├── council_review.yaml      # (DECLARED; optional — ARC council)
│   └── governance_review.yaml   # (DECLARED; optional)
├── evidence_bundle.yaml         # roll-up: artifacts map + counts + governance + lineage
├── telemetry/
│   └── run_trace.jsonl          # append-only stage events
└── writebacks/
    ├── ccdash_event.yaml        # execution telemetry event (metrics/governance/reuse)
    ├── meatywiki_writeback.md    # source-note writeback payload
    └── skillbom_candidate.md     # reusable-skill candidate payload
```

**Always-present (observed across 38-42 runs):** `run.yaml`, `routing_decision.yaml`, `research_brief.md`, `swarm_plan.yaml`, `sources/`, `extractions/`, `claims/{claim_ledger,contradiction_log,inference_log}.yaml`, `reports/report_draft.md`, `reviews/verification.yaml`, `evidence_bundle.yaml`, `telemetry/run_trace.jsonl`, `writebacks/{ccdash_event.yaml, meatywiki_writeback.md, skillbom_candidate.md}`.

**Declared-but-optional (in `RunPaths`, absent in the deterministic-tail runs):** `source_candidates.yaml`, `reports/report_final.md`, `reviews/{critic_review,council_review,governance_review}.yaml`.

**Upstream (outside `runs/`, referenced by id):** `raw_idea`, `research_intent`, `ibom`, `intenttree_node`.

---

## COMPLETE Run Entity Model

Legend — Presence: ●=always, ◐=optional/conditional, ○=upstream (lives outside the run dir, linked by id).

| # | Entity | Presence | On-disk location & format | Key fields | Relationships | Lifecycle states | Display affordance |
|---|--------|:---:|---------------------------|-----------|---------------|------------------|--------------------|
| 1 | **raw_idea** | ○ | `inbox/raw_ideas/raw_*.md` (MD + frontmatter) | `id`, `title`, `body`, `tags`, `sensitivity`, `urgency`, `research_potential`, `triage.status`, `triage.intent_id` | parent of → research_intent (via `triage.intent_id`); referenced by `evidence_bundle.lineage.raw_idea_ids` | `triage.status`: captured → converted_to_intent | Collapsible origin card at top of run timeline; tag chips; "captured from" badge |
| 2 | **research_intent** | ○ | `intents/active/intent_*.yaml` | `id`, `title`, `objective`, `motivation`, `research_questions`, `constraints.hard/soft`, `governance` (sensitivity, key_profile_allowed, allowed_writebacks), `ibom_ref`, `intenttree_node_ref` | parent of → ibom, research_brief, run; child of ← raw_idea | `status`: active / … | Header panel: objective hero text + hard-constraint pills (e.g. "every claim → source") |
| 3 | **ibom** (Intent Bill of Materials) | ○ | `iboms/active/ibom_*.yaml` | `id`, `intent_id`, `context_snapshot`, `tools_available`, `model_policy` (extraction/synthesis/verification profiles), `assumptions`, `security_boundaries`, `open_questions` | child of ← intent; informs routing_decision/swarm_plan | `snapshot_status`: draft / … | Side panel "run inputs": tools list, model-policy table, security-boundary callouts |
| 4 | **intenttree_node** | ○ | `intenttree/nodes/*.yaml` (schema `intenttree_node.schema.yaml`) | node id, abstraction level, links | links run into the IntentTree graph (`routing_decision.active_node_id`) | n/a | Breadcrumb / "open in IntentTree" deep link badge |
| 5 | **run** (`run.yaml`) | ● | `run.yaml` (YAML) | `run_id`, `intent_id`, `ibom_id`, `brief_id`, `swarm_id`, `routing_id`, `created_at`, `status`, `sensitivity`, `human_required`, `profile` (depth, audience, max_cost_usd, max_runtime_minutes, freshness_days, model profiles) | hub: links every id; parent of all run-local artifacts | `status` enum observed: `planned` (NOTE: not advanced by the deterministic tail) | Run header bar: status badge, sensitivity badge, profile chips (depth/audience/budget) |
| 6 | **routing_decision** | ● | `routing_decision.yaml` | `selected_abstraction_level` (L0–L4), `selected_posture_chain`, `selected_skillbom`, `selected_context_packs`, `selected_tools`, `human_required`, `rationale`, `expected_output`, `validation[]`, `writebacks[]` | derived from intent/ibom; declares planned writebacks → writeback entities | static (decided at plan time) | "How this run was routed" card: posture-chain stepper, tool chips, rationale quote |
| 7 | **research_brief** | ● | `research_brief.md` (MD + frontmatter) | `questions.primary[]/secondary[]` (rq_NNN), `source_strategy` (include/exclude source_types, freshness rules), `output_requirements` | child of ← intent; questions are answered by claims/report | static | Questions list (rq_NNN as anchors); source-strategy as include/exclude filter chips |
| 8 | **swarm_plan** | ● | `swarm_plan.yaml` | `agents[]` (role, posture, tool, model_profile, task), `budget`, `required_outputs[]`, `status` | parent of → swarm/subagent run records (conceptually); lists required_outputs (checklist for bundle) | `status` enum: planned / running / completed / failed | Agent roster table (role × posture × tool × model); required-outputs checklist with present/absent ticks |
| 9 | **source_candidates** | ◐ | `source_candidates.yaml` | ranked, deduped candidate sources (url, score, dedup) | parent of → source_cards (accepted candidates become cards) | absent in tailed runs (Path-B authors cards directly) | Ranked candidate table with accept/reject status; graceful empty-state when absent |
| 10 | **source_card** | ● (1..N) | `sources/src_*.md` (MD + frontmatter) | `source_card_id`, `source` (title, source_type, locator{url,file_path,doi,repo}, authors, publisher, published_at, accessed_at), `trust` (source_rank, reliability_notes, known_limitations, conflicts_with), `usage` (allowed_for_public/work/personal, citation_required, quote_limit_notes), `extracted_points[]` (evidence_id, locator, summary, quote) | child of ← source_candidate; parent of → extraction_card; cited by → claim (via `source_card_id` + `evidence_id`) | ingested → reliability-rated (observed: "not yet reliability-rated") | Source card (literal card UI): trust badge, source-type icon, usage-permission pills, expandable quotes; node in provenance graph |
| 11 | **extraction_card** | ● (1..N) | `extractions/ext_*.yaml` | `id`, `source_card_id`, `extractor_agent`, `model_profile`, `extracted_facts[]` (evidence_id, text, locator, confidence, quote_available), `extracted_definitions[]`, `extracted_metrics[]`, `contradictions_or_cautions[]` | child of ← source_card (1:1 typical); feeds → claim_ledger | static | Nested under its source card; confidence badge per fact; "metrics extracted" sub-table |
| 12 | **claim_ledger entry (clm_NNN)** | ● (1..N) | `claims/claim_ledger.yaml` → `claims[]` | `claim_id`, `text`, `materiality` (background/material), `claim_type` (factual/quantitative/attribution/…), `status` (supported/mixed/contradicted/inference/speculation/unsupported), `confidence`, `sources[]` (source_card_id, evidence_id, relation, locator), `inference_basis` (from_claims, reasoning_summary), `report_locations[]`, `reviewer_notes` | THE central entity: child of ← source_card+evidence; cited by → report (`[claim:clm_NNN]`); root of provenance chain | `status` per claim; ledger-level `verification_status`: passed/… | **Claim ledger table** (status badge, confidence, materiality) — the marquee view; click claim → provenance drill-down (claim → source_card → evidence quote) |
| 13 | **contradiction_log** | ● | `claims/contradiction_log.yaml` | `run_id`, `generated_at`, `contradictions[]` (usually empty) | references claims/source_cards in conflict | static | Conflict callout panel; empty-state "no contradictions"; diff/side-by-side when populated |
| 14 | **inference_log** | ● | `claims/inference_log.yaml` | `run_id`, `generated_at`, `inferences[]` (usually empty) | references inference-type claims | static | "Analytic inferences" panel; links to inference-status claims |
| 15 | **report (draft)** | ● | `reports/report_draft.md` (MD + frontmatter) | frontmatter: `report_id`, `title`, `intent_id`, `evidence_bundle_id`, `status`, `audience`, `sensitivity`, `claim_policy`, `verification_status`; body sections: Findings / Inferences / Speculation with `[claim:clm_NNN]` inline tags | child of ← claim_ledger; tags resolve to claims | `status`: draft; `verification_status`: pending/passed | Rendered Markdown with **inline claim chips** — hover/click a `[claim:clm_NNN]` to pop the claim + its source provenance |
| 16 | **report (final)** | ◐ | `reports/report_final.md` | same as draft, promoted | supersedes draft | absent in tailed runs | Tab toggle draft↔final; diff view when both exist |
| 17 | **verification** | ● | `reviews/verification.yaml` | `passed`, `exit_code`, `human_review_required`, `report_path`, `claim_ledger_path`, `checks[]` (id, severity error/warning, status pass/fail, detail, locations) | the **gate** over report+ledger | `passed`: true/false | **Verification checklist** — pass/fail rows with severity; big green/red gate badge at run header |
| 18 | **critic_review** | ◐ | `reviews/critic_review.yaml` (schema `review_packet`) | critic findings | review over report | absent in tailed runs | Review packet card (collapsed by default) |
| 19 | **council_review** | ◐ | `reviews/council_review.yaml` (ARC council) | multi-reviewer verdicts | review over report | absent unless ARC run | Reviewer-panel grid (per-reviewer verdict) |
| 20 | **governance_review** | ◐ | `reviews/governance_review.yaml` | policy verdict (in-run file form) | governance over run | absent in tailed runs (governance runs as a hook — see §"Governance") | Policy verdict card |
| 21 | **evidence_bundle** | ● | `evidence_bundle.yaml` | `id`, `intent_id`, `run_id`, `status`, `artifacts{}` (map of every artifact path), `counts{}` (source_cards, extraction_cards, claims_total/supported/mixed/contradicted/inference/speculation/unsupported), `governance` (sensitivity, approved_for_writeback, approved_by), `lineage` (raw_idea_ids, intent_id, ibom_id, intenttree_node_id, skillbom_ids_used) | **roll-up / index** of the whole run; best single entrypoint for a viewer | `status`: verified/… | **Run summary dashboard**: counts as stat tiles, claim-status donut, governance/approval badge, artifact map as nav |
| 22 | **telemetry / run_trace** | ● | `telemetry/run_trace.jsonl` (JSONL) | per-line `{stage, ts, run_id, …}`; observed stages: plan, ingest, extract, claim_map, synthesize, verify, bundle, writeback, ccdash_event, guard | sequence of stage events for the run | append-only event log | **Run timeline / stepper** (plan → ingest → extract → claim_map → synthesize → verify → bundle → writeback); per-stage status dots |
| 23 | **swarm/subagent run records** | ◐ | *no dedicated per-agent artifact in tailed runs*; reconstructable from `swarm_plan.agents[]` (intended roster) + `telemetry` stages (actual execution) + `extraction_card.extractor_agent` / `source_card.created_by_agent` | which agent/posture/tool produced which artifact | swarm_plan ↔ telemetry ↔ artifact `created_by_agent` | n/a (derived) | "Who did what" lane view; map agents to the stages/artifacts they emitted |
| 24 | **ccdash_event (writeback)** | ● | `writebacks/ccdash_event.yaml` | `event_id`, `project`, `agent_postures`, `skillbom_ids`, `tools`, `input/output_artifacts`, `metrics{}` (cost_estimated_usd, latency_minutes, tokens_estimated, rework_count, drift_score, quality_score, verification_passed, claim counts), `governance{}` (sensitivity, key_profile_used, policy_passed, violations), `reuse{}`, `human_review{}` | telemetry writeback to CCDash | static payload | **Cost/telemetry panel** (cost, latency, drift, quality tiles) + governance verdict badge + reuse-candidate flags |
| 25 | **meatywiki_writeback** | ● | `writebacks/meatywiki_writeback.md` (schema `meatywiki_writeback`) | source-note payload destined for MeatyWiki | writeback target | candidate → written (governed) | Writeback-target card: destination badge, "approved_for_writeback" gate, payload preview/diff |
| 26 | **skillbom_candidate** | ● | `writebacks/skillbom_candidate.md` (schema `skillbom_candidate`) | reusable-skill candidate payload destined for SkillMeat | writeback target | candidate → promoted (`rf skillbom promote`) | Writeback-target card: destination badge, candidate/promoted state |
| 27 | **governance / key-profile verdict** | ● (as data) | embedded: `evidence_bundle.governance`, `ccdash_event.governance` (`policy_passed`, `violations[]`, `key_profile_used`, `approved_for_writeback`); enforced live by the PreToolUse guard hook (`validators/guard_pretool.py`) | sensitivity × key_profile × writeback-target legality | gates writebacks | pass / fail (+ violations) | Governance verdict badge at run header; violations list; key-profile chip |
| 28 | **secret-scan result** | ● (as process) | **no persistent run artifact** — runs as a PostToolUse hook (`validators/scan_artifact.py` → `services/governance.scan_secrets`) at write time; surfaced via telemetry `guard` stage / governance `violations` | scans each written file for secrets, lints claim labels | cross-cuts all artifacts | clean / hit | Inline warning badge on any artifact flagged; aggregate "scan clean" badge (derive from governance.violations) |
| 29 | **AAR (after-action report)** | ◐ | *not a per-run artifact*; AARs are authored at the wave level under `docs/projects/research-foundry/aars/*.md` (per project memory) | wave-level lessons, cost rollups | spans multiple runs | n/a | Out of v1 run-viewer scope; optional "related AAR" link at wave/index level |

**Entity count: 29** distinct entity types (12 always-present run-local, 9 optional/declared, 4 upstream, plus telemetry/derived/process entities).

### Core provenance chain (the spine of the viewer)

```
raw_idea → research_intent → ibom → routing_decision + research_brief + swarm_plan
                                          ↓
        source_candidate → source_card → extraction_card → claim_ledger(clm_NNN) → report(draft)
                                                                   ↓
                                                            verification (gate)
                                                                   ↓
                                                          evidence_bundle (roll-up)
                                                                   ↓
                                            writebacks: meatywiki / skillbom / ccdash
```

This chain — **claim → source_card → evidence quote**, with `[claim:clm_NNN]` tags binding report prose to the ledger — is the highest-value thing a viewer makes legible.

---

## Read-Path Feasibility (deal-killer test)

**Can a faithful viewer read runs purely from on-disk artifacts + `rf` CLI, with no always-on backend and no LLM on recall?** **Yes.**

Evidence:
1. **All entities are static files.** YAML/MD/JSONL only (`runs/`: 779 md, 776 yaml, 42 jsonl). No DB, no service-of-record for runs. Files are canonical (AOS file-first honored).
2. **A machine-readable manifest already exists in code.** `RunPaths` (`paths.py:129-214`) enumerates every file path a run can hold; `evidence_bundle.yaml.artifacts{}` is a per-run artifact map. A walker is trivial and deterministic.
3. **Reads require zero inference.** Resolving `[claim:clm_NNN]` → claim → `source_card_id`/`evidence_id` → quote is pure key lookup. No LLM on the recall path.
4. **Schemas are the stable contract.** 20 `schemas/*.schema.yaml` define every shape; a viewer can validate/parse against them (no guessing field names).

**The gap (the "constraints" in the verdict):** there is **no existing aggregate read/export command.** The CLI (`cli_commands.py`) has `intent show` and per-domain commands but **no `rf run show/export --json`** and no run-aggregate JSON. So a viewer must either (a) read the raw files directly, or (b) we author a thin deterministic export. Authoring that export is small, no-LLM, file-only work — it does **not** require a new always-on service. **Deal-killer NOT triggered.**

### Recommended read path

**Primary: build-time static export → static SPA.** Author `rf run export [--json] [--all]` that walks `RunPaths` + parses YAML/MD frontmatter + resolves the claim→source graph into one `run.json` per run (plus an `index.json`). Bake into the existing MkDocs/site build or a separate static SPA. Honors file-first, no-LLM, no-runtime-service, deployable as static assets (matches the just-shipped MkDocs site model).

**Optional dev/live mode: thin loopback read API.** A `rf serve --read-only` (loopback-only, like MeatyWiki API `:8765`) that serves the same `run.json` for live browsing of fresh runs without a rebuild. Read-only, loopback-bound, no LLM — fully within AOS constraints. Use only if "browse runs as they land" becomes a need; otherwise static export alone suffices.

**Anti-pattern (reject): in-browser raw-file parsing** of arbitrary `runs/` paths — couples the UI tightly to the on-disk layout (schema-drift risk) and re-implements the claim-graph join in JS. Centralize the join in the `rf` export instead, so the data-shape contract lives in Python next to the schemas.

---

## Integration Points (what a viewer depends on)

- `runs/rf_run_*/` directory tree (the data) — layout defined by `src/research_foundry/paths.py` `RunPaths`.
- `schemas/*.schema.yaml` (20 schemas) — the field contract; viewer types should be generated/validated from these.
- `evidence_bundle.yaml` per run — best single entrypoint (`artifacts{}` map + `counts{}` + `lineage`).
- `claims/claim_ledger.yaml` + report `[claim:clm_NNN]` tags — the provenance join.
- Upstream by-id lookups: `intents/active/intent_*.yaml`, `iboms/active/ibom_*.yaml`, `inbox/raw_ideas/raw_*.md`.
- **New code to author:** `rf run export --json` in `src/research_foundry/cli_commands.py` + a `services/` export helper (deterministic walk; reuse `yamlio`, `frontmatter`, `paths`).
- Prior-art stack: `website/mkdocs.yml` (MkDocs Material) — candidate host for a static viewer, or a sibling static SPA.

---

## Effort Estimate (ROM)

**Range: 13–21 story points** (Tier 3 candidate, consistent with charter's greenfield/high-uncertainty framing).

Bottom-up:
- `rf run export --json` + index export (deterministic walk, claim-graph join, schema-typed): **3–5 pts**.
- Run index / list view (cards, status/sensitivity/counts): **2–3 pts**.
- Single-run dashboard (evidence_bundle stat tiles, timeline from telemetry, verification gate): **3 pts**.
- Claim ledger view + claim→source provenance drill-down (the marquee feature): **3–5 pts**.
- Report viewer with inline `[claim:clm_NNN]` resolution: **2–3 pts**.
- Source/extraction cards + writeback/governance panels: **2 pts**.
- Hidden plumbing (TS types from schemas, empty-states for optional entities, build/deploy glue): **~2 pts** (H6).

**H5 anchor:** the closest comparable past feature is the **MkDocs site + 18-run case study** (commit `1ae5bff`, 2026-06-19) — same data corpus, static-build pattern, already-solved deploy story. That build is the single best anchor: it proves the static-from-files read path is viable and gives a deploy template. Delta vs. that anchor: the viewer adds an interactive claim-graph and a JSON export (the case study was hand-curated narrative, not a generic per-run viewer), justifying the higher point range.

---

## Open Questions (OQ-*)

- **OQ-1 (contract — the conditional precondition):** Author `rf run export --json` schema. What is the exact `run.json` shape — flat artifact map mirroring `evidence_bundle.artifacts`, or a denormalized claim-graph with embedded source/evidence? Recommendation: denormalized claim-graph (UI shouldn't re-join). This is the named next step for a `conditional`-style go.
- **OQ-2 (run status):** `run.yaml.status` stays `planned` even in fully-verified runs (deterministic tail doesn't advance it). Should the viewer derive effective status from `evidence_bundle.status` + `verification.passed` instead of trusting `run.yaml.status`? Recommendation: yes — derive, treat `run.yaml.status` as advisory.
- **OQ-3 (optional-entity rendering):** `source_candidates.yaml`, `report_final.md`, `critic/council/governance_review.yaml` are schema-declared but absent in tailed runs. Confirm graceful empty-states (not errors) for all 9 optional entities.
- **OQ-4 (governance/secret-scan surfacing):** secret-scan + governance run as Claude Code hooks (no persistent per-run artifact); their verdict lives in `evidence_bundle.governance` / `ccdash_event.governance.violations`. Is that sufficient for the viewer, or should the export synthesize a dedicated "governance verdict" object? Recommendation: synthesize one in the export from those two sources.
- **OQ-5 (schema-drift coupling):** schemas are v0.1. Should the export pin/version-check the schema_version per artifact and warn on mismatch, to insulate the UI from drift? (Risk leg should weigh in.)
- **OQ-6 (static vs loopback):** Is "browse runs as they land" a real JTBD (→ loopback read API) or is per-build static export enough? Defer to value leg.
- **OQ-7 (wave/AAR scope):** AARs are wave-level (`docs/projects/research-foundry/aars/`), not per-run. In/out of v1? Recommendation: out of v1 run viewer; optional index-level link.

---

## Feasibility Verdict

**`feasible-with-constraints`** — the run entity model is complete, stable (schema-backed), and fully derivable from on-disk artifacts; a faithful read-only viewer needs no always-on service and no LLM on the recall path. The single constraint is authoring a deterministic `rf run export --json` (OQ-1) so the claim-graph join lives in Python beside the schemas rather than in the browser. The charter deal-killer does **not** fire.

**Confidence score: 0.82**
