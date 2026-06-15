---
schema_version: '0.1'
type: research_report
report_id: report_20260614_for_turning_a_structured_crochet_ir
title: 'Forward Engine Bake-Off: Selecting an Accurate-Enough, Mobile-Feasible Crochet-IR-to-3D Embedding for KnitWit'
intent_id: intent_research_20260614_for_turning_a_structured_crochet_ir
evidence_bundle_id: pending
created_at: '2026-06-14T21:20:07-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Executive summary

The forward problem for KnitWit is turning a structured Crochet IR into an interactive 3D preview on a mid-range phone at roughly 30-60 FPS with limited memory, where early versions prioritize accurate shape and topology over photorealistic yarn physics. [claim:clm_046]
The KnitWit plan names three forward (pattern->3D) candidate approaches to evaluate: stitch-graph + procedural embedding, surface reconstruction from rounds, and a hybrid that decouples topology truth from rendering. [claim:clm_043]
**Inference:** Across the surveyed forward approaches, the real division is not "deterministic procedural" versus "force-directed" as two clean families but a topology-vs-embedding distinction, because every approach that uses force-directed/spring relaxation is iterative and non-deterministic while the stitch-graph layer can be built deterministically by parsing. [claim:clm_inf01]
**Inference:** The recommended KnitWit v1 baseline is deterministic procedural stitch placement (parse Crochet IR -> stitch graph -> closed-form per-stitch coordinates via frame propagation around each round), because it is the only family that simultaneously satisfies exact topology/inc-dec fidelity, trivial per-round/per-stitch highlight mapping, and an O(stitches) generation cost that makes the <2s-generate target reachable where force-directed methods provably are not. [claim:clm_inf04]
**Inference:** The runner-up, force-directed relaxation, wins only as a bounded optional refinement pass and not as the primary embedder, applied locally on flagged high-curvature rounds with an iteration ceiling tuned per stitch budget. [claim:clm_inf05]
**Inference:** Pure surface-reconstruction-from-rounds is the weakest forward family for KnitWit v1 on topological correctness and highlight mapping, and is at best a rendering enhancement on top of an authoritative graph rather than the baseline. [claim:clm_inf08]
**Inference:** The smallest credible forward-engine prototype is a five-module pipeline aligned to Crochet IR v0.1, buildable by one engineer because every module maps to an existing documented mechanism. [claim:clm_inf12]

## Approaches under comparison

The 'Procedural Geometry via Pattern IR' family parses a formal pattern (DSL/IR) into a stitch graph and then deterministically computes 3D coordinates for each stitch based on stitch types and connections, building the object row by row. [claim:clm_014]
Greer & Mould convert pattern instructions into a stitch graph and use a force-directed spring layout to position stitches in 3D, treating yarn like connecting springs to approximate the shape without full yarn physics (a simulation-lite alternative). [claim:clm_020]
The crochet-language prototype editor renders patterns in 3D using a force-directed graph library (Three.js/WebGL with a D3 physics engine) so the spatial layout of stitches is computed automatically as an approximation of the crocheted shape. [claim:clm_054]
AmiGo's pipeline segments the input mesh into crochetable components, orders them and chooses a seed start point, then constructs a Crochet Graph that is translated into human-readable instructions, placing increases at positive curvature and decreases at negative curvature. [claim:clm_019]
A crochet pattern can also be represented as a stitch mesh: a library of tiles where each tile contains yarn geometry and tiles connect along their edges. [claim:clm_063]
Curvy reconstructs a shape point cloud from planar sparse cross-sections using generative modeling and a Graph Neural Network, designed to reduce dependence on the number of cross-sections supplied. [claim:clm_007]

### Head-to-head comparison matrix

| Approach | Geometric fidelity | Topological correctness | Mobile compute cost | Highlight mapping | Evidence |
|----------|-------------------|------------------------|---------------------|---------------------------|----------|
| Deterministic procedural (CrochetPARADE-style) | Reproduces the pattern exactly as the author intended; flags loose/tight stitches as a fidelity proxy | Guarantees fidelity to every increase/decrease because structure is retained | Not optimized for mobile; thousands of stitches can take minutes | Easy to highlight specific rows or stitches | [claim:clm_022] |
| Deterministic procedural (tension/fidelity feedback) | Colors stitches blue when too loose and red when too stretched by more than ~15% relative to baseline height | Per-stitch tension feedback is computed against pattern structure | Per-stitch comparison is local arithmetic | Pressing 's' provides per-stitch tension/fidelity feedback | [claim:clm_029] |
| Force-directed (Greer & Mould spring layout) | Resulting 3D models reproduce shape and size but are explicitly 'similar, though not identical' to real crocheted objects | Topology recovered via relaxation, not constructed | Bunny legs (318 sts) and arms (264 sts) converged under 5s, but head (798 sts) and body (708 sts) did not converge even after well over two minutes | Per-row metadata exists in the source graph | [claim:clm_074] |
| Force-directed (CrochetPARADE placement step) | Under default settings converges only to within ~10% of requested stitch lengths | Iterative relaxation does not reproduce requested lengths exactly | Iterative; default 500 iterations and fails to converge if learning_rate set too high | Inherits the graph's per-stitch indices | [claim:clm_030] |
| Force-directed (crochet-language 3D editor) | Movement of the pattern made it difficult for users to orient themselves; a stable layout algorithm is framed as an open problem | Force-based layouting used as a heuristic | Layout instability is the main usability complaint | Live 3D visualization praised but unstable | [claim:clm_058] |
| Hybrid topology+surface (graph language) | Topology carried exactly as graph properties independent of any 3D embedding | Increases/decreases encoded purely by edge multiplicity | Topology operations are graph property reads | Layer number stored as a property on each node | [claim:clm_052] |
| Stitch-mesh (fidelity/perf reference) | Simulated fabric became 'lacy' with larger holes and less detailed shaping where stitch density dropped | Only chain, slip, sc, sc2tog, sc3tog modeled; tile set far from complete | Generated from 3D models via the Narayanan et al. 2019 pipeline | Stitch-level identity tied to tile faces | [claim:clm_069] |
| Surface reconstruction (Curvy) | Reconstructs a shape point cloud designed to reduce dependence on cross-section count | Trained on ShapeNet to generalize shape, not stitch identity | Three-step learned pipeline (cross-sections, autoencoder, GNN/GAN) | Point cloud discards index-to-vertex correspondence | [claim:clm_007] |

### Cross-cutting evidence on each comparison axis

**Geometric fidelity.** Because the model retains pattern structure, procedural-IR rendering guarantees fidelity to every increase/decrease and makes it easy to highlight specific rows or stitches. [claim:clm_015]
Without physics, geometry can distort under extreme curvature, but CrochetPARADE mitigates this by flagging overly loose or tight stitches. [claim:clm_016]
The Greer & Mould force-directed models reproduce shape and size but are explicitly 'similar, though not identical' to the real-world crocheted objects. [claim:clm_072]
The ad-hoc yarn-relaxation/simulation approach produces visible artifacts such as dense stitches and large gaps, and the stitch-mesh generation yields small holes and non-ideal shaping. [claim:clm_070]

**Topological correctness.** In the AmiGo formulation the method builds a Crochet Graph G=(S, R u C) whose vertices S are the tops/bases of stitches, separating row edges (R) from column edges (C) as the structured intermediate representation. [claim:clm_036]
The graph language models a crochet fabric as a directed graph in which stitches are nodes and edges encode the structural relations (previous, insertion, slip-stitch) between insertion points, providing an explicit IR for arbitrary topologies. [claim:clm_049]
Increases and decreases are encoded purely by edge multiplicity: an increase is several stitches sharing one insertion target (multiple incoming insertion edges), and a decrease is a node with more than one outgoing insertion edge. [claim:clm_051]
The language enforces a valid-sequence (crochetability) constraint requiring a yarn track from the initial node such that no step works into an insertion point that is only created later in the pattern. [claim:clm_053]
**Inference:** On topological correctness the pattern-IR/stitch-graph family is strictly superior because topology is constructed by parsing rather than recovered from geometry, so topological correctness should be owned by the graph, not the embedder. [claim:clm_inf02]

**Mobile compute cost.** CrochetPARADE is not optimized for mobile and heavy patterns of thousands of stitches can take minutes to compute, a key mobile-feasibility caveat. [claim:clm_018]
CrochetPARADE placement is not closed-form: it uses iterative force-directed relaxation whose learning_rate (default 0.1) will fail to converge if set too high, and runs a default of 500 iterations. [claim:clm_028]
For the Greer & Mould layout, larger or higher-curvature patterns such as the apple took 30 seconds or more to run, versus a few seconds for small patterns. [claim:clm_075]
**Inference:** Force-directed/spring layout is disqualified as the primary real-time embedder for mobile amigurumi because its cost scales super-linearly and unpredictably with stitch count, far outside the <2s-generate budget at the spec's ~1k-5k-stitch / 30-60-round scale. [claim:clm_inf03]

**Highlight-mapping support.** Interactive features include rotate/zoom/pan of the 3D view, animating the pattern-creation process, highlighting and hiding selected stitches, changing yarn thickness and color, and hover-to-read stitch information. [claim:clm_025]
Exports include an auto-generated standard-symbol crochet chart, an SVG that shows stitch connections and identifies stitches by type/row number/position-in-row, and 3D files importable into Blender. [claim:clm_026]
Row and stitch indices are zero-based, which matters for any external tool consuming or generating CrochetPARADE coordinates. [claim:clm_033]
Rows and rounds are unified into a single concept called 'layers' with no special graph structure; the layer number is stored as a property on each node, so a pattern can switch between row- and round-wise work at any point. [claim:clm_052]
**Inference:** Highlight-mapping correctness is essentially free in the procedural/graph family and fragile in the geometry-recovery families, because per-round and per-stitch indices are properties carried on graph nodes whereas surface-reconstruction discards the index-to-vertex correspondence and would have to re-establish it. [claim:clm_inf07]

## Analytical derivation: why deterministic procedural is the baseline

**Inference:** The deterministic family is the only one that owns topology by construction, and topology is exactly what the success criteria reward. [claim:clm_inf02]
The grammar encodes increases and decreases compactly: sc2inc means two single-crochet stitches into the same stitch, while sc2tog is a decrease combining two single-crochet stitches. [claim:clm_032]
Attachment direction is governed by even/odd turn counting: an even count attaches the next stitch in the direction the prior row was crocheted, while an odd count attaches to the previous stitch (reverse order). [claim:clm_031]
**Inference:** Twisting/orientation drift when walking stitches around a round is a solved problem with two cheap deterministic options KnitWit can adopt directly: CrochetPARADE's even/odd turn-count attachment rule gives a local closed-form next-stitch direction, while AmiGo's column-ordering optimization is the principled but heavier frame-propagation analogue, so v1 should use turn-parity frame propagation and reserve the tangent-field solve for cases where drift accumulates. [claim:clm_inf09]
In AmiGo's geometry, rows (rounds) are defined as isolines of a geodesic distance field f(v)=d(v,s) measured from the seed vertex s, so stitch placement follows level-sets of geodesic distance. [claim:clm_039]
Twist/orientation is solved by a column-ordering function g obtained from an optimization whose objective minimizes the integral of |<J grad f, grad g> - 1|^2, aligning column progression with the isoline tangent field. [claim:clm_040]
The convergence ceiling of the force-directed alternative is documented: the bunny legs (318 stitches) and arms (264 stitches) converged in under 5 seconds, but the head (798 stitches) and body (708 stitches) did not converge even after well over two minutes. [claim:clm_074]
The directed-graph crochet language carries topology decoupled from any embedding, since rows and rounds are unified into one concept (layers) carried as a node property and increases/decreases are multiple incoming versus multiple outgoing insertion edges. [claim:clm_060]
**Inference:** The hybrid 'topology as truth, surface as render' decoupling named in the KnitWit plan is the correct long-term architecture and is directly evidenced as feasible, so KnitWit can keep the stitch graph authoritative for highlight/validation while swapping the visual layer without re-deriving topology. [claim:clm_inf06]
**Inference:** Gauge/yarn-weight/hook-size should be modeled as a pure post-topology affine scale and per-stitch dimension transform, not a re-derivation, so the preview updates in O(stitches) without re-running placement. [claim:clm_inf10]
**Inference:** Cheap live feasibility/constraint signals are available without physics by reusing the procedural family's existing per-stitch tension model, all computable per-frame during preview. [claim:clm_inf11]

## Recommendation and decision rules

**Inference:** Adopt deterministic procedural stitch placement as the KnitWit v1 forward baseline, because it is the only family that simultaneously hits exact topology/inc-dec fidelity, trivial per-round/per-stitch highlight mapping, and an O(stitches) generation cost that reaches the <2s-generate target where force-directed methods provably cannot. [claim:clm_inf04]
**Inference:** The decision rule for the runner-up is 'procedural for placement; capped force-directed only on flagged high-curvature rounds, with an iteration ceiling tuned per stitch budget', so force-directed relaxation wins only as a bounded refinement pass rather than as the primary embedder. [claim:clm_inf05]
**Inference:** Do not select pure surface-reconstruction-from-rounds as the baseline, though contour-lofting between consecutive rounds is a cheap deterministic way to add a smoothed skin once the graph fixes stitch positions. [claim:clm_inf08]
The plan directs treating the 3D preview as structural geometry first (graph/mesh) rather than yarn physics, and adopting at least one structured Crochet IR rather than relying on arbitrary PDF parsing. [claim:clm_047]
The plan flags the 'PDF importer trap': full-generality pattern parsing is treated as a quagmire, so early ingestion should be restricted to structured authoring/import templates. [claim:clm_048]

## Prototype contract: the smallest forward engine one engineer can build

The forward prototype contract is defined as taking a Crochet IR as input and producing an OBJ/GLTF mesh plus per-round indices for highlighting. [claim:clm_044]
The grammar supports stitch multipliers (a number before a stitch) and bracket repetition (a number before [...]), e.g. '3[2sc,inc]' repeats '2 single crochet stitches followed by an increase' three times. [claim:clm_002]
**Inference:** The smallest credible forward-engine prototype is a five-module pipeline aligned to Crochet IR v0.1 - (M1) IR validator + repeat expansion, (M2) IR->stitch-graph builder, (M3) deterministic embedder (magic-ring seed, turn-parity frame propagation, per-round radius from stitch count), (M4) mesh emitter to OBJ/GLTF plus a per-round and per-stitch index map, (M5) row-highlight exporter - buildable by one engineer because every module maps to an existing documented mechanism. [claim:clm_inf12]

### Module-to-IR mapping

| Module | Crochet IR fields consumed | Output | Mechanism evidence |
|--------|--------------------------------|--------|--------------------|
| M1 IR validator + repeat expansion | pieces[].rounds[].ops with op:repeat; expected_stitch_count | Expanded explicit op list, count assertion | [claim:clm_002] |
| M2 IR->stitch-graph builder | ops enum (mr/sc/inc/dec/...); rounds[].index as layer | Stitch graph with layer per node, inc/dec as edge multiplicity | [claim:clm_051] |
| M2 layer indexing | rounds[].index | Layer number stored per node | [claim:clm_052] |
| M3 deterministic embedder | construction (round/spiral); ops sequence | Per-stitch coordinates via turn-parity attachment | [claim:clm_031] |
| M4 mesh emitter | yarn diameter_mm; gauge | OBJ/GLTF mesh plus per-round and per-stitch index map | [claim:clm_044] |
| M4 export format precedent | n/a (format choice) | GLTF/SVG exports are an established output | [claim:clm_017] |
| M5 row-highlight exporter | rounds[].index, visual_hint.shape_role | Per-round highlight groups read from the index map | [claim:clm_026] |

## Benchmark protocol

The forward engine is to be evaluated against three benchmark metrics: time per pattern, mesh stability (no avoidable self-intersections), and row-highlighting mapping correctness. [claim:clm_045]
The pattern input grammar is one row per line, the first line must be 'mc' (magic circle), valid stitches are 'sc', 'inc', and 'dec', and 'fo' at the end represents sewing the final row closed. [claim:clm_001]
**Inference:** The benchmark protocol should bind three pass thresholds to a reference pattern set of escalating stitch budgets (a magic-ring ball at rounds 6-12-18 of ~150-300 stitches, an egg, and a multi-piece toy of ~1k-2k stitches across 30-60 rounds): (T1 generation time) cold IR->mesh < 2s on a mid-range phone-class CPU with a stretch target of incremental edits < 100ms; (T2 mesh stability) zero broken loops and zero avoidable self-intersections, asserted by checking every round has expected_stitch_count nodes and every adjacent-round edge exists; (T3 highlight correctness) 100% of per-round index-map entries resolve to the correct rendered stitch set, verified by round-trip selecting round k and asserting node membership. [claim:clm_inf13]
**Inference:** Mesh-stability is best validated topologically rather than geometrically for the procedural baseline: a broken loop is detectable as a missing adjacent-round edge or a stitch-count mismatch (an O(stitches) graph check), whereas self-intersection is the one purely-geometric failure mode that should trigger a capped force-directed relax. [claim:clm_inf14]

### Metric-to-measurement table

| Metric | Pass threshold | Measured on | Evidence |
|--------|----------------|-------------|----------|
| T1 generation time | Cold IR->mesh < 2s on mid-range phone CPU; incremental edits < 100ms | ball 6-12-18 (~150-300 sts), egg, multi-piece toy (~1k-2k sts) | [claim:clm_inf13] |
| T2 mesh stability | Zero broken loops; zero avoidable self-intersections | Every round has expected_stitch_count nodes; every adjacent-round edge exists | [claim:clm_inf14] |
| T2 budget reference | Force-directed exceeds budget by 1-2 orders at ~700+ sts | Greer & Mould head/body non-convergence past 2 min | [claim:clm_074] |
| T3 highlight correctness | 100% of per-round index-map entries resolve to the correct rendered stitch set | Round-trip select round k, assert node membership | [claim:clm_inf13] |
| Mobile FPS envelope | Smooth interactive 3D at roughly 30-60 FPS with limited memory | Mid-range phone target from the spec assumptions | [claim:clm_046] |

## Force-directed convergence and stability risk

For the Greer & Mould layout, convergence has a hard ceiling by node count: the bunny legs (318 stitches) and arms (264 stitches) converged in under 5 seconds, but the head (798 stitches) and body (708 stitches) did not converge even after well over two minutes. [claim:clm_074]
Larger or higher-curvature patterns such as the apple took 30 seconds or more to run, versus a few seconds for small patterns. [claim:clm_075]
The layout is solved as a non-linear least-squares minimization combining an edge-length energy E_L (each edge target length 1) and a Laplacian curvature energy as (1-lambda)*E_L + lambda*C, using a static lambda=0.65 for all pieces except the bunny head and body where lambda=0.9, via the Ceres Solver library. [claim:clm_073]
The authors note that convergence is often unnecessary - iterating beyond a point made no noticeable difference - and propose raising the convergence threshold and letting users trade visual quality against run-time. [claim:clm_076]
The proposed real-time workflow runs the Ceres solver for a small number of iterations after each edit (and can target only the changed region, since Ceres allows stopping/restarting without re-setup) to give the designer near-instant feedback. [claim:clm_077]
A core limitation is that least-squares can only minimize cost, so the authors minimize curvature as a proxy for the incompatible goal of maximizing volume, yielding a sub-maximal volume. [claim:clm_078]
The method was validated only on beginner-level, stuffed, single-crochet-like amigurumi; flat/2D row pieces were excluded, and the authors caution the two metrics (edge length, curvature) may not be sufficient and that a one-size-fits-all layout is unlikely. [claim:clm_079]
The crochet-language editor independently corroborates the instability: movement of the pattern caused by the force-based layout made it difficult for users to orient themselves, and the authors state a stable layout algorithm for 2D/3D crochet visualization is desirable, framing it as an open problem. [claim:clm_058]
Designers expressed amazement at the live 3D visualization while editing, but the prototype suffered from force-layout instability and rotation of the chart as the main usability complaints. [claim:clm_061]
**Inference:** Force-directed is therefore neither a baseline nor a non-starter but a bounded refinement step, applied with a capped iteration ceiling only on flagged high-curvature rounds. [claim:clm_inf05]

## Academic feasibility vs product readiness

The CrochetPARADE engine deterministically parses and correctness-checks any user-provided pattern, then builds and 3D-renders a virtual model that reproduces the pattern exactly as the author intended - a shipped, usable tool. [claim:clm_022]
A think-aloud user study with six professional crochet designers found the language removes ambiguities present in standard chart notation, and most designers reacted positively to the 3D view for judging shape (e.g., comparing proportions of amigurumi parts) - academically validated for usefulness. [claim:clm_055]
The directed-graph crochet language removes ambiguities observed in current standard crochet notations, but the work is a prototype illustrating potential features rather than a released tool - academic feasibility, not product readiness. [claim:clm_062]
AmiGo assumes a smooth, genus-0 closed mesh and notes 'curvature obstructions to crochetability' where extremely sharp features cannot be captured with continuous stitching - a research-scoped precondition not yet a product guarantee. [claim:clm_021]
The stitch-mesh tile set is explicitly incomplete: only the chain stitch, slip stitch, single crochet, sc2tog, and sc3tog were modeled, with double/treble crochet left as future work - a research demo, not product coverage. [claim:clm_067]
The Greer & Mould 3D models reproduce shape and size but are explicitly 'similar, though not identical' to the real-world crocheted objects, so the academic result stops short of a product fidelity guarantee. [claim:clm_072]
**Inference:** A genuine contradiction exists on whether force-directed layout is viable for interactive use, and the resolution is that force-directed is academically demonstrated yet not product-ready for real-time mobile, a high-decision-impact finding that flips the baseline to deterministic procedural. [claim:clm_inf15]
**Speculation:** Speculation: because no surveyed source reports a quantitative geometric-fidelity metric (Hausdorff/volumetric error) for any forward crochet method, KnitWit will be unable to rank approaches on silhouette/volume error from the literature and should instead adopt round-trip visual-similarity scoring as its own fidelity metric, accepting that v1's fidelity claim rests on internal benchmarks rather than published evidence. [claim:clm_spec02]

## Contradictions & open disagreements

The KnitWit B1 seed frames Greer & Mould's spring layout as a usable 'simulation-lite' approximation that treats yarn like connecting springs to approximate the shape without full yarn physics. [claim:clm_020]
The primary Greer & Mould paper instead documents non-convergence beyond ~700 stitches, with the head (798 stitches) and body (708 stitches) failing to converge even after well over two minutes. [claim:clm_074]
The crochet-language study reports force-layout instability and chart rotation as the top usability complaint, independently weakening the 'usable approximation' framing. [claim:clm_061]
**Inference:** The contradiction over whether force-directed layout is viable for interactive use resolves against using it as the baseline, because the primary evidence (non-convergence, instability) outweighs the B1 seed's favorable framing, a high-decision-impact finding. [claim:clm_inf15]
**Speculation:** Speculation: a second latent disagreement is on geometric fidelity numbers, where the literature offers only 'similar, though not identical' qualitative claims and ~10% length accuracy rather than Hausdorff/volumetric metrics, so KnitWit cannot resolve a fidelity ranking from published evidence and must measure it internally. [claim:clm_spec02]

## Implications

Because the model retains pattern structure, procedural-IR rendering guarantees fidelity to every increase/decrease and makes it easy to highlight specific rows or stitches - the technical implication that owns the highlight success criterion. [claim:clm_015]
The mobile constraint requires interactive 3D to run smoothly on mid-range phones at roughly 30-60 FPS with limited memory, with early versions prioritizing accurate shape/topology over photorealistic yarn physics - the product implication that sets the acceptance bar. [claim:clm_046]
**Inference:** The product implication of the baseline choice is that gauge/yarn-weight/color edits become O(stitches) affine transforms that update the preview without re-deriving topology, satisfying the 'update without re-deriving topology' requirement. [claim:clm_inf10]
**Inference:** The technical implication is that live feasibility/constraint signals (loose/tight flags, excessive-curvature warnings) are available without physics by reusing the procedural family's existing per-stitch tension model, all computable per-frame. [claim:clm_inf11]
**Inference:** The architectural implication is that the hybrid topology-truth/render decoupling lets KnitWit swap the visual layer (instanced stitch glyphs now, smoothed lofted surface later) without re-deriving topology. [claim:clm_inf06]

## Risks

CrochetPARADE is open-source (GPL v3) with all computation client-side, its grammar is public domain, and it exports standard crochet charts (SVG) and 3D models (GLTF). [claim:clm_017]
The website and all of its computational components are free and open source under the GPLv3 license, a copyleft constraint for reuse in a closed-source product. [claim:clm_027]
**Inference:** IP/legal risk - GPLv3 licensing makes CrochetPARADE a study/reference asset rather than a drop-in dependency for a closed-source mobile product; this is a medium-severity risk whose mitigation is to adopt the documented algorithms (turn-parity attachment, 15%-threshold tension flags, GLTF export) as a clean-room re-implementation against the Crochet IR. [claim:clm_inf16]
**Inference:** Mobile performance risk - force-directed/spring layout is disqualified as the primary real-time embedder because its cost scales super-linearly and unpredictably with stitch count, a high-severity, high-likelihood failure mode mitigated by selecting deterministic procedural placement as the baseline. [claim:clm_inf03]
**Inference:** Generation-crochetability/fidelity risk - the stitch-graph family owns topological correctness by construction, so the mitigation for broken-loop and inc/dec errors is to make topology a parsed graph property checked as an O(stitches) graph assertion rather than recovered from geometry. [claim:clm_inf02]
Without physics, geometry can distort under extreme curvature, but CrochetPARADE mitigates this by flagging overly loose or tight stitches. [claim:clm_016]
**Speculation:** Speculation: model-accuracy risk - a deterministic turn-parity embedder will hold the <2s-generate budget for amigurumi up to roughly 3k-5k stitches on a mid-range phone where force-directed cannot, with the residual risk being purely local self-intersection on extreme-curvature transitions resolvable by a capped (<=50-iteration) region-local relax, but this projected envelope is unmeasured and must be confirmed by the EXP-005/EXP-012 mobile-rendering benchmark before it is treated as fact. [claim:clm_spec01]

### Risk register summary

| Risk | Category | Severity | Likelihood | Mitigation | Evidence |
|------|----------|----------|------------|------------|----------|
| GPLv3 copyleft blocks reuse of CrochetPARADE code | legal/IP | medium | high | Clean-room re-implementation of documented algorithms against the Crochet IR | [claim:clm_inf16] |
| Force-directed cost scales super-linearly past the mobile budget | performance | high | high | Select deterministic procedural placement as baseline | [claim:clm_inf03] |
| Geometry distorts under extreme curvature without physics | technical | medium | medium | Capped region-local force-directed relax on flagged rounds | [claim:clm_inf05] |
| No published quantitative fidelity metric to rank against | model/data | medium | high | Adopt internal round-trip visual-similarity scoring | [claim:clm_spec02] |
| Deterministic envelope (3k-5k sts < 2s) is unmeasured | performance | medium | medium | Confirm via EXP-005/EXP-012 mobile benchmark before treating as fact | [claim:clm_spec01] |

## Prototype experiments & decision-gate relevance

**Inference:** The findings most directly de-risk decision gates G2 (Crochet-IR viability) and G3 (pattern->3D viability) and recommend proving EXP-004 (IR->stitch-graph) and EXP-005 (stitch-graph->approximate-3D via deterministic turn-parity embedding) before ever invoking a force solver, because topology and highlighting are achievable deterministically and only EXP-005's self-intersection cases on high-curvature shapes need a separate force-refinement spike. [claim:clm_inf17]
**Inference:** The five-module prototype maps directly onto the EXP-001..EXP-006 backlog (IR hello-world, stitch-count validator, repeat expansion, IR->stitch-graph, stitch-graph->approximate-3D, row-highlight export), so a single engineer can build it because every module maps to an existing documented mechanism. [claim:clm_inf12]
**Inference:** The benchmark thresholds (T1 time, T2 mesh stability, T3 highlight correctness) operationalize the G3 pass conditions on the reference pattern set, binding gate decisions to measurable outcomes. [claim:clm_inf13]
**Inference:** Mesh-stability is split into a cheap topological G3 check (every round has expected_stitch_count nodes, every adjacent-round edge exists) plus a curvature-triggered geometric fix, so most of G3 passes deterministically. [claim:clm_inf14]
**Speculation:** Speculation: the deterministic mobile-performance envelope that would clear G5 (MVP recommendation) remains unmeasured and must be confirmed by the EXP-005/EXP-012 mobile-rendering benchmark before the MVP claim is treated as fact. [claim:clm_spec01]

### Gate-to-experiment mapping

| Gate | What the evidence establishes | Next experiment | Evidence |
|------|-------------------------------|-----------------------------|----------|
| G2 Crochet-IR viability | IR->stitch-graph build is deterministic; inc/dec are edge multiplicity | EXP-004 IR->stitch-graph | [claim:clm_inf17] |
| G3 pattern->3D viability | Topology + highlighting achievable without a force solver | EXP-005 stitch-graph->approximate-3D | [claim:clm_inf17] |
| G3 mesh stability | Broken loops detectable as a topological graph check | EXP-005 self-intersection spike + capped relax | [claim:clm_inf14] |
| G3 highlight correctness | Per-round index map is a direct read-off the graph | EXP-006 row-highlight export | [claim:clm_inf07] |
| G5 MVP recommendation | Deterministic envelope is projected, not measured | EXP-012 mobile rendering feasibility | [claim:clm_spec01] |

## Open questions

- What is the measured cold IR->mesh generation time for the deterministic embedder on a ~1k-2k-stitch multi-piece toy on a representative mid-range phone?
- At what stitch budget, if any, does local self-intersection on extreme-curvature transitions actually appear, and does a <=50-iteration region-local relax clear it within the 2s budget?
- Which round-trip visual-similarity scoring scheme should serve as KnitWit's internal fidelity metric in the absence of published Hausdorff/volumetric numbers?
- Does turn-parity frame propagation alone control orientation drift on joined-round amigurumi, or is AmiGo's tangent-field column solve needed for longer pieces?

## Sources

- src_20260614_kw004_05: modeling-amigurumi (EnbyMonkey) — Connectivity Shapes amigurumi modeler
- src_20260614_kw004_11: Curvy: A Parametric Cross-section based Surface Reconstruction
- src_20260614_kw004_08: KnitWit B1 Workstream Report - Prior Art & Taxonomy
- src_20260614_kw004_02: CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger) repository
- src_20260614_kw004_03: CrochetPARADE Manual (Crochet PAttern Renderer, Analyzer, and DEbugger)
- src_20260614_kw004_06: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw004_09: KnitWit Research Plan (local project seed)
- src_20260614_kw004_07: Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260614_kw004_01: Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260614_kw004_10: Representing Crochet with Stitch Meshes
- src_20260614_kw004_00: Modeling crochet patterns with a force-directed graph layout
- src_20260614_kw004_04: CrochetPARADE: Crochet PAttern Renderer, Analyzer and DEbugger
