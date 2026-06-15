---
id: mwb_20260614_past_the_pdf_importer_trap_an
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_does_the
target_page: meatywiki/sources/past_the_pdf_importer_trap_an.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_does_the_empirical_evidence_say:
  59 supported claim(s) across 9 source card(s).'
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
links:
  source_cards:
  - src_20260614_kw003_00
  - src_20260614_kw003_01
  - src_20260614_kw003_02
  - src_20260614_kw003_03
  - src_20260614_kw003_04
  - src_20260614_kw003_05
  - src_20260614_kw003_06
  - src_20260614_kw003_07
  - src_20260614_kw003_08
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Past the PDF Importer Trap: An Evidence Review of Crochet Pattern Parsing and a Validator-Backed Ingestion Strategy

## Summary

Source note distilled from research run rf_run_20260614_what_does_the_empirical_evidence_say: 59 supported claim(s) across 9 source card(s).

## Key claims

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

## Sources

- src_20260614_kw003_00 — CrochetBench: Can Vision-Language Models Move from Describing to Doing in the Crochet Domain?
- src_20260614_kw003_01 — Translation of User Crochet Patterns to CrochetPARADE Syntax Using Large Language Models
- src_20260614_kw003_02 — CrochetPARADE - Crochet PAttern Renderer, Analyzer, and DEbugger (repository)
- src_20260614_kw003_03 — CrochetBench: Can Vision-Language Models Move from Describing to Doing in the Crochet Domain?
- src_20260614_kw003_04 — CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger)
- src_20260614_kw003_05 — Parsing Semi-structured Languages: A Crochet Pattern to Diagram Translation
- src_20260614_kw003_06 — KnitScript: A Domain-Specific Scripting Language for Advanced Machine Knitting
- src_20260614_kw003_07 — [Literature Review] CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260614_kw003_08 — Developing CROML (Crochet Obvious Minimal Language)

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
