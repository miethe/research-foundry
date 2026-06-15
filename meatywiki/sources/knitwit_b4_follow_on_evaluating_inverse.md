---
id: mwb_20260614_knitwit_b4_follow_on_evaluating_inverse
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_is_the
target_page: meatywiki/sources/knitwit_b4_follow_on_evaluating_inverse.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_is_the_right_evaluation_protocol:
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
  - src_20260614_kw007_00
  - src_20260614_kw007_01
  - src_20260614_kw007_02
  - src_20260614_kw007_03
  - src_20260614_kw007_04
  - src_20260614_kw007_05
  - src_20260614_kw007_06
  - src_20260614_kw007_07
  - src_20260614_kw007_08
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# KnitWit B4 Follow-on: Evaluating Inverse Amigurumi Generators - Shape-Fidelity Metrics, Pattern-Complexity Benchmarks, and the Evidence-Backed Edit Loop

## Summary

Source note distilled from research run rf_run_20260614_what_is_the_right_evaluation_protocol: 59 supported claim(s) across 9 source card(s).

## Key claims

- AmiGo generates crochet instructions (patterns) from an input 3D model, focusing specifically on Amigurumi (knitted stuffed toys). [claim:clm_001]
- Input to the method is a closed triangle mesh plus a single user-specified point, and the output, when knitted and stuffed, yields a toy similar to the input geometry. [claim:clm_002]
- The core artifact is a 'Crochet Graph' encoding geometry and connectivity that is then translated into a human-readable crochet pattern. [claim:clm_003]
- The shape is automatically segmented into crochetable components joined via the join-as-you-go method, eliminating any additional sewing. [claim:clm_004]
- The authors claim applicability to a large variety of shapes and geometries yielding 'easily crochetable' patterns, but state no numeric fidelity score in the abstract. [claim:clm_005]
- The paper is an 11-page, 10-figure work published at SCF 2022, submitted 2 Nov 2022, classified under Graphics (cs.GR). [claim:clm_006]
- The input is a closed manifold triangle mesh plus a single user-specified seed vertex and a user-selected stitch width; seed placement is an interactive control with no automatic selection provided. [claim:clm_007]
- Success is judged only qualitatively, with the paper stating the result will be 'similar' to the input mesh and reporting no Hausdorff/Chamfer/volume distance metric. [claim:clm_008]
- The shape is auto-segmented at the saddle points of a geodesic distance function from the seed, and isolines of that geodesic distance become the crochet rows. [claim:clm_009]
- Segments are joined with the 'join-as-you-go' method, where each segment is crocheted onto the last row of the previous one, requiring no sewing and leaving seams invisible. [claim:clm_010]
- The stitch vocabulary is single crochet (sc) plus increase inc(x) and decrease dec(x) stitches whose x counts are derived from row-to-row vertex coupling/degree, with no explicit per-round bound on increases or decreases stated. [claim:clm_011]
- Reported complexity: the Teddy hi-res model is 60 rows / 6 segments / 3,670 stitches in 2.5 min and Moomoo is 60 rows / 8 segments / 2,491 stitches in 6.9 min, with all runtimes between 0.2 and 6.9 min on an Intel Core i7 desktop. [claim:clm_012]
- The benchmark evaluates reconstructed surfaces against ground truth using three geometric metrics: volumetric IoU, symmetric Chamfer distance (CD), and normal consistency (NC). [claim:clm_013]
- Symmetric Chamfer distance is computed by sampling equal-size point sets on the facets of both the ground-truth mesh and the reconstructed mesh, with each set fixed at 100,000 points. [claim:clm_014]
- The symmetric Chamfer distance averages, in both directions, the squared nearest-neighbor distance from each sampled point on one mesh to the closest point on the other mesh. [claim:clm_015]
- Volumetric IoU is approximated by sampling 100,000 points in the union of the bounding boxes of the ground-truth and reconstructed volumes and computing the inside-intersection over inside-union ratio. [claim:clm_016]
- The stated evaluation goal is for the reconstructed surface to be as close as possible to the ground-truth surface in both geometry and topology, motivating the multi-metric protocol. [claim:clm_017]
- All benchmark surfaces are single-component, closed, and manifold, which lets the benchmark add topology indices (number of components, boundary edges, non-manifold edges) on top of the geometric metrics. [claim:clm_018]
- NCD adds a normal-steered weighting to Chamfer Distance based on the angle between each mesh-sampled point's normal and the vector to its corresponding input point. [claim:clm_019]
- NCD uses readily available mesh-sampled point normals to weight coordinate-based Euclidean distances, extending Chamfer Distance without requiring input-cloud normals. [claim:clm_020]
- Normal estimation on unoriented input point clouds is computationally intensive (matrix decomposition or pre-trained models), whereas mesh-sampled normals come cheaply from the cross product of mesh vertices. [claim:clm_021]
- NCD incurs only a negligible increase in computational complexity compared with plain Chamfer Distance, keeping it viable for efficiency-sensitive training/evaluation loops. [claim:clm_022]
- Used as the training loss across multiple point-to-mesh reconstruction models and initial watertight meshes on benchmark datasets, NCD outperforms state-of-the-art Chamfer Distance variants. [claim:clm_023]
- Plain Chamfer Distance can add a normal-consistency term to improve reconstruction fidelity, but only at the cost of efficiency, which is the trade-off NCD is designed to avoid. [claim:clm_024]
- CrochetBench evaluates the shift from describing to doing via fine-grained procedural reasoning, using the CrochetPARADE DSL as an intermediate representation for structural validation and execution-based functional evaluation. [claim:clm_025]
- The benchmark is built from 6,085 crochet patterns across 55 project categories scraped from Yarnspirations, parsed via a GPT-4o-mini conversion pipeline into JSON with over 98% image coverage. [claim:clm_026]
- Four tasks use distinct metrics: Stitch Recognition (precision/recall/F1), Instruction Selection (4-way MCQ accuracy), Instruction Generation (BLEU/ROUGE-L/ChrF), and DSL Translation (Valid Pattern Rate = proportion of DSL steps that compile, plus DINO similarity). [claim:clm_027]
- Performance collapses on executable tasks: even the strongest models produce only 5-8% executable DSL programs, exposing the gap between surface similarity and executable correctness. [claim:clm_028]
- Best Task A stitch-recognition F1 was Claude Sonnet 4 at 60.94%, while best Task C instruction-generation BLEU was Gemini 2.5 Flash-Lite at only 4.93%. [claim:clm_029]
- Across all tasks, performance sharply decreases as evaluation shifts from surface-level similarity to executable correctness, revealing limits in long-range symbolic reasoning and 3D-aware procedural synthesis (DINO visual similarity uniformly low at 0.10-0.17). [claim:clm_030]
- Instruction length stratifies pattern complexity by skill level, with average character counts of Beginner ~1,674, Easy ~2,761, Intermediate ~4,221, and Experienced ~7,689 - a usable proxy for complexity bins. [claim:clm_031]
- CrochetPARADE provides a custom language grammar for defining stitches and stitch patterns whose explicit aim is to remove the ambiguities of plain-English crochet instructions. [claim:clm_032]
- The tool parses a user-provided pattern, checks it for correctness, builds a virtual model, and renders it in 3D, so compilation itself acts as the validity gate. [claim:clm_033]
- CrochetPARADE's analyzer/debug step identifies overly loose or tight stitches and lets users swap them for more suitable ones before crocheting, acting as a stitch-tension quality proxy. [claim:clm_034]
- Export outputs include an auto-generated chart using standard crochet symbols, an SVG that labels each stitch by type, row number, and in-row position, and 3D files importable into Blender. [claim:clm_035]
- The interactive 3D view supports rotate, zoom, and pan plus an animation of the pattern-creation process to visualize how stitches attach. [claim:clm_036]
- CrochetPARADE runs fully client-side, performing all calculations locally with no data sent to a central server, which makes it usable as a self-hostable scoring backend. [claim:clm_037]
- The website and all of its computational components are open source under GPLv3, making the validator/renderer freely reusable. [claim:clm_038]
- The author anticipates the grammar plus renderer enabling AI to learn to write correct crochet instructions for complicated patterns beyond simple amigurumi. [claim:clm_039]
- A crochet pattern is modeled as a directed graph whose nodes are stitches/insertion points and whose edges encode the 'previous', 'insertion', and slip-stitch relations between them, directly representing fabric structure rather than a linear stitch sequence. [claim:clm_040]
- The language deliberately encodes the structure of the pattern (and its inter-stitch dependencies) rather than a producing sequence, giving an unambiguous, machine-readable intermediate representation. [claim:clm_041]
- Crochetability is enforced as an edge-ordering invariant: an edge whose loop uses insertion points created by a later edge is invalid, because a stitch cannot be worked into a loop before that loop exists. [claim:clm_042]
- Increases are encoded as multiple incoming insert edges and decreases as multiple outgoing insert edges, giving a concrete graph-structural signature for shaping operations. [claim:clm_043]
- Rows and rounds are unified into a single concept called 'layers', stored as a per-node layer-number property, so a pattern can switch between row- and round-wise crochet without structural change. [claim:clm_044]
- User feedback surfaced the need for per-layer complexity overviews — specifically a count of stitches per layer and clear layer-number marking — supporting layer as the natural unit for complexity metrics. [claim:clm_045]
- In the user study with experienced designers, the linear editing workflow and shape/3D preview made previously hidden chart ambiguities apparent, supporting validator-gated, construction-time edit loops over free-form symbol placement. [claim:clm_046]
- The editor can check crochetability of the resulting pattern before committing an edit (e.g., inserting a sub-pattern), so stitch requirements are guaranteed by construction — a concrete validator-gated edit loop. [claim:clm_047]
- The benchmark evaluates reconstruction geometry with three geometric metrics: volumetric intersection-over-union (IoU), symmetric Chamfer distance (CD), and normal consistency (NC). [claim:clm_048]
- Volumetric IoU is approximated by sampling 100,000 points in the union of the bounding boxes of the ground-truth and reconstructed interior volumes and taking the intersection over union of occupied space. [claim:clm_049]
- The symmetric Chamfer distance is approximated by sampling 100,000 points each on the ground-truth and reconstructed meshes, then averaging bidirectional nearest-neighbor (minimum) Euclidean distances between the two point sets. [claim:clm_050]
- Normal consistency is estimated as the mean of scalar products between the unit normal at each sampled point and the unit normal at its nearest-neighbor point on the other mesh, averaged bidirectionally. [claim:clm_051]
- Beyond geometric accuracy the benchmark reports topologic quality indices: number of components, number of boundary edges (edges in only one facet), and number of non-manifold edges, since target surfaces are single-component, closed, and manifold. [claim:clm_052]
- The method computes geodesic distance on the surface from a seed point, then samples the equidistant curves non-uniformly, guided by surface curvature, framing amigurumi shaping as a geodesic-distance problem. [claim:clm_053]
- The mean curvature of the surface at crease lines determines which stitch types are used, so the pattern better adheres to the input shape. [claim:clm_054]
- Because amigurumi are crocheted in the round at constant row height, each stitch in a row is equidistant from the start point, making geodesic distance the natural model for crochet rows. [claim:clm_055]
- In saddle-like regions (negative Gaussian and mean curvature) the algorithm adapts row sampling to use fewer stitches, directly supporting curvature-bounded stitch-density / inc-dec thresholds. [claim:clm_056]
- Creases are reproduced via BLO/FLO stitches applied automatically in areas of high maximal absolute curvature whose curvature direction is orthogonal to the crocheting direction. [claim:clm_057]
- The paper explicitly identifies AmiGo (Edelstein, Peleg, Itzhaki, Ben-Chen; Symposium on Computational Fabrication, Seattle, Oct 2022) as the fuller treatment and lineage for inverse amigurumi generation. [claim:clm_058]
- The authors call for standardization of crochet instructions to enable interoperability between computational crochet tools, relevant to evaluation-protocol portability. [claim:clm_059]

## Sources

- src_20260614_kw007_00 — AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw007_01 — AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw007_02 — A Survey and Benchmark of Automatic Surface Reconstruction from Point Clouds
- src_20260614_kw007_03 — A Survey and Benchmark of Automatic Surface Reconstruction from Point Clouds
- src_20260614_kw007_04 — NCD: Normal-Guided Chamfer Distance Loss for Watertight Mesh Reconstruction from Unoriented Point Clouds
- src_20260614_kw007_05 — Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260614_kw007_06 — CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260614_kw007_07 — Amigurumi Crochet Patterns from Geodesic Distances
- src_20260614_kw007_08 — CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger)

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
