---
title: Quickstart
description: Install Research Foundry and run the demo loop in 5 minutes
audience: developers, researchers
tags: getting-started, tutorial, installation
created: 2026-06-19
updated: 2026-06-19
category: guide
status: published
related_documents: [concepts/pipeline.md, reference/cli.md]
---

# Quickstart

Get Research Foundry running in 5 minutes with a self-referential demo loop.

## Install

Research Foundry requires Python 3.9+. Install with [uv](https://docs.astral.sh/uv/):

```bash
uv venv
source .venv/bin/activate  # or `uv run`
uv pip install -e ".[dev]"
```

Or with pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Verify installation:

```bash
rf --version
rf doctor
```

## Initialize a Foundry

Create a new foundry workspace with default structure, schemas, and config:

```bash
rf init ./research-foundry --profile personal
cd research-foundry
```

This creates:

```
research-foundry/
  foundry.yaml                # Configuration
  .env.example                # Secrets template
  .gitignore
  config/                     # Governance, model profiles, schemas
  schemas/                    # YAML artifact schemas
  templates/                  # Markdown/YAML templates
  inbox/                      # Raw ideas capture
  intents/                    # Research intents
  runs/                       # Research runs (append-first)
  registries/                 # Artifact indexes
```

Check your setup:

```bash
rf doctor
```

Expected output:

```
Profile: personal
  Status: OK
  Keys: (offline mode)
  Providers: local/offline
  Writebacks: meatywiki_personal, skillmeat_personal, ccdash_local

Offline mode: enabled (no API keys required)
```

## The Demo Loop

A self-contained, deterministic research workflow. Topic: *"What is the minimum viable architecture for an evidence-backed research swarm?"*

### 1. Capture a raw idea

```bash
rf capture "Research how agentic research workflows should handle evidence bundles" \
  --from manual \
  --sensitivity personal \
  --tag agentic-os \
  --tag research-foundry
```

Output: `inbox/raw_ideas/raw_research_how_agentic_research_workflows_*.md`

### 2. Triage into intent + I-BOM + IntentTree node

```bash
rf triage inbox/raw_ideas/raw_*.md \
  --create-intent \
  --create-ibom \
  --create-tree-node
```

Output:
- `intents/active/<intent_id>.yaml`
- `iboms/active/<ibom_id>.yaml`
- `intenttree/nodes/<node_id>.yaml`

Note the generated intent ID (e.g., `intent_research_20260614_agentic_research_workflows`); you'll use it next.

### 3. Plan the research swarm

```bash
rf plan intent_research_20260614_agentic_research_workflows \
  --depth deep \
  --audience technical \
  --max-cost 5 \
  --freshness 180d
```

Output: `runs/rf_run_YYYYMMDD_*/` with:
- `run.yaml`
- `research_brief.md`
- `swarm_plan.yaml`
- `routing_decision.yaml`

Note the generated run ID (e.g., `rf_run_20260614_agentic_research_workflows`); save it.

### 4. Ingest sources

Add sources from local files, URLs, or notebooks:

```bash
# Local file
rf ingest ./examples/source.pdf \
  --source-type paper \
  --sensitivity personal \
  --run rf_run_20260614_agentic_research_workflows

# URL (if online)
# rf ingest "https://example.com/source" \
#   --source-type official_doc \
#   --sensitivity public \
#   --run rf_run_20260614_agentic_research_workflows

# Notebook (if available)
# rf ingest notebook://my_notebook \
#   --source-type notebook \
#   --sensitivity personal \
#   --run rf_run_20260614_agentic_research_workflows
```

Output: `runs/rf_run_*/sources/src_*.md` (normalized source cards)

### 5. Extract evidence

Run cheap model profile to extract claims:

```bash
rf extract rf_run_20260614_agentic_research_workflows \
  --model-profile rf_extract_cheap
```

Output: `runs/rf_run_*/extractions/ext_*.yaml`

### 6. Build the claim ledger

Map extractions to authoritative claims:

```bash
rf claim-map rf_run_20260614_agentic_research_workflows \
  --from extractions \
  --out claims/claim_ledger.yaml
```

Output: `runs/rf_run_*/claims/claim_ledger.yaml` with all claims tagged `clm_001`, `clm_002`, etc.

### 7. Synthesize the report

Deep model synthesizes a report; may only cite claim ledger IDs:

```bash
rf synthesize rf_run_20260614_agentic_research_workflows \
  --report reports/report_draft.md \
  --model-profile rf_synthesize_deep
```

Output: `runs/rf_run_*/reports/report_draft.md`

### 8. Verify all claims

Ensure every material claim is supported, labeled, or unresolved:

```bash
rf verify rf_run_20260614_agentic_research_workflows \
  --fail-on-unsupported
```

Exit codes:
- **0** – All claims verified; report passes
- **4** – Unsupported material claim detected

### 9. Bundle the evidence

Create immutable snapshot of sources, extractions, claims, and report:

```bash
rf bundle rf_run_20260614_agentic_research_workflows \
  --verify \
  --out evidence_bundle.yaml
```

Output: `runs/rf_run_*/evidence_bundle.yaml`

### 10. Write back to downstream systems

Render outputs for MeatyWiki, SkillMeat, CCDash:

```bash
rf writeback rf_run_20260614_agentic_research_workflows \
  --targets meatywiki,skillmeat,ccdash \
  --require-review
```

Output: `runs/rf_run_*/writebacks/`:
- `meatywiki_writeback.md`
- `skillbom_candidate.md`
- `ccdash_event.yaml`

### 11. Summarize telemetry

Aggregate costs and outcomes for the day:

```bash
rf summarize --period daily
```

Output: Cost, token usage, verification pass/fail, run count.

## Copy-Paste Loop (All at Once)

```bash
# Setup
rf init ./research-foundry --profile personal
cd research-foundry

# Run all steps
INTENT_ID=$(rf capture "Research agentic research workflows" --from manual --sensitivity personal --tag demo | grep intent_id | cut -d: -f2)
rf triage inbox/raw_ideas/raw_*.md --create-intent --create-ibom

RUN_ID=$(rf plan $INTENT_ID --depth deep --audience technical --max-cost 5 | grep run_id | cut -d: -f2)

rf ingest ./examples/source.pdf --source-type paper --sensitivity personal --run $RUN_ID

rf extract $RUN_ID --model-profile rf_extract_cheap
rf claim-map $RUN_ID --from extractions
rf synthesize $RUN_ID --report reports/report_draft.md --model-profile rf_synthesize_deep
rf verify $RUN_ID --fail-on-unsupported
rf bundle $RUN_ID --verify

rf writeback $RUN_ID --targets meatywiki,skillmeat,ccdash

rf summarize --period daily
```

## Next Steps

- **[The Pipeline](concepts/pipeline.md)** — detailed walkthrough of the 11-step flow
- **[The Claim Model](concepts/claim-model.md)** — how claims are tagged and verified
- **[Governance](concepts/governance.md)** — key profiles and runtime gates
- **[CLI Reference](reference/cli.md)** — full `rf` command reference
- **[Run Artifacts](concepts/artifacts.md)** — anatomy of a run directory

## Troubleshooting

### "No module named research_foundry"

Ensure you're running `pytest` under the venv:

```bash
./.venv/bin/python -m pytest  # ✓ Correct
# or
uv run pytest                  # ✓ Correct
# not
pytest                         # ✗ Wrong interpreter
```

### "rf: command not found"

Activate the venv:

```bash
source .venv/bin/activate  # or `uv run rf ...`
```

### "Profile check failed"

Initialize a foundry first:

```bash
rf init ./research-foundry --profile personal
cd research-foundry
rf doctor
```

### NotebookLM offline

NLM is optional. Enable it with `notebooklm login`; offline, the system degrades gracefully.

## See Also

- **Install:** `uv pip install research-foundry`
- **Repo:** https://github.com/miethe/research-foundry
- **Spec:** [docs/projects/research-foundry/](https://github.com/miethe/research-foundry/tree/main/docs/projects/research-foundry)
