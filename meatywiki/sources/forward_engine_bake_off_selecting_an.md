---
id: mwb_20260614_forward_engine_bake_off_selecting_an
evidence_bundle_id: bundle_20260614_intent_research_20260614_for_turning_a
target_page: meatywiki/sources/forward_engine_bake_off_selecting_an.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_for_turning_a_structured_crochet_ir:
  86 supported claim(s) across 12 source card(s).'
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
- claim_id: clm_060
  include: true
- claim_id: clm_061
  include: true
- claim_id: clm_062
  include: true
- claim_id: clm_063
  include: true
- claim_id: clm_064
  include: true
- claim_id: clm_065
  include: true
- claim_id: clm_066
  include: true
- claim_id: clm_067
  include: true
- claim_id: clm_068
  include: true
- claim_id: clm_069
  include: true
- claim_id: clm_070
  include: true
- claim_id: clm_071
  include: true
- claim_id: clm_072
  include: true
- claim_id: clm_073
  include: true
- claim_id: clm_074
  include: true
- claim_id: clm_075
  include: true
- claim_id: clm_076
  include: true
- claim_id: clm_077
  include: true
- claim_id: clm_078
  include: true
- claim_id: clm_079
  include: true
- claim_id: clm_080
  include: true
- claim_id: clm_081
  include: true
- claim_id: clm_082
  include: true
- claim_id: clm_083
  include: true
- claim_id: clm_084
  include: true
- claim_id: clm_085
  include: true
- claim_id: clm_086
  include: true
links:
  source_cards:
  - src_20260614_kw004_00
  - src_20260614_kw004_01
  - src_20260614_kw004_02
  - src_20260614_kw004_03
  - src_20260614_kw004_04
  - src_20260614_kw004_05
  - src_20260614_kw004_06
  - src_20260614_kw004_07
  - src_20260614_kw004_08
  - src_20260614_kw004_09
  - src_20260614_kw004_10
  - src_20260614_kw004_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Forward Engine Bake-Off: Selecting an Accurate-Enough, Mobile-Feasible Crochet-IR-to-3D Embedding for KnitWit

## Summary

Source note distilled from research run rf_run_20260614_for_turning_a_structured_crochet_ir: 86 supported claim(s) across 12 source card(s).

## Key claims

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

## Sources

- src_20260614_kw004_00 — Modeling crochet patterns with a force-directed graph layout
- src_20260614_kw004_01 — Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260614_kw004_02 — CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger) repository
- src_20260614_kw004_03 — CrochetPARADE Manual (Crochet PAttern Renderer, Analyzer, and DEbugger)
- src_20260614_kw004_04 — CrochetPARADE: Crochet PAttern Renderer, Analyzer and DEbugger
- src_20260614_kw004_05 — modeling-amigurumi (EnbyMonkey) — Connectivity Shapes amigurumi modeler
- src_20260614_kw004_06 — AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw004_07 — Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260614_kw004_08 — KnitWit B1 Workstream Report - Prior Art & Taxonomy
- src_20260614_kw004_09 — KnitWit Research Plan (local project seed)
- src_20260614_kw004_10 — Representing Crochet with Stitch Meshes
- src_20260614_kw004_11 — Curvy: A Parametric Cross-section based Surface Reconstruction

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
