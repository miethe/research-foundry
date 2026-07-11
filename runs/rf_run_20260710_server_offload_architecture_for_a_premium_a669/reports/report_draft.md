---
schema_version: '0.1'
type: research_report
report_id: report_20260711_research_report_for_rf_run_20260710
title: 'Server Offload Architecture for a KnitWit/LoopNest Premium Tier: Workload Placement, Cost Model, Hybrid Architecture, and Privacy/Offline Posture'
intent_id: intent_research_20260710_server_offload_architecture_for_a_premium_cb41
evidence_bundle_id: pending
created_at: '2026-07-11T11:00:43-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# Server Offload Architecture for a KnitWit/LoopNest Premium Tier

## Executive summary

**Inference:** LLM pattern structuring/extraction from PDFs and URLs must be offloaded to a server because typical multi-page patterns exceed Apple's 4096-token on-device window, which throws .exceededContextWindowSize and halts the session. [claim:clm_inf01]
**Inference:** Interactive 3D rendering, stitch counters, and step mode should stay on-device (Metal) because they are latency-sensitive, low-compute, and touch no data that requires cloud reasoning. [claim:clm_inf02]
**Inference:** Heavy mesh generation and physics relaxation of stitch graphs should be offloaded to a server GPU/CPU as an asynchronous job, not run interactively on-device, because the iterative least-squares solver is the dominant compute cost of the layout. [claim:clm_inf03]
**Inference:** The architecture should split by job duration: PDF/URL extraction and mesh relaxation run as queue+callback async jobs (enqueue, return immediately, client polls), while counters, step mode, and cached-preview rendering run synchronously on-device. [claim:clm_inf09]
**Inference:** Use pay-per-use cloud LLM APIs for extraction (no infra, batch discount, elastic) and reserve self-hosting for the mesh-relaxation GPU tier only if volume justifies it, since the Ceres-based solver is open-source and deterministic with no per-token cost. [claim:clm_inf10]
**Inference:** At these token prices LLM extraction is not the binding cost for a $9.99-$19.99/month premium tier (a $9.99 plan covers hundreds of Flash-tier extractions); the real cost driver and metering target is server GPU mesh relaxation, not text extraction. [claim:clm_inf06]
**Inference:** Caching by pattern hash cuts marginal server cost sharply: identical prompt prefixes bill cache hits at 0.1x input (a ~90% reduction), and cross-user reuse of precomputed meshes/renders keyed by pattern hash drops a popular pattern's repeat cost toward storage+egress only. [claim:clm_inf07]
**Inference:** Pattern->3D via force-directed layout is academically demonstrated but not product-ready for interactive mobile use; the product path is server-side precompute plus pattern-hash caching, delivering a static renderable mesh to the device rather than solving on-device in real time. [claim:clm_inf15]
**Inference:** Required privacy posture: route user photos and user-private pattern imports through zero-retention, no-train endpoints with optional data-residency (the ~10% regional uplift is acceptable), and constrain any shared/ingested patterns to designer opt-in or license per the #1 copyright landmine. [claim:clm_inf13]

## Workload placement recommendation matrix

| Workload | Placement | Mode | Rationale | Evidence |
|---|---|---|---|---|
| PDF/URL LLM pattern structuring/extraction | Server (large-context cloud LLM) | Async queue+callback | Multi-page patterns exceed the 4096-token on-device window and error out | [claim:clm_inf01] |
| Long-context (>4096-token) extraction path | Server large-context structured extraction into Crochet IR | Async | Single server pass preserves exact per-round counts that chunk-and-summarize drops | [claim:clm_inf11] |
| Model choice for long-context extraction | GPT-5 mini (400k/272k) or Gemini 3.1 Pro, structured output | Async | Both windows dwarf 4096 tokens and support structured IR emission | [claim:clm_inf04] |
| Interactive 3D rendering, stitch counters, step mode | On-device (Metal) | Synchronous | Latency-sensitive, low-compute, no cloud-reasoning data | [claim:clm_inf02] |
| Mesh generation / stitch-graph physics relaxation | Server GPU/CPU | Async background job | Iterative least-squares solver is the dominant compute cost | [claim:clm_inf03] |
| Cached-preview rendering | On-device (cached IR + precomputed mesh) | Synchronous | Cached assets need no server round-trip | [claim:clm_inf09] |
| Oversized patterns (pattern books) chunking | Server, adaptive/semantic chunking along IR round/piece boundaries | Async | Adaptive chunking beat fixed-length on retrieval (F1 0.64 vs 0.24) | [claim:clm_inf12] |

## Per-operation cost model

### Cloud LLM and image pricing (published rates)

| Model / operation | Standard-tier price | Evidence |
|---|---|---|
| Gemini 2.5 Flash-Lite | $0.10/M input, $0.40/M output; batch $0.05/$0.20 | [claim:clm_014] |
| Gemini 2.5 Flash | $0.30/M input, $2.50/M output; batch $0.15/$1.25 | [claim:clm_015] |
| Gemini 3.5 Flash | $1.50/M input, $9.00/M output; batch $0.75/$4.50 | [claim:clm_016] |
| Gemini 3.1 Pro Preview | $2.00/$12.00 (<=200k tokens), $4.00/$18.00 (>200k) | [claim:clm_017] |
| Gemini 2.5 Flash Image | $0.039/image standard, $0.0195/image batch | [claim:clm_018] |
| gpt-5.6-terra (workhorse) | $2.50/M input, $0.25 cached, $15.00/M output | [claim:clm_027] |
| gpt-5.6-luna (cheap/fast) | $1.00/M input, $0.10 cached, $6.00/M output | [claim:clm_028] |
| gpt-5.6-sol (frontier) | $5.00/M input, $0.50 cached, $30.00/M output | [claim:clm_029] |
| gpt-5.6-terra batch tier | $1.25/M input, $7.50/M output (half standard) | [claim:clm_031] |
| Claude Haiku 4.5 | $1/M in, $5/M out; cache write $1.25/$2, cache hit $0.10/M | [claim:clm_012] |
| Regional (data-residency) endpoints | +10% uplift on eligible models released on/after 2026-03-05 | [claim:clm_032] |
| Built-in web-search tool (gpt-4o-mini / gpt-4.1-mini) | fixed 8,000-input-token block per call | [claim:clm_030] |

### Caching multipliers

| Cache mechanism | Multiplier / rule | Evidence |
|---|---|---|
| Cache read (hit) | 0.1x base input token price | [claim:clm_009] |
| 5-minute cache write | 1.25x base input | [claim:clm_010] |
| Default cache TTL | 5 minutes, refreshed free on use; 1-hour TTL at extra cost | [claim:clm_011] |
| Cached prefix scope | Entire prefix (tools -> system -> messages) up to the cache_control block | [claim:clm_013] |

### Derived per-operation cost tied to subscription economics

**Inference:** Per-pattern extraction cost (~25k input + ~8k structured-IR output tokens) ranges from ~$0.006 on Gemini 2.5 Flash-Lite ($0.10/$0.40 per M) to ~$0.028 on Gemini 2.5 Flash, ~$0.073 on gpt-5.6-luna, and ~$0.15 on Gemini 3.1 Pro, each roughly halving under batch tier. [claim:clm_inf05]
**Inference:** At these token prices LLM extraction is not the binding cost for a $9.99-$19.99/month premium tier (a $9.99 plan covers hundreds of Flash-tier extractions); the real cost driver and metering target is server GPU mesh relaxation, not text extraction. [claim:clm_inf06]
**Inference:** Caching by pattern hash cuts marginal server cost sharply: identical prompt prefixes bill cache hits at 0.1x input (a ~90% reduction), and cross-user reuse of precomputed meshes/renders keyed by pattern hash drops a popular pattern's repeat cost toward storage+egress only. [claim:clm_inf07]

### Subscription and metering reference (Adobe Firefly comparable)

| Firefly plan / mechanism | Value | Evidence |
|---|---|---|
| Firefly Standard / Pro entry tiers | US$9.99/mo / US$19.99/mo | [claim:clm_049] |
| Firefly Pro Plus | US$49.99/mo regular; US$34.97/mo promo first year | [claim:clm_046] |
| Firefly Premium | US$199.99/mo regular; US$139.91/mo promo first year | [claim:clm_047] |
| Generative credits by tier | 2,000 / 4,000 / 10,000 / 50,000 per month | [claim:clm_048] |
| Per-operation metering | caps scale by tier (e.g. 5-sec video 20/40/100) | [claim:clm_050] |
| Credit exhaustion behavior | directs users to purchase add-on credit plans | [claim:clm_051] |

**Inference:** KnitWit premium should adopt Adobe Firefly-style per-operation credit metering, capping expensive operations (mesh generation, image render) by tier rather than offering unlimited compute, with credit add-ons for overage. [claim:clm_inf08]
**Speculation:** With batch-tier extraction and pattern-hash caching, a KnitWit premium tier priced in the Firefly $9.99-$19.99 band is projected to be gross-margin-positive at typical hobbyist usage (a few dozen extractions plus mostly-cached previews per month), with margin risk only from heavy uncached mesh-generation users. [claim:clm_spec03]

## Recommended architecture

### Self-hosted vs cloud APIs

**Inference:** Use pay-per-use cloud LLM APIs for extraction (no infra, batch discount, elastic) and reserve self-hosting for the mesh-relaxation GPU tier only if volume justifies it, since the Ceres-based solver is open-source and deterministic with no per-token cost. [claim:clm_inf10]

### Sync vs queue+callback

**Inference:** The architecture should split by job duration: PDF/URL extraction and mesh relaxation run as queue+callback async jobs (enqueue, return immediately, client polls), while counters, step mode, and cached-preview rendering run synchronously on-device. [claim:clm_inf09]
Ray Serve runs long-running inference asynchronously via background task processing so HTTP APIs stay responsive while work runs in the background. [claim:clm_020]
For workloads that exceed typical HTTP timeouts (e.g. video processing, large document indexing), the system enqueues work in a background queue and immediately returns a quick response. [claim:clm_021]
Async task execution decouples request lifetime from compute time while still leveraging Serve's scalability. [claim:clm_022]
A background worker (@task_consumer) is a Serve deployment that consumes and executes tasks pulled from a queue, independent of incoming HTTP requests. [claim:clm_023]
Backpressure is controlled by max_ongoing_requests on the consumer deployment, capping how many tasks each replica processes simultaneously; failed tasks retry up to max_retries then route to a dead-letter queue. [claim:clm_024]
Clients poll for results rather than blocking: the API enqueues tasks via enqueue_task_sync and fetches status via get_task_status_sync. [claim:clm_025]
A built-in AsyncInferenceAutoscalingPolicy polls the message broker for queue length and scales replicas to match demand from pending and in-flight requests. [claim:clm_026]

### Caching by pattern hash

**Inference:** Caching by pattern hash cuts marginal server cost sharply: identical prompt prefixes bill cache hits at 0.1x input (a ~90% reduction), and cross-user reuse of precomputed meshes/renders keyed by pattern hash drops a popular pattern's repeat cost toward storage+egress only. [claim:clm_inf07]
Caching references the entire prefix — tools, then system, then messages — up to and including the block marked with cache_control, so a stable prefix maximizes hit rate. [claim:clm_013]

### Resolving the long-context (>4096-token) extraction path

**Inference:** The >4096-token extraction path should be resolved by server-side large-context structured extraction directly into Crochet IR, NOT by on-device chunk-and-summarize, because summarization across sessions risks dropping exact per-round stitch counts that the IR's expected_stitch_count requires. [claim:clm_inf11]
**Inference:** For long-context PDF/URL extraction, GPT-5 mini (400k-token window, 272k input) and Gemini 3.1 Pro (tiered <=200k / >200k) can ingest whole patterns that the 4096-token on-device model cannot, and all viable cloud options support structured output for direct Crochet IR emission. [claim:clm_inf04]
**Inference:** When a pattern is too large even for one server pass (e.g., pattern books), chunk adaptively/semantically along Crochet IR round and piece boundaries rather than by fixed token windows, since adaptive chunking beat fixed-length on retrieval (F1 0.64 vs 0.24). [claim:clm_inf12]

## Privacy & offline posture

**Inference:** Required privacy posture: route user photos and user-private pattern imports through zero-retention, no-train endpoints with optional data-residency (the ~10% regional uplift is acceptable), and constrain any shared/ingested patterns to designer opt-in or license per the #1 copyright landmine. [claim:clm_inf13]
Apple states it does not use users' private personal data or user interactions to train its foundation models. [claim:clm_058]
Regional processing (data residency) endpoints add a 10% price uplift for eligible models released on or after March 5, 2026. [claim:clm_032]
Pattern IP/copyright is flagged the #1 business landmine, constraining ingestion to designer opt-in, licensing, or user-private imports. [claim:clm_042]
**Inference:** Offline degradation should let cached Crochet IR, precomputed meshes, counters, and step mode run fully on-device, while new extraction and mesh-generation jobs queue locally and dispatch when connectivity returns, with .exceededContextWindowSize caught to fail over to the server path. [claim:clm_inf14]
Exceeding the window makes the framework throw an .exceededContextWindowSize error and the session can no longer respond, so apps must catch it (e.g., by starting a new session). [claim:clm_008]

## Analysis & derivation

### On-device context budget (why extraction cannot run locally)

Apple's on-device foundation model has a context window of 4096 tokens per LanguageModelSession. [claim:clm_001]
Apple's on-device system foundation model supports a context window of up to 4,096 tokens per session instance. [claim:clm_059]
A token is roughly 3-4 characters in Latin-alphabet languages like English, but roughly one character per token for multi-byte languages such as Chinese, Japanese, and Korean. [claim:clm_002]
A single token maps to roughly three or four characters in English/Spanish/German, and one token per character in Japanese/Chinese/Korean. [claim:clm_060]
All input and output count against the session context window, including instructions, prompts, tool schemas/inputs/outputs, Generable schemas, and every model response. [claim:clm_003]
Instructions, all prompts, and all outputs jointly count against the single 4,096-token context window, so prompt plus response must fit within one budget. [claim:clm_061]
The tokenCount(for:) API lets an app measure token consumption of its instructions, prompts, tools, schema, and transcript entries before sending. [claim:clm_004]
For oversized tasks Apple recommends splitting into smaller chunks summarized in separate sessions, carrying the previous summary forward in the prompt to preserve context, then reassembling. [claim:clm_005]
Data too large for a single context window must be split into smaller chunks, each processed in a separate session, then recombined. [claim:clm_062]
For large knowledge bases Apple recommends RAG (chunk + embed) integrated via Core ML, with the Natural Language framework providing tokenizing and embedding APIs, instead of stuffing the window. [claim:clm_006]
Vectorizing a whole knowledge base is computationally heavy, so Apple advises running it as a separate data-preparation process or serving embeddings from a server rather than at request time. [claim:clm_007]
The framework provides guided generation to produce a developer-defined custom Swift data structure instead of raw string output (structured output). [claim:clm_063]

### On-device vs server model capabilities

Apple ships a compact on-device model of roughly 3 billion parameters alongside a separate mixture-of-experts server model whose architecture is tailored for Private Cloud Compute. [claim:clm_052]
The server model uses a parallel-track mixture-of-experts (PT-MoE) design that reduces synchronization overhead. [claim:clm_053]
Architecture changes to the on-device model reduce KV cache memory usage by 37.5% and improve time-to-first-token. [claim:clm_054]
The on-device model is compressed to 2 bits per weight using Quantization-Aware Training. [claim:clm_055]
The on-device model is optimized for text tasks such as summarization, entity extraction, text understanding, and refinement. [claim:clm_056]
Apple states the on-device model is not intended to serve as a general-knowledge chatbot, implying heavier general reasoning is not its role. [claim:clm_057]
The existing design stance already earmarks on-device AI for small parsing helpers while allowing heavy generation to run cloud-based. [claim:clm_039]

### Cloud model fit for offloaded extraction

GPT-5 mini exposes a 400,000-token context window with up to 272,000 input tokens and 128,000 output tokens. [claim:clm_036]
GPT-5 mini supports structured outputs, function calling, and web search, making it suitable for offloaded structuring and tool-driven tasks. [claim:clm_037]
GPT-5 mini supports the batch endpoint alongside chat_completions and responses, enabling asynchronous/queued offloaded workloads. [claim:clm_035]
GPT-5 mini is positioned as a faster, more cost-efficient GPT-5 variant targeted at cost-sensitive, low-latency, high-volume workloads. [claim:clm_033]
GPT-5 mini is a reasoning-type model whose current snapshot is gpt-5-mini-2025-08-07 with a 2024-05-31 knowledge cutoff. [claim:clm_038]
The page exposes both a Free Tier (free-of-charge input/output for development) and a Paid Tier, and batch pricing is consistently ~50% of the interactive standard rate across models. [claim:clm_019]

### Chunking strategy for oversized documents

RAG output quality depends on how source documents are segmented before indexing, and fixed-length chunks can split concepts or add noise that reduces retrieval precision. [claim:clm_064]
Naive equal-sized chunking dilutes meaning and surfaces incomplete or misleading information, lowering retrieval precision. [claim:clm_065]
Advanced chunking methods (semantic, proposition-based, adaptive) improve retrieval by organizing text around meaningful units rather than token counts. [claim:clm_066]
Adaptive chunking substantially outperformed the fixed-length baseline on retrieval metrics (precision 0.50, recall 0.88, F1 0.64 vs 0.17, 0.40, 0.24). [claim:clm_067]
Fixed recursive character windowing performed worst, fragmenting coupled statements and duplicating content across overlapping windows, yielding the lowest scores. [claim:clm_068]
The adaptive method's added preprocessing stayed computationally practical by reusing pre-computed sentence embeddings and applying a single linear boundary pass. [claim:clm_069]

### Pattern->3D compute cost (why mesh relaxation is the offload target)

The method takes a written crochet pattern as input, translates it into a graph, and produces a 3D model matching the hand-crocheted object's shape and size. [claim:clm_070]
Each stitch is a node in the pattern graph and the physical connections between stitches (sequential and working) are the edges. [claim:clm_071]
The force-directed layout is a non-linear least-squares optimization that minimizes two energy functions (edge length and local curvature). [claim:clm_072]
The layout builds on the Isenburg et al. graph-inflation algorithm, which inflates a planar graph by assigning edge lengths and minimizing curvature to maximize volume. [claim:clm_074]
The implementation solves the optimization with the Ceres Solver library, using a static blend weight lambda = 0.65 for most pieces. [claim:clm_075]
The iterative linear solver is the dominant compute cost of the application, which the authors flag as a concern for general-audience usability. [claim:clm_073]

### IR alignment

A structured Crochet IR is required as the parse->render contract, with rows[] as sequences of stitch ops and counts. [claim:clm_041]
The spec scopes 3D as structural geometry (stitch-graph/mesh approximation) rendered without simulating actual yarn physics. [claim:clm_040]

## Decision rules & recommendations

**Inference:** LLM pattern structuring/extraction from PDFs and URLs must be offloaded to a server because typical multi-page patterns exceed Apple's 4096-token on-device window, which throws .exceededContextWindowSize and halts the session. [claim:clm_inf01]
**Inference:** Interactive 3D rendering, stitch counters, and step mode should stay on-device (Metal) because they are latency-sensitive, low-compute, and touch no data that requires cloud reasoning. [claim:clm_inf02]
**Inference:** Heavy mesh generation and physics relaxation of stitch graphs should be offloaded to a server GPU/CPU as an asynchronous job, not run interactively on-device, because the iterative least-squares solver is the dominant compute cost of the layout. [claim:clm_inf03]
**Inference:** The >4096-token extraction path should be resolved by server-side large-context structured extraction directly into Crochet IR, NOT by on-device chunk-and-summarize, because summarization across sessions risks dropping exact per-round stitch counts that the IR's expected_stitch_count requires. [claim:clm_inf11]
**Inference:** KnitWit premium should adopt Adobe Firefly-style per-operation credit metering, capping expensive operations (mesh generation, image render) by tier rather than offering unlimited compute, with credit add-ons for overage. [claim:clm_inf08]

## Academic feasibility vs product readiness

**Inference:** Pattern->3D via force-directed layout is academically demonstrated but not product-ready for interactive mobile use; the product path is server-side precompute plus pattern-hash caching, delivering a static renderable mesh to the device rather than solving on-device in real time. [claim:clm_inf15]
The method takes a written crochet pattern as input, translates it into a graph, and produces a 3D model matching the hand-crocheted object's shape and size. [claim:clm_070]
The iterative linear solver is the dominant compute cost of the application, which the authors flag as a concern for general-audience usability. [claim:clm_073]
The spec cites peer-reviewed work (ACM/AmiGo) generating amigurumi instructions from a closed 3D model, seed point, and stitch size as feasibility basis. [claim:clm_043]
The spec cites a 2025 force-directed graph-layout paper as basis for turning written patterns into a 3D representation. [claim:clm_044]
The spec scopes 3D as structural geometry (stitch-graph/mesh approximation) rendered without simulating actual yarn physics. [claim:clm_040]

## Contradictions & open disagreements

**Inference:** The >4096-token extraction path should be resolved by server-side large-context structured extraction directly into Crochet IR, NOT by on-device chunk-and-summarize, because summarization across sessions risks dropping exact per-round stitch counts that the IR's expected_stitch_count requires. [claim:clm_inf11]
For oversized tasks Apple recommends splitting into smaller chunks summarized in separate sessions, carrying the previous summary forward in the prompt to preserve context, then reassembling. [claim:clm_005]
GPT-5 mini is positioned as a faster, more cost-efficient GPT-5 variant targeted at cost-sensitive, low-latency, high-volume workloads. [claim:clm_033]
OpenAI recommends starting new low-latency, high-volume workloads on GPT-5.6 Terra rather than GPT-5 mini, indicating a newer preferred tier for offloaded high-volume work. [claim:clm_034]

## Risks

**Speculation:** Running the stitch-graph physics relaxation on-device via Metal would likely blow the interactive latency budget for non-trivial amigurumi on current phones (risk severity high, likelihood high); mitigation is mandatory server offload with a queued job and cached result. [claim:clm_spec01]
**Speculation:** Cross-user cache sharing keyed by pattern hash could leak that a specific user possesses a copyrighted or private pattern (risk severity medium, likelihood medium); mitigation is to share precomputed meshes/renders only for licensed/public patterns and salt user-private hashes so they never collide across accounts. [claim:clm_spec02]
**Speculation:** With batch-tier extraction and pattern-hash caching, a KnitWit premium tier priced in the Firefly $9.99-$19.99 band is projected to be gross-margin-positive at typical hobbyist usage (a few dozen extractions plus mostly-cached previews per month), with margin risk only from heavy uncached mesh-generation users. [claim:clm_spec03]
Parsing ambiguity (inconsistent abbreviations, formatting, charts, freeform notes) is a named risk motivating structured/validator-gated extraction. [claim:clm_045]
Pattern IP/copyright is flagged the #1 business landmine, constraining ingestion to designer opt-in, licensing, or user-private imports. [claim:clm_042]

## Prototype experiments & decision-gate relevance

**Inference:** These placement findings most de-risk gates G2 (Crochet IR viability) and G3 (pattern->3D viability); the highest-value next experiments are EXP-004 (IR->stitch graph) and EXP-005 (stitch-graph->approximate-3D) run server-side to measure real solver latency and validate the async precompute+cache design. [claim:clm_inf16]
**Inference:** The >4096-token extraction path should be resolved by server-side large-context structured extraction directly into Crochet IR, NOT by on-device chunk-and-summarize, because summarization across sessions risks dropping exact per-round stitch counts that the IR's expected_stitch_count requires. [claim:clm_inf11]
A structured Crochet IR is required as the parse->render contract, with rows[] as sequences of stitch ops and counts. [claim:clm_041]
The spec cites peer-reviewed work (ACM/AmiGo) generating amigurumi instructions from a closed 3D model, seed point, and stitch size as feasibility basis. [claim:clm_043]
The spec cites a 2025 force-directed graph-layout paper as basis for turning written patterns into a 3D representation. [claim:clm_044]

## Open questions

- What is the measured on-device Metal latency for stitch-graph relaxation on a non-trivial amigurumi, and does it confirm the mandatory-offload speculation?
- What is the real distribution of extractions vs uncached mesh-generation jobs per premium user per month, on which the margin projection depends?
- What server solver latency do EXP-004 and EXP-005 produce, and does it confirm the queue+callback plus pattern-hash-cache design?
- Where should the licensed/public vs user-private boundary sit for cross-user cache sharing to avoid leaking pattern ownership?
- Which single long-context model (GPT-5 mini vs Gemini 3.1 Pro) best preserves exact per-round stitch counts in structured Crochet IR extraction?

## Sources

- src_20260710_offload_00: TN3193: Managing the on-device foundation model's context window
- src_20260710_offload_07: Prompt caching - Claude Platform Docs
- src_20260710_offload_10: Gemini Developer API Pricing
- src_20260710_offload_08: Asynchronous Inference - Ray Serve
- src_20260710_offload_02: OpenAI API Pricing
- src_20260710_offload_11: GPT-5 mini model — OpenAI API
- src_20260710_offload_04: KnitWit design-spec.md (project seed)
- src_20260710_offload_03: Compare plans that include generative AI | Adobe Firefly
- src_20260710_offload_06: Updates to Apple's On-Device and Server Foundation Language Models
- src_20260710_offload_05: Generating content and performing tasks with Foundation Models
- src_20260710_offload_09: Comparative Evaluation of Advanced Chunking for Retrieval-Augmented Generation in Large Language Models for Clinical Decision Support
- src_20260710_offload_01: Modeling Crochet Patterns with a Force-directed Graph Layout
