---
schema_version: '0.1'
type: research_report
report_id: report_20260615_what_evidence_grounded_acceptance_test_suites
title: 'From Paper-Grade to Product-Grade: Acceptance-Test Suites and Round-Trip Validation Protocols for Crochet Patterns and Meshes'
intent_id: intent_research_20260614_what_evidence_grounded_acceptance_test_suites
evidence_bundle_id: pending
created_at: '2026-06-15T00:13:27-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# From Paper-Grade to Product-Grade: Acceptance-Test Suites and Round-Trip Validation Protocols for Crochet Patterns and Meshes

## Executive summary

**Inference:** This memo specifies a deterministic, evidence-grounded quality-assurance harness for KnitWit's two flagship capabilities — Pattern to 3D visualization and 3D Object to crochet pattern generation — and traces each acceptance signal to the amigurumi-generation and pattern-representation literature. [claim:clm_inf12]

**Inference:** A four-layer machine-checkable pattern acceptance suite is assemblable from the literature: (1) per-round stitch-count invariants where expected_stitch_count equals the previous round count plus inc minus dec; (2) inc/dec legality restricting shaping ops to the sc|inc(x)|dec(x) alphabet AmiGo proves sufficient; (3) attachment resolvability requiring every stitch to attach unambiguously to a consecutive previous-round stitch; and (4) closure validation that the final round resolves to a closed piece. [claim:clm_inf01]
**Inference:** AmiGo's coupling theorem (Observation 2.3) is the single strongest literature-grounded crochetability acceptance criterion available: it gives a decidable, per-row-pair predicate (consecutive rows coupled => valid sc/inc/dec instructions exist) that is constructively checkable via the finite-state transducer, making it the recommended formal backbone of the inverse-engine acceptance gate rather than heuristic shaping-rate caps alone. [claim:clm_inf02]
**Inference:** Acceptance scoring should be tiered: deterministic execution-grounded checks (Compilation Success Rate via a CrochetPARADE-style validator, stitch-count/attachment consistency, coupling) must be the hard pass/fail gate, while any LLM/VLM judge is advisory only, because CrochetBench shows model performance collapses moving from surface metrics (BLEU/ROUGE) to structural compilation - i.e., string-similarity scoring systematically overstates correctness for spatial-instruction tasks. [claim:clm_inf03]
**Inference:** The acceptance signals map cleanly onto a tiered user-facing confidence meter: GREEN = coupling/CSR pass AND all per-round stitch counts validate AND shape distance within band; YELLOW = pattern compiles and closes but shape distance is marginal OR the validator flags over/under-stretched (tension) stitches; RED = any unresolvable attachment, impossible stitch-count transition, or compilation failure; each tier is backed by a deterministic machine check, so the meter never depends on a model judge alone. [claim:clm_inf08]
**Inference:** Academic feasibility vs product readiness verdict for the acceptance harness: the crochetability/IR-validity gate is academically PROVEN and near-product-ready (coupling theorem + CrochetPARADE/CrochetBench validators are executable today), whereas the mesh shape-fidelity gate is only DEMONSTRATED in research on simple closed forms - it lacks calibrated tolerance bands, a mobile-performance profile, and any test on non-watertight or thin meshes - so KnitWit should ship the deterministic crochetability suite first and treat shape-match scoring as an experimental, clearly-labeled v1 signal. [claim:clm_inf11]

## Background

The paper proposes the first visual, domain-specific, graph-based language for representing crochet patterns, intended as the foundation for rich domain-specific tool support. [claim:clm_001]
The paper establishes ambiguity and limited expressiveness in existing crochet pattern languages as a defined defect class that constrains current digital tools. [claim:clm_002]
Existing graphical crochet notations (such as crochet charts) lack a formal, structured representation of relations between individual stitches, which limits domain-specific tool support. [claim:clm_005]
Even standardized crochet charts can be ambiguous because insertion points are only conveyed by the visual direction of stitch symbols, a defect the authors demonstrate in the user study. [claim:clm_006]
A user study showed the proposed language lets pattern designers express both 2D and 3D patterns and removes ambiguities present in current standard crochet notations. [claim:clm_003]
The contribution is demonstrated via a prototype editor that lets users author patterns in 2D and view them in 3D — the same author-then-preview loop KnitWit targets. [claim:clm_004]
The qualitative think-aloud user study was conducted with six professional crochet designers recruited from a formative survey of designers from the myboshi pattern company. [claim:clm_007]
In the study, participants confirmed that even a small, well-arranged state-of-the-art crochet chart contained three concrete ambiguities (unspecified closing methods and a missing insertion point), evidencing ambiguity as a real defect. [claim:clm_008]
The KnitWit plan mandates Crochet IR validation rules covering per-round stitch-count invariants, increase/decrease legality, and piece-closure constraints as the core of machine validation. [claim:clm_016]

## Pattern acceptance-test suite: machine-checkable crochetability rules

**Inference:** A four-layer machine-checkable pattern acceptance suite is assemblable from the literature: (1) per-round stitch-count invariants where expected_stitch_count equals the previous round count plus inc minus dec; (2) inc/dec legality restricting shaping ops to the sc|inc(x)|dec(x) alphabet AmiGo proves sufficient; (3) attachment resolvability requiring every stitch to attach unambiguously to a consecutive previous-round stitch; and (4) closure validation that the final round resolves to a closed piece. [claim:clm_inf01]
The formal crochetability acceptance criterion is the coupling theorem: if all pairs of consecutive rows of the crochet graph G are coupled, then valid instructions P(G) exist using only sc, inc(x), dec(x). [claim:clm_024]
A finite-state transducer emits dec(x) when x>1 vertices on the current row connect to one head vertex on the next row, inc(x) for the reverse, and sc for a 1:1 coupling. [claim:clm_026]
AmiGo's inputs are exactly a closed manifold triangle mesh M, a single user seed vertex s, and a stitch width w, and it generates instructions using only single crochet (sc), inc(x), and dec(x). [claim:clm_023]
Stitches are validated against the previous row/round by attaching one-by-one to consecutive previous stitches, with turn accounting handled automatically. [claim:clm_010]
The @ attachment operator supports explicit coordinates (@[2,10]), stitch-type counting (@[sc:-1,3]), relative positions referencing the last attachment (@[@+1]), and named stitch labels. [claim:clm_011]
CrochetPARADE uses a custom formal grammar that parses and checks any user-provided pattern for correctness before building a virtual 3D model, explicitly to avoid the ambiguities of plain-English instructions. [claim:clm_009]
The CrochetPARADE validator checks for syntactic and consistency errors such as mismatched stitch counts and impossible attachments, and flags over- or under-stretched stitches - directly reusable as acceptance checks. [claim:clm_036]
The inverse generator must guarantee bounded shaping: no impossible stitch-count transitions and manageable bounded increase/decrease rate. [claim:clm_019]
Inverse-engine acceptance criteria require crochetability (each round resolves, no ambiguous instructions) and shape-match within tolerance bands. [claim:clm_018]
**Inference:** AmiGo's coupling theorem (Observation 2.3) is the single strongest literature-grounded crochetability acceptance criterion available: it gives a decidable, per-row-pair predicate (consecutive rows coupled => valid sc/inc/dec instructions exist) that is constructively checkable via the finite-state transducer, making it the recommended formal backbone of the inverse-engine acceptance gate rather than heuristic shaping-rate caps alone. [claim:clm_inf02]

| Rule | Acceptance check | IR field operated over | Literature source | Evidence |
|------|-----------------|-----------------------------|-------------------|----------|
| Stitch-count invariant | expected_stitch_count of round N equals round N-1 count plus inc minus dec | rounds[].expected_stitch_count, op enum inc/dec | KnitWit plan mandates per-round stitch-count invariants as core machine validation [claim:clm_016] |
| Stitch-count invariant | Validator flags mismatched stitch counts | rounds[].ops, expected_stitch_count | CrochetPARADE checks mismatched stitch counts and impossible attachments [claim:clm_036] |
| Inc/dec legality | Shaping restricted to sc/inc(x)/dec(x) alphabet proven sufficient | op enum sc/inc/dec, visual_hint.shape_role | AmiGo generates instructions using only sc, inc(x), dec(x) from a closed mesh [claim:clm_023] |
| Inc/dec legality | Transducer degree rule decides inc/dec/sc per row-pair coupling | rounds[].ops (inc/dec/sc) | Transducer emits dec(x) for x:1, inc(x) for 1:x, sc for 1:1 coupling [claim:clm_026] |
| Bounded shaping | No impossible stitch-count transitions; bounded inc/dec rate | rounds[].ops shaping sequence | Inverse generator must guarantee bounded shaping with no impossible transitions [claim:clm_019] |
| Attachment resolvability | Every stitch attaches one-by-one to consecutive previous-round stitches | attach op, assembly[].attachment_points | CrochetPARADE validates stitches against the previous row by one-by-one attachment [claim:clm_010] |
| Attachment resolvability | Explicit attachment operator resolves coordinates, counts, relative, labels | attach op, rounds[].ops[].notes | The @ operator supports coordinates, stitch-type counting, relative positions, labels [claim:clm_011] |
| Piece closure | Final round resolves to a closed piece | pieces[].construction, visual_hint.shape_role closure | Coupling theorem guarantees valid instructions exist when all consecutive rows couple [claim:clm_024] |
| Ambiguity detection | Grammar parses/checks for correctness before building a 3D model | pieces[].rounds[].ops parse | CrochetPARADE grammar checks correctness to avoid plain-English ambiguity [claim:clm_009] |
| Ambiguity detection | Ambiguity is a demonstrated real defect class to detect | n/a (defect class) | Participants confirmed three concrete ambiguities in a state-of-the-art chart [claim:clm_008] |

## Shape-match and topology-fidelity metric set

**Inference:** The mesh shape-match metric set should pair a global surface-distance metric (Hausdorff distance or volumetric/approximate-volume difference, as the KnitWit plan specifies) with a topology-fidelity metric (stitch-graph correctness: correct stitch count per round and no broken loops); the force-directed-layout finding that simple amigurumi models were 'accurate in shape and size' establishes that unit-edge geometry plus topological correctness is sufficient signal for plausible-match on beginner forms. [claim:clm_inf04]
Visualizer acceptance criteria require geometric fidelity measured against a reference model (Hausdorff distance or volumetric difference) plus topological correctness (no broken loops, correct stitch counts per round). [claim:clm_017]
The authors report their digital models were accurate in shape and size to the real-world crochet counterparts for the tested simple patterns. [claim:clm_056]
The core method computes geodesic distance on the input surface from a given seed point, then non-uniformly samples the equidistant curves guided by surface curvature to generate an amigurumi crochet pattern. [claim:clm_061]
Rows are isolines of the geodesic distance function f(v)=d(v,s) from the seed, so two points lie on the same row iff f(p)=f(q). [claim:clm_025]
Because amigurumi are crocheted in the round with constant-height single-crochet rows, each stitch in a row is equidistant to the starting point, making geodesic distance the natural model for crochet rows. [claim:clm_062]
The method implements Isenburg et al. [IGG01]'s force-directed layout, which inflates a planar graph by assigning each edge a length and minimizing overall curvature, balancing the two to maximize volume (the analog of stuffing the crocheted shell). [claim:clm_054]
The layout is a non-linear least-squares problem minimizing two energy functions (edge length and per-node local curvature), starting from the assumption that each edge has length one and each node has minimal curvature. [claim:clm_055]
Not every closed 3D model is realizable as a stuffed crocheted object: regions with 'craters' (negative mean and positive Gaussian curvature) are not realizable and are removed by a pre-processing 'inflation' step, while 'saddle-like' regions are handled by adapting the row sampling to use fewer stitches. [claim:clm_065]
**Inference:** No source provides empirically validated numeric tolerance bands (no published Hausdorff or volumetric thresholds distinguishing 'plausible match' from 'failure' for amigurumi exist in this evidence set); KnitWit must therefore derive tolerance bands empirically from its own primitive-mesh corpus, and any band quoted in v1 must be labeled an engineering assumption rather than a literature-cited constant. [claim:clm_inf05]

| Metric axis | Geometric distance used in prior work | Tolerance band status | Evidence |
|-------------|---------------------------------------|----------------------|----------|
| Global surface distance | Hausdorff distance or volumetric difference against a reference model | Named in plan; no numeric threshold published | Visualizer criteria require Hausdorff/volumetric difference plus topological correctness [claim:clm_017] |
| Global surface distance | Geodesic distance field f(v)=d(v,s) from seed defines rows | Method-defining; equidistant-isoline rows | Rows are isolines of the geodesic distance function from the seed [claim:clm_025] |
| Topology fidelity | Correct stitch count per round, no broken loops | Discrete pass/fail, deterministic | Visualizer criteria require topological correctness and correct stitch counts per round [claim:clm_017] |
| Shape/size accuracy | Force-directed unit-edge layout vs real counterpart | Demonstrated qualitatively on simple forms only | Digital models were accurate in shape and size for tested simple patterns [claim:clm_056] |
| Realizability pre-filter | Curvature-based crater/saddle handling before sampling | Hard constructibility gate, not a tolerance | Crater regions are unrealizable and removed; saddle regions use fewer stitches [claim:clm_065] |
| Numeric tolerance band | (none) | Unestablished in evidence set; must be derived empirically | No published Hausdorff/volumetric thresholds for amigurumi exist; bands are engineering assumptions [claim:clm_inf05] |

## Mesh->pattern->preview round-trip benchmark protocol

**Inference:** A reproducible mesh->pattern->preview round-trip benchmark is constructible by composing existing pieces: use AmiGo's mesh->Crochet-Graph->pattern generator as the forward leg and a force-directed-graph-layout reconstruction as the preview leg, scoring the loop on (a) crochetability via the coupling/CSR gate, (b) round-trip visual/shape similarity, and (c) pattern-complexity metrics (max inc/dec rate per round, total rounds, stitch-count variance) over the sphere/egg/pear/animal-primitive corpus. [claim:clm_inf06]
AmiGo generates crochet instructions from a closed triangle mesh plus a single user-specified point such that the knitted, stuffed result resembles the input geometry. [claim:clm_039]
The pipeline builds the geometry and connectivity of a Crochet Graph, which is then translated into a crochet pattern. [claim:clm_040]
In the Crochet Graph, vertices are stitch bases/tops while column edges are stitch stems and row edges encode within-row connectivity. [claim:clm_041]
The method takes a written crochet pattern as input, translates it into a graph, and obtains a 3D representation via a force-directed graph layout. [claim:clm_045]
The tool accepts patterns written in row-by-stitch notation, the most common notation for amigurumi, and converts them to a graph before computing a layout. [claim:clm_046]
The system targets amigurumi and is meant to let designers visualize a pattern before physically crocheting it, reducing crochet/unravel iterations. [claim:clm_051]
The plan defines an inverse-engine test set of 20-50 simple meshes (sphere, egg, pear, animal-ish primitives) scored on shape distance and pattern-complexity metrics including max inc/dec rate per round, total rounds, and stitch-count variance. [claim:clm_020]
Inverse design preconditions are stated explicitly: a closed/watertight triangle mesh, a user-selected seed point, and target stitch size plus gauge assumptions. [claim:clm_021]
Reported example patterns range from ~586 stitches (Pretzel, 30 rows) to 3670 stitches (Teddy, 60 rows), with row counts spanning roughly 30 to 60. [claim:clm_030]
**Inference:** CrochetBench 2025 is directly reusable as a KnitWit acceptance harness for the DSL/IR layer - its Compilation Success Rate metric, four-category error taxonomy (syntax, stitch-definition, labeling/reference, structural), and CrochetPARADE validator transfer with minimal adaptation - but it has a hard scope gap: CrochetBench evaluates text/image->instruction tasks and contains no mesh inputs or geometric shape-fidelity metrics, so KnitWit must build the entire mesh->pattern shape-match half of the harness itself. [claim:clm_inf07]
Acceptance for DSL outputs is measured by Compilation Success Rate (CSR) via the CrochetPARADE validator, directly testing whether generated programs are executable rather than surface-similar. [claim:clm_034]

| Protocol element | Specification | Reuse source | Evidence |
|------------------|---------------|--------------|----------|
| Forward leg (mesh->pattern) | AmiGo mesh->Crochet-Graph->pattern generator | AmiGo | AmiGo generates instructions from a closed mesh plus seed point that resemble the geometry [claim:clm_039] |
| Preview leg (pattern->3D) | Force-directed graph-layout reconstruction from row-by-stitch notation | Greer-Mould force-directed layout | The method translates a written pattern into a graph and gets 3D via force-directed layout [claim:clm_045] |
| Test corpus | 20-50 simple meshes: sphere, egg, pear, animal-ish primitives | KnitWit plan | Plan defines a 20-50 mesh inverse-engine test set scored on shape distance and complexity [claim:clm_020] |
| Corpus preconditions | Closed/watertight mesh, user seed point, target stitch size + gauge | KnitWit plan / AmiGo | Inverse design preconditions: watertight mesh, seed point, stitch size + gauge [claim:clm_021] |
| Pass criterion (crochetability) | Coupling/CSR gate via CrochetPARADE validator | CrochetBench / AmiGo | DSL acceptance is Compilation Success Rate via the CrochetPARADE validator [claim:clm_034] |
| Pass criterion (complexity) | Max inc/dec rate per round, total rounds, stitch-count variance within bounds | KnitWit plan | Scored on max inc/dec rate per round, total rounds, stitch-count variance [claim:clm_020] |
| Scale reference | ~586 stitches (30 rows) to 3670 stitches (60 rows) for realistic forms | AmiGo Table 2 | Example patterns range ~586 to 3670 stitches, rows ~30-60 [claim:clm_030] |
| Scope gap (must build) | Mesh shape-fidelity half absent from reusable benchmarks | CrochetBench gap | CrochetBench has no mesh inputs or geometric shape-fidelity metrics [claim:clm_inf07] |

## Deterministic backstops vs model-based scoring

**Inference:** Acceptance scoring should be tiered: deterministic execution-grounded checks (Compilation Success Rate via a CrochetPARADE-style validator, stitch-count/attachment consistency, coupling) must be the hard pass/fail gate, while any LLM/VLM judge is advisory only, because CrochetBench shows model performance collapses moving from surface metrics (BLEU/ROUGE) to structural compilation - i.e., string-similarity scoring systematically overstates correctness for spatial-instruction tasks. [claim:clm_inf03]
Empirically, performance decays sharply when evaluation moves from surface-level fidelity (BLEU, ROUGE) to structural validity (compilation), motivating execution-grounded acceptance metrics over string-overlap scoring. [claim:clm_038]
CrochetBench reframes crochet evaluation from describing to doing, requiring models to recognize stitches, select structurally appropriate instructions, and generate compilable procedures rather than mere descriptions. [claim:clm_031]
The benchmark centers evaluation on instructional fidelity, asking whether models can output step-wise, compilable instructions that respect symbolic, numerical, and topological structure. [claim:clm_032]
CrochetBench defines a four-task ladder (Tasks A-D) progressing from stitch recognition to comprehension, generation, and executable instruction-to-DSL synthesis, forming an acceptance-style evaluation hierarchy. [claim:clm_033]
Beyond pass/fail compilation, CrochetBench runs a fine-grained error analysis over four failure categories: syntax structure, stitch definition, labeling/reference, and structural/formatting errors. [claim:clm_035]
Reference patterns are sourced from the Yarnspirations repository (6,085 patterns across 55 project categories, 98.77% with product images), normalized into machine-readable JSON via a GPT-4o-mini pipeline. [claim:clm_037]
After rendering, the platform identifies overly loose or tight stitches so users can swap them before crocheting, reducing the need for blocking — a gauge/tension acceptance signal. [claim:clm_012]
**Speculation:** An LLM/VLM judge will likely add value only as a tie-breaker for the YELLOW band (e.g., rating human-readability or whether decreases cluster awkwardly) and should be capped at advisory weight; given the documented surface-vs-structural performance gap, a model judge used as a hard gate would probably admit a non-trivial fraction of non-crochetable patterns, so its outputs should never override a deterministic RED. [claim:clm_spec01]

## Confidence-meter mapping

**Inference:** The acceptance signals map cleanly onto a tiered user-facing confidence meter: GREEN = coupling/CSR pass AND all per-round stitch counts validate AND shape distance within band; YELLOW = pattern compiles and closes but shape distance is marginal OR the validator flags over/under-stretched (tension) stitches; RED = any unresolvable attachment, impossible stitch-count transition, or compilation failure; each tier is backed by a deterministic machine check, so the meter never depends on a model judge alone. [claim:clm_inf08]

| Confidence tier | Deterministic machine signal | Backing check | Evidence |
|-----------------|------------------------------|---------------|----------|
| GREEN | Coupling/CSR pass AND all per-round stitch counts validate AND shape distance within band | Coupling theorem + stitch-count invariant + shape band | Coupling guarantees valid sc/inc/dec instructions exist when consecutive rows couple [claim:clm_024] |
| GREEN | Topological correctness confirmed (no broken loops, correct counts per round) | Topology-fidelity check | Visualizer criteria require topological correctness and correct stitch counts per round [claim:clm_017] |
| YELLOW | Pattern compiles and closes but validator flags over/under-stretched stitches | Tension-flag check | CrochetPARADE flags over- or under-stretched stitches [claim:clm_036] |
| YELLOW | Tension swap signal surfaced to user pre-crochet | Loose/tight stitch detection | Platform identifies overly loose or tight stitches so users can swap them before crocheting [claim:clm_012] |
| RED | Any unresolvable attachment, impossible stitch-count transition, or compilation failure | Attachment/transition/CSR gate | CSR via CrochetPARADE directly tests whether generated programs are executable [claim:clm_034] |

## Analytical derivation: composing the acceptance gate

A finite-state transducer emits dec(x) when x>1 vertices on the current row connect to one head vertex on the next row, inc(x) for the reverse, and sc for a 1:1 coupling. [claim:clm_026]
A single-piece graph requires f to have no saddles; when isolines are multiply-connected the model is auto-decomposed into segments sliced along saddle isolines (ordered by increasing geodesic distance), with crocheting order set by a topological sort of a segment DAG Gsigma. [claim:clm_027]
Adjacent segments are connected by the join-as-you-go method (no sewing), and the crocheting order of segments is determined by a topological sort of the directed segment graph Gsigma ordered by increasing f. [claim:clm_028]
When the topology of the equidistant curves requires more than one cut (e.g., a model with two legs), the method partitions the model into separately crochetable parts and adds assembly instructions for connecting them with no sewing required. [claim:clm_064]
Given a seed point and stitch height, the algorithm computes geodesic distances of all model points from the seed and creates curves equidistant to the seed, spaced by the stitch height; these equidistant curves represent the pattern's rows. [claim:clm_063]
The shape is automatically segmented into crochetable components joined with the join-as-you-go method, requiring no additional sewing. [claim:clm_042]
Join-as-you-go means each segment is crocheted directly onto the last row of the previous segment, so no separate sewing step is needed. [claim:clm_043]
Each stitch becomes a graph node and physical connections between stitches become edges, giving an explicit per-stitch node/edge structure. [claim:clm_047]
Edges carry distinct topological semantics — horizontal edges encode sequential stitch order, vertical edges encode worked-into connections, and constraint edges encode shaping effects. [claim:clm_048]
Each stitch is a node and physical connections are edges: horizontal edges mark sequential (made-immediately-after) connections, vertical edges mark working (top worked into bottom) connections, and non-stitch shaping (e.g., pull-tight dimpling) is represented with additional constraint edges. [claim:clm_052]
Only increase stitches are represented as multiple graph nodes; other tested stitch types map to a single node. [claim:clm_053]
Geometric rendering is produced separately from topology by solving a force-directed layout as a non-linear least-squares optimization that minimizes an edge-length energy and a local-curvature energy. [claim:clm_049]
Each graph node is rendered as a sphere so users can see individual stitches, supporting per-stitch instance rendering and highlighting. [claim:clm_050]
Short rows are deliberately avoided because they are uncommon in crochet, keeping patterns appealing to beginner crocheters. [claim:clm_029]
The method is demonstrated across a large variety of shapes and yields patterns the authors describe as easily crochetable, establishing crochetability and shape-similarity as the acceptance axes. [claim:clm_044]

## Academic feasibility vs product readiness

**Inference:** Academic feasibility vs product readiness verdict for the acceptance harness: the crochetability/IR-validity gate is academically PROVEN and near-product-ready (coupling theorem + CrochetPARADE/CrochetBench validators are executable today), whereas the mesh shape-fidelity gate is only DEMONSTRATED in research on simple closed forms - it lacks calibrated tolerance bands, a mobile-performance profile, and any test on non-watertight or thin meshes - so KnitWit should ship the deterministic crochetability suite first and treat shape-match scoring as an experimental, clearly-labeled v1 signal. [claim:clm_inf11]
All computation runs locally with no central server, but performance scales poorly: patterns of tens of thousands of stitches can take minutes or more to calculate. [claim:clm_014]
The authors report their digital models were accurate in shape and size to the real-world crochet counterparts for the tested simple patterns. [claim:clm_056]
Scope was deliberately restricted to stitches that behave like the single crochet (the prototypical amigurumi stitch) and to patterns worked in continuous rounds, with 'rows' used generically to also mean rounds. [claim:clm_059]
The platform and its computational components are free/open-source under GPLv3 with a Graphviz exception; the manual (including the grammar description) is licensed CC BY-NC-SA 4.0. [claim:clm_015]
**Inference:** No source provides empirically validated numeric tolerance bands (no published Hausdorff or volumetric thresholds distinguishing 'plausible match' from 'failure' for amigurumi exist in this evidence set); KnitWit must therefore derive tolerance bands empirically from its own primitive-mesh corpus, and any band quoted in v1 must be labeled an engineering assumption rather than a literature-cited constant. [claim:clm_inf05]

| Capability | Feasibility side | What remains unproven for product readiness | Evidence |
|------------|-----------------|----------------------------------------|----------|
| Crochetability / IR-validity gate | Academically proven, near-product-ready | Mobile validator latency at scale not profiled | Coupling theorem guarantees valid instructions exist for coupled rows [claim:clm_024] |
| Compilation-success acceptance (CSR) | Academically proven, executable today | Integration into a mobile QA loop unproven | CSR via CrochetPARADE directly tests executability [claim:clm_034] |
| Mesh shape-fidelity scoring | Demonstrated in research on simple forms only | No calibrated tolerance bands; untested on non-watertight/thin meshes | Shape/size accuracy reported only for tested simple patterns [claim:clm_056] |
| Local geometry compute cost | Demonstrated but slow at scale | Mobile performance profile absent | Patterns of tens of thousands of stitches take minutes or more locally [claim:clm_014] |
| Stitch-type coverage | Demonstrated for sc-like stitches in rounds | Non-sc stitch behavior in the harness unproven | Scope restricted to single-crochet-like stitches worked in rounds [claim:clm_059] |

## Contradictions & open disagreements

**Inference:** There is a real terminology/representation contradiction to resolve before building the harness: AmiGo and the force-directed-layout paper both call their structure a 'crochet/stitch graph' but encode it differently - AmiGo's graph rows are geodesic isolines with column/row edges for a generator, while Greer-Mould add horizontal/vertical/constraint edges and model only increases as multiple nodes for a renderer; KnitWit should adopt the IR v0.1 rounds/ops schema as the neutral interchange layer and treat both graphs as derived views, a low-to-medium decision-impact choice that prevents a forward/preview representation mismatch. [claim:clm_inf09]

| Disagreement | Side A | Side B | Resolution | Decision impact | Evidence |
|--------------|--------|--------|-------------------|-----------------|----------|
| Stitch-graph encoding | AmiGo generator graph: vertices are stitch bases/tops, column edges are stems, row edges are within-row connectivity | Greer-Mould renderer graph: horizontal/vertical/constraint edges, increases as multiple nodes | Adopt IR v0.1 rounds/ops as neutral interchange; treat both as derived views | Low-to-medium | AmiGo Crochet Graph uses column/row edges over stitch base/top vertices [claim:clm_041] |
| Stitch-graph encoding | (as above) | Greer-Mould edges encode horizontal sequential, vertical worked-into, constraint shaping | (as above) | Low-to-medium | Greer-Mould edges encode sequential order, worked-into connections, and shaping [claim:clm_048] |
| Increase node count | AmiGo: shaping ops decided by transducer degree rule | Greer-Mould: only increases represented as multiple nodes; others single-node | IR ops layer normalizes both encodings | Low-to-medium | Only increase stitches are represented as multiple graph nodes [claim:clm_053] |

## Risks

**Inference:** Gauge/tension variability is the highest-severity validity risk for the shape-fidelity half of the harness (severity high, likelihood high): both the force-directed layout's constant unit-edge-length assumption and AmiGo's fixed stitch width mean geometric distances are computed on uncalibrated geometry, so a mesh can pass topology checks yet diverge in real stuffed size; the concrete mitigation is to require a user gauge swatch (e.g., a 10x10 stitch/row rectangle) feeding per-edge lengths before any shape-distance band is asserted. [claim:clm_inf10]
Constant edge length of 1 is an explicit accuracy limitation because real stitch size varies with yarn tension, hook size, yarn weight, and stitch type; the authors propose user-supplied gauge swatch measurements (e.g., a 10-row by 10-stitch rectangle) to set per-edge lengths. [claim:clm_057]
A pull-in/closing effect was recreated by adding a single constraint edge linking the first and last graph nodes with an edge length of 6 chosen by trial and error, with curvature computation omitted for those constrained nodes to produce sharp points. [claim:clm_058]
The plan flags the 'PDF importer trap' and gauge/tension variability as top risks, recommending restriction to structured authoring/import templates over full general parsing. [claim:clm_022]
All computation runs locally with no central server, but performance scales poorly: patterns of tens of thousands of stitches can take minutes or more to calculate. [claim:clm_014]
**Speculation:** An LLM/VLM judge will likely add value only as a tie-breaker for the YELLOW band (e.g., rating human-readability or whether decreases cluster awkwardly) and should be capped at advisory weight; given the documented surface-vs-structural performance gap, a model judge used as a hard gate would probably admit a non-trivial fraction of non-crochetable patterns, so its outputs should never override a deterministic RED. [claim:clm_spec01]

| Risk | Severity | Likelihood | Concrete mitigation | Label | Evidence |
|------|----------|-----------|---------------------|-------|----------|
| Gauge/tension variability invalidates shape-distance bands | High | High | Require a user gauge swatch (10x10 stitch/row) feeding per-edge lengths before asserting any band | Inference | Uncalibrated unit-edge/fixed-width geometry can pass topology yet diverge in size [claim:clm_inf10] |
| Constant unit-edge-length geometric error | High | High | Use user-supplied gauge swatch measurements to set per-edge lengths | Supported | Constant edge length of 1 is an explicit accuracy limitation tied to tension/hook/weight [claim:clm_057] |
| PDF-importer trap (freeform parsing) | High | High | Restrict to structured authoring/import templates over general parsing | Supported | Plan flags the PDF importer trap and gauge variability as top risks [claim:clm_022] |
| Mobile/local compute cost at scale | Medium | High | Precompute or bound stitch counts; avoid tens-of-thousands-stitch live compute | Supported | Local compute scales poorly: tens of thousands of stitches take minutes or more [claim:clm_014] |
| Model-judge admits non-crochetable patterns if used as a gate | High | Medium | Cap LLM/VLM judge at advisory weight; never override a deterministic RED | Speculation | A model judge used as a hard gate would probably admit non-crochetable patterns [claim:clm_spec01] |

## Prototype experiments & decision-gate relevance

**Inference:** A four-layer machine-checkable pattern acceptance suite is assemblable from the literature: (1) per-round stitch-count invariants where expected_stitch_count equals the previous round count plus inc minus dec; (2) inc/dec legality restricting shaping ops to the sc|inc(x)|dec(x) alphabet AmiGo proves sufficient; (3) attachment resolvability requiring every stitch to attach unambiguously to a consecutive previous-round stitch; and (4) closure validation that the final round resolves to a closed piece. [claim:clm_inf01]
**Inference:** CrochetBench 2025 is directly reusable as a KnitWit acceptance harness for the DSL/IR layer - its Compilation Success Rate metric, four-category error taxonomy (syntax, stitch-definition, labeling/reference, structural), and CrochetPARADE validator transfer with minimal adaptation - but it has a hard scope gap: CrochetBench evaluates text/image->instruction tasks and contains no mesh inputs or geometric shape-fidelity metrics, so KnitWit must build the entire mesh->pattern shape-match half of the harness itself. [claim:clm_inf07]
**Inference:** A reproducible mesh->pattern->preview round-trip benchmark is constructible by composing existing pieces: use AmiGo's mesh->Crochet-Graph->pattern generator as the forward leg and a force-directed-graph-layout reconstruction as the preview leg, scoring the loop on (a) crochetability via the coupling/CSR gate, (b) round-trip visual/shape similarity, and (c) pattern-complexity metrics (max inc/dec rate per round, total rounds, stitch-count variance) over the sphere/egg/pear/animal-primitive corpus. [claim:clm_inf06]

| Gate | What this run de-risks | Prototype experiment most relevant | Evidence |
|------|------------------------|------------------------------------|----------|
| G1 Evidence quality | All acceptance signals traced to amigurumi-generation/pattern-representation sources | n/a (evidence synthesis) | The acceptance suite is assemblable from the cited literature [claim:clm_inf01] |
| G2 Crochet-IR viability | Stitch-count invariant + inc/dec legality validatable over IR ops | Stitch-count validator; repeat expansion; IR hello-world | KnitWit plan mandates IR stitch-count/inc-dec/closure validation rules [claim:clm_016] |
| G2 Crochet-IR viability | CSR + error taxonomy reusable on IR/DSL outputs | Stitch-count validator (CSR harness) | CrochetBench CSR and four-category error taxonomy transfer with minimal adaptation [claim:clm_inf07] |
| G3 Pattern->3D viability | Force-directed reconstruction supplies the preview leg | IR->stitch-graph; stitch-graph->approximate-3D; row-highlight export | Force-directed layout produces a 3D representation from a pattern graph [claim:clm_045] |
| G4 Mesh->pattern primitive | Coupling theorem backstops generated-pattern crochetability | Primitive-mesh->rounds; mesh-pattern->IR | Coupling theorem is the strongest crochetability acceptance criterion available [claim:clm_inf02] |
| G4 Mesh->pattern primitive | Round-trip protocol scores forward+preview over primitive corpus | Round-trip evaluator | A reproducible mesh->pattern->preview round-trip is constructible from existing pieces [claim:clm_inf06] |
| G5 MVP recommendation | Ship deterministic crochetability suite first; label shape-match experimental | Round-trip evaluator (gated, labeled) | Crochetability gate is product-ready; shape-fidelity is an experimental v1 signal [claim:clm_inf11] |

## Recommendations & decision rules

**Inference:** A four-layer machine-checkable pattern acceptance suite is assemblable from the literature: (1) per-round stitch-count invariants where expected_stitch_count equals the previous round count plus inc minus dec; (2) inc/dec legality restricting shaping ops to the sc|inc(x)|dec(x) alphabet AmiGo proves sufficient; (3) attachment resolvability requiring every stitch to attach unambiguously to a consecutive previous-round stitch; and (4) closure validation that the final round resolves to a closed piece. [claim:clm_inf01]
**Inference:** AmiGo's coupling theorem (Observation 2.3) is the single strongest literature-grounded crochetability acceptance criterion available: it gives a decidable, per-row-pair predicate (consecutive rows coupled => valid sc/inc/dec instructions exist) that is constructively checkable via the finite-state transducer, making it the recommended formal backbone of the inverse-engine acceptance gate rather than heuristic shaping-rate caps alone. [claim:clm_inf02]
**Inference:** Acceptance scoring should be tiered: deterministic execution-grounded checks (Compilation Success Rate via a CrochetPARADE-style validator, stitch-count/attachment consistency, coupling) must be the hard pass/fail gate, while any LLM/VLM judge is advisory only, because CrochetBench shows model performance collapses moving from surface metrics (BLEU/ROUGE) to structural compilation - i.e., string-similarity scoring systematically overstates correctness for spatial-instruction tasks. [claim:clm_inf03]
**Inference:** Gauge/tension variability is the highest-severity validity risk for the shape-fidelity half of the harness (severity high, likelihood high): both the force-directed layout's constant unit-edge-length assumption and AmiGo's fixed stitch width mean geometric distances are computed on uncalibrated geometry, so a mesh can pass topology checks yet diverge in real stuffed size; the concrete mitigation is to require a user gauge swatch (e.g., a 10x10 stitch/row rectangle) feeding per-edge lengths before any shape-distance band is asserted. [claim:clm_inf10]
**Inference:** No source provides empirically validated numeric tolerance bands (no published Hausdorff or volumetric thresholds distinguishing 'plausible match' from 'failure' for amigurumi exist in this evidence set); KnitWit must therefore derive tolerance bands empirically from its own primitive-mesh corpus, and any band quoted in v1 must be labeled an engineering assumption rather than a literature-cited constant. [claim:clm_inf05]
**Inference:** The acceptance signals map cleanly onto a tiered user-facing confidence meter: GREEN = coupling/CSR pass AND all per-round stitch counts validate AND shape distance within band; YELLOW = pattern compiles and closes but shape distance is marginal OR the validator flags over/under-stretched (tension) stitches; RED = any unresolvable attachment, impossible stitch-count transition, or compilation failure; each tier is backed by a deterministic machine check, so the meter never depends on a model judge alone. [claim:clm_inf08]

## Open questions

- What numeric Hausdorff or volumetric tolerance band separates a plausible amigurumi shape-match from a failure on the primitive-mesh corpus?
- Does the deterministic acceptance suite remain fast enough for interactive mobile use given the documented poor scaling at tens of thousands of stitches?
- Do non-watertight or thin meshes, untested in the prior work, break the round-trip protocol's preconditions in practice?
- Should the IR v0.1 rounds/ops schema be extended with explicit attachment-resolution fields beyond the current attach op and assembly attachment_points?

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
