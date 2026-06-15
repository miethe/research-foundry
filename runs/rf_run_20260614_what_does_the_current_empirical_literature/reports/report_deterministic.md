---
schema_version: '0.1'
type: research_report
report_id: report_20260615_what_does_the_current_empirical_literature
title: What does the current empirical literature, led by
intent_id: intent_research_20260614_what_does_the_current_empirical_literature
evidence_bundle_id: pending
created_at: '2026-06-15T11:10:38-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

AmiGo takes a closed manifold triangle mesh, a seed vertex, and a stitch width as input and outputs human-readable crochet instructions for the model. [claim:clm_001]
Crochet rows are defined as isolines of the geodesic distance from the seed (f(v)=d(v,s)), with a second function g ordering within rows; vertices are sampled on a 2D grid of width w. [claim:clm_002]
Patterns use only the standard amigurumi stitch set (single crochet, increase, decrease) and deliberately avoid short rows to appeal to beginner crocheters. [claim:clm_003]
Crochetability is enforced through curvature preprocessing: Conformal Mean Curvature Flow is applied locally where mean curvature is not positive, and the sampling rate is modulated in negative-Gaussian-curvature regions via h(x)=tanh(-x/alpha)/2+1 with alpha=10. [claim:clm_004]
Branching shapes are split into segments that are crocheted onto the previous segment's last row using a join-as-you-go method, so no sewing is required. [claim:clm_005]
Table 2 reports per-model statistics (e.g., Teddy: 60 rows, 6 segments, 3670 stitches, 2.5 min) with instruction generation taking a few minutes on a desktop Intel Core i7. [claim:clm_006]
The method only handles closed (stuffed) surfaces, reflecting its amigurumi target domain. [claim:clm_007]
CrochetBench is a benchmark of 6,085 crochet patterns spanning 55 distinct project categories, built from publicly available Yarnspirations patterns. [claim:clm_008]
The dataset is sourced from Yarnspirations patterns originally distributed as PDFs and normalized via a GPT-4o-mini conversion pipeline. [claim:clm_009]
The benchmark uses the CrochetPARADE DSL as an intermediate representation to enable structural validation and functional evaluation by execution, rather than text-similarity scoring. [claim:clm_010]
Nine state-of-the-art vision-language models were evaluated, including GPT-4o, Gemini 2.5 Flash-Lite, Claude Sonnet 4, and open-source models spanning 3B to 72B parameters. [claim:clm_011]
On stitch recognition the best model, Claude Sonnet 4, reaches an F1 of 60.94%; instruction selection plateaus, with large and closed-source models clustering around 55-60% accuracy. [claim:clm_012]
Performance collapses from recognition/retrieval to synthesis: models that can recognize stitches or retrieve plausible text still fail to synthesize coherent multi-step procedures. [claim:clm_013]
Project-level DSL synthesis is severely limited: even the strongest models (Claude, Gemini, and Qwen2-VL-7B) produce only 5-8% executable programs. [claim:clm_014]
Linguistic plausibility is decoupled from structural validity: models generate fluent, crochet-like descriptions while failing to preserve the algorithmic structure needed for faithful pattern synthesis, revealing limits in long-range symbolic reasoning that scaling and finetuning do not close. [claim:clm_015]
The study created the first structured, open-source collection of crochet patterns designed for machine-learning applications, pairing user-generated patterns with their CrochetPARADE translations. [claim:clm_016]
The authors evaluated baseline, few-shot, and fine-tuning approaches with LLMs for translating crochet patterns into CrochetPARADE syntax. [claim:clm_017]
The best result was fine-tuning DeepSeek-R1-Distill-Llama8b, which reached 74% accuracy on pattern-to-CrochetPARADE translation. [claim:clm_018]
The work frames LLM-assisted translation as a way to bridge the gap between standard crochet notation and CrochetPARADE's non-intuitive syntax, lowering the barrier for novice crocheters. [claim:clm_019]
The paper motivates the work by noting that crochet pattern creation and modification is challenging for novices because of the spatial reasoning and structural stitch understanding it requires. [claim:clm_020]
The paper is a peer-reviewed AAAI Symposium Series publication (Vol.6 No.1, pp.200-208, published 2025-08-01, DOI 10.1609/aaaiss.v6i1.36054) in the Human-AI Collaboration track. [claim:clm_021]
The plan splits the work into two research tracks - a forward Pattern->3D preview and an inverse 3D-object->pattern synthesizer - and treats the 3D preview as structural geometry first (not yarn-physics) and the inverse track as amigurumi-first. [claim:clm_022]
The plan explicitly scopes the 3D preview as structural geometry (graph/mesh) before yarn-physics and the inverse generator as amigurumi-first with watertight mesh, seed point, and stitch size. [claim:clm_023]
The Crochet IR validation spec names three explicit rule classes: stitch-count invariants per round, increase/decrease legality, and piece-closure constraints. [claim:clm_024]
Inverse-engine preconditions are a closed (watertight) triangle mesh plus a user-selected seed point and target stitch size/gauge assumptions. [claim:clm_025]
The inverse generator must guarantee no impossible stitch-count transitions and a bounded (manageable) increase/decrease rate per round as a hard output constraint. [claim:clm_026]
Proposed inverse-engine acceptance metrics are shape distance versus the target mesh plus pattern-complexity metrics: max inc/dec rate per round, total rounds, and stitch-count variance. [claim:clm_027]
Topological-correctness acceptance for the forward visualizer requires a consistent stitch graph with no broken loops and correct stitch counts per round. [claim:clm_028]
The plan flags the 'PDF importer trap' (general NL parsing is a quagmire, so restrict to structured authoring/import templates) and gauge/tension variability as primary risks, reinforcing a narrow validator-gated structured-IR approach. [claim:clm_029]
The spec decomposes the 3D ambition into a four-level capability ladder: L0 (2D + counters + highlighting), L1 (structural 3D preview), L2 (editable 3D with consistent stitch semantics), and L3 (3D object to pattern synthesis). [claim:clm_030]
The spec states the differentiation wedge must be interactive 3D plus guided assembly, because the market already has strong pattern-and-tracking apps such as Ribblr and My Row Counter. [claim:clm_031]
The spec scopes the first 3D as structural geometry rather than yarn-physics realism, and warns the product must be messaged as a structural preview because users may otherwise expect perfect realism. [claim:clm_032]
The Crochet intermediate representation sketch specifies units/gauge/hook/yarn-weight, pieces[], rows[] as stitch ops with counts (e.g. sc x6, inc, dec, repeat), end-of-row stitch-count constraints and checkpoints, and assembly join/placement markers. [claim:clm_033]
Pattern IP/copyright is flagged as the number-one business landmine, arguing for designer opt-in, licensing, or user-private imports rather than scrape-from-anywhere ingestion. [claim:clm_034]
The spec recommends amigurumi-first positioning (pieces, assembly, shaping, safety eyes, stuffing, symmetry checks) as where 3D guidance delivers the most user value. [claim:clm_035]
The spec defers the inverse 3D-object-to-pattern generator to Phase 3, noting peer-reviewed work generates amigurumi instructions from a closed 3D model, seed point, and stitch size, but warns 'works in a paper' does not mean it delights in an app. [claim:clm_036]
CrochetBench is a benchmark for evaluating multimodal LLMs on fine-grained, low-level procedural reasoning in crochet, shifting emphasis from describing to doing. [claim:clm_037]
The benchmark requires models to recognize stitches, select appropriate instructions, generate pattern instructions, and produce compilable crochet procedures. [claim:clm_038]
CrochetBench adopts the CrochetPARADE DSL as an intermediate representation and enables functional evaluation through program execution. [claim:clm_039]
Task A (CrochetBench-A) is stitch recognition, scored by F1/Precision/Recall, with a test size of 6,009. [claim:clm_040]
Task D requires models to output a compilable program in the CrochetPARADE DSL, scored by Compilation Success Rate against the validator, enabling executable evaluation rather than only generative training. [claim:clm_041]
Data is released as structured JSON test files (e.g., multiple-choice and project/step-level DSL test sets) plus crochet patterns organized by project type. [claim:clm_042]
The repository includes a Copyright Permission section (an email screenshot), indicating use of the original pattern sources required explicit permission rather than carrying an open redistribution license. [claim:clm_043]
Task D validation requires cloning the external CrochetPARADE repository, and data is collected via a CLI scraper keyed by project type (e.g., Hats). [claim:clm_044]
The method takes a written crochet pattern as input, translates it into a graph, and obtains a force-directed graph layout that yields a 3D model matching the hand-crocheted result in shape and size. [claim:clm_045]
The stated benefit is that designers can preview and adjust a pattern digitally without physically crocheting it; the work is oriented toward amigurumi but could be extended to clothing or similar crochet styles. [claim:clm_046]
Each stitch is modeled as a graph node; horizontal edges encode sequential connections between consecutive stitches and vertical edges encode working connections (a stitch worked into a stitch below). [claim:clm_047]
The layout adapts Isenburg et al.'s force-directed algorithm: a non-linear least-squares optimization minimizing two energy functions (edge length and local curvature), since stuffing a crocheted shell is treated as equivalent to inflating the planar graph. [claim:clm_048]
The implementation uses the Ceres Solver library with a static blend weight λ = 0.65 for most pieces (λ = 0.9 for the bunny head and body), and the linear solver is the most time-expensive part of the application. [claim:clm_049]
Performance is limited: small patterns converge in seconds (bunny legs at 318 stitches and arms at 264 stitches in under 5s), but the bunny head (798 stitches) and body (708 stitches) failed to converge even after more than two minutes. [claim:clm_050]
The authors released their source code as an open repository, providing a usable reference implementation of a stitch-graph plus force-directed embedding forward engine. [claim:clm_051]
Crochet remains largely manual and, unlike knitting or weaving, is barely supported by domain-specific digital tooling for authoring new pattern instructions. [claim:clm_052]
Existing crochet tools are constrained by underlying pattern languages that are either ambiguous or limited in expressiveness, so authoring requires substantial manual effort and can yield incomplete or ambiguous instructions. [claim:clm_053]
The paper proposes a first visual, domain-specific, graph-based language for representing crochet patterns. [claim:clm_054]
The language is realized in a prototype editor that supports authoring patterns in 2D and viewing them in 3D, demonstrating domain-specific tool support. [claim:clm_055]
A user study showed the proposed language lets designers express both 2D and 3D patterns and removes ambiguities present in current standard crochet notations. [claim:clm_056]
The work was published at the 2022 ACM SIGPLAN International Symposium on New Ideas, New Paradigms, and Reflections on Programming and Software (Onward!/SPLASH 2022), framing crochet pattern representation as a programming-language design problem. [claim:clm_057]
Crochet fabricates a 3D surface from yarn by interlacing loops formed with a special hook. [claim:clm_058]
Standard abstract pictorial crochet notation does not directly show the yarn layout of stitches, hindering parsing, visualization, and computational design. [claim:clm_059]
The paper represents a crochet pattern in the stitch-mesh paradigm as a library of tiles where each tile holds yarn geometry and tiles connect along their edges. [claim:clm_060]
To adapt stitch meshes to crochet, the authors introduce a special edge type capturing the 'current loop' held on the hook during fabrication. [claim:clm_061]
The authors build a library of mesh face types that model commonly-used crochet stitches. [claim:clm_062]
The richness of crochet stitch faces is illustrated with examples including patterns generated from 3D models, in a peer-reviewed SCF '20 paper by Guo, Lin, Narayanan, and McCann. [claim:clm_063]
AmiGo takes a closed manifold triangle mesh, a single user-specified seed vertex, and a stitch width w, and outputs human-readable crochet instructions for the model. [claim:clm_064]
The method builds a Crochet Graph G=(S, R union C) whose vertices are stitch tops/bases, with column edges C as stitch stems connecting rows and row edges R ordering bases within a row. [claim:clm_065]
Row ordering is induced by the geodesic distance function f(v)=d(v,s) from the seed (isolines of f are rows), and an optimized perpendicular function g orders stitches within each row. [claim:clm_066]
AmiGo uses only three simple stitches - single crochet (sc), increase inc(x), and decrease dec(x) - and compresses instructions via loop folding into notation such as (sc, inc, 2sc)*3. [claim:clm_067]
Branching shapes are segmented automatically by slicing along the isolines of the saddle points of the seed distance function, and segments are joined with the join-as-you-go method so no additional sewing is required. [claim:clm_068]
AmiGo was evaluated on 11 models ranging 30-60 rows, 1-8 segments, and 365-3,670 stitches, with running times of 0.2-6.9 minutes measured on a desktop with an Intel Core i7. [claim:clm_069]
On the 4-way instruction-selection task, weaker VLMs sit near the 25% chance level (BLIP-2 0.2562, Gemma 3 0.2494) while top open-source Qwen2-VL reaches 0.4196 and GPT-4o leads at 0.5811. [claim:clm_070]
At step-level DSL compilation, Claude achieves the highest valid (compilation success) rate at 52.1%, with DeepSeek-VL and Qwen2-VL the strongest open-source models. [claim:clm_071]
At project-level compilation, open-source Qwen2-VL leads with a 21.0% valid rate and strong partial-executable rate, surpassing all closed-source systems. [claim:clm_072]
The two model families fail differently: open models commit syntax errors such as undefined stitches and malformed brackets, while closed models emit syntactically valid but semantically inconsistent programs. [claim:clm_073]
The authors conclude that gains on this task may come from architecture or training that captures long-range dependencies and stateful operations, not from raw scaling. [claim:clm_074]
Instruction-generation absolute scores are uniformly low, with the best model (Gemini 2.5 Flash-Lite) scoring BLEU 0.0482, ROUGE-L 0.2583, and ChrF 30.20. [claim:clm_075]
CrochetPARADE is a platform for creating, visualizing, and analyzing both 2D and 3D crochet patterns. [claim:clm_076]
It uses a custom language grammar (DSL) to define stitches and stitch patterns, aiming to avoid the ambiguities of plain-English crochet instructions. [claim:clm_077]
The system parses and checks any user-provided pattern for correctness, then builds a virtual model that is rendered in 3D. [claim:clm_078]
It provides structural validation feedback by identifying overly loose or tight stitches so users can swap them before crocheting, reducing the need for blocking. [claim:clm_079]
Interactive 3D features include rotate/zoom/pan, animating the pattern-creation process, per-stitch info on hover, and export to 3D files for Blender. [claim:clm_080]
All calculations run locally on the user's device with no data collected to a central server or transmitted over the internet, supporting privacy and on-device runtime feasibility. [claim:clm_081]

## Inferences

**Inference:** CrochetBench's headline empirical result is a monotonic capability collapse along its four-task ladder: best stitch recognition F1 ~60.94% (Claude Sonnet 4) and instruction selection ~55-60% degrade to near-zero usable output at project-level DSL synthesis, where even the strongest models (Claude, Gemini, Qwen2-VL-7B) emit only 5-8% executable programs. [claim:clm_inf01]
**Inference:** CrochetBench's most decision-relevant finding for KnitWit is that linguistic fluency is decoupled from structural validity: models produce crochet-like prose while violating the very stitch-count, transition, and closure invariants the app must guarantee, so generation quality cannot be judged by reading the output and must be judged by execution against a validator. [claim:clm_inf02]
**Inference:** The enumerated generative failure-mode taxonomy for amigurumi maps to two empirically distinct families documented by CrochetBench: open-model syntactic failures (undefined/illegal stitches, malformed brackets/repeats) and closed-model semantic failures (compilable but state-inconsistent programs that break stitch-count continuity, unbounded inc/dec, broken loop topology, and non-closing pieces), and the KnitWit IR validation rule classes target the second, harder family. [claim:clm_inf03]
**Inference:** The single most de-risking finding is that the recognition-to-synthesis gap is an architecture/training problem, not a scaling problem: closed-source scale does not win project-level synthesis (open-source Qwen2-VL leads at ~21% vs 5-8% for the strongest closed models), so an amigurumi-first app cannot expect a near-term larger general model to deliver end-to-end pattern generation that satisfies structural rules. [claim:clm_inf04]
**Inference:** Viable near-term role recommendation: ML/VLM generation should be positioned as assist-then-deterministic-validator (drafting plus author-in-the-loop), never as autonomous end-to-end synthesis, because a 5-8% executable rate at project level means roughly 92-95% of unvalidated raw generations would be structurally broken if shipped directly to a crocheter. [claim:clm_inf05]
**Inference:** Recommendation: the deterministic mesh-to-pattern engine (AmiGo's geodesic-isoline plus sc/inc/dec plus curvature-preprocessing pipeline) should be KnitWit's primary inverse generator, with VLM generation reserved for the LLM-translation and authoring-assist surfaces, because AmiGo provably restricts output to legal sc/inc/dec transitions on closed meshes whereas no learned model yet produces structurally valid project-level patterns reliably. [claim:clm_inf06]
**Inference:** Dataset/benchmark inventory verdict: for an amigurumi app, CrochetBench (6,085 patterns / 55 categories, JSON plus DSL, permission-gated, no open redistribution license) is best as a validator-and-evaluation harness rather than a generator training corpus, the Dias-Karim CrochetPARADE-paired collection is the most usable open generator-finetuning set, and the Greer-Mould force-directed repo (CC-BY, code released) is the most reusable forward-engine reference. [claim:clm_inf07]
**Inference:** Licensing decision rule: KnitWit must treat the CMU stitch-mesh work (Guo 2020, 'Not licensed for use with or for AI') and CrochetBench/Yarnspirations data (explicit copyright-permission gate, no open license) as study-only / non-ingestible, and may only build training or product pipelines on CC-BY or explicitly open assets such as the Greer-Mould repo and the Dias-Karim open collection. [claim:clm_inf08]
**Inference:** Academic-feasibility vs product-readiness verdict: deterministic mesh-to-amigurumi (AmiGo) and pattern-to-3D forward preview (Greer-Mould, Digital Crochet, CrochetPARADE) are demonstrated in peer-reviewed/open work and are on the 'shown to work' side, but none is shown product-ready for a mobile app, since AmiGo and Greer-Mould run multi-minute desktop solves and Greer-Mould failed to converge on ~700-800-stitch pieces after 2+ minutes. [claim:clm_inf09]
**Inference:** Contradiction (decision impact: medium): the AAAI Dias-Karim result reports 74% accuracy for fine-tuned DeepSeek-R1-Distill-Llama8b on pattern-to-CrochetPARADE translation, which looks far rosier than CrochetBench's 5-8% project-level executable rate; the likely resolution is task-difference (constrained translation of an existing well-formed pattern vs end-to-end synthesis from images/specs), so the optimistic figure does NOT license autonomous generation. [claim:clm_inf10]
**Inference:** Implication: KnitWit should adopt CrochetPARADE-style execution-based validation (parse, build virtual model, check stitch tightness/looseness and closure) as the deterministic gate behind any generation, because CrochetBench's choice of compilation-success-rate as its primary metric and CrochetPARADE's own correctness-checking demonstrate execution is the only reliable correctness signal for crochet structure. [claim:clm_inf11]
**Inference:** IR alignment recommendation: the spec's Crochet IR v0.1 (op enum mr|ch|slst|sc|hdc|dc|tr|inc|dec|repeat|color_change|fasten_off|attach, expected_stitch_count per round, visual_hint.shape_role, assembly[]) is the right shared baseline because expected_stitch_count operationalizes CrochetBench's failed stitch-count invariant, the inc/dec ops match AmiGo's minimal sc/inc/dec stitch set, and shape_role maps onto AmiGo's curvature/geodesic round semantics; the only addition needed is an explicit per-round inc/dec-rate bound field to encode the hard crochetability constraint. [claim:clm_inf12]
**Inference:** Decision-gate framing: the gathered B1 evidence (CrochetBench, AmiGo, Greer-Mould, Digital Crochet/Seitz, stitch meshes/Guo, CrochetPARADE) is sufficient to pass G1 (evidence quality) and supports a conditional G2 (Crochet-IR viability), but G3 (pattern-to-3D), G4 (mesh-to-pattern primitive), and G5 (MVP) cannot be cleared by literature alone and require the prototype experiments, since every G3/G4 claim rests on desktop-research artifacts with unmeasured mobile behavior. [claim:clm_inf13]
**Inference:** Experiment-prioritization recommendation: the two highest-leverage next prototypes are EXP-002 stitch-count validator and EXP-003 repeat expansion, because they directly instrument the exact invariant CrochetBench shows models violating; IR-to-stitch-graph (EXP-004) and primitive-mesh-to-rounds (EXP-008) then de-risk the AmiGo-style inverse primitive that the literature only proves on desktop. [claim:clm_inf14]
**Inference:** Risk (mobile performance/crochetability, severity: high, likelihood: medium): a faithful pattern-to-3D preview or mesh-to-pattern solve may be infeasible at interactive mobile speed, since Greer-Mould's force-directed layout failed to converge on 700-800-stitch pieces after 2+ minutes on a desktop and AmiGo took up to 6.9 minutes; mitigation is server-side or precomputed solves plus a coarse on-device structural-graph approximation messaged explicitly as a structural preview, not realtime physics. [claim:clm_inf15]
**Inference:** Risk (UX trust, severity: high, likelihood: high): because models emit fluent-but-wrong patterns and the preview is only structural geometry, an amigurumi user could follow a confidently-rendered pattern that does not close or whose stitch counts are illegal; mitigation is to never surface an unvalidated generation, attach per-round validator status and confidence indicators, and message previews as approximate, aligning with the spec's structural-preview and validation-feedback posture. [claim:clm_inf16]
**Inference:** B1 baseline framing: the six anchor sources cleanly partition the problem space and let KnitWit skip re-surveying forward/inverse rendering prior art - CrochetBench supplies the empirical limits of learned generation, AmiGo the deterministic inverse mesh-to-pattern primitive, Greer-Mould the open forward pattern-to-3D engine, Digital Crochet/Seitz and CrochetPARADE the DSL/visual-language design baseline, and stitch meshes/Guo the yarn-geometry representation ceiling that the spec deliberately defers. [claim:clm_inf17]

## Speculation

**Speculation:** Speculation: a domain-tuned small model fine-tuned on a CrochetPARADE-paired open corpus, constrained to emit only the IR op-enum and gated by an execution validator, could plausibly lift product-usable amigurumi generation well above the current 5-8% project-level rate within 1-2 years - but this remains unproven for an interactive mobile product and is forward-looking. [claim:clm_spec01]

## Open questions

- None recorded.

## Sources

- src_20260614_kw016_02: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw016_00: CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260614_kw016_05: Translation of User Crochet Patterns to CrochetPARADE Syntax Using Large Language Models
- src_20260614_kw016_06: KnitWit Research Plan (local seed, project primary context)
- src_20260614_kw016_07: KnitWit Design Spec (local seed, project primary context)
- src_20260614_kw016_08: CrochetBench (official code & data repository)
- src_20260614_kw016_03: Modeling Crochet Patterns with a Force-directed Graph Layout
- src_20260614_kw016_11: Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260614_kw016_10: Representing Crochet with Stitch Meshes
- src_20260614_kw016_09: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw016_01: CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260614_kw016_04: CrochetPARADE - Crochet PAttern Renderer, Analyzer, and DEbugger (Manual)
