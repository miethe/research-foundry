---
title: About Research Foundry
description: Project status, integrations, long-term direction, and key links
audience: all
tags: overview, status, integrations, roadmap
created: 2026-06-19
updated: 2026-06-19
category: reference
status: published
related_documents: [why.md]
---

# About Research Foundry

## Status: MVP

Research Foundry is a **7-day MVP** — fully functional, tested (102+ tests), and ready for experimental use. The core loop (capture → triage → plan → ingest → extract → claim-map → synthesize → verify → bundle → writeback → summarize) runs deterministically, offline-first, with all model adapters as opt-in extras.

**Key achievements:**
- Markdown/YAML substrate fully implemented
- Claim ledger and verification enforced
- Offline default (no API keys required to run)
- Schema validation and governance gates working
- Integration surfaces defined and partially implemented
- Full `rf` CLI in place

**Status symbols:**
- ✓ Core MVP (capture through writeback)
- ✓ Claim ledger and verification
- ✓ Offline-first determinism
- ✓ Governance profiles (personal, work_approved, client_approved, offline_only)
- ✓ Integration surfaces (MeatyWiki, SkillMeat, CCDash, IntentTree)
- ⚠ NotebookLM integration (implemented offline; live testing pending)
- ⚠ ARC council reviews (adapter stubbed; awaiting live ARC session)
- ⚠ External LLM adapters (contracts defined; implementation in progress)

## Architecture Overview

Research Foundry is a thin, file-backed control plane:

- **Frontend:** `rf` CLI (Python)
- **Core:** `research_foundry` package (Python 3.11+)
- **Substrate:** Markdown/YAML on disk (no database)
- **Integration targets:** MeatyWiki, SkillMeat, CCDash, IntentTree, ARC, NotebookLM
- **Execution:** Local + opt-in remote via adapters (Claude Agent SDK, GPT Researcher, PaperQA2, LiteLLM router)

## Key Principles

1. **Evidence-first.** Start with intents and sources, not prompts.
2. **The claim ledger is authority.** Not any model or tool.
3. **Markdown/YAML as source of truth.** Human-readable, diff-friendly, no black boxes.
4. **Cheap extract, expensive synthesize.** Local/free for evidence extraction; pay for deep reasoning only.
5. **Governance is a runtime gate.** Enforced deterministically before execution.
6. **The swarm is disposable, the bundle is durable.** Agents are rerunnable; evidence snapshots persist.

## Integration Surfaces

### MeatyWiki

**Purpose:** Personal and team knowledge base.

**Writebacks:** Research findings render as MeatyWiki articles with source links and claim lineage. Targets:
- `meatywiki_personal` — personal research (default)
- `meatywiki_internal` — work-internal (work_approved profile)

**Live:** File-based candidate generation + push workflow
**Status:** Implemented; awaiting live MeatyWiki session for validation

### SkillMeat

**Purpose:** Skill catalog and learning outcomes registry.

**Writebacks:** Research that identifies or validates new skills renders as SkillBOM candidates. Targets:
- `skillmeat_personal` — personal learning
- `skillmeat_internal` — work skills

**Live:** File-based candidate generation + review gate
**Status:** Implemented; SkillBOM structure validated

### CCDash

**Purpose:** Centralized control dashboard for cost tracking and observability.

**Writebacks:** Token costs, claim statistics, verification outcomes, run metrics stream to CCDash events.

**Live:** YAML event payload generation
**Status:** Implemented; awaiting CCDash telemetry intake

### IntentTree

**Purpose:** Distributed research task orchestration.

**Bidirectional:**
- `rf intake intenttree <node_id>` — ingest a dispatched task from IntentTree
- `rf status push --to intenttree` — push research progress updates back

**Live:** API contracts drafted; awaiting live IntentTree node connection
**Status:** Partially implemented; offline-capable with fallback

### ARC (Anthropic Research Council)

**Purpose:** Live council review for contradiction detection and synthesis critique.

**Workflows:**
- `rf council <run_id> --via arc` — request live ARC reviews (vs. local stub)
- `rf swarm run --adapters arc_council` — use ARC as a critic during swarm

**Live:** Stub workflow in place; awaits live ARC connection
**Status:** Scaffolded; offline fallback to local workflow

### NotebookLM

**Purpose:** Notebook-based sourcing and synthesis.

**Bidirectional:**
- `rf swarm run --adapters notebooklm --project <slug>` — emit RF source cards from NLM synthesis
- `rf intake notebooklm <notebook_id>` — ingest NLM notebook as RF idea
- `rf writeback <run_id> --targets notebooklm` — push research findings back as NLM sources

**Live:** Requires active `notebooklm login` session; degrades to stub when offline
**Correlation modes:** `project` (reuse notebook across runs), `run` (one notebook per run), or explicit `--notebook-id`
**Status:** Fully implemented offline; first live run is remaining validation

## Learning Resources

### Documentation

- **[Why Research Foundry](why.md)** — the problem and thesis
- **[The Pipeline](concepts/pipeline.md)** — end-to-end flow
- **[The Claim Model](concepts/claim-model.md)** — claim-status tagging and verification
- **[Governance](concepts/governance.md)** — key profiles and runtime gates
- **[Artifacts](concepts/artifacts.md)** — run directory anatomy
- **[Quickstart](quickstart.md)** — install and demo loop
- **[CLI Reference](reference/cli.md)** — complete `rf` command reference
- **[Run Artifacts](reference/run-artifacts.md)** — per-file reference

### Specification & Plans

- **MVP Spec:** `docs/projects/research-foundry/research-foundry-mvp-spec.md` (authoritative, 19 sections)
- **Implementation Plan:** `docs/projects/research-foundry/IMPLEMENTATION_PLAN.md`
- **Service Contract:** `docs/projects/research-foundry/SERVICE_CONTRACT.md` (Wave 2 service API)

### Real-World Examples

Two AARs document live runs:

1. **Swarm Orchestration Cost Runs** (`docs/projects/research-foundry/aars/swarm-orchestration-cost-runs-aar-2026-06-13.md`)  
   First 4 demonstration runs: research questions, token costs, claim statistics, verification outcomes.

2. **Roots Wave High-Priority Runs** (`docs/projects/research-foundry/aars/roots-wave-high-priority-runs-aar-2026-06-14.md`)  
   10-item root-cause research wave: determinism, cost control, artifact feedback loops, semantic entity consolidation, sensitivity-aware routing, embedding strategies, hybrid ranking, token distribution analysis, contradiction detection, closed-loop telemetry.

## Getting Started

1. **Read** [Why Research Foundry](why.md) (3 min)
2. **Run** [Quickstart](quickstart.md) (5 min)
3. **Explore** [The Pipeline](concepts/pipeline.md) (10 min)
4. **Reference** [CLI](reference/cli.md) as you work

## Long-Term Direction

Research Foundry is positioned to become:

- **A research orchestration platform** for teams running agentic workflows at scale
- **The claim ledger as a durable, auditable asset** — research never gets lost; evidence is forever traceable
- **Integrated deeply into Agentic OS** — bi-directional with IntentTree (task dispatch), ARC (council reviews), MeatyWiki (knowledge base), SkillMeat (capability registry), CCDash (observability)
- **Multi-model and multi-tool agnostic** — cheap extraction via Haiku or local models, deep synthesis via Opus or specialist research tools (GPT Researcher, PaperQA2), all normalized into the same Markdown/YAML substrate
- **Cost-optimized by default** — with tool-use filtering, token budgets per run, and determinism enforcement to catch wasteful patterns early

## Community & Contributing

Research Foundry is built as part of the Agentic OS ecosystem. To contribute:

1. Read [CONTRIBUTING.md](https://github.com/miethe/research-foundry/blob/main/CONTRIBUTING.md) (linked in repo)
2. Join discussions on the [Discord](https://discord.gg/anthropic-research) (Agentic OS channel)
3. File issues or PRs on [GitHub](https://github.com/miethe/research-foundry)

## License

Apache 2.0

## Contact

- **Author:** Nick Miethe
- **Email:** miethe.dev@gmail.com
- **GitHub:** https://github.com/miethe/research-foundry
- **Agentic OS LAN:** 10.42.10.76 (docs, integrations, team infrastructure)

## Key Links

| Resource | URL |
|----------|-----|
| Repository | https://github.com/miethe/research-foundry |
| MVP Spec | docs/projects/research-foundry/research-foundry-mvp-spec.md |
| Implementation Plan | docs/projects/research-foundry/IMPLEMENTATION_PLAN.md |
| Service Contract | docs/projects/research-foundry/SERVICE_CONTRACT.md |
| Swarm Cost AAR | docs/projects/research-foundry/aars/swarm-orchestration-cost-runs-aar-2026-06-13.md |
| Roots Wave AAR | docs/projects/research-foundry/aars/roots-wave-high-priority-runs-aar-2026-06-14.md |
| MeatyWiki | http://10.42.10.76:3020 (LAN) |
| IntentTree | http://10.42.10.76:5173 (LAN) |
| CCDash | http://10.42.10.76:3010 (LAN) |

## FAQ

### Does Research Foundry require an internet connection?

No. The MVP runs fully offline by default. Live adapters (Claude API, external search, IntentTree, etc.) are opt-in and degrade gracefully when unreachable.

### Can I use this with my own LLM?

Yes. Define custom model profiles in `config/model_profiles.yaml`. LiteLLM router is supported for multi-provider routing. Local Ollama models work offline.

### What if I have work-sensitive data?

Use the `work_approved` key profile. Governance gates enforce that work keys cannot be used for personal research and personal keys cannot leak into work writebacks. Sensitive operations require human review before publishing.

### How much does a typical run cost?

Depends on research depth and source count. The Swarm Cost AAR documents real runs: shallow research ~$0.01–0.05, medium ~$0.10–0.50, deep ~$1.00–5.00. Extraction is cheap (local/free); synthesis costs the most. Token budgets can cap spend per run.

### Can I integrate Research Foundry with my existing tools?

Yes. Writebacks go to MeatyWiki, SkillMeat, CCDash, IntentTree, and ARC. Intake workflows pull from IntentTree and NotebookLM. Define custom adapters in `src/research_foundry/adapters/`.

### What's the roadmap?

Short term: validate live integrations (NotebookLM, ARC, IntentTree). Medium term: add multi-model orchestration (Opus for planning, Sonnet for synthesis, Haiku for extraction). Long term: distributed research networks and federated claim ledgers.

---

## See Also

- [Why Research Foundry](why.md)
- [GitHub Repository](https://github.com/miethe/research-foundry)
- [Specification](https://github.com/miethe/research-foundry/tree/main/docs/projects/research-foundry)
