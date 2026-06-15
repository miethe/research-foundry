---
schema_version: '0.1'
type: research_report
report_id: report_20260615_what_evidence_grounded_acceptance_test_suites
title: What evidence-grounded acceptance-test suites and quantitative validation protocols
intent_id: intent_research_20260614_what_evidence_grounded_acceptance_test_suites
evidence_bundle_id: pending
created_at: '2026-06-15T00:13:27-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

The paper proposes the first visual, domain-specific, graph-based language for representing crochet patterns, intended as the foundation for rich domain-specific tool support. [claim:clm_001]
The paper establishes ambiguity and limited expressiveness in existing crochet pattern languages as a defined defect class that constrains current digital tools. [claim:clm_002]
A user study showed the proposed language lets pattern designers express both 2D and 3D patterns and removes ambiguities present in current standard crochet notations. [claim:clm_003]
The contribution is demonstrated via a prototype editor that lets users author patterns in 2D and view them in 3D — the same author-then-preview loop KnitWit targets. [claim:clm_004]
Existing graphical crochet notations (such as crochet charts) lack a formal, structured representation of relations between individual stitches, which limits domain-specific tool support. [claim:clm_005]
Even standardized crochet charts can be ambiguous because insertion points are only conveyed by the visual direction of stitch symbols, a defect the authors demonstrate in the user study. [claim:clm_006]
The qualitative think-aloud user study was conducted with six professional crochet designers recruited from a formative survey of designers from the myboshi pattern company. [claim:clm_007]
In the study, participants confirmed that even a small, well-arranged state-of-the-art crochet chart contained three concrete ambiguities (unspecified closing methods and a missing insertion point), evidencing ambiguity as a real defect. [claim:clm_008]
CrochetPARADE uses a custom formal grammar that parses and checks any user-provided pattern for correctness before building a virtual 3D model, explicitly to avoid the ambiguities of plain-English instructions. [claim:clm_009]
Stitches are validated against the previous row/round by attaching one-by-one to consecutive previous stitches, with turn accounting handled automatically. [claim:clm_010]
The @ attachment operator supports explicit coordinates (@[2,10]), stitch-type counting (@[sc:-1,3]), relative positions referencing the last attachment (@[@+1]), and named stitch labels. [claim:clm_011]
After rendering, the platform identifies overly loose or tight stitches so users can swap them before crocheting, reducing the need for blocking — a gauge/tension acceptance signal. [claim:clm_012]
Export produces a 2D SVG that shows stitch connections and identifies each stitch by type, row number, and position within a row, plus 3D files importable into Blender. [claim:clm_013]
All computation runs locally with no central server, but performance scales poorly: patterns of tens of thousands of stitches can take minutes or more to calculate. [claim:clm_014]
The platform and its computational components are free/open-source under GPLv3 with a Graphviz exception; the manual (including the grammar description) is licensed CC BY-NC-SA 4.0. [claim:clm_015]
The KnitWit plan mandates Crochet IR validation rules covering per-round stitch-count invariants, increase/decrease legality, and piece-closure constraints as the core of machine validation. [claim:clm_016]
Visualizer acceptance criteria require geometric fidelity measured against a reference model (Hausdorff distance or volumetric difference) plus topological correctness (no broken loops, correct stitch counts per round). [claim:clm_017]
Inverse-engine acceptance criteria require crochetability (each round resolves, no ambiguous instructions) and shape-match within tolerance bands. [claim:clm_018]
The inverse generator must guarantee bounded shaping: no impossible stitch-count transitions and manageable bounded increase/decrease rate. [claim:clm_019]
The plan defines an inverse-engine test set of 20-50 simple meshes (sphere, egg, pear, animal-ish primitives) scored on shape distance and pattern-complexity metrics including max inc/dec rate per round, total rounds, and stitch-count variance. [claim:clm_020]
Inverse design preconditions are stated explicitly: a closed/watertight triangle mesh, a user-selected seed point, and target stitch size plus gauge assumptions. [claim:clm_021]
The plan flags the 'PDF importer trap' and gauge/tension variability as top risks, recommending restriction to structured authoring/import templates over full general parsing. [claim:clm_022]
AmiGo's inputs are exactly a closed manifold triangle mesh M, a single user seed vertex s, and a stitch width w, and it generates instructions using only single crochet (sc), inc(x), and dec(x). [claim:clm_023]
The formal crochetability acceptance criterion is the coupling theorem: if all pairs of consecutive rows of the crochet graph G are coupled, then valid instructions P(G) exist using only sc, inc(x), dec(x). [claim:clm_024]
Rows are isolines of the geodesic distance function f(v)=d(v,s) from the seed, so two points lie on the same row iff f(p)=f(q). [claim:clm_025]
A finite-state transducer emits dec(x) when x>1 vertices on the current row connect to one head vertex on the next row, inc(x) for the reverse, and sc for a 1:1 coupling. [claim:clm_026]
A single-piece graph requires f to have no saddles; when isolines are multiply-connected the model is auto-decomposed into segments sliced along saddle isolines (ordered by increasing geodesic distance), with crocheting order set by a topological sort of a segment DAG Gsigma. [claim:clm_027]
Adjacent segments are connected by the join-as-you-go method (no sewing), and the crocheting order of segments is determined by a topological sort of the directed segment graph Gsigma ordered by increasing f. [claim:clm_028]
Short rows are deliberately avoided because they are uncommon in crochet, keeping patterns appealing to beginner crocheters. [claim:clm_029]
Reported example patterns range from ~586 stitches (Pretzel, 30 rows) to 3670 stitches (Teddy, 60 rows), with row counts spanning roughly 30 to 60. [claim:clm_030]
CrochetBench reframes crochet evaluation from describing to doing, requiring models to recognize stitches, select structurally appropriate instructions, and generate compilable procedures rather than mere descriptions. [claim:clm_031]
The benchmark centers evaluation on instructional fidelity, asking whether models can output step-wise, compilable instructions that respect symbolic, numerical, and topological structure. [claim:clm_032]
CrochetBench defines a four-task ladder (Tasks A-D) progressing from stitch recognition to comprehension, generation, and executable instruction-to-DSL synthesis, forming an acceptance-style evaluation hierarchy. [claim:clm_033]
Acceptance for DSL outputs is measured by Compilation Success Rate (CSR) via the CrochetPARADE validator, directly testing whether generated programs are executable rather than surface-similar. [claim:clm_034]
Beyond pass/fail compilation, CrochetBench runs a fine-grained error analysis over four failure categories: syntax structure, stitch definition, labeling/reference, and structural/formatting errors. [claim:clm_035]
The CrochetPARADE validator checks for syntactic and consistency errors such as mismatched stitch counts and impossible attachments, and flags over- or under-stretched stitches - directly reusable as acceptance checks. [claim:clm_036]
Reference patterns are sourced from the Yarnspirations repository (6,085 patterns across 55 project categories, 98.77% with product images), normalized into machine-readable JSON via a GPT-4o-mini pipeline. [claim:clm_037]
Empirically, performance decays sharply when evaluation moves from surface-level fidelity (BLEU, ROUGE) to structural validity (compilation), motivating execution-grounded acceptance metrics over string-overlap scoring. [claim:clm_038]
AmiGo generates crochet instructions from a closed triangle mesh plus a single user-specified point such that the knitted, stuffed result resembles the input geometry. [claim:clm_039]
The pipeline builds the geometry and connectivity of a Crochet Graph, which is then translated into a crochet pattern. [claim:clm_040]
In the Crochet Graph, vertices are stitch bases/tops while column edges are stitch stems and row edges encode within-row connectivity. [claim:clm_041]
The shape is automatically segmented into crochetable components joined with the join-as-you-go method, requiring no additional sewing. [claim:clm_042]
Join-as-you-go means each segment is crocheted directly onto the last row of the previous segment, so no separate sewing step is needed. [claim:clm_043]
The method is demonstrated across a large variety of shapes and yields patterns the authors describe as easily crochetable, establishing crochetability and shape-similarity as the acceptance axes. [claim:clm_044]
The method takes a written crochet pattern as input, translates it into a graph, and obtains a 3D representation via a force-directed graph layout. [claim:clm_045]
The tool accepts patterns written in row-by-stitch notation, the most common notation for amigurumi, and converts them to a graph before computing a layout. [claim:clm_046]
Each stitch becomes a graph node and physical connections between stitches become edges, giving an explicit per-stitch node/edge structure. [claim:clm_047]
Edges carry distinct topological semantics — horizontal edges encode sequential stitch order, vertical edges encode worked-into connections, and constraint edges encode shaping effects. [claim:clm_048]
Geometric rendering is produced separately from topology by solving a force-directed layout as a non-linear least-squares optimization that minimizes an edge-length energy and a local-curvature energy. [claim:clm_049]
Each graph node is rendered as a sphere so users can see individual stitches, supporting per-stitch instance rendering and highlighting. [claim:clm_050]
The system targets amigurumi and is meant to let designers visualize a pattern before physically crocheting it, reducing crochet/unravel iterations. [claim:clm_051]
Each stitch is a node and physical connections are edges: horizontal edges mark sequential (made-immediately-after) connections, vertical edges mark working (top worked into bottom) connections, and non-stitch shaping (e.g., pull-tight dimpling) is represented with additional constraint edges. [claim:clm_052]
Only increase stitches are represented as multiple graph nodes; other tested stitch types map to a single node. [claim:clm_053]
The method implements Isenburg et al. [IGG01]'s force-directed layout, which inflates a planar graph by assigning each edge a length and minimizing overall curvature, balancing the two to maximize volume (the analog of stuffing the crocheted shell). [claim:clm_054]
The layout is a non-linear least-squares problem minimizing two energy functions (edge length and per-node local curvature), starting from the assumption that each edge has length one and each node has minimal curvature. [claim:clm_055]
The authors report their digital models were accurate in shape and size to the real-world crochet counterparts for the tested simple patterns. [claim:clm_056]
Constant edge length of 1 is an explicit accuracy limitation because real stitch size varies with yarn tension, hook size, yarn weight, and stitch type; the authors propose user-supplied gauge swatch measurements (e.g., a 10-row by 10-stitch rectangle) to set per-edge lengths. [claim:clm_057]
A pull-in/closing effect was recreated by adding a single constraint edge linking the first and last graph nodes with an edge length of 6 chosen by trial and error, with curvature computation omitted for those constrained nodes to produce sharp points. [claim:clm_058]
Scope was deliberately restricted to stitches that behave like the single crochet (the prototypical amigurumi stitch) and to patterns worked in continuous rounds, with 'rows' used generically to also mean rounds. [claim:clm_059]
The paper 'Amigurumi Crochet Patterns from Geodesic Distances' is authored by Mirela Ben Chen and Michal Edelstein of the Technion Computer Science Department, in the Bridges 2024 Conference Proceedings (pp. 369-372). [claim:clm_060]
The core method computes geodesic distance on the input surface from a given seed point, then non-uniformly samples the equidistant curves guided by surface curvature to generate an amigurumi crochet pattern. [claim:clm_061]
Because amigurumi are crocheted in the round with constant-height single-crochet rows, each stitch in a row is equidistant to the starting point, making geodesic distance the natural model for crochet rows. [claim:clm_062]
Given a seed point and stitch height, the algorithm computes geodesic distances of all model points from the seed and creates curves equidistant to the seed, spaced by the stitch height; these equidistant curves represent the pattern's rows. [claim:clm_063]
When the topology of the equidistant curves requires more than one cut (e.g., a model with two legs), the method partitions the model into separately crochetable parts and adds assembly instructions for connecting them with no sewing required. [claim:clm_064]
Not every closed 3D model is realizable as a stuffed crocheted object: regions with 'craters' (negative mean and positive Gaussian curvature) are not realizable and are removed by a pre-processing 'inflation' step, while 'saddle-like' regions are handled by adapting the row sampling to use fewer stitches. [claim:clm_065]
This Bridges paper is an accessible overview of the authors' prior publication 'AmiGo: Computational Design of Amigurumi Crochet Patterns' (Edelstein, Peleg, Itzhaki, Ben-Chen) presented at the Symposium on Computational Fabrication. [claim:clm_066]

## Inferences

**Inference:** A four-layer machine-checkable pattern acceptance suite is assemblable from the literature: (1) per-round stitch-count invariants where expected_stitch_count equals the previous round count plus inc minus dec; (2) inc/dec legality restricting shaping ops to the sc|inc(x)|dec(x) alphabet AmiGo proves sufficient; (3) attachment resolvability requiring every stitch to attach unambiguously to a consecutive previous-round stitch; and (4) closure validation that the final round resolves to a closed piece. [claim:clm_inf01]
**Inference:** AmiGo's coupling theorem (Observation 2.3) is the single strongest literature-grounded crochetability acceptance criterion available: it gives a decidable, per-row-pair predicate (consecutive rows coupled => valid sc/inc/dec instructions exist) that is constructively checkable via the finite-state transducer, making it the recommended formal backbone of the inverse-engine acceptance gate rather than heuristic shaping-rate caps alone. [claim:clm_inf02]
**Inference:** Acceptance scoring should be tiered: deterministic execution-grounded checks (Compilation Success Rate via a CrochetPARADE-style validator, stitch-count/attachment consistency, coupling) must be the hard pass/fail gate, while any LLM/VLM judge is advisory only, because CrochetBench shows model performance collapses moving from surface metrics (BLEU/ROUGE) to structural compilation - i.e., string-similarity scoring systematically overstates correctness for spatial-instruction tasks. [claim:clm_inf03]
**Inference:** The mesh shape-match metric set should pair a global surface-distance metric (Hausdorff distance or volumetric/approximate-volume difference, as the KnitWit plan specifies) with a topology-fidelity metric (stitch-graph correctness: correct stitch count per round and no broken loops); the force-directed-layout finding that simple amigurumi models were 'accurate in shape and size' establishes that unit-edge geometry plus topological correctness is sufficient signal for plausible-match on beginner forms. [claim:clm_inf04]
**Inference:** No source provides empirically validated numeric tolerance bands (no published Hausdorff or volumetric thresholds distinguishing 'plausible match' from 'failure' for amigurumi exist in this evidence set); KnitWit must therefore derive tolerance bands empirically from its own primitive-mesh corpus, and any band quoted in v1 must be labeled an engineering assumption rather than a literature-cited constant. [claim:clm_inf05]
**Inference:** A reproducible mesh->pattern->preview round-trip benchmark is constructible by composing existing pieces: use AmiGo's mesh->Crochet-Graph->pattern generator as the forward leg and a force-directed-graph-layout reconstruction as the preview leg, scoring the loop on (a) crochetability via the coupling/CSR gate, (b) round-trip visual/shape similarity, and (c) pattern-complexity metrics (max inc/dec rate per round, total rounds, stitch-count variance) over the sphere/egg/pear/animal-primitive corpus. [claim:clm_inf06]
**Inference:** CrochetBench 2025 is directly reusable as a KnitWit acceptance harness for the DSL/IR layer - its Compilation Success Rate metric, four-category error taxonomy (syntax, stitch-definition, labeling/reference, structural), and CrochetPARADE validator transfer with minimal adaptation - but it has a hard scope gap: CrochetBench evaluates text/image->instruction tasks and contains no mesh inputs or geometric shape-fidelity metrics, so KnitWit must build the entire mesh->pattern shape-match half of the harness itself. [claim:clm_inf07]
**Inference:** The acceptance signals map cleanly onto a tiered user-facing confidence meter: GREEN = coupling/CSR pass AND all per-round stitch counts validate AND shape distance within band; YELLOW = pattern compiles and closes but shape distance is marginal OR the validator flags over/under-stretched (tension) stitches; RED = any unresolvable attachment, impossible stitch-count transition, or compilation failure; each tier is backed by a deterministic machine check, so the meter never depends on a model judge alone. [claim:clm_inf08]
**Inference:** There is a real terminology/representation contradiction to resolve before building the harness: AmiGo and the force-directed-layout paper both call their structure a 'crochet/stitch graph' but encode it differently - AmiGo's graph rows are geodesic isolines with column/row edges for a generator, while Greer-Mould add horizontal/vertical/constraint edges and model only increases as multiple nodes for a renderer; KnitWit should adopt the IR v0.1 rounds/ops schema as the neutral interchange layer and treat both graphs as derived views, a low-to-medium decision-impact choice that prevents a forward/preview representation mismatch. [claim:clm_inf09]
**Inference:** Gauge/tension variability is the highest-severity validity risk for the shape-fidelity half of the harness (severity high, likelihood high): both the force-directed layout's constant unit-edge-length assumption and AmiGo's fixed stitch width mean geometric distances are computed on uncalibrated geometry, so a mesh can pass topology checks yet diverge in real stuffed size; the concrete mitigation is to require a user gauge swatch (e.g., a 10x10 stitch/row rectangle) feeding per-edge lengths before any shape-distance band is asserted. [claim:clm_inf10]
**Inference:** Academic feasibility vs product readiness verdict for the acceptance harness: the crochetability/IR-validity gate is academically PROVEN and near-product-ready (coupling theorem + CrochetPARADE/CrochetBench validators are executable today), whereas the mesh shape-fidelity gate is only DEMONSTRATED in research on simple closed forms - it lacks calibrated tolerance bands, a mobile-performance profile, and any test on non-watertight or thin meshes - so KnitWit should ship the deterministic crochetability suite first and treat shape-match scoring as an experimental, clearly-labeled v1 signal. [claim:clm_inf11]

## Speculation

**Speculation:** An LLM/VLM judge will likely add value only as a tie-breaker for the YELLOW band (e.g., rating human-readability or whether decreases cluster awkwardly) and should be capped at advisory weight; given the documented surface-vs-structural performance gap, a model judge used as a hard gate would probably admit a non-trivial fraction of non-crochetable patterns, so its outputs should never override a deterministic RED. [claim:clm_spec01]

## Open questions

- None recorded.

## Sources

- src_20260614_kw011_06: Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260614_kw011_03: CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger) — Manual & Grammar
- src_20260614_kw011_07: KnitWit Research Plan — Two-Track Deep Dive (local seed, ChatGPT 5.2, 2026-02 to 2026-04)
- src_20260614_kw011_00: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw011_02: CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260614_kw011_01: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw011_04: Modeling Crochet Patterns with a Force-directed Graph Layout
- src_20260614_kw011_08: Modeling crochet patterns with a force-directed graph layout
- src_20260614_kw011_05: Amigurumi Crochet Patterns from Geodesic Distances
