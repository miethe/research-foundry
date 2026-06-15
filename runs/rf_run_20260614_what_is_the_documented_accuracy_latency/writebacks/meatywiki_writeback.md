---
id: mwb_20260615_ai_assisted_crochet_pattern_parsing_on
evidence_bundle_id: bundle_20260615_intent_research_20260614_what_is_the
target_page: meatywiki/sources/ai_assisted_crochet_pattern_parsing_on.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_is_the_documented_accuracy_latency:
  83 supported claim(s) across 12 source card(s).'
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
- claim_id: clm_047
  include: true
- claim_id: clm_048
  include: true
- claim_id: clm_049
  include: true
- claim_id: clm_050
  include: true
- claim_id: clm_051
  include: true
- claim_id: clm_052
  include: true
- claim_id: clm_053
  include: true
- claim_id: clm_054
  include: true
- claim_id: clm_055
  include: true
- claim_id: clm_056
  include: true
- claim_id: clm_057
  include: true
- claim_id: clm_058
  include: true
- claim_id: clm_059
  include: true
- claim_id: clm_060
  include: true
- claim_id: clm_061
  include: true
- claim_id: clm_062
  include: true
- claim_id: clm_063
  include: true
- claim_id: clm_064
  include: true
- claim_id: clm_065
  include: true
- claim_id: clm_066
  include: true
- claim_id: clm_067
  include: true
- claim_id: clm_068
  include: true
- claim_id: clm_069
  include: true
- claim_id: clm_070
  include: true
- claim_id: clm_071
  include: true
- claim_id: clm_072
  include: true
- claim_id: clm_073
  include: true
- claim_id: clm_074
  include: true
- claim_id: clm_075
  include: true
- claim_id: clm_076
  include: true
- claim_id: clm_077
  include: true
- claim_id: clm_078
  include: true
- claim_id: clm_079
  include: true
- claim_id: clm_080
  include: true
- claim_id: clm_081
  include: true
- claim_id: clm_082
  include: true
- claim_id: clm_083
  include: true
links:
  source_cards:
  - src_20260614_kw015_00
  - src_20260614_kw015_01
  - src_20260614_kw015_02
  - src_20260614_kw015_03
  - src_20260614_kw015_04
  - src_20260614_kw015_05
  - src_20260614_kw015_06
  - src_20260614_kw015_07
  - src_20260614_kw015_08
  - src_20260614_kw015_09
  - src_20260614_kw015_10
  - src_20260614_kw015_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# AI-Assisted Crochet Pattern Parsing: On-Device vs Cloud Capability Review

## Summary

Source note distilled from research run rf_run_20260614_what_is_the_documented_accuracy_latency: 83 supported claim(s) across 12 source card(s).

## Key claims

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

## Sources

- src_20260614_kw015_00 — CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260614_kw015_01 — Crochet Abbreviations Master List
- src_20260614_kw015_02 — CrochetPARADE Manual (Crochet PAttern Renderer, Analyzer, and DEbugger)
- src_20260614_kw015_03 — PaddleOCR-VL: Boosting Multilingual Document Parsing via a 0.9B Ultra-Compact Vision-Language Model
- src_20260614_kw015_04 — dots.ocr / dots.mocr - Multilingual Document Layout Parsing in a Single Vision-Language Model
- src_20260614_kw015_05 — Modeling Crochet Patterns with a Force-directed Graph Layout
- src_20260614_kw015_06 — AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw015_07 — SmolVLM - small yet mighty Vision Language Model
- src_20260614_kw015_08 — MagicVL-2B: Empowering Vision-Language Models on Mobile Devices with Lightweight Visual Encoders via Curriculum Learning
- src_20260614_kw015_09 — ChartMuseum: Testing Visual Reasoning Capabilities of Large Vision-Language Models
- src_20260614_kw015_10 — PaddleOCR-VL: Boosting Multilingual Document Parsing via a 0.9B Ultra-Compact Vision-Language Model
- src_20260614_kw015_11 — Apple Intelligence Foundation Language Models Tech Report 2025

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
