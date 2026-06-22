---
id: mwb_20260622_dr_ai_assisted_crochet_pattern_parsing
evidence_bundle_id: bundle_20260615_intent_research_20260614_what_is_the
target_page: meatywiki/decisions/ai_assisted_crochet_pattern_parsing_on.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_what_is_the_documented_accuracy_latency: Tokens/repeats
  are standardized (clm_031/032) so rules suffice for clean text; CrochetBench shows LLMs collapse on
  execu'
key_claims:
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf14
  include: true
- claim_id: clm_inf15
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_031
  - clm_032
  - clm_008
  - clm_012
  - clm_076
  - clm_044
  - clm_059
  - clm_037
  - clm_039
  - clm_014
  - clm_020
  - clm_033
  - clm_030
  - clm_034
  - clm_077
  - clm_005
  - clm_065
  - clm_069
  - clm_064
  - clm_045
  - clm_022
  - clm_027
  - clm_038
  - clm_042
  - clm_013
  - clm_003
  - clm_009
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: AI-Assisted Crochet Pattern Parsing: On-Device vs Cloud Capability Review

## Context

- PaddleOCR-VL is a 0.9B-parameter vision-language model combining a NaViT-style dynamic-resolution visual encoder with the ERNIE-4.5-0.3B language model. [claim:clm_001]
- The model supports 109 languages and is designed to recognize complex document elements including text, tables, formulas, and charts. [claim:clm_002]
- On OmniDocBench v1.5 it reports an overall score of 92.56, text edit distance 0.035, Table TEDS 89.76 / TEDS-S 93.52, formula CDM 91.43, and reading-order edit distance 0.043. [claim:clm_003]
- The authors claim state-of-the-art performance on both page-level document parsing and element-level recognition, reportedly surpassing much larger general VLMs. [claim:clm_004]
- Reported throughput is server-side: 1.2241 pages/s and 1881.2 tokens/s via the vLLM backend on a single NVIDIA A100, using about 43.7 GB of GPU memory. [claim:clm_005]
- The paper claims PaddleOCR-VL has consistent advantages in both processing speed and memory efficiency relative to compared systems. [claim:clm_006]
- It emits structured outputs per element type: tables in a structured (OTSL/HTML-style) representation, formulas as LaTeX, and charts as Markdown tables, with reading-order prediction. [claim:clm_007]
- On project-level crochet-to-CrochetPARADE program synthesis, even the strongest VLMs produce only 5-8% executable programs and most models fall below 3%. [claim:clm_008]
- Natural-language instruction generation is weak, with the best system (Gemini 2.5 Flash-Lite) reaching only 4.93% BLEU and 30.50% ChrF. [claim:clm_009]
- Stitch recognition from images is the strongest task for the models, with Claude Sonnet 4 achieving the highest F1 score of 60.94%. [claim:clm_010]
- Instruction-selection accuracy is modest, with most large and closed-source models clustering around 55-60% accuracy. [claim:clm_011]
- Errors made in early steps propagate irreversibly, with later correctness occurring mainly when the initial state happens to be valid, indicating reliance on continuation heuristics rather than genuine procedural reasoning. [claim:clm_012]
- Image grounding particularly aids interpretation of repeated motifs, symmetry, shaping, and termination conditions that are under-specified in text alone. [claim:clm_013]
- Larger models exhibit substantially higher rates of undefined-stitch errors, suggesting a tendency toward uncontrolled symbolic invention rather than disciplined DSL use. [claim:clm_014]
- The benchmark evaluates nine VLMs spanning ~3B-72B parameters - open models BLIP-2 Flan-T5 XL (3B), Gemma 3 (4B/27B), DeepSeek-VL (7B), Qwen2-VL (7B/72B) plus closed GPT-4o, Gemini 2.5 Flash-Lite, and Claude Sonnet 4 - from Li et al., University of Notre Dame (arXiv 2511.09483v2). [claim:clm_015]
- AmiGo generates human-executable crochet instructions from a closed triangle mesh plus a single user-specified point, producing a toy that approximates the input geometry. [claim:clm_016]
- The method's inputs are precisely a 3D mesh, a seed point, and a stitch width (gauge), bounding the problem with explicit parameters. [claim:clm_017]
- The input mesh is required to be a closed triangle mesh together with a seed vertex and a real-valued stitch width, formalizing a watertight-topology precondition. [claim:clm_018]
- The shape is automatically segmented into crochetable components joined by the join-as-you-go method, requiring no additional sewing. [claim:clm_019]
- The output is a structured pattern restricted to a fixed, small instruction set (single crochet, increase, decrease), i.e. deterministic structured output rather than free-form text. [claim:clm_020]
- The work frames inverse mesh-to-pattern design as a computationally grounded approach producing patterns, not general free-form generation. [claim:clm_021]
- SmolVLM (2B) reports the best memory usage among vision language models in transformers, requiring a minimum of 5.02 GB GPU RAM. [claim:clm_022]
- SmolVLM uses SmolLM2 1.7B as its language backbone, replacing the larger Llama 3.1 8B. [claim:clm_023]
- SmolVLM encodes each 384x384 image patch to 81 visual tokens. [claim:clm_024]
- Encoding a test prompt plus a single image takes ~1.2k tokens with SmolVLM versus ~16k tokens with Qwen2-VL. [claim:clm_025]
- Compared with Qwen2-VL, SmolVLM achieves 3.3-4.5x faster prefill throughput and 7.5-16x faster generation throughput. [claim:clm_026]
- SmolVLM benchmark accuracy: DocVQA 81.6, TextVQA 72.7, MMMU (val) 38.8, MathVista 44.6, MMStar 42.1. [claim:clm_027]
- All SmolVLM model checkpoints, datasets, training recipes, and tools are released under the Apache 2.0 license. [claim:clm_028]
- The CYC list is the canonical published abbreviation reference used by yarn-industry designers and publishers, and its definitions reflect U.S. crochet terminology. [claim:clm_029]
- Core stitch tokens are defined as ch=chain stitch, sc=single crochet, hdc=half double crochet, dc=double crochet, tr=treble crochet, dtr=double treble crochet, and sl st=slip stitch. [claim:clm_030]
- The '2tog' decrease tokens are defined explicitly: sc2tog, hdc2tog, dc2tog, and tr2tog each mean working two stitches together of the named stitch type. [claim:clm_031]
- Repeat and grouping notation is standardized: a single asterisk marks instructions to repeat, paired asterisks repeat the span between them, and brackets, braces, and parentheses enclose instructions worked a given number of times — with parentheses additionally signaling stitches worked all in the same stitch or space. [claim:clm_032]
- The same stitch token denotes different stitches across locales: U.S. single crochet = U.K. double crochet, U.S. double crochet = U.K. treble, and U.S. treble = U.K. double treble — a one-step naming offset that makes US/UK tokens collide. [claim:clm_033]
- Terminology divergence extends beyond stitches: U.S. 'gauge' corresponds to U.K./Canada 'tension', and U.S. 'yarn over (yo)' corresponds to 'yarn over hook (yoh)'. [claim:clm_034]
- Measurement abbreviations a parser must normalize are standardized as in/" (inch), cm (centimeter), m (meter), mm (millimeter), g (gram), oz (ounce), and yd (yard). [claim:clm_035]
- ChartMuseum is a chart-QA benchmark of 1,162 expert-annotated image-question-answer tuples drawn from 928 unique real-world charts across 184 websites. [claim:clm_036]
- On ChartMuseum, humans reach 93% accuracy while the best proprietary model Gemini-2.5-Pro attains only 63.0% and the leading open-source LVLM Qwen2.5-VL-72B-Instruct reaches only 38.5%. [claim:clm_037]
- There is a 24.5-point accuracy gap between the best open-source model (Qwen2.5-VL-72B-Instruct, 38.5%) and the best proprietary model (Gemini-2.5-Pro, 63.0%). [claim:clm_038]
- On questions requiring primarily visual reasoning, all evaluated models drop 35%-55% relative to their performance on text-reasoning-heavy questions. [claim:clm_039]
- Humans remain near-perfect on the sampled visual-reasoning set, scoring 56/57 correct (98.2%), unlike models. [claim:clm_040]
- Unlike prior chart benchmarks where frontier models cluster near saturation, ChartMuseum exposes a substantial model-vs-human gap while differentiating model capabilities. [claim:clm_041]
- The hardest visual skill category is visual comparison, defined as comparing multiple objects or groups by size, height, or spatial placement. [claim:clm_042]
- MagicVL-2B uses a SigLIP2-base ViT visual encoder with 93M parameters at 384x384 input resolution, paired with Qwen2.5-1.5B or Qwen3-1.7B as the LLM backbone. [claim:clm_043]
- On Snapdragon 8 Elite, MagicVL-2B reports 0.09s ViT latency, 1.7s LLM latency and 23.9 token/s throughput, versus InternVL2.5-2B's 0.90s ViT latency and 14.3 token/s. [claim:clm_044]
- Among <=2B-class models, MagicVL-2B (Qwen3-1.7B) scores DocVQA 89.0, OCRBench 828, AI2D 77.4, MMBench-V1.1_en 73.7, and MMStar 57.9. [claim:clm_045]
- The dynamic high-resolution token resizing scheme reduces total visual tokens by ~37.8% (0.52M vs 0.81M) while slightly improving accuracy (74.5% vs 74.3%). [claim:clm_046]
- MagicVL-2B matches state-of-the-art accuracy while reducing on-device power consumption by 41.1%, positioning it as a practical mobile VLM. [claim:clm_047]
- MagicVL-2B is a sub-100M-parameter-encoder VLM optimized for flagship smartphones, using a redesigned dynamic resolution scheme plus a multimodal curriculum learning strategy that incrementally increases task difficulty and data density during training. [claim:clm_048]
- The method takes a written crochet pattern as input, translates it into a graph, and computes a force-directed graph layout to produce a 3D representation. [claim:clm_049]
- The resulting 3D model matches the hand-crocheted piece in shape and size, letting designers adjust the digital model instead of physically crocheting. [claim:clm_050]
- The intended audience is both professional designers and beginners, and the application is oriented toward amigurumi but could extend to clothing or similar crochet styles. [claim:clm_051]
- Each crochet stitch is a node in the graph and physical connections between stitches are edges, with sequential, working, and constraint edge types. [claim:clm_052]
- The layout reimplements the force-directed graph layout of Isenburg et al. [IGG01] as a non-linear least-squares optimization minimizing two energy functions (edge length and local curvature), solved with the Ceres Solver and a static blend parameter lambda = 0.65 for most pieces. [claim:clm_053]
- Performance scales poorly with pattern size: small patterns converge in a few seconds while large/high-curvature pieces are slow; the bunny head (798 stitches) and body (708 stitches) did not converge even after over two minutes. [claim:clm_054]
- Models were accurate in shape and size to their real-world counterparts but not identical; some discrepancies (e.g. raindrop height) trace to the uniform edge-length assumption of 1, not yarn-specific stitch dimensions. [claim:clm_055]
- A formulation limitation is that least-squares minimization is incompatible with the goal of maximizing volume, so the method minimizes curvature instead and yields sub-maximal volume; testing was limited to simple beginner-level patterns and single-crochet-like stitches. [claim:clm_056]
- PaddleOCR-VL's core component is a compact 0.9B vision-language model that pairs a NaViT-style dynamic-resolution visual encoder with the ERNIE-4.5-0.3B language model and supports 109 languages. [claim:clm_057]
- The model targets document parsing and recognizes complex elements such as text, tables, formulas, and charts while minimizing resource consumption. [claim:clm_058]
- On OmniDocBench v1.5, PaddleOCR-VL achieves a top overall score of 92.86, surpassing the next-best model MinerU2.5-1.2B at 90.67. [claim:clm_059]
- PaddleOCR-VL reports leading per-task metrics including Text-Edit distance 0.035, Formula-CDM 91.22, Table-TEDS 90.89 / Table-TEDS-S 94.76, and reading-order edit distance 0.043. [claim:clm_060]
- The architecture combines a NaViT-style dynamic high-resolution visual encoder with the lightweight ERNIE-4.5-0.3B language model to improve recognition and decoding efficiency. [claim:clm_061]
- The technical report was first submitted Oct 16, 2025 (v1) with the latest revision v4 dated Nov 25, 2025, authored by Cheng Cui, Ting Sun, and colleagues. [claim:clm_062]
- The project rebranded dots.ocr-1.5 as dots.mocr on 2026-03-19, with technical details in an arXiv paper. [claim:clm_063]
- dots.mocr is a single multilingual document-parsing vision-language model built on a 1.7b-parameter LLM and described as a 3B-parameter VLM. [claim:clm_064]
- On olmOCR-Bench, dots.mocr reports an overall score of 83.9 plus or minus 0.9. [claim:clm_065]
- On OmniDocBench, dots.mocr reports a text-edit distance of 0.031, lower (better) than Gemini-2.5 Pro at 0.075 and Qwen3-VL-235B-A22B-Instruct at 0.069. [claim:clm_066]
- The model parses eleven layout categories and sorts all detected elements in human reading order. [claim:clm_067]
- The project claims the model can recognize virtually any human script and reaches state-of-the-art multilingual document parsing among models of comparable size. [claim:clm_068]
- The documentation reports no explicit latency or throughput metrics, leaving on-device inference cost unquantified. [claim:clm_069]
- Apple's on-device model is a roughly 3B-parameter model optimized for Apple silicon using KV-cache sharing and 2-bit quantization-aware training. [claim:clm_070]
- The on-device model is split into two blocks; Block 2 (37.5% of layers) drops its key/value projections and shares Block 1's KV cache, cutting KV-cache memory usage by 37.5%. [claim:clm_071]
- Because Block 2 produces no keys or values, prefill can bypass its computation, reducing time-to-first-token by about 37.5%. [claim:clm_072]
- The on-device model is compressed to 2 bits-per-weight via QAT, with the embedding table jointly quantized to 4 bits and the KV-cache quantized to 8 bits, plus low-rank adapters for quality recovery. [claim:clm_073]
- The models support additional languages and can understand images and execute tool calls, while the server model uses a Parallel-Track Mixture-of-Experts (PT-MoE) transformer on Private Cloud Compute. [claim:clm_074]
- Apple reports its on-device model beats Qwen-2.5-3B, Gemma-3-4B, and Gemma-3n-E4B on MMLU/MMMLU but performs lower than the larger Qwen-3-4B model. [claim:clm_075]
- CrochetPARADE is explicitly designed as an unambiguous DSL whose grammar aims for accuracy and precision, avoiding the ambiguities of plain-English crochet instructions. [claim:clm_076]
- The grammar supports compact repeat syntax where a stitch is multiplied by an integer, e.g. 10*sc, 10 sc, or 10sc all mean ten single crochet stitches. [claim:clm_077]
- Stitch modifications are expressed as token suffixes, including front-loop/back-loop variants formed by appending 'fl' or 'bl' to a stitch name (e.g. scbl, dcfl). [claim:clm_078]
- The DSL supports explicit attachment points, including direct attachment to a stitch coordinate given as an integer pair such as @[2,10]. [claim:clm_079]
- Turns are handled automatically by reversing attachment direction: an even count of preceding turn directives attaches to the next stitch, an odd count attaches to the previous stitch (reverse order). [claim:clm_080]
- Exporting to SVG produces multiple files, including a chart using standard crochet symbols (optionally with yarn colors) and a stitch-connection/view diagram. [claim:clm_081]
- All computation runs locally on the user's device, with no data collected to a server or transmitted over the internet. [claim:clm_082]
- The tool analyzes stitch tension, identifying overly loose or tight stitches so users can swap them before crocheting and reduce the need for blocking. [claim:clm_083]

## Decision

For clean machine-readable pattern text (typed body copy, not scanned), a rule-based tokenizer plus a deterministic stitch-count validator is the highest-accuracy and lowest-cost extractor available and should own the parse path, because the IR's expected_stitch_count field provides a closed-form correctness check that no current LLM/VLM can match on procedural fidelity. [claim:clm_inf03]

## Rationale

- Tokens/repeats are standardized (clm_031/032) so rules suffice for clean text; CrochetBench shows LLMs collapse on executable synthesis (clm_008) and propagate early errors irreversibly (clm_012); CrochetPARADE (clm_076) confirms a deterministic grammar is the precision path. The IR expected_stitch_count gives a deterministic validator. [claim:clm_inf03]
- Standardized tokens (clm_031) justify tier 1; MagicVL-2B on-device (clm_044) and PaddleOCR-VL doc parsing (clm_059) justify tier 2; ChartMuseum's chart gap (clm_037) and CrochetBench's synthesis collapse (clm_008) justify reserving tier 3 cloud VLMs for charts only. [claim:clm_inf08]
- clm_012 shows early errors propagate irreversibly with later correctness accidental; clm_031 standardized decreases make stitch arithmetic deterministic; clm_008 the low executable rate. A per-round count validator (IR expected_stitch_count) catches drift early and routes low-confidence rows to human review. [claim:clm_inf09]
- An end-to-end PDF importer must do both program synthesis (CrochetBench 5-8%, clm_008) and chart visual reasoning (ChartMuseum, clm_037/039). Compounding two low-accuracy steps yields an unacceptable product success rate, validating the spec's PDF-trap warning. [claim:clm_inf10]
- clm_014 shows undefined-stitch invention rises with model size when unconstrained; clm_020 AmiGo's fixed small instruction set yields deterministic structured output; clm_076 CrochetPARADE's unambiguous grammar. Constraining decoding to the IR enum directly suppresses the invention failure mode. [claim:clm_inf12]
- Maps each HITL trigger to evidence: count drift (clm_012), undefined-stitch invention (clm_014), chart visual-reasoning gap (clm_037). These are the three places automated extraction is documented to be unreliable. [claim:clm_inf13]
- clm_033/034 establish the US/UK one-step naming collision (US sc = UK dc), clm_032 the overloaded parenthesis semantics, and clm_030 the core token set; together these mean token identity is context-dependent, so locale must be resolved before op decoding. [claim:clm_inf01]
- clm_030 core stitch tokens and clm_031 the 2tog decreases align to sc/hdc/dc/tr/dec; clm_032 standardized repeat/grouping maps to the repeat op; clm_077 shows CrochetPARADE's integer-multiplied stitch syntax (10*sc) is exactly count-based op expansion. The IR enum covers these directly. [claim:clm_inf02]
- PaddleOCR-VL tops OmniDocBench (clm_059) but its only reported throughput is A100/43.7GB server-side (clm_005); dots.mocr scores well (clm_065) but is a 3B model (clm_064) with no latency reported (clm_069). Mobile RAM is far below 43.7GB, so these are cloud-side by evidence. [claim:clm_inf04]
- clm_044/045 give MagicVL-2B's on-device latency and DocVQA 89.0/OCRBench 828; clm_022/027 give SmolVLM's 5.02GB floor and DocVQA 81.6 but no phone latency. MagicVL-2B is the only candidate with both on-device latency and high doc accuracy. [claim:clm_inf05]
- ChartMuseum (clm_037/038) shows a 24.5-pt open-vs-proprietary gap and a large human gap; clm_039 the 35-55% visual-reasoning drop; clm_042 names visual comparison (spatial size/placement) as hardest - exactly the skill a crochet stitch chart demands. [claim:clm_inf07]
- Tokens/repeats/counts (clm_030/031/032) map deterministically to IR op/count/repeat/expected_stitch_count. shape_role and assembly need shaping/termination cues that clm_013 says are under-specified in text and clm_037 shows charts read poorly, so those IR fields stay ambiguous. [claim:clm_inf11]
- OmniDocBench/olmOCR (clm_003/065) reward transcription fidelity; CrochetBench (clm_008/009) measures executable synthesis and NL generation, which collapse. The two are not in tension once the task distinction is named - OCR layer trustworthy, synthesis layer not. [claim:clm_inf14]
- Strong doc benchmarks (clm_059/065/044) = academic feasibility; absence of mid-range-phone figures (clm_069 notes dots.mocr reports none), no crochet-specific accuracy, and the chart ceiling (clm_037) = product gaps. Separates 'shown in paper' from 'ready for product' per spec. [claim:clm_inf15]

## Consequences

- The viable KnitWit import architecture is a three-tier cascade: (1) on-device deterministic tokenizer + stitch-count validator for clean text patterns of known templates, (2) on-device small VLM (MagicVL-2B-class) or cloud OCR for typed/scanned text-layout, and (3) cloud VLM only for stitch charts and ambiguous diagrams - because deterministic rules dominate where notation is standardized, small VLMs handle layout, and only charts demand the highest-capability proprietary models. [claim:clm_inf08]
- Because LLM/VLM crochet errors propagate irreversibly from early steps (CrochetBench) and the IR carries a per-round expected_stitch_count, the architecture should run the deterministic stitch-count validator as a hard gate on every model-produced round and force human confirmation wherever the count check fails, converting an open-ended generation-error risk into a bounded, locatable confirmation task. [claim:clm_inf09]
- The design-spec 'PDF importer trap' is empirically justified: a single end-to-end VLM PDF-to-pattern importer would inherit CrochetBench's 5-8% executable-program ceiling and ChartMuseum's chart-reasoning gap simultaneously, so attempting full free-form PDF/chart ingestion in v1 is the highest-risk path and should be explicitly de-scoped in favor of templated/clean-text import plus assisted chart entry. [claim:clm_inf10]
- Constraining model output to the closed IR op enum (rather than free text) is a documented error-reduction lever, because CrochetBench shows larger models invent undefined stitches when unconstrained while AmiGo achieves reliable structured patterns precisely by restricting output to a fixed small instruction set - so KnitWit should require any model extractor to emit IR ops and reject out-of-enum tokens. [claim:clm_inf12]
- Human-in-the-loop confirmation should be triggered by three documented low-confidence signals - (a) a failed per-round stitch-count check, (b) any out-of-enum/undefined token emitted by a model, and (c) any content originating from a stitch chart or symbol diagram - because each corresponds to an evidenced failure mode (count drift, symbolic invention, and the chart visual-reasoning gap respectively). [claim:clm_inf13]
- Real-world crochet pattern text is structurally ambiguous in ways that defeat naive tokenization, because the same surface token denotes different stitches across US/UK locales (sc/dc/tr offset) and parentheses are overloaded to mean both 'repeat N times' and 'all worked in one stitch', so a parser that does not first resolve a declared terminology context will systematically mis-decode the most common stitch ops. [claim:clm_inf01]
- The CYC abbreviation list and CrochetPARADE's compact syntax map almost one-to-one onto the Crochet IR v0.1 op enum (mr/ch/slst/sc/hdc/dc/tr/inc/dec/repeat), so the deterministic core of pattern parsing is a finite token-to-op normalization plus a count/repeat expander, not an open-ended NLP problem. [claim:clm_inf02]
- The on-device-vs-cloud boundary for document/layout parsing falls between text-layout extraction (cloud-grade today) and on-device deployment: the strongest open document parsers (PaddleOCR-VL 0.9B at OmniDocBench 92.86; dots.mocr 3B at olmOCR-Bench 83.9) publish only server-side cost (PaddleOCR-VL needs ~43.7 GB A100 memory at 1.22 pages/s), and dots.mocr publishes no latency at all, so neither is documented to run within a mid-range phone's memory budget. [claim:clm_inf04]
- Among documented candidates, MagicVL-2B is the only model with measured mid-to-high-end phone parsing performance (Snapdragon 8 Elite: 0.09 s ViT + 1.7 s LLM, 23.9 tok/s, DocVQA 89.0, OCRBench 828), making it the strongest evidence that on-device text-document extraction is feasible at near-cloud DocVQA accuracy, while SmolVLM (5.02 GB, DocVQA 81.6) demonstrates the memory floor but reports no on-phone latency. [claim:clm_inf05]
- Stitch-chart and symbol-diagram parsing is the hardest sub-problem and the clearest cloud-only boundary, because chart understanding requires visual-comparison reasoning where ChartMuseum shows the best open model reaches only 38.5% and even the best proprietary model 63.0% (vs 93% human), and all models drop 35-55% on visually-grounded questions. [claim:clm_inf07]
- Mapping to the Crochet IR v0.1, the reliably-extractable-today fields are op (sc/hdc/dc/tr/slst/ch/mr), count, repeat, and expected_stitch_count for clean text; the ambiguous-today fields are visual_hint.shape_role, assembly[] attachment_points, and any field that requires chart geometry or free-text 'do what feels right' notes - because the former map to standardized tokens while the latter require visual or pragmatic inference current models do poorly. [claim:clm_inf11]
- There is an apparent contradiction between document-parsing optimism (PaddleOCR-VL/dots.mocr reporting 83-93 on OmniDocBench/olmOCR) and crochet-task pessimism (CrochetBench 5-8% executable), and the resolution is that the benchmarks measure different things - generic text/table/formula transcription versus domain procedural synthesis - so strong OCR scores justify trusting text-layout transcription but not trusting any model to produce a correct executable pattern; decision impact: high. [claim:clm_inf14]
- Academic feasibility is established for OCR/layout transcription (PaddleOCR-VL, dots.mocr, MagicVL-2B all publish strong document benchmarks) but product-readiness for an amigurumi-first mobile importer is NOT, because no source documents (i) a mid-range-phone latency/memory figure for these parsers, (ii) crochet-pattern-specific extraction accuracy, or (iii) chart-symbol recognition above the ~38-63% ChartMuseum ceiling - so the import feature is research-feasible but product-unproven without a dedicated evaluation. [claim:clm_inf15]

## Links

- [[claim:clm_031]]
- [[claim:clm_032]]
- [[claim:clm_008]]
- [[claim:clm_012]]
- [[claim:clm_076]]
- [[claim:clm_044]]
- [[claim:clm_059]]
- [[claim:clm_037]]
- [[claim:clm_039]]
- [[claim:clm_014]]
- [[claim:clm_020]]
- [[claim:clm_033]]
- [[claim:clm_030]]
- [[claim:clm_034]]
- [[claim:clm_077]]
- [[claim:clm_005]]
- [[claim:clm_065]]
- [[claim:clm_069]]
- [[claim:clm_064]]
- [[claim:clm_045]]
- [[claim:clm_022]]
- [[claim:clm_027]]
- [[claim:clm_038]]
- [[claim:clm_042]]
- [[claim:clm_013]]
- [[claim:clm_003]]
- [[claim:clm_009]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
