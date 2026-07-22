# Research Foundry

**An evidence-first, Markdown/YAML-first research control plane.** Research Foundry captures raw
ideas, converts them into structured research intents, plans and runs research swarms, collects
normalized source cards, extracts evidence, builds an auditable **claim ledger**, synthesizes
reports, and verifies that every material claim traces back to a source — before anything is
published or fed downstream into **MeatyWiki**, **SkillMeat/SAM**, and **CCDash**. Claim
traceability is the core value: a report may contain only supported claims mapped to source cards,
plus explicitly labeled inference, speculation, mixed, or contradicted claims. Nothing else passes.

Everything is human-readable on disk. Every intent, source card, extraction, claim, report,
writeback, SkillBOM candidate, and telemetry event is plain Markdown/YAML — no database required,
deterministic, and diff-friendly.

---

## Why it's different

- **The claim ledger is the authority, not the model.** The synthesis step can only cite claim IDs
  that already exist in `claims/claim_ledger.yaml`, or it must label a sentence as inference or
  speculation. `rf verify` fails the build on any unsupported material claim. The durable asset is
  the **evidence bundle** (source cards, extractions, claim ledger, report, reviews, telemetry) —
  the swarm that produced it is disposable and rerunnable.
- **Cheap models extract; expensive models synthesize.** Extraction, source-card creation,
  deduplication, tagging, and formatting run on local/free/cheap model profiles. Higher-reasoning
  models are reserved for synthesis, contradiction analysis, and executive framing — controlled by
  named model profiles (e.g. `rf_extract_cheap`, `rf_synthesize_deep`).
- **Governance is a runtime gate, not a memo.** Work-provided keys, sensitive source material,
  model routing, and writeback targets are checked *before* execution. Key profiles
  (`personal`, `work_approved`, `client_approved`, `offline_only`) are enforced by `rf guard`, and
  work/personal key mixing is blocked deterministically.

---

## Status: working platform, growing beyond the MVP core

Research Foundry started as a 7-day MVP CLI (spec below) and that core — capture → triage → plan →
ingest → extract → claim-map → synthesize → verify → bundle → writeback — is still intact, still
fully **offline and deterministic by default**, and remains the differentiated value: the
deterministic report verifier and the claim ledger it checks against. That core has since grown a
platform around it: ~30 `rf` CLI commands (Report Builder, evidence catalog, audit log, workspace
migration), an HTTP API + MCP surface (`rf serve`, `rf-mcp`), and a web app
(`frontend/runs-viewer/`, Vite + React) with a static read-only mode deployed today and an
opt-in live-loopback mode for authoring. An early self-host/small-team scaffold — auth providers
(`none`/`local_static`/`clerk`), role-based access control, and workspace row-level isolation — is
shipped but **advisory-by-default**, not yet hardened for a shared multi-tenant deployment.

Be clear-eyed about maturity: the governance guard, schema validation, claim verification, and the
full demo loop need no network and no LLM, and are battle-tested. Several platform-expanding pieces
are newer and less proven — the Search Router's keyed providers, the ARC/IntentTree bidirectional
integrations, and the NotebookLM sync loop are implemented against inferred external contracts but
have not yet had first contact with a live remote system from this repo (see
`docs/project_plans/exploration/web-app-platform-evolution/current-state-and-direction.md` for the
full capability-maturity map). Live model adapters (Claude Agent SDK, GPT Researcher, PaperQA2,
OpenCode, LiteLLM router) remain **opt-in extras**, enabled at init time and only used when you ask
for them — `rf synthesize --llm` is a deterministic no-op by design; only the Claude Agent SDK
adapter has confirmed live use (the Path B discovery-swarm workflow).

Source of truth:

- Spec: [`docs/projects/research-foundry/research-foundry-mvp-spec.md`](docs/projects/research-foundry/research-foundry-mvp-spec.md)
- Plan: [`docs/projects/research-foundry/IMPLEMENTATION_PLAN.md`](docs/projects/research-foundry/IMPLEMENTATION_PLAN.md)
- Service contract (current): [`docs/projects/research-foundry/SERVICE_CONTRACT.md`](docs/projects/research-foundry/SERVICE_CONTRACT.md)
- Current-state report: [`docs/project_plans/exploration/web-app-platform-evolution/current-state-and-direction.md`](docs/project_plans/exploration/web-app-platform-evolution/current-state-and-direction.md)

---

## Install & quickstart

Install with [uv](https://docs.astral.sh/uv/):

```bash
uv venv
uv pip install -e ".[dev]"
```

Initialize a foundry (folder structure, schemas, templates, governance policy, default model
profiles, `.env.example`, `.gitignore`):

```bash
rf init ./research-foundry --profile personal
rf doctor
```

### The demo loop, end to end

A self-referential, bounded, work-data-free demo:
*"What is the minimum viable architecture for an evidence-backed research swarm inside Agentic OS?"*
This loop is deterministic and offline by default.

```bash
# 1. Capture a raw idea -> inbox/raw_ideas/raw_*.md
rf capture "Research how agentic research workflows should handle evidence bundles" \
  --from manual --sensitivity personal --tag agentic-os --tag research-foundry

# 2. Triage into intent + I-BOM + IntentTree node
rf triage inbox/raw_ideas/raw_*.md --create-intent --create-ibom --create-tree-node

# 3. Plan the swarm -> research brief, swarm plan, routing decision
rf plan intent_research_20260612_agentic_research_workflows \
  --depth deep --audience technical --max-cost 5 --freshness 180d

# 4. Ingest sources (mixed types) -> source cards in the run's sources/
rf ingest ./examples/source.pdf --source-type paper --sensitivity personal \
  --run rf_run_20260612_agentic_research_workflows
rf ingest "https://example.com/source" --source-type official_doc --sensitivity public \
  --run rf_run_20260612_agentic_research_workflows

# 5. Extract evidence -> extraction cards (cheap model profile)
rf extract rf_run_20260612_agentic_research_workflows --model-profile rf_extract_cheap

# 6. Build the claim ledger -> claims/claim_ledger.yaml
rf claim-map rf_run_20260612_agentic_research_workflows \
  --from extractions --out claims/claim_ledger.yaml

# 7. Synthesize the report (deep model profile; may only cite ledger claim IDs)
rf synthesize rf_run_20260612_agentic_research_workflows \
  --report reports/report_draft.md --model-profile rf_synthesize_deep

# 8. Verify every material claim -> fails the build on anything unsupported
#    Auto-discovers the run's report + claim ledger (preferred form):
rf verify rf_run_20260612_agentic_research_workflows --fail-on-unsupported
#    Or with explicit relative paths (resolved against the run directory):
#    rf verify rf_run_20260612_agentic_research_workflows \
#      --report reports/report_draft.md \
#      --claim-ledger claims/claim_ledger.yaml --fail-on-unsupported

# 9. Publish the durable evidence bundle -> evidence_bundle.yaml
rf bundle rf_run_20260612_agentic_research_workflows --verify --out evidence_bundle.yaml

# 10. Write back to MeatyWiki, SkillMeat, and CCDash
rf writeback rf_run_20260612_agentic_research_workflows \
  --targets meatywiki,skillmeat,ccdash --require-review

# 11. Summarize CCDash telemetry for the day
rf ccdash summarize --period daily
```

Optional review and promotion steps:

```bash
rf council rf_run_20260612_agentic_research_workflows \
  --roles critic,domain_reviewer,governance_officer,executive_translator \
  --vote approve-concern-block
rf skillbom propose rf_run_20260612_agentic_research_workflows
```

### Viewing run provenance

Export a run's full claim graph to a static JSON file and open the viewer:

```bash
# Export a single run (writes <run_dir>/run.json; default threshold: public)
rf run export --json --run-id rf_run_20260612_agentic_research_workflows

# Export all discovered runs before a viewer build (catches nested runs/runs/)
rf run export --json --all

# Override sensitivity threshold (expose personal-level content locally)
rf run export --json --run-id rf_run_20260612_agentic_research_workflows \
  --sensitivity-threshold personal

# Print JSON to stdout for piping
rf run export --json --run-id rf_run_20260612_agentic_research_workflows --stdout | jq '.claims | length'

# List all runs as JSON with derived status (never stale run.yaml.status)
rf run list --json
```

The `frontend/runs-viewer/` SPA loads the exported `run.json` files from a
static-file server. Sensitivity redaction is applied at export time — governed
content never reaches the viewer. See
`docs/dev/architecture/adr-runs-read-path.md` for the full read-path decision.

### Reusable Assertion Ledger Readiness

The optional reusable assertion ledger is default-off. Its local readiness
controls, safe aggregate metrics, and disable rehearsal are documented in the
[operator runbook](docs/dev/architecture/runbooks/assertion-ledger-readiness.md).
The user-facing model (assertions, inferences, denial and correction states) is
in [the assertion-ledger guide](docs/user/assertion-ledger.md). Neither document
authorizes private rollout, shared indexing, public promotion, or external
writeback.

### Serving Runs Live (Loopback API)

Alternatively, run a local HTTP server to serve live run data without pre-exporting:

```bash
# Start the server on loopback (127.0.0.1:7432, no auth required)
rf serve

# Or start on LAN with a shared-secret token (requires RF_SERVE_TOKEN env var)
export RF_SERVE_TOKEN="your-secret-token-here"
rf serve --bind-host 0.0.0.0 --auth-mode token

# Configure the SPA to use the live API
export VITE_RUNS_FRONTEND_LOOPBACK_API=true
export VITE_RUNS_LOOPBACK_API_BASE=http://127.0.0.1:7432/api
export VITE_RUNS_LOOPBACK_API_TOKEN="your-secret-token-here"  # if LAN mode
pnpm --filter runs-viewer build
pnpm --filter runs-viewer preview  # or serve with your static host
```

**`rf serve` environment variables and defaults:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `RF_SERVE_TOKEN` | — | Shared-secret token for LAN mode (`--auth-mode token`). Must be set before starting with `--bind-host 0.0.0.0`. |
| `VITE_RUNS_FRONTEND_LOOPBACK_API` | `false` | Set to `true` to enable loopback API mode in the SPA (at build time). |
| `VITE_RUNS_LOOPBACK_API_BASE` | `http://127.0.0.1:7432/api` | Base URL for loopback API requests (override if `rf serve` runs on a different host/port). |
| `VITE_RUNS_LOOPBACK_API_TOKEN` | — | Bearer token for loopback API requests when `--auth-mode token` is enabled. |

**Port allocation:**

- Default port: `7432` (loopback and LAN modes)
- Configurable: `rf serve --port 9000` (or set `foundry.yaml → viewer.serve_port`)
- **Note**: Port `8765` is reserved for MeatyWiki on agentic-nuc; `7432` avoids this conflict.

**Static export vs. loopback API:**

| Aspect | Static Export | Loopback API |
|--------|---------------|--------------|
| **Setup** | `rf run export --json --all` (one-time or pre-build) | `rf serve` (always-on process) |
| **Freshness** | Stale until re-export | Live (per-request reads) |
| **Deployment** | Works offline, no auth needed | Requires running server; LAN mode requires token |
| **Scalability** | Pre-build scales with run count | Per-request reads scale per query |
| **Default** | Enabled (`VITE_RUNS_FRONTEND_LOOPBACK_API=false`) | Opt-in (`VITE_RUNS_FRONTEND_LOOPBACK_API=true`) |

For details, see `docs/dev/architecture/adr-runs-read-path.md`.

### Run Metadata (Linked Projects, Category, Tags)

Runs can carry rich metadata derived from the research backlog, displayed across the viewer and
used for portfolio filtering and project linking:

**Metadata fields:**
- **Linked Projects:** Project slugs the run is associated with (e.g., `research-foundry`,
  `skillmeat`). Used for portfolio filtering and cross-project linking.
- **Category:** Research pillar or domain (e.g., `AI Engineering`, `Frontend Tooling`).
- **Tags:** User-defined topic tags for classification and discovery.
- **Backlog Idea Reference:** The RIB-NNN identifier when the run was created from a research
  idea backlog entry.

**Where metadata is displayed:**
- **Portfolio table:** Project column shows linked projects as badges; filter by project,
  category, or tag using the FilterTabs.
- **Run cards:** Project badges and tag chips visible at a glance.
- **Run Detail:** All metadata fields shown in the Overview section with enrichment widgets
  (cost, model profiles, source diversity).
- **Claim ledger:** Tag references linked to claims for contextual discovery.

**Filtering portfolio by metadata:**

Use the FilterTabs (Project, Category, Tags filters) to narrow the portfolio view:
```
Portfolio filters use AND logic: runs must match selected projects AND category AND tags.
Runs with null metadata are excluded when a filter is active.
Clear all filters to see the full portfolio.
```

**Backfill migration for pre-migration runs:**

Runs created before metadata enrichment was enabled (schema < 1.2) carry `null` values for these
fields. The backfill migration idempotently populates metadata by inverting the research backlog's
idea↔run linkage:

```bash
# Preview changes without committing
scripts/backfill_run_metadata.py --dry-run

# Apply the migration
scripts/backfill_run_metadata.py --commit
```

After backfill, re-export runs before restarting the viewer:
```bash
rf run export --json --all
pnpm --filter runs-viewer build
```

See `docs/dev/architecture/rf-run-export-schema.md` §11–13 for complete schema documentation.

---

## Folder map

Condensed from the spec's MVP folder structure:

```
research-foundry/
  foundry.yaml            # foundry config
  .env.example            # secrets template (.env* always gitignored)
  config/                 # governance.yaml, model_profiles.yaml, routing_rules.yaml,
                          #   tools.yaml, claim_policy.yaml
  schemas/                # YAML schemas: raw_idea, research_intent, ibom, source_card,
                          #   extraction_card, claim_ledger, evidence_bundle, ccdash_event, ...
  templates/              # Markdown/YAML templates for ideas, briefs, cards, reports, writebacks
  inbox/                  # raw_ideas/, clips/, imports/, voice_transcripts/
  intents/                # active/, paused/, completed/, archived/
  iboms/                  # active/, snapshots/
  intenttree/             # research_foundry_tree.yaml, nodes/
  runs/                   # rf_run_YYYYMMDD_slug/  (append-first, mostly immutable)
    rf_run_*/
      run.yaml  routing_decision.yaml  research_brief.md  swarm_plan.yaml
      sources/        # src_*.md (normalized source cards)
      extractions/    # ext_*.yaml
      claims/         # claim_ledger.yaml, contradiction_log.yaml, inference_log.yaml
      reports/        # report_draft.md, report_final.md
      reviews/        # critic_review.yaml, council_review.yaml, governance_review.yaml
      evidence_bundle.yaml
      writebacks/     # meatywiki_writeback.md, skillbom_candidate.md, ccdash_event.yaml
      telemetry/      # token_costs.yaml, tool_calls.yaml, run_trace.jsonl
  registries/             # indexes (source, claim, skillbom, report, run) over the artifacts
  meatywiki/              # local mirror: concepts/, sources/, decisions/, patterns/
  skillmeat/              # local mirror: skillboms/, prompts/, context_packs/, evals/
  ccdash/                 # local mirror: events/, daily/, summaries/
  src/research_foundry/   # cli.py, config.py, schemas.py, validators/, adapters/, services/
  tests/                  # schema validation, claim verifier, governance, writebacks
```

Folder rules: `runs/` is append-first and mostly immutable for reproducibility; `registries/`
index artifacts but never replace them; `meatywiki/`, `skillmeat/`, and `ccdash/` are local mirrors
for later sync; `.env*` files are always gitignored; work-sensitive runs do not write to a personal
MeatyWiki by default.

---

## Claim-status model

A **material claim** is any statement a reader could reasonably rely on as true (factual,
quantitative, comparative, causal, attribution, recommendation, or prediction). Every material
claim in a report must carry one of these statuses:

| Status | Meaning | Report label required | Build effect |
| --- | --- | --- | --- |
| `supported` | Directly supported by one or more source cards | no | passes |
| `mixed` | Sources disagree or support only part of the claim | yes (`Mixed evidence`) | passes |
| `contradicted` | Evidence contradicts the claim | yes (`Contradicted / do not use as finding`) | passes |
| `inference` | Reasonable synthesis from supported claims, not directly stated | yes (`Inference`) | passes |
| `speculation` | Forward-looking or insufficiently evidenced idea | yes (`Speculation`) | passes |
| `unsupported` | Material claim lacks a source or a proper label | yes | **fail** |

`rf verify --fail-on-unsupported` enforces this. Its exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Pass |
| 2 | Schema validation failed |
| 3 | Governance policy blocked |
| 4 | Unsupported material claim |
| 5 | Budget exceeded |
| 6 | Adapter/tool failure |
| 7 | Human review required |

---

## Governance & key profiles

Governance is enforced at runtime, before any model or tool runs. Each run executes under a key
profile that scopes which keys, providers, and writeback targets are allowed:

- **`personal`** — personal research; forbids employer/client confidential data. Uses `.env.personal`.
- **`work_approved`** — approved work-internal research and tools; requires an explicit profile
  flag; forbids personal cost-avoidance, unreviewed personal publication, and non-approved
  endpoints. Uses `.env.work`.
- **`client_approved`** — explicit client-authorized research only; requires human review; forbids
  cross-client reuse and public/personal writeback. Uses `.env.client`.
- **`offline_only`** — local documents and local models only; no external LLM calls or search.

Non-negotiable rules are enforced deterministically (no LLM required): for example, work-provided
keys cannot be used for personal runs. Check a profile before running:

```bash
rf guard check --profile personal
rf doctor
```

Utility commands: `rf status`, `rf cost runs/rf_run_*/`, `rf redact runs/rf_run_*/ --target public`,
`rf index rebuild`.

Live integrations (degrade to file candidates when servers offline):
- `rf intake intenttree <node_id> [--from-file PATH] [--plan/--no-plan] [--sensitivity S] [--profile P]` — ingest a dispatched IntentTree task with linked detail into capture → triage → optional plan.
- `rf status push --run <run_id> --to intenttree [--stage STAGE]` — push progress updates to the originating IntentTree node at key milestones (discovery_started, sources_ingested, verify_passed, bundle_written).
- `rf council <run_id> --via arc` (vs default `--local`) — run live ARC council review when reachable; offline fallback to local `research-foundry-council.js` workflow.
- `rf writeback <run_id> --targets intenttree,arc,meatywiki,skillmeat,ccdash [--require-review]` — link results back to IntentTree node and request ARC review when servers reachable.
- `rf swarm run --adapters arc_council` — use ARC reviewers to critique discovery/synthesis; degrades to stub when ARC offline.
- `rf doctor` — reports ARC and IntentTree reachability alongside adapter status.

### Rights & Evidence Provenance

Every captured `source_card`/`source_assertion` carries a denormalized,
non-authoritative `rights_summary` mirror (`mirror_is_authoritative: false`)
so rights posture is machine-checkable at the recall path without a live
service. The authoritative record is a separate `rights_record` (plus
`content_reuse_assessment`, `permission_record`, and `rights_failure` when
applicable) — full model and the ten schema-conflict adjudications applied at
port time: `docs/dev/architecture/adr-rights-entity-model.md`.

- `rf rights inspect <entity_id>` — show one entity's `rights_summary`,
  substitutability assessment, and linked `rights_record` synthesis state.
- `rf rights list [--status STATUS]` — enumerate entities by
  `rights_summary.review_status`.
- `rf rights validate [PATHS...] --as-of YYYY-MM-DD` — check `rights_summary`
  mirrors for divergence from their authoritative `rights_record`
  (deterministic; never reads the wall clock).
- `rf rights backfill [PATHS...] [--dry-run]` — write an all-"unknown"
  fail-closed `rights_summary` onto legacy instances missing one (idempotent).

`CLEARED_*`/`counsel_approved`/`attested` rights-clearance values are
human/counsel-only — no agent-writable code path can mint one (governance
guard `no_agent_cleared_rights_value`).

### NotebookLM (NLM)

NLM integrates across four use cases via the `notebooklm` CLI (no REST API). All paths are
fail-soft: with no live `notebooklm login` session they degrade to file candidates / `skip`,
never breaking a run. Runs map to notebooks through a configurable **correlation mode** set in
`foundry.yaml → integrations.notebooklm.correlation_mode`:

- **`project`** (default) — every run sharing a `--project <slug>` reuses one notebook.
- **`run`** — each run gets its own notebook.
- explicit `--notebook-id <id>` on a run overrides both.

Commands:
- `rf swarm run … --adapters notebooklm --project <slug> [--notebook-mode project|run] [--notebook-id ID]` — sourcing: emit RF source cards from NLM synthesis, resolving/creating the run's notebook.
- `rf notebooklm resolve --run <id> [--project S] [--create]` / `status` / `sync --run <id>` — inspect or create the run↔notebook mapping (registry: `registries/notebooklm/notebooks.yaml`); workflows call `resolve --create`.
- `rf writeback <run_id> --targets notebooklm` — render an upload-back candidate and (when a notebook exists, not review-gated, profile online) push RF output back as NLM sources; lineage records notebook + source ids. Not a default target — opt in explicitly.
- `rf intake notebooklm <id> [--project S]` — inbound: ingest an NLM notebook as a new RF idea/intent (mirrors `rf intake intenttree`).
- Auto-sync: the `notebooklm-sync` skill resolves notebooks from the same registry when `NOTEBOOK_RESOLVER_ENABLED=true` (opt-in); `work_sensitive`/`client_sensitive` runs are excluded from silent sync.

Workflows (`.claude/workflows/`): `notebooklm-sourcing`, `notebooklm-report`, `notebooklm-extended`.
Governance: writeback target `notebooklm` permits `personal`/`work_approved`/`client_approved`;
`work_sensitive`/`client_sensitive` are review-gated. The claim ledger stays authoritative — NLM
artifacts are never spliced into report bodies. Full design: `docs/projects/research-foundry/notebooklm-integration-plan.md`.
