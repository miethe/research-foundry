#!/usr/bin/env bash
# Seed Research Foundry swarm runs from the research-idea backlog.
# Generated: 2026-06-13. One `rf capture` per backlog idea (RIB-NNN).
# After capturing, triage + plan + run the swarm + deterministic tail per idea (see backlog/README.md).
set -euo pipefail

rf guard check --profile personal

# ===== Evidence & Claim Verification =====
# RIB-001 [high] Claim segmentation and claim-to-source alignment for automated verification
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'How can a draft report be reliably decomposed into discrete material claims and each claim aligned to a supporting source card (or labeled inference/speculation) so the claim verifier'\''s hard gates can be enforced?' --from manual --sensitivity personal --tag research-foundry --tag claim-verification --tag attribution --tag entailment --tag claim-ledger --backlog-idea-ref RIB-001

# RIB-002 [high] Claim-traceability and hallucination-mitigation: claim-ledger vs RAG, constitutional, self-consistency
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 365d  (artifact: literature_review)
rf capture 'What does the empirical literature say about unsupported-claim/hallucination rates in multi-step LLM synthesis, what existing frameworks implement claim-to-source traceability, and how does a claim-ledger + verifier architecture compare to RAG, constitutional AI, and self-consistency for reducing material unsupported claims?' --from manual --sensitivity personal --tag research-foundry --tag claim-verification --tag hallucination --tag verifiable-ai --tag rag --backlog-idea-ref RIB-002

# RIB-003 [high] Contradiction detection across heterogeneous source cards
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'What NLP/LLM approaches most effectively detect factual contradictions between extracted evidence points across heterogeneous source types (web, PDF, papers, notes) for building a contradiction_log, and how should LLM-maintained knowledge graphs flag stale/orphaned/conflicting claims at acceptable precision and cost?' --from manual --sensitivity personal --tag research-foundry --tag contradiction-detection --tag evidence-quality --tag knowledge-graph --tag fact-checking --backlog-idea-ref RIB-003

# RIB-004 [medium] Faithful source-card excerpting and citation-locator precision under copyright constraints
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'What extraction approach yields faithful, locator-precise source cards from heterogeneous web and PDF sources without over-storing full text or producing untrustworthy citations?' --from manual --sensitivity personal --tag research-foundry --tag source-cards --tag extraction --tag citations --tag copyright --backlog-idea-ref RIB-004

# RIB-005 [medium] Publishing contradicted/mixed-evidence claims: suppress, highlight, or escalate
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: brief)
rf capture 'What governance policies and report-surface patterns best handle contradicted and mixed-evidence claims at publication time, and what evidence exists on whether highlighting vs suppressing conflicting sources improves reader trust and decision quality?' --from manual --sensitivity personal --tag research-foundry --tag claim-status --tag evidence-quality --tag source-ranking --tag contradiction --backlog-idea-ref RIB-005

# RIB-006 [medium] Source freshness validation and stale-source detection at scale
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'What methods do existing research/evidence-synthesis systems use to detect, flag, and re-validate stale or superseded sources over time, and how do they apply to RF'\''s source-card model and 180-day default freshness window?' --from manual --sensitivity personal --tag research-foundry --tag source-freshness --tag stale-data --tag source-cards --tag knowledge-decay --backlog-idea-ref RIB-006

# ===== Swarm Orchestration & Cost Routing =====
# RIB-007 [high] Cheap-extract vs deep-synthesize: empirical cost/quality of the two-tier model split
#   -> plan: --depth deep --audience technical --max-cost 8 --freshness 180d  (artifact: technical_memo)
rf capture 'What is the empirical accuracy differential and cost breakdown between cheap (Haiku/Flash-class) and expensive (Opus/o3-class) models for structured extraction vs synthesis across compilation/research pipeline stages, and at what token volume and quality threshold does the two-tier split pay off vs a flat policy?' --from manual --sensitivity personal --tag research-foundry --tag model-routing --tag cost-quality --tag extraction --tag batch-processing --backlog-idea-ref RIB-007

# RIB-008 [high] Claude Agent SDK readiness: skills API, subagent API, and Python package stability
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'What is the current release state, versioning policy, and Python API surface of the Claude Agent SDK — specifically whether it exposes a stable native skills/resources API and a documented parent-child subagent API — and do billing, latency, observability, and stability justify migrating from plain-text prompt injection and implementing RF'\''s real-mode claude_agent_sdk adapter?' --from manual --sensitivity personal --tag research-foundry --tag claude-agent-sdk --tag skills-api --tag subagents --tag stability --backlog-idea-ref RIB-008

# RIB-009 [high] Current capability landscape of agentic web/scientific research tools
#   -> plan: --depth standard --audience technical --max-cost 6 --freshness 180d  (artifact: market_scan)
rf capture 'As of mid-2026, what are the capabilities, APIs, output formats, pricing, governance limits, and reliability of GPT Researcher, Perplexity Deep Research, Gemini Deep Research, and PaperQA2, and how do they map to RF'\''s adapter-contract requirements for prioritizing real-mode implementation?' --from manual --sensitivity personal --tag research-foundry --tag landscape --tag market-scan --tag gpt-researcher --tag perplexity --backlog-idea-ref RIB-009

# RIB-010 [high] GPT Researcher vs PaperQA2 vs Claude Agent SDK as RF discovery adapters
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'How do GPT Researcher, PaperQA2, and the Claude Agent SDK compare on source recall, citation accuracy, cost-per-source-card/claim, governance compliance, and integration complexity when used as the extraction layer in RF'\''s governed pipeline, and what adapter-selection rules follow?' --from manual --sensitivity personal --tag research-foundry --tag gpt-researcher --tag paperqa2 --tag claude-agent-sdk --tag adapter --backlog-idea-ref RIB-010

# RIB-011 [medium] Adapter failure isolation, retry, and partial-result handling in swarm runs
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'How should RF isolate, retry, and degrade gracefully when an individual research adapter fails, times out, or returns partial results mid-swarm?' --from manual --sensitivity personal --tag research-foundry --tag swarm --tag adapters --tag resilience --tag retry --backlog-idea-ref RIB-011

# RIB-012 [medium] Batch sizes for LLM relationship synthesis: cost vs per-artifact quality
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 365d  (artifact: technical_memo)
rf capture 'At what batch sizes does LLM relationship synthesis achieve cost-optimal throughput without degrading per-artifact relationship count/quality, and is batch synthesis compatible with a strict linear (non-DAG) workflow constraint?' --from manual --sensitivity personal --tag research-foundry --tag batch-synthesis --tag cost-optimization --tag relationship-extraction --backlog-idea-ref RIB-012

# RIB-013 [medium] Lightweight ML classifier for per-artifact LLM tier routing
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'Given intake-time features (artifact type, length, structural richness, source hint), which lightweight classification architectures predict the optimal LLM tier with sub-5ms overhead, and what minimum labeled dataset size is needed for reliable calibration?' --from manual --sensitivity personal --tag research-foundry --tag llm-routing --tag classification --tag cost-optimization --tag model-selection --backlog-idea-ref RIB-013

# RIB-014 [medium] LiteLLM routing strategies for a two-tier model-profile architecture
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'Which LiteLLM routing strategies (cost-based, lowest-latency, simple-shuffle, load-balancing) best fit a two-tier extract-cheap/synthesize-deep profile architecture, and how does the broader LLM provider-abstraction landscape (LiteLLM, pydantic-ai, instructor) compare for sync-first, mypy-strict pipelines?' --from manual --sensitivity personal --tag research-foundry --tag litellm --tag model-routing --tag provider-abstraction --tag cost-optimization --backlog-idea-ref RIB-014

# RIB-015 [medium] PaperQA2 agentic RAG vs traditional RAG for citation-grounded scientific QA
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 365d  (artifact: literature_review)
rf capture 'How does PaperQA2'\''s agentic RAG (re-ranking, in-text citations, iterative retrieval) compare to standard vector-store RAG on scientific-literature QA for citation accuracy, hallucination rate, and latency, and what does this imply for RF'\''s scientific adapter and its evaluation criteria?' --from manual --sensitivity personal --tag research-foundry --tag paperqa2 --tag rag --tag scientific-literature --tag benchmarking --backlog-idea-ref RIB-015

# RIB-016 [medium] Parallel vs sequential adapter execution and fan-in merge strategies
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 365d  (artifact: technical_memo)
rf capture 'What are the correctness, deduplication, cost, and latency trade-offs between sequential and parallel adapter execution in rf swarm run, and which fan-in merge strategies best produce a deduplicated source_candidates set from heterogeneous adapter outputs?' --from manual --sensitivity personal --tag research-foundry --tag swarm --tag parallelism --tag deduplication --tag orchestration --backlog-idea-ref RIB-016

# ===== Governance & Multi-Key Safety =====
# RIB-017 [high] Sensitivity-aware AI tool routing and tier assignment for writeback targets
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 365d  (artifact: technical_memo)
rf capture 'What frameworks and enforcement patterns do enterprises use to classify task sensitivity and route AI workloads to appropriate providers, and which data-sensitivity tiers (personal, work_approved, client_approved) should be permitted to push to RF writeback targets like ARC and IntentTree, with what threat-model justification?' --from manual --sensitivity personal --tag research-foundry --tag sensitivity --tag data-classification --tag llm-routing --tag governance --backlog-idea-ref RIB-017

# RIB-018 [high] Work/personal key isolation in multi-profile AI agent systems
#   -> plan: --depth deep --audience technical --max-cost 6 --freshness 365d  (artifact: technical_memo)
rf capture 'What published security frameworks, threat models, and runtime-enforcement mechanisms address work/personal API-key isolation and cross-profile credential leakage in multi-profile agentic systems, where have prior implementations failed, and how do they validate or improve RF'\''s four-profile key-governance model?' --from manual --sensitivity personal --tag research-foundry --tag key-isolation --tag governance --tag credential-security --tag boundary --backlog-idea-ref RIB-018

# RIB-019 [medium] Content-level secret and PII scanning as a writeback runtime gate
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'How should RF detect secrets and PII inside report/evidence content and block or redact before writeback, as a runtime gate distinct from key isolation?' --from manual --sensitivity personal --tag agentic-os --tag governance --tag secret-scanning --tag pii --tag writeback --backlog-idea-ref RIB-019

# RIB-020 [medium] Human-in-the-loop approval patterns balancing autonomy and reversibility
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: report)
rf capture 'What approval-gate designs (cost-cap triggers, reversibility classification, policy flags, escalation tiers) best prevent irreversible agentic actions while minimizing operator interruption in continuous delivery, and how do LangChain, Temporal, and Claude Code handle this?' --from manual --sensitivity personal --tag research-foundry --tag hitl --tag approval-gates --tag reversibility --tag agentic-safety --backlog-idea-ref RIB-020

# RIB-021 [medium] Live-adapter credential plumbing without breaking offline-first guarantees
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'What credential-management, secret-injection, and network-isolation patterns allow RF'\''s live adapter modes to be enabled securely without compromising the offline-deterministic default or violating key-profile governance?' --from manual --sensitivity personal --tag research-foundry --tag credentials --tag security --tag adapters --tag offline-first --backlog-idea-ref RIB-021

# RIB-022 [medium] Policy-floor enforcement via constraint lattices in layered governance overlays
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 365d  (artifact: literature_review)
rf capture 'What formal models (lattice-based partial orders, capability sets, ranked constraint systems) best enforce policy floors in a multi-layer governance overlay stack where overlays may only tighten constraints, and how do production access-control systems implement this for the ARC rank-lattice enhancement?' --from manual --sensitivity personal --tag research-foundry --tag policy-floors --tag lattice --tag governance --tag access-control --backlog-idea-ref RIB-022

# RIB-023 [medium] Security hardening for Claude Code governance hooks
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'What specific vulnerabilities arise when Claude Code PreToolUse/PostToolUse hooks run with full user permissions, and what input-validation, path-traversal-prevention, and secret-handling practices are evidence-backed for safely implementing governance hooks?' --from manual --sensitivity personal --tag claude-code-hooks --tag governance --tag security --tag agentic-os --backlog-idea-ref RIB-023

# ===== Cross-Tool Integration (Agentic OS) =====
# RIB-024 [high] Event-driven seam integration for a local-first agentic OS without a shared bus
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'What patterns (file-watch hooks, post-merge triggers, SSE, event sourcing) most effectively close manual cross-tool handoff seams (research→vault, vault→graph, telemetry→governance) in a local-first agentic OS without introducing a centralized message broker?' --from manual --sensitivity personal --tag research-foundry --tag event-driven --tag seam-integration --tag local-first --tag file-watch --backlog-idea-ref RIB-024

# RIB-025 [high] Minimum viable architecture for an evidence-backed research swarm (RF self-validation)
#   -> plan: --depth deep --audience technical --max-cost 8 --freshness 365d  (artifact: report)
rf capture 'What components, schemas, agent roles, and execution loop are truly required for a functional evidence-backed, claim-traceable research swarm inside an Agentic OS, what can be safely deferred post-MVP, and how does a deep scan of agentic-research literature validate or challenge RF'\''s current architecture choices?' --from manual --sensitivity personal --tag research-foundry --tag agentic-os --tag research-swarm --tag evidence-bundle --tag architecture --backlog-idea-ref RIB-025

# RIB-026 [high] Origination layers: routing research intent to the right agent/platform
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'What architectures define an agentic '\''origination layer'\'' that receives a research intent, generates platform-specific prompt packages, and routes to the right agent/external tool, and what are the trade-offs of rule-based routing vs LLM intent extraction vs ML classifiers — including hard cost caps, Agent SDK, CLI exec, or hybrid execution-packet models?' --from manual --sensitivity personal --tag research-foundry --tag origination-layer --tag research-routing --tag control-plane --tag execution-packets --backlog-idea-ref RIB-026

# RIB-027 [medium] Agentic read/write to file-canonical vaults without breaking write-through
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'What patterns do PKM systems use for programmatic agent read/write while keeping files canonical, and what failure modes (corruption, drift, conflicting writes) arise when agents write to file-backed vaults concurrently with humans — reconciling the origination layer with the write-through invariant?' --from manual --sensitivity personal --tag research-foundry --tag agentic-write --tag file-canonical --tag pkm --tag write-through --backlog-idea-ref RIB-027

# RIB-028 [medium] API/data-contract requirements for live writeback to MeatyWiki and CCDash
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'What stable API contracts, auth patterns, and data schemas must a live MeatyWiki API and CCDash endpoint expose for RF'\''s writeback service to push bundles programmatically, and what prior art exists in PKM-tool APIs?' --from manual --sensitivity personal --tag research-foundry --tag meatywiki --tag ccdash --tag api --tag writeback --backlog-idea-ref RIB-028

# RIB-029 [medium] Candidate-first, push-second file-backed integration architectures
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'What architectural patterns, offline-safety guarantees, and degradation strategies are recommended for file-first agentic systems that integrate with live HTTP services using an '\''always write a candidate first, push when reachable'\'' pattern, and what are the validated failure modes?' --from manual --sensitivity personal --tag agentic-os --tag local-first --tag offline-safety --tag integration-patterns --tag degradation --backlog-idea-ref RIB-029

# RIB-030 [medium] Exposing a CLI tool's operations as MCP tools for agent consumption
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'What architectural patterns, libraries, and trade-offs govern exposing an existing Python CLI (like rf) as an MCP server so agents invoke pipeline operations via MCP rather than subprocess shell calls?' --from manual --sensitivity personal --tag research-foundry --tag mcp --tag cli --tag agent-interface --tag protocol --backlog-idea-ref RIB-030

# RIB-031 [medium] Idempotent writeback and reconciliation for re-run research swarms
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'How can RF make writebacks to MeatyWiki, SkillBOM, and CCDash idempotent and reconcilable so re-running a disposable swarm does not duplicate or pollute downstream knowledge?' --from manual --sensitivity personal --tag agentic-os --tag integration --tag writeback --tag idempotency --tag reconciliation --backlog-idea-ref RIB-031

# RIB-032 [medium] IntentTree to RF inbound dispatch: preserving research context across handoff
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'What data structures, API contracts, and workflow patterns best preserve research context (linked notes, prior artifacts, structured questions) when dispatching a task from IntentTree to RF, and what are the known failure modes of such bidirectional handoffs?' --from manual --sensitivity personal --tag intenttree --tag bidirectional-integration --tag handoff --tag agentic-os --backlog-idea-ref RIB-032

# ===== Knowledge Compilation & Retrieval =====
# RIB-033 [high] Embedding model and vector-store strategy for a file-first vault at 1K-100K scale
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'Which combination of embedding model (local bge-m3/MiniLM/nomic vs API text-embedding-3-small) and vector backend (sqlite-vec, pgvector IVFFlat/HNSW, FAISS, Chroma, LanceDB, Qdrant) achieves the best precision/recall, cost, and query latency for a single-user file-first Markdown vault in the 1K-100K artifact range, considering privacy and Git/Obsidian compatibility?' --from manual --sensitivity personal --tag research-foundry --tag embeddings --tag vector-search --tag pgvector --tag sqlite-vec --backlog-idea-ref RIB-033

# RIB-034 [high] Hybrid BM25+vector and FTS5 ranking for structured Markdown knowledge bases
#   -> plan: --depth deep --audience technical --max-cost 6 --freshness 180d  (artifact: technical_memo)
rf capture 'At what corpus size does BM25/FTS5 alone become insufficient for a Markdown artifact KB, what hybrid architectures (BM25+vector, BM25+frontmatter, semantic chunking, BM25+reranking) deliver the best recall/precision at each scale tier, and what FTS5 indexing practices (heading-boost, frontmatter indexing, BM25 ranking customization) are best for 1K-50K documents?' --from manual --sensitivity personal --tag research-foundry --tag search --tag bm25 --tag vector-search --tag fts5 --backlog-idea-ref RIB-034

# RIB-035 [high] Semantic entity consolidation and auto-merge thresholds in a file-first vault
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'What entity-resolution algorithms and merge strategies (Fellegi-Sunter, TF-IDF blocking, LLM-assisted dedup) best consolidate semantically equivalent compiled artifacts while producing valid Obsidian-compatible Markdown, and what empirically grounded confidence thresholds and signal mixes (title sim, body cosine, provenance overlap, graph neighborhood) should govern auto-merge vs review-queue vs ignore?' --from manual --sensitivity personal --tag research-foundry --tag entity-resolution --tag deduplication --tag threshold-calibration --tag knowledge-graph --backlog-idea-ref RIB-035

# RIB-036 [medium] LLM-wiki vs RAG: when a compiled persistent wiki outperforms stateless retrieval
#   -> plan: --depth deep --audience technical --max-cost 6 --freshness 180d  (artifact: report)
rf capture 'Under what corpus size, query-type distribution, and update frequency does a Karpathy-style compiled persistent wiki produce measurably better answer quality, latency, and cost than standard RAG over the same raw sources, and what scaling limits do community implementations reveal?' --from manual --sensitivity personal --tag research-foundry --tag llm-wiki --tag rag --tag knowledge-management --tag benchmarks --backlog-idea-ref RIB-036

# RIB-037 [medium] Markdown/Git vs DB-as-truth for reproducible AI knowledge artifacts
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 365d  (artifact: technical_memo)
rf capture 'What are the documented trade-offs between file-first (Markdown+Git) and database-first (Postgres/SQLite/vector/graph) architectures for LLM-maintained knowledge bases — around reproducibility, diffability, schema evolution, concurrent writes, agent tool compatibility, human editability, and query performance at scale?' --from manual --sensitivity personal --tag research-foundry --tag file-first --tag database --tag architecture --tag git --backlog-idea-ref RIB-037

# RIB-038 [medium] Open-source LLM wiki implementations landscape (sage-wiki, CRATE, Binder, LENS, hyalo)
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: market_scan)
rf capture 'What are the capabilities, architectural decisions, limitations, and maintenance status of open-source LLM wiki implementations, and how do their design choices map to MeatyWiki requirements (multi-artifact-type, integration hooks, workflow engine, SAM/CCDash compatibility) — validating build-from-scratch or surfacing forkable components?' --from manual --sensitivity personal --tag research-foundry --tag llm-wiki --tag open-source --tag market-scan --tag tooling --backlog-idea-ref RIB-038

# RIB-039 [low] Context compression and progressive disclosure (L0-L3) for KB query cost
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'What context-budgeting strategies (L0 ~200 tokens through L3 5-20k) produce the best quality-to-cost ratio for answering queries against a compiled KB, and how should context assembly (artifact selection, truncation, metadata-first vs body-first) be structured per query type?' --from manual --sensitivity personal --tag research-foundry --tag context-engineering --tag token-budget --tag retrieval --tag query-optimization --backlog-idea-ref RIB-039

# RIB-040 [low] Knowledge graph edge vocabulary and relationship semantics audit
#   -> plan: --depth standard --audience technical --max-cost 4 --freshness 365d  (artifact: technical_memo)
rf capture 'Which semantic relationship predicates appear in established KG schemas (Wikidata, DBpedia, schema.org, academic KG benchmarks) and PKM tools, and how do they map onto MeatyWiki'\''s seven-type EdgeType enum to identify coverage gaps that meaningfully increase graph density?' --from manual --sensitivity personal --tag research-foundry --tag knowledge-graph --tag edge-types --tag ontology --tag relationship-extraction --backlog-idea-ref RIB-040

# ===== Evaluation & Quality Scoring =====
# RIB-041 [high] Non-determinism and cost-control for agentic eval harnesses in CI
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'What determinism strategies (temperature-0+seed, stubbed tool responses, rubric-based LLM-as-judge) and CI cost-control approaches (per-PR vs nightly vs gated runs with cost ceilings) are most effective for evaluating multi-turn agentic workflows where tool-call patterns matter but exact output text does not?' --from manual --sensitivity personal --tag research-foundry --tag evals --tag agent-sdk --tag ci-cd --tag llm-as-judge --backlog-idea-ref RIB-041

# RIB-042 [high] Quality scoring for evidence bundles and agent-generated reports
#   -> plan: --depth deep --audience technical --max-cost 8 --freshness 180d  (artifact: report)
rf capture 'What methods exist for automatically scoring agent-generated research outputs (claim support rate, source diversity, contradiction coverage, synthesis coherence, cost-per-verified-claim), which telemetry signals most reliably distinguish high- from low-quality runs, and how should RF'\''s CCDash quality_score field be computed?' --from manual --sensitivity personal --tag research-foundry --tag quality-scoring --tag evaluation --tag ccdash --tag telemetry --backlog-idea-ref RIB-042

# RIB-043 [medium] Artifact fidelity assessment frameworks for AI-generated outputs
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 365d  (artifact: literature_review)
rf capture 'What frameworks systematically assess the fidelity/quality of AI-generated artifacts (drafts, syntheses, PRDs, ADRs) across dimensions (accuracy, structural completeness, source grounding, handoff readiness), and how do G-Eval, prometheus-eval, and LLM-as-judge apply to the F0-F4 8-axis fidelity radar?' --from manual --sensitivity work_sensitive --tag research-foundry --tag fidelity --tag artifact-quality --tag evaluation --tag llm-judge --backlog-idea-ref RIB-043

# RIB-044 [medium] Golden regression corpus for the claim verifier and quality scorers
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 365d  (artifact: technical_memo)
rf capture 'How should RF build and maintain a golden corpus of reports with known claim labels so the claim verifier and quality scorers can be regression-tested for false negatives?' --from manual --sensitivity personal --tag research-foundry --tag evaluation --tag verifier --tag golden-corpus --tag regression --backlog-idea-ref RIB-044

# RIB-045 [medium] Logprob-based vs self-reported confidence for LLM classification
#   -> plan: --depth deep --audience technical --max-cost 6 --freshness 180d  (artifact: technical_memo)
rf capture 'Do token-logprob distributions provide more calibrated classification confidence than self-reported JSON confidence fields for structured document classification, and is the per-call overhead and provider-portability cost justified at vault scale?' --from manual --sensitivity personal --tag research-foundry --tag logprobs --tag classification-confidence --tag calibration --tag llm --backlog-idea-ref RIB-045

# RIB-046 [medium] Multi-agent review-council orchestration: independence, groupthink, and quality
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: report)
rf capture 'What council orchestration patterns (sequential blind review, parallel-then-synthesis, adversarial red-team injection) best preserve reviewer independence while converging on actionable findings, and what is the evidence that approve/concern/block council review catches weak claims better than single-agent verification?' --from manual --sensitivity personal --tag agentic-os --tag multi-agent --tag review-council --tag orchestration --tag independence --backlog-idea-ref RIB-046

# ===== Reuse & Promotion Governance =====
# RIB-047 [high] Closed-loop feedback from telemetry to artifact-version improvement
#   -> plan: --depth deep --audience technical --max-cost 8 --freshness 180d  (artifact: literature_review)
rf capture 'What does the literature and practitioner evidence say about closed-loop feedback from agentic telemetry (session logs, cost, quality gates) to artifact version improvement — what signal types, lag times, and governance structures reliably improve rather than degrade artifact quality?' --from manual --sensitivity personal --tag research-foundry --tag feedback-loop --tag artifact-governance --tag telemetry --tag closed-loop --backlog-idea-ref RIB-047

# RIB-048 [medium] Agent bundle / context-pack design patterns and handoff schemas
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'What design patterns, schemas, and metadata contracts do existing systems (SkillMeat, Continue.dev, Cursor rules, Copilot Workspace) use for '\''agent bundles'\'' / '\''context packs'\'' passed from knowledge/planning systems to coding agents, and what handoff format maximizes interoperability?' --from manual --sensitivity work_sensitive --tag research-foundry --tag agent-bundle --tag context-pack --tag handoff --tag certification --backlog-idea-ref RIB-048

# RIB-049 [medium] Preventing writeback pollution and memory hygiene in knowledge bases
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'What policies, filters, and human-review gates effectively prevent AI-generated research writebacks from polluting a knowledge wiki, and what evidence exists on KB contamination rates from automated AI writing across MeatyWiki, IntentTree, and ARC targets?' --from manual --sensitivity personal --tag research-foundry --tag meatywiki --tag writeback --tag memory-hygiene --tag knowledge-management --backlog-idea-ref RIB-049

# RIB-050 [medium] Provenance/supply-chain standards for agentic artifacts (SkillBOM vs SBOM)
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'How do software supply-chain frameworks (SBOM, SLSA, Sigstore, in-toto) map onto agentic artifact supply chains for skills/agents/context files, and what attestation, signing, and provenance standards are emerging specifically for agentic artifacts to benchmark SkillMeat'\''s Ed25519 attestation?' --from manual --sensitivity work_sensitive --tag research-foundry --tag sbom --tag skillbom --tag provenance --tag supply-chain --backlog-idea-ref RIB-050

# RIB-051 [medium] SkillBOM promotion governance: candidate to evaluated to promoted lifecycle
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: technical_memo)
rf capture 'What governance criteria, evaluation frameworks, and promotion gates should define the candidate → evaluated → human-reviewed → promoted SkillBOM lifecycle, what prior art exists for reusable prompt/agent-component governance, and how is premature reuse of unvalidated workflows prevented?' --from manual --sensitivity personal --tag research-foundry --tag skillbom --tag governance --tag promotion --tag reusable-skills --backlog-idea-ref RIB-051

# RIB-052 [low] Agentic control-plane and artifact-management market landscape
#   -> plan: --depth deep --audience technical --max-cost 8 --freshness 180d  (artifact: market_scan)
rf capture 'What is the current competitive landscape for agentic SDLC control planes and artifact-management platforms (Cursor, Copilot Workspace, Windsurf, Devin, LangSmith, PromptLayer, HF Hub, W&B Prompts), and how does a file-backed local-first approach (SkillMeat/CCDash) compare on governance, portability, and developer experience?' --from manual --sensitivity work_sensitive --tag research-foundry --tag competitive-analysis --tag market-scan --tag control-plane --tag skillmeat --backlog-idea-ref RIB-052

# ===== Capture & Ingestion =====
# RIB-053 [high] Unified research-capture harness: normalize sources from heterogeneous AI tools
#   -> plan: --depth deep --audience technical --max-cost 7 --freshness 180d  (artifact: technical_memo)
rf capture 'What pipeline architecture best ingests outputs from ChatGPT deep-research, Perplexity, NotebookLM, and Gemini into a structured vault — handling source attribution, provenance metadata, deduplication, and content normalization across incompatible export formats?' --from manual --sensitivity personal --tag research-foundry --tag research-capture --tag ingestion-pipeline --tag provenance --tag normalization --backlog-idea-ref RIB-053

# RIB-054 [medium] Audio/voice-to-structured-artifact intake without GPU dependence
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: market_scan)
rf capture 'What transcription and diarization solutions (Whisper variants, WhisperX, Pyannote, Deepgram, AssemblyAI) offer the best accuracy-cost-latency tradeoff for local-first intake where GPU availability is uncertain, and what end-to-end pipelines convert voice memos into structured, tagged, routed artifacts (including Stream Deck capture)?' --from manual --sensitivity personal --tag research-foundry --tag audio --tag transcription --tag diarization --tag whisper --backlog-idea-ref RIB-054

# RIB-055 [medium] Frictionless capture and retrieval: zero-cognitive-lift PKM design patterns
#   -> plan: --depth standard --audience technical --max-cost 5 --freshness 180d  (artifact: market_scan)
rf capture 'What design patterns and interaction models in PKM systems (Obsidian, Logseq, Roam, Notion, Mem) produce the lowest cognitive overhead for capturing, finding, and linking artifacts — including mobile share-extension and offline-tolerant intake — and what measurable proxies validate '\''zero cognitive lift'\''?' --from manual --sensitivity personal --tag research-foundry --tag pkm --tag cognitive-lift --tag capture --tag mobile-ux --backlog-idea-ref RIB-055
