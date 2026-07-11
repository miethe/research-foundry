---
schema_version: '0.1'
type: research_report
report_id: report_20260711_research_report_for_rf_run_20260710
title: 'Stitch-Level 3D Crochet Rendering Fidelity for KnitWit/LoopNest: Reconstruction Techniques, Shaping Algorithms, Progressive Guides, and On-Device vs Server Placement'
intent_id: intent_research_20260710_stitch_level_3d_crochet_rendering_fidelity_6718
evidence_bundle_id: pending
created_at: '2026-07-11T10:32:07-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# Stitch-Level 3D Crochet Rendering Fidelity for KnitWit/LoopNest

Technical memo for the KnitWit/LoopNest Pattern to 3D visualizer and 3D-object to pattern generator workstreams.

## Executive summary

**Inference:** Purely geometric constraint-embedding (AmiGo's ShapeUp embedding, Greer-Mould force-directed layout, and CrochetPARADE forward simulation) is empirically sufficient to produce object-recognizable amigurumi shapes without any yarn-level physics simulation. [claim:clm_inf01]
**Inference:** Ranked by visual-fidelity-per-compute-cost, the crochet representations order as yarn-level Stitch Meshes (highest fidelity, highest cost) > neighbor-aware mesh-level relaxation > abstract crochet-graph geometric embedding (AmiGo) > force-directed graph layout; the crochet-graph / structural-geometry tier is the fidelity-vs-mobile-cost sweet spot for KnitWit. [claim:clm_inf02]
**Inference:** The literature splits into a FORWARD family for pattern->3D (Greer-Mould force-directed layout, CrochetPARADE forward sim, Digital Crochet 2D-edit/3D-view) and an INVERSE family for mesh->pattern (AmiGo, CrochetPARADE Remesher); KnitWit's L1 preview needs the forward family because at playback time the app holds a pattern/IR, not a mesh. [claim:clm_inf03]
**Inference:** For KnitWit's L1 structural preview, adopt a written-pattern-in engine (Greer-Mould force-directed layout or an independently reimplemented CrochetPARADE-style forward simulator) rather than AmiGo or the Remesher, which require a mesh input the app will not have during pattern playback. [claim:clm_inf04]
**Inference:** A round-by-round inc/dec schedule is functionally a discrete Gaussian-curvature specification: constant stitch count yields zero curvature (tube/cylinder), net increases yield positive curvature (sphere/cap growth), and net decreases yield closure/negative regions - so shaping global form reduces to placing curvature via stitch-count deltas. [claim:clm_inf05]
**Inference:** The on-device/server boundary should be drawn at the embedding solve, not the render: precompute the stitch-graph positions once (at pattern import, on-device for small pieces or server-side/cached for pieces beyond a few thousand stitches) and do only interactive rendering, round reveal, and highlighting on-device with Metal. [claim:clm_inf13]
**Inference:** On the academic-feasibility vs product-readiness line: AmiGo, Stitch Meshes, and neighbor-aware relaxation are research demos (gated papers, no mobile/Swift implementation), while CrochetPARADE is the only product-adjacent artifact (shipping, client-side, exporting) - but none is a drop-in amigurumi-mobile solution. [claim:clm_inf15]
**Inference:** Forking CrochetPARADE's code is a high-severity legal risk because GPLv3 copyleft would force KnitWit's closed-source iOS app open; the mitigation is to independently reimplement the DSL and forward simulator, since the grammar itself is public domain while only the code is GPLv3. [claim:clm_inf16]
**Speculation:** The single highest-value G3 de-risking experiment is EXP-005 (stitch-graph -> approximate 3D) on a 6-sc magic-ring sphere and a plain cylinder using AmiGo's constrained-embedding recipe; if these embed to a recognizable ball and tube with stable round highlighting, L1 is greenlit - and this is more likely than not to succeed given three sources already report geometric embedding matching real objects. [claim:clm_spec01]
**Speculation:** Reverse mesh->pattern generation (L3 / Phase 3) will remain the product's weakest link and should stay deferred behind pattern->3D + IR, because even AmiGo/Remesher 'looks-like-the-model' outputs are not guaranteed pleasant or stable to crochet and VLM-based procedural synthesis collapses on executable correctness. [claim:clm_spec02]

## Technique catalog: pattern<->3D crochet reconstruction methods

The following matrix catalogs the leading pattern->3D and yarn/stitch-mesh reconstruction techniques, their direction, their 3D mechanism, and whether they yield object-recognizable shapes.

| Method (source) | Direction | Core 3D mechanism | Object-recognizable result | Evidence |
|---|---|---|---|---|
| AmiGo (Amigurumi computational design) | inverse (mesh->pattern) | ShapeUp geometric embedding constrained to stitch size | closely matches physical crocheted-and-stuffed object | [claim:clm_062] |
| Amigurumi from Geodesic Distances | inverse (mesh->pattern) | crochet-graph embedding via constrained optimization | very similar to crocheted output, no physics | [claim:clm_076] |
| Greer-Mould force-directed layout | forward (pattern->3D) | force-directed graph layout of pattern graph | reproduces hand-crocheted shape and size | [claim:clm_041] |
| CrochetPARADE forward simulation | forward (pattern->3D) | DSL forward-sim to 3D with chart/SVG/3D export | 3D models generated from written patterns | [claim:clm_019] |
| CrochetPARADE Remesher | inverse (mesh->pattern) | frontier-growth surface remesher | round-based instructions incl. non-watertight STLs | [claim:clm_027] |
| Representing Crochet with Stitch Meshes | representation | tile library with yarn geometry + current-loop edge | patterns demonstrated from 3D models | [claim:clm_049] |
| Neighbor-Aware Relaxation (knits) | relaxation | four-way kernels fit to measured swatches | fast fabric preview + more accurate sim | [claim:clm_014] |
| Digital Crochet visual language | forward / editing | graph-based DSL, create 2D and view 3D | user study: expresses 2D+3D, removes ambiguity | [claim:clm_055] |

### AmiGo: computational design of amigurumi crochet patterns

AmiGo takes a closed triangle mesh plus a single user-specified seed point and generates crochet instructions that, when crocheted and stuffed, approximate the input geometry. [claim:clm_001]
AmiGo's inputs are a closed manifold triangle mesh M, a single user seed vertex s, and a stitch width w, from which it generates human-readable crochet instructions P(M, s, w). [claim:clm_057]
Single crochet (sc) is treated as an approximately square stitch, so covering the mesh with sc stitches is equivalent to a constant-edge-length unit-square quad remesh. [claim:clm_058]
A square-stitch cover is impossible on non-developable (nonzero Gaussian curvature) surfaces, so curvature is accommodated by local increase (inc(x)) and decrease (dec(x)) stitches. [claim:clm_059]
Rows are defined as isolines of the geodesic distance function f(v)=d(v,s) from the seed, so two points lie on the same row iff their geodesic distance to the seed is equal. [claim:clm_060]
A crochet stitch is modeled as a top, base, and stem (inc/dec stitches have multiple stems), and the 'crochet graph' abstraction represents only stitch heads/bases and stems rather than a full yarn-level representation like Stitch Meshes. [claim:clm_003]
The crochet graph is a more abstract representation than yarn-level Stitch Meshes, encoding only stitch heads/bases and stems. [claim:clm_004]
Curvature-adapted sampling of the parameterization reconstructs negative curvature and yields object-similar shapes, whereas uniform sampling does not. [claim:clm_061]
A 3D preview is produced by embedding the crochet graph (via ShapeUp) with edge lengths constrained to the stitch size, so purely geometric conditions yield a result similar to the crocheted model - not a yarn physics simulation. [claim:clm_006]
A 3D preview embedding is computed with ShapeUp using purely geometric conditions, and the result closely matches the physical crocheted-and-stuffed object. [claim:clm_062]
Crochetability is obstructed by 'craters' (regions of positive Gaussian curvature and negative mean curvature), which when stuffed do not reproduce the input geometry. [claim:clm_007]
The method assumes the model is stuffed enough to reach maximal volume but not so much that the yarn stretches and creates gaps. [claim:clm_008]
Branching shapes are auto-segmented and joined via 'join-as-you-go', where each segment is crocheted onto the previous segment's last row, requiring no additional sewing. [claim:clm_063]
Segments are attached via the 'join-as-you-go' method - each segment is crocheted onto the previous segment's last row - so no additional sewing is required and only simple stitches are used. [claim:clm_002]
Instruction generation takes only a few minutes, compared to tens of minutes for AutoKnit knitting, aided by crochet's low-resolution models and the avoidance of short rows. [claim:clm_005]
AmiGo's simpler approach and crochet's low resolution give pattern-generation times of a few minutes, versus tens of minutes for AutoKnit. [claim:clm_064]

### Amigurumi crochet patterns from geodesic distances

Amigurumi are crocheted in the round in single crochet with near-constant row height (~= SC width), so each stitch in a row is equidistant to the seed and rows follow geodesic equidistant curves. [claim:clm_071]
Stitch locations are found by cutting and flattening the model (vertical = geodesic distance/row number, horizontal = arc length along the equidistant curve/stitch number), then evenly sampling. [claim:clm_072]
Vertical (column) edges of the crochet graph are chosen by solving an optimization that minimizes the total length of the vertical edges. [claim:clm_073]
'Crater' regions (negative mean + positive Gaussian curvature) are unrealizable under maximal-stuffing and are removed by pre-inflating the model; saddle regions (both curvatures negative) use fewer stitches via adapted sampling. [claim:clm_074]
Creases are reproduced by automatically switching to Back-Loop-Only (BLO) / Front-Loop-Only (FLO) stitches where maximal absolute curvature is high and its direction is orthogonal to the crocheting direction. [claim:clm_075]
A 3D preview is produced by embedding the crochet graph via optimization (fix seed, constrain SC/row edge lengths to fixed width, require smoothness); the result is very similar to the crocheted output without any physical simulation. [claim:clm_076]
The method joins-and-turns at each round rather than spiraling to avoid stitch slanting (incompatible with their shortest-vertical-edge optimization); spiral compatibility is planned future work. [claim:clm_077]

### Representing crochet with stitch meshes

Crochet is a fabrication technique that builds a 3D surface from yarn by interlacing loops formed with a special hook. [claim:clm_045]
Standard crochet pictorial symbol notation does not directly show the yarn layout of stitches, making patterns hard for novices and computer programs to parse, visualize, and design. [claim:clm_046]
The paper represents crochet patterns in the 'stitch mesh' paradigm as a library of tiles, where each tile contains yarn geometry and tiles connect along their edges. [claim:clm_047]
To adapt stitch meshes to crochet, the authors introduce a special edge type capturing the 'current loop' - the loop of yarn held on the crochet hook during fabrication. [claim:clm_048]
The authors create a library of mesh face types that model commonly-used crochet stitches, and demonstrate patterns generated from 3D models. [claim:clm_049]
The work is an 8-page research article (Article No. 4, pp. 1-8) in SCF '20: Proceedings of the 5th Annual ACM Symposium on Computational Fabrication. [claim:clm_050]

### Neighbor-aware data-driven relaxation of stitch mesh models

Mesh-level (stitch-mesh) knit models serve two purposes: interactive pattern editing and initialization of offline yarn-level simulations (a hybrid pipeline). [claim:clm_009]
Prior mesh-level methods abstract knitting as a homogeneous material, which prevents capturing more complicated mixed structures. [claim:clm_010]
The core observation is that a stitch's physical behavior depends not only on its own structure but on the surrounding stitch types; the paper extends the stitch mesh model with neighbor-aware per-stitch material properties. [claim:clm_011]
Structural analysis of stitch connections yields a finite set of four-way kernels that combine to create general knit-purl patterns for relaxation. [claim:clm_012]
The 4 neighbors of each stitch account for much of the neighborhood-dependent deformation while staying simple enough to fit directly to measured data using 11 basis swatches. [claim:clm_013]
Kernel rest-lengths are inferred from measured reference patterns via a linear model, enabling efficient rest-shape estimation for mixed knit-purl patterns that supports fast fabric preview and more accurate yarn-level simulation. [claim:clm_014]

### CrochetPARADE platform

CrochetPARADE is an open-source platform to create, visualize, and analyze both 2D and 3D crochet patterns. [claim:clm_015]
CrochetPARADE defines a custom crochet grammar/DSL for stitches and stitch patterns and forward-simulates written patterns into 3D models with chart, SVG, and 3D-file export. [claim:clm_019]
All calculations run locally on the user's device with no data collected to a central server or transmitted over the internet, a direct precedent for client-side rendering feasibility. [claim:clm_016]
The platform can be sluggish on old hardware, and patterns involving tens of thousands of stitches can take minutes or more to calculate. [claim:clm_017]
The code is released under GPLv3 while the user manual is under Creative Commons BY-NC-SA, with the grammar itself in the public domain. [claim:clm_018]
The repository is a small, self-contained codebase with 12 commits on the main branch. [claim:clm_020]

### CrochetPARADE Remesher

The Remesher crochets in rounds only with no turning chains, growing the fabric outward on the surface, seeded by either a Magic Ring (ring point + axis + stitch direction) or a Starting Chain (chain midpoint + axis + chain count). [claim:clm_021]
The backend is a surface remesher that grows a stitched patch while maintaining a 'frontier' (the current boundary of the crocheted surface). [claim:clm_022]
At each step it tries stitch/decrease/increase-style moves across stitch heights (ss, sc, hdc, dc, etc.) and checks geometric/topological guards such as overlap and surface proximity. [claim:clm_023]
On dead-ends the remesher backtracks to a prior snapshot and applies an 'adaptive relaxation ladder' that selectively loosens epsilons/guards to escape local minima, emitting 'zip' sewing edges when independently-grown regions meet and supporting multiple yarns for complicated shapes. [claim:clm_024]
A very fine stitch size (small L) explodes stitch count and can hit WebAssembly memory limits in the browser, requiring a larger L or the desktop app build. [claim:clm_025]
Outputs are a 3D preview of the crocheted surface plus copy/paste-able CrochetPARADE instructions, and users can pause at specific points to inject their own moves, yarn starts/ends, or forced zips. [claim:clm_026]
An admin follow-up reports the Remesher can generate round-based crochet instructions for non-watertight STLs with holes/openings, demonstrated with the baby-bootie STL exported from the new Export STL tool. [claim:clm_027]

### CrochetBench: vision-language models in the crochet domain

CrochetBench evaluates the shift from describing to doing via fine-grained procedural reasoning in crochet, requiring models to recognize stitches, select structurally appropriate instructions, and generate compilable procedures. [claim:clm_028]
The benchmark adopts the CrochetPARADE DSL as its intermediate representation, enabling structural validation and functional evaluation via execution. [claim:clm_029]
The benchmark spans stitch classification, instruction grounding, and both natural-language-to-DSL and image-to-DSL translation tasks. [claim:clm_030]
Across all tasks, model performance sharply decreases as evaluation shifts from surface-level similarity to executable correctness, revealing weak long-range symbolic reasoning and weak 3D-aware procedural synthesis in VLMs. [claim:clm_031]
The work frames the core unsolved problem as the gap between surface-level understanding and executable precision in real-world creative domains. [claim:clm_032]

### Modeling crochet patterns with a force-directed graph layout (Greer-Mould)

Crochet pattern design is an iterative guess-and-check loop of crocheting, evaluating the physical result, then undoing and remaking stitches across multiple passes. [claim:clm_039]
The method takes a written crochet pattern as input, translates it into a graph, and computes a force-directed graph layout to produce a 3D representation. [claim:clm_040]
The output 3D model reproduces the hand-crocheted pattern's shape and size, letting designers adjust from the digital model without physically crocheting it. [claim:clm_041]
The tool targets both professional designers and beginners, aimed at pre-visualizing a pattern before investing the time and effort to physically make it. [claim:clm_042]
The application is oriented toward amigurumi but the authors state it could be extended to clothing or similar crochet styles. [claim:clm_043]
The work is classified under Human-centered computing, Graph drawings, published at the ACM/EG Expressive Symposium (WICED 2025) by The Eurographics Association (DOI 10.2312/exw.20251057). [claim:clm_044]

### Digital Crochet: toward a visual language for pattern description

Crochet remains a purely manual craft with little digital tool support, in contrast to knitting and weaving which have received technical support. [claim:clm_051]
Existing crochet tools are constrained by underlying pattern languages that are either ambiguous or limited in expressiveness, making instruction creation effortful and error-prone. [claim:clm_052]
The paper proposes the first visual, domain-specific, graph-based language for crochet pattern representation. [claim:clm_053]
A prototype editor implements the language, allowing patterns to be created in 2D and viewed in 3D. [claim:clm_054]
A user study demonstrated the language lets designers express both 2D and 3D patterns and removes ambiguities present in current standard notations. [claim:clm_055]
The paper appeared in Onward! 2022 (ACM SIGPLAN SPLASH), pages 48-62, published 01 December 2022, as an open-access research article. [claim:clm_056]

### KnitWit design spec (project seed)

The spec defines a 4-level 3D ambition ladder: L0 2D+counters+highlighting, L1 structural 3D preview (stitch graph/mesh approximation), L2 editable 3D with consistent stitch semantics, L3 3D object to pattern synthesis. [claim:clm_033]
The spec defines a four-level 3D capability ladder: L0 = 2D + counters + highlighting, L1 = structural 3D preview (stitch graph/mesh approximation), L2 = editable 3D with consistent stitch semantics, L3 = 3D object to pattern synthesis. [claim:clm_065]
The spec recommends 'structural geometry' 3D (stitches as a connected graph/surface with thickness, textured to suggest yarn) rather than yarn-level physics, to deliver preview/assembly utility 'without melting phones'. [claim:clm_034]
The spec recommends the first '3D' be structural geometry (stitches as a connected graph/surface with thickness, textured to suggest yarn) rather than yarn-level physics, to deliver preview and assembly utility 'without melting phones.'. [claim:clm_066]
The spec specifies a Crochet IR with units (US/UK, gauge, hook, yarn weight), pieces[], rows[] as stitch ops with counts (sc x6, inc, dec, repeat), constraints (expected end-of-row count, checkpoints), and assembly/placement markers. [claim:clm_035]
The spec sketches a Crochet intermediate representation with units (US/UK, gauge, hook, yarn weight), pieces[], rows[] of stitch ops with counts (sc x6, inc, dec, repeat), constraints (expected end-of-row counts, checkpoints), and assembly/placement markers, mapping each stitch to a node/edge with spatial placement rules. [claim:clm_067]
The spec cites CrochetPARADE, a 2025 EG paper on force-directed graph layout for crochet, and a peer-reviewed ACM paper on computational amigurumi pattern generation as credible non-physics 3D paths. [claim:clm_068]
The spec identifies a 'Ghost next row' transparent overlay as very doable in 2D now and later in 3D, positioned within the highest-ROI pattern playback feature. [claim:clm_069]
The spec names market incumbents Ribblr (interactive ePatterns) and My Row Counter (imports PDFs/webpages/videos, multi-counter, Ravelry integration), and notes there is historically no official native Ravelry app. [claim:clm_036]
The spec flags pattern IP/copyright as the #1 business landmine and parsing ambiguity (inconsistent abbreviations/formatting/charts) as a core technical risk. [claim:clm_037]
The spec positions reverse 3D-to-pattern as a Phase 3 capability that is computationally grounded (citing peer-reviewed amigurumi generation) but warns 'looks like the model' does not equal pleasant/stable to crochet. [claim:clm_038]
The spec frames reverse 3D-to-pattern generation as a Phase 3 capability with major hurdles: models need watertight meshes and sane topology, stitch size/tension vary per user, and 'looks like the model' does not equal pleasant/stable to crochet. [claim:clm_070]

## Fidelity vs compute comparison

**Inference:** The representation tiers below are ordered from highest visual-fidelity-per-compute-cost to lowest, and the abstract crochet-graph tier is the KnitWit fidelity-vs-mobile-cost sweet spot. [claim:clm_inf02]

| Representation tier | What it encodes | Fidelity / cost | KnitWit fit | Evidence |
|---|---|---|---|---|
| Yarn-level Stitch Meshes | full per-tile yarn geometry + current-loop edge | highest fidelity, highest cost | **Inference:** too heavy for interactive mobile | [claim:clm_inf11] |
| Neighbor-aware mesh relaxation | neighbor-aware per-stitch material properties | mid fidelity, data-fit cost | research-grade, knit-focused | [claim:clm_013] |
| Abstract crochet-graph embedding (AmiGo) | stitch heads/bases/stems only, no yarn-level | structural fidelity, low cost | fidelity-vs-mobile sweet spot | [claim:clm_004] |
| Force-directed graph layout | soft-energy layout of pattern graph | structural, less deterministic | **Inference:** local-minima instability risk | [claim:clm_inf07] |

## Shaping algorithm: round-by-round stitch counts to global shape

**Inference:** This section derives the recommended forward shaping pipeline (repeat expansion, stitch-graph construction, constrained embedding) and traces its curvature basis to cited sources. [claim:clm_inf06]

Single crochet is an approximately square stitch, so a stitch cover is equivalent to a constant-edge-length unit-square quad remesh of the surface. [claim:clm_058]
A square-stitch cover is impossible on non-developable (nonzero Gaussian curvature) surfaces, so curvature must be accommodated by local increase and decrease stitches. [claim:clm_059]
**Inference:** A round-by-round inc/dec schedule is functionally a discrete Gaussian-curvature specification: constant stitch count yields zero curvature (tube/cylinder), net increases yield positive curvature (sphere/cap growth), and net decreases yield closure/negative regions - so shaping global form reduces to placing curvature via stitch-count deltas. [claim:clm_inf05]
Rows correspond to geodesic isolines from the seed and amigurumi are worked in the round at near-constant row height, so each stitch in a row is equidistant to the seed. [claim:clm_071]
Vertical (column) edges of the crochet graph are chosen by solving an optimization that minimizes the total length of the vertical edges. [claim:clm_073]
The 3D preview is produced by a constrained embedding that fixes the seed, constrains SC/row edge lengths to a fixed width, and requires smoothness, yielding a result very similar to the crocheted output without physical simulation. [claim:clm_076]
**Inference:** Recommended forward shaping pipeline for the KnitWit engine: (1) expand IR repeats to explicit per-stitch ops, (2) build a stitch graph with intra-round row edges and inter-round column edges, (3) solve a constrained embedding that fixes the seed, constrains row/column edge lengths to the stitch width, and enforces smoothness - i.e. AmiGo's ShapeUp preview recipe applied directly to an IR-derived graph. [claim:clm_inf06]
**Inference:** AmiGo's constrained-optimization embedding (fixed seed + edge-length constraints + smoothness) should be preferred over a pure force-directed layout for the model-at-round-N preview, because force-directed layouts are prone to local-minima instability - exactly the 'graph layout is unstable' condition the spec names as a G3 failure. [claim:clm_inf07]
Crater regions of positive Gaussian and negative mean curvature are unrealizable under maximal stuffing and are removed by pre-inflating the model, while saddle regions use fewer stitches via adapted sampling. [claim:clm_074]
**Inference:** The dominant shape-fidelity failure mode is 'craters' (positive Gaussian + negative mean curvature), which are physically unrealizable under maximal stuffing; a forward preview that renders such regions as clean geometry will actively mislead users, so the engine must detect and flag (or pre-inflate) them rather than silently smooth. [claim:clm_inf08]
Creases are reproduced by switching to Back-Loop-Only / Front-Loop-Only stitches where maximal absolute curvature is high and orthogonal to the crocheting direction. [claim:clm_075]
The method joins-and-turns at each round rather than spiraling to avoid stitch slanting incompatible with the shortest-vertical-edge optimization. [claim:clm_077]

## Per-stitch progressive-construction rendering

This section specifies how to render construction progressively with stable per-stitch identity.

To adapt stitch meshes to crochet, a special edge type captures the 'current loop' - the loop of yarn held on the hook during fabrication - which is the yarn-level basis for true per-stitch V-stitch geometry. [claim:clm_048]
The stitch-mesh approach carries full per-tile yarn geometry via a library of mesh face types modeling common crochet stitches. [claim:clm_049]
**Inference:** True per-stitch V-stitch geometry requires yarn-level tile meshes (Stitch Meshes' 'current loop' edge and mesh-face library), which is too heavy for interactive mobile; a cheaper equivalent is instanced low-poly/textured stitch glyphs per graph node that suggest yarn - recommended for KnitWit's on-device layer. [claim:clm_inf11]
Stitch locations follow from cutting and flattening the model into row-number (vertical) and stitch-number (horizontal) coordinates, giving every stitch a natural index. [claim:clm_072]
The spec's Crochet IR indexes pieces[], rounds[], and per-round stitch ops with expected end-of-row counts and checkpoints. [claim:clm_035]
**Inference:** Model-at-round-N and current-stitch highlighting reduce to a graph-visibility filter: give every stitch a stable (piece_id, round_index, stitch_index) triple derived from IR position, then render round N = the subgraph with round_index <= N and the current-stitch highlight = the single node at (N, k) - no re-computation needed. [claim:clm_inf09]
The spec identifies a 'Ghost next row' transparent overlay as very doable in 2D now and later in 3D, within the highest-ROI pattern playback feature. [claim:clm_069]
**Inference:** Ghost-next-row overlay and current-round highlighting are low-risk and should ship first on the shared 2D stitch graph (L0), reusing the same node metadata that later drives the 3D embedding, so highlighting logic is authored once and inherited by L1. [claim:clm_inf10]

## On-device vs server placement verdict

**Inference:** This section states the on-device/server placement verdict, drawing the boundary at the embedding solve with mesh/compute budget reasoning. [claim:clm_inf13]

All CrochetPARADE calculations run locally on the user's device with no server or internet transmission, a direct precedent for client-side rendering feasibility. [claim:clm_016]
The platform can be sluggish on old hardware, and patterns of tens of thousands of stitches can take minutes or more to calculate. [claim:clm_017]
A very fine stitch size explodes stitch count and can hit WebAssembly memory limits in the browser, requiring a larger stitch size or the desktop build. [claim:clm_025]
AmiGo reports pattern-generation times of a few minutes, indicating the solve is a one-time non-interactive cost. [claim:clm_064]
**Inference:** CrochetPARADE is the decisive precedent that stitch-level crochet rendering can run fully client-side (no server), but its own README shows the embedding/relaxation step - not rendering - is the bottleneck: tens-of-thousands-of-stitch models take minutes and can exhaust WebAssembly memory. [claim:clm_inf12]
**Inference:** The on-device/server boundary should be drawn at the embedding solve, not the render: precompute the stitch-graph positions once (at pattern import, on-device for small pieces or server-side/cached for pieces beyond a few thousand stitches) and do only interactive rendering, round reveal, and highlighting on-device with Metal. [claim:clm_inf13]
**Inference:** Rendering is not the mobile constraint: a typical amigurumi of a few hundred to a few thousand stitches maps to that many instanced glyphs (order 10^5-10^6 triangles at low-poly), comfortably within iPhone Metal budgets; therefore the compute-bound relaxation, not the draw, is what must be moved off the interactive path. [claim:clm_inf14]

## Academic feasibility vs product readiness

This section separates capabilities shown in research from capabilities ready for an amigurumi-first mobile product.

**Inference:** On the academic-feasibility vs product-readiness line: AmiGo, Stitch Meshes, and neighbor-aware relaxation are research demos (gated papers, no mobile/Swift implementation), while CrochetPARADE is the only product-adjacent artifact (shipping, client-side, exporting) - but none is a drop-in amigurumi-mobile solution. [claim:clm_inf15]
CrochetPARADE is a shipping open-source platform that runs locally and exports chart, SVG, and 3D files, placing pattern->3D forward simulation on the product-adjacent side. [claim:clm_019]
Digital Crochet remains a research prototype editor validated only by a user study, not a shipped product. [claim:clm_054]
The Digital Crochet user study showed the language expresses both 2D and 3D patterns and removes notation ambiguity, which is academic-feasibility evidence rather than product proof. [claim:clm_055]
Reverse 3D-to-pattern is positioned as a computationally grounded Phase 3 capability, but the spec warns 'looks like the model' does not equal pleasant/stable to crochet, so it is not product-ready. [claim:clm_038]
VLM performance collapses from surface-level similarity to executable correctness, so learned pattern generation is not yet reliable enough for product use. [claim:clm_031]
The core unsolved problem is framed as the gap between surface-level understanding and executable precision in real-world creative domains. [claim:clm_032]

## Contradictions & open disagreements

**Inference:** There is a direct capability contradiction: CrochetPARADE's Remesher is reported to handle non-watertight STLs with holes, whereas AmiGo strictly requires a closed manifold mesh; the likely resolution is that the Remesher's frontier-growth-with-zips treats open boundaries as edges to grow toward while AmiGo's geodesic-isoline formulation needs a closed surface - decision impact medium, relevant only if/when mesh->pattern is built. [claim:clm_inf18]
The Remesher admin follow-up claims round-based instructions for non-watertight STLs with holes/openings. [claim:clm_027]
AmiGo's formal input requires a closed manifold triangle mesh, seed vertex, and stitch width. [claim:clm_057]

## Risks

The rows below name risk-relevant findings with severity, likelihood, and one mitigation each; forward-looking risk rows carry an inference/speculation label.

| Risk | Category | Severity | Likelihood | Mitigation | Evidence |
|---|---|---|---|---|---|
| Pattern IP/copyright is the #1 business landmine and parsing ambiguity is a core technical risk | legal / technical | high | high | license-gated ingestion + structured-IR-only import | [claim:clm_037] |
| **Inference:** Forking CrochetPARADE's GPLv3 code would force the closed-source iOS app open | legal | high | high (if forked) | independently reimplement the public-domain grammar and forward simulator | [claim:clm_inf16] |
| **Inference:** A preview that renders crater regions as clean geometry misleads users about crochetability | ux / trust | high | medium | detect and flag (or pre-inflate) crater regions rather than silently smooth | [claim:clm_inf08] |
| **Inference:** The embedding/relaxation solve is the compute bottleneck (minutes, WASM memory limits) | performance / cost | high | medium | move the cacheable solve off the interactive path (precompute/server for large pieces) | [claim:clm_inf12] |
| Generated patterns that 'look like the model' are not guaranteed pleasant or stable to crochet | product / generation | high | medium | keep generation behind IR + human-controllable knobs, defer to Phase 3 | [claim:clm_070] |
| VLM procedural synthesis collapses on executable correctness | model / accuracy | high | high | do not rely on VLMs for compilable pattern generation without execution validation | [claim:clm_031] |
| **Speculation:** Reverse mesh->pattern will remain the product's weakest link | product | high | medium | defer behind pattern->3D + IR until forward path is proven | [claim:clm_spec02] |

## Prototype experiments & decision-gate relevance

This section maps findings to decision gates G1-G5 and the named prototype experiment backlog.

| Gate | Question it answers | Finding that de-risks it | Evidence |
|---|---|---|---|
| G1 Evidence Quality | Is the evidence base sound? | **Inference:** three independent sources converge on geometric-only object recognizability | [claim:clm_inf01] |
| G2 Crochet-IR Viability | Can the IR represent basic amigurumi? | **Inference:** adopt IR v0.1 as-is plus stable id and shape_role<->curvature mapping | [claim:clm_inf17] |
| G3 Pattern-to-3D Viability | Does structural preview render usefully? | **Speculation:** EXP-005 sphere+cylinder embedding is the highest-value greenlight test | [claim:clm_spec01] |
| G4 Mesh-to-Pattern Primitive | Can simple meshes yield crochetable patterns? | **Speculation:** mesh->pattern stays weakest and should be deferred | [claim:clm_spec02] |
| G5 MVP Recommendation | What is the buildable MVP path? | **Inference:** adopt a written-pattern-in forward engine for L1 | [claim:clm_inf04] |

**Speculation:** The single highest-value G3 de-risking experiment is EXP-005 (stitch-graph -> approximate 3D) on a 6-sc magic-ring sphere and a plain cylinder using AmiGo's constrained-embedding recipe; if these embed to a recognizable ball and tube with stable round highlighting, L1 is greenlit - and this is more likely than not to succeed given three sources already report geometric embedding matching real objects. [claim:clm_spec01]
**Inference:** EXP-004 (IR->stitch-graph) followed by EXP-005 implement the recommended forward shaping pipeline of repeat-expansion, graph construction, and constrained embedding. [claim:clm_inf06]
**Inference:** EXP-006 (row-highlight export) reduces to attaching the stable (piece_id, round_index, stitch_index) triple and filtering the graph, requiring no re-computation. [claim:clm_inf09]
**Inference:** EXP-001 (IR hello-world), EXP-002 (stitch-count validator), and EXP-003 (repeat expansion) validate the Crochet IR v0.1 baseline needed to pass G2. [claim:clm_inf17]
**Inference:** Ghost-next-row and current-round highlighting should ship first at L0 on the shared 2D stitch graph before the L1 EXP-005 embedding work. [claim:clm_inf10]
**Speculation:** The mesh->pattern experiments EXP-008 (primitive-mesh->rounds), EXP-009 (mesh-pattern->IR), and EXP-010 (round-trip evaluator) should stay deferred behind the forward path. [claim:clm_spec02]

## Recommendations / decision rules

**Inference:** For KnitWit's L1 structural preview, adopt a written-pattern-in engine (Greer-Mould force-directed layout or an independently reimplemented CrochetPARADE-style forward simulator) rather than AmiGo or the Remesher, which require a mesh input the app will not have during pattern playback. [claim:clm_inf04]
The first '3D' should be structural geometry (a connected graph/surface with thickness, textured to suggest yarn) rather than yarn-level physics, to deliver preview and assembly utility without melting phones. [claim:clm_066]
**Inference:** Use AmiGo's ShapeUp-style constrained embedding on an IR-derived stitch graph as the shaping engine, preferring it over pure force-directed layout for determinism. [claim:clm_inf07]
**Inference:** Render per-stitch appearance with instanced low-poly textured glyphs per graph node rather than yarn-level tile meshes. [claim:clm_inf11]
**Inference:** Draw the on-device/server boundary at the embedding solve: precompute stitch-graph positions once, then keep only interactive rendering, round reveal, and highlighting on-device with Metal. [claim:clm_inf13]
**Inference:** Adopt the Crochet IR v0.1 starter schema as-is for gate G2, adding a stable per-stitch id field and an explicit shape_role<->curvature mapping. [claim:clm_inf17]
**Inference:** Do not fork CrochetPARADE's GPLv3 code; independently reimplement the public-domain grammar and forward simulator to keep the iOS app closed-source. [claim:clm_inf16]
**Speculation:** Defer reverse mesh->pattern generation behind a proven pattern->3D + IR path. [claim:clm_spec02]

## Open questions

- Does AmiGo's constrained embedding remain stable and interactive on iPhone-class Metal hardware for a few-thousand-stitch amigurumi, or must the solve always be precomputed/server-side?
- At what stitch-count threshold should the embedding solve move from on-device to server or cache?
- Can spiral (non-turning) construction be embedded without the stitch-slanting artifact that AmiGo's join-and-turn approach avoids?
- What per-stitch triangle budget and glyph level-of-detail keep a fully assembled multi-piece character within interactive Metal frame budgets?
- Does the public-domain CrochetPARADE grammar cover amigurumi round/inc/dec constructs completely enough to reimplement a forward simulator without touching the GPLv3 code?
- How should the engine surface crater/unrealizable regions to users so the preview stays trustworthy rather than misleading?

## Sources

- src_20260710_stitch3d_11: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260710_stitch3d_08: Neighbor-Aware Data-Driven Relaxation of Stitch Mesh Models for Knits
- src_20260710_stitch3d_03: CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger)
- src_20260710_stitch3d_09: CrochetPARADE Remesher: Turn a 3D Model Into Crochet Instructions
- src_20260710_stitch3d_04: CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260710_stitch3d_06: KnitWit Design Spec (project seed)
- src_20260710_stitch3d_05: Modeling Crochet Patterns with a Force-directed Graph Layout
- src_20260710_stitch3d_00: Representing Crochet with Stitch Meshes
- src_20260710_stitch3d_02: Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260710_stitch3d_01: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260710_stitch3d_10: KnitWit design-spec.md (project seed, ChatGPT 5.2)
- src_20260710_stitch3d_07: Amigurumi Crochet Patterns from Geodesic Distances
