---
id: mwb_20260614_knitwit_b4_deterministic_mesh_to_amigurumi
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_is_the
target_page: meatywiki/sources/knitwit_b4_deterministic_mesh_to_amigurumi.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_is_the_most_reproducible_deterministic:
  82 supported claim(s) across 12 source card(s).'
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
links:
  source_cards:
  - src_20260614_kw006_00
  - src_20260614_kw006_01
  - src_20260614_kw006_02
  - src_20260614_kw006_03
  - src_20260614_kw006_04
  - src_20260614_kw006_05
  - src_20260614_kw006_06
  - src_20260614_kw006_07
  - src_20260614_kw006_08
  - src_20260614_kw006_09
  - src_20260614_kw006_10
  - src_20260614_kw006_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# KnitWit B4: Deterministic Mesh-to-Amigurumi Pattern Synthesis - Method Reproduction, Crochetability Constraints, and the Reproduce-vs-Heuristic-vs-ML Decision

## Summary

Source note distilled from research run rf_run_20260614_what_is_the_most_reproducible_deterministic: 82 supported claim(s) across 12 source card(s).

## Key claims

- The paper is openly available on arXiv as 2211.01178 with DOI 10.48550/arXiv.2211.01178 under a CC BY-NC-SA 4.0 license, with both PDF and TeX source downloadable. [claim:clm_001]
- AmiGo frames amigurumi pattern creation as the inverse problem of generating human-executable crochet instructions from an input 3D model. [claim:clm_002]
- The only required geometric inputs are a closed triangle mesh and a single user-specified point, from which a toy approximating the input geometry is produced. [claim:clm_003]
- The method works by constructing the geometry and connectivity of a Crochet Graph, which is then translated into the final crochet pattern. [claim:clm_004]
- The shape is automatically segmented into crochetable components that are joined using the join-as-you-go method, eliminating the need for additional sewing. [claim:clm_005]
- The authors report the method generalizes across a wide variety of shapes and yields easily crochetable patterns; the paper is 11 pages with 10 figures (SCF 2022). [claim:clm_006]
- The report's recommended inverse baseline, 'Amigurumi Graph Lite' (Geodesic Row Planner), generates rows around a chosen seed axis and sets each row's stitch count from the mesh circumference at that height versus gauge, deliberately de-scoping AmiGo by handling only single-part convex meshes first. [claim:clm_007]
- The report states a concrete crochetability heuristic: keep each row's stitch count within +/-1 of the smooth ratio, insert increases evenly, and never grow more than about 2x stitches from one round to the next (ideally less), flagging regions that would need a sudden large increase for segmentation. [claim:clm_008]
- The report documents a deterministic geometry-mapping family (AmiGo-style: trace a continuous geodesic/iso-curve path that spirals around the shape, inserting increases on positive curvature and decreases on negative curvature) as distinct from the other inverse families it catalogs. [claim:clm_009]
- The report's inverse-mapping taxonomy enumerates four families with capability matrices: deterministic geometry mapping (AmiGo / Capunaman NURBS-UV), shape templates and segmentation / primitives (Nakjan sketch-to-primitive, Crochet Lathe), optimization and constraint-solving, and ML-assisted pipelines. [claim:clm_010]
- The report flags that for surfaces of revolution the inverse mapping is essentially a solved problem analytically, supporting symmetric shapes as the lowest-risk first milestone. [claim:clm_011]
- The report notes AmiGo-style general-mesh inverse mapping is higher risk: no public code, implemented in Matlab/C++, and reported running times of seconds to minutes (not real-time). [claim:clm_012]
- The report identifies a top de-risk experiment defining a max-curvature / rate-of-increase threshold: a shape feature forcing roughly a >50% single-round increase is treated as not reliably crochetable and must be segmented. [claim:clm_013]
- The report names seed/seam placement effect on pattern symmetry, and round-trippability of a generated pattern back through the forward visualizer/validator, as key open de-risk experiments for the inverse pipeline. [claim:clm_014]
- The algorithm requires a UV-parameterized surface as input, deriving stitch direction and connectivity from the surface's parameter directions rather than from a single seed point. [claim:clm_015]
- Because the platform (Grasshopper for Rhino) evaluates NURBS, the method relies on NURBS UV division to transfer a 3D geometry into a crochet pattern. [claim:clm_016]
- The crafter's hand effect (grip on the yarn) is captured empirically through six different physical 10-by-10-stitch tension swatches crocheted before running the algorithm. [claim:clm_017]
- Gauge variables are split into determinate inputs (yarn weight, hook size) and an indeterminate input — the crafter's grip on the yarn — which the swatch is used to measure. [claim:clm_018]
- The work formalizes crochet of non-symmetrical 3D objects as a computer algorithm whose output is a conventional, human-readable text crochet pattern, going beyond axially symmetric revolved surfaces (sphere, cylinder, cone, ellipsoid). [claim:clm_019]
- The study has two stages — an analytical systematic approach to crocheting 3D objects to discover the underlying computational aspects, then a formal representation of that logic as a computer algorithm. [claim:clm_020]
- The project is licensed under AGPL-3.0, a strong copyleft license that constrains embedding its code in a closed-source commercial mobile app. [claim:clm_021]
- The codebase is implemented entirely in Sage (reported as 100% of the repository's languages), designed to run in the CoCalc environment. [claim:clm_022]
- The tool is run by opening a Sage worksheet ('Crocheting Surfaces of Revolution') inside CoCalc rather than as a standalone or mobile application. [claim:clm_023]
- Inputs are a function f(x), interval bounds a and b, stitch gauge S, row gauge R, and a scale, and the chosen function must be strictly positive on (a,b). [claim:clm_024]
- The function must also have a defined derivative on the closed interval [a,b], a smoothness precondition on permitted inputs. [claim:clm_025]
- Outputs are a set of crochet instructions plus a list of coordinates per row and a plot of the function with dots marking where each crochet row aligns to the profile curve. [claim:clm_026]
- Scope is limited to mathematical surfaces of revolution, always rotating the given function about the x-axis, with no support for arbitrary meshes or branching. [claim:clm_027]
- AmiGo takes a closed triangle mesh M=(V,E), a seed vertex s, and a stitch width w as input, and only handles closed surfaces because amigurumi are stuffed. [claim:clm_028]
- The row function is the geodesic distance f(v)=d(v,s) computed via the Heat Method with diffusion time t set to the average edge length squared. [claim:clm_029]
- The column function g is found by minimizing the integral of |<J grad f, grad g> - 1|^2 subject to g=0 on the longest boundary path B along which f is strictly monotone. [claim:clm_030]
- Consecutive rows of the crochet graph G=(S, R union C) must be coupled, and a minimal coupling is computed by Dynamic Time Warping minimizing the summed inter-vertex distance. [claim:clm_031]
- A transducer over two coupled rows emits single crochet, decrease dec(x), or increase inc(x) based on how many vertices connect to a head; the paper states no explicit numeric cap on inc/dec rate. [claim:clm_032]
- Regions of negative mean curvature with positive Gaussian curvature cannot be realized by crocheting and stuffing alone, and are preprocessed with Conformal Mean Curvature Flow until mean curvature is positive everywhere. [claim:clm_033]
- AmiGo is implemented in Matlab and C++ using Heat Geodesics, geodesic paths, and ShapeUp; the Teddy example yields 60 rows, 6 segments, and 3670 stitches in 2.5 minutes, with no code or data release stated. [claim:clm_034]
- The framework is a parametric model that generates crochet patterns for NURBS surfaces using a 10-stitches-by-10-rows tension swatch to calibrate the digital-to-physical mapping. [claim:clm_035]
- The generated crochet patterns are text-based, step-by-step representations explicitly analogized to g-code in additive manufacturing, serving documentation and communication of the crocheting process. [claim:clm_036]
- The method extends to branching geometries by decomposing a parametric form into multiple components that can be crocheted by multiple crafters. [claim:clm_037]
- As proof of concept, a branching structure of 14 unique components was designed and crocheted by two architecture students at Pennsylvania State University, each completing 7 components. [claim:clm_038]
- Per-crafter tension swatches capture individual gauge variables, so different users can crochet different components while preserving the digitally designed geometry and dimensional accuracy. [claim:clm_039]
- The authors frame the approach as enabling a collective, distributed crocheting platform and an alternative path for transitioning from the digital to the physical. [claim:clm_040]
- The program's inputs are a function f(x) (positive on (a,b), with f'(x) defined on [a,b]) rotated about the x-axis, x-bounds a and b, stitch gauge S (stitches per 4 in), row gauge R (rows per 4 in), and a scale (inches per unit), confining scope to axially symmetric shapes. [claim:clm_041]
- Row landmarks are placed by dividing the total arclength, computed as L = (scale*R/4) * integral_a^b sqrt(1 + (f'(x))^2) dx (measured in rows), with the worked example yielding L ~= 16.162 rows. [claim:clm_042]
- Each row landmark x_i is found by solving the cumulative-arclength equation with a 'guess and check' protocol accurate to two decimal places, always measuring arclength from x0 = a to mitigate rounding error. [claim:clm_043]
- Stitch count per row is deterministic: s(i) = round(2*pi * scale * (S/4) * f(x_i)), i.e., the circumference at that height times the stitch gauge. [claim:clm_044]
- The program flags an error at the top of the pattern when the stitch count between rows more than doubles or more than halves (so Inc/Dec cannot accomplish the move), and recommends adding a positive constant to f(x) or changing scale/multiplying the function. [claim:clm_045]
- Output is standard human crochet notation with per-row counts and totals; the worked example f(x)=x^3+2x^2-2x+4 over [-3,1], S=22, R=25, scale=0.18 produces rows 0-16 (17 rows) with stitch counts ranging from 6 up to 51 and back to 31. [claim:clm_046]
- The code is published and runnable: written in a Sage worksheet, freely accessible via CoCalc, with the source in the GitHub repository github.com/meganmartinez/math_crochet. [claim:clm_047]
- The method takes a written crochet pattern as input, translates it into a graph, and computes a force-directed graph layout to produce a 3D representation matching the hand-crocheted object in shape and size. [claim:clm_048]
- The digital preview lets a designer adjust a pattern from the model without physically crocheting it, removing the manual crochet/modify/redo iteration loop. [claim:clm_049]
- Conventional crochet pattern design is iterative and wasteful: a pattern is crocheted, evaluated, then stitches are undone and remade across multiple guesswork-heavy iterations involving manual labor. [claim:clm_050]
- The tool targets both professional designers and beginners, helping designers visualize a pattern before investing time and effort to physically make it. [claim:clm_051]
- The modeling tool consumes patterns written in row-by-stitch notation, the most common notation for amigurumi, and represents each graph node as a sphere so the user can see individual stitches. [claim:clm_052]
- The paper is a 2025 Eurographics primary source (Expressive Symposium / WICED 2025, DOI 10.2312/exw.20251057, ISBN 978-3-03868-271-4), published open-access by The Eurographics Association. [claim:clm_053]
- Prior crochet-from-shape tools are constrained: Nakjan et al. let users trace 2D shapes converted to 3D and then to a pattern but are limited to relatively symmetrical shapes such as spheres and cylinders. [claim:clm_054]
- AmiGo takes a closed triangle mesh plus a single user-specified point as input and outputs crochet instructions that, when crocheted and stuffed, approximate the input geometry. [claim:clm_055]
- The method's core representation is a 'Crochet Graph' whose geometry and connectivity are constructed and then translated into a human-crochetable pattern. [claim:clm_056]
- The shape is segmented automatically into crochetable components that are joined with the 'join-as-you-go' method, eliminating any additional sewing. [claim:clm_057]
- Segmentation iterates over saddle points: for each saddle, the isoline of the geodesic field is computed and a new segment is sliced for each resulting connected component. [claim:clm_058]
- The order in which the segments are crocheted is fixed by a topological sort of the directed segment adjacency graph. [claim:clm_059]
- The authors demonstrate the pipeline across a large variety of shapes and report that it yields easily crochetable patterns. [claim:clm_060]
- The AmiGo paper is 'AmiGo: Computational Design of Amigurumi Crochet Patterns' by Michal Edelstein, Hila Peleg, Shachar Itzhaky and Mirela Ben-Chen, published at the Symposium on Computational Fabrication (SCF) 2022. [claim:clm_061]
- The official AmiGo entry exposes only two artifact links -- the paper PDF and the arXiv page -- with the canonical PDF hosted at mirelabc.github.io/publications/AmiGo_lores.pdf. [claim:clm_062]
- Other entries on the same page DO carry code releases -- e.g. the PH-CPF entry links [code] (with a replicability stamp), supplemental, and presentation -- showing the AmiGo entry's omission of a [code] link reflects that AmiGo's code/data are not publicly released, not a page-wide convention. [claim:clm_063]
- The same group published a follow-up short paper, 'Amigurumi Crochet Patterns from Geodesic Distances' by Mirela Ben-Chen and Michal Edelstein, at Bridges 2024. [claim:clm_064]
- The same group authored 'A Convex Optimization Framework for Regularized Geodesic Distances' (Edelstein, Guillen, Solomon, Ben-Chen) at SIGGRAPH 2023, the regularized-geodesic-distance machinery underpinning the AmiGo row function. [claim:clm_065]
- The page is the official publications listing of Mirela Ben-Chen at the Center for Graphics and Geometric Computing, CS, Technion, confirming the affiliation and the authoritative artifact location for the AmiGo (B1) anchor. [claim:clm_066]
- The autoknit codebase is placed in the public domain, making its pipeline and intermediate formats reusable for IP-safe work. [claim:clm_067]
- autoknit is an open re-implementation of the paper 'Automatic Machine Knitting of 3D Meshes' that does not exactly match the paper's original code. [claim:clm_068]
- Inputs are an OBJ mesh plus user-defined constraints: the interface loads an .obj model and saves user-marked boundary/direction constraints to a .cons file. [claim:clm_069]
- Constraints must cover all boundaries and can additionally be placed to control knitting direction, with a region-cut option for meshes without boundaries. [claim:clm_070]
- Stitch geometry is parameterized by obj-scale, stitch-width, and stitch-height, giving stitch size relative to the scaled object. [claim:clm_071]
- The pipeline runs Constraints -> Peeling/Linking -> Scheduling -> Knitout with a distinct intermediate file format per stage: .cons constraints, .st traced stitches, .js scheduling/javascript, and .k knitout. [claim:clm_072]
- Peeling/Linking converts the mesh into a row-column graph, and the implementation is described as mostly working for peeling/tracing with working linking. [claim:clm_073]
- Scheduling is a concrete maturity caveat: it works for small cases only and lacks a greedy fallback (only the optimal search is implemented). [claim:clm_074]
- The core method computes geodesic distance on the surface from a seed point, then samples the equidistant curves non-uniformly under curvature guidance, with mean curvature at crease lines selecting stitch types. [claim:clm_075]
- This Bridges 2024 short paper is positioned as a brief introduction to the authors' fuller SCF publication 'AmiGo: Computational Design of Amigurumi Crochet Patterns.' [claim:clm_076]
- Because amigurumi are crocheted in the round from a starting circle with constant row height equal to a single-crochet (SC) stitch width, every stitch in a row is equidistant from the start, making surface geodesic distance the natural model for crochet rows. [claim:clm_077]
- Equidistant curves spaced by the stitch height define the pattern rows; stitch locations are computed by flattening the model (vertical = distance from seed/row number, horizontal = distance along the curve/stitch number) and evenly sampling, then mapping points back to form the crochet graph. [claim:clm_078]
- Saddle-like regions (negative Gaussian and mean curvature) trigger reduced stitch counts in the row sampling, while creases are reproduced via BLO/FLO stitches applied where maximal absolute curvature is high and its direction is orthogonal to the crocheting direction; both adaptations are automatic. [claim:clm_079]
- Models with 'craters' (negative mean curvature and positive Gaussian curvature) are not realizable as maximally-stuffed crochet, so the input is pre-processed by 'inflating' it to remove craters before pattern generation. [claim:clm_080]
- Multi-component equidistant curves (e.g., a two-legged human-like model seeded at the head) require partitioning the model into separately-crochetable parts with pick-up connection instructions, and assembly is seamless with no sewing. [claim:clm_081]
- The authors acknowledge results do not look like classic amigurumi because they join-and-turn each round (to avoid spiral slanting incompatible with their shortest-vertical-edge optimization), and plan future support for spiral crocheting, higher stitches, color, and yarn-quantity reporting. [claim:clm_082]

## Sources

- src_20260614_kw006_00 — AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw006_01 — AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw006_02 — AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw006_03 — Mirela Ben-Chen Publications (Center for Graphics and Geometric Computing, Technion)
- src_20260614_kw006_04 — Amigurumi Crochet Patterns from Geodesic Distances
- src_20260614_kw006_05 — Computing Stitches and Crocheting Geometry
- src_20260614_kw006_06 — From Stitches to Digits and Back: Computational Crocheting of Branching Geometries
- src_20260614_kw006_07 — Automating Crochet Patterns for Surfaces of Revolution
- src_20260614_kw006_08 — math_crochet - surfaces-of-revolution crochet generator (reference implementation)
- src_20260614_kw006_09 — KnitWit B1 Workstream Report (project prior-art synthesis)
- src_20260614_kw006_10 — autoknit: a re-implementation of "Automatic Machine Knitting of 3D Meshes"
- src_20260614_kw006_11 — Modeling Crochet Patterns with a Force-directed Graph Layout

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
