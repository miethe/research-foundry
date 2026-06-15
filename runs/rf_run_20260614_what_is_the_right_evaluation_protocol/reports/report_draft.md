---
schema_version: '0.1'
type: research_report
report_id: report_20260614_what_is_the_right_evaluation_protocol
title: 'KnitWit B4 Follow-on: Evaluating Inverse Amigurumi Generators - Shape-Fidelity Metrics, Pattern-Complexity Benchmarks, and the Evidence-Backed Edit Loop'
intent_id: intent_research_20260614_what_is_the_right_evaluation_protocol
evidence_bundle_id: pending
created_at: '2026-06-14T22:42:50-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# KnitWit B4 Follow-on: Evaluating Inverse Amigurumi Generators

## Executive summary

This memo specifies how to score an inverse amigurumi generator and where the evidence currently stands. The reference generator in the literature, AmiGo, generates crochet instructions (patterns) from an input 3D model, focusing specifically on Amigurumi (knitted stuffed toys). [claim:clm_001]

The central gap is that AmiGo judges success only qualitatively, with the paper stating the result will be 'similar' to the input mesh and reporting no Hausdorff/Chamfer/volume distance metric. [claim:clm_008]

**Inference:** A genuine contradiction exists between AmiGo's qualitative-only success criterion ('the result will be similar to M', no numeric metric) and this run's evaluation goal of a numeric shape-fidelity score; the resolution is that AmiGo proves academic feasibility of generation but provides zero quantitative evaluation, so the geometric triad must be imported from the reconstruction-benchmark lineage - a high-impact decision because without it the generator has no automated regression test. [claim:clm_inf10]

**Inference:** The recommended shape-fidelity metric set for an inverse amigurumi generator is symmetric Chamfer distance plus volumetric IoU plus normal consistency (the Sulzer-benchmark triad), because it jointly captures point-wise geometric error, occupied-volume overlap, and surface-orientation agreement, and AmiGo currently ships none of these despite explicitly targeting 'similarity' to the input mesh. [claim:clm_inf01]

**Inference:** A defensible three-metric crochetability set is (1) max increase/decrease rate per round, (2) stitch-count per layer/round (and its round-to-round variance), and (3) piece/segment count, all computable directly from the Crochet IR rounds[].ops and assembly[] without external tooling; AmiGo's own outputs (60 rounds, 6-8 segments, 2.5k-3.7k stitches) supply a concrete worked-example envelope for these metrics. [claim:clm_inf04]

**Inference:** CrochetBench (2025) is reusable as a complexity-stratification and model-baseline reference but NOT as a drop-in mesh-to-pattern scoring harness, because its four tasks score text/DSL generation from descriptions (F1, BLEU, Valid Pattern Rate, DINO) and contain no target-mesh-vs-output geometric metric; the inverse-generator benchmark must therefore be built fresh on the B4 20-50 primitive set, borrowing only its DSL-compilation validity gate. [claim:clm_inf06]

**Speculation:** The highest-leverage prototype to de-risk gate G4 is a round-trip evaluator (EXP-010): generate a pattern from each B4 primitive mesh, compile it in CrochetPARADE to a 3D render, and score that render against the (stuffing-deformed) target with the CD+IoU+NC triad; this single harness simultaneously exercises the mesh-to-pattern primitive, the validity gate, and the shape-fidelity metric set, and is likely the cheapest path to a defensible go/no-go on the inverse generator. [claim:clm_spec01]

## Background: the reference generator and its representation

Input to the AmiGo method is a closed triangle mesh plus a single user-specified point, and the output, when knitted and stuffed, yields a toy similar to the input geometry. [claim:clm_002]
The core artifact is a 'Crochet Graph' encoding geometry and connectivity that is then translated into a human-readable crochet pattern. [claim:clm_003]
The input is a closed manifold triangle mesh plus a single user-specified seed vertex and a user-selected stitch width; seed placement is an interactive control with no automatic selection provided. [claim:clm_007]
The shape is automatically segmented into crochetable components joined via the join-as-you-go method, eliminating any additional sewing. [claim:clm_004]
The shape is auto-segmented at the saddle points of a geodesic distance function from the seed, and isolines of that geodesic distance become the crochet rows. [claim:clm_009]
The stitch vocabulary is single crochet (sc) plus increase inc(x) and decrease dec(x) stitches whose x counts are derived from row-to-row vertex coupling/degree, with no explicit per-round bound on increases or decreases stated. [claim:clm_011]
The method computes geodesic distance on the surface from a seed point, then samples the equidistant curves non-uniformly, guided by surface curvature, framing amigurumi shaping as a geodesic-distance problem. [claim:clm_053]
Because amigurumi are crocheted in the round at constant row height, each stitch in a row is equidistant from the start point, making geodesic distance the natural model for crochet rows. [claim:clm_055]
The authors claim applicability to a large variety of shapes and geometries yielding 'easily crochetable' patterns, but state no numeric fidelity score in the abstract. [claim:clm_005]
The paper is an 11-page, 10-figure work published at SCF 2022, submitted 2 Nov 2022, classified under Graphics (cs.GR). [claim:clm_006]
Reported complexity: the Teddy hi-res model is 60 rows / 6 segments / 3,670 stitches in 2.5 min and Moomoo is 60 rows / 8 segments / 2,491 stitches in 6.9 min, with all runtimes between 0.2 and 6.9 min on an Intel Core i7 desktop. [claim:clm_012]

## Shape-fidelity metric set

This section defines the geometric metrics, each backed by a source card, and notes how each adapts from a rigid mesh to a soft stuffed result.

### Metric definitions and provenance

The surface-reconstruction benchmark evaluates reconstructed surfaces against ground truth using three geometric metrics: volumetric IoU, symmetric Chamfer distance (CD), and normal consistency (NC). [claim:clm_013]
The stated evaluation goal is for the reconstructed surface to be as close as possible to the ground-truth surface in both geometry and topology, motivating the multi-metric protocol. [claim:clm_017]
Symmetric Chamfer distance is computed by sampling equal-size point sets on the facets of both the ground-truth mesh and the reconstructed mesh, with each set fixed at 100,000 points. [claim:clm_014]
The symmetric Chamfer distance averages, in both directions, the squared nearest-neighbor distance from each sampled point on one mesh to the closest point on the other mesh. [claim:clm_015]
Volumetric IoU is approximated by sampling 100,000 points in the union of the bounding boxes of the ground-truth and reconstructed volumes and computing the inside-intersection over inside-union ratio. [claim:clm_016]
Normal consistency is estimated as the mean of scalar products between the unit normal at each sampled point and the unit normal at its nearest-neighbor point on the other mesh, averaged bidirectionally. [claim:clm_051]
All benchmark surfaces are single-component, closed, and manifold, which lets the benchmark add topology indices (number of components, boundary edges, non-manifold edges) on top of the geometric metrics. [claim:clm_018]
Beyond geometric accuracy the benchmark reports topologic quality indices: number of components, number of boundary edges (edges in only one facet), and number of non-manifold edges, since target surfaces are single-component, closed, and manifold. [claim:clm_052]

### The curvature/normal-aware term

NCD adds a normal-steered weighting to Chamfer Distance based on the angle between each mesh-sampled point's normal and the vector to its corresponding input point. [claim:clm_019]
NCD uses readily available mesh-sampled point normals to weight coordinate-based Euclidean distances, extending Chamfer Distance without requiring input-cloud normals. [claim:clm_020]
Normal estimation on unoriented input point clouds is computationally intensive (matrix decomposition or pre-trained models), whereas mesh-sampled normals come cheaply from the cross product of mesh vertices. [claim:clm_021]
NCD incurs only a negligible increase in computational complexity compared with plain Chamfer Distance, keeping it viable for efficiency-sensitive training/evaluation loops. [claim:clm_022]
Used as the training loss across multiple point-to-mesh reconstruction models and initial watertight meshes on benchmark datasets, NCD outperforms state-of-the-art Chamfer Distance variants. [claim:clm_023]
Plain Chamfer Distance can add a normal-consistency term to improve reconstruction fidelity, but only at the cost of efficiency, which is the trade-off NCD is designed to avoid. [claim:clm_024]

**Inference:** Normal-guided Chamfer Distance (NCD) is the preferred curvature/normal-aware fidelity term over a plain CD-plus-normal-consistency combination for an iterative edit loop, because NCD folds orientation sensitivity into a single distance at negligible added compute and uses cheap mesh-sampled normals, making it viable to re-score after every edit without the efficiency penalty of a separate NC term. [claim:clm_inf03]

### Soft-result adaptation

**Inference:** Because the deliverable is a stuffed soft object rather than a rigid mesh, shape-fidelity scoring should compare against a stuffing-deformed proxy of the target (or apply tolerance bands of at least one stitch-width w) rather than the raw input mesh, since AmiGo itself only guarantees the stuffed result is 'similar' under the assumption that all edge lengths equal the stitch width w. [claim:clm_inf02]

### Shape-fidelity metric matrix

| Metric | What it captures | Source-backed definition | Soft-result adaptation | Evidence |
|--------|------------------|--------------------------|------------------------|----------|
| Symmetric Chamfer distance (CD) | Point-wise bidirectional geometric error | 100k point samples per mesh, bidirectional nearest-neighbor distance | Compare to stuffing-deformed proxy / tolerance band >= one stitch-width w | [claim:clm_014] |
| Symmetric Chamfer distance (CD) | Bidirectional averaging detail | Averages squared nearest-neighbor distance both directions | Quantization at stitch-width w should not count as error | [claim:clm_015] |
| Volumetric IoU | Occupied-volume overlap | 100k points in union of bounding boxes, inside-intersection over inside-union | Robust to small surface deformation from stuffing | [claim:clm_016] |
| Normal consistency (NC) | Surface-orientation agreement | Mean bidirectional scalar product of nearest-neighbor unit normals | Sensitive to lumpiness of stuffed result; pair with tolerance band | [claim:clm_051] |
| Normal-guided CD (NCD) | Single curvature/normal-aware distance | Normal-angle weighting folded into CD at negligible extra compute | Preferred for per-edit re-scoring on soft target | [claim:clm_022] |
| Topology indices | Components / boundary / non-manifold edges | Counted because targets are single-component, closed, manifold | Validate generated surface is a single closed piece before scoring | [claim:clm_052] |

## Pattern-complexity / crochetability metric set

This section defines the crochetability metrics and the human-executable thresholds, and ties them to the B4 constraint spec.

CrochetBench evaluates the shift from describing to doing via fine-grained procedural reasoning, using the CrochetPARADE DSL as an intermediate representation for structural validation and execution-based functional evaluation. [claim:clm_025]
Instruction length stratifies pattern complexity by skill level, with average character counts of Beginner ~1,674, Easy ~2,761, Intermediate ~4,221, and Experienced ~7,689 - a usable proxy for complexity bins. [claim:clm_031]
In saddle-like regions (negative Gaussian and mean curvature) the algorithm adapts row sampling to use fewer stitches, directly supporting curvature-bounded stitch-density / inc-dec thresholds. [claim:clm_056]
User feedback surfaced the need for per-layer complexity overviews — specifically a count of stitches per layer and clear layer-number marking — supporting layer as the natural unit for complexity metrics. [claim:clm_045]
Increases are encoded as multiple incoming insert edges and decreases as multiple outgoing insert edges, giving a concrete graph-structural signature for shaping operations. [claim:clm_043]

**Inference:** A defensible three-metric crochetability set is (1) max increase/decrease rate per round, (2) stitch-count per layer/round (and its round-to-round variance), and (3) piece/segment count, all computable directly from the Crochet IR rounds[].ops and assembly[] without external tooling; AmiGo's own outputs (60 rounds, 6-8 segments, 2.5k-3.7k stitches) supply a concrete worked-example envelope for these metrics. [claim:clm_inf04]

**Inference:** No source supplies a published numeric threshold separating 'human-executable' from 'too brittle', so any inc/dec-rate cap must be labeled defensible inference; the strongest evidence-backed proxy is CrochetBench's instruction-length skill bands (Beginner ~1,674 to Experienced ~7,689 chars), which can be repurposed to bin generated-pattern complexity by stitch/round count rather than inventing an unsupported per-round bound. [claim:clm_inf05]

### Crochetability metric matrix (tied to the B4 constraint spec)

| Metric | IR field it reads | Human-executable threshold basis | B4 constraint tie-in | Evidence |
|--------|-------------------|----------------------------------|----------------------|----------|
| Max increase/decrease rate per round | rounds[].ops (inc/dec) | Inference: no published cap; geometry-driven, bin via skill bands | inc/dec schedule produced by mesh-to-pattern step | [claim:clm_inf05] |
| Stitch-count per layer + round-to-round variance | rounds[].expected_stitch_count | Worked envelope 2,491-3,670 stitches over 60 rounds | per-round counts emitted by round extraction | [claim:clm_inf04] |
| Piece / segment count | assembly[] | Worked envelope 6-8 segments | join-as-you-go segments from auto-segmentation | [claim:clm_004] |
| Complexity bin (proxy) | derived stitch/round totals | Beginner ~1,674 to Experienced ~7,689 chars repurposed | maps generated pattern to a skill-level band | [claim:clm_031] |
| Curvature-adaptive density check | rounds[].visual_hint.shape_role | Fewer stitches in saddle regions is expected, not an error | validates inc/dec follows mesh curvature | [claim:clm_056] |

## Benchmark protocol

This section specifies the mesh set, scoring procedure, and pass/fail bands, and judges what to reuse versus build.

The surface-reconstruction benchmark evaluates reconstruction geometry with three geometric metrics: volumetric intersection-over-union (IoU), symmetric Chamfer distance (CD), and normal consistency (NC). [claim:clm_048]
Volumetric IoU is approximated by sampling 100,000 points in the union of the bounding boxes of the ground-truth and reconstructed interior volumes and taking the intersection over union of occupied space. [claim:clm_049]
The symmetric Chamfer distance is approximated by sampling 100,000 points each on the ground-truth and reconstructed meshes, then averaging bidirectional nearest-neighbor (minimum) Euclidean distances between the two point sets. [claim:clm_050]
The benchmark is built from 6,085 crochet patterns across 55 project categories scraped from Yarnspirations, parsed via a GPT-4o-mini conversion pipeline into JSON with over 98% image coverage. [claim:clm_026]
Four tasks use distinct metrics: Stitch Recognition (precision/recall/F1), Instruction Selection (4-way MCQ accuracy), Instruction Generation (BLEU/ROUGE-L/ChrF), and DSL Translation (Valid Pattern Rate = proportion of DSL steps that compile, plus DINO similarity). [claim:clm_027]
Performance collapses on executable tasks: even the strongest models produce only 5-8% executable DSL programs, exposing the gap between surface similarity and executable correctness. [claim:clm_028]

**Inference:** CrochetBench (2025) is reusable as a complexity-stratification and model-baseline reference but NOT as a drop-in mesh-to-pattern scoring harness, because its four tasks score text/DSL generation from descriptions (F1, BLEU, Valid Pattern Rate, DINO) and contain no target-mesh-vs-output geometric metric; the inverse-generator benchmark must therefore be built fresh on the B4 20-50 primitive set, borrowing only its DSL-compilation validity gate. [claim:clm_inf06]

**Inference:** CrochetPARADE is the recommended self-hostable execution backend for the benchmark's crochetability/validity gate because it parses, correctness-checks, and renders any supplied pattern fully client-side under GPLv3, giving a compile-or-fail Valid-Pattern-Rate-style signal and a 3D render for round-trip silhouette scoring with no server dependency or licensing cost. [claim:clm_inf07]

### Reuse-vs-build decision (judged on evidence)

| Asset | Reuse or build | Why | Evidence |
|-------|----------------|-----|----------|
| Geometric triad (CD/IoU/NC) | Reuse | Reproducible point-sampled protocol transfers directly to scoring a generated surface | [claim:clm_inf01] |
| CrochetBench tasks/dataset | Reuse as reference only | Tasks score describing-to-doing on scraped patterns, no mesh-distance metric | [claim:clm_inf06] |
| CrochetPARADE compile/render | Reuse as validity-gate backend | Client-side GPLv3 compile-or-fail plus 3D render, no server or license cost | [claim:clm_inf07] |
| Mesh set on B4 20-50 primitives | Build fresh | No existing target-mesh-vs-output harness for inverse generation | [claim:clm_inf06] |

### Protocol bands

Each generated pattern that compiles in CrochetPARADE passes the validity gate, since the tool parses a user-provided pattern, checks it for correctness, builds a virtual model, and renders it in 3D, so compilation itself acts as the validity gate. [claim:clm_033]

**Speculation:** The highest-leverage prototype to de-risk gate G4 is a round-trip evaluator (EXP-010): generate a pattern from each B4 primitive mesh, compile it in CrochetPARADE to a 3D render, and score that render against the (stuffing-deformed) target with the CD+IoU+NC triad; this single harness simultaneously exercises the mesh-to-pattern primitive, the validity gate, and the shape-fidelity metric set, and is likely the cheapest path to a defensible go/no-go on the inverse generator. [claim:clm_spec01]

## Edit-loop control matrix

CrochetPARADE's analyzer/debug step identifies overly loose or tight stitches and lets users swap them for more suitable ones before crocheting, acting as a stitch-tension quality proxy. [claim:clm_034]
In the user study with experienced designers, the linear editing workflow and shape/3D preview made previously hidden chart ambiguities apparent, supporting validator-gated, construction-time edit loops over free-form symbol placement. [claim:clm_046]
The editor can check crochetability of the resulting pattern before committing an edit (e.g., inserting a sub-pattern), so stitch requirements are guaranteed by construction — a concrete validator-gated edit loop. [claim:clm_047]
Crochetability is enforced as an edge-ordering invariant: an edge whose loop uses insertion points created by a later edge is invalid, because a stitch cannot be worked into a loop before that loop exists. [claim:clm_042]
Creases are reproduced via BLO/FLO stitches applied automatically in areas of high maximal absolute curvature whose curvature direction is orthogonal to the crocheting direction. [claim:clm_057]
The mean curvature of the surface at crease lines determines which stitch types are used, so the pattern better adheres to the input shape. [claim:clm_054]

**Inference:** Among the proposed edit-loop controls, only validator-gated structural edits (region inflate/deflate, redistribute increases, piece split, symmetry enforcement) have positive evidence of measurably improving shape match or crochetability; seam/split-line placement is automatic in AmiGo (geodesic saddles) so exposing it as a user knob is a speculative addition, and any control must re-run the crochetability invariant or it risks producing uncrochetable graphs. [claim:clm_inf08]

### Control-to-evidence matrix

| User control | Maps to evidenced operation | Measurably helps? | Evidence |
|--------------|-----------------------------|-------------------|----------|
| Region inflate/deflate | Curvature-driven inflating/sampling; fewer stitches in saddle regions | Positive evidence (shape adherence) | [claim:clm_056] |
| Redistribute increases | Curvature/mean-curvature-driven inc/dec and crease stitch choice | Positive evidence (shape adherence) | [claim:clm_054] |
| Piece split | Auto-segmentation into join-as-you-go components | Positive evidence (crochetability, no sewing) | [claim:clm_004] |
| Symmetry enforcement | Validator-gated construction-time edit, crochetability checked before commit | Positive evidence (guaranteed by construction) | [claim:clm_047] |
| Seam/split-line placement | Automatic at geodesic saddle points | Speculative as a user knob (already automatic) | [claim:clm_inf08] |
| Any edit | Must re-run edge-ordering invariant or output is uncrochetable | Required guard, not an improvement | [claim:clm_042] |

## IR alignment

Rows and rounds are unified into a single concept called 'layers', stored as a per-node layer-number property, so a pattern can switch between row- and round-wise crochet without structural change. [claim:clm_044]
A crochet pattern is modeled as a directed graph whose nodes are stitches/insertion points and whose edges encode the 'previous', 'insertion', and slip-stitch relations between them, directly representing fabric structure rather than a linear stitch sequence. [claim:clm_040]
The language deliberately encodes the structure of the pattern (and its inter-stitch dependencies) rather than a producing sequence, giving an unambiguous, machine-readable intermediate representation. [claim:clm_041]

**Inference:** The metric set and edit controls should operate on the Crochet IR v0.1 representation directly: shape role (increase/straight/decrease/closure) on each round maps to AmiGo's curvature-driven inc/dec decisions, expected_stitch_count is the per-layer complexity metric, and assembly[] is the piece/seam-count metric - so a single IR instance feeds both the generator and its evaluator rather than a divergent model. [claim:clm_inf09]

### IR-field mapping

| IR field | Generator role | Evaluator role | Evidence |
|---------------|-----------------------------------|-----------------------------------|----------|
| pieces[].rounds[].index (layer) | Geodesic isoline / row, unified rows+rounds | Per-layer scoring unit | [claim:clm_044] |
| rounds[].ops (sc/inc/dec) | Curvature-derived inc(x)/dec(x) over sc | Increase/decrease-rate crochetability metric | [claim:clm_011] |
| rounds[].expected_stitch_count | Stitches assigned per row from coupling | Per-layer complexity metric + variance | [claim:clm_045] |
| rounds[].visual_hint.shape_role | increase/straight/decrease/closure from curvature | Curvature-adaptive density check | [claim:clm_056] |
| assembly[] | Join-as-you-go segments | Piece/seam-count crochetability metric | [claim:clm_004] |

## Academic feasibility vs product readiness

**Inference:** A genuine contradiction exists between AmiGo's qualitative-only success criterion ('the result will be similar to M', no numeric metric) and this run's evaluation goal of a numeric shape-fidelity score; the resolution is that AmiGo proves academic feasibility of generation but provides zero quantitative evaluation, so the geometric triad must be imported from the reconstruction-benchmark lineage - a high-impact decision because without it the generator has no automated regression test. [claim:clm_inf10]

Across all tasks, performance sharply decreases as evaluation shifts from surface-level similarity to executable correctness, revealing limits in long-range symbolic reasoning and 3D-aware procedural synthesis (DINO visual similarity uniformly low at 0.10-0.17). [claim:clm_030]
Best Task A stitch-recognition F1 was Claude Sonnet 4 at 60.94%, while best Task C instruction-generation BLEU was Gemini 2.5 Flash-Lite at only 4.93%. [claim:clm_029]

### Feasibility-vs-readiness matrix

| Capability conclusion | Academic feasibility | Product readiness gap (still unproven for product) | Evidence |
|-----------------------|----------------------|----------------------------------------------------|----------|
| Mesh-to-pattern generation | Shown: AmiGo generates crochetable patterns from a mesh | No numeric fidelity metric, no automated regression test | [claim:clm_008] |
| Shape-fidelity scoring | Shown in reconstruction benchmark, not on amigurumi | Soft-result/stuffing deformation adaptation untested | [claim:clm_inf02] |
| Executable-correctness from models | Shown: only 5-8% executable DSL programs | Far below a product reliability bar | [claim:clm_028] |
| DSL validity/render gate | Shown: CrochetPARADE compiles, validates, renders | Not yet wired to a mesh-target geometric score | [claim:clm_033] |

## Contradictions & open disagreements

**Inference:** A genuine contradiction exists between AmiGo's qualitative-only success criterion ('the result will be similar to M', no numeric metric) and this run's evaluation goal of a numeric shape-fidelity score; the resolution is that AmiGo proves academic feasibility of generation but provides zero quantitative evaluation, so the geometric triad must be imported from the reconstruction-benchmark lineage - a high-impact decision because without it the generator has no automated regression test. [claim:clm_inf10]

**Inference:** Among the proposed edit-loop controls, only validator-gated structural edits (region inflate/deflate, redistribute increases, piece split, symmetry enforcement) have positive evidence of measurably improving shape match or crochetability; seam/split-line placement is automatic in AmiGo (geodesic saddles) so exposing it as a user knob is a speculative addition, and any control must re-run the crochetability invariant or it risks producing uncrochetable graphs. [claim:clm_inf08]

## Risks

**Speculation:** Without a curvature/symmetry-aware explainability layer, the inverse generator carries a HIGH-severity, MEDIUM-likelihood UX-trust risk that users distrust opaque inc/dec placement and abandon edits; the concrete mitigation is to surface per-round rationale ('this round decreases because mean curvature is saddle-like here') drawn from AmiGo's curvature signals and CrochetBench's evidence that even strong models produce only 5-8% executable patterns, underscoring how often outputs will be wrong and need explained, user-correctable edits. [claim:clm_spec02]

**Inference:** Because the deliverable is a stuffed soft object rather than a rigid mesh, shape-fidelity scoring should compare against a stuffing-deformed proxy of the target (or apply tolerance bands of at least one stitch-width w) rather than the raw input mesh, since AmiGo itself only guarantees the stuffed result is 'similar' under the assumption that all edge lengths equal the stitch width w. [claim:clm_inf02]

### Risk register

| Risk | Severity | Likelihood | Mitigation | Evidence |
|------|----------|------------|------------|----------|
| Opaque inc/dec placement erodes UX trust | High | Medium | Surface per-round curvature rationale | [claim:clm_spec02] |
| Scoring rigid mesh penalizes soft/stuffed result | Medium | High | Score against stuffing-deformed proxy / stitch-width tolerance band | [claim:clm_inf02] |
| No numeric metric means no regression test | High | High | Import CD+IoU+NC triad from reconstruction benchmark | [claim:clm_inf10] |
| Low model executable-correctness yields broken patterns | High | High | Gate every output through CrochetPARADE compile-or-fail | [claim:clm_028] |

## Prototype experiments & decision-gate relevance

This section maps findings to gates G1-G5 and the named prototype-experiment backlog.

The website and all of its computational components are open source under GPLv3, making the validator/renderer freely reusable. [claim:clm_038]
CrochetPARADE runs fully client-side, performing all calculations locally with no data sent to a central server, which makes it usable as a self-hostable scoring backend. [claim:clm_037]
Export outputs include an auto-generated chart using standard crochet symbols, an SVG that labels each stitch by type, row number, and in-row position, and 3D files importable into Blender. [claim:clm_035]
The interactive 3D view supports rotate, zoom, and pan plus an animation of the pattern-creation process to visualize how stitches attach. [claim:clm_036]
The author anticipates the grammar plus renderer enabling AI to learn to write correct crochet instructions for complicated patterns beyond simple amigurumi. [claim:clm_039]
The paper explicitly identifies AmiGo (Edelstein, Peleg, Itzhaki, Ben-Chen; Symposium on Computational Fabrication, Seattle, Oct 2022) as the fuller treatment and lineage for inverse amigurumi generation. [claim:clm_058]
The authors call for standardization of crochet instructions to enable interoperability between computational crochet tools, relevant to evaluation-protocol portability. [claim:clm_059]
CrochetPARADE provides a custom language grammar for defining stitches and stitch patterns whose explicit aim is to remove the ambiguities of plain-English crochet instructions. [claim:clm_032]

**Speculation:** The highest-leverage prototype to de-risk gate G4 is a round-trip evaluator (EXP-010): generate a pattern from each B4 primitive mesh, compile it in CrochetPARADE to a 3D render, and score that render against the (stuffing-deformed) target with the CD+IoU+NC triad; this single harness simultaneously exercises the mesh-to-pattern primitive, the validity gate, and the shape-fidelity metric set, and is likely the cheapest path to a defensible go/no-go on the inverse generator. [claim:clm_spec01]

### Gate-to-experiment matrix

| Gate | What this run de-risks | Most-relevant prototype experiment | Evidence |
|------|------------------------|-------------------------------------|----------|
| G1 Evidence quality | Geometric triad and crochetability metrics are source-backed | n/a (synthesis gate) | [claim:clm_inf01] |
| G2 Crochet-IR viability | Metrics read IR fields directly, single shared representation | EXP-001/EXP-002 IR hello-world + stitch-count validator | [claim:clm_inf09] |
| G3 pattern-to-3D viability | CrochetPARADE renders a pattern to 3D for silhouette scoring | EXP-005 stitch-graph to approximate-3D | [claim:clm_inf07] |
| G4 mesh-to-pattern primitive | Round-trip evaluator scores generated pattern vs target | EXP-010 round-trip mesh generator | [claim:clm_spec01] |
| G5 MVP recommendation | Crochetability thresholds + soft-result tolerance define pass bands | EXP-009 mesh-generated pattern to IR | [claim:clm_inf04] |

## Recommendations & decision rules

**Inference:** The recommended shape-fidelity metric set for an inverse amigurumi generator is symmetric Chamfer distance plus volumetric IoU plus normal consistency (the Sulzer-benchmark triad), because it jointly captures point-wise geometric error, occupied-volume overlap, and surface-orientation agreement, and AmiGo currently ships none of these despite explicitly targeting 'similarity' to the input mesh. [claim:clm_inf01]

**Inference:** Normal-guided Chamfer Distance (NCD) is the preferred curvature/normal-aware fidelity term over a plain CD-plus-normal-consistency combination for an iterative edit loop, because NCD folds orientation sensitivity into a single distance at negligible added compute and uses cheap mesh-sampled normals, making it viable to re-score after every edit without the efficiency penalty of a separate NC term. [claim:clm_inf03]

**Inference:** CrochetPARADE is the recommended self-hostable execution backend for the benchmark's crochetability/validity gate because it parses, correctness-checks, and renders any supplied pattern fully client-side under GPLv3, giving a compile-or-fail Valid-Pattern-Rate-style signal and a 3D render for round-trip silhouette scoring with no server dependency or licensing cost. [claim:clm_inf07]

**Inference:** The metric set and edit controls should operate on the Crochet IR v0.1 representation directly: shape role (increase/straight/decrease/closure) on each round maps to AmiGo's curvature-driven inc/dec decisions, expected_stitch_count is the per-layer complexity metric, and assembly[] is the piece/seam-count metric - so a single IR instance feeds both the generator and its evaluator rather than a divergent model. [claim:clm_inf09]

## Open questions

- What numeric Chamfer/IoU/NC band on a stuffing-deformed proxy should count as a 'pass' for an amigurumi-first product?
- What per-round increase/decrease rate is the empirical human-executable cap, given no source publishes one?
- Does a CrochetPARADE 3D render correlate well enough with the physical stuffed result to serve as the scoring surface?
- Should seam/split-line placement remain fully automatic, or is there user demand for a manual override despite the speculative crochetability cost?

## Sources

- src_20260614_kw007_01: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw007_00: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw007_03: A Survey and Benchmark of Automatic Surface Reconstruction from Point Clouds
- src_20260614_kw007_04: NCD: Normal-Guided Chamfer Distance Loss for Watertight Mesh Reconstruction from Unoriented Point Clouds
- src_20260614_kw007_06: CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260614_kw007_08: CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger)
- src_20260614_kw007_05: Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260614_kw007_02: A Survey and Benchmark of Automatic Surface Reconstruction from Point Clouds
- src_20260614_kw007_07: Amigurumi Crochet Patterns from Geodesic Distances
