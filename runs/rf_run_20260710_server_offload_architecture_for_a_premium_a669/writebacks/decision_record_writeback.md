---
id: mwb_20260711_dr_server_offload_architecture_for_a
evidence_bundle_id: bundle_20260711_intent_research_20260710_server_offload_architec
target_page: meatywiki/decisions/server_offload_architecture_for_a_knitwit.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260710_server_offload_architecture_for_a_premium_a669: A 4096-token
  window (shared by instructions+prompt+output) cannot hold a multi-page PDF pattern plus a structured
  Croche'
key_claims:
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf14
  include: true
- claim_id: clm_inf16
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf15
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_001
  - clm_059
  - clm_061
  - clm_008
  - clm_039
  - clm_040
  - clm_054
  - clm_072
  - clm_073
  - clm_075
  - clm_070
  - clm_021
  - clm_048
  - clm_050
  - clm_051
  - clm_020
  - clm_025
  - clm_002
  - clm_005
  - clm_062
  - clm_036
  - clm_063
  - clm_041
  - clm_067
  - clm_066
  - clm_068
  - clm_045
  - clm_058
  - clm_032
  - clm_042
  - clm_007
  - clm_022
  - clm_037
  - clm_017
  - clm_016
  - clm_015
  - clm_014
  - clm_028
  - clm_019
  - clm_031
  - clm_049
  - clm_009
  - clm_013
  - clm_018
  - clm_027
  - clm_074
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Server Offload Architecture for a KnitWit/LoopNest Premium Tier: Workload Placement, Cost Model, Hybrid Architecture, and Privacy/Offline Posture

## Context

- Apple's on-device foundation model has a context window of 4096 tokens per LanguageModelSession. [claim:clm_001]
- A token is roughly 3-4 characters in Latin-alphabet languages like English, but roughly one character per token for multi-byte languages such as Chinese, Japanese, and Korean. [claim:clm_002]
- All input and output count against the session context window, including instructions, prompts, tool schemas/inputs/outputs, Generable schemas, and every model response. [claim:clm_003]
- The tokenCount(for:) API lets an app measure token consumption of its instructions, prompts, tools, schema, and transcript entries before sending. [claim:clm_004]
- For oversized tasks Apple recommends splitting into smaller chunks summarized in separate sessions, carrying the previous summary forward in the prompt to preserve context, then reassembling. [claim:clm_005]
- For large knowledge bases Apple recommends RAG (chunk + embed) integrated via Core ML, with the Natural Language framework providing tokenizing and embedding APIs, instead of stuffing the window. [claim:clm_006]
- Vectorizing a whole knowledge base is computationally heavy, so Apple advises running it as a separate data-preparation process or serving embeddings from a server rather than at request time. [claim:clm_007]
- Exceeding the window makes the framework throw an .exceededContextWindowSize error and the session can no longer respond, so apps must catch it (e.g., by starting a new session). [claim:clm_008]
- Cache read (hit) tokens are priced at 0.1x the base input token price. [claim:clm_009]
- 5-minute cache write tokens cost 1.25x base input, and 1-hour cache write tokens cost 2x base input. [claim:clm_010]
- The default cache TTL is 5 minutes and is refreshed at no additional cost on each use; a 1-hour TTL is available at extra cost. [claim:clm_011]
- For Claude Haiku 4.5, base input is $1/MTok, 5m cache writes $1.25/MTok, 1h cache writes $2/MTok, cache hits/refreshes $0.10/MTok, and output $5/MTok. [claim:clm_012]
- Caching references the entire prefix — tools, then system, then messages — up to and including the block marked with cache_control, so a stable prefix maximizes hit rate. [claim:clm_013]
- Gemini 2.5 Flash-Lite costs $0.10/M input (text/image/video) and $0.40/M output at standard tier, halving to $0.05/$0.20 under batch tier. [claim:clm_014]
- Gemini 2.5 Flash costs $0.30/M input (text/image/video) and $2.50/M output at standard tier, with batch tier at $0.15/$1.25. [claim:clm_015]
- Gemini 3.5 Flash costs $1.50/M input and $9.00/M output at standard tier, with batch tier at $0.75/$4.50 (a consistent 50% reduction). [claim:clm_016]
- Gemini 3.1 Pro Preview is tiered by prompt length: $2.00/M input and $12.00/M output for prompts <=200k tokens, rising to $4.00/$18.00 above 200k. [claim:clm_017]
- Gemini 2.5 Flash Image is priced at $0.039 per image standard, halving to $0.0195 per image under batch. [claim:clm_018]
- The page exposes both a Free Tier (free-of-charge input/output for development) and a Paid Tier, and batch pricing is consistently ~50% of the interactive standard rate across models. [claim:clm_019]
- Ray Serve runs long-running inference asynchronously via background task processing so HTTP APIs stay responsive while work runs in the background. [claim:clm_020]
- For workloads that exceed typical HTTP timeouts (e.g. video processing, large document indexing), the system enqueues work in a background queue and immediately returns a quick response. [claim:clm_021]
- Async task execution decouples request lifetime from compute time while still leveraging Serve's scalability. [claim:clm_022]
- A background worker (@task_consumer) is a Serve deployment that consumes and executes tasks pulled from a queue, independent of incoming HTTP requests. [claim:clm_023]
- Backpressure is controlled by max_ongoing_requests on the consumer deployment, capping how many tasks each replica processes simultaneously; failed tasks retry up to max_retries then route to a dead-letter queue. [claim:clm_024]
- Clients poll for results rather than blocking: the API enqueues tasks via enqueue_task_sync and fetches status via get_task_status_sync. [claim:clm_025]
- A built-in AsyncInferenceAutoscalingPolicy polls the message broker for queue length and scales replicas to match demand from pending and in-flight requests. [claim:clm_026]
- gpt-5.6-terra (workhorse) lists at $2.50 per 1M input tokens, $0.25 cached input, and $15.00 per 1M output tokens on the standard tier. [claim:clm_027]
- gpt-5.6-luna (cheap/fast) lists at $1.00 per 1M input tokens, $0.10 cached input, and $6.00 per 1M output tokens on the standard tier. [claim:clm_028]
- gpt-5.6-sol (frontier) lists at $5.00 per 1M input tokens, $0.50 cached input, and $30.00 per 1M output tokens on the standard tier. [claim:clm_029]
- For gpt-4o-mini and gpt-4.1-mini using the non-preview web search tool, search content is billed as a fixed 8,000-input-token block per call. [claim:clm_030]
- Batch-tier pricing for gpt-5.6-terra is exactly half the standard tier ($1.25 input / $7.50 output per 1M), reflecting the documented 50% batch discount. [claim:clm_031]
- Regional processing (data residency) endpoints add a 10% price uplift for eligible models released on or after March 5, 2026. [claim:clm_032]
- GPT-5 mini is positioned as a faster, more cost-efficient GPT-5 variant targeted at cost-sensitive, low-latency, high-volume workloads. [claim:clm_033]
- OpenAI recommends starting new low-latency, high-volume workloads on GPT-5.6 Terra rather than GPT-5 mini, indicating a newer preferred tier for offloaded high-volume work. [claim:clm_034]
- GPT-5 mini supports the batch endpoint alongside chat_completions and responses, enabling asynchronous/queued offloaded workloads. [claim:clm_035]
- GPT-5 mini exposes a 400,000-token context window with up to 272,000 input tokens and 128,000 output tokens. [claim:clm_036]
- GPT-5 mini supports structured outputs, function calling, and web search, making it suitable for offloaded structuring and tool-driven tasks. [claim:clm_037]
- GPT-5 mini is a reasoning-type model whose current snapshot is gpt-5-mini-2025-08-07 with a 2024-05-31 knowledge cutoff. [claim:clm_038]
- The existing design stance already earmarks on-device AI for small parsing helpers while allowing heavy generation to run cloud-based. [claim:clm_039]
- The spec scopes 3D as structural geometry (stitch-graph/mesh approximation) rendered without simulating actual yarn physics. [claim:clm_040]
- A structured Crochet IR is required as the parse->render contract, with rows[] as sequences of stitch ops and counts. [claim:clm_041]
- Pattern IP/copyright is flagged the #1 business landmine, constraining ingestion to designer opt-in, licensing, or user-private imports. [claim:clm_042]
- The spec cites peer-reviewed work (ACM/AmiGo) generating amigurumi instructions from a closed 3D model, seed point, and stitch size as feasibility basis. [claim:clm_043]
- The spec cites a 2025 force-directed graph-layout paper as basis for turning written patterns into a 3D representation. [claim:clm_044]
- Parsing ambiguity (inconsistent abbreviations, formatting, charts, freeform notes) is a named risk motivating structured/validator-gated extraction. [claim:clm_045]
- Adobe Firefly Pro Plus is priced at US$49.99/month (regular rate), with a promotional first-year rate of US$34.97/month. [claim:clm_046]
- Adobe Firefly Premium is priced at US$199.99/month (regular rate), with a promotional first-year rate of US$139.91/month. [claim:clm_047]
- Generative credits are a fixed monthly allocation that scales by plan tier: 2,000 (Standard), 4,000 (Pro), 10,000 (Pro Plus), and 50,000 (Premium) per month. [claim:clm_048]
- The entry Firefly tiers are Standard at US$9.99/month and Pro at US$19.99/month, establishing the low end of the credit-metered pricing ladder. [claim:clm_049]
- Metering is per operation type: caps scale by tier (e.g., 5-second video generations up to 20/40/100), demonstrating differentiated allowances for expensive generative operations. [claim:clm_050]
- When a plan's generative credits are exhausted, Adobe directs users to purchase credit add-on plans to continue generating, rather than describing an on-page reduced-speed continuation. [claim:clm_051]
- Apple ships a compact on-device model of roughly 3 billion parameters alongside a separate mixture-of-experts server model whose architecture is tailored for Private Cloud Compute. [claim:clm_052]
- The server model uses a parallel-track mixture-of-experts (PT-MoE) design that reduces synchronization overhead. [claim:clm_053]
- Architecture changes to the on-device model reduce KV cache memory usage by 37.5% and improve time-to-first-token. [claim:clm_054]
- The on-device model is compressed to 2 bits per weight using Quantization-Aware Training. [claim:clm_055]
- The on-device model is optimized for text tasks such as summarization, entity extraction, text understanding, and refinement. [claim:clm_056]
- Apple states the on-device model is not intended to serve as a general-knowledge chatbot, implying heavier general reasoning is not its role. [claim:clm_057]
- Apple states it does not use users' private personal data or user interactions to train its foundation models. [claim:clm_058]
- Apple's on-device system foundation model supports a context window of up to 4,096 tokens per session instance. [claim:clm_059]
- A single token maps to roughly three or four characters in English/Spanish/German, and one token per character in Japanese/Chinese/Korean. [claim:clm_060]
- Instructions, all prompts, and all outputs jointly count against the single 4,096-token context window, so prompt plus response must fit within one budget. [claim:clm_061]
- Data too large for a single context window must be split into smaller chunks, each processed in a separate session, then recombined. [claim:clm_062]
- The framework provides guided generation to produce a developer-defined custom Swift data structure instead of raw string output (structured output). [claim:clm_063]
- RAG output quality depends on how source documents are segmented before indexing, and fixed-length chunks can split concepts or add noise that reduces retrieval precision. [claim:clm_064]
- Naive equal-sized chunking dilutes meaning and surfaces incomplete or misleading information, lowering retrieval precision. [claim:clm_065]
- Advanced chunking methods (semantic, proposition-based, adaptive) improve retrieval by organizing text around meaningful units rather than token counts. [claim:clm_066]
- Adaptive chunking substantially outperformed the fixed-length baseline on retrieval metrics (precision 0.50, recall 0.88, F1 0.64 vs 0.17, 0.40, 0.24). [claim:clm_067]
- Fixed recursive character windowing performed worst, fragmenting coupled statements and duplicating content across overlapping windows, yielding the lowest scores. [claim:clm_068]
- The adaptive method's added preprocessing stayed computationally practical by reusing pre-computed sentence embeddings and applying a single linear boundary pass. [claim:clm_069]
- The method takes a written crochet pattern as input, translates it into a graph, and produces a 3D model matching the hand-crocheted object's shape and size. [claim:clm_070]
- Each stitch is a node in the pattern graph and the physical connections between stitches (sequential and working) are the edges. [claim:clm_071]
- The force-directed layout is a non-linear least-squares optimization that minimizes two energy functions (edge length and local curvature). [claim:clm_072]
- The iterative linear solver is the dominant compute cost of the application, which the authors flag as a concern for general-audience usability. [claim:clm_073]
- The layout builds on the Isenburg et al. graph-inflation algorithm, which inflates a planar graph by assigning edge lengths and minimizing curvature to maximize volume. [claim:clm_074]
- The implementation solves the optimization with the Ceres Solver library, using a static blend weight lambda = 0.65 for most pieces. [claim:clm_075]

## Decision

LLM pattern structuring/extraction from PDFs and URLs must be offloaded to a server because typical multi-page patterns exceed Apple's 4096-token on-device window, which throws .exceededContextWindowSize and halts the session. [claim:clm_inf01]

## Rationale

- A 4096-token window (shared by instructions+prompt+output) cannot hold a multi-page PDF pattern plus a structured Crochet IR response; exceeding it errors out, so full-document extraction belongs on a large-context server model rather than on-device. [claim:clm_inf01]
- The spec scopes 3D as structural geometry without yarn physics (cheap to render) and already earmarks on-device for small helpers; counters/step-mode need instant response and no server round-trip, so keeping them local minimizes latency and preserves offline use. [claim:clm_inf02]
- The force-directed layout is a non-linear least-squares optimization (Ceres Solver, lambda=0.65) whose iterative solver the authors flag as the dominant cost and a usability concern; such long-running compute fits a server background queue that returns immediately, not an interactive mobile thread. [claim:clm_inf03]
- Firefly meters per operation type with tier-scaled caps and add-on purchases on exhaustion; because mesh relaxation is the dominant, unbounded cost, metering it per-operation (not per-token) aligns spend with the true cost driver. [claim:clm_inf08]
- Ray Serve's async pattern (enqueue_task_sync + poll get_task_status_sync) exists precisely for work exceeding HTTP timeouts like large document indexing; the solver's long runtime and multi-page extraction both fit this, whereas instant interactions must not block on a server. [claim:clm_inf09]
- Apple's on-device remedy is chunking + carried-forward summaries, which is lossy for precise numeric stitch ops; a single large-context server pass with guided/structured output preserves every row's ops and counts needed by the parse->render IR contract. [claim:clm_inf11]
- Fixed recursive windowing scored worst by fragmenting coupled statements; a round's ops must stay intact, so boundary-aware chunking (aligned to pieces/rounds) both preserves meaning and matches the IR's natural units, mitigating parsing-ambiguity risk. [claim:clm_inf12]
- Apple's no-private-data-training stance sets the user expectation; regional endpoints exist at a 10% uplift for residency; copyright is flagged the top business risk, so user-private and licensed-only ingestion plus non-training processing is the minimum defensible posture. [claim:clm_inf13]
- Async job decoupling means offloaded work can be enqueued and deferred; on-device rendering/counters need no network; catching the context-window error is the natural trigger to escalate an oversized on-device parse to the queued server job. [claim:clm_inf14]
- The IR contract (G2) and the graph->3D step (G3) are exactly where the solver-cost and structured-extraction decisions bite; running EXP-004/005 on a server harness produces the latency numbers needed to confirm queue+callback and caching before committing MVP scope. [claim:clm_inf16]
- GPT-5 mini's 400k/272k window and Gemini 3.1 Pro's length-tiered pricing both dwarf 4096 tokens; structured-output/function-calling support across GPT-5 mini and Gemini lets extraction return a validated IR object rather than free text. [claim:clm_inf04]
- Applying published per-M input/output rates to a representative 25k-in/8k-out pattern: Flash-Lite 25k*0.10+8k*0.40=~$0.0057; Flash ~$0.0275; luna ~$0.073; 3.1 Pro ~$0.146; documented ~50% batch discount halves all. [claim:clm_inf05]
- Firefly's low tiers ($9.99/$19.99) set a realistic premium anchor; at ~$0.006-$0.028 per extraction a single subscription funds hundreds of extractions, so margin risk concentrates in the compute-dominant solver, which is what per-operation caps should meter. [claim:clm_inf06]
- Cache reads at 0.1x base input plus stable-prefix caching make re-extraction of the same document ~10% of first-run input cost; storing the solver's expensive mesh output once and serving it to later requests avoids recomputing the dominant-cost relaxation entirely. [claim:clm_inf07]
- Cloud LLM pricing with ~50% batch tiers makes bursty extraction cheapest as a metered API; the mesh solver (Ceres, open library) carries fixed compute but no token cost, so self-hosting it becomes economical only past a volume threshold where reserved GPU beats per-call cloud GPU. [claim:clm_inf10]
- The paper shows the pattern->graph->3D method works (feasibility) but names the iterative solver as the dominant cost and a general-audience usability concern (not product-ready on mobile); precomputing server-side and caching the result reconciles the two. [claim:clm_inf15]

## Consequences

- Interactive 3D rendering, stitch counters, and step mode should stay on-device (Metal) because they are latency-sensitive, low-compute, and touch no data that requires cloud reasoning. [claim:clm_inf02]
- Heavy mesh generation and physics relaxation of stitch graphs should be offloaded to a server GPU/CPU as an asynchronous job, not run interactively on-device, because the iterative least-squares solver is the dominant compute cost of the layout. [claim:clm_inf03]
- KnitWit premium should adopt Adobe Firefly-style per-operation credit metering, capping expensive operations (mesh generation, image render) by tier rather than offering unlimited compute, with credit add-ons for overage. [claim:clm_inf08]
- The architecture should split by job duration: PDF/URL extraction and mesh relaxation run as queue+callback async jobs (enqueue, return immediately, client polls), while counters, step mode, and cached-preview rendering run synchronously on-device. [claim:clm_inf09]
- The >4096-token extraction path should be resolved by server-side large-context structured extraction directly into Crochet IR, NOT by on-device chunk-and-summarize, because summarization across sessions risks dropping exact per-round stitch counts that the IR's expected_stitch_count requires. [claim:clm_inf11]
- When a pattern is too large even for one server pass (e.g., pattern books), chunk adaptively/semantically along Crochet IR round and piece boundaries rather than by fixed token windows, since adaptive chunking beat fixed-length on retrieval (F1 0.64 vs 0.24). [claim:clm_inf12]
- Required privacy posture: route user photos and user-private pattern imports through zero-retention, no-train endpoints with optional data-residency (the ~10% regional uplift is acceptable), and constrain any shared/ingested patterns to designer opt-in or license per the #1 copyright landmine. [claim:clm_inf13]
- Offline degradation should let cached Crochet IR, precomputed meshes, counters, and step mode run fully on-device, while new extraction and mesh-generation jobs queue locally and dispatch when connectivity returns, with .exceededContextWindowSize caught to fail over to the server path. [claim:clm_inf14]
- These placement findings most de-risk gates G2 (Crochet IR viability) and G3 (pattern->3D viability); the highest-value next experiments are EXP-004 (IR->stitch graph) and EXP-005 (stitch-graph->approximate-3D) run server-side to measure real solver latency and validate the async precompute+cache design. [claim:clm_inf16]
- For long-context PDF/URL extraction, GPT-5 mini (400k-token window, 272k input) and Gemini 3.1 Pro (tiered <=200k / >200k) can ingest whole patterns that the 4096-token on-device model cannot, and all viable cloud options support structured output for direct Crochet IR emission. [claim:clm_inf04]
- Per-pattern extraction cost (~25k input + ~8k structured-IR output tokens) ranges from ~$0.006 on Gemini 2.5 Flash-Lite ($0.10/$0.40 per M) to ~$0.028 on Gemini 2.5 Flash, ~$0.073 on gpt-5.6-luna, and ~$0.15 on Gemini 3.1 Pro, each roughly halving under batch tier. [claim:clm_inf05]
- At these token prices LLM extraction is not the binding cost for a $9.99-$19.99/month premium tier (a $9.99 plan covers hundreds of Flash-tier extractions); the real cost driver and metering target is server GPU mesh relaxation, not text extraction. [claim:clm_inf06]
- Caching by pattern hash cuts marginal server cost sharply: identical prompt prefixes bill cache hits at 0.1x input (a ~90% reduction), and cross-user reuse of precomputed meshes/renders keyed by pattern hash drops a popular pattern's repeat cost toward storage+egress only. [claim:clm_inf07]
- Use pay-per-use cloud LLM APIs for extraction (no infra, batch discount, elastic) and reserve self-hosting for the mesh-relaxation GPU tier only if volume justifies it, since the Ceres-based solver is open-source and deterministic with no per-token cost. [claim:clm_inf10]
- Pattern->3D via force-directed layout is academically demonstrated but not product-ready for interactive mobile use; the product path is server-side precompute plus pattern-hash caching, delivering a static renderable mesh to the device rather than solving on-device in real time. [claim:clm_inf15]

## Links

- [[claim:clm_001]]
- [[claim:clm_059]]
- [[claim:clm_061]]
- [[claim:clm_008]]
- [[claim:clm_039]]
- [[claim:clm_040]]
- [[claim:clm_054]]
- [[claim:clm_072]]
- [[claim:clm_073]]
- [[claim:clm_075]]
- [[claim:clm_070]]
- [[claim:clm_021]]
- [[claim:clm_048]]
- [[claim:clm_050]]
- [[claim:clm_051]]
- [[claim:clm_020]]
- [[claim:clm_025]]
- [[claim:clm_002]]
- [[claim:clm_005]]
- [[claim:clm_062]]
- [[claim:clm_036]]
- [[claim:clm_063]]
- [[claim:clm_041]]
- [[claim:clm_067]]
- [[claim:clm_066]]
- [[claim:clm_068]]
- [[claim:clm_045]]
- [[claim:clm_058]]
- [[claim:clm_032]]
- [[claim:clm_042]]
- [[claim:clm_007]]
- [[claim:clm_022]]
- [[claim:clm_037]]
- [[claim:clm_017]]
- [[claim:clm_016]]
- [[claim:clm_015]]
- [[claim:clm_014]]
- [[claim:clm_028]]
- [[claim:clm_019]]
- [[claim:clm_031]]
- [[claim:clm_049]]
- [[claim:clm_009]]
- [[claim:clm_013]]
- [[claim:clm_018]]
- [[claim:clm_027]]
- [[claim:clm_074]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
