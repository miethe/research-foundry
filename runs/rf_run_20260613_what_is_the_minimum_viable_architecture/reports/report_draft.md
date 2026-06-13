---
schema_version: '0.1'
type: research_report
report_id: report_20260613_what_is_the_minimum_viable_architecture
title: What is the minimum viable architecture for an
intent_id: intent_research_20260613_what_is_the_minimum_viable_architecture
evidence_bundle_id: pending
created_at: '2026-06-13T02:11:45-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

CCDash tracks completion, rework, drift, cost, latency, quality, and reuse candidates to answer which research workflows actually worked. [claim:clm_001]
PaperQA2 performs agentic RAG over scientific papers, grounding responses with in-text citations and re-ranking. [claim:clm_002]
GPT Researcher supports web, local, and hybrid research, produces multi-source cited reports, and supports many LLMs. [claim:clm_003]
The Claude Agent SDK exposes built-in tools, hooks, subagents, MCP, permissions, and sessions. [claim:clm_004]
LiteLLM supports routing strategies including cost-based and lowest-cost routing, and provider, model, and tag budgets. [claim:clm_005]

## Inferences

<!-- No analytic inferences were drawn for this run. -->

## Speculation

<!-- No speculation was recorded for this run. -->

## Open questions

- None recorded.

## Sources

- src_20260613_ccdash_36212ddb: ccdash
- src_20260613_paperqa2_5f264205: paperqa2
- src_20260613_gpt_researcher_b4d1f755: gpt_researcher
- src_20260613_claude_agent_sdk_3fc9e943: claude_agent_sdk
- src_20260613_litellm_c5cef789: litellm
