---
id: mwb_20260711_dr_stitch_level_3d_crochet_rendering
evidence_bundle_id: bundle_20260711_intent_research_20260710_stitch_level_3d
target_page: meatywiki/decisions/stitch_level_3d_crochet_rendering_fidelity.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260710_stitch_level_3d_crochet_rendering_fidelity_caec: Greer-Mould
  and CrochetPARADE forward-simulate a written pattern to 3D (matching IR-in), while AmiGo/Remesher require
  a '
key_claims:
- claim_id: clm_inf04
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
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf16
  include: true
- claim_id: clm_inf17
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf14
  include: true
- claim_id: clm_inf15
  include: true
- claim_id: clm_inf18
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_040
  - clm_042
  - clm_019
  - clm_001
  - clm_057
  - clm_076
  - clm_073
  - clm_062
  - clm_067
  - clm_072
  - clm_035
  - clm_069
  - clm_054
  - clm_033
  - clm_047
  - clm_048
  - clm_049
  - clm_034
  - clm_066
  - clm_016
  - clm_017
  - clm_025
  - clm_064
  - clm_005
  - clm_018
  - clm_028
  - clm_029
  - clm_006
  - clm_041
  - clm_003
  - clm_004
  - clm_009
  - clm_021
  - clm_059
  - clm_007
  - clm_071
  - clm_074
  - clm_008
  - clm_045
  - clm_015
  - clm_027
  - clm_022
  - clm_024
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Stitch-Level 3D Crochet Rendering Fidelity for KnitWit/LoopNest: Reconstruction Techniques, Shaping Algorithms, Progressive Guides, and On-Device vs Server Placement

## Context

- AmiGo takes a closed triangle mesh plus a single user-specified seed point and generates crochet instructions that, when crocheted and stuffed, approximate the input geometry. [claim:clm_001]
- Segments are attached via the 'join-as-you-go' method — each segment is crocheted onto the previous segment's last row — so no additional sewing is required and only simple stitches are used. [claim:clm_002]
- A crochet stitch is modeled as a top, base, and stem (inc/dec stitches have multiple stems), and the 'crochet graph' abstraction represents only stitch heads/bases and stems rather than a full yarn-level representation like Stitch Meshes. [claim:clm_003]
- The crochet graph is a more abstract representation than yarn-level Stitch Meshes, encoding only stitch heads/bases and stems. [claim:clm_004]
- Instruction generation takes only a few minutes, compared to tens of minutes for AutoKnit knitting, aided by crochet's low-resolution models and the avoidance of short rows. [claim:clm_005]
- A 3D preview is produced by embedding the crochet graph (via ShapeUp) with edge lengths constrained to the stitch size, so purely geometric conditions yield a result similar to the crocheted model — not a yarn physics simulation. [claim:clm_006]
- Crochetability is obstructed by 'craters' (regions of positive Gaussian curvature and negative mean curvature), which when stuffed do not reproduce the input geometry. [claim:clm_007]
- The method assumes the model is stuffed enough to reach maximal volume but not so much that the yarn stretches and creates gaps. [claim:clm_008]
- Mesh-level (stitch-mesh) knit models serve two purposes: interactive pattern editing and initialization of offline yarn-level simulations (a hybrid pipeline). [claim:clm_009]
- Prior mesh-level methods abstract knitting as a homogeneous material, which prevents capturing more complicated mixed structures. [claim:clm_010]
- The core observation is that a stitch's physical behavior depends not only on its own structure but on the surrounding stitch types; the paper extends the stitch mesh model with neighbor-aware per-stitch material properties. [claim:clm_011]
- Structural analysis of stitch connections yields a finite set of four-way kernels that combine to create general knit-purl patterns for relaxation. [claim:clm_012]
- The 4 neighbors of each stitch account for much of the neighborhood-dependent deformation while staying simple enough to fit directly to measured data using 11 basis swatches. [claim:clm_013]
- Kernel rest-lengths are inferred from measured reference patterns via a linear model, enabling efficient rest-shape estimation for mixed knit-purl patterns that supports fast fabric preview and more accurate yarn-level simulation. [claim:clm_014]
- CrochetPARADE is an open-source platform to create, visualize, and analyze both 2D and 3D crochet patterns. [claim:clm_015]
- All calculations run locally on the user's device with no data collected to a central server or transmitted over the internet, a direct precedent for client-side rendering feasibility. [claim:clm_016]
- The platform can be sluggish on old hardware, and patterns involving tens of thousands of stitches can take minutes or more to calculate. [claim:clm_017]
- The code is released under GPLv3 while the user manual is under Creative Commons BY-NC-SA, with the grammar itself in the public domain. [claim:clm_018]
- CrochetPARADE defines a custom crochet grammar/DSL for stitches and stitch patterns and forward-simulates written patterns into 3D models with chart, SVG, and 3D-file export. [claim:clm_019]
- The repository is a small, self-contained codebase with 12 commits on the main branch. [claim:clm_020]
- The Remesher crochets in rounds only with no turning chains, growing the fabric outward on the surface, seeded by either a Magic Ring (ring point + axis + stitch direction) or a Starting Chain (chain midpoint + axis + chain count). [claim:clm_021]
- The backend is a surface remesher that grows a stitched patch while maintaining a 'frontier' (the current boundary of the crocheted surface). [claim:clm_022]
- At each step it tries stitch/decrease/increase-style moves across stitch heights (ss, sc, hdc, dc, etc.) and checks geometric/topological guards such as overlap and surface proximity. [claim:clm_023]
- On dead-ends the remesher backtracks to a prior snapshot and applies an 'adaptive relaxation ladder' that selectively loosens epsilons/guards to escape local minima, emitting 'zip' sewing edges when independently-grown regions meet and supporting multiple yarns for complicated shapes. [claim:clm_024]
- A very fine stitch size (small L) explodes stitch count and can hit WebAssembly memory limits in the browser, requiring a larger L or the desktop app build. [claim:clm_025]
- Outputs are a 3D preview of the crocheted surface plus copy/paste-able CrochetPARADE instructions, and users can pause at specific points to inject their own moves, yarn starts/ends, or forced zips. [claim:clm_026]
- An admin follow-up reports the Remesher can generate round-based crochet instructions for non-watertight STLs with holes/openings, demonstrated with the baby-bootie STL exported from the new Export STL tool. [claim:clm_027]
- CrochetBench evaluates the shift from describing to doing via fine-grained procedural reasoning in crochet, requiring models to recognize stitches, select structurally appropriate instructions, and generate compilable procedures. [claim:clm_028]
- The benchmark adopts the CrochetPARADE DSL as its intermediate representation, enabling structural validation and functional evaluation via execution. [claim:clm_029]
- The benchmark spans stitch classification, instruction grounding, and both natural-language-to-DSL and image-to-DSL translation tasks. [claim:clm_030]
- Across all tasks, model performance sharply decreases as evaluation shifts from surface-level similarity to executable correctness, revealing weak long-range symbolic reasoning and weak 3D-aware procedural synthesis in VLMs. [claim:clm_031]
- The work frames the core unsolved problem as the gap between surface-level understanding and executable precision in real-world creative domains. [claim:clm_032]
- The spec defines a 4-level 3D ambition ladder: L0 2D+counters+highlighting, L1 structural 3D preview (stitch graph/mesh approximation), L2 editable 3D with consistent stitch semantics, L3 3D object to pattern synthesis. [claim:clm_033]
- The spec recommends 'structural geometry' 3D (stitches as a connected graph/surface with thickness, textured to suggest yarn) rather than yarn-level physics, to deliver preview/assembly utility 'without melting phones'. [claim:clm_034]
- The spec specifies a Crochet IR with units (US/UK, gauge, hook, yarn weight), pieces[], rows[] as stitch ops with counts (sc x6, inc, dec, repeat), constraints (expected end-of-row count, checkpoints), and assembly/placement markers. [claim:clm_035]
- The spec names market incumbents Ribblr (interactive ePatterns) and My Row Counter (imports PDFs/webpages/videos, multi-counter, Ravelry integration), and notes there is historically no official native Ravelry app. [claim:clm_036]
- The spec flags pattern IP/copyright as the #1 business landmine and parsing ambiguity (inconsistent abbreviations/formatting/charts) as a core technical risk. [claim:clm_037]
- The spec positions reverse 3D-to-pattern as a Phase 3 capability that is computationally grounded (citing peer-reviewed amigurumi generation) but warns 'looks like the model' does not equal pleasant/stable to crochet. [claim:clm_038]
- Crochet pattern design is an iterative guess-and-check loop of crocheting, evaluating the physical result, then undoing and remaking stitches across multiple passes. [claim:clm_039]
- The method takes a written crochet pattern as input, translates it into a graph, and computes a force-directed graph layout to produce a 3D representation. [claim:clm_040]
- The output 3D model reproduces the hand-crocheted pattern's shape and size, letting designers adjust from the digital model without physically crocheting it. [claim:clm_041]
- The tool targets both professional designers and beginners, aimed at pre-visualizing a pattern before investing the time and effort to physically make it. [claim:clm_042]
- The application is oriented toward amigurumi but the authors state it could be extended to clothing or similar crochet styles. [claim:clm_043]
- The work is classified under Human-centered computing, Graph drawings, published at the ACM/EG Expressive Symposium (WICED 2025) by The Eurographics Association (DOI 10.2312/exw.20251057). [claim:clm_044]
- Crochet is a fabrication technique that builds a 3D surface from yarn by interlacing loops formed with a special hook. [claim:clm_045]
- Standard crochet pictorial symbol notation does not directly show the yarn layout of stitches, making patterns hard for novices and computer programs to parse, visualize, and design. [claim:clm_046]
- The paper represents crochet patterns in the 'stitch mesh' paradigm as a library of tiles, where each tile contains yarn geometry and tiles connect along their edges. [claim:clm_047]
- To adapt stitch meshes to crochet, the authors introduce a special edge type capturing the 'current loop' — the loop of yarn held on the crochet hook during fabrication. [claim:clm_048]
- The authors create a library of mesh face types that model commonly-used crochet stitches, and demonstrate patterns generated from 3D models. [claim:clm_049]
- The work is an 8-page research article (Article No. 4, pp. 1-8) in SCF '20: Proceedings of the 5th Annual ACM Symposium on Computational Fabrication. [claim:clm_050]
- Crochet remains a purely manual craft with little digital tool support, in contrast to knitting and weaving which have received technical support. [claim:clm_051]
- Existing crochet tools are constrained by underlying pattern languages that are either ambiguous or limited in expressiveness, making instruction creation effortful and error-prone. [claim:clm_052]
- The paper proposes the first visual, domain-specific, graph-based language for crochet pattern representation. [claim:clm_053]
- A prototype editor implements the language, allowing patterns to be created in 2D and viewed in 3D. [claim:clm_054]
- A user study demonstrated the language lets designers express both 2D and 3D patterns and removes ambiguities present in current standard notations. [claim:clm_055]
- The paper appeared in Onward! 2022 (ACM SIGPLAN SPLASH), pages 48-62, published 01 December 2022, as an open-access research article. [claim:clm_056]
- AmiGo's inputs are a closed manifold triangle mesh M, a single user seed vertex s, and a stitch width w, from which it generates human-readable crochet instructions P(M, s, w). [claim:clm_057]
- Single crochet (sc) is treated as an approximately square stitch, so covering the mesh with sc stitches is equivalent to a constant-edge-length unit-square quad remesh. [claim:clm_058]
- A square-stitch cover is impossible on non-developable (nonzero Gaussian curvature) surfaces, so curvature is accommodated by local increase (inc(x)) and decrease (dec(x)) stitches. [claim:clm_059]
- Rows are defined as isolines of the geodesic distance function f(v)=d(v,s) from the seed, so two points lie on the same row iff their geodesic distance to the seed is equal. [claim:clm_060]
- Curvature-adapted sampling of the parameterization reconstructs negative curvature and yields object-similar shapes, whereas uniform sampling does not. [claim:clm_061]
- A 3D preview embedding is computed with ShapeUp using purely geometric conditions, and the result closely matches the physical crocheted-and-stuffed object. [claim:clm_062]
- Branching shapes are auto-segmented and joined via 'join-as-you-go', where each segment is crocheted onto the previous segment's last row, requiring no additional sewing. [claim:clm_063]
- AmiGo's simpler approach and crochet's low resolution give pattern-generation times of a few minutes, versus tens of minutes for AutoKnit. [claim:clm_064]
- The spec defines a four-level 3D capability ladder: L0 = 2D + counters + highlighting, L1 = structural 3D preview (stitch graph/mesh approximation), L2 = editable 3D with consistent stitch semantics, L3 = 3D object to pattern synthesis. [claim:clm_065]
- The spec recommends the first '3D' be structural geometry (stitches as a connected graph/surface with thickness, textured to suggest yarn) rather than yarn-level physics, to deliver preview and assembly utility 'without melting phones.' [claim:clm_066]
- The spec sketches a Crochet intermediate representation with units (US/UK, gauge, hook, yarn weight), pieces[], rows[] of stitch ops with counts (sc x6, inc, dec, repeat), constraints (expected end-of-row counts, checkpoints), and assembly/placement markers, mapping each stitch to a node/edge with spatial placement rules. [claim:clm_067]
- The spec cites CrochetPARADE, a 2025 EG paper on force-directed graph layout for crochet, and a peer-reviewed ACM paper on computational amigurumi pattern generation as credible non-physics 3D paths. [claim:clm_068]
- The spec identifies a 'Ghost next row' transparent overlay as very doable in 2D now and later in 3D, positioned within the highest-ROI pattern playback feature. [claim:clm_069]
- The spec frames reverse 3D-to-pattern generation as a Phase 3 capability with major hurdles: models need watertight meshes and sane topology, stitch size/tension vary per user, and 'looks like the model' does not equal pleasant/stable to crochet. [claim:clm_070]
- Amigurumi are crocheted in the round in single crochet with near-constant row height (~= SC width), so each stitch in a row is equidistant to the seed and rows follow geodesic equidistant curves. [claim:clm_071]
- Stitch locations are found by cutting and flattening the model (vertical = geodesic distance/row number, horizontal = arc length along the equidistant curve/stitch number), then evenly sampling. [claim:clm_072]
- Vertical (column) edges of the crochet graph are chosen by solving an optimization that minimizes the total length of the vertical edges. [claim:clm_073]
- 'Crater' regions (negative mean + positive Gaussian curvature) are unrealizable under maximal-stuffing and are removed by pre-inflating the model; saddle regions (both curvatures negative) use fewer stitches via adapted sampling. [claim:clm_074]
- Creases are reproduced by automatically switching to Back-Loop-Only (BLO) / Front-Loop-Only (FLO) stitches where maximal absolute curvature is high and its direction is orthogonal to the crocheting direction. [claim:clm_075]
- A 3D preview is produced by embedding the crochet graph via optimization (fix seed, constrain SC/row edge lengths to fixed width, require smoothness); the result is very similar to the crocheted output without any physical simulation. [claim:clm_076]
- The method joins-and-turns at each round rather than spiraling to avoid stitch slanting (incompatible with their shortest-vertical-edge optimization); spiral compatibility is planned future work. [claim:clm_077]

## Decision

For KnitWit's L1 structural preview, adopt a written-pattern-in engine (Greer-Mould force-directed layout or an independently reimplemented CrochetPARADE-style forward simulator) rather than AmiGo or the Remesher, which require a mesh input the app will not have during pattern playback. [claim:clm_inf04]

## Rationale

- Greer-Mould and CrochetPARADE forward-simulate a written pattern to 3D (matching IR-in), while AmiGo/Remesher require a closed mesh + seed; therefore the pattern-input engines are the only ones that fit the L1 playback pipeline. [claim:clm_inf04]
- AmiGo builds column edges via a length-minimizing optimization and embeds via constrained ShapeUp; Greer-Mould shows the pattern->graph->layout flow; the IR already encodes rounds/ops, so these steps compose into a concrete forward pipeline. [claim:clm_inf06]
- Force-directed layouts (Greer-Mould) optimize a soft energy that can settle in unstable local minima, whereas AmiGo's hard geometric constraints with a fixed seed produce a more deterministic embedding; for a repeatable round-by-round reveal, determinism matters, so the constrained formulation is safer against the G3 instability fail signal. [claim:clm_inf07]
- AmiGo's flattening assigns vertical=row-number and horizontal=stitch-number coordinates, and the IR already indexes rounds and ops; a stable per-stitch id from those indices makes progressive reveal and highlighting a pure filter over precomputed positions. [claim:clm_inf09]
- The spec calls the ghost-row overlay very doable in 2D now; Digital Crochet demonstrates 2D-edit/3D-view over one graph; since 2D and 3D share the stitch-graph node metadata, highlighting built at L0 transfers directly to L1. [claim:clm_inf10]
- Stitch Meshes carry full per-tile yarn geometry (high cost); the spec explicitly recommends texturing to *suggest* yarn rather than modeling it; instanced glyphs per node deliver the visual read at a fraction of the geometry, aligning with the structural-geometry recommendation. [claim:clm_inf11]
- Both AmiGo (few minutes) and CrochetPARADE (minutes, WASM limits) show the solve is a one-time non-interactive cost, while CrochetPARADE proves local rendering is viable; placing the cacheable solve off the per-frame path and keeping only render on-device follows directly. [claim:clm_inf13]
- CrochetPARADE releases code under GPLv3 but states the grammar is public domain; a closed-source App Store product cannot link GPLv3 code, so reimplementing against the public-domain grammar is the compliant path. [claim:clm_inf16]
- CrochetBench uses the CrochetPARADE DSL as an IR enabling structural validation and execution; the KnitWit IR already carries ops/expected_stitch_count/visual_hint.shape_role, so it is a viable G2 baseline needing only stable ids (for highlighting) and a shape_role-to-curvature link (for the forward engine). [claim:clm_inf17]
- Three independent research/tool sources (AmiGo, Greer-Mould, CrochetPARADE) each report that geometric-only embedding closely matches the real crocheted object, and the KnitWit spec independently recommends structural geometry over physics; convergence across independent sources makes the no-physics-needed conclusion high-confidence. [claim:clm_inf01]
- The AmiGo authors explicitly state the crochet graph is more abstract (heads/bases/stems) than yarn-level Stitch Meshes; neighbor-aware relaxation sits between as a mesh-level method; the spec's 'structural geometry without melting phones' target aligns with the abstract-graph tier, so the cost/fidelity ordering follows. [claim:clm_inf02]
- AmiGo and the Remesher take a 3D mesh as input and emit a pattern; Greer-Mould, CrochetPARADE forward sim, and Digital Crochet take a written pattern and emit 3D. KnitWit's data flow (Crochet IR -> preview) matches the forward family, making that the correct L1 source set. [claim:clm_inf03]
- AmiGo states square-stitch cover is only possible on developable (zero-Gaussian-curvature) surfaces and that inc/dec locally add/remove curvature; combined with the constant-row-height geometry, this establishes stitch-count delta as the discrete curvature control knob. [claim:clm_inf05]
- AmiGo reports craters cannot reproduce input geometry when stuffed and pre-inflates to remove them; a KnitWit preview that hides this discrepancy would violate the spec's 'output is not visually misleading' G3 criterion, so explicit detection/flagging is required. [claim:clm_inf08]
- CrochetPARADE runs all calculations locally (client-side precedent) yet reports minutes-scale compute and WASM memory limits at high stitch counts; this isolates the compute-heavy solve, not the draw call, as the scaling constraint. [claim:clm_inf12]
- The spec's 'without melting phones' structural-geometry target plus CrochetPARADE's local-rendering precedent imply modest instanced-glyph counts render fine; the stated minutes-scale compute at high stitch counts identifies the solve as the real limiter. Triangle estimate is order-of-magnitude inference, hence low confidence. [claim:clm_inf14]
- AmiGo/Stitch Meshes/neighbor-aware relaxation are peer-reviewed methods without released mobile tooling; CrochetPARADE is a running open-source platform with exports and local compute, placing it alone on the product-adjacent side of the line. [claim:clm_inf15]
- The Remesher admin note claims non-watertight handling via a growing frontier and zip edges, while AmiGo defines rows as geodesic isolines on a closed manifold; the algorithmic difference (local surface growth vs global geodesic field) plausibly explains the differing input tolerance. [claim:clm_inf18]

## Consequences

- Recommended forward shaping pipeline for the KnitWit engine: (1) expand IR repeats to explicit per-stitch ops, (2) build a stitch graph with intra-round row edges and inter-round column edges, (3) solve a constrained embedding that fixes the seed, constrains row/column edge lengths to the stitch width, and enforces smoothness - i.e. AmiGo's ShapeUp preview recipe applied directly to an IR-derived graph. [claim:clm_inf06]
- AmiGo's constrained-optimization embedding (fixed seed + edge-length constraints + smoothness) should be preferred over a pure force-directed layout for the model-at-round-N preview, because force-directed layouts are prone to local-minima instability - exactly the 'graph layout is unstable' condition the spec names as a G3 failure. [claim:clm_inf07]
- Model-at-round-N and current-stitch highlighting reduce to a graph-visibility filter: give every stitch a stable (piece_id, round_index, stitch_index) triple derived from IR position, then render round N = the subgraph with round_index <= N and the current-stitch highlight = the single node at (N, k) - no re-computation needed. [claim:clm_inf09]
- Ghost-next-row overlay and current-round highlighting are low-risk and should ship first on the shared 2D stitch graph (L0), reusing the same node metadata that later drives the 3D embedding, so highlighting logic is authored once and inherited by L1. [claim:clm_inf10]
- True per-stitch V-stitch geometry requires yarn-level tile meshes (Stitch Meshes' 'current loop' edge and mesh-face library), which is too heavy for interactive mobile; a cheaper equivalent is instanced low-poly/textured stitch glyphs per graph node that suggest yarn - recommended for KnitWit's on-device layer. [claim:clm_inf11]
- The on-device/server boundary should be drawn at the embedding solve, not the render: precompute the stitch-graph positions once (at pattern import, on-device for small pieces or server-side/cached for pieces beyond a few thousand stitches) and do only interactive rendering, round reveal, and highlighting on-device with Metal. [claim:clm_inf13]
- Forking CrochetPARADE's code is a high-severity legal risk because GPLv3 copyleft would force KnitWit's closed-source iOS app open; the mitigation is to independently reimplement the DSL and forward simulator, since the grammar itself is public domain while only the code is GPLv3. [claim:clm_inf16]
- The Crochet IR v0.1 starter schema should be adopted as-is for gate G2, with two additions - a stable per-stitch id field and an explicit shape_role<->curvature mapping - because CrochetBench validates that a CrochetPARADE-style DSL can serve as an executable, compilable intermediate representation. [claim:clm_inf17]
- Purely geometric constraint-embedding (AmiGo's ShapeUp embedding, Greer-Mould force-directed layout, and CrochetPARADE forward simulation) is empirically sufficient to produce object-recognizable amigurumi shapes without any yarn-level physics simulation. [claim:clm_inf01]
- Ranked by visual-fidelity-per-compute-cost, the crochet representations order as yarn-level Stitch Meshes (highest fidelity, highest cost) > neighbor-aware mesh-level relaxation > abstract crochet-graph geometric embedding (AmiGo) > force-directed graph layout; the crochet-graph / structural-geometry tier is the fidelity-vs-mobile-cost sweet spot for KnitWit. [claim:clm_inf02]
- The literature splits into a FORWARD family for pattern->3D (Greer-Mould force-directed layout, CrochetPARADE forward sim, Digital Crochet 2D-edit/3D-view) and an INVERSE family for mesh->pattern (AmiGo, CrochetPARADE Remesher); KnitWit's L1 preview needs the forward family because at playback time the app holds a pattern/IR, not a mesh. [claim:clm_inf03]
- A round-by-round inc/dec schedule is functionally a discrete Gaussian-curvature specification: constant stitch count yields zero curvature (tube/cylinder), net increases yield positive curvature (sphere/cap growth), and net decreases yield closure/negative regions - so shaping global form reduces to placing curvature via stitch-count deltas. [claim:clm_inf05]
- The dominant shape-fidelity failure mode is 'craters' (positive Gaussian + negative mean curvature), which are physically unrealizable under maximal stuffing; a forward preview that renders such regions as clean geometry will actively mislead users, so the engine must detect and flag (or pre-inflate) them rather than silently smooth. [claim:clm_inf08]
- CrochetPARADE is the decisive precedent that stitch-level crochet rendering can run fully client-side (no server), but its own README shows the embedding/relaxation step - not rendering - is the bottleneck: tens-of-thousands-of-stitch models take minutes and can exhaust WebAssembly memory. [claim:clm_inf12]
- Rendering is not the mobile constraint: a typical amigurumi of a few hundred to a few thousand stitches maps to that many instanced glyphs (order 10^5-10^6 triangles at low-poly), comfortably within iPhone Metal budgets; therefore the compute-bound relaxation, not the draw, is what must be moved off the interactive path. [claim:clm_inf14]
- On the academic-feasibility vs product-readiness line: AmiGo, Stitch Meshes, and neighbor-aware relaxation are research demos (gated papers, no mobile/Swift implementation), while CrochetPARADE is the only product-adjacent artifact (shipping, client-side, exporting) - but none is a drop-in amigurumi-mobile solution. [claim:clm_inf15]
- There is a direct capability contradiction: CrochetPARADE's Remesher is reported to handle non-watertight STLs with holes, whereas AmiGo strictly requires a closed manifold mesh; the likely resolution is that the Remesher's frontier-growth-with-zips treats open boundaries as edges to grow toward while AmiGo's geodesic-isoline formulation needs a closed surface - decision impact medium, relevant only if/when mesh->pattern is built. [claim:clm_inf18]

## Links

- [[claim:clm_040]]
- [[claim:clm_042]]
- [[claim:clm_019]]
- [[claim:clm_001]]
- [[claim:clm_057]]
- [[claim:clm_076]]
- [[claim:clm_073]]
- [[claim:clm_062]]
- [[claim:clm_067]]
- [[claim:clm_072]]
- [[claim:clm_035]]
- [[claim:clm_069]]
- [[claim:clm_054]]
- [[claim:clm_033]]
- [[claim:clm_047]]
- [[claim:clm_048]]
- [[claim:clm_049]]
- [[claim:clm_034]]
- [[claim:clm_066]]
- [[claim:clm_016]]
- [[claim:clm_017]]
- [[claim:clm_025]]
- [[claim:clm_064]]
- [[claim:clm_005]]
- [[claim:clm_018]]
- [[claim:clm_028]]
- [[claim:clm_029]]
- [[claim:clm_006]]
- [[claim:clm_041]]
- [[claim:clm_003]]
- [[claim:clm_004]]
- [[claim:clm_009]]
- [[claim:clm_021]]
- [[claim:clm_059]]
- [[claim:clm_007]]
- [[claim:clm_071]]
- [[claim:clm_074]]
- [[claim:clm_008]]
- [[claim:clm_045]]
- [[claim:clm_015]]
- [[claim:clm_027]]
- [[claim:clm_022]]
- [[claim:clm_024]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
