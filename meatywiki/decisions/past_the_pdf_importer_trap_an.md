---
id: mwb_20260622_dr_past_the_pdf_importer_trap
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_does_the
target_page: meatywiki/decisions/past_the_pdf_importer_trap_an.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_what_does_the_empirical_evidence_say: CrochetPARADE
  and KnitScript both gate output behind a virtual-model validator; KnitScript''s per-instance-code-is-error-'
key_claims:
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf09
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_014
  - clm_043
  - clm_044
  - clm_052
  - clm_055
  - clm_018
  - clm_003
  - clm_023
  - clm_024
  - clm_025
  - clm_026
  - clm_047
  - clm_048
  - clm_050
  - clm_006
  - clm_053
  - clm_056
  - clm_059
  - clm_027
  - clm_028
  - clm_015
  - clm_016
  - clm_036
  - clm_054
  - clm_002
  - clm_038
  - clm_007
  - clm_008
  - clm_010
  - clm_011
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Past the PDF Importer Trap: An Evidence Review of Crochet Pattern Parsing and a Validator-Backed Ingestion Strategy

## Context

- CrochetBench reframes the evaluation of vision-language models from describing visual content to generating executable crochet procedures, requiring stitch recognition, structurally appropriate instruction selection, and compilable procedure generation. [claim:clm_001]
- The benchmark dataset comprises 6,085 real crochet patterns scraped from Yarnspirations, spanning 55 project categories with over 98% image coverage and ranging from beginner to expert difficulty. [claim:clm_002]
- Correctness is measured by functional executability using the CrochetPARADE DSL validator, which checks whether predicted DSL programs are syntactically valid, structurally consistent, and fully executable, rather than by textual similarity. [claim:clm_003]
- Task D (NL-to-DSL translation) tests stateful procedural reasoning with step-level and project-level variants, the latter providing the full natural-language instruction alongside the product image rather than as an isolated image-to-DSL task. [claim:clm_004]
- Across all tasks, model performance declines sharply as evaluation shifts from surface-level textual similarity to executable correctness, exposing limits in long-range symbolic reasoning and 3D-aware procedural synthesis. [claim:clm_005]
- Larger models hallucinate undefined or non-existent stitches at substantially higher rates than smaller siblings, showing model scale does not fix structural validity (Qwen2-VL-72B 72.0% vs Qwen2-VL-7B 13.6%; Gemma-3-27B 42.6% vs Gemma-3-4B 27.4%). [claim:clm_006]
- The author reports that LLM-generated JSON for crochet patterns is frequently invalid (e.g., a missing closing brace) and is token-expensive and slow because patterns contain many rows and stitches. [claim:clm_007]
- The author created CROML, a custom minimal data representation, specifically so the output can be easily and locally parsed rather than relying on the LLM to emit JSON directly. [claim:clm_008]
- CROML is indentation-agnostic and is parsed with simple regex then converted to JSON locally, which the author says is faster than waiting for the LLM to generate JSON. [claim:clm_009]
- The author concludes that instructing the LLM to emit CROML (a compact DSL) instead of JSON significantly reduces token usage and speeds up generation time. [claim:clm_010]
- The author argues the DSL is more robust than JSON because a single missing character does not cause a fatal parse error the way it would with JSON. [claim:clm_011]
- The author rejected existing minimal formats like TOML and YAML for crochet patterns because they felt too indentation-heavy and not readable for the pattern context, motivating a purpose-built authoring surface. [claim:clm_012]
- CrochetPARADE defines a custom DSL grammar for stitches and patterns expressly to ensure precision and avoid the ambiguity of plain-English crochet instructions. [claim:clm_013]
- The engine parses and validates any user-supplied pattern for correctness, builds a virtual model, and renders it in 3D - the compile/validate/render gate. [claim:clm_014]
- Beyond rendering, the debugger flags overly loose or tight stitches so users can correct them before crocheting, reducing the need for blocking - structural feasibility checking. [claim:clm_015]
- Exports include an auto-generated standard-symbol crochet chart plus an SVG that identifies each stitch by type, row number, and position within a row. [claim:clm_016]
- Projects can be exported to 3D files importable into Blender for further manipulation and visualization. [claim:clm_017]
- The project treats AI/natural-language-to-pattern generation as a future possibility layered on the grammar+renderer, confirming the NL-to-DSL ingestion problem is decoupled from the core renderer. [claim:clm_018]
- The paper was authored by Rachael Dias and Kayvan Karim of Heriot-Watt University and published 2025-08-01 in the AAAI Symposium Series, Vol. 6 No. 1, pp. 200-208. [claim:clm_019]
- CrochetPARADE is a pattern-visualisation tool whose syntax differs from standard crochet notation and may not be intuitive to the average crocheter, motivating automated translation as an accessibility layer. [claim:clm_020]
- The authors built the first structured, open-source collection of user-generated crochet patterns paired with their CrochetPARADE translations, designed for machine learning applications. [claim:clm_021]
- Baseline, few-shot, and fine-tuning approaches were evaluated across LLMs for prose-to-DSL crochet-pattern translation. [claim:clm_022]
- The best result was fine-tuning DeepSeek-R1-Distill-Llama8b, reaching 74% accuracy - meaning roughly one in four prose patterns still translate incorrectly even in the best dedicated, fine-tuned setup. [claim:clm_023]
- At the single-step level, the best model (Claude Sonnet 4) compiles only about half its translations at 52.1% CSR, ahead of Qwen2-VL (35.3%) and DeepSeek-VL (32.8%). [claim:clm_024]
- On full-pattern, project-level generation, closed-source models (GPT-4o, Gemini, Claude) collapse to only 4-5% compilation success. [claim:clm_025]
- At the project level, the open-source Qwen2-VL surprisingly outperforms closed-source models, reaching 21.0% CSR. [claim:clm_026]
- CrochetBench groups compilation errors into four families: syntax structure, stitch definition, labeling and reference, and structural/formatting issues. [claim:clm_027]
- Failure modes differ by model family: closed-source models fail mostly on label/reference inconsistencies, while open-source models fail more on undefined stitches and syntax errors. [claim:clm_028]
- The benchmark identifies a sharp performance decline when shifting from textual similarity to executable correctness, exposing limits in long-range symbolic reasoning and 3D-aware procedural synthesis. [claim:clm_029]
- CrochetBench frames the core gap as the distance between describing visual content and generating functionally correct, executable procedures with valid symbolic grammar, numerical accuracy, and topological coherence. [claim:clm_030]
- CrochetPARADE defines a custom language grammar for specifying stitches and stitch patterns, intended to remove the ambiguity of plain-English crochet instructions. [claim:clm_031]
- The grammar is explicitly designed to achieve precision and avoid the ambiguities of plain-English instructions. [claim:clm_032]
- The tool parses and checks any user-provided pattern for correctness before building a virtual model of the project, gating rendering behind validation. [claim:clm_033]
- The validator flags overly loose or tight stitches so users can replace them with better-suited stitches before crocheting. [claim:clm_034]
- The rendered virtual model supports interactive rotate/zoom/pan, animated pattern creation, and highlighting or hiding selected stitches (relevant to KnitWit row/round highlighting and piece isolation). [claim:clm_035]
- The tool exports an automatically generated crochet chart using standard crochet symbols, identifying stitches by type, row number, and position. [claim:clm_036]
- Projects can be exported to 3D files that can be imported into Blender for further manipulation and visualization. [claim:clm_037]
- The software and computational components are free and open source under GPLv3, while the user manual (including the grammar description) is under Creative Commons BY-NC-SA; GPLv3 carries copyleft implications for direct code reuse. [claim:clm_038]
- KnitScript is a domain-specific machine-knitting scripting language that provides a comprehensive virtual model of knitting machines and automates tedious, error-prone details. [claim:clm_039]
- KnitScript is a higher-level language that interprets into low-level Knitout instructions, demonstrating the layered DSL-to-IR compilation pattern. [claim:clm_040]
- Knitout is an assembly-like low-level language (analogous to g-code) operating on individual machine operations, lacking higher-level control structures, parameters, or a model of machine state. [claim:clm_041]
- KnitScript builds on general-purpose languages by maintaining a virtual model of the knitting machine and introducing new abstractions (carriage passes, yarn management, stitch tracking, lateral transfers) beyond individual instructions. [claim:clm_042]
- The KnitScript interpreter validates each operation against a virtual machine model and knit graph, raising errors and warnings to prevent machine damage or unstable fabric before recording valid operations as Knitout. [claim:clm_043]
- Because Knitout code is specific to a single instance of a knitted object, it cannot be reused, and reimplementing methods per-instance is likely to introduce errors and inefficiencies (motivating native structured authoring over per-instance code). [claim:clm_044]
- The paper was published at UIST '23, the 36th Annual ACM Symposium on User Interface Software and Technology, October 2023, San Francisco, CA, USA, anchoring a 2023 methodological reference. [claim:clm_045]
- CrochetBench defines four progressive tasks (stitch recognition, instruction selection, instruction generation, and image/NL-to-DSL translation into executable CrochetPARADE code), with the DSL-translation task split into a 119-item step-level set and a 100-item project-level set. [claim:clm_046]
- On project-level DSL translation, even the strongest models (Claude, Gemini, and Qwen2-VL-7B) produced only about 5-8% executable programs, indicating valid generations are rare. [claim:clm_047]
- Stitch recognition F1 stayed in the high-50s to low-60s across leading models: Claude Sonnet 4 at 60.94%, GPT-4o at 58.01%, and Gemini 2.5 Flash-Lite at 56.83%. [claim:clm_048]
- Across all tasks, model performance dropped sharply as evaluation shifted from surface-level similarity to executable correctness, exposing limits in long-range symbolic reasoning and 3D-aware procedural synthesis. [claim:clm_049]
- Even when a model emits a compilable DSL program, the rendered result rarely resembles the intended pattern, so syntactic validity does not imply correct procedural structure. [claim:clm_050]
- Models can produce fluent, crochet-like text while failing to preserve the algorithmic structure needed for faithful pattern synthesis, evidencing a gap between perception and procedural synthesis. [claim:clm_051]
- The paper frames its core takeaway as a gap between surface-level understanding and executable precision in real-world creative domains, which for KnitWit implies any image/PDF-to-IR importer must gate on an executable IR validator to catch the large fraction of invalid generations. [claim:clm_052]
- The paper frames crochet patterns as a semi-structured natural language whose restrictiveness lets standard multi-phase compiler parsing methods handle it, rather than requiring NLP for free text. [claim:clm_053]
- The system uses a two-parser pipeline: the first parser builds a uniform structured representation defined as a formal language, and the second parser translates that formal language into a crochet diagram. [claim:clm_054]
- The authors report the approach succeeds for a wide range of different crochet patterns, evidence that conventionally formatted patterns are tractable to rule-based parsing. [claim:clm_055]
- The defined formal-language representation is described as applicable to most crochet patterns, but the wording ('most') signals the tractability is bounded to a structured subset rather than arbitrary patterns. [claim:clm_056]
- The parsing approach is explicitly grounded in classic compiler phases - lexical, syntactic, semantic analysis, and code generation - rather than statistical NLP. [claim:clm_057]
- The pattern-to-diagram translation is characterized as a transpiler (same-abstraction-level compilation), and the reference list includes the ANTLR predicated-LL(k) parser generator, indicating conventional grammar/parser-generator tooling. [claim:clm_058]
- The parser must account for crochet-dialect variation (American vs. British stitch terminology), an explicit source of surface ambiguity the formal grammar has to normalize. [claim:clm_059]

## Decision

The evidence supports a three-tier ingestion architecture for KnitWit: (1) native structured authoring / GUI entry as the primary path that never needs a parser at all, (2) narrow template-bounded importers (single designer format, semi-structured text, chart symbols) using rule-based compiler-style parsing, and (3) optional LLM/VLM-assisted import strictly gated behind the B2 Crochet-IR validator as a compile-and-check backstop, mirroring how CrochetPARADE and KnitScript validate every operation against a model before accepting it. [claim:clm_inf05]

## Rationale

- CrochetPARADE and KnitScript both gate output behind a virtual-model validator; KnitScript's per-instance-code-is-error-prone argument and CrochetPARADE decoupling NL-from-renderer favor native authoring primary; rule-based parsing handles the template lane; CrochetBench mandates execution-gating for any LLM/VLM lane. [claim:clm_inf05]
- All three tools converge on execution/validation as the correctness backstop; the spec's EXP-002/G2 target stitch-count validation, which is exactly the structural-consistency axis that degrades with length, making it the experiment that retires the most uncertainty earliest. [claim:clm_inf10]
- Lining up the best measured numbers across the same DSL target (CrochetPARADE) shows monotonic decay 74% (fine-tuned, conventional prose) -> ~52% (single step) -> 4-5% (full pattern), isolating sequence length / long-range structural consistency as the controlling variable. [claim:clm_inf01]
- Recognition F1 (~57-61%) vastly exceeds executable CSR (4-21%); clm_050 confirms even compilable output rarely renders the intended pattern, so the gap is procedural, not perceptual. [claim:clm_inf02]
- Inverse scaling on undefined-stitch hallucination plus the small open model out-performing frontier closed models at project level jointly refute 'bigger model solves it'; the only common guarantee left is compile-and-check. [claim:clm_inf03]
- Semi-structured patterns are parseable by classic compiler phases for 'most' patterns (a bounded subset, with US/UK dialect normalization needed), whereas full-pattern LLM/VLM generation collapses to single-digit CSR; the boundary sits between conventional-format structured text and freeform/PDF/long synthesis. [claim:clm_inf04]
- Mapping CrochetBench's four error families against the IR v0.1 fields: undefined stitches violate the op enum; miscounts violate expected_stitch_count; label/reference issues are partially structural; dialect and 'as established' resolution are semantic and outside what a count/enum validator can adjudicate. [claim:clm_inf06]
- Standard-symbol charts encode stitch type + row + position (a graph-like structure that maps almost directly onto rounds/ops), and van Staden's pattern->diagram pipeline treats the diagram as a structured target; this is closer to the IR than freeform prose, which is where the 4-5% collapse occurs. [claim:clm_inf07]
- CrochetBench's scrape-based corpus is a research artifact not a licensing template; CrochetPARADE's CC BY-NC-SA manual + GPLv3 code constrain direct reuse; combined with the spec's no-unlicensed-ingestion governance rule, permissible import collapses to opt-in/private regardless of feasibility. [claim:clm_inf08]
- CROML reports LLM-emitted JSON is invalid/slow and a compact regex-parsed DSL is more robust; CrochetPARADE decouples NL-generation from the renderer; both point to a thin authoring DSL + deterministic local expansion to the validated IR. [claim:clm_inf09]

## Consequences

- The single highest-leverage de-risking experiment is the stitch-count validator (EXP-002) feeding gate G2, because the evidence shows the dominant, length-correlated failure is structural carryover and the only common correctness guarantee across all sources is compile-and-check; an IR-validator-as-import-gate experiment that measures how much of a CrochetBench-style error taxonomy it rejects would directly de-risk gate G2 (IR viability) before any pattern->3D (G3) work. [claim:clm_inf10]
- The evidence draws a sharp accuracy boundary for prose/image-to-DSL ingestion: dedicated fine-tuning on conventional prose reaches ~74% (DeepSeek-R1-Distill-Llama8b), single-step VLM translation tops out near 52% CSR (Claude Sonnet 4), and full-pattern project-level generation collapses to 4-5% for closed-source models, so length and must-execute structural carryover are the dominant failure axis, not stitch perception. [claim:clm_inf01]
- Stitch recognition F1 staying in the high-50s to low-60s (Claude 60.94%, GPT-4o 58.01%) while project-level executable success is 4-21% demonstrates that perception is roughly an order of magnitude less broken than procedural synthesis, so an ingestion strategy should treat per-stitch recognition as assistive but never trust an end-to-end image/PDF-to-IR pipeline as correct without execution-validation. [claim:clm_inf02]
- Model scale does not fix structural validity and can worsen it: Qwen2-VL-72B hallucinates undefined stitches at 72.0% vs 13.6% for the 7B sibling, and at project level the 7B open model (21.0% CSR) beats GPT-4o/Gemini/Claude (4-5%), so an importer cannot be de-risked by simply swapping in a larger or frontier model; the de-risking must come from the executable IR validator. [claim:clm_inf03]
- The tractability boundary the plan flags as its #1 landmine is real and locatable: rule-based compiler-style parsing succeeds for conventionally-formatted, single-dialect, 'most' (not all) structured-text patterns (van Staden & van Zijl two-parser ANTLR-class pipeline), while arbitrary freeform prose, scanned PDFs, and project-length synthesis fall on the intractable side (4-5% CSR), so 'any PDF magically works' is empirically off the table and template-bounded importers are the only defensible automated lane. [claim:clm_inf04]
- Because the B2 IR validator checks expected_stitch_count carryover and op-enum membership, it natively catches the open-source-dominant failure families - undefined/non-existent stitches (out-of-enum ops) and stitch-miscount/structural errors (count mismatch across rounds) - while the closed-source-dominant label/reference inconsistency family is partially catchable; ambiguous 'work as established', conditional instructions, and US/UK term confusion are semantic and require human-in-the-loop confirmation. [claim:clm_inf06]
- Chart/diagram ingestion is a lower-risk import lane than prose for amigurumi: symbol charts are a near-graph representation with fixed standard symbols labeled by type/row/position (as CrochetPARADE itself emits and round-trips), whereas CrochetBench's worst collapse is on long prose-to-DSL synthesis; so chart-first import better preserves the round/position structure the IR's rounds/ops and visual_hint fields need. [claim:clm_inf07]
- IP/licensing constraints are a first-class boundary that narrows import below even what is technically feasible: the operating spec forbids unlicensed/scraped pattern ingestion, CrochetBench's own corpus is scraped from a single site (Yarnspirations) and is not a reuse model, and CrochetPARADE's grammar/manual is CC BY-NC-SA (non-commercial/share-alike) with GPLv3 code - so permissible import is limited to designer opt-in and private user-owned patterns, independent of parser accuracy. [claim:clm_inf08]
- Two independent efforts (Tassev's CrochetPARADE grammar+renderer with NL-generation deferred as future work, and the CROML practitioner blog) converge on decoupling the human/LLM authoring surface from the validated machine IR - emit a compact, parse-robust DSL and expand it deterministically/locally rather than have the model emit the final structured form (JSON) directly - which validates KnitWit keeping a thin authoring DSL over the IR v0.1 JSON schema rather than asking models to emit IR JSON end-to-end. [claim:clm_inf09]

## Links

- [[claim:clm_014]]
- [[claim:clm_043]]
- [[claim:clm_044]]
- [[claim:clm_052]]
- [[claim:clm_055]]
- [[claim:clm_018]]
- [[claim:clm_003]]
- [[claim:clm_023]]
- [[claim:clm_024]]
- [[claim:clm_025]]
- [[claim:clm_026]]
- [[claim:clm_047]]
- [[claim:clm_048]]
- [[claim:clm_050]]
- [[claim:clm_006]]
- [[claim:clm_053]]
- [[claim:clm_056]]
- [[claim:clm_059]]
- [[claim:clm_027]]
- [[claim:clm_028]]
- [[claim:clm_015]]
- [[claim:clm_016]]
- [[claim:clm_036]]
- [[claim:clm_054]]
- [[claim:clm_002]]
- [[claim:clm_038]]
- [[claim:clm_007]]
- [[claim:clm_008]]
- [[claim:clm_010]]
- [[claim:clm_011]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
