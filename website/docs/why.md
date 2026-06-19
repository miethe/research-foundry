---
title: Why Research Foundry
description: The problem of ungoverned AI research and how evidence-first systems solve it
audience: developers, researchers, team leads
tags: vision, problem-statement, governance
created: 2026-06-19
updated: 2026-06-19
category: concepts
status: published
related_documents: []
---

# Why Research Foundry

Large language models hallucinate, and research teams often cannot tell. Reports get published without knowing which claims are grounded in evidence, which are inferences, and which are educated guesses dressed as facts. This gap between assertion and audit creates risk: teams rely on AI research without traceability, executives make decisions on unverified claims, and when something goes wrong, the chain of custody is lost.

Research Foundry solves this by making **the claim ledger — not the model — the authority**. Every material claim in a report must either be traced back to a source or explicitly labeled as inference, speculation, or unresolved. `rf verify` enforces this deterministically before anything is published or fed downstream.

## The Problem

- **LLM fabrication is real.** Models confidently assert facts they've never seen. Detecting hallucination requires human effort, and teams often skip that step under time pressure.
- **Research workflows are ungoverned.** No standard way to track where a claim came from, who validated it, or whether it's safe to act on. Researchers mix personal exploration, work-internal analysis, and client research in the same tools without isolation.
- **Synthesis is expensive.** Teams run multiple passes — cheap extraction, then expensive deep reasoning — but there's no standard orchestration to route work efficiently. Every claim ends up re-analyzed.
- **Writebacks are opaque.** Research findings get copied into wikis, dashboards, and skill catalogs manually. If a source changes or a claim gets contradicted, nobody knows which downstream systems need updates.

## The Thesis

Research Foundry turns AI research from a black box into an auditable, governed pipeline:

1. **Evidence-first.** Start with raw ideas, convert them to structured intents, plan swarms, and *deliberately* ingest sources. No models speak until sources exist.

2. **Markdown/YAML as source of truth.** Every artifact (intent, source card, extraction, claim, report, verification result) is human-readable Markdown or YAML on disk. No database. Deterministic. Diff-friendly. Reproducible.

3. **The claim ledger as authority.** Synthesis can only cite claim IDs already in `claims/claim_ledger.yaml`, or it must label text as inference/speculation/contradicted. `rf verify` fails the build on any unsupported material claim (exit code 4).

4. **Cheap extract, expensive synthesize.** Free/local models run extraction, deduplication, and tagging. Expensive models are reserved for synthesis, contradiction analysis, and executive framing. Named model profiles (`rf_extract_cheap`, `rf_synthesize_deep`) control routing.

5. **The swarm is disposable, the evidence bundle is durable.** Agents and tool runs are rerunnable. The durable asset is the evidence bundle: source cards, extractions, claim ledger, report, reviews, telemetry, and writebacks. Dispose of the swarm; keep the bundle.

6. **Governance is a runtime gate.** Key profiles (`personal`, `work_approved`, `client_approved`, `offline_only`) are enforced *before* execution. Work and personal keys cannot be mixed. Sensitive research requires human review before writeback. Deterministically.

## What It Means in Practice

Research Foundry provides a thin `rf` CLI and a Markdown/YAML substrate. You define intents (research questions), ingest sources (PDFs, URLs, docs), extract evidence via cheap models, build a claim ledger, synthesize reports with expensive models, verify every claim traces back to a source, bundle the results, and write back to MeatyWiki, SkillMeat, and CCDash.

All optional steps (live model adapters, external search, ARC council reviews) are opt-in. The core loop runs fully offline and deterministically.

**Example**: you want to research "What is the minimum viable architecture for agentic research workflows?" You run `rf capture`, `rf triage`, `rf plan`, then `rf ingest` several papers and docs. Models extract key points cheaply. You map those points to a claim ledger. A deep model synthesizes a report using only claim IDs from the ledger. `rf verify` confirms every material claim in the report maps back to a source. `rf bundle` packages the evidence. `rf writeback` pushes findings to your MeatyWiki and SkillMeat, with links to source cards. Later, if you find a contradiction, the evidence bundle makes it searchable and traceable.

## Where to Next

- **[Quickstart](quickstart.md)** — install and run the demo loop in 5 minutes
- **[The Pipeline](concepts/pipeline.md)** — walk the 11-step end-to-end flow
- **[The Claim Model](concepts/claim-model.md)** — how claim-status tagging works
- **[Governance](concepts/governance.md)** — key profiles and runtime gates
- **[Artifacts](concepts/artifacts.md)** — anatomy of a run directory
- **[CLI Reference](reference/cli.md)** — `rf` command reference
- **[About](about.md)** — project status, integrations, and long-term direction
