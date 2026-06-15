---
id: mwb_20260613_cheap_extract_vs_deep_synthesize_the
evidence_bundle_id: bundle_20260613_intent_research_20260613_what_is_the
target_page: meatywiki/sources/cheap_extract_vs_deep_synthesize_the.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260613_what_is_the_empirical_accuracy_differential:
  46 supported claim(s) across 7 source card(s).'
key_claims:
- claim_id: clm_001
  include: true
- claim_id: clm_002
  include: true
- claim_id: clm_003
  include: true
- claim_id: clm_004
  include: true
- claim_id: clm_005
  include: true
- claim_id: clm_006
  include: true
- claim_id: clm_007
  include: true
- claim_id: clm_008
  include: true
- claim_id: clm_009
  include: true
- claim_id: clm_010
  include: true
- claim_id: clm_011
  include: true
- claim_id: clm_012
  include: true
- claim_id: clm_013
  include: true
- claim_id: clm_014
  include: true
- claim_id: clm_015
  include: true
- claim_id: clm_016
  include: true
- claim_id: clm_017
  include: true
- claim_id: clm_018
  include: true
- claim_id: clm_019
  include: true
- claim_id: clm_020
  include: true
- claim_id: clm_021
  include: true
- claim_id: clm_022
  include: true
- claim_id: clm_023
  include: true
- claim_id: clm_024
  include: true
- claim_id: clm_025
  include: true
- claim_id: clm_026
  include: true
- claim_id: clm_027
  include: true
- claim_id: clm_028
  include: true
- claim_id: clm_029
  include: true
- claim_id: clm_030
  include: true
- claim_id: clm_031
  include: true
- claim_id: clm_032
  include: true
- claim_id: clm_033
  include: true
- claim_id: clm_034
  include: true
- claim_id: clm_035
  include: true
- claim_id: clm_036
  include: true
- claim_id: clm_037
  include: true
- claim_id: clm_038
  include: true
- claim_id: clm_039
  include: true
- claim_id: clm_040
  include: true
- claim_id: clm_041
  include: true
- claim_id: clm_042
  include: true
- claim_id: clm_043
  include: true
- claim_id: clm_044
  include: true
- claim_id: clm_045
  include: true
- claim_id: clm_046
  include: true
links:
  source_cards:
  - src_20260613_rib007_00
  - src_20260613_rib007_01
  - src_20260613_rib007_04
  - src_20260613_rib007_06
  - src_20260613_rib007_07
  - src_20260613_rib007_08
  - src_20260613_rib007_09
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Cheap-extract vs deep-synthesize: the empirical cost/quality case for Research Foundry's two-tier model split

## Summary

Source note distilled from research run rf_run_20260613_what_is_the_empirical_accuracy_differential: 46 supported claim(s) across 7 source card(s).

## Key claims

- Claude Haiku 4.5 was released October 15, 2025 at $1 per million input tokens and $5 per million output tokens. [claim:clm_001]
- Anthropic positions Haiku 4.5 as matching the coding performance of Sonnet 4 (a frontier model five months prior) at one-third the cost and more than twice the speed. [claim:clm_002]
- Per Augment's agentic coding evaluation, Haiku 4.5 achieves 90% of Sonnet 4.5's performance. [claim:clm_003]
- Haiku 4.5 is reported to run up to 4-5 times faster than Sonnet 4.5 at a fraction of the cost. [claim:clm_004]
- On some tasks such as computer use, Haiku 4.5 surpasses the larger Sonnet 4 model. [claim:clm_005]
- Haiku 4.5 showed a statistically significantly lower overall rate of misaligned behaviors than both Sonnet 4.5 and Opus 4.1. [claim:clm_006]
- Across an evaluation of 23 LLMs, even state-of-the-art models encounter significant challenges in long-form generation as real-world complexity and output length increase. [claim:clm_007]
- LongWeave supports customizable input/output lengths up to 64K/8K tokens across seven distinct tasks. [claim:clm_008]
- LongWeave balances real-world and verifiable assessment via Constraint-Verifier Evaluation (CoV-Eval). [claim:clm_009]
- CoV-Eval builds tasks by first defining verifiable targets within real-world scenarios, then systematically generating the corresponding queries, textual materials, and constraints from those targets to make tasks realistic yet objectively assessable. [claim:clm_010]
- Existing long-form generation benchmarks either assess real-world queries with hard-to-verify metrics or use synthetic setups that ease evaluation but overlook real-world intricacies. [claim:clm_011]
- The paper was submitted to arXiv on 2025-10-28 (arXiv:2510.24345) and accepted to EMNLP 2025 Findings, authored by a team including Bowen Yu and Junyang Lin (Qwen). [claim:clm_012]
- Claude Haiku 4.5 lists at $1/MTok base input and $5/MTok output, with cache reads at $0.10/MTok. [claim:clm_013]
- Claude Sonnet 4.5 and Sonnet 4.6 both list at $3/MTok base input and $15/MTok output. [claim:clm_014]
- Claude Opus 4.5, 4.6, 4.7, and 4.8 all list at $5/MTok base input and $25/MTok output. [claim:clm_015]
- Prompt-caching multipliers relative to base input are 1.25x (5-min write), 2x (1-hour write), and 0.1x (cache read/hit). [claim:clm_016]
- The Batch API applies a 50% discount on both input and output tokens, e.g. Haiku 4.5 at $0.50/$2.50 and Sonnet at $1.50/$7.50. [claim:clm_017]
- Processing 10,000 support tickets averaging ~3,700 tokens each on Claude Haiku 4.5 costs roughly $37.00 total. [claim:clm_018]
- Opus 4.7 and later use a new tokenizer that may consume up to 35% more tokens for the same fixed text, affecting effective per-text cost. [claim:clm_019]
- Gemini 3.1 Pro Preview, the flagship, is priced at $2.00/MTok input and $12.00/MTok output for prompts <=200K tokens, rising to $4.00/$18.00 for prompts >200K tokens. [claim:clm_020]
- Gemini 3.5 Flash is priced at $1.50/MTok input and $9.00/MTok output (output includes thinking tokens). [claim:clm_021]
- Gemini 3 Flash Preview is priced at $0.50/MTok input (text/image/video) and $3.00/MTok output. [claim:clm_022]
- Gemini 3.1 Flash-Lite, the cheapest current-generation model, is priced at $0.25/MTok text/image/video input and $1.50/MTok output. [claim:clm_023]
- Gemini 2.5 Pro uses tiered pricing of $1.25/$10.00 (<=200K tokens) rising to $2.50/$15.00 (>200K tokens), with a 50% batch discount available. [claim:clm_024]
- Gemini 2.5 Flash is $0.30/$2.50 standard ($0.15/$1.25 batch) for text/image/video, and Gemini 2.5 Flash-Lite is the cheapest at $0.10/$0.40. [claim:clm_025]
- Google offers a Batch API with a 50% cost reduction relative to standard synchronous pricing across Gemini models. [claim:clm_026]
- The benchmark evaluates 21 frontier and open-weight models, ranging from 8B to 358B parameters, across three source domains and seven metrics. [claim:clm_027]
- It is a multi-source benchmark spanning three modalities: native text, images, and audio conversations. [claim:clm_028]
- Phi-4 (14B) scored 0.798 Value Accuracy on text, slightly above GPT-5 (0.795) and GPT-5 Mini (0.779). [claim:clm_029]
- Schematron-8B scored 0.754, outperforming GPT-OSS 20B (0.693) despite having roughly 2.5x fewer parameters. [claim:clm_030]
- The paper's explicit headline conclusion is that model size does not predict structured output quality. [claim:clm_031]
- Value Accuracy, the primary metric, measures the fraction of ground-truth leaf paths where the predicted value exactly matches. [claim:clm_032]
- The smaller open model Qwen3.5-35B scored 0.801 Value Accuracy on text, exceeding closed-source frontier models on the primary metric. [claim:clm_033]
- The survey defines small language models as 1-12B parameters (sometimes up to 20B) and argues they are sufficient and often superior for schema- and API-constrained agentic work rather than open-ended generation. [claim:clm_034]
- The paper claims guided decoding, strict JSON Schema outputs, and validator-first tool execution let SLMs match or surpass larger models on tool use, function calling, and RAG at 10x-100x lower token cost with better latency and energy. [claim:clm_035]
- The survey synthesizes evidence across specific open and proprietary SLMs including Phi-4-Mini, Qwen-2.5-7B, Gemma-2-9B, Llama-3.2-1B/3B, Ministral-3B/8B, Apple on-device 3B, and DeepSeek-R1-Distill. [claim:clm_036]
- The authors formalize SLM-default, LLM-fallback systems with uncertainty-aware routing and verifier cascades, and propose production metrics: cost per successful task, schema validity rate, executable call rate, p50/p95 latency, and energy per request. [claim:clm_037]
- The survey recommends SLM-first agent design patterns (schema-first prompting, type-safe function registries, confidence scoring with verifier rollups, LoRA/QLoRA adaptation) while preserving LLM fallback for open-domain reasoning and some long-horizon planning. [claim:clm_038]
- The survey is authored by Raghav Sharma and Manan Mehta and was submitted to arXiv on October 4, 2025. [claim:clm_039]
- The study benchmarks four multi-agent orchestration architectures across five LLMs on a 10,000-document SEC filing corpus. [claim:clm_040]
- Evaluation used a corpus of 10,000 SEC filings (10-K, 10-Q, 8-K) across five frontier and open-weight LLMs. [claim:clm_041]
- Extraction quality was measured across 25 field types along five axes including field-level F1, document accuracy, latency, cost per document, and token efficiency. [claim:clm_042]
- Reflexive architectures achieved the highest field-level F1 (0.943) but at 2.3x the cost of sequential baselines. [claim:clm_043]
- Hybrid configurations (semantic caching, model routing, adaptive retry) recovered 89% of the reflexive architecture's accuracy gains at only 1.15x baseline cost. [claim:clm_044]
- A scaling analysis from 1K to 100K documents per day revealed non-obvious throughput-accuracy degradation curves relevant to capacity planning. [claim:clm_045]
- The paper frames itself as filling a gap in empirical guidance for production multi-agent LLM extraction in regulated financial environments. [claim:clm_046]

## Sources

- src_20260613_rib007_00 — Pricing — Anthropic Claude API (Official Docs)
- src_20260613_rib007_01 — Introducing Claude Haiku 4.5
- src_20260613_rib007_04 — Gemini API Pricing (Gemini Developer API pricing)
- src_20260613_rib007_06 — Benchmarking Multi-Agent LLM Architectures for Financial Document Processing: A Comparative Study of Orchestration Patterns, Cost-Accuracy Tradeoffs and Production Scaling Strategies
- src_20260613_rib007_07 — The Structured Output Benchmark: A Multi-Source Benchmark for Evaluating Structured Output Quality in Large Language Models
- src_20260613_rib007_08 — Small Language Models for Agentic Systems: A Survey of Architectures, Capabilities, and Deployment Trade-offs
- src_20260613_rib007_09 — LongWeave: A Long-Form Generation Benchmark Bridging Real-World Relevance and Verifiability

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
