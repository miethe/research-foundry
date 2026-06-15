---
schema_version: '0.1'
type: research_report
report_id: report_20260614_what_is_the_most_reproducible_deterministic
title: 'KnitWit B4: Deterministic Mesh-to-Amigurumi Pattern Synthesis - Method Reproduction, Crochetability Constraints, and the Reproduce-vs-Heuristic-vs-ML Decision'
intent_id: intent_research_20260614_what_is_the_most_reproducible_deterministic
evidence_bundle_id: pending
created_at: '2026-06-14T22:16:40-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# KnitWit B4: Deterministic Mesh-to-Amigurumi Pattern Synthesis

Technical memo — method reproduction, crochetability constraints, and the reproduce-vs-heuristic-vs-ML decision for the 3D-object-to-pattern generator.

## Executive summary

Among the four candidate methods, only Martinez & Taylor Lipnicki's surfaces-of-revolution generator is end-to-end reproducible today (open AGPL-3.0 Sage code, fully specified deterministic formulas s(i)=round(2*pi*scale*(S/4)*f(x_i)) and arclength row placement), whereas AmiGo, the Capunaman NURBS-UV method, and Crochet Lathe each have at least one reproduction-blocking gap (no released code, a Grasshopper/Rhino dependency, or unspecified internals). **Inference:** [claim:clm_inf01]
For KnitWit's v1 the evidence supports an option (b)+(a) hybrid: ship a heuristic/templated surface-of-revolution generator first (analytically solved, low-risk) and reproduce only the de-scoped AmiGo-style geodesic row planner ('Amigurumi Graph Lite') as the general-mesh path, while option (c) ML-assist is not yet justified by any source in the set. **Inference:** [claim:clm_inf02]
On the academic-feasibility vs product-readiness line, every method in the set is academically demonstrated but none is product-ready for an amigurumi-first mobile app: AmiGo's 2.5-minute Matlab/C++ runtime and unreleased code, Capunaman's desktop Rhino dependency, and math_crochet's Sage/CoCalc worksheet all fail the mobile/offline/closed-source product bar, so KnitWit's v1 deterministic engine must be a fresh mobile-targeted re-implementation of published math, not an integration of any existing artifact. **Inference:** [claim:clm_inf09]
The recommended deterministic pipeline maps cleanly onto Crochet IR v0.1 with one structural caveat: each extracted geodesic row becomes a rounds[] entry whose ops are sc/inc/dec with an expected_stitch_count equal to round(circumference*gauge), and visual_hint.shape_role is set to increase/straight/decrease from the sign of the row-to-row delta; multi-segment shapes become separate pieces[] joined via assembly[] (join-as-you-go), so the only fields the IR lacks natively are BLO/FLO crease stitches and pick-up attachment coordinates. **Inference:** [claim:clm_inf13]

## AmiGo (Edelstein 2022) pipeline reconstruction


AmiGo frames amigurumi pattern creation as the inverse problem of generating human-executable crochet instructions from an input 3D model. [claim:clm_002]
The AmiGo paper is 'AmiGo: Computational Design of Amigurumi Crochet Patterns' by Michal Edelstein, Hila Peleg, Shachar Itzhaky and Mirela Ben-Chen, published at the Symposium on Computational Fabrication (SCF) 2022. [claim:clm_061]
The paper is openly available on arXiv as 2211.01178 with DOI 10.48550/arXiv.2211.01178 under a CC BY-NC-SA 4.0 license, with both PDF and TeX source downloadable. [claim:clm_001]
AmiGo takes a closed triangle mesh M=(V,E), a seed vertex s, and a stitch width w as input, and only handles closed surfaces because amigurumi are stuffed. [claim:clm_028]
The only required geometric inputs are a closed triangle mesh and a single user-specified point, from which a toy approximating the input geometry is produced. [claim:clm_003]
The method works by constructing the geometry and connectivity of a Crochet Graph, which is then translated into the final crochet pattern. [claim:clm_004]
The row function is the geodesic distance f(v)=d(v,s) computed via the Heat Method with diffusion time t set to the average edge length squared. [claim:clm_029]
The column function g is found by minimizing the integral of |<J grad f, grad g> - 1|^2 subject to g=0 on the longest boundary path B along which f is strictly monotone. [claim:clm_030]
Consecutive rows of the crochet graph G=(S, R union C) must be coupled, and a minimal coupling is computed by Dynamic Time Warping minimizing the summed inter-vertex distance. [claim:clm_031]
A transducer over two coupled rows emits single crochet, decrease dec(x), or increase inc(x) based on how many vertices connect to a head; the paper states no explicit numeric cap on inc/dec rate. [claim:clm_032]
Segmentation iterates over saddle points: for each saddle, the isoline of the geodesic field is computed and a new segment is sliced for each resulting connected component. [claim:clm_058]
The order in which the segments are crocheted is fixed by a topological sort of the directed segment adjacency graph. [claim:clm_059]
The shape is automatically segmented into crochetable components that are joined using the join-as-you-go method, eliminating the need for additional sewing. [claim:clm_005]
Regions of negative mean curvature with positive Gaussian curvature cannot be realized by crocheting and stuffing alone, and are preprocessed with Conformal Mean Curvature Flow until mean curvature is positive everywhere. [claim:clm_033]
AmiGo is implemented in Matlab and C++ using Heat Geodesics, geodesic paths, and ShapeUp; the Teddy example yields 60 rows, 6 segments, and 3670 stitches in 2.5 minutes, with no code or data release stated. [claim:clm_034]
The same group authored 'A Convex Optimization Framework for Regularized Geodesic Distances' (Edelstein, Guillen, Solomon, Ben-Chen) at SIGGRAPH 2023, the regularized-geodesic-distance machinery underpinning the AmiGo row function. [claim:clm_065]
The official AmiGo entry exposes only two artifact links -- the paper PDF and the arXiv page -- with the canonical PDF hosted at mirelabc.github.io/publications/AmiGo_lores.pdf. [claim:clm_062]
Other entries on the same page DO carry code releases -- e.g. the PH-CPF entry links [code] (with a replicability stamp), supplemental, and presentation -- showing the AmiGo entry's omission of a [code] link reflects that AmiGo's code/data are not publicly released, not a page-wide convention. [claim:clm_063]

### AmiGo stage-by-stage reproducibility matrix

Mapped stage-by-stage, AmiGo's reproducible-vs-underspecified split is: row function (geodesic distance via Heat Method, t = avg-edge-length^2) is fully specified; column function (least-squares J-gradient minimization) is specified as an objective; segmentation over saddle isolines plus topological-sort ordering is specified; but the DTW coupling parameters, the inc/dec numeric cap, the CMCF inflation stop-criterion beyond 'mean curvature positive everywhere', and all dataset/code are underspecified or unreleased. **Inference:** [claim:clm_inf07]

| Pipeline stage | Specification status | Reproducibility verdict | Evidence |
|----------------|---------------------|-------------------------|----------|
| Input (closed mesh, seed s, stitch width w) | Fully specified | Reproducible | [claim:clm_028] |
| Row function (geodesic distance, Heat Method, t=avg-edge-length^2) | Fully specified with parameter | Reproducible | [claim:clm_029] |
| Column function (least-squares J-gradient objective) | Objective stated | Reproducible objective, tuning underspecified | [claim:clm_030] |
| Row coupling (Dynamic Time Warping) | Objective stated, parameters absent | Underspecified | [claim:clm_031] |
| Instruction transducer (sc/inc(x)/dec(x)) | No explicit numeric inc/dec cap | Underspecified for bounded constraints | [claim:clm_032] |
| Segmentation (saddle isolines) + topological-sort ordering | Fully specified | Reproducible | [claim:clm_058] |
| Curvature repair (CMCF until mean curvature positive) | Qualitative stop-criterion only | Underspecified stop-criterion | [claim:clm_033] |
| Implementation & dataset (Matlab/C++, Teddy: 60 rows, 3670 stitches, 2.5 min) | No code/data release | Not reproducible, no artifact | [claim:clm_034] |

AmiGo is the only source-backed method that gives no explicit numeric inc/dec-rate cap, deriving transitions implicitly from DTW row coupling and the sc/inc(x)/dec(x) transducer; this is the single largest underspecified stage for KnitWit's bounded-constraint goal and must be supplied externally (e.g. by adopting the math_crochet 2x bound) rather than read off AmiGo. **Inference:** [claim:clm_inf06]

### Bridges 2024: the more reproducible row-extraction specification

This Bridges 2024 short paper is positioned as a brief introduction to the authors' fuller SCF publication 'AmiGo: Computational Design of Amigurumi Crochet Patterns.'. [claim:clm_076]
Because amigurumi are crocheted in the round from a starting circle with constant row height equal to a single-crochet (SC) stitch width, every stitch in a row is equidistant from the start, making surface geodesic distance the natural model for crochet rows. [claim:clm_077]
Equidistant curves spaced by the stitch height define the pattern rows; stitch locations are computed by flattening the model (vertical = distance from seed/row number, horizontal = distance along the curve/stitch number) and evenly sampling, then mapping points back to form the crochet graph. [claim:clm_078]
The core method computes geodesic distance on the surface from a seed point, then samples the equidistant curves non-uniformly under curvature guidance, with mean curvature at crease lines selecting stitch types. [claim:clm_075]
Saddle-like regions (negative Gaussian and mean curvature) trigger reduced stitch counts in the row sampling, while creases are reproduced via BLO/FLO stitches applied where maximal absolute curvature is high and its direction is orthogonal to the crocheting direction; both adaptations are automatic. [claim:clm_079]
Models with 'craters' (negative mean curvature and positive Gaussian curvature) are not realizable as maximally-stuffed crochet, so the input is pre-processed by 'inflating' it to remove craters before pattern generation. [claim:clm_080]
Multi-component equidistant curves (e.g., a two-legged human-like model seeded at the head) require partitioning the model into separately-crochetable parts with pick-up connection instructions, and assembly is seamless with no sewing. [claim:clm_081]
The authors acknowledge results do not look like classic amigurumi because they join-and-turn each round (to avoid spiral slanting incompatible with their shortest-vertical-edge optimization), and plan future support for spiral crocheting, higher stitches, color, and yarn-quantity reporting. [claim:clm_082]
Geodesic-distance iso-curve extraction (Bridges 2024) and AmiGo share the same row model (equidistant geodesic curves spaced by SC stitch height) but Bridges is the more reproducible specification of the row-extraction stage for simple primitives, because on a sphere/egg/pear the geodesic field is smooth and single-component, avoiding the saddle-segmentation and DTW machinery that AmiGo invokes only for branching shapes. **Inference:** [claim:clm_inf10]

### The same group's follow-up artifacts

The same group published a follow-up short paper, 'Amigurumi Crochet Patterns from Geodesic Distances' by Mirela Ben-Chen and Michal Edelstein, at Bridges 2024. [claim:clm_064]
The page is the official publications listing of Mirela Ben-Chen at the Center for Graphics and Geometric Computing, CS, Technion, confirming the affiliation and the authoritative artifact location for the AmiGo (B1) anchor. [claim:clm_066]

## Crochetability constraint model


The crochetability constraint model that should govern KnitWit's generator is: (1) a hard legality bound that no row-to-row transition may more than double or more than halve the stitch count (a single inc/dec step cannot exceed 2x or 0.5x); (2) a tighter design bound of approximately +/-1 stitch of the smooth circumference ratio per row with increases distributed evenly; and (3) a segmentation trigger when a feature would force roughly a >50% single-round increase. **Inference:** [claim:clm_inf04]
The program flags an error at the top of the pattern when the stitch count between rows more than doubles or more than halves (so Inc/Dec cannot accomplish the move), and recommends adding a positive constant to f(x) or changing scale/multiplying the function. [claim:clm_045]
The report states a concrete crochetability heuristic: keep each row's stitch count within +/-1 of the smooth ratio, insert increases evenly, and never grow more than about 2x stitches from one round to the next (ideally less), flagging regions that would need a sudden large increase for segmentation. [claim:clm_008]
The report identifies a top de-risk experiment defining a max-curvature / rate-of-increase threshold: a shape feature forcing roughly a >50% single-round increase is treated as not reliably crochetable and must be segmented. [claim:clm_013]
Stitch count per row is deterministic: s(i) = round(2*pi * scale * (S/4) * f(x_i)), i.e., the circumference at that height times the stitch gauge. [claim:clm_044]

### Numeric crochetability rules and their source disagreement

| Rule | Numeric bound | Purpose | Source | Evidence |
|------|---------------|---------|--------|----------|
| Legal stitch-count transition (machine ceiling) | No more than 2x or 0.5x per round | Hard legality, Inc/Dec physically realizable | math_crochet | [claim:clm_045] |
| Per-round design bound | Within +/-1 of smooth circumference ratio, increases distributed evenly | Quality, even fabric | B1 baseline | [claim:clm_008] |
| Segmentation trigger | Feature forcing roughly >50% single-round increase | Quality ceiling, segment instead | B1 de-risk rule | [claim:clm_013] |
| Per-row stitch count basis | s(i)=round(2*pi*scale*(S/4)*f(x_i)) | Deterministic count = circumference x gauge | math_crochet | [claim:clm_044] |

The two numeric crochetability bounds in the source set disagree by roughly 2x in strictness: math_crochet's published legality cap permits up to a 100% single-round increase (2x) before erroring, whereas the B1 heuristic treats a >~50% single-round increase as already not reliably crochetable and a segmentation trigger; the resolution is to treat ~2x as the absolute machine-legality ceiling and ~50% as the design/quality ceiling, with decision impact medium. **Inference:** [claim:clm_inf05]

## Reproduce-vs-heuristic-vs-ML decision


The recommended-method comparison matrix scores math_crochet (surface-of-revolution) highest on reproducibility and compute but lowest on shape coverage, AmiGo highest on shape fidelity/robustness but worst on license-free reproducibility and mobile compute (2.5 min, 3670 stitches for Teddy), Capunaman NURBS-UV mid on fidelity but blocked by Rhino dependence, and the Greer-Mould force-directed layout as the natural pattern-to-3D round-trip engine rather than a mesh-to-pattern generator. **Inference:** [claim:clm_inf03]

### Weighted decision criteria

| Criterion (weight) | math_crochet reproduce | AmiGo reproduce / general-mesh | Heuristic SoR template | ML-assist | Evidence |
|--------------------|--------------------------|-------------------------------|------------------------|-----------|----------|
| Accuracy / shape fidelity (high) | Lowest coverage, revolution-only | Highest fidelity/robustness across shapes | Solved analytically for symmetric shapes | No source evidence of accuracy | [claim:clm_inf03] |
| Robustness across mesh classes (high) | Surfaces of revolution only, no arbitrary meshes | Generalizes across a wide variety of shapes | Symmetric shapes are the lowest-risk first milestone | Unjustified by any source in the set | [claim:clm_027] |
| Compute cost / mobile fit (high) | Closed-form, cheap | 2.5 min, 3670 stitches for Teddy on desktop, not real-time | Analytically solved, low-risk | No evidence | [claim:clm_012] |
| License / IP (high) | AGPL-3.0 copyleft, not embeddable | CC BY-NC-SA non-commercial, not reusable | Re-implemented math, IP-clean | No evidence | [claim:clm_021] |

The report flags that for surfaces of revolution the inverse mapping is essentially a solved problem analytically, supporting symmetric shapes as the lowest-risk first milestone. [claim:clm_011]
The report notes AmiGo-style general-mesh inverse mapping is higher risk: no public code, implemented in Matlab/C++, and reported running times of seconds to minutes (not real-time). [claim:clm_012]
The report's inverse-mapping taxonomy enumerates four families with capability matrices: deterministic geometry mapping (AmiGo / Capunaman NURBS-UV), shape templates and segmentation / primitives (Nakjan sketch-to-primitive, Crochet Lathe), optimization and constraint-solving, and ML-assisted pipelines. [claim:clm_010]
The report documents a deterministic geometry-mapping family (AmiGo-style: trace a continuous geodesic/iso-curve path that spirals around the shape, inserting increases on positive curvature and decreases on negative curvature) as distinct from the other inverse families it catalogs. [claim:clm_009]
The report's recommended inverse baseline, 'Amigurumi Graph Lite' (Geodesic Row Planner), generates rows around a chosen seed axis and sets each row's stitch count from the mesh circumference at that height versus gauge, deliberately de-scoping AmiGo by handling only single-part convex meshes first. [claim:clm_007]
Crochet Lathe / the math_crochet lineage is the correct lower-risk first milestone (G4 mesh-to-pattern primitive) because its constraint model is fully closed-form and self-validating: it deterministically resolves every row via arclength and flags illegal transitions itself, but its AGPL-3.0 license and Sage/CoCalc runtime make direct code reuse unfit for a closed-source mobile app, so KnitWit should re-implement the documented formulas rather than embed the repo. **Inference:** [claim:clm_inf08]

### math_crochet (surfaces of revolution), the reproducible reference

The project is licensed under AGPL-3.0, a strong copyleft license that constrains embedding its code in a closed-source commercial mobile app. [claim:clm_021]
The codebase is implemented entirely in Sage (reported as 100% of the repository's languages), designed to run in the CoCalc environment. [claim:clm_022]
The tool is run by opening a Sage worksheet ('Crocheting Surfaces of Revolution') inside CoCalc rather than as a standalone or mobile application. [claim:clm_023]
The code is published and runnable: written in a Sage worksheet, freely accessible via CoCalc, with the source in the GitHub repository github.com/meganmartinez/math_crochet. [claim:clm_047]
The program's inputs are a function f(x) (positive on (a,b), with f'(x) defined on [a,b]) rotated about the x-axis, x-bounds a and b, stitch gauge S (stitches per 4 in), row gauge R (rows per 4 in), and a scale (inches per unit), confining scope to axially symmetric shapes. [claim:clm_041]
Scope is limited to mathematical surfaces of revolution, always rotating the given function about the x-axis, with no support for arbitrary meshes or branching. [claim:clm_027]
Row landmarks are placed by dividing the total arclength, computed as L = (scale*R/4) * integral_a^b sqrt(1 + (f'(x))^2) dx (measured in rows), with the worked example yielding L ~= 16.162 rows. [claim:clm_042]
Each row landmark x_i is found by solving the cumulative-arclength equation with a 'guess and check' protocol accurate to two decimal places, always measuring arclength from x0 = a to mitigate rounding error. [claim:clm_043]
Output is standard human crochet notation with per-row counts and totals; the worked example f(x)=x^3+2x^2-2x+4 over [-3,1], S=22, R=25, scale=0.18 produces rows 0-16 (17 rows) with stitch counts ranging from 6 up to 51 and back to 31. [claim:clm_046]
Outputs are a set of crochet instructions plus a list of coordinates per row and a plot of the function with dots marking where each crochet row aligns to the profile curve. [claim:clm_026]
Inputs are a function f(x), interval bounds a and b, stitch gauge S, row gauge R, and a scale, and the chosen function must be strictly positive on (a,b). [claim:clm_024]
The function must also have a defined derivative on the closed interval [a,b], a smoothness precondition on permitted inputs. [claim:clm_025]

### Capunaman NURBS-UV, fidelity blocked by Rhino dependence

The algorithm requires a UV-parameterized surface as input, deriving stitch direction and connectivity from the surface's parameter directions rather than from a single seed point. [claim:clm_015]
Because the platform (Grasshopper for Rhino) evaluates NURBS, the method relies on NURBS UV division to transfer a 3D geometry into a crochet pattern. [claim:clm_016]
The work formalizes crochet of non-symmetrical 3D objects as a computer algorithm whose output is a conventional, human-readable text crochet pattern, going beyond axially symmetric revolved surfaces (sphere, cylinder, cone, ellipsoid). [claim:clm_019]
The study has two stages — an analytical systematic approach to crocheting 3D objects to discover the underlying computational aspects, then a formal representation of that logic as a computer algorithm. [claim:clm_020]
The crafter's hand effect (grip on the yarn) is captured empirically through six different physical 10-by-10-stitch tension swatches crocheted before running the algorithm. [claim:clm_017]
Gauge variables are split into determinate inputs (yarn weight, hook size) and an indeterminate input — the crafter's grip on the yarn — which the swatch is used to measure. [claim:clm_018]
The framework is a parametric model that generates crochet patterns for NURBS surfaces using a 10-stitches-by-10-rows tension swatch to calibrate the digital-to-physical mapping. [claim:clm_035]
The generated crochet patterns are text-based, step-by-step representations explicitly analogized to g-code in additive manufacturing, serving documentation and communication of the crocheting process. [claim:clm_036]
The method extends to branching geometries by decomposing a parametric form into multiple components that can be crocheted by multiple crafters. [claim:clm_037]
As proof of concept, a branching structure of 14 unique components was designed and crocheted by two architecture students at Pennsylvania State University, each completing 7 components. [claim:clm_038]
Per-crafter tension swatches capture individual gauge variables, so different users can crochet different components while preserving the digitally designed geometry and dimensional accuracy. [claim:clm_039]
The authors frame the approach as enabling a collective, distributed crocheting platform and an alternative path for transitioning from the digital to the physical. [claim:clm_040]

## Mesh preconditioning and OSS toolchains


Mesh preconditioning is non-optional for any deterministic generator in this set: inputs must be watertight closed genus-0 manifolds, and 'crater' regions (negative mean curvature with positive Gaussian curvature) must be removed by inflation / Conformal Mean Curvature Flow before pattern generation, meaning a mesh-sanitization plus curvature-repair pass is a hard prerequisite stage, not an optional cleanup. **Inference:** [claim:clm_inf11]
A fit-for-purpose OSS mesh-preconditioning toolchain for mobile-targeted v1 plausibly exists in two stacks: (A) libigl (MPL-2.0) for heat-method geodesics, mean/Gaussian curvature, and remeshing, paired with geometry-central for the regularized geodesic solver underpinning AmiGo's row function; and (B) Open3D (MIT) or pymeshlab (GPL) for hole-filling, non-manifold repair, and remeshing to a target edge length tied to stitch size - with the MIT/MPL options preferred over GPL/AGPL for a closed-source app. **Speculation:** [claim:clm_inf12]

### OSS toolchain fitness for mobile-targeted v1

| Toolchain | License | Role | Fit for mobile v1 | Evidence |
|-----------|---------|------|-------------------|----------|
| libigl + geometry-central | MPL-2.0 | Heat-method geodesics, curvature, remeshing, regularized geodesic solver | Fit, permissive license | [claim:clm_inf12] |
| Open3D | MIT | Hole-filling, non-manifold repair, remeshing to stitch-size edge length | Fit, permissive license | [claim:clm_inf12] |
| pymeshlab | GPL | Hole-filling, non-manifold repair, remeshing | Unfit for closed-source, copyleft | [claim:clm_inf12] |
| autoknit pipeline/formats | Public domain | Reusable staged pipeline + intermediate formats | Fit, IP-safe to borrow structure | [claim:clm_067] |

The autoknit codebase is placed in the public domain, making its pipeline and intermediate formats reusable for IP-safe work. [claim:clm_067]
autoknit is an open re-implementation of the paper 'Automatic Machine Knitting of 3D Meshes' that does not exactly match the paper's original code. [claim:clm_068]
Inputs are an OBJ mesh plus user-defined constraints: the interface loads an .obj model and saves user-marked boundary/direction constraints to a .cons file. [claim:clm_069]
Constraints must cover all boundaries and can additionally be placed to control knitting direction, with a region-cut option for meshes without boundaries. [claim:clm_070]
Stitch geometry is parameterized by obj-scale, stitch-width, and stitch-height, giving stitch size relative to the scaled object. [claim:clm_071]
The pipeline runs Constraints -> Peeling/Linking -> Scheduling -> Knitout with a distinct intermediate file format per stage: .cons constraints, .st traced stitches, .js scheduling/javascript, and .k knitout. [claim:clm_072]
Peeling/Linking converts the mesh into a row-column graph, and the implementation is described as mostly working for peeling/tracing with working linking. [claim:clm_073]
Scheduling is a concrete maturity caveat: it works for small cases only and lacks a greedy fallback (only the optimal search is implemented). [claim:clm_074]

## Crochet IR alignment and round-trip


The recommended deterministic pipeline maps cleanly onto Crochet IR v0.1 with one structural caveat: each extracted geodesic row becomes a rounds[] entry whose ops are sc/inc/dec with an expected_stitch_count equal to round(circumference*gauge), and visual_hint.shape_role is set to increase/straight/decrease from the sign of the row-to-row delta; multi-segment shapes become separate pieces[] joined via assembly[] (join-as-you-go), so the only fields the IR lacks natively are BLO/FLO crease stitches and pick-up attachment coordinates. **Inference:** [claim:clm_inf13]

### Method output to Crochet IR v0.1 field mapping

| Method output | Crochet IR field | Round-trip | Evidence |
|---------------|------------------------|----------|----------|
| Extracted geodesic row | rounds[] entry | Yes | [claim:clm_inf13] |
| Per-row stitch count round(circumference*gauge) | rounds[].expected_stitch_count | Yes | [claim:clm_044] |
| sc / inc(x) / dec(x) instruction | ops[].op = sc / inc / dec | Yes | [claim:clm_032] |
| Row-to-row delta sign | visual_hint.shape_role = increase/straight/decrease | Yes | [claim:clm_inf13] |
| Automatic segment + join-as-you-go | pieces[] + assembly[] | Yes | [claim:clm_005] |
| BLO/FLO crease stitch | no native field | Lossy / missing | [claim:clm_079] |
| Pick-up attachment coordinate | no native field | Lossy / missing | [claim:clm_081] |

The pattern-to-3D round-trip needed for G3 is achievable with the Greer-Mould force-directed graph layout because its input (row-by-stitch amigurumi notation, each node a sphere) is information-equivalent to Crochet IR rounds[].ops, so the generator's IR output can be visualized without a second lossy conversion; the only round-trip loss is geometric (the layout approximates shape and size, it does not reconstruct the original mesh exactly). **Inference:** [claim:clm_inf14]
The method takes a written crochet pattern as input, translates it into a graph, and computes a force-directed graph layout to produce a 3D representation matching the hand-crocheted object in shape and size. [claim:clm_048]
The modeling tool consumes patterns written in row-by-stitch notation, the most common notation for amigurumi, and represents each graph node as a sphere so the user can see individual stitches. [claim:clm_052]
The digital preview lets a designer adjust a pattern from the model without physically crocheting it, removing the manual crochet/modify/redo iteration loop. [claim:clm_049]
Conventional crochet pattern design is iterative and wasteful: a pattern is crocheted, evaluated, then stitches are undone and remade across multiple guesswork-heavy iterations involving manual labor. [claim:clm_050]
The tool targets both professional designers and beginners, helping designers visualize a pattern before investing time and effort to physically make it. [claim:clm_051]
The paper is a 2025 Eurographics primary source (Expressive Symposium / WICED 2025, DOI 10.2312/exw.20251057, ISBN 978-3-03868-271-4), published open-access by The Eurographics Association. [claim:clm_053]
Prior crochet-from-shape tools are constrained: Nakjan et al. let users trace 2D shapes converted to 3D and then to a pattern but are limited to relatively symmetrical shapes such as spheres and cylinders. [claim:clm_054]

## Academic feasibility vs product readiness


On the academic-feasibility vs product-readiness line, every method in the set is academically demonstrated but none is product-ready for an amigurumi-first mobile app: AmiGo's 2.5-minute Matlab/C++ runtime and unreleased code, Capunaman's desktop Rhino dependency, and math_crochet's Sage/CoCalc worksheet all fail the mobile/offline/closed-source product bar, so KnitWit's v1 deterministic engine must be a fresh mobile-targeted re-implementation of published math, not an integration of any existing artifact. **Inference:** [claim:clm_inf09]

### Where each method sits on the feasibility/readiness line

| Method | Academic feasibility, shown in paper | Product readiness, mobile / offline / closed-source | Evidence |
|--------|---------------------------------------|----------------------------------------------------|----------|
| AmiGo | Demonstrated across a wide variety of shapes | Unproven, 2.5 min desktop runtime, unreleased Matlab/C++ | [claim:clm_034] |
| Capunaman NURBS-UV | Demonstrated for non-symmetrical shapes + branching PoC | Unproven, desktop Grasshopper/Rhino dependency | [claim:clm_016] |
| math_crochet | Published runnable reference | Unproven, Sage worksheet in CoCalc, not mobile | [claim:clm_023] |
| Greer-Mould visualizer | Demonstrated pattern-to-3D layout matching shape/size | Round-trip engine, not a generator | [claim:clm_048] |

The authors report the method generalizes across a wide variety of shapes and yields easily crochetable patterns; the paper is 11 pages with 10 figures (SCF 2022). [claim:clm_006]
The authors demonstrate the pipeline across a large variety of shapes and report that it yields easily crochetable patterns. [claim:clm_060]
AmiGo takes a closed triangle mesh plus a single user-specified point as input and outputs crochet instructions that, when crocheted and stuffed, approximate the input geometry. [claim:clm_055]
The method's core representation is a 'Crochet Graph' whose geometry and connectivity are constructed and then translated into a human-crochetable pattern. [claim:clm_056]
The shape is segmented automatically into crochetable components that are joined with the 'join-as-you-go' method, eliminating any additional sewing. [claim:clm_057]

## Contradictions & open disagreements


The two numeric crochetability bounds in the source set disagree by roughly 2x in strictness: math_crochet's published legality cap permits up to a 100% single-round increase (2x) before erroring, whereas the B1 heuristic treats a >~50% single-round increase as already not reliably crochetable and a segmentation trigger; the resolution is to treat ~2x as the absolute machine-legality ceiling and ~50% as the design/quality ceiling, with decision impact medium. **Inference:** [claim:clm_inf05]
AmiGo is the only source-backed method that gives no explicit numeric inc/dec-rate cap, deriving transitions implicitly from DTW row coupling and the sc/inc(x)/dec(x) transducer; this is the single largest underspecified stage for KnitWit's bounded-constraint goal and must be supplied externally (e.g. by adopting the math_crochet 2x bound) rather than read off AmiGo. **Inference:** [claim:clm_inf06]

## Risks


RISK (severity high, likelihood medium): re-implementing AmiGo's geodesic row planner without the released DTW coupling and CMCF parameters will likely produce off-by-stitch row misalignment on non-spherical primitives; mitigation is to validate every generated pattern against the two-tier crochetability linter (2x legality plus ~50% segmentation trigger) and round-trip it through a Greer-Mould-style visualizer before exposing it to users (forward-looking inference). **Speculation:** [claim:clm_spec01]
RISK (severity high, likelihood high) and DECISION GATE: AmiGo's 2.5-minute desktop Matlab/C++ runtime for a 60-row 3670-stitch Teddy predicts that a faithful general-mesh inverse generator will not run interactively on mid-range mobile, so G4 should be gated on a primitive-only generator (sphere/egg/pear) running in well under a few seconds, deferring general-mesh AmiGo to a server-side or post-MVP path (forward-looking speculation). **Speculation:** [claim:clm_spec02]
The IP/license landscape predicts a clear build path: AmiGo (CC BY-NC-SA, non-commercial) and math_crochet (AGPL-3.0, copyleft) both forbid direct reuse in a closed-source commercial app, while autoknit (public domain) and the Greer-Mould paper supply IP-safe reusable pipeline structure and intermediate formats; therefore KnitWit should treat the academic methods as specifications to re-implement and borrow concrete file-format/staging patterns from autoknit's public-domain Constraints-Peeling/Linking-Scheduling-Knitout pipeline (forward-looking inference). **Inference:** [claim:clm_spec03]

### Risk register

| Risk | Severity | Likelihood | Mitigation | Evidence |
|------|----------|------------|------------|----------|
| Row misalignment from re-implementing AmiGo without DTW/CMCF parameters | High | Medium | Validate against two-tier linter + round-trip visualizer | [claim:clm_spec01] |
| Faithful general-mesh generator too slow for mid-range mobile | High | High | Gate G4 on primitive-only generator, defer general-mesh to server/post-MVP | [claim:clm_spec02] |
| IP/license blocking direct code reuse, CC BY-NC-SA and AGPL-3.0 | High | High | Re-implement academic math, borrow only public-domain autoknit structure | [claim:clm_spec03] |

## Prototype experiments & decision-gate relevance


Seed-point placement is a quality-not-feasibility variable for convex primitives but becomes feasibility-critical for branching shapes: AmiGo/Bridges require the seed at a pole/extremum so the geodesic field stays single-component, and a poorly placed seed on a multi-limbed model forces earlier saddle segmentation; for KnitWit v1 (single-part convex meshes) automatic pole/extremum detection is sufficient and user seed selection is an optional refinement. **Inference:** [claim:clm_inf15]
The report names seed/seam placement effect on pattern symmetry, and round-trippability of a generated pattern back through the forward visualizer/validator, as key open de-risk experiments for the inverse pipeline. [claim:clm_014]

### Findings mapped to decision gates and prototype experiments

| Gate | What the findings de-risk | Suggested prototype experiment | Evidence |
|------|---------------------------|----------------------------------|----------|
| G2 Crochet IR viability | Method output maps onto IR v0.1 rounds/ops/expected_stitch_count, only crease/pick-up fields missing | IR hello-world + stitch-count validator + repeat expansion | [claim:clm_inf13] |
| G3 Pattern-to-3D viability | Greer-Mould round-trips IR without a second lossy conversion | IR-to-stitch-graph + stitch-graph-to-approximate-3D + row-highlight export | [claim:clm_inf14] |
| G4 Mesh-to-pattern primitive | math_crochet / Crochet-Lathe lineage is the closed-form self-validating first milestone | Primitive-mesh-to-rounds + mesh-pattern-to-IR | [claim:clm_inf08] |
| G4 performance gate | Gate on primitive-only generator under a few seconds, defer general-mesh AmiGo | Primitive-mesh-to-rounds running under a few seconds | [claim:clm_spec02] |
| G4/G5 validation | Two-tier crochetability linter + visualizer round-trip mitigates misalignment | Round-trip evaluator, mesh -> pattern -> visualizer | [claim:clm_spec01] |

## Recommendations and decision rules


For KnitWit's v1 the evidence supports an option (b)+(a) hybrid: ship a heuristic/templated surface-of-revolution generator first (analytically solved, low-risk) and reproduce only the de-scoped AmiGo-style geodesic row planner ('Amigurumi Graph Lite') as the general-mesh path, while option (c) ML-assist is not yet justified by any source in the set. **Inference:** [claim:clm_inf02]
Crochet Lathe / the math_crochet lineage is the correct lower-risk first milestone (G4 mesh-to-pattern primitive) because its constraint model is fully closed-form and self-validating: it deterministically resolves every row via arclength and flags illegal transitions itself, but its AGPL-3.0 license and Sage/CoCalc runtime make direct code reuse unfit for a closed-source mobile app, so KnitWit should re-implement the documented formulas rather than embed the repo. **Inference:** [claim:clm_inf08]
The crochetability constraint model that should govern KnitWit's generator is: (1) a hard legality bound that no row-to-row transition may more than double or more than halve the stitch count (a single inc/dec step cannot exceed 2x or 0.5x); (2) a tighter design bound of approximately +/-1 stitch of the smooth circumference ratio per row with increases distributed evenly; and (3) a segmentation trigger when a feature would force roughly a >50% single-round increase. **Inference:** [claim:clm_inf04]
The IP/license landscape predicts a clear build path: AmiGo (CC BY-NC-SA, non-commercial) and math_crochet (AGPL-3.0, copyleft) both forbid direct reuse in a closed-source commercial app, while autoknit (public domain) and the Greer-Mould paper supply IP-safe reusable pipeline structure and intermediate formats; therefore KnitWit should treat the academic methods as specifications to re-implement and borrow concrete file-format/staging patterns from autoknit's public-domain Constraints-Peeling/Linking-Scheduling-Knitout pipeline (forward-looking inference). **Inference:** [claim:clm_spec03]

## Open questions

- Does the seed/seam placement materially change pattern symmetry on single-part convex primitives, or only on multi-limbed shapes?
- What concrete CMCF inflation stop-criterion (beyond 'mean curvature positive everywhere') reproduces AmiGo's crater removal deterministically?
- What DTW coupling parameters does AmiGo use, given that they are not stated in the paper?
- Will a primitive-only mesh-to-rounds generator round-trip cleanly through a Greer-Mould-style visualizer within the G3/G4 acceptance metrics?
- Is the ~50% segmentation trigger or the ~2x legality ceiling the better default user-facing bound for KnitWit's linter?

## Sources

- src_20260614_kw006_02: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw006_09: KnitWit B1 Workstream Report (project prior-art synthesis)
- src_20260614_kw006_05: Computing Stitches and Crocheting Geometry
- src_20260614_kw006_08: math_crochet - surfaces-of-revolution crochet generator (reference implementation)
- src_20260614_kw006_00: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw006_06: From Stitches to Digits and Back: Computational Crocheting of Branching Geometries
- src_20260614_kw006_07: Automating Crochet Patterns for Surfaces of Revolution
- src_20260614_kw006_11: Modeling Crochet Patterns with a Force-directed Graph Layout
- src_20260614_kw006_01: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw006_03: Mirela Ben-Chen Publications (Center for Graphics and Geometric Computing, Technion)
- src_20260614_kw006_10: autoknit: a re-implementation of "Automatic Machine Knitting of 3D Meshes"
- src_20260614_kw006_04: Amigurumi Crochet Patterns from Geodesic Distances
