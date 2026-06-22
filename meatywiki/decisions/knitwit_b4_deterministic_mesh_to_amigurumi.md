---
id: mwb_20260622_dr_knitwit_b4_deterministic_mesh_to
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_is_the
target_page: meatywiki/decisions/knitwit_b4_deterministic_mesh_to_amigurumi.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_what_is_the_most_reproducible_deterministic: Surfaces
  of revolution are called analytically solved and lowest-risk (clm_011) with a closed-form deterministic
  stitch '
key_claims:
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_spec03
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf05
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
- claim_id: clm_inf14
  include: true
- claim_id: clm_inf15
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_007
  - clm_011
  - clm_012
  - clm_044
  - clm_009
  - clm_042
  - clm_043
  - clm_045
  - clm_021
  - clm_022
  - clm_023
  - clm_001
  - clm_067
  - clm_072
  - clm_073
  - clm_034
  - clm_047
  - clm_016
  - clm_048
  - clm_027
  - clm_008
  - clm_013
  - clm_032
  - clm_031
  - clm_029
  - clm_030
  - clm_058
  - clm_059
  - clm_033
  - clm_077
  - clm_078
  - clm_081
  - clm_028
  - clm_080
  - clm_003
  - clm_005
  - clm_079
  - clm_052
  - clm_014
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: KnitWit B4: Deterministic Mesh-to-Amigurumi Pattern Synthesis - Method Reproduction, Crochetability Constraints, and the Reproduce-vs-Heuristic-vs-ML Decision

## Context

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

## Decision

For KnitWit's v1 the evidence supports an option (b)+(a) hybrid: ship a heuristic/templated surface-of-revolution generator first (analytically solved, low-risk) and reproduce only the de-scoped AmiGo-style geodesic row planner ('Amigurumi Graph Lite') as the general-mesh path, while option (c) ML-assist is not yet justified by any source in the set. [claim:clm_inf02]

## Rationale

- Surfaces of revolution are called analytically solved and lowest-risk (clm_011) with a closed-form deterministic stitch count (clm_044); general AmiGo-style mapping is flagged higher-risk with no public code and second-to-minute runtimes (clm_012); the project's own recommended baseline is the de-scoped Graph Lite (clm_007, clm_009); no source provides ML accuracy/robustness evidence, so ML-assist lacks an evidentiary basis. [claim:clm_inf02]
- The method resolves rows by arclength (clm_042, clm_043), counts stitches deterministically (clm_044), and self-flags illegal transitions (clm_045) - a complete constraint model; but it is AGPL-3.0 (clm_021), 100% Sage (clm_022), run in CoCalc (clm_023), so the formulas are reusable as a spec but the code is not embeddable, motivating clean re-implementation. [claim:clm_inf08]
- AmiGo is CC BY-NC-SA non-commercial (clm_001); math_crochet is AGPL-3.0 (clm_021); both block closed-source reuse. autoknit is public domain (clm_067) with a documented staged pipeline and intermediate formats (clm_072, clm_073), so its structure is IP-safe to borrow while the academic methods are re-implemented from their published math. [claim:clm_spec03]
- AmiGo is Matlab/C++ with no code/data release (clm_034, clm_012); the Capunaman method runs only inside Grasshopper-for-Rhino on NURBS UV (clm_016) with no public code cited; only math_crochet publishes runnable code (clm_047) with fully stated deterministic formulas (clm_044), so it is the sole turnkey-reproducible pipeline despite AGPL copyleft (clm_021). [claim:clm_inf01]
- Synthesizes per-method properties: math_crochet reproducible but revolution-only (clm_047, clm_027); AmiGo high-fidelity general-mesh but heavy and unreleased (clm_034, clm_012); Capunaman tied to NURBS UV in Rhino (clm_016); Greer-Mould maps written pattern to graph to 3D (clm_048), making it the round-trip/visualizer side, not a generator. [claim:clm_inf03]
- math_crochet enforces the hard 2x/0.5x legality bound and errors otherwise (clm_045); the B1 baseline sets the +/-1 smooth-ratio and ~2x design heuristic (clm_008); the >50%-increase segmentation threshold is the project's de-risk rule (clm_013); all sit atop the deterministic circumference-times-gauge stitch count (clm_044). [claim:clm_inf04]
- math_crochet errors only when count more than doubles or halves (clm_045 = 100%/2x ceiling); the B1 report flags >~50% per round as not reliably crochetable (clm_013) and recommends staying near the smooth ratio (clm_008). The two are different thresholds for different purposes (legality vs quality), so both are kept as a two-tier rule rather than averaged. [claim:clm_inf05]
- AmiGo's transducer emits inc(x)/dec(x) from DTW coupling with no stated numeric cap (clm_032, clm_031); only math_crochet states an explicit numeric transition bound (clm_045), so the bound must be imported from the revolution method, not from AmiGo. [claim:clm_inf06]
- Row function (clm_029) and column objective (clm_030) and saddle segmentation/topo-sort (clm_058, clm_059) are stated; DTW (clm_031) and transducer (clm_032) lack numeric parameters; CMCF stop is qualitative (clm_033); no code/data released (clm_034). The split follows from which stages carry equations/parameters versus prose. [claim:clm_inf07]
- AmiGo: 2.5 min, Matlab/C++, unreleased (clm_034, clm_012); Capunaman: Grasshopper/Rhino NURBS (clm_016); math_crochet: Sage in CoCalc (clm_023, clm_022). None targets mobile/offline/closed-source, so all are feasibility demos, not products. [claim:clm_inf09]
- Bridges models rows as geodesic equidistant curves spaced by stitch height (clm_077, clm_078), identical to AmiGo's geodesic row function (clm_029); saddle segmentation (clm_058) and multi-component partitioning (clm_081) only arise for branching/multi-leg shapes, so convex primitives need only the simpler single-field extraction. [claim:clm_inf10]
- AmiGo requires closed surfaces (clm_028, clm_003); both AmiGo (clm_033) and Bridges (clm_080) preprocess away non-realizable craters via CMCF/inflation, establishing curvature repair plus watertightness as mandatory preconditions before generation. [claim:clm_inf11]
- Deterministic per-row stitch count (clm_044) maps to expected_stitch_count; sc/inc/dec ops (clm_032) match the IR op enum; equidistant rows (clm_078) map to rounds[]; automatic segmentation plus join-as-you-go (clm_005, clm_081) map to pieces[] plus assembly[]; BLO/FLO creasing (clm_079) and pick-up points have no native IR field, naming the gap. [claim:clm_inf13]
- Greer-Mould consumes row-by-stitch notation and lays it out into a shape/size-matching 3D model (clm_048, clm_052); that notation is isomorphic to IR rounds/ops, so IR feeds the visualizer directly. The layout matches shape/size approximately, naming the lossy boundary as geometric approximation. [claim:clm_inf14]
- Rows are geodesic distance from the seed (clm_029); a head-seeded two-legged model yields multi-component curves requiring partitioning (clm_081, clm_058); the project names seed/seam placement as an open de-risk item (clm_014); v1 is scoped to single-part convex meshes (clm_007), where seed choice mainly affects symmetry/quality, not feasibility. [claim:clm_inf15]

## Consequences

- Crochet Lathe / the math_crochet lineage is the correct lower-risk first milestone (G4 mesh-to-pattern primitive) because its constraint model is fully closed-form and self-validating: it deterministically resolves every row via arclength and flags illegal transitions itself, but its AGPL-3.0 license and Sage/CoCalc runtime make direct code reuse unfit for a closed-source mobile app, so KnitWit should re-implement the documented formulas rather than embed the repo. [claim:clm_inf08]
- The IP/license landscape predicts a clear build path: AmiGo (CC BY-NC-SA, non-commercial) and math_crochet (AGPL-3.0, copyleft) both forbid direct reuse in a closed-source commercial app, while autoknit (public domain) and the Greer-Mould paper supply IP-safe reusable pipeline structure and intermediate formats; therefore KnitWit should treat the academic methods as specifications to re-implement and borrow concrete file-format/staging patterns from autoknit's public-domain Constraints-Peeling/Linking-Scheduling-Knitout pipeline (forward-looking inference). [claim:clm_spec03]
- Among the four candidate methods, only Martinez & Taylor Lipnicki's surfaces-of-revolution generator is end-to-end reproducible today (open AGPL-3.0 Sage code, fully specified deterministic formulas s(i)=round(2*pi*scale*(S/4)*f(x_i)) and arclength row placement), whereas AmiGo, the Capunaman NURBS-UV method, and Crochet Lathe each have at least one reproduction-blocking gap (no released code, a Grasshopper/Rhino dependency, or unspecified internals). [claim:clm_inf01]
- The recommended-method comparison matrix scores math_crochet (surface-of-revolution) highest on reproducibility and compute but lowest on shape coverage, AmiGo highest on shape fidelity/robustness but worst on license-free reproducibility and mobile compute (2.5 min, 3670 stitches for Teddy), Capunaman NURBS-UV mid on fidelity but blocked by Rhino dependence, and the Greer-Mould force-directed layout as the natural pattern-to-3D round-trip engine rather than a mesh-to-pattern generator. [claim:clm_inf03]
- The crochetability constraint model that should govern KnitWit's generator is: (1) a hard legality bound that no row-to-row transition may more than double or more than halve the stitch count (a single inc/dec step cannot exceed 2x or 0.5x); (2) a tighter design bound of approximately +/-1 stitch of the smooth circumference ratio per row with increases distributed evenly; and (3) a segmentation trigger when a feature would force roughly a >50% single-round increase. [claim:clm_inf04]
- The two numeric crochetability bounds in the source set disagree by roughly 2x in strictness: math_crochet's published legality cap permits up to a 100% single-round increase (2x) before erroring, whereas the B1 heuristic treats a >~50% single-round increase as already not reliably crochetable and a segmentation trigger; the resolution is to treat ~2x as the absolute machine-legality ceiling and ~50% as the design/quality ceiling, with decision impact medium. [claim:clm_inf05]
- AmiGo is the only source-backed method that gives no explicit numeric inc/dec-rate cap, deriving transitions implicitly from DTW row coupling and the sc/inc(x)/dec(x) transducer; this is the single largest underspecified stage for KnitWit's bounded-constraint goal and must be supplied externally (e.g. by adopting the math_crochet 2x bound) rather than read off AmiGo. [claim:clm_inf06]
- Mapped stage-by-stage, AmiGo's reproducible-vs-underspecified split is: row function (geodesic distance via Heat Method, t = avg-edge-length^2) is fully specified; column function (least-squares J-gradient minimization) is specified as an objective; segmentation over saddle isolines plus topological-sort ordering is specified; but the DTW coupling parameters, the inc/dec numeric cap, the CMCF inflation stop-criterion beyond 'mean curvature positive everywhere', and all dataset/code are underspecified or unreleased. [claim:clm_inf07]
- On the academic-feasibility vs product-readiness line, every method in the set is academically demonstrated but none is product-ready for an amigurumi-first mobile app: AmiGo's 2.5-minute Matlab/C++ runtime and unreleased code, Capunaman's desktop Rhino dependency, and math_crochet's Sage/CoCalc worksheet all fail the mobile/offline/closed-source product bar, so KnitWit's v1 deterministic engine must be a fresh mobile-targeted re-implementation of published math, not an integration of any existing artifact. [claim:clm_inf09]
- Geodesic-distance iso-curve extraction (Bridges 2024) and AmiGo share the same row model (equidistant geodesic curves spaced by SC stitch height) but Bridges is the more reproducible specification of the row-extraction stage for simple primitives, because on a sphere/egg/pear the geodesic field is smooth and single-component, avoiding the saddle-segmentation and DTW machinery that AmiGo invokes only for branching shapes. [claim:clm_inf10]
- Mesh preconditioning is non-optional for any deterministic generator in this set: inputs must be watertight closed genus-0 manifolds, and 'crater' regions (negative mean curvature with positive Gaussian curvature) must be removed by inflation / Conformal Mean Curvature Flow before pattern generation, meaning a mesh-sanitization plus curvature-repair pass is a hard prerequisite stage, not an optional cleanup. [claim:clm_inf11]
- The recommended deterministic pipeline maps cleanly onto Crochet IR v0.1 with one structural caveat: each extracted geodesic row becomes a rounds[] entry whose ops are sc/inc/dec with an expected_stitch_count equal to round(circumference*gauge), and visual_hint.shape_role is set to increase/straight/decrease from the sign of the row-to-row delta; multi-segment shapes become separate pieces[] joined via assembly[] (join-as-you-go), so the only fields the IR lacks natively are BLO/FLO crease stitches and pick-up attachment coordinates. [claim:clm_inf13]
- The pattern-to-3D round-trip needed for G3 is achievable with the Greer-Mould force-directed graph layout because its input (row-by-stitch amigurumi notation, each node a sphere) is information-equivalent to Crochet IR rounds[].ops, so the generator's IR output can be visualized without a second lossy conversion; the only round-trip loss is geometric (the layout approximates shape and size, it does not reconstruct the original mesh exactly). [claim:clm_inf14]
- Seed-point placement is a quality-not-feasibility variable for convex primitives but becomes feasibility-critical for branching shapes: AmiGo/Bridges require the seed at a pole/extremum so the geodesic field stays single-component, and a poorly placed seed on a multi-limbed model forces earlier saddle segmentation; for KnitWit v1 (single-part convex meshes) automatic pole/extremum detection is sufficient and user seed selection is an optional refinement. [claim:clm_inf15]

## Links

- [[claim:clm_007]]
- [[claim:clm_011]]
- [[claim:clm_012]]
- [[claim:clm_044]]
- [[claim:clm_009]]
- [[claim:clm_042]]
- [[claim:clm_043]]
- [[claim:clm_045]]
- [[claim:clm_021]]
- [[claim:clm_022]]
- [[claim:clm_023]]
- [[claim:clm_001]]
- [[claim:clm_067]]
- [[claim:clm_072]]
- [[claim:clm_073]]
- [[claim:clm_034]]
- [[claim:clm_047]]
- [[claim:clm_016]]
- [[claim:clm_048]]
- [[claim:clm_027]]
- [[claim:clm_008]]
- [[claim:clm_013]]
- [[claim:clm_032]]
- [[claim:clm_031]]
- [[claim:clm_029]]
- [[claim:clm_030]]
- [[claim:clm_058]]
- [[claim:clm_059]]
- [[claim:clm_033]]
- [[claim:clm_077]]
- [[claim:clm_078]]
- [[claim:clm_081]]
- [[claim:clm_028]]
- [[claim:clm_080]]
- [[claim:clm_003]]
- [[claim:clm_005]]
- [[claim:clm_079]]
- [[claim:clm_052]]
- [[claim:clm_014]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
