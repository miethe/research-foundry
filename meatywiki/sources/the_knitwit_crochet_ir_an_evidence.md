---
id: mwb_20260614_the_knitwit_crochet_ir_an_evidence
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_is_the
target_page: meatywiki/sources/the_knitwit_crochet_ir_an_evidence.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_is_the_evidence_grounded_design:
  87 supported claim(s) across 12 source card(s).'
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
- claim_id: clm_087
  include: true
links:
  source_cards:
  - src_20260614_kw002_00
  - src_20260614_kw002_01
  - src_20260614_kw002_02
  - src_20260614_kw002_03
  - src_20260614_kw002_04
  - src_20260614_kw002_05
  - src_20260614_kw002_06
  - src_20260614_kw002_07
  - src_20260614_kw002_08
  - src_20260614_kw002_09
  - src_20260614_kw002_10
  - src_20260614_kw002_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# The KnitWit Crochet IR: An Evidence-Grounded Schema, Validation-Rule Set, and Adopt/Adapt Decision over CrochetPARADE and CrochetBench

## Summary

Source note distilled from research run rf_run_20260614_what_is_the_evidence_grounded_design: 87 supported claim(s) across 12 source card(s).

## Key claims

- CrochetPARADE does not distinguish rows from rounds with a keyword; each new line of the pattern text is treated as a new row/round. [claim:clm_001]
- Bracketed repeat blocks can have their last iteration ended early with `>` and their first iteration started at a marked location with `<`, and `...` provides line continuation/wrap. [claim:clm_002]
- Stitches on a row are auto-attached one-by-one to consecutive stitches in the previous row, and turning the work at the end of a row is accounted for automatically by the renderer. [claim:clm_003]
- The grammar has variable/counter machinery: a counter is initialized between two `$` signs (e.g. `$k=0$`) and incremented/decremented with `++`, `--`, `prev k`, or `next k`, with algebra (e.g. mod) permitted in indexing. [claim:clm_004]
- Increase stitches follow a `Ninc` shorthand whose raw definition packs multiple top nodes into one insertion point, e.g. `sc2inc` is two single-crochet top nodes chained onto a shared base. [claim:clm_005]
- Disjoint pieces are created by using a connection length of `skip`; the internally defined `start_anew` stitch uses this so the next stitch has no connection to the previous one, like starting a new part of the project. [claim:clm_006]
- The CrochetPARADE manual is CC BY-NC-SA and the computational components are GPLv3, but the grammar itself cannot be copyrighted and is in the public domain. [claim:clm_007]
- The CrochetPARADE website and all of its computational components are released as free and open source under the GPLv3 license. [claim:clm_008]
- The user manual, which includes a description of the CrochetPARADE grammar, is released under the Creative Commons BY-NC-SA license. [claim:clm_009]
- The grammar itself cannot be copyrighted and is in the public domain, so the DSL grammar is adoptable even though the reference engine is GPLv3 copyleft. [claim:clm_010]
- CrochetPARADE uses a custom DSL grammar to remove the ambiguities of plain-English crochet instructions, parsing and checking patterns for correctness before building a 3D virtual model. [claim:clm_011]
- The CrochetPARADE grammar follows rules similar to those of real programming languages, making it usable to teach both crocheting and programming. [claim:clm_012]
- The platform supports interactive 3D rendering (rotate/zoom/pan), detection of overly loose or tight stitches for adjustment, export of standard-symbol crochet charts and SVG diagrams, and export to 3D files importable in Blender. [claim:clm_013]
- CrochetPARADE performs all calculations locally on-device with no data collected or transmitted, at the cost of being sluggish on old hardware for very large (tens of thousands of stitches) patterns. [claim:clm_014]
- The repository is hosted on Codeberg (canonical) and mirrored on GitHub, with showcase asset filenames timestamped 2025-02-22, indicating active maintenance in early 2025. [claim:clm_015]
- The paper proposes the first visual, domain-specific, graph-based language for unambiguous crochet pattern representation, contributed alongside a 2D-editing/3D-viewing editor prototype and a qualitative user evaluation. [claim:clm_016]
- In the language a stitch is represented as a graph node (an 'insertion point'), and the basic idea is to directly encode the structure and dependency relations of a pattern rather than a linear sequence of stitches. [claim:clm_017]
- Edges encode the worked-into/insertion relationship between stitches: 'previous' edges trace the yarn origin and each node has exactly one outgoing previous edge, while 'insertion' edges point to the insertion points that the current stitch is worked into. [claim:clm_018]
- Increases are represented as multiple incoming insertion edges into one insertion point, and decreases as multiple outgoing insertion edges from a single stitch node. [claim:clm_019]
- Rows and rounds are unified into a single 'layers' abstraction so that flat and circular work share one graph structure, with the layer number stored as a per-node property; no structural change distinguishes a row from a round. [claim:clm_020]
- The core validity invariant for crochetability is that no node may be worked into before it is created (no use of a future insertion point), and the editor renders the graph in 2D/3D via a force-based / 3D force-directed layout heuristic. [claim:clm_021]
- In a think-aloud study with six professional crochet designers, all but one participant successfully reproduced the pattern in 2D; four cited the shape preview as beneficial, and several expressed enthusiasm about the 3D perspective for understanding shape (e.g., amigurumi proportions). [claim:clm_022]
- The graph IR represents each stitch as a node, with horizontal edges encoding sequential connections (one stitch made immediately after another) and vertical edges encoding working connections (top stitch worked into the bottom stitch). [claim:clm_023]
- Shaping effects done without crochet stitches (e.g. pulling yarn tight to create a dimple) are encoded as additional 'constraint edges', as in the apple model where a constraint edge of length 6 (chosen by trial and error) links the first and last node. [claim:clm_024]
- Rows and rounds are treated identically ('rows' is used generically for both), and the first row's single-crochet nodes all connect to a shared anchor (ring) node while later rows work into the previous row. [claim:clm_025]
- The layout is a non-linear least-squares optimization (solved with Ceres Solver) blending an edge-length energy (targeting unit-length edges) and a curvature energy as (1-lambda)*EL + lambda*C, with a default lambda=0.65 (raised to lambda=0.9 for the bunny head and body); inflating the planar graph emulates stuffing. [claim:clm_026]
- Stated limitations include the assumption of constant edge length 1 (real stitch dimensions vary with tension, hook, and yarn, so a swatch measurement is needed for accuracy), testing only on beginner-level patterns and sc-like stitches, and ad hoc piece-joining with no systematic method yet. [claim:clm_027]
- The implementation is released as open-source code at https://github.com/EnbyMonkey/modelingamigurumi.git, and the paper is an open-access article under the Creative Commons Attribution License. [claim:clm_028]
- CrochetPARADE is the acronym for 'Crochet PAttern Renderer, Analyzer, and DEbugger', positioning it as a crochet pattern domain-specific language with rendering and validation tooling. [claim:clm_029]
- Increases and decreases are encoded as suffixes on stitch tokens (Ninc / Ntog), where for example sc2inc means two single-crochet stitches worked into the same stitch. [claim:clm_030]
- Repeats use bracketed blocks with an integer multiplier; for example [10sc,turn]*3 expands to three rows of 10 single crochets each ending with a turn. [claim:clm_031]
- The language is extensible to new stitch types via a DEF directive carrying a raw node/connection grammar of the form top_nodes:bottom_nodes~attachments:other_nodes:connections. [claim:clm_032]
- The CrochetPARADE grammar/language itself is explicitly stated to be in the public domain and not copyrightable, separating the language from the GPLv3-licensed implementation. [claim:clm_033]
- The website and all of CrochetPARADE's computational components are open source and released under the GPLv3 license, while the manual is released under Creative Commons BY-NC-SA. [claim:clm_034]
- The force-directed engine does not produce exact stitch lengths; the author reports it converges to within 10% of requested stitch lengths under default settings. [claim:clm_035]
- The paper represents crochet patterns in the stitch-mesh paradigm as a library of tiles where each tile contains yarn geometry and tiles connect along their edges. [claim:clm_036]
- To adapt stitch meshes to crochet, the authors introduce a special edge type capturing the 'current loop' - the loop of yarn held on the crochet hook during fabrication. [claim:clm_037]
- Faces use short-term (orange) edge types crossed by the leading loop and free yarn and long-term (purple) edge types crossed only by loops, encoding crochet's construction dependencies. [claim:clm_038]
- Four edge labels - Next/Previous (consecutive-stitch leading-loop dependencies) and Future/Past (loop-through-fabric dependencies) - connect as previous-next and past-future pairs to cover a surface. [claim:clm_039]
- Decreases use multi-past-edge faces (sc2tog uses two past loop edges to make one future loop edge; sc3tog three), while the 'inc' utility face splits a future edge into two future edges, and 'turn'/'cap'/'ch_edge' utility faces enable partial-width rows and variants. [claim:clm_040]
- An automatic pipeline (a variant of Narayanan et al. 2019) turns a manifold triangulated 3D mesh into a stitch mesh of quad faces (sc/turn), pentagons (sc2tog), and increase triangles (inc). [claim:clm_041]
- The pattern-generation system (a variant of Narayanan et al. 2019) uses a single stitch 'aspect ratio' to drive the remeshing process, a gauge-like parameter that limits accuracy across varied stitch types. [claim:clm_042]
- CrochetBench adopts the CrochetPARADE DSL as its intermediate representation for crochet patterns. [claim:clm_043]
- The benchmark vendors the CrochetPARADE repository by cloning it from Codeberg for validation. [claim:clm_044]
- Two JavaScript validators ship in the benchmark: verify_crochet_pattern.js and verify_crochet_pattern_with_history.js. [claim:clm_045]
- Data files include project-level and step-level DSL test sets plus a multiple-choice archive (project_level_test.json, step_level_test_*.json, mc_data.json.zip). [claim:clm_046]
- Compilation Success Rate (CSR) is the proportion of generated DSL outputs that compile successfully with the CrochetPARADE validator. [claim:clm_047]
- Partial Executable Rate (PER) is the average fraction of a program that compiles successfully before failure. [claim:clm_048]
- The benchmark defines four tasks: A Stitch Recognition (6,009), B Instruction Selection (6,003), C Instruction Generation (6,009), and D Instruction-to-DSL (119 step-level / 100 project-level). [claim:clm_049]
- The language models a crochet pattern as a directed graph in which each stitch is a node carrying its stitch type as a property, and edges of three kinds (previous, insertion, slip-stitch) encode where the yarn came from and which fabric points the stitch is worked into. [claim:clm_050]
- Rows and rounds are unified into a single concept the authors call 'layers,' requiring no structural change in the graph because whether a pattern is worked row-wise or round-wise depends only on where the next stitch is inserted; each node stores its layer number as a property. [claim:clm_051]
- An increase is represented as multiple stitches sharing one insertion point (multiple incoming insertion edges), and a decrease as a stitch with multiple outgoing insertion edges, directly mirroring the manual increase/decrease methods that widen or narrow a layer. [claim:clm_052]
- Because a crochet pattern is worked along a single yarn, the graph encodes a crochetability (reproducibility) constraint: edge orderings must be such that no loop ever uses an insertion point that has not yet been created, guaranteeing exactly one unambiguous yarn path through the pattern. [claim:clm_053]
- A projectional editor prototype lets designers build patterns step-wise 'as if crocheting,' which by construction only permits reproducible (crochetable) patterns, and renders the same graph as a 2D crochet chart and a force-based 3D view. [claim:clm_054]
- The language and editor were evaluated in a think-aloud study with six professional crochet designers, recruited from 25 respondents of a formative survey originally sent to 200 myboshi designers, who confirmed the language could express 2D and 3D patterns and remove ambiguities present in standard crochet charts. [claim:clm_055]
- The language explicitly represents holes (openings under a stitch or chain) as dedicated nodes connected via surroundingNode edges, making them valid insertion points and capturing a technique that standard crochet charts cannot represent. [claim:clm_056]
- The Crochet Graph G = (S, R union C) models a pattern as vertices S that are stitch tops/bases indexed (i,j) for the j-th stitch in row i, column edges C representing stitch stems between rows, and row edges R representing within-row connectivity. [claim:clm_057]
- Curved geometry is achieved in crochet through stitches that locally increase (inc(x)) or decrease (dec(x)) the stitch count by x, so curvature is encoded directly as stitch-level operations. [claim:clm_058]
- Increases and decreases are emitted by a transducer that reads vertex connectivity: x>1 vertices in row S_i feeding one head vertex in S_{i+1} produce dec(x), and x>1 vertices in S_{i+1} feeding one vertex in S_i produce inc(x). [claim:clm_059]
- Two consecutive rows are 'coupled' when a coupling C between their vertex sets matches exactly the column edges C; if all consecutive row pairs are coupled then valid crochet instructions P(G) exist using only sc, inc(x), and dec(x), guaranteeing yarn continuity. [claim:clm_060]
- Multi-part shapes use 'join-as-you-go': each segment is crocheted directly onto the last row of the previous segment so no sewing is needed, segment order follows a topological sort of the segment DAG, and any shared edge (s,t) requires the last row of M_s to be coupled to the first row of M_t. [claim:clm_061]
- Gauge is controlled by a single stitch width w: the row function f and column function g are uniformly sampled on a 2D grid of width w, producing vertices of S indexed (f/w, g/w), so one width parameter directly maps mesh area to stitch count. [claim:clm_062]
- For regions of negative Gaussian curvature the column sampling rate is modulated by setting <grad g, J grad f> = h(k_j grad f) with h(x)=tanh(-x/alpha)/2+1 and alpha=10, to avoid degenerate sampling rates. [claim:clm_063]
- A two-by-two table over the sign of mean and Gaussian curvature governs crochetability: most combinations are directly crochetable, negative Gaussian with negative mean requires sampling modification, and positive Gaussian with negative mean requires preprocessing. [claim:clm_064]
- CrochetPARADE is an open-source forward crochet visualizer whose engine is GPLv3 (copyleft) but whose pattern-language grammar is public domain, making the grammar adoptable as a Crochet IR while the engine carries integration risk. [claim:clm_065]
- CrochetBench compiled 6,085 real crochet patterns into the CrochetPARADE DSL and validates structural correctness by compiling outputs in the CrochetPARADE interpreter, demonstrating the DSL is expressive enough to capture thousands of real patterns. [claim:clm_066]
- The CrochetBench tooling is permissively licensed (MIT, assumed) but the underlying patterns are copyrighted by Yarnspirations, so the corpus is usable for validation/testing rather than redistribution. [claim:clm_067]
- AmiGo (SCF 2022) is the state-of-art inverse mesh-to-pattern pipeline: it segments a closed mesh into crochetable components, places increases on positive curvature and decreases on negative curvature, and uses join-as-you-go to attach pieces without sewing; no public code (Matlab/C++). [claim:clm_068]
- Digital Crochet (Onward! 2022) defines a graph-based crochet IR where increases are nodes with multiple incoming edges and decreases nodes with multiple outgoing edges, and uses a force-directed algorithm to lay out stitches in 3D as the pattern is built. [claim:clm_069]
- Guo et al. 2020 (SCF) define a special 'current loop' edge type that tracks the live yarn loop moving from stitch to stitch, providing the basis for guaranteeing one continuous yarn path in generated patterns. [claim:clm_070]
- The report's sequencing guidance is to ship the forward visualizer first on a CrochetPARADE-style IR (lower risk, immediate value) and pursue the inverse (3D->pattern) generator, which is more complex, as a longer-term payoff de-risked by focused experiments. [claim:clm_071]
- CrochetPARADE is an acronym for 'Crochet PAttern Renderer, Analyzer, and DEbugger,' authored by Svetlin Tassev, and is a platform for creating, visualizing, and analyzing both 2D and 3D crochet patterns. [claim:clm_072]
- CrochetPARADE uses a custom grammar to define stitches and patterns, parses and checks any user-provided pattern for correctness, then builds a virtual model that it renders in 3D. [claim:clm_073]
- The custom grammar is intended to ensure accuracy and precision in instructions, avoiding the ambiguities of plain-English crochet directions. [claim:clm_074]
- After rendering, users can 'debug' the project's shape; the platform flags overly loose or tight stitches so users can replace them before crocheting, reducing the need for blocking. [claim:clm_075]
- CrochetPARADE can export an auto-generated crochet chart with standard symbols, an SVG that shows stitch connections and labels each stitch by type, row number, and position, and 3D files importable into Blender. [claim:clm_076]
- All calculations run locally on the user's device with no data sent to a central server, with the trade-off that large patterns (tens of thousands of stitches) can take minutes or more to compute on old hardware. [claim:clm_077]
- The website and all computational components are free and open source under the GPLv3 license; the canonical repository is hosted on Codeberg (mirrored on GitHub). [claim:clm_078]
- CrochetPARADE is built on the SVG.js and three.js JavaScript libraries (three.js handles the 3D rendering). [claim:clm_079]
- CrochetBench is a dataset of 6,085 crochet patterns across 55 project categories scraped from Yarnspirations, with roughly 98% image coverage. [claim:clm_080]
- To respect copyright the authors do not redistribute raw pattern PDFs or full text, releasing only GPT-generated structured JSON annotations, reference URLs, and their scripts. [claim:clm_081]
- The CrochetPARADE DSL serves as an intermediate representation that parses input and checks for syntactic and consistency errors such as mismatched stitch counts and impossible attachments before execution. [claim:clm_082]
- Functional evaluation compares the target product image against a rendering produced from each model's executable program using DINO similarity. [claim:clm_083]
- Even the strongest tested models produce only 5-8% executable programs at the project level, showing current VLMs largely fail at executable generation. [claim:clm_084]
- DINO similarity scores of valid model renderings remain uniformly low (0.10-0.17), far below the threshold indicating faithful reproduction. [claim:clm_085]
- Step-level validity is also low, with most models achieving under 15% validity even in the first two steps of generation. [claim:clm_086]
- Across all tasks, performance sharply decreases as evaluation shifts from surface-level similarity to executable correctness, revealing limits in long-range symbolic reasoning and 3D-aware procedural synthesis. [claim:clm_087]

## Sources

- src_20260614_kw002_00 — CrochetPARADE Manual (grammar specification) — Svetlin Tassev
- src_20260614_kw002_01 — CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger) — repository README
- src_20260614_kw002_02 — CrochetBench: Can Vision-Language Models Move from Describing to Doing in the Crochet Domain?
- src_20260614_kw002_03 — AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw002_04 — Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260614_kw002_05 — Modeling Crochet Patterns with a Force-directed Graph Layout
- src_20260614_kw002_06 — KnitWit B1 Workstream Report — Crochet IR / forward & inverse prior-art survey (ChatGPT Deep Research)
- src_20260614_kw002_07 — Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260614_kw002_08 — CrochetPARADE Manual (Crochet PAttern Renderer, Analyzer, and DEbugger)
- src_20260614_kw002_09 — Representing Crochet with Stitch Meshes
- src_20260614_kw002_10 — crochetBench (official CrochetBench code + data repository)
- src_20260614_kw002_11 — CrochetPARADE source repository (Crochet PAttern Renderer, Analyzer, and DEbugger)

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
