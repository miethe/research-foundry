---
id: mwb_20260711_stitch_level_3d_crochet_rendering_fidelity
evidence_bundle_id: bundle_20260711_intent_research_20260710_stitch_level_3d
target_page: meatywiki/sources/stitch_level_3d_crochet_rendering_fidelity.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260710_stitch_level_3d_crochet_rendering_fidelity_caec:
  77 supported claim(s) across 12 source card(s).'
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
links:
  source_cards:
  - src_20260710_stitch3d_00
  - src_20260710_stitch3d_01
  - src_20260710_stitch3d_02
  - src_20260710_stitch3d_03
  - src_20260710_stitch3d_04
  - src_20260710_stitch3d_05
  - src_20260710_stitch3d_06
  - src_20260710_stitch3d_07
  - src_20260710_stitch3d_08
  - src_20260710_stitch3d_09
  - src_20260710_stitch3d_10
  - src_20260710_stitch3d_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Stitch-Level 3D Crochet Rendering Fidelity for KnitWit/LoopNest: Reconstruction Techniques, Shaping Algorithms, Progressive Guides, and On-Device vs Server Placement

## Summary

Source note distilled from research run rf_run_20260710_stitch_level_3d_crochet_rendering_fidelity_caec: 77 supported claim(s) across 12 source card(s).

## Key claims

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

## Sources

- src_20260710_stitch3d_00 — Representing Crochet with Stitch Meshes
- src_20260710_stitch3d_01 — AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260710_stitch3d_02 — Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260710_stitch3d_03 — CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger)
- src_20260710_stitch3d_04 — CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260710_stitch3d_05 — Modeling Crochet Patterns with a Force-directed Graph Layout
- src_20260710_stitch3d_06 — KnitWit Design Spec (project seed)
- src_20260710_stitch3d_07 — Amigurumi Crochet Patterns from Geodesic Distances
- src_20260710_stitch3d_08 — Neighbor-Aware Data-Driven Relaxation of Stitch Mesh Models for Knits
- src_20260710_stitch3d_09 — CrochetPARADE Remesher: Turn a 3D Model Into Crochet Instructions
- src_20260710_stitch3d_10 — KnitWit design-spec.md (project seed, ChatGPT 5.2)
- src_20260710_stitch3d_11 — AmiGo: Computational Design of Amigurumi Crochet Patterns

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
