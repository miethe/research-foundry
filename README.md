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

## Status: MVP

This is the 7-day MVP described in the spec. Source of truth:

- Spec: [`docs/projects/research-foundry/research-foundry-mvp-spec.md`](docs/projects/research-foundry/research-foundry-mvp-spec.md)
- Plan: [`docs/projects/research-foundry/IMPLEMENTATION_PLAN.md`](docs/projects/research-foundry/IMPLEMENTATION_PLAN.md)

The MVP runs **fully offline and deterministic by default**. The governance guard, schema
validation, claim verification, and the full demo loop require no network and no LLM. Live model
adapters (Claude Agent SDK, GPT Researcher, PaperQA2, OpenCode, LiteLLM router) are **opt-in
extras**, enabled at init time and only used when you ask for them.

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
