# Research Foundry — Research Idea Backlog

> Generated **2026-06-13** by the `rf-idea-backlog-discovery` swarm (92 raw candidates → **55 ideas** across **8 pillars**; 15 dropped). Priority: 19 high / 33 medium / 3 low.

## What this is

A curated set of **evidence-seedable research questions** for Research Foundry. The canonical file is [`research_idea_backlog.yaml`](research_idea_backlog.yaml). Each entry is a **superset** of the RF `raw_idea` + `research_intent` + `intenttree_node` fields, so one idea can drive both:

1. **A swarm run** — `rf capture` → `rf triage` → `rf plan` → discovery swarm → deterministic tail (`extract` → `claim-map` → `synthesize` → `verify` → `bundle`).
2. **An IntentTree import** — pillar → work_package/atomic_task node hierarchy with priority, dependencies, success criteria, and expected artifacts.

Ideas are **research questions answerable with evidence**, not engineering tasks. Schema: [`../schemas/research_idea_backlog.schema.yaml`](../schemas/research_idea_backlog.schema.yaml).

## Quick start

```bash
# Capture every idea as an rf raw idea (then triage/plan/run each):
bash backlog/seed_swarm_runs.sh

# Or one idea at a time:
rf guard check --profile personal
rf capture '<research_question from the YAML>' --from manual --sensitivity personal --tag research-foundry
rf triage inbox/raw_ideas/raw_*.md --create-intent --create-ibom --create-tree-node
rf plan <intent_id> --depth deep --audience technical --max-cost 7 --freshness 365d
```

## Pillars

| Pillar | # | Theme |
|---|---|---|
| **Evidence & Claim Verification** (`pillar_evidence-claim-verification`) | 6 | Claim-to-source traceability, hallucination mitigation, contradiction detection, and source freshness — RF's core differentiator. |
| **Swarm Orchestration & Cost Routing** (`pillar_swarm-orchestration-cost`) | 10 | Adapter selection/comparison, parallel-vs-sequential fan-in, cheap-extract/deep-synthesize model routing, and the real cost economics of multi-step pipelines. |
| **Governance & Multi-Key Safety** (`pillar_governance-multi-key-safety`) | 7 | Work/personal key isolation, sensitivity-tier routing, policy-floor lattices, hook hardening, and credential plumbing for live adapters. |
| **Cross-Tool Integration (Agentic OS)** (`pillar_cross-tool-integration-agentic-os`) | 9 | Event-driven seams between tools, candidate-first/push-second patterns, MCP-vs-subprocess interfaces, writeback contracts, inbound dispatch, and origination/routing layers. |
| **Knowledge Compilation & Retrieval** (`pillar_knowledge-compilation-retrieval`) | 8 | Embedding/vector-store selection, hybrid BM25+vector search, entity consolidation/dedup, edge vocabulary, context budgeting, and file-first vs DB-as-truth architecture. |
| **Evaluation & Quality Scoring** (`pillar_evaluation-quality`) | 6 | Evidence-bundle/report quality scoring, artifact fidelity frameworks, agentic eval harnesses (CI determinism/cost), telemetry-to-quality prediction, and classification confidence calibration. |
| **Reuse & Promotion Governance** (`pillar_reuse-promotion-governance`) | 6 | SkillBOM/agent-bundle promotion lifecycles, artifact provenance/supply-chain standards, prompt/skill versioning, and closed-loop telemetry-to-artifact-improvement. |
| **Capture & Ingestion** (`pillar_capture-ingestion`) | 3 | Unified research-capture harness across heterogeneous AI tools, audio/voice-to-artifact pipelines, mobile/frictionless capture UX, and ambient telemetry. |

## Ideas by pillar

### Evidence & Claim Verification

| Ref | Pri | Idea | Output | Depth |
|---|---|---|---|---|
| RIB-001 | high | Claim segmentation and claim-to-source alignment for automated verification | technical_memo | deep |
| RIB-002 | high | Claim-traceability and hallucination-mitigation: claim-ledger vs RAG, constitutional, self-consistency | literature_review | deep |
| RIB-003 | high | Contradiction detection across heterogeneous source cards | technical_memo | deep |
| RIB-004 | medium | Faithful source-card excerpting and citation-locator precision under copyright constraints | technical_memo | standard |
| RIB-005 | medium | Publishing contradicted/mixed-evidence claims: suppress, highlight, or escalate | brief | standard |
| RIB-006 | medium | Source freshness validation and stale-source detection at scale | technical_memo | standard |

### Swarm Orchestration & Cost Routing

| Ref | Pri | Idea | Output | Depth |
|---|---|---|---|---|
| RIB-007 | high | Cheap-extract vs deep-synthesize: empirical cost/quality of the two-tier model split | technical_memo | deep |
| RIB-008 | high | Claude Agent SDK readiness: skills API, subagent API, and Python package stability | technical_memo | deep |
| RIB-009 | high | Current capability landscape of agentic web/scientific research tools | market_scan | standard |
| RIB-010 | high | GPT Researcher vs PaperQA2 vs Claude Agent SDK as RF discovery adapters | technical_memo | deep |
| RIB-011 | medium | Adapter failure isolation, retry, and partial-result handling in swarm runs | technical_memo | standard |
| RIB-012 | medium | Batch sizes for LLM relationship synthesis: cost vs per-artifact quality | technical_memo | standard |
| RIB-013 | medium | Lightweight ML classifier for per-artifact LLM tier routing | technical_memo | standard |
| RIB-014 | medium | LiteLLM routing strategies for a two-tier model-profile architecture | technical_memo | standard |
| RIB-015 | medium | PaperQA2 agentic RAG vs traditional RAG for citation-grounded scientific QA | literature_review | deep |
| RIB-016 | medium | Parallel vs sequential adapter execution and fan-in merge strategies | technical_memo | standard |

### Governance & Multi-Key Safety

| Ref | Pri | Idea | Output | Depth |
|---|---|---|---|---|
| RIB-017 | high | Sensitivity-aware AI tool routing and tier assignment for writeback targets | technical_memo | deep |
| RIB-018 | high | Work/personal key isolation in multi-profile AI agent systems | technical_memo | deep |
| RIB-019 | medium | Content-level secret and PII scanning as a writeback runtime gate | technical_memo | standard |
| RIB-020 | medium | Human-in-the-loop approval patterns balancing autonomy and reversibility | report | deep |
| RIB-021 | medium | Live-adapter credential plumbing without breaking offline-first guarantees | technical_memo | standard |
| RIB-022 | medium | Policy-floor enforcement via constraint lattices in layered governance overlays | literature_review | deep |
| RIB-023 | medium | Security hardening for Claude Code governance hooks | technical_memo | standard |

### Cross-Tool Integration (Agentic OS)

| Ref | Pri | Idea | Output | Depth |
|---|---|---|---|---|
| RIB-024 | high | Event-driven seam integration for a local-first agentic OS without a shared bus | technical_memo | deep |
| RIB-025 | high | Minimum viable architecture for an evidence-backed research swarm (RF self-validation) | report | deep |
| RIB-026 | high | Origination layers: routing research intent to the right agent/platform | technical_memo | deep |
| RIB-027 | medium | Agentic read/write to file-canonical vaults without breaking write-through | technical_memo | deep |
| RIB-028 | medium | API/data-contract requirements for live writeback to MeatyWiki and CCDash | technical_memo | standard |
| RIB-029 | medium | Candidate-first, push-second file-backed integration architectures | technical_memo | standard |
| RIB-030 | medium | Exposing a CLI tool's operations as MCP tools for agent consumption | technical_memo | standard |
| RIB-031 | medium | Idempotent writeback and reconciliation for re-run research swarms | technical_memo | standard |
| RIB-032 | medium | IntentTree to RF inbound dispatch: preserving research context across handoff | technical_memo | standard |

### Knowledge Compilation & Retrieval

| Ref | Pri | Idea | Output | Depth |
|---|---|---|---|---|
| RIB-033 | high | Embedding model and vector-store strategy for a file-first vault at 1K-100K scale | technical_memo | deep |
| RIB-034 | high | Hybrid BM25+vector and FTS5 ranking for structured Markdown knowledge bases | technical_memo | deep |
| RIB-035 | high | Semantic entity consolidation and auto-merge thresholds in a file-first vault | technical_memo | deep |
| RIB-036 | medium | LLM-wiki vs RAG: when a compiled persistent wiki outperforms stateless retrieval | report | deep |
| RIB-037 | medium | Markdown/Git vs DB-as-truth for reproducible AI knowledge artifacts | technical_memo | standard |
| RIB-038 | medium | Open-source LLM wiki implementations landscape (sage-wiki, CRATE, Binder, LENS, hyalo) | market_scan | standard |
| RIB-039 | low | Context compression and progressive disclosure (L0-L3) for KB query cost | technical_memo | standard |
| RIB-040 | low | Knowledge graph edge vocabulary and relationship semantics audit | technical_memo | standard |

### Evaluation & Quality Scoring

| Ref | Pri | Idea | Output | Depth |
|---|---|---|---|---|
| RIB-041 | high | Non-determinism and cost-control for agentic eval harnesses in CI | technical_memo | deep |
| RIB-042 | high | Quality scoring for evidence bundles and agent-generated reports | report | deep |
| RIB-043 | medium | Artifact fidelity assessment frameworks for AI-generated outputs | literature_review | deep |
| RIB-044 | medium | Golden regression corpus for the claim verifier and quality scorers | technical_memo | standard |
| RIB-045 | medium | Logprob-based vs self-reported confidence for LLM classification | technical_memo | deep |
| RIB-046 | medium | Multi-agent review-council orchestration: independence, groupthink, and quality | report | deep |

### Reuse & Promotion Governance

| Ref | Pri | Idea | Output | Depth |
|---|---|---|---|---|
| RIB-047 | high | Closed-loop feedback from telemetry to artifact-version improvement | literature_review | deep |
| RIB-048 | medium | Agent bundle / context-pack design patterns and handoff schemas | technical_memo | deep |
| RIB-049 | medium | Preventing writeback pollution and memory hygiene in knowledge bases | technical_memo | standard |
| RIB-050 | medium | Provenance/supply-chain standards for agentic artifacts (SkillBOM vs SBOM) | technical_memo | deep |
| RIB-051 | medium | SkillBOM promotion governance: candidate to evaluated to promoted lifecycle | technical_memo | standard |
| RIB-052 | low | Agentic control-plane and artifact-management market landscape | market_scan | deep |

### Capture & Ingestion

| Ref | Pri | Idea | Output | Depth |
|---|---|---|---|---|
| RIB-053 | high | Unified research-capture harness: normalize sources from heterogeneous AI tools | technical_memo | deep |
| RIB-054 | medium | Audio/voice-to-structured-artifact intake without GPU dependence | market_scan | standard |
| RIB-055 | medium | Frictionless capture and retrieval: zero-cognitive-lift PKM design patterns | market_scan | standard |

## How ideas were sourced (provenance)

- meatywiki: Backlog convention: the primary deferred-items tracker is at /Users/miethe/dev/homelab/development/meatywiki/docs/project_plans/deferred-items-backlog.md using DI-NNN identifiers. Open questions in design specs use OQ-N identifiers. Spikes use charter + findings pairs in docs/project_plans/llm_wiki/compilation-engine/spikes/. The RF-local mirror at /Users/miethe/dev/homelab/development/research-foundry/meatywiki/ contains only one source note (what_is_the_minimum_viable_architecture.md) — the main vault is the canonical source. Research candidates are ordered roughly by strategic impact to the Agentic-OS vision: embedding/vector infrastructure, entity consolidation, and the origination-layer design are the highest-signal gaps. The Claude Agent SDK skills and subagents questions have natural expiry dates tied to SDK release cadence and should be researched before Q4 2026.
- rf_docs: RF does NOT define a single centralized "backlog" file. Instead, the backlog convention is distributed: each skill's SPEC.md contains a Section 4 "Enhancement Backlog" with stable BL-N numbered entries (candidate | planned | deferred | will-not-fix statuses). This convention is defined at /Users/miethe/dev/homelab/development/research-foundry/.claude/specs/artifact-structures/skill-spec-convention.md §2.4 and mirrored at /Users/miethe/dev/homelab/development/research-foundry/.claude/context/key-context/spec-backed-skills-convention.md. The authoritative SPEC.md files with active backlogs found are: /Users/miethe/dev/homelab/development/research-foundry/.claude/skills/research-foundry-swarm/SPEC.md (BL-1 through BL-5), /Users/miethe/dev/homelab/development/research-foundry/.claude/skills/workflow-authoring/SPEC.md (BL-1 through BL-5), /Users/miethe/dev/homelab/development/research-foundry/.claude/skills/intenttree-cli/SPEC.md (BL-1 through BL-6), /Users/miethe/dev/homelab/development/research-foundry/.claude/skills/meatywiki-suite/SPEC.md (BL-1 through BL-8). There is no single backlog.yaml or backlog.md file at the project root or in .claude/.
- rf_runs: All candidates were mined from the single active intent/run, the spec, the bidirectional integrations plan, the implementation plan, and the agent memory files. The research-foundry/intents/{paused,completed,archived} directories are empty (only .gitkeep). The inbox raw_ideas directory contains only the one converted idea. There are no additional runs beyond rf_run_20260613_what_is_the_minimum_viable_architecture. The existing backlog/intent convention uses intents/active/*.yaml as the canonical queue. The research_brief.md 'open questions' section says 'None recorded', and claim_ledger.yaml unresolved_questions is empty — indicating the first run was deliberately shallow/demo. The richest source of follow-on questions came from spec §17 (Risks and open questions table), the adapter contracts in §13, the model routing in §8, and the bidirectional integrations plan open-decisions list (§5).
- ideation: Sources explored: MeatyIdeas (README, docs/init-prd.md, docs/SEED.md, docs/init_implementation.md, docs/init-2-impl.md, docs/init-2-output.md, docs/BUNDLE_SCHEMA.md, app/api/search.py) and PKM MeatyBrain vault (App Ideas/Work/Agentic Control Plane/LLM Wiki/* including LLM-Wiki.md, llm-wiki-eval.md, llm-wiki-design-spec.md, llm-wiki-impl-spec.md, llm-wiki-workflow-os-addendum.md, compilation-engine-spec.md, meatywiki-overview.md; App Ideas/Ideations/consolidated_notes.md).

The Agentic Control Plane PKM backup directory at /Users/miethe/dev/homelab/development/claude-backup/projects/-Users-miethe-Documents-Other-PKM-MeatyBrain-App-Ideas-Work-Agentic-Control-Plane-LLM-Wiki/ contained only a .session-aliases file (no content) — the actual content lives at /Users/miethe/Documents/Other/PKM/MeatyBrain/App Ideas/Work/Agentic Control Plane/LLM Wiki/.

No existing Research Foundry backlog convention was discovered in these source directories; the RF backlog would need to be checked in the research-foundry project itself.
- agentic_os: Backlog convention: this ecosystem does not have a dedicated RF research backlog file. The closest analog is the AI-workflow audit's improvement backlog (08-top-10-improvements.md) and the IntentTree deferred-items-backlog.md. Open questions (OQ-NN) are the primary signpost for research-worthy gaps. Key source locations for future mining: /Users/miethe/dev/homelab/development/meatywiki/docs/project_plans/reports/audits/ai-workflow-audit/ (the richest single source of cross-project OQs), /Users/miethe/dev/homelab/development/agentic_meta_dev/docs/RECONCILIATION.md (D1-D5 open decisions), /Users/miethe/dev/homelab/development/intenttree/docs/project_plans/deferred-items-backlog.md (DI-001..030 operational deferrals), and /Users/miethe/dev/homelab/development/agentic-research/docs/project_plans/human-briefs/ (ARC OQ ledgers). MAP (migration assistant) and signal_to_system (Astro starter shell) are peripheral to the AOS and yielded no research candidates. MeatyPrompts (prompt effectiveness / PSR metric) has latent research potential around cross-model prompt evaluation but is pre-production with no confirmed user data.

## Relationship to existing backlog conventions

- RF per-skill SPEC.md section 4 'Enhancement Backlog' (BL-N ids) — engineering enhancements, not research questions.
- MeatyWiki docs/project_plans/deferred-items-backlog.md (DI-NNN) — deferred implementation items.
- Design-spec Open Questions use OQ-N ids. This file uses RIB-NNN for research ideas (new, complementary).

## Completeness pass

The discovery critic flagged 6 potential gap themes. A manual audit found **each was already covered** by an authored idea (the critic judged from titles only), so no supplemental entries were added:

| Critic-flagged gap | Already covered by |
|---|---|
| Claim segmentation & claim-to-source alignment (producing claim_ids) | `idea_claim-segmentation-source-alignment` |
| Source-card extraction fidelity & citation-locator precision under copyright/excerpt constraints | `idea_source-card-extraction-fidelity` |
| Verifier self-validation: golden/regression corpus & false-negative measurement | `idea_verifier-golden-corpus-regression` |
| Content-level secret & PII scanning as a writeback runtime gate | `idea_secret-pii-writeback-scanning` |
| Writeback idempotency, reconciliation & conflict resolution for re-run swarms | `idea_writeback-idempotency-reconciliation` |
| Adapter resilience: failure isolation, retry, timeout, partial-result handling | `idea_adapter-failure-retry-resilience` |

> Critic assessment: Strong, well-distributed backlog: 49 ideas, no duplicate ids, every pillar populated (Swarm Orchestration 9, Knowledge Compilation 8, Cross-Tool 8, Reuse/Promotion 6, Governance 6, Evaluation 5, Evidence/Claim 4, Capture 3). Coverage is broadest exactly where the spec is deepest (model routing, adapters, retrieval, integration seams). The most material gaps cluster around the system's own differentiator — the claim verifier and the evidence-extraction pipeline that feeds it. Per MVP spec sec 18, the claim verifier is the load-bearing component ('implement the claim verifier before fancy swarm orchestration'), yet the backlog covers the verification *landscape* and downstream publication policy but NOT the upstream mechanics: (a) how to segment a draft into 'material claims' and align each to a source card (sec 12.1/12.3 material_claims_have_claim_ids + supported_claims_have_source_cards are hard error gates), (b) faithful source-card excerpting / citation-locator precision under copyright constraints (sec 6.8, sec 17 'source cards become too heavy'), and (c) a golden regression corpus to prove the verifier itself is correct. Secondary gaps: content-level secret/PII scanning as a writeback gate (sec 7.2 non-negotiable, distinct from key-isolation/hook-hardening which are already covered), and writeback idempotency/reconciliation for re-run swarms (sec 17 'writebacks pollute memory'; candidate-first idea covers architecture but not dedup semantics). Adapter failure/retry/normalization resilience (sec 17 'tool APIs change quickly') is partly implied by parallel-vs-sequential fan-in but not its own question. I authored 6 additional entries targeting the four highest-value gaps plus two adjacent ones, all assigned to existing pillars.

## Dropped candidates (out of scope / low potential)

- **What approaches exist for knowledge-system origination layers / SME persona consultant agent architecture** — The SME-persona/consultant agent-memory question (MemGPT/Zep/LangMem) is a long-horizon vision item for MeatyWiki's far future, weakly tied to RF's evidence-first mission. The origination-layer half is captured in idea_origination-layer-routing; the agent-memory half is out of near-term scope.
- **How should lens scores (freshness, relevance, novelty, clarity) be designed to be facet-contextual?** — Narrow MeatyWiki storage-model decision (denormalized vs join table vs JSONB) for a specific F5 feature. Low leverage to RF's mission, minimal external evidence base, better resolved by internal design spike than research.
- **What suggested-link UX patterns balance surfacing latent connections with avoiding false-positive noise?** — Downstream UX question that depends on idea_embedding-vector-store-strategy resolving first; deferred to MeatyWiki v2.2. Low immediate leverage and overlaps with the broader retrieval work.
- **What are the best skill versioning and rollback patterns for LLM instruction bundles?** — Self-rated low research_potential; a small, well-understood ops problem (git history / hashed registers) with limited external evidence to mine. Better solved by convention than a research bundle.
- **What is the optimal status-callback cadence for RF-to-IntentTree progress updates?** — Self-rated low; a minor design trade-off (every-stage vs milestone) decidable by judgment in minutes. No research bundle warranted.
- **How should ExecutionReport data from Claude Code workflow runs be ingested into CCDash?** — Specific internal plumbing/integration task, not a research question; the integration point is already decided (ExecutionReport). Engineering, not evidence-gathering.
- **Graph/backlinks UI for knowledge portals: when to render relationship graphs** — Self-rated skim/medium; specs already converge on 'avoid full graph viz early.' Low marginal value and out of RF's core scope.
- **Notion/Confluence/Drive importers for Markdown-native knowledge systems** — Self-rated low; explicitly deferred post-MVP across specs and listed as a non-goal. Importer engineering complexity, not a high-leverage research question.
- **Desktop activity telemetry for ambient context capture** — Speculative ambient-capture ideation with privacy overhead and weak tie to RF's evidence-first control-plane mission. Premature relative to core capture/ingestion work.
- **AI writing style personalization: extracting a writer's voice for blog generation** — Blog-workflow personalization peripheral to RF's research-control-plane mission; medium potential but low strategic leverage.
- **Git submodule vs linked worktree for artifacts repos** — Self-rated low; a narrow MeatyIdeas git-ops default already chosen. Decidable by a short spike, not a research bundle.
- **Universal flat Item model vs hierarchical tree model for an agentic work OS** — IntentTree-specific data-modeling reconciliation (D2). Important to that project but tangential to RF's mission; better handled in IntentTree's own planning thread.
- **Workflow tiering and governance-based promotion systems in agentic SDLC** — Internal AOS workflow-registry tier-model conflict (OQ-17/18); largely an internal taxonomy reconciliation decision rather than an externally-researchable evidence gap. Overlaps conceptually with idea_skillbom-promotion-governance.
- **Live cross-feature work register that multiple agents can query** — Self-rated skim; a workflow-wiki/CCDash internal tracking-index implementation problem with limited external evidence. Engineering pattern choice, not research.
- **Multi-dimensional priority scoring models for agentic task scheduling** — IntentTree M2-specific scoring-formula grounding; medium potential but peripheral to RF's evidence/claim mission and largely an internal product calibration question.
