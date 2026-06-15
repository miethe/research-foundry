---
schema_version: '0.1'
type: research_report
report_id: report_20260613_what_is_the_empirical_accuracy_differential
title: What is the empirical accuracy differential and cost
intent_id: intent_research_20260613_what_is_the_empirical_accuracy_differential
evidence_bundle_id: pending
created_at: '2026-06-13T23:19:18-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

Claude Haiku 4.5 was released October 15, 2025 at $1 per million input tokens and $5 per million output tokens. [claim:clm_001]
Anthropic positions Haiku 4.5 as matching the coding performance of Sonnet 4 (a frontier model five months prior) at one-third the cost and more than twice the speed. [claim:clm_002]
Per Augment's agentic coding evaluation, Haiku 4.5 achieves 90% of Sonnet 4.5's performance. [claim:clm_003]
Haiku 4.5 is reported to run up to 4-5 times faster than Sonnet 4.5 at a fraction of the cost. [claim:clm_004]
On some tasks such as computer use, Haiku 4.5 surpasses the larger Sonnet 4 model. [claim:clm_005]
Haiku 4.5 showed a statistically significantly lower overall rate of misaligned behaviors than both Sonnet 4.5 and Opus 4.1. [claim:clm_006]
Across an evaluation of 23 LLMs, even state-of-the-art models encounter significant challenges in long-form generation as real-world complexity and output length increase. [claim:clm_007]
LongWeave supports customizable input/output lengths up to 64K/8K tokens across seven distinct tasks. [claim:clm_008]
LongWeave balances real-world and verifiable assessment via Constraint-Verifier Evaluation (CoV-Eval). [claim:clm_009]
CoV-Eval builds tasks by first defining verifiable targets within real-world scenarios, then systematically generating the corresponding queries, textual materials, and constraints from those targets to make tasks realistic yet objectively assessable. [claim:clm_010]
Existing long-form generation benchmarks either assess real-world queries with hard-to-verify metrics or use synthetic setups that ease evaluation but overlook real-world intricacies. [claim:clm_011]
The paper was submitted to arXiv on 2025-10-28 (arXiv:2510.24345) and accepted to EMNLP 2025 Findings, authored by a team including Bowen Yu and Junyang Lin (Qwen). [claim:clm_012]
Claude Haiku 4.5 lists at $1/MTok base input and $5/MTok output, with cache reads at $0.10/MTok. [claim:clm_013]
Claude Sonnet 4.5 and Sonnet 4.6 both list at $3/MTok base input and $15/MTok output. [claim:clm_014]
Claude Opus 4.5, 4.6, 4.7, and 4.8 all list at $5/MTok base input and $25/MTok output. [claim:clm_015]
Prompt-caching multipliers relative to base input are 1.25x (5-min write), 2x (1-hour write), and 0.1x (cache read/hit). [claim:clm_016]
The Batch API applies a 50% discount on both input and output tokens, e.g. Haiku 4.5 at $0.50/$2.50 and Sonnet at $1.50/$7.50. [claim:clm_017]
Processing 10,000 support tickets averaging ~3,700 tokens each on Claude Haiku 4.5 costs roughly $37.00 total. [claim:clm_018]
Opus 4.7 and later use a new tokenizer that may consume up to 35% more tokens for the same fixed text, affecting effective per-text cost. [claim:clm_019]
Gemini 3.1 Pro Preview, the flagship, is priced at $2.00/MTok input and $12.00/MTok output for prompts <=200K tokens, rising to $4.00/$18.00 for prompts >200K tokens. [claim:clm_020]
Gemini 3.5 Flash is priced at $1.50/MTok input and $9.00/MTok output (output includes thinking tokens). [claim:clm_021]
Gemini 3 Flash Preview is priced at $0.50/MTok input (text/image/video) and $3.00/MTok output. [claim:clm_022]
Gemini 3.1 Flash-Lite, the cheapest current-generation model, is priced at $0.25/MTok text/image/video input and $1.50/MTok output. [claim:clm_023]
Gemini 2.5 Pro uses tiered pricing of $1.25/$10.00 (<=200K tokens) rising to $2.50/$15.00 (>200K tokens), with a 50% batch discount available. [claim:clm_024]
Gemini 2.5 Flash is $0.30/$2.50 standard ($0.15/$1.25 batch) for text/image/video, and Gemini 2.5 Flash-Lite is the cheapest at $0.10/$0.40. [claim:clm_025]
Google offers a Batch API with a 50% cost reduction relative to standard synchronous pricing across Gemini models. [claim:clm_026]
The benchmark evaluates 21 frontier and open-weight models, ranging from 8B to 358B parameters, across three source domains and seven metrics. [claim:clm_027]
It is a multi-source benchmark spanning three modalities: native text, images, and audio conversations. [claim:clm_028]
Phi-4 (14B) scored 0.798 Value Accuracy on text, slightly above GPT-5 (0.795) and GPT-5 Mini (0.779). [claim:clm_029]
Schematron-8B scored 0.754, outperforming GPT-OSS 20B (0.693) despite having roughly 2.5x fewer parameters. [claim:clm_030]
The paper's explicit headline conclusion is that model size does not predict structured output quality. [claim:clm_031]
Value Accuracy, the primary metric, measures the fraction of ground-truth leaf paths where the predicted value exactly matches. [claim:clm_032]
The smaller open model Qwen3.5-35B scored 0.801 Value Accuracy on text, exceeding closed-source frontier models on the primary metric. [claim:clm_033]
The survey defines small language models as 1-12B parameters (sometimes up to 20B) and argues they are sufficient and often superior for schema- and API-constrained agentic work rather than open-ended generation. [claim:clm_034]
The paper claims guided decoding, strict JSON Schema outputs, and validator-first tool execution let SLMs match or surpass larger models on tool use, function calling, and RAG at 10x-100x lower token cost with better latency and energy. [claim:clm_035]
The survey synthesizes evidence across specific open and proprietary SLMs including Phi-4-Mini, Qwen-2.5-7B, Gemma-2-9B, Llama-3.2-1B/3B, Ministral-3B/8B, Apple on-device 3B, and DeepSeek-R1-Distill. [claim:clm_036]
The authors formalize SLM-default, LLM-fallback systems with uncertainty-aware routing and verifier cascades, and propose production metrics: cost per successful task, schema validity rate, executable call rate, p50/p95 latency, and energy per request. [claim:clm_037]
The survey recommends SLM-first agent design patterns (schema-first prompting, type-safe function registries, confidence scoring with verifier rollups, LoRA/QLoRA adaptation) while preserving LLM fallback for open-domain reasoning and some long-horizon planning. [claim:clm_038]
The survey is authored by Raghav Sharma and Manan Mehta and was submitted to arXiv on October 4, 2025. [claim:clm_039]
The study benchmarks four multi-agent orchestration architectures across five LLMs on a 10,000-document SEC filing corpus. [claim:clm_040]
Evaluation used a corpus of 10,000 SEC filings (10-K, 10-Q, 8-K) across five frontier and open-weight LLMs. [claim:clm_041]
Extraction quality was measured across 25 field types along five axes including field-level F1, document accuracy, latency, cost per document, and token efficiency. [claim:clm_042]
Reflexive architectures achieved the highest field-level F1 (0.943) but at 2.3x the cost of sequential baselines. [claim:clm_043]
Hybrid configurations (semantic caching, model routing, adaptive retry) recovered 89% of the reflexive architecture's accuracy gains at only 1.15x baseline cost. [claim:clm_044]
A scaling analysis from 1K to 100K documents per day revealed non-obvious throughput-accuracy degradation curves relevant to capacity planning. [claim:clm_045]
The paper frames itself as filling a gap in empirical guidance for production multi-agent LLM extraction in regulated financial environments. [claim:clm_046]

## Inferences

**Inference:** For RF's structured-extraction stage, the cheap-vs-deep accuracy differential is empirically near-zero or negative, because small models (Phi-4 14B at 0.798, Qwen3.5-35B at 0.801, Schematron-8B at 0.754) match or beat frontier models (GPT-5 at 0.795) on exact-match Value Accuracy, so extraction is the clearest case for defaulting to the cheap tier. [claim:clm_inf01]
**Inference:** The cheap-vs-deep gap inverts at the synthesis stage, where long-form, complex outputs degrade even for state-of-the-art models, so RF should reserve the deep tier (Opus/Gemini Pro) for synthesis and claim-verification rather than for extraction. [claim:clm_inf02]
**Inference:** On Anthropic list pricing, an all-deep policy costs 5x the input and 5x the output of an all-cheap policy (Opus $5/$25 vs Haiku $1/$5), so the two-tier split's savings ceiling is the fraction of total tokens that extraction (the high-volume, cheap-eligible stage) represents. [claim:clm_inf03]
**Inference:** Across providers the cheap-to-deep price ladder is similar in shape, with Gemini 3.1 Flash-Lite ($0.25/$1.50) about 8x cheaper on input than Gemini 3.1 Pro ($2.00/$12.00) and roughly 4x cheaper than Claude Haiku, making Flash-Lite-class models the cost floor for RF's extraction tier when modality permits. [claim:clm_inf04]
**Inference:** For a representative RF run dominated by extraction, the two-tier split (Haiku extract + Opus synthesize) lands close to the all-cheap cost curve rather than the all-deep curve, because synthesis is a small minority of tokens while extraction carries the bulk volume. [claim:clm_inf05]
**Inference:** The two-tier split pays off relative to a flat all-deep policy whenever extraction is a material share of tokens, but it stops paying off below a small per-run volume where the deep-tier premium on extraction is dwarfed by fixed orchestration overhead and the engineering cost of running and validating two models. [claim:clm_inf06]
**Inference:** A defensible break-even rule for RF is that the two-tier split beats a flat all-deep policy once extraction exceeds roughly tens of thousands of tokens per run (order of one full source corpus), derived from the support-ticket datapoint where 37M tokens of Haiku work cost ~$37 versus ~$185 if run on Opus, a ~$148 saving that easily exceeds split overhead. [claim:clm_inf07]
**Inference:** The most cost-efficient RF policy is not a pure two-tier split but a hybrid of cheap extraction plus targeted deep escalation, because the SEC benchmark shows hybrid configurations recover 89% of the best architecture's accuracy gains at only 1.15x baseline cost versus 2.3x for always running the expensive reflexive loop. [claim:clm_inf08]
**Inference:** At intake, batch classification is the preferred default over per-artifact LLM classification because the 50% Batch API discount (Haiku effectively $0.50/$2.50) halves cost at negligible accuracy loss for the high-volume, latency-tolerant classification step, while pure heuristic classification should be reserved for unambiguous signals where it is effectively free. [claim:clm_inf09]
**Inference:** Field-level extraction subtasks with verifiable leaf values (numbers, dates, enumerated categories, governance/compensation fields) are 'good enough' on cheap models, evidenced by SLMs matching frontier Value Accuracy and by the SEC study measuring extraction at the field level across 25 typed fields. [claim:clm_inf10]
**Inference:** The extraction subtasks that silently degrade on cheap models are those requiring cross-document synthesis, long-context reasoning, or judgment about relevance and contradiction, since these inherit the long-form-generation fragility that LongWeave shows worsens with complexity and length and that the SLM survey flags as LLM-fallback territory. [claim:clm_inf11]
**Inference:** RF should adopt an explicit SLM-default, deep-fallback guardrail with uncertainty-aware routing and a verifier cascade, scoring each cheap-tier extraction with a confidence value and escalating any field below threshold to the deep tier before it can enter the claim ledger. [claim:clm_inf12]
**Inference:** A concrete guardrail set for keeping the cheap tier from poisoning the claim ledger is: (1) reject any extraction that fails strict JSON-Schema validation, (2) escalate any field whose confidence falls below a calibrated threshold to the deep tier, and (3) require deep-tier or human verification for every material claim, leaving only background claims eligible for cheap-tier-only provenance. [claim:clm_inf13]
**Inference:** RF's choice of cost-per-successful-task over cost-per-token is the correct optimization target, because a cheap-tier extraction that fails schema validation or is escalated and reworked costs more end-to-end than a single deep-tier pass, so the break-even must be computed on successful-task cost not raw token price. [claim:clm_inf14]
**Inference:** The Opus 4.7+ tokenizer change, which can consume up to 35% more tokens for the same text, erodes headline per-MTok parity and widens the effective cost gap between deep and cheap tiers, strengthening the case for keeping high-volume extraction off Opus-class models. [claim:clm_inf15]
**Inference:** Stacking prompt caching on the two-tier split is the highest-leverage incremental optimization for RF, because cache reads at 0.1x base input let a repeatedly-referenced source corpus be re-fed to both tiers at roughly a tenth of input cost, disproportionately benefiting synthesis where the same evidence is read many times. [claim:clm_inf16]

## Speculation

**Speculation:** As Flash-Lite- and Haiku-class models continue closing the structured-output gap, RF's economically optimal policy will trend toward cheap-tier-for-everything-except-final-synthesis, shrinking the deep tier's role to claim verification and the last synthesis pass within roughly the next model generation. [claim:clm_spec01]
**Speculation:** If RF adopts cross-provider routing, the lowest-cost compliant configuration will likely pair a Gemini Flash-Lite-class extractor with an Opus-class synthesizer, but this is contingent on per-provider schema-validity and batch behavior that the current sources price but do not benchmark head-to-head. [claim:clm_spec02]

## Open questions

- None recorded.

## Sources

- src_20260613_rib007_01: Introducing Claude Haiku 4.5
- src_20260613_rib007_09: LongWeave: A Long-Form Generation Benchmark Bridging Real-World Relevance and Verifiability
- src_20260613_rib007_00: Pricing — Anthropic Claude API (Official Docs)
- src_20260613_rib007_04: Gemini API Pricing (Gemini Developer API pricing)
- src_20260613_rib007_07: The Structured Output Benchmark: A Multi-Source Benchmark for Evaluating Structured Output Quality in Large Language Models
- src_20260613_rib007_08: Small Language Models for Agentic Systems: A Survey of Architectures, Capabilities, and Deployment Trade-offs
- src_20260613_rib007_06: Benchmarking Multi-Agent LLM Architectures for Financial Document Processing: A Comparative Study of Orchestration Patterns, Cost-Accuracy Tradeoffs and Production Scaling Strategies
