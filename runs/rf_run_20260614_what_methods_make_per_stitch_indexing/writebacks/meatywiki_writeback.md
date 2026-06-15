---
id: mwb_20260614_stable_stitch_identity_and_provable_highlight
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_methods_make
target_page: meatywiki/sources/stable_stitch_identity_and_provable_highlight.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_methods_make_per_stitch_indexing:
  62 supported claim(s) across 9 source card(s).'
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
links:
  source_cards:
  - src_20260614_kw005_00
  - src_20260614_kw005_01
  - src_20260614_kw005_02
  - src_20260614_kw005_03
  - src_20260614_kw005_04
  - src_20260614_kw005_05
  - src_20260614_kw005_06
  - src_20260614_kw005_07
  - src_20260614_kw005_08
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Stable Stitch Identity and Provable Highlight Mapping for KnitWit Pattern Playback

## Summary

Source note distilled from research run rf_run_20260614_what_methods_make_per_stitch_indexing: 62 supported claim(s) across 9 source card(s).

## Key claims

- The method translates a written crochet pattern into a graph and obtains a force-directed graph layout, producing a 3D model that matches the hand-crocheted pattern in shape and size without physically crocheting. [claim:clm_001]
- Each stitch becomes a node and physical connections between stitches become edges, with horizontal edges marking stitches made one immediately after the other and vertical edges marking the stitch worked into the one below. [claim:clm_002]
- The layout follows Isenburg et al.'s force-directed algorithm, which inflates a planar graph by assigning each edge a length and minimizing overall curvature to maximize volume - analogous to stuffing a crocheted shell. [claim:clm_003]
- The layout is a non-linear least-squares optimization minimizing two energy functions - one controlling edge lengths (each edge assumed length one) and one measuring local curvature at each node (assumed minimal). [claim:clm_004]
- On simple beginner-level patterns the models were accurate in shape and size to their real-world counterparts, though similar rather than identical, with some differences attributed to the uniform edge-length-of-1 assumption. [claim:clm_005]
- Shaping effects such as pulling tight to create a dimpling effect are modeled with additional constraint edges, recreating a pulling-in effect by linking the first and last node, paralleling how a crocheter pulls the yarn until satisfied with the shape. [claim:clm_006]
- The application is oriented toward amigurumi - dense uniform stitches worked in continuous rounds to make stuffed 3D figures - but the authors state it could be extended to clothing or other crochet styles. [claim:clm_007]
- Force-directed layouts are slow: simple pieces (legs 318 stitches, arms 264 stitches) converged in under 5 seconds, while larger pieces (bunny head 798 stitches, body 708 stitches) did not converge even after running for over two minutes. [claim:clm_008]
- CrochetPARADE's website and all computational components are free and open source under GPLv3, ensuring the platform stays free and open in perpetuity. [claim:clm_009]
- Showcase patterns are in the public domain while the user manual (including the grammar description) is released under Creative Commons BY-NC-SA, and the grammar itself is uncopyrightable and public domain. [claim:clm_010]
- The SVG export identifies each stitch by its type, row number, and position within a row, presenting the same information as a standard crochet diagram so it can serve as an alternative crocheting guide. [claim:clm_011]
- Interactive 3D features include animating the pattern-creation process, highlighting and hiding selected stitches, changing yarn thickness and color, and accessing per-stitch information by hovering. [claim:clm_012]
- All calculations run locally on the user's device with no central-server collection or internet transmission, at the cost of sluggish performance and multi-minute calculations for patterns of tens of thousands of stitches. [claim:clm_013]
- The project is dual-hosted, with the primary repository on Codeberg and a mirror on GitHub, and the live platform at crochetparade.org. [claim:clm_014]
- CrochetPARADE uses a custom language grammar to define stitches and stitch patterns, parsing and checking patterns for correctness before building and rendering a 3D virtual model, eliminating the ambiguity of plain-English instructions. [claim:clm_015]
- CrochetPARADE indexes each stitch as (row, per-row stitch | global stitch number), e.g. (4,23|410), with both row and stitch counters starting from 0. [claim:clm_016]
- The global stitch counter counts non-stitches such as 'sk' but excludes internal stitches like those inside bobbles or popcorns. [claim:clm_017]
- Stitches on a row are automatically attached one-by-one to consecutive stitches in the previous row/round, and turning at row end is accounted for automatically. [claim:clm_018]
- When attaching to a base row A, an even stitch index attaches to the next stitch of A in A's crochet direction, while an odd index attaches to the previous stitch on A. [claim:clm_019]
- Stitches over- or under-stretched by more than ~15% relative to baseline height are flagged (blue=too loose, red=too stretched), and the engine converges to within ~10% of requested stitch lengths under default settings. [claim:clm_020]
- If the model looks inside-out or follows left-hand directions, the user changes the random start seed via 'DOT: start=2' (or other values) because inside/outside is picked at random. [claim:clm_021]
- The DSL uses sc2inc for two single crochets worked into one stitch and sc2tog for a decrease combining two; each new line is a new row/round. [claim:clm_022]
- Row/stitch highlighting is done via ctrl+f (entering a row number or row,stitch pair), and stitches can be revealed one by one via the 'a' control. [claim:clm_023]
- The paper proposes a first visual, domain-specific, graph-based language for representing crochet patterns. [claim:clm_024]
- A prototype editor lets designers create patterns in 2D and view them in 3D; a user study showed the language expresses both 2D and 3D patterns and removes ambiguities of current notations. [claim:clm_025]
- Stitch connectivity carries the semantics: the increase method is encoded as multiple incoming insert edges and the decrease method as multiple outgoing insert edges. [claim:clm_026]
- Graph nodes are insertion points rather than stitches directly, decoupling stitch/loop identity from a positional stitch sequence. [claim:clm_027]
- The editor requires patterns to be built linearly in the order they would be crocheted, so node creation order equals the canonical work/traversal order. [claim:clm_028]
- In a think-aloud study with six professional crochet designers, all but one reproduced the test pattern in the 2D editor, and four said reproducing it surfaced previously hidden ambiguities. [claim:clm_029]
- The paper is authored by Vidya Narayanan, Kui Wu, Cem Yuksel, and James McCann and was published in ACM Transactions on Graphics (SIGGRAPH 2019), Volume 38, Issue 4, Article 63, on 12 July 2019. [claim:clm_030]
- The augmented stitch mesh data structure stores low-level knitting operations per-face and encodes the dependencies between faces using directed edge labels. [claim:clm_031]
- The system generates knittable augmented stitch meshes from 3D models, supports edits that preserve knittability, and schedules the execution order and location of each face for production on a knitting machine. [claim:clm_032]
- Each face is a fragment of a knitting program that operates on the yarns and loops from its in edges to produce the yarns and loops indicated by its out edges. [claim:clm_033]
- The directed edge labels provide a type signature -- the input and output loop and yarn counts -- for each knitting program fragment. [claim:clm_034]
- The directed edge labels induce a directed graph on the faces, which is used to check for dependency cycles; an in edge may connect only to an out edge of the same type. [claim:clm_035]
- The paper adapts the stitch-mesh tile paradigm to crochet by introducing a special edge type that captures the 'current loop' — the loop held on the crochet hook during fabrication. [claim:clm_036]
- All crochet stitches, despite differing in topology and texture, share the property that they start and end with a single leading loop on the hook, giving a well-defined sequential yarn-path order. [claim:clm_037]
- International crochet notation is inconvenient for computer-based authoring because its symbols carry no explicit information on how yarn is used within each stitch. [claim:clm_038]
- The method encodes crochet construction dependencies as four directed edge labels: Next and Previous handle short-term consecutive-stitch dependencies, while Future and Past handle long-term loop-through-fabric dependencies. [claim:clm_039]
- Faces use short-term (orange) and long-term (purple) edge types, where the leading loop and free yarn cross the short-term edges and the long-term edges are crossed only by loops. [claim:clm_040]
- Increases are realized by an 'inc' utility face that splits one future edge into two future edges, while decreases use sc2tog (two past edges to one future) and sc3tog (three past edges). [claim:clm_041]
- Only five crochet stitches — chain, slip stitch, single crochet, sc2tog, and sc3tog — were actually modeled by the method, making the tile set explicitly incomplete. [claim:clm_042]
- The crochet face set was used to generate stitch-mesh patterns for a cube, a sphere, and the Stanford bunny, with the sphere and bunny derived from triangle meshes via the Narayanan et al. 2019 pipeline. [claim:clm_043]
- The stitch graph encodes two distinct connection types: yarn connections (loops sequentially adjacent on the needle) and loop connections (loops pulled through each other), which is the structural basis for per-stitch indexing. [claim:clm_044]
- A Hamiltonian path encodes the stitch-creation order and the yarn's physical flow is recovered as an Eulerian path derived from it, linking logical stitch index to physical yarn traversal. [claim:clm_045]
- The paper proposes a Desired Edge Length (DEL) metric defined as the root-mean-square of the relative edge-length error, where 0 means perfect preservation of target lengths, giving a candidate per-stitch correctness/drift measure. [claim:clm_046]
- Layout refinement uses three forces — an attractive/repulsive edge-length force, a collision force, and a universal electrostatic repulsion — and any move that introduces an edge crossing is rejected (the node is kept in place). [claim:clm_047]
- Across seven real knitting patterns (90 to 1183 nodes) the proposed method beat SFDP, ImPrEd, and KnitGrid on DEL; on Antique Diamonds it scored 0.07 versus 0.33 (SFDP), 0.55 (ImPrEd), and 0.20 (KnitGrid). [claim:clm_048]
- The exact-length layout is far slower than baselines (Antique Diamonds 25s vs SFDP 0.074s; Triangle-5 at 1539 nodes took 40,906s vs SFDP 1.01s), evidence it does not scale to interactive mobile use without approximation. [claim:clm_049]
- The authors' stated motivation is to expedite error detection and pattern validation: visualizing the generated pattern helps catch too many/too few stitches, adornments in the wrong spot, or an unintended shape. [claim:clm_050]
- The model represents a crochet pattern as a graph in which stitch insertion points are nodes and the connections between stitches are edges, so traversing the graph follows the yarn path through every stitch. [claim:clm_051]
- Edges are typed: a 'previous' edge encodes stitch order while an 'insert' edge encodes the worked-into relationship from the current stitch to the insertion point it was crocheted into. [claim:clm_052]
- Increases and decreases are modeled by edge multiplicity: a node with multiple out-going insert edges is an increasing stitch, and a node receiving multiple incoming insert edges is the one being increased (decrease being the inverse). [claim:clm_053]
- Rows and rounds are unified into a single concept called 'layers,' requiring no structural change in the graph, and the layer number is stored as a property on each node. [claim:clm_054]
- Crochetability is enforced structurally: a slip-stitch / 'previous' edge can only point at a node that already existed when the connection was made, and the prototype UI only permits valid stitch connections so every pattern produced is always crochetable. [claim:clm_055]
- The prototype lays out and positions stitch nodes in 3D using a force-directed graph layout: the '3D Force-Directed Graph' library built on Three.js and WebGL with a D3 variant as physics engine, applying Dwyer's force layout algorithm. [claim:clm_056]
- Each node carries explicit addressing/traversal properties — its layer integer, a 'start' boolean marking the first node of its layer, plus previous/next references and an array of nodes it inserts into — giving a layer-plus-position identity per stitch. [claim:clm_057]
- The paper proposes three distinct graph models for any arbitrary knit object: a simple undirected graph, a simple directed graph, and a directed multigraph, each carrying a knot-theoretic component. [claim:clm_058]
- From these models the authors derive natural categories tied to the complexity of knitting structures, providing a basis for bounding which structural classes are tractable to reason about. [claim:clm_059]
- Determining whether a knit object of a given class exists for a given graph is NP-hard in general, but specific cases admit linear- and polynomial-time algorithms by exploiting properties of common knitting techniques. [claim:clm_060]
- The framework is explicitly designed both to analyze existing knitting objects from their graphs and to generate knitting objects from graphs, establishing a rigorous bidirectional mapping between graph structure and knit structure. [claim:clm_061]
- The framework is authored by Kathryn Gray, Brian Bell, Diana Sieper, Stephen Kobourov, Falk Schreiber, Karsten Klein, and Seokhee Hong, submitted to arXiv (2407.00511) on 29 June 2024. [claim:clm_062]

## Sources

- src_20260614_kw005_00 — Representing Crochet with Stitch Meshes
- src_20260614_kw005_01 — Language and Tool Support for 3D Crochet Patterns: Virtual Crochet with a Graph Structure (HPI Technical Report 137)
- src_20260614_kw005_02 — Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260614_kw005_03 — Visual Knitting Machine Programming
- src_20260614_kw005_04 — Modeling crochet patterns with a force-directed graph layout
- src_20260614_kw005_05 — CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger) — Repository README
- src_20260614_kw005_06 — Wooly Graphs: A Mathematical Framework for Knitting
- src_20260614_kw005_07 — CrochetPARADE Manual (Crochet PAttern Renderer, Analyzer, and DEbugger)
- src_20260614_kw005_08 — A Graph Model and a Layout Algorithm for Knitting Patterns

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
