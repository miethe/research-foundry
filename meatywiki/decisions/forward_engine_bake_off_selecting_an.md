---
id: mwb_20260622_dr_forward_engine_bake_off_selecting
evidence_bundle_id: bundle_20260614_intent_research_20260614_for_turning_a
target_page: meatywiki/decisions/forward_engine_bake_off_selecting_an.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_for_turning_a_structured_crochet_ir: clm_014 defines
  the deterministic embedding; clm_015/clm_025 give it the fidelity+highlight properties the success crite'
key_claims:
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf17
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf14
  include: true
- claim_id: clm_inf15
  include: true
- claim_id: clm_inf16
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_014
  - clm_015
  - clm_025
  - clm_031
  - clm_074
  - clm_046
  - clm_076
  - clm_077
  - clm_016
  - clm_073
  - clm_007
  - clm_013
  - clm_069
  - clm_inf07
  - clm_044
  - clm_002
  - clm_051
  - clm_052
  - clm_017
  - clm_045
  - clm_001
  - clm_047
  - clm_043
  - clm_058
  - clm_inf04
  - clm_020
  - clm_028
  - clm_054
  - clm_036
  - clm_071
  - clm_070
  - clm_075
  - clm_018
  - clm_049
  - clm_059
  - clm_033
  - clm_040
  - clm_039
  - clm_083
  - clm_037
  - clm_029
  - clm_082
  - clm_030
  - clm_021
  - clm_061
  - clm_005
  - clm_027
  - clm_085
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Forward Engine Bake-Off: Selecting an Accurate-Enough, Mobile-Feasible Crochet-IR-to-3D Embedding for KnitWit

## Context

- The pattern input grammar is one row per line, the first line must be 'mc' (magic circle), valid stitches are 'sc', 'inc', and 'dec', and 'fo' at the end represents sewing the final row closed. [claim:clm_001]
- The grammar supports stitch multipliers (a number before a stitch) and bracket repetition (a number before [...]), e.g. '3[2sc,inc]' repeats '2 single crochet stitches followed by an increase' three times. [claim:clm_002]
- The project is C++ (about 98% of the codebase), built with CMake >= 3.15, and depends on Eigen3 and Ceres Solver (with SuiteSparse required for Ceres Solver to work properly). [claim:clm_003]
- The tool embeds the stitch graph in 3D using the 'Connectivity Shapes' force-directed graph layout. [claim:clm_004]
- The author states the graph layout does not work well for small patterns and is quite slow for larger patterns — a direct feasibility caveat for real-time or mobile use. [claim:clm_005]
- The tool does not support joining patterns (a standard amigurumi technique for attaching limbs), bounding which amigurumi it can model. [claim:clm_006]
- Curvy reconstructs a shape point cloud from planar sparse cross-sections using generative modeling and a Graph Neural Network, designed to reduce dependence on the number of cross-sections supplied. [claim:clm_007]
- Each cross-section piece is encoded as a tensor in R^6x3 holding the coefficients of a degree-5 parametric polynomial f_j(t) in R^3. [claim:clm_008]
- Cross-sections are split adaptively via iterated Douglas-Peucker, retaining the k points with maximum absolute angle so high-curvature regions get denser sampling. [claim:clm_009]
- The representation is permutation-invariant: any reordering of cross-sections, and any circular permutation of a cross-section's pieces, denotes the same input. [claim:clm_010]
- Models are trained on ShapeNet manifold meshes, from which surface point clouds are sampled to serve as the network's ground truth. [claim:clm_011]
- The method is a three-step pipeline: generate cross-sections from 3D models, train a point-cloud autoencoder, then train a GNN in a GAN setting to match the autoencoder's encoded vector and decode to points. [claim:clm_012]
- The authors position learned contour reconstruction against classical methods, which they say lack object-class generalization and rely on complex mathematical machinery. [claim:clm_013]
- The 'Procedural Geometry via Pattern IR' family parses a formal pattern (DSL/IR) into a stitch graph and then deterministically computes 3D coordinates for each stitch based on stitch types and connections, building the object row by row. [claim:clm_014]
- Because the model retains pattern structure, procedural-IR rendering guarantees fidelity to every increase/decrease and makes it easy to highlight specific rows or stitches. [claim:clm_015]
- Without physics, geometry can distort under extreme curvature, but CrochetPARADE mitigates this by flagging overly loose or tight stitches. [claim:clm_016]
- CrochetPARADE is open-source (GPL v3) with all computation client-side, its grammar is public domain, and it exports standard crochet charts (SVG) and 3D models (GLTF). [claim:clm_017]
- CrochetPARADE is not optimized for mobile and heavy patterns of thousands of stitches can take minutes to compute, a key mobile-feasibility caveat. [claim:clm_018]
- AmiGo's pipeline segments the input mesh into crochetable components, orders them and chooses a seed start point, then constructs a Crochet Graph that is translated into human-readable instructions, placing increases at positive curvature and decreases at negative curvature. [claim:clm_019]
- Greer & Mould convert pattern instructions into a stitch graph and use a force-directed spring layout to position stitches in 3D, treating yarn like connecting springs to approximate the shape without full yarn physics (a simulation-lite alternative). [claim:clm_020]
- AmiGo assumes a smooth, genus-0 closed mesh and notes 'curvature obstructions to crochetability' where extremely sharp features cannot be captured with continuous stitching. [claim:clm_021]
- CrochetPARADE deterministically parses and correctness-checks any user-provided pattern, then builds and 3D-renders a virtual model that reproduces the pattern exactly as the author intended. [claim:clm_022]
- Shared CrochetPARADE pattern text renders into a model of the pattern exactly as intended by the pattern author, free from ambiguities or typographic mistakes. [claim:clm_023]
- All calculation runs locally on-device with no server transmission; as a side effect the platform can be sluggish on old hardware, and models of patterns with (tens of) thousands of stitches can take minutes or more to calculate. [claim:clm_024]
- Interactive features include rotate/zoom/pan of the 3D view, animating the pattern-creation process, highlighting and hiding selected stitches, changing yarn thickness and color, and hover-to-read stitch information. [claim:clm_025]
- Exports include an auto-generated standard-symbol crochet chart, an SVG that shows stitch connections and identifies stitches by type/row number/position-in-row, and 3D files importable into Blender. [claim:clm_026]
- The website and all of its computational components are free and open source under the GPLv3 license, a copyleft constraint for reuse in a closed-source product. [claim:clm_027]
- CrochetPARADE placement is not closed-form: it uses iterative force-directed relaxation whose learning_rate (default 0.1) will fail to converge if set too high, and runs a default of 500 iterations. [claim:clm_028]
- Pressing 's' colors stitches blue when too loose and red when too stretched by more than about 15% relative to their baseline height, providing per-stitch tension/fidelity feedback. [claim:clm_029]
- Under default settings the placement engine only converges to within ~10% of the requested stitch lengths, so it does not reproduce requested lengths exactly. [claim:clm_030]
- Attachment direction is governed by even/odd turn counting: an even count attaches the next stitch in the direction the prior row was crocheted, while an odd count attaches to the previous stitch (reverse order). [claim:clm_031]
- The grammar encodes increases and decreases compactly: sc2inc means two single-crochet stitches into the same stitch, while sc2tog is a decrease combining two single-crochet stitches. [claim:clm_032]
- Row and stitch indices are zero-based, which matters for any external tool consuming or generating CrochetPARADE coordinates. [claim:clm_033]
- CrochetPARADE runs entirely client-side with no server data collection, and large patterns of tens of thousands of stitches can take minutes or more to compute and may be sluggish on old hardware. [claim:clm_034]
- AmiGo generates crochet patterns from a closed triangle mesh plus a single user-specified seed point, producing instructions that when knitted and stuffed yield a toy resembling the input geometry. [claim:clm_035]
- The method builds a Crochet Graph G=(S, R u C) whose vertices S are the tops/bases of stitches, separating row edges (R) from column edges (C) as the structured intermediate representation. [claim:clm_036]
- The stitch vocabulary is limited to single crochet (sc) as an approximately square stitch, with increase inc(x) and decrease dec(x) stitches that locally add or remove x stitches to accommodate curvature. [claim:clm_037]
- The generated instructions are crochetable, use only simple crochet stitches, and follow the join-as-you-go method so the resulting pattern requires no sewing. [claim:clm_038]
- Rows (rounds) are defined as isolines of a geodesic distance field f(v)=d(v,s) measured from the seed vertex s, so stitch placement follows level-sets of geodesic distance. [claim:clm_039]
- Twist/orientation is solved by a column-ordering function g obtained from an optimization whose objective minimizes the integral of |<J grad f, grad g> - 1|^2, aligning column progression with the isoline tangent field. [claim:clm_040]
- Consecutive rows must satisfy a coupling relation (Definition 2.2) that constrains how stitch correspondences change between rows; a minimal coupling between each pair of consecutive rows is computed via Dynamic Time Warping (DTW). [claim:clm_041]
- Curvature obstructs direct crochetability: crater regions are preprocessed with localized Conformal Mean Curvature Flow until mean curvature is positive, and negative-Gaussian-curvature regions are handled by curvature-adaptive sampling that sets the inner product of grad g and J grad f to a function of curvature. [claim:clm_042]
- The plan names three forward (pattern->3D) candidate approaches to evaluate: stitch-graph + procedural embedding, surface reconstruction from rounds, and a hybrid that decouples topology truth from rendering. [claim:clm_043]
- The forward prototype contract is defined as taking a Crochet IR as input and producing an OBJ/GLTF mesh plus per-round indices for highlighting. [claim:clm_044]
- The forward engine is to be evaluated against three benchmark metrics: time per pattern, mesh stability (no avoidable self-intersections), and row-highlighting mapping correctness. [claim:clm_045]
- The mobile constraint requires interactive 3D to run smoothly on mid-range phones at roughly 30-60 FPS with limited memory, with early versions prioritizing accurate shape/topology over photorealistic yarn physics. [claim:clm_046]
- The plan directs treating the 3D preview as structural geometry first (graph/mesh) rather than yarn physics, and adopting at least one structured Crochet IR rather than relying on arbitrary PDF parsing. [claim:clm_047]
- The plan flags the 'PDF importer trap': full-generality pattern parsing is treated as a quagmire, so early ingestion should be restricted to structured authoring/import templates. [claim:clm_048]
- The language models a crochet fabric as a directed graph in which stitches are nodes and edges encode the structural relations (previous, insertion, slip-stitch) between insertion points, providing an explicit IR for arbitrary topologies. [claim:clm_049]
- Each node has exactly one outgoing 'previous' edge pointing to the insertion point the yarn originates from, while 'insertion' edges point to the insertion points worked into by the current stitch, ensuring a single unambiguous yarn path. [claim:clm_050]
- Increases and decreases are encoded purely by edge multiplicity: an increase is several stitches sharing one insertion target (multiple incoming insertion edges), and a decrease is a node with more than one outgoing insertion edge. [claim:clm_051]
- Rows and rounds are unified into a single concept called 'layers' with no special graph structure; the layer number is stored as a property on each node, so a pattern can switch between row- and round-wise work at any point. [claim:clm_052]
- The language enforces a valid-sequence (crochetability) constraint requiring a yarn track from the initial node such that no step works into an insertion point that is only created later in the pattern. [claim:clm_053]
- The prototype editor renders patterns in 3D using a force-directed graph library (Three.js/WebGL with a D3 physics engine) so the spatial layout of stitches is computed automatically as an approximation of the crocheted shape. [claim:clm_054]
- A think-aloud user study with six professional crochet designers found the language removes ambiguities present in standard chart notation, and most designers reacted positively to the 3D view for judging shape (e.g., comparing proportions of amigurumi parts). [claim:clm_055]
- Both the 2D and 3D views use force-based layouting as a heuristic, and the 3D view is built on Vasco Asturiano's 3D force-directed graph library, which uses Three.js and WebGL for rendering with a variant of D3 as the physics engine. [claim:clm_056]
- The authors scope the 3D force-based layout as approximate, useful as a first approximation of a pattern's 3D appearance, whereas an exact model would require modeling the physical properties of stitches and yarn as is done for knitting. [claim:clm_057]
- Movement of the pattern caused by the force-based layout made it difficult for users to orient themselves, and the authors state a stable layout algorithm for 2D/3D crochet visualization is desirable, framing it as an open problem. [claim:clm_058]
- In the graph IR, nodes are insertion points (the connected loops), which do not correspond one-to-one to stitches; a stitch such as a slip stitch may not produce a loop that serves as an insertion point. [claim:clm_059]
- Increases and decreases are encoded structurally as multiple incoming versus multiple outgoing insertion edges on a node, and rows and rounds are unified into one concept (layers) carried as a node property, since either method depends only on where stitches continue. [claim:clm_060]
- Designers expressed amazement at the live 3D visualization while editing, but the prototype suffered from force-layout instability and rotation of the chart as the main usability complaints. [claim:clm_061]
- The language removes ambiguities observed in current standard crochet notations, but the work is a prototype illustrating potential features rather than a released tool. [claim:clm_062]
- A crochet pattern is represented as a stitch mesh: a library of tiles where each tile contains yarn geometry and tiles connect along their edges. [claim:clm_063]
- The representation introduces a special edge type capturing the 'current loop' - the loop of yarn held on the crochet hook during fabrication. [claim:clm_064]
- Crochet stitch faces use four edge labels - Next/Previous (short-term, consecutive stitches) and Future/Past (long-term, loop-through-fabric to a prior stitch) - connected as previous-next and past-future pairs to cover a surface. [claim:clm_065]
- Faces use short-term (orange) and long-term (purple) edge types; the leading loop and free yarn cross the short-term edges while long-term edges are crossed only by loops. [claim:clm_066]
- Only the chain stitch, slip stitch, single crochet, sc2tog, and sc3tog were modeled; the tile set is explicitly described as far from complete, with double/treble crochet left as future work. [claim:clm_067]
- Patterns are generated from 3D models via the Narayanan et al. 2019 pipeline, which maps quad faces to single crochet/turn, pentagons to sc2tog, and increase triangles to inc, demonstrated on a cube, sphere, and Stanford bunny. [claim:clm_068]
- Because remeshing produced lower stitch density in the bunny body than the ears, the simulated fabric became more 'lacy' with larger holes and less detailed shaping - a documented fidelity failure of the approach. [claim:clm_069]
- The ad-hoc yarn-relaxation/simulation approach produces visible artifacts such as dense stitches and large gaps, and the stitch-mesh generation yields small holes and non-ideal shaping. [claim:clm_070]
- The method translates a written amigurumi pattern into a stitch graph and applies the Isenburg et al. [IGG01] 'Connectivity Shapes' force-directed layout, where stuffing the crocheted shell is treated as inflating the graph. [claim:clm_071]
- The resulting 3D models reproduce shape and size but are explicitly 'similar, though not identical' to the real-world crocheted objects. [claim:clm_072]
- The layout is solved as a non-linear least-squares minimization combining an edge-length energy E_L (each edge target length 1) and a Laplacian curvature energy as (1-lambda)*E_L + lambda*C, using a static lambda=0.65 for all pieces except the bunny head and body where lambda=0.9, via the Ceres Solver library. [claim:clm_073]
- Convergence has a hard ceiling by node count: the bunny legs (318 stitches) and arms (264 stitches) converged in under 5 seconds, but the head (798 stitches) and body (708 stitches) did not converge even after well over two minutes. [claim:clm_074]
- Larger or higher-curvature patterns such as the apple took 30 seconds or more to run, versus a few seconds for small patterns. [claim:clm_075]
- The authors note that convergence is often unnecessary—iterating beyond a point made no noticeable difference—and propose raising the convergence threshold and letting users trade visual quality against run-time. [claim:clm_076]
- The proposed real-time workflow runs the Ceres solver for a small number of iterations after each edit (and can target only the changed region, since Ceres allows stopping/restarting without re-setup) to give the designer near-instant feedback. [claim:clm_077]
- A core limitation is that least-squares can only minimize cost, so the authors minimize curvature as a proxy for the incompatible goal of maximizing volume, yielding a sub-maximal volume. [claim:clm_078]
- The method was validated only on beginner-level, stuffed, single-crochet-like amigurumi; flat/2D row pieces were excluded, and the authors caution the two metrics (edge length, curvature) may not be sufficient and that a one-size-fits-all layout is unlikely. [claim:clm_079]
- CrochetPARADE defines stitches and stitch patterns via a custom language grammar designed to remove the ambiguity of plain-English crochet instructions. [claim:clm_080]
- The tool parses and validates any user-provided pattern for correctness before building and rendering a 3D virtual model. [claim:clm_081]
- CrochetPARADE flags overly loose or tight stitches so users can replace them before crocheting, reducing the need for blocking. [claim:clm_082]
- Interactive 3D features include rotate/zoom/pan, animating the pattern-creation process, highlighting/hiding selected stitches, and changing yarn thickness and color. [claim:clm_083]
- Projects can be exported to 3D files importable into Blender for further manipulation and visualization. [claim:clm_084]
- CrochetPARADE was authored by Svetlin Tassev (2023) and its website and computational components are free and open source under the GPLv3 license. [claim:clm_085]
- All calculations run locally on the user's device with no data sent to a central server, at the cost of slow performance on old hardware and large patterns. [claim:clm_086]

## Decision

The recommended KnitWit v1 baseline is deterministic procedural stitch placement (CrochetPARADE-style: parse Crochet IR -> stitch graph -> closed-form per-stitch coordinates via frame propagation around each round), because it is the only family that simultaneously satisfies the three acceptance gates: exact topology/inc-dec fidelity (clm_015), trivial per-round/per-stitch highlight mapping (clm_015, clm_025), and a generation cost that is O(stitches) rather than iterative-to-convergence, making the <2s-generate target reachable where force-directed methods provably are not. [claim:clm_inf04]

## Rationale

- clm_014 defines the deterministic embedding; clm_015/clm_025 give it the fidelity+highlight properties the success criteria demand; clm_031 supplies a closed-form attachment rule (even/odd turn counting) usable for frame propagation; clm_074 shows the force-directed alternative cannot meet the budget; clm_046 is the acceptance target. [claim:clm_inf04]
- clm_076 says convergence is often unnecessary and the threshold can be raised; clm_077 shows Ceres can run a few iterations on only the changed region; clm_016 says procedural geometry distorts under extreme curvature, which is exactly where a capped relax helps; together they define force-directed as a localized refinement, not the baseline. [claim:clm_inf05]
- clm_007/clm_013 show learned contour reconstruction targets shape generalization, not stitch-level identity; clm_069 shows reconstruction-style density problems produce lacy/holey shaping; combined with clm_inf07 (lost index correspondence), surface reconstruction cannot own topology or highlighting and is therefore a skin, not a baseline. [claim:clm_inf08]
- clm_044 fixes the IR-in/OBJ-GLTF+per-round-index-out contract; clm_002 (multiplier/bracket repeats) defines repeat expansion; clm_051/clm_052 define the graph build; clm_031 defines the embedder's deterministic step; clm_017 shows GLTF export is an established output, so each module is a known quantity, not research. [claim:clm_inf12]
- clm_045 names the three metrics (time, mesh stability, highlight correctness); clm_046 sets the <2s/30-60FPS budget that becomes T1; clm_044 defines the index map T3 checks; clm_074's stitch-count thresholds motivate escalating budgets; clm_001 (mc-first ball pattern) grounds the reference set. [claim:clm_inf13]
- clm_047 (structural-geometry-first, IR-first) and clm_043 (three forward candidates) define the G2/G3 scope; clm_015 shows deterministic highlighting passes G3's mapping condition; clm_058 shows force-layout instability is what G3 fails on; clm_inf04 names deterministic as baseline, so sequencing EXP-004/005 before any solver is the lowest-risk path. [claim:clm_inf17]
- clm_014/clm_036/clm_049 build an explicit deterministic stitch/insertion graph (topology truth), while clm_020/clm_028/clm_054/clm_071 all rely on force-directed relaxation for the 3D embedding; CrochetPARADE proves a tool can be deterministic at the grammar/topology layer (clm_022) yet iterative at the placement layer (clm_028), establishing the two layers are separable. [claim:clm_inf01]
- clm_015 + clm_051 show topology is exact by construction in a parsed graph (inc/dec are edge-multiplicity facts), while clm_069/clm_070 document the stitch-mesh/relaxation family losing structural fidelity (holes, lacy regions); therefore the graph layer, not the surface, is the correct authority for topology. [claim:clm_inf02]
- clm_074 shows a hard convergence ceiling between ~300 and ~700 stitches; clm_075 shows curvature worsens it (apple 30s+); clm_018/clm_028 corroborate minutes-scale cost on thousands of stitches in a second force-directed tool; clm_046 sets the <2s/30-60FPS budget that these times violate by 1-2 orders of magnitude. [claim:clm_inf03]
- clm_043 names the hybrid as a candidate; clm_049/clm_052 show the graph language stores topology (layers, insertion edges) decoupled from geometry; clm_059 warns nodes are insertion points not stitches, which is precisely the kind of mapping a topology-truth layer must own; clm_015 ties retained structure to highlight correctness, so the hybrid keeps that property while freeing the render layer. [claim:clm_inf06]
- clm_052 (layer property per node) and clm_033 (zero-based row/stitch indices) mean the index map exists for free in the graph; clm_044 requires that index map as output; clm_007 (Curvy reconstructs a point cloud from cross-sections) shows pure surface reconstruction outputs geometry without stitch identity, so highlight mapping would be lossy there. [claim:clm_inf07]
- clm_031 gives a local deterministic attachment-direction rule (frame propagation by turn parity); clm_040 gives AmiGo's tangent-field column-ordering as the principled anti-twist solve; clm_039 grounds rounds as geodesic isolines; clm_016 notes distortion under extreme curvature, the regime where the heavier solve earns its cost. [claim:clm_inf09]
- clm_025/clm_083 show CrochetPARADE already changes yarn thickness/color interactively; clm_052 (topology is graph-level, size-agnostic) and clm_037 (sc is an approximately square unit stitch) imply gauge is a scale on a fixed graph, so color/weight edits are a transform over existing nodes, not a new solve. [claim:clm_inf10]
- clm_029/clm_082 give a concrete per-stitch tension flag (15% threshold, loose/tight) that is a local arithmetic check; clm_030 shows even relaxed placement only hits ~10% of target length, so a tension flag is meaningful; clm_021 (curvature obstructions) and clm_016 (distortion under extreme curvature) supply the curvature/inc-dec-rate signal. [claim:clm_inf11]
- clm_051/clm_052 make broken-loop detection a graph-property check (missing edge or wrong layer count); clm_016 names extreme-curvature distortion as the geometric failure the deterministic method retains; clm_045 requires mesh stability as a metric, so splitting it into a cheap topological check plus a curvature-triggered geometric fix is the efficient design. [claim:clm_inf14]
- clm_020 (B1 seed) presents force-directed favorably; clm_074 (primary) shows non-convergence at scale; clm_058/clm_061 (crochet-language study) report force-layout instability and rotation as the main UX failure; clm_005 independently caveats slowness; the primary evidence outweighs the seed's framing, resolving the contradiction against force-directed as baseline. [claim:clm_inf15]
- clm_017/clm_027/clm_085 establish GPLv3 code with a public-domain grammar; clm_031/clm_029 are the algorithmic ideas (attachment rule, tension flag) that are facts/methods rather than copyrightable code, so a clean-room re-implementation is the lawful path for a closed-source product. [claim:clm_inf16]

## Consequences

- The runner-up, force-directed relaxation, wins only as a bounded optional refinement pass, not as the primary embedder: Greer & Mould's own finding that iterating past a point 'made no noticeable difference' and their incremental edit workflow (a few solver iterations on only the changed region) show a capped-iteration spring relax can be applied locally to soften procedural geometry under extreme curvature, so the decision rule is 'procedural for placement; capped force-directed only on flagged high-curvature rounds, with an iteration ceiling tuned per stitch budget'. [claim:clm_inf05]
- Pure surface-reconstruction-from-rounds (round-contour lofting, Poisson/ball-pivoting, marching-cubes, or learned methods like Curvy) is the weakest forward family for KnitWit v1 on the two criteria that matter most, topological correctness and highlight mapping, and is at best a rendering enhancement on top of an authoritative graph; it should not be the baseline, though contour-lofting between consecutive rounds is a cheap deterministic way to add a smoothed skin once the graph fixes stitch positions. [claim:clm_inf08]
- The smallest credible forward-engine prototype is a five-module pipeline aligned to Crochet IR v0.1: (M1) IR validator + repeat expansion (expand op:repeat, verify per-round expected_stitch_count); (M2) IR->stitch-graph builder (nodes=stitches/insertion points, layer index per node per clm_052, inc/dec as edge multiplicity per clm_051); (M3) deterministic embedder (magic-ring seed, turn-parity frame propagation per clm_031, per-round radius from stitch count); (M4) mesh emitter (instanced stitch glyphs to OBJ/GLTF) plus a per-round and per-stitch index map; (M5) row-highlight exporter reading the index map; buildable by one engineer because every module maps to an existing documented mechanism. [claim:clm_inf12]
- The benchmark protocol should bind three pass thresholds to a reference pattern set of escalating stitch budgets (a magic-ring ball at rounds 6-12-18 of ~150-300 stitches, an egg, and a multi-piece toy of ~1k-2k stitches across 30-60 rounds): (T1 generation time) cold IR->mesh < 2s on a mid-range phone-class CPU with a stretch target of incremental edits < 100ms; (T2 mesh stability) zero broken loops and zero avoidable self-intersections, asserted by checking every round has expected_stitch_count nodes and every adjacent-round edge exists; (T3 highlight correctness) 100% of per-round index-map entries resolve to the correct rendered stitch set, verified by round-trip selecting round k and asserting node membership. [claim:clm_inf13]
- The findings most directly de-risk decision gates G2 (Crochet-IR viability) and G3 (pattern->3D viability) and recommend a specific next-experiment ordering: prove EXP-004 (IR->stitch-graph) and EXP-005 (stitch-graph->approximate-3D via deterministic turn-parity embedding) before ever invoking a force solver, because the evidence shows topology+highlighting (the G3 pass conditions: round highlighting maps correctly, layout not unstable) are achievable deterministically, and only EXP-005's self-intersection cases on high-curvature shapes need a separate force-refinement spike. [claim:clm_inf17]
- Across the surveyed forward approaches, exactly one family is deterministic and closed-form-ish on topology: stitch-graph + procedural embedding (CrochetPARADE-style placement, the AmiGo crochet-graph, and the directed-graph crochet language); every approach that uses force-directed/spring relaxation (Greer & Mould, CrochetPARADE's own placement step, the crochet-language 3D editor) is iterative and non-deterministic, so 'deterministic procedural' and 'force-directed' are not two clean families but a topology-vs-embedding distinction. [claim:clm_inf01]
- On topological correctness (stitch-count-per-round, no broken loops, every inc/dec reflected) the pattern-IR/stitch-graph family is strictly superior because topology is constructed by parsing rather than recovered from geometry: clm_015 states procedural-IR rendering guarantees fidelity to every increase/decrease, whereas force-directed-only layouts (Greer & Mould, crochet-language editor) and surface/stitch-mesh methods can produce broken or lacy structure (e.g. the Guo 2020 bunny became 'lacy' with larger holes), so topological correctness should be owned by the graph, not the embedder. [claim:clm_inf02]
- Force-directed/spring layout is disqualified as the primary real-time embedder for mobile amigurumi because its cost scales super-linearly and unpredictably with stitch count: Greer & Mould report bunny legs/arms (264-318 stitches) converging under 5s but head/body (708-798 stitches) failing to converge after 2+ minutes, and CrochetPARADE (force-directed placement) takes minutes on thousands of stitches, both far outside the <2s-generate budget at the spec's ~1k-5k-stitch / 30-60-round scale. [claim:clm_inf03]
- The hybrid 'topology as truth, surface as render' decoupling named in the KnitWit plan is the correct long-term architecture and is directly evidenced as feasible: the directed-graph crochet language already proves topology can be carried exactly as graph properties (layers, insertion edges) independent of any 3D embedding, so KnitWit can keep the stitch graph authoritative for highlight/validation while swapping the visual layer (instanced stitch glyphs now, smoothed lofted surface later) without re-deriving topology. [claim:clm_inf06]
- Highlight-mapping correctness, a hard success criterion, is essentially free in the procedural/graph family and fragile in the geometry-recovery families: because per-round and per-stitch indices are properties carried on graph nodes (layer number on each node, zero-based row/stitch indices in CrochetPARADE), the per-round index map required by the prototype contract is a direct read-off, whereas surface-reconstruction (Curvy, Poisson/marching-cubes from points) discards the index-to-vertex correspondence and would have to re-establish it. [claim:clm_inf07]
- Twisting/orientation drift when walking stitches around a round is a solved problem with two cheap deterministic options KnitWit can adopt directly: CrochetPARADE's even/odd turn-count attachment rule gives a local closed-form next-stitch direction (spiral vs joined rounds handled by the turn parity), while AmiGo's column-ordering optimization that aligns column progression with the isoline tangent field is the principled but heavier frame-propagation analogue, so v1 should use turn-parity frame propagation and reserve the tangent-field solve for cases where drift accumulates. [claim:clm_inf09]
- Gauge/yarn-weight/hook-size should be modeled as a pure post-topology affine scale and per-stitch dimension transform, not a re-derivation: because the stitch graph and round structure are independent of physical size, recolor (yarn_id/color) and yarn-weight edits change only stitch diameter and inter-stitch spacing, exactly the parameters CrochetPARADE exposes live (change yarn thickness/color interactively), so the preview updates in O(stitches) without re-running placement, satisfying the 'update without re-deriving topology' requirement. [claim:clm_inf10]
- Cheap live feasibility/constraint signals are available without physics by reusing the procedural family's existing per-stitch tension model: CrochetPARADE's 's' mode (blue=too loose, red=>~15% over-stretched relative to baseline height) and its loose/tight flagging show that overly-tight/-loose stitch flags and excessive-curvature warnings are computable as O(stitches) comparisons of achieved-vs-target stitch length, while inc/dec-rate limits map onto AmiGo's curvature-obstruction notion, all computable per-frame during preview. [claim:clm_inf11]
- Mesh-stability (no broken loops, no avoidable self-intersection) is best validated topologically rather than geometrically for the procedural baseline: since inc/dec are edge-multiplicity facts and each round has a known expected_stitch_count, a broken loop is detectable as a missing adjacent-round edge or a stitch-count mismatch (an O(stitches) graph check), whereas self-intersection, the one purely-geometric failure mode the deterministic embedder can still produce under extreme curvature, is exactly the local region where a capped force-directed relax (per clm_inf05) should be triggered. [claim:clm_inf14]
- A genuine contradiction exists on whether force-directed layout is viable for interactive use, and it resolves against using it as the baseline: the KnitWit B1 seed frames Greer & Mould's spring layout as a usable 'simulation-lite' approximation, but the primary Greer & Mould paper documents non-convergence beyond ~700 stitches and the crochet-language study reports force-layout instability and chart rotation as the top usability complaint; the resolution is that force-directed is academically demonstrated yet not product-ready for real-time mobile, a high-decision-impact finding that flips the baseline to deterministic procedural. [claim:clm_inf15]
- GPLv3 licensing makes CrochetPARADE a study/reference asset, not a drop-in dependency, for a closed-source mobile product: its grammar is public domain and reusable, but its code being GPLv3 (copyleft) means KnitWit must re-implement the deterministic placement and tension-flagging logic rather than embed CrochetPARADE itself, a medium-severity IP risk whose mitigation is to adopt the documented algorithms (turn-parity attachment, 15%-threshold tension flags, GLTF export) as a clean-room re-implementation against the Crochet IR. [claim:clm_inf16]

## Links

- [[claim:clm_014]]
- [[claim:clm_015]]
- [[claim:clm_025]]
- [[claim:clm_031]]
- [[claim:clm_074]]
- [[claim:clm_046]]
- [[claim:clm_076]]
- [[claim:clm_077]]
- [[claim:clm_016]]
- [[claim:clm_073]]
- [[claim:clm_007]]
- [[claim:clm_013]]
- [[claim:clm_069]]
- [[claim:clm_inf07]]
- [[claim:clm_044]]
- [[claim:clm_002]]
- [[claim:clm_051]]
- [[claim:clm_052]]
- [[claim:clm_017]]
- [[claim:clm_045]]
- [[claim:clm_001]]
- [[claim:clm_047]]
- [[claim:clm_043]]
- [[claim:clm_058]]
- [[claim:clm_inf04]]
- [[claim:clm_020]]
- [[claim:clm_028]]
- [[claim:clm_054]]
- [[claim:clm_036]]
- [[claim:clm_071]]
- [[claim:clm_070]]
- [[claim:clm_075]]
- [[claim:clm_018]]
- [[claim:clm_049]]
- [[claim:clm_059]]
- [[claim:clm_033]]
- [[claim:clm_040]]
- [[claim:clm_039]]
- [[claim:clm_083]]
- [[claim:clm_037]]
- [[claim:clm_029]]
- [[claim:clm_082]]
- [[claim:clm_030]]
- [[claim:clm_021]]
- [[claim:clm_061]]
- [[claim:clm_005]]
- [[claim:clm_027]]
- [[claim:clm_085]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
