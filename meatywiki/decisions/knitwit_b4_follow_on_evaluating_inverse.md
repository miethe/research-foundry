---
id: mwb_20260622_dr_knitwit_b4_follow_on_evaluating
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_is_the
target_page: meatywiki/decisions/knitwit_b4_follow_on_evaluating_inverse.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_what_is_the_right_evaluation_protocol: AmiGo reports
  no Hausdorff/Chamfer/volume metric (clm_008) so the gap is real; the surface-reconstruction benchmark
  defi'
key_claims:
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf10
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_008
  - clm_013
  - clm_048
  - clm_050
  - clm_051
  - clm_049
  - clm_011
  - clm_012
  - clm_045
  - clm_043
  - clm_004
  - clm_033
  - clm_037
  - clm_038
  - clm_035
  - clm_028
  - clm_044
  - clm_056
  - clm_002
  - clm_005
  - clm_007
  - clm_019
  - clm_022
  - clm_021
  - clm_024
  - clm_023
  - clm_031
  - clm_025
  - clm_027
  - clm_047
  - clm_046
  - clm_042
  - clm_009
  - clm_053
  - clm_017
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: KnitWit B4 Follow-on: Evaluating Inverse Amigurumi Generators - Shape-Fidelity Metrics, Pattern-Complexity Benchmarks, and the Evidence-Backed Edit Loop

## Context

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

## Decision

The recommended shape-fidelity metric set for an inverse amigurumi generator is symmetric Chamfer distance plus volumetric IoU plus normal consistency (the Sulzer-benchmark triad), because it jointly captures point-wise geometric error, occupied-volume overlap, and surface-orientation agreement, and AmiGo currently ships none of these despite explicitly targeting 'similarity' to the input mesh. [claim:clm_inf01]

## Rationale

- AmiGo reports no Hausdorff/Chamfer/volume metric (clm_008) so the gap is real; the surface-reconstruction benchmark defines a reproducible, point-sampled CD+IoU+NC triad (clm_013/048/049/050/051) that is directly transferable to scoring a generated-pattern surface against a target mesh. [claim:clm_inf01]
- AmiGo derives inc(x)/dec(x) from row coupling (clm_011) and reports per-model row/segment/stitch totals (clm_012); designers requested per-layer stitch counts (clm_045); increases/decreases have a graph signature (clm_043) and segmentation defines piece/seam count (clm_004) - these are exactly the IR fields rounds[].ops, expected_stitch_count, and assembly[]. [claim:clm_inf04]
- CrochetPARADE compiles+validates+renders 3D (clm_033), runs fully client-side (clm_037) under GPLv3 (clm_038) and exports charts/SVG/3D (clm_035); CrochetBench already treats DSL compilation as the executable-correctness gate (clm_028) - so CrochetPARADE can serve as the local compile/render backend. [claim:clm_inf07]
- AmiGo's sc/inc/dec vocabulary (clm_011) and curvature-driven shaping (clm_056) align with the IR op enum and visual_hint.shape_role; the layer abstraction unifying rows/rounds (clm_044) matches IR rounds[].index; per-layer stitch counts (clm_045) match expected_stitch_count; join-as-you-go segments (clm_004) match assembly[]. [claim:clm_inf09]
- AmiGo's similarity guarantee is conditioned on uniform edge length w and is asserted against the rigid input, not a deformed simulation (clm_002/005/008); fidelity scoring is only fair if tolerance is scaled to the discretization unit (the user-selected stitch width w, clm_007), otherwise quantization and stuffing deformation are penalized as shape error. [claim:clm_inf02]
- NCD weights CD by normal angle (clm_019) at negligible extra cost (clm_022) using cheap mesh-sampled normals (clm_021) and outperforms CD variants (clm_023), whereas adding a separate NC term to CD improves fidelity only at an efficiency cost (clm_024) - so for a per-edit re-scoring loop NCD dominates. [claim:clm_inf03]
- AmiGo states no explicit per-round inc/dec bound (clm_011); the only quantitative complexity stratifier in evidence is CrochetBench's length-by-skill bands (clm_031); curvature-adaptive sampling that uses fewer stitches in saddle regions (clm_056) implies inc/dec rate is geometry-driven, not a fixed published constant - so thresholds are inference, not measured. [claim:clm_inf05]
- CrochetBench's IR is CrochetPARADE and its tasks measure describing-to-doing on scraped patterns (clm_025/027/028) with no mesh-distance metric; the only geometric protocol comes from the reconstruction benchmark (clm_013) - so reuse is partial: borrow the executable-validity idea, build the geometric scoring separately. [claim:clm_inf06]
- Digital Crochet shows construction-time crochetability checking before committing an edit (clm_047/046) enforcing an edge-ordering invariant (clm_042); AmiGo derives segmentation and inflate/redistribute automatically from geodesic distance and curvature (clm_009/053/056) - so inflate/redistribute map to evidenced geometry operations, but seam placement is automatic, making a manual seam knob speculative. [claim:clm_inf08]
- AmiGo asserts applicability/similarity with no numeric fidelity score (clm_005/008) while the benchmark literature defines an explicit geometry+topology scoring goal (clm_013/017); the two are reconciled by treating AmiGo as the generation method and the benchmark as the (missing) evaluation layer. [claim:clm_inf10]

## Consequences

- A defensible three-metric crochetability set is (1) max increase/decrease rate per round, (2) stitch-count per layer/round (and its round-to-round variance), and (3) piece/segment count, all computable directly from the Crochet IR rounds[].ops and assembly[] without external tooling; AmiGo's own outputs (60 rounds, 6-8 segments, 2.5k-3.7k stitches) supply a concrete worked-example envelope for these metrics. [claim:clm_inf04]
- CrochetPARADE is the recommended self-hostable execution backend for the benchmark's crochetability/validity gate because it parses, correctness-checks, and renders any supplied pattern fully client-side under GPLv3, giving a compile-or-fail Valid-Pattern-Rate-style signal and a 3D render for round-trip silhouette scoring with no server dependency or licensing cost. [claim:clm_inf07]
- The metric set and edit controls should operate on the Crochet IR v0.1 representation directly: shape role (increase/straight/decrease/closure) on each round maps to AmiGo's curvature-driven inc/dec decisions, expected_stitch_count is the per-layer complexity metric, and assembly[] is the piece/seam-count metric - so a single IR instance feeds both the generator and its evaluator rather than a divergent model. [claim:clm_inf09]
- Because the deliverable is a stuffed soft object rather than a rigid mesh, shape-fidelity scoring should compare against a stuffing-deformed proxy of the target (or apply tolerance bands of at least one stitch-width w) rather than the raw input mesh, since AmiGo itself only guarantees the stuffed result is 'similar' under the assumption that all edge lengths equal the stitch width w. [claim:clm_inf02]
- Normal-guided Chamfer Distance (NCD) is the preferred curvature/normal-aware fidelity term over a plain CD-plus-normal-consistency combination for an iterative edit loop, because NCD folds orientation sensitivity into a single distance at negligible added compute and uses cheap mesh-sampled normals, making it viable to re-score after every edit without the efficiency penalty of a separate NC term. [claim:clm_inf03]
- No source supplies a published numeric threshold separating 'human-executable' from 'too brittle', so any inc/dec-rate cap must be labeled defensible inference; the strongest evidence-backed proxy is CrochetBench's instruction-length skill bands (Beginner ~1,674 to Experienced ~7,689 chars), which can be repurposed to bin generated-pattern complexity by stitch/round count rather than inventing an unsupported per-round bound. [claim:clm_inf05]
- CrochetBench (2025) is reusable as a complexity-stratification and model-baseline reference but NOT as a drop-in mesh-to-pattern scoring harness, because its four tasks score text/DSL generation from descriptions (F1, BLEU, Valid Pattern Rate, DINO) and contain no target-mesh-vs-output geometric metric; the inverse-generator benchmark must therefore be built fresh on the B4 20-50 primitive set, borrowing only its DSL-compilation validity gate. [claim:clm_inf06]
- Among the proposed edit-loop controls, only validator-gated structural edits (region inflate/deflate, redistribute increases, piece split, symmetry enforcement) have positive evidence of measurably improving shape match or crochetability; seam/split-line placement is automatic in AmiGo (geodesic saddles) so exposing it as a user knob is a speculative addition, and any control must re-run the crochetability invariant or it risks producing uncrochetable graphs. [claim:clm_inf08]
- A genuine contradiction exists between AmiGo's qualitative-only success criterion ('the result will be similar to M', no numeric metric) and this run's evaluation goal of a numeric shape-fidelity score; the resolution is that AmiGo proves academic feasibility of generation but provides zero quantitative evaluation, so the geometric triad must be imported from the reconstruction-benchmark lineage - a high-impact decision because without it the generator has no automated regression test. [claim:clm_inf10]

## Links

- [[claim:clm_008]]
- [[claim:clm_013]]
- [[claim:clm_048]]
- [[claim:clm_050]]
- [[claim:clm_051]]
- [[claim:clm_049]]
- [[claim:clm_011]]
- [[claim:clm_012]]
- [[claim:clm_045]]
- [[claim:clm_043]]
- [[claim:clm_004]]
- [[claim:clm_033]]
- [[claim:clm_037]]
- [[claim:clm_038]]
- [[claim:clm_035]]
- [[claim:clm_028]]
- [[claim:clm_044]]
- [[claim:clm_056]]
- [[claim:clm_002]]
- [[claim:clm_005]]
- [[claim:clm_007]]
- [[claim:clm_019]]
- [[claim:clm_022]]
- [[claim:clm_021]]
- [[claim:clm_024]]
- [[claim:clm_023]]
- [[claim:clm_031]]
- [[claim:clm_025]]
- [[claim:clm_027]]
- [[claim:clm_047]]
- [[claim:clm_046]]
- [[claim:clm_042]]
- [[claim:clm_009]]
- [[claim:clm_053]]
- [[claim:clm_017]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
