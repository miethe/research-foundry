---
id: mwb_20260615_what_does_the_current_empirical_literature
evidence_bundle_id: bundle_20260615_intent_research_20260614_what_does_the
target_page: meatywiki/sources/what_does_the_current_empirical_literature.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_does_the_current_empirical_literature:
  81 supported claim(s) across 12 source card(s).'
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
links:
  source_cards:
  - src_20260614_kw016_00
  - src_20260614_kw016_01
  - src_20260614_kw016_02
  - src_20260614_kw016_03
  - src_20260614_kw016_04
  - src_20260614_kw016_05
  - src_20260614_kw016_06
  - src_20260614_kw016_07
  - src_20260614_kw016_08
  - src_20260614_kw016_09
  - src_20260614_kw016_10
  - src_20260614_kw016_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# What does the current empirical literature, led by

## Summary

Source note distilled from research run rf_run_20260614_what_does_the_current_empirical_literature: 81 supported claim(s) across 12 source card(s).

## Key claims

- AmiGo takes a closed manifold triangle mesh, a seed vertex, and a stitch width as input and outputs human-readable crochet instructions for the model. [claim:clm_001]
- Crochet rows are defined as isolines of the geodesic distance from the seed (f(v)=d(v,s)), with a second function g ordering within rows; vertices are sampled on a 2D grid of width w. [claim:clm_002]
- Patterns use only the standard amigurumi stitch set (single crochet, increase, decrease) and deliberately avoid short rows to appeal to beginner crocheters. [claim:clm_003]
- Crochetability is enforced through curvature preprocessing: Conformal Mean Curvature Flow is applied locally where mean curvature is not positive, and the sampling rate is modulated in negative-Gaussian-curvature regions via h(x)=tanh(-x/alpha)/2+1 with alpha=10. [claim:clm_004]
- Branching shapes are split into segments that are crocheted onto the previous segment's last row using a join-as-you-go method, so no sewing is required. [claim:clm_005]
- Table 2 reports per-model statistics (e.g., Teddy: 60 rows, 6 segments, 3670 stitches, 2.5 min) with instruction generation taking a few minutes on a desktop Intel Core i7. [claim:clm_006]
- The method only handles closed (stuffed) surfaces, reflecting its amigurumi target domain. [claim:clm_007]
- CrochetBench is a benchmark of 6,085 crochet patterns spanning 55 distinct project categories, built from publicly available Yarnspirations patterns. [claim:clm_008]
- The dataset is sourced from Yarnspirations patterns originally distributed as PDFs and normalized via a GPT-4o-mini conversion pipeline. [claim:clm_009]
- The benchmark uses the CrochetPARADE DSL as an intermediate representation to enable structural validation and functional evaluation by execution, rather than text-similarity scoring. [claim:clm_010]
- Nine state-of-the-art vision-language models were evaluated, including GPT-4o, Gemini 2.5 Flash-Lite, Claude Sonnet 4, and open-source models spanning 3B to 72B parameters. [claim:clm_011]
- On stitch recognition the best model, Claude Sonnet 4, reaches an F1 of 60.94%; instruction selection plateaus, with large and closed-source models clustering around 55-60% accuracy. [claim:clm_012]
- Performance collapses from recognition/retrieval to synthesis: models that can recognize stitches or retrieve plausible text still fail to synthesize coherent multi-step procedures. [claim:clm_013]
- Project-level DSL synthesis is severely limited: even the strongest models (Claude, Gemini, and Qwen2-VL-7B) produce only 5-8% executable programs. [claim:clm_014]
- Linguistic plausibility is decoupled from structural validity: models generate fluent, crochet-like descriptions while failing to preserve the algorithmic structure needed for faithful pattern synthesis, revealing limits in long-range symbolic reasoning that scaling and finetuning do not close. [claim:clm_015]
- The study created the first structured, open-source collection of crochet patterns designed for machine-learning applications, pairing user-generated patterns with their CrochetPARADE translations. [claim:clm_016]
- The authors evaluated baseline, few-shot, and fine-tuning approaches with LLMs for translating crochet patterns into CrochetPARADE syntax. [claim:clm_017]
- The best result was fine-tuning DeepSeek-R1-Distill-Llama8b, which reached 74% accuracy on pattern-to-CrochetPARADE translation. [claim:clm_018]
- The work frames LLM-assisted translation as a way to bridge the gap between standard crochet notation and CrochetPARADE's non-intuitive syntax, lowering the barrier for novice crocheters. [claim:clm_019]
- The paper motivates the work by noting that crochet pattern creation and modification is challenging for novices because of the spatial reasoning and structural stitch understanding it requires. [claim:clm_020]
- The paper is a peer-reviewed AAAI Symposium Series publication (Vol.6 No.1, pp.200-208, published 2025-08-01, DOI 10.1609/aaaiss.v6i1.36054) in the Human-AI Collaboration track. [claim:clm_021]
- The plan splits the work into two research tracks - a forward Pattern->3D preview and an inverse 3D-object->pattern synthesizer - and treats the 3D preview as structural geometry first (not yarn-physics) and the inverse track as amigurumi-first. [claim:clm_022]
- The plan explicitly scopes the 3D preview as structural geometry (graph/mesh) before yarn-physics and the inverse generator as amigurumi-first with watertight mesh, seed point, and stitch size. [claim:clm_023]
- The Crochet IR validation spec names three explicit rule classes: stitch-count invariants per round, increase/decrease legality, and piece-closure constraints. [claim:clm_024]
- Inverse-engine preconditions are a closed (watertight) triangle mesh plus a user-selected seed point and target stitch size/gauge assumptions. [claim:clm_025]
- The inverse generator must guarantee no impossible stitch-count transitions and a bounded (manageable) increase/decrease rate per round as a hard output constraint. [claim:clm_026]
- Proposed inverse-engine acceptance metrics are shape distance versus the target mesh plus pattern-complexity metrics: max inc/dec rate per round, total rounds, and stitch-count variance. [claim:clm_027]
- Topological-correctness acceptance for the forward visualizer requires a consistent stitch graph with no broken loops and correct stitch counts per round. [claim:clm_028]
- The plan flags the 'PDF importer trap' (general NL parsing is a quagmire, so restrict to structured authoring/import templates) and gauge/tension variability as primary risks, reinforcing a narrow validator-gated structured-IR approach. [claim:clm_029]
- The spec decomposes the 3D ambition into a four-level capability ladder: L0 (2D + counters + highlighting), L1 (structural 3D preview), L2 (editable 3D with consistent stitch semantics), and L3 (3D object to pattern synthesis). [claim:clm_030]
- The spec states the differentiation wedge must be interactive 3D plus guided assembly, because the market already has strong pattern-and-tracking apps such as Ribblr and My Row Counter. [claim:clm_031]
- The spec scopes the first 3D as structural geometry rather than yarn-physics realism, and warns the product must be messaged as a structural preview because users may otherwise expect perfect realism. [claim:clm_032]
- The Crochet intermediate representation sketch specifies units/gauge/hook/yarn-weight, pieces[], rows[] as stitch ops with counts (e.g. sc x6, inc, dec, repeat), end-of-row stitch-count constraints and checkpoints, and assembly join/placement markers. [claim:clm_033]
- Pattern IP/copyright is flagged as the number-one business landmine, arguing for designer opt-in, licensing, or user-private imports rather than scrape-from-anywhere ingestion. [claim:clm_034]
- The spec recommends amigurumi-first positioning (pieces, assembly, shaping, safety eyes, stuffing, symmetry checks) as where 3D guidance delivers the most user value. [claim:clm_035]
- The spec defers the inverse 3D-object-to-pattern generator to Phase 3, noting peer-reviewed work generates amigurumi instructions from a closed 3D model, seed point, and stitch size, but warns 'works in a paper' does not mean it delights in an app. [claim:clm_036]
- CrochetBench is a benchmark for evaluating multimodal LLMs on fine-grained, low-level procedural reasoning in crochet, shifting emphasis from describing to doing. [claim:clm_037]
- The benchmark requires models to recognize stitches, select appropriate instructions, generate pattern instructions, and produce compilable crochet procedures. [claim:clm_038]
- CrochetBench adopts the CrochetPARADE DSL as an intermediate representation and enables functional evaluation through program execution. [claim:clm_039]
- Task A (CrochetBench-A) is stitch recognition, scored by F1/Precision/Recall, with a test size of 6,009. [claim:clm_040]
- Task D requires models to output a compilable program in the CrochetPARADE DSL, scored by Compilation Success Rate against the validator, enabling executable evaluation rather than only generative training. [claim:clm_041]
- Data is released as structured JSON test files (e.g., multiple-choice and project/step-level DSL test sets) plus crochet patterns organized by project type. [claim:clm_042]
- The repository includes a Copyright Permission section (an email screenshot), indicating use of the original pattern sources required explicit permission rather than carrying an open redistribution license. [claim:clm_043]
- Task D validation requires cloning the external CrochetPARADE repository, and data is collected via a CLI scraper keyed by project type (e.g., Hats). [claim:clm_044]
- The method takes a written crochet pattern as input, translates it into a graph, and obtains a force-directed graph layout that yields a 3D model matching the hand-crocheted result in shape and size. [claim:clm_045]
- The stated benefit is that designers can preview and adjust a pattern digitally without physically crocheting it; the work is oriented toward amigurumi but could be extended to clothing or similar crochet styles. [claim:clm_046]
- Each stitch is modeled as a graph node; horizontal edges encode sequential connections between consecutive stitches and vertical edges encode working connections (a stitch worked into a stitch below). [claim:clm_047]
- The layout adapts Isenburg et al.'s force-directed algorithm: a non-linear least-squares optimization minimizing two energy functions (edge length and local curvature), since stuffing a crocheted shell is treated as equivalent to inflating the planar graph. [claim:clm_048]
- The implementation uses the Ceres Solver library with a static blend weight λ = 0.65 for most pieces (λ = 0.9 for the bunny head and body), and the linear solver is the most time-expensive part of the application. [claim:clm_049]
- Performance is limited: small patterns converge in seconds (bunny legs at 318 stitches and arms at 264 stitches in under 5s), but the bunny head (798 stitches) and body (708 stitches) failed to converge even after more than two minutes. [claim:clm_050]
- The authors released their source code as an open repository, providing a usable reference implementation of a stitch-graph plus force-directed embedding forward engine. [claim:clm_051]
- Crochet remains largely manual and, unlike knitting or weaving, is barely supported by domain-specific digital tooling for authoring new pattern instructions. [claim:clm_052]
- Existing crochet tools are constrained by underlying pattern languages that are either ambiguous or limited in expressiveness, so authoring requires substantial manual effort and can yield incomplete or ambiguous instructions. [claim:clm_053]
- The paper proposes a first visual, domain-specific, graph-based language for representing crochet patterns. [claim:clm_054]
- The language is realized in a prototype editor that supports authoring patterns in 2D and viewing them in 3D, demonstrating domain-specific tool support. [claim:clm_055]
- A user study showed the proposed language lets designers express both 2D and 3D patterns and removes ambiguities present in current standard crochet notations. [claim:clm_056]
- The work was published at the 2022 ACM SIGPLAN International Symposium on New Ideas, New Paradigms, and Reflections on Programming and Software (Onward!/SPLASH 2022), framing crochet pattern representation as a programming-language design problem. [claim:clm_057]
- Crochet fabricates a 3D surface from yarn by interlacing loops formed with a special hook. [claim:clm_058]
- Standard abstract pictorial crochet notation does not directly show the yarn layout of stitches, hindering parsing, visualization, and computational design. [claim:clm_059]
- The paper represents a crochet pattern in the stitch-mesh paradigm as a library of tiles where each tile holds yarn geometry and tiles connect along their edges. [claim:clm_060]
- To adapt stitch meshes to crochet, the authors introduce a special edge type capturing the 'current loop' held on the hook during fabrication. [claim:clm_061]
- The authors build a library of mesh face types that model commonly-used crochet stitches. [claim:clm_062]
- The richness of crochet stitch faces is illustrated with examples including patterns generated from 3D models, in a peer-reviewed SCF '20 paper by Guo, Lin, Narayanan, and McCann. [claim:clm_063]
- AmiGo takes a closed manifold triangle mesh, a single user-specified seed vertex, and a stitch width w, and outputs human-readable crochet instructions for the model. [claim:clm_064]
- The method builds a Crochet Graph G=(S, R union C) whose vertices are stitch tops/bases, with column edges C as stitch stems connecting rows and row edges R ordering bases within a row. [claim:clm_065]
- Row ordering is induced by the geodesic distance function f(v)=d(v,s) from the seed (isolines of f are rows), and an optimized perpendicular function g orders stitches within each row. [claim:clm_066]
- AmiGo uses only three simple stitches - single crochet (sc), increase inc(x), and decrease dec(x) - and compresses instructions via loop folding into notation such as (sc, inc, 2sc)*3. [claim:clm_067]
- Branching shapes are segmented automatically by slicing along the isolines of the saddle points of the seed distance function, and segments are joined with the join-as-you-go method so no additional sewing is required. [claim:clm_068]
- AmiGo was evaluated on 11 models ranging 30-60 rows, 1-8 segments, and 365-3,670 stitches, with running times of 0.2-6.9 minutes measured on a desktop with an Intel Core i7. [claim:clm_069]
- On the 4-way instruction-selection task, weaker VLMs sit near the 25% chance level (BLIP-2 0.2562, Gemma 3 0.2494) while top open-source Qwen2-VL reaches 0.4196 and GPT-4o leads at 0.5811. [claim:clm_070]
- At step-level DSL compilation, Claude achieves the highest valid (compilation success) rate at 52.1%, with DeepSeek-VL and Qwen2-VL the strongest open-source models. [claim:clm_071]
- At project-level compilation, open-source Qwen2-VL leads with a 21.0% valid rate and strong partial-executable rate, surpassing all closed-source systems. [claim:clm_072]
- The two model families fail differently: open models commit syntax errors such as undefined stitches and malformed brackets, while closed models emit syntactically valid but semantically inconsistent programs. [claim:clm_073]
- The authors conclude that gains on this task may come from architecture or training that captures long-range dependencies and stateful operations, not from raw scaling. [claim:clm_074]
- Instruction-generation absolute scores are uniformly low, with the best model (Gemini 2.5 Flash-Lite) scoring BLEU 0.0482, ROUGE-L 0.2583, and ChrF 30.20. [claim:clm_075]
- CrochetPARADE is a platform for creating, visualizing, and analyzing both 2D and 3D crochet patterns. [claim:clm_076]
- It uses a custom language grammar (DSL) to define stitches and stitch patterns, aiming to avoid the ambiguities of plain-English crochet instructions. [claim:clm_077]
- The system parses and checks any user-provided pattern for correctness, then builds a virtual model that is rendered in 3D. [claim:clm_078]
- It provides structural validation feedback by identifying overly loose or tight stitches so users can swap them before crocheting, reducing the need for blocking. [claim:clm_079]
- Interactive 3D features include rotate/zoom/pan, animating the pattern-creation process, per-stitch info on hover, and export to 3D files for Blender. [claim:clm_080]
- All calculations run locally on the user's device with no data collected to a central server or transmitted over the internet, supporting privacy and on-device runtime feasibility. [claim:clm_081]

## Sources

- src_20260614_kw016_00 — CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260614_kw016_01 — CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260614_kw016_02 — AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw016_03 — Modeling Crochet Patterns with a Force-directed Graph Layout
- src_20260614_kw016_04 — CrochetPARADE - Crochet PAttern Renderer, Analyzer, and DEbugger (Manual)
- src_20260614_kw016_05 — Translation of User Crochet Patterns to CrochetPARADE Syntax Using Large Language Models
- src_20260614_kw016_06 — KnitWit Research Plan (local seed, project primary context)
- src_20260614_kw016_07 — KnitWit Design Spec (local seed, project primary context)
- src_20260614_kw016_08 — CrochetBench (official code & data repository)
- src_20260614_kw016_09 — AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw016_10 — Representing Crochet with Stitch Meshes
- src_20260614_kw016_11 — Digital Crochet: Toward a Visual Language for Pattern Description

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
