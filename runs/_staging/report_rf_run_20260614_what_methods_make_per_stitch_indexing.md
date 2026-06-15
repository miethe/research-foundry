---
schema_version: '0.1'
type: research_report
report_id: report_20260614_what_methods_make_per_stitch_indexing
title: Stable Stitch Identity and Provable Highlight Mapping for KnitWit Pattern Playback
intent_id: intent_research_20260614_what_methods_make_per_stitch_indexing
evidence_bundle_id: pending
created_at: '2026-06-14T21:51:30-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Executive summary

The discrete per-stitch index and the row-by-row highlight it powers are the most product-ready part of the pattern-to-3D pipeline, while the 3D layout they would highlight onto is the least ready, so the two must be decoupled. [claim:clm_inf11]
**Inference:** There is a real contradiction between academic feasibility and product readiness for the indexing-and-highlight capability: the discrete stitch-index/highlight mapping is product-ready (CrochetPARADE ships exact (row,stitch) highlight and deterministic indexing today), but the underlying 3D layout it would highlight onto is NOT product-ready for an amigurumi-first mobile app (force-directed convergence is multi-minute to non-convergent at 700+ stitches), so KnitWit should de-risk by decoupling the highlight map from the layout solver - shipping correct highlighting on a fast approximate/precomputed geometry rather than gating it on an exact physics layout - decision impact high. [claim:clm_inf11]
Three distinct stitch-identity schemes appear across the surveyed tools, and the graph-node insertion-point scheme is the most edit-stable because identity is carried by structural connectivity rather than by a recomputed positional counter. [claim:clm_inf01]
**Inference:** Positional (row,stitch|global) indices such as CrochetPARADE's (4,23|410) are provably unstable under inc/dec or insertion edits because the global counter renumbers every downstream stitch, so KnitWit must NOT use a recomputed positional integer as the persistent stitch key and should instead mint a stable per-op GUID at op-creation time, retaining the positional label only as a derived, display-time projection. [claim:clm_inf02]
**Inference:** The Crochet IR v0.1 starter schema (pattern/pieces/rounds/ops with op enum and expected_stitch_count) currently lacks any persistent per-op identifier field, which is the single highest-leverage schema gap for highlight stability; KnitWit should add a required immutable op-level stitch_id (UUID minted on op creation) plus a derived round_index/pos_in_round projection so that highlighting and round-trip key off the GUID while the human-readable label is recomputed on demand. [claim:clm_inf03]

## Stitch-identity scheme comparison

**Inference:** Across the surveyed tools, three distinct stitch-identity schemes exist - positional (row,stitch|global) labels (CrochetPARADE), graph-node/insertion-point identity with layer+start+prev/next addressing (Seitz/HPI Digital Crochet), and current-loop/edge-typed stitch-mesh identity (Guo et al., Narayanan et al.) - and for an edit-tolerant interactive preview the graph-node insertion-point scheme is the most stable because identity is carried by structural connectivity rather than by a recomputed positional counter. [claim:clm_inf01]

| Scheme | Identity carrier | Surveyed source | Edit stability | Evidence |
|--------|------------------|-----------------|----------------|----------|
| Positional (row, per-row / global) | A recomputed global counter; both row and stitch counters start from 0, e.g. (4,23|410) | CrochetPARADE | Renumbers every downstream stitch on any inc/dec or insertion | [claim:clm_016] |
| Positional counting rule | The global counter counts non-stitches such as 'sk' but excludes internal stitches like bobble/popcorn sub-stitches | CrochetPARADE | Counting inconsistency is a direct off-by-one source | [claim:clm_017] |
| Graph node = insertion point | Graph nodes are insertion points rather than stitches directly, decoupling stitch/loop identity from a positional stitch sequence | Digital Crochet / HPI | Identity persists because it is structural, not positional | [claim:clm_027] |
| Graph node addressing | Each node carries its layer integer, a 'start' boolean for the first node of its layer, plus previous/next references and an array of nodes it inserts into | HPI Digital Crochet | Layer-plus-position identity survives renumbering | [claim:clm_057] |
| Current-loop / typed-edge | A special edge type captures the 'current loop' held on the crochet hook during fabrication | Guo et al. stitch meshes | Identity bound to fabrication-order loop, not position | [claim:clm_036] |
| Yarn/loop connection graph | Two distinct connection types - yarn connections (sequentially adjacent on the needle) and loop connections (pulled through each other) - form the structural basis for per-stitch indexing | Gray et al. knitting graph | Structural connectivity is the indexing basis | [claim:clm_044] |

The increase method is encoded as multiple incoming insert edges and the decrease method as multiple outgoing insert edges, so connectivity rather than position carries the shaping semantics. [claim:clm_026]
The editor requires patterns to be built linearly in the order they would be crocheted, so node creation order equals the canonical work/traversal order. [claim:clm_028]
All crochet stitches, despite differing in topology and texture, share the property that they start and end with a single leading loop on the hook, giving a well-defined sequential yarn-path order. [claim:clm_037]
The method encodes crochet construction dependencies as four directed edge labels: Next and Previous handle short-term consecutive-stitch dependencies, while Future and Past handle long-term loop-through-fabric dependencies. [claim:clm_039]

### Recommended scheme for KnitWit

**Inference:** Positional (row,stitch|global) indices such as CrochetPARADE's (4,23|410) are provably unstable under inc/dec or insertion edits because the global counter renumbers every downstream stitch, so KnitWit must NOT use a recomputed positional integer as the persistent stitch key and should instead mint a stable per-op GUID at op-creation time, retaining the positional label only as a derived, display-time projection. [claim:clm_inf02]
**Inference:** The Crochet IR v0.1 starter schema (pattern/pieces/rounds/ops with op enum and expected_stitch_count) currently lacks any persistent per-op identifier field, which is the single highest-leverage schema gap for highlight stability; KnitWit should add a required immutable op-level stitch_id (UUID minted on op creation) plus a derived round_index/pos_in_round projection so that highlighting and round-trip key off the GUID while the human-readable label is recomputed on demand. [claim:clm_inf03]

## IR traversal-to-geometry mapping

**Inference:** IR traversal order can be mapped to rendered geometry without drift by treating the linear op-creation order as the canonical Hamiltonian traversal and emitting exactly one mesh instance (or vertex group) per op in that order, because every surveyed system that guarantees correct stitch-to-geometry correspondence (CrochetPARADE sequential attachment, HPI linear construction, Gray et al. Hamiltonian/Eulerian recovery) relies on a single deterministic 1:1 traversal rather than re-deriving positions independently. [claim:clm_inf04]
The model represents a crochet pattern as a graph in which stitch insertion points are nodes and the connections between stitches are edges, so traversing the graph follows the yarn path through every stitch. [claim:clm_051]
Each stitch becomes a node and physical connections between stitches become edges, with horizontal edges marking stitches made one immediately after the other and vertical edges marking the stitch worked into the one below. [claim:clm_002]
Stitches on a row are automatically attached one-by-one to consecutive stitches in the previous row/round, and turning at row end is accounted for automatically. [claim:clm_018]
A Hamiltonian path encodes the stitch-creation order and the yarn's physical flow is recovered as an Eulerian path derived from it, linking logical stitch index to physical yarn traversal. [claim:clm_045]
Edges are typed: a 'previous' edge encodes stitch order while an 'insert' edge encodes the worked-into relationship from the current stitch to the insertion point it was crocheted into. [claim:clm_052]
Rows and rounds are unified into a single concept called 'layers,' requiring no structural change in the graph, and the layer number is stored as a property on each node. [claim:clm_054]
The SVG export identifies each stitch by its type, row number, and position within a row, presenting the same information as a standard crochet diagram so it can serve as an alternative crocheting guide. [claim:clm_011]

### Concrete failure modes and mitigations

**Inference:** The dominant off-by-one / drift failure modes for the highlight map are: (a) the global counter including non-stitches like sk while excluding internal bobble/popcorn sub-stitches, (b) spiral-vs-joined-round numbering ambiguity at the round seam, and (c) inc/dec changing per-round population mid-traversal; each is mitigated cheaply at IR level by storing an explicit per-op boolean for counts_in_index, an explicit round-closure/seam op, and deriving pos_in_round from a running count keyed to GUIDs rather than to raw line position. [claim:clm_inf05]

| Failure mode | Origin in evidence | IR-level mitigation | Evidence |
|--------------|------------------------|---------------------|----------|
| Off-by-one (counting rule) | The global stitch counter counts non-stitches such as 'sk' but excludes internal stitches like those inside bobbles or popcorns | Per-op counts_in_index boolean | [claim:clm_017] |
| Spiral-vs-joined seam ambiguity | Rows and rounds are unified into 'layers' with no structural change, and turning at row end is auto-handled, so the seam is implicit | Explicit round-closure/seam op | [claim:clm_054] |
| Drift from inc/dec | The DSL uses sc2inc for two single crochets worked into one stitch and sc2tog for a decrease, so per-round population changes mid-traversal | Derive pos_in_round from a GUID-keyed running count | [claim:clm_022] |
| Mirroring / handedness | If the model looks inside-out or follows left-hand directions, the user changes the random start seed via 'DOT: start=2' because inside/outside is picked at random | Presentation-layer transform, not reindexing | [claim:clm_021] |
| Attachment-direction parity | When attaching to a base row A, an even stitch index attaches to the next stitch of A while an odd index attaches to the previous stitch on A | Store explicit insert-target references per op | [claim:clm_019] |

**Inference:** Left-handed mirroring and US/UK term differences should be handled as presentation-layer transforms over a single canonical right-handed, US-term IR rather than by reindexing, because CrochetPARADE already shows handedness is a downstream rendering choice (a random start seed flips inside/outside and left/right without changing the pattern) and the stitch-mesh leading-loop yarn-path order is direction-defined but term-agnostic; reindexing for handedness would break the persistent stitch IDs and the round-trip key. [claim:clm_inf09]

## Highlight-mapping correctness metric and test protocol

**Inference:** A reproducible highlight-mapping correctness metric for KnitWit is a Highlight Index Agreement (HIA) rate - the fraction of (round,stitch) pattern steps whose highlighted geometry instance equals the ground-truth index-map entry - computed over a labeled reference pattern set, and the Desired Edge Length (DEL = RMS relative edge-length error) metric from Gray et al. is the right complementary geometry-fidelity gate; KnitWit should adopt HIA as the primary acceptance gate (recommended pass threshold 100% exact match on the reference set, since highlight mapping is discrete and any mismatch is a visible bug) and DEL as a secondary spatial-plausibility check. [claim:clm_inf06]
The paper proposes a Desired Edge Length (DEL) metric defined as the root-mean-square of the relative edge-length error, where 0 means perfect preservation of target lengths, giving a candidate per-stitch correctness/drift measure. [claim:clm_046]
Row/stitch highlighting is done via ctrl+f (entering a row number or row,stitch pair), and stitches can be revealed one by one via the 'a' control. [claim:clm_023]
The authors' stated motivation is to expedite error detection and pattern validation: visualizing the generated pattern helps catch too many/too few stitches, adornments in the wrong spot, or an unintended shape. [claim:clm_050]

### Reproducible reference pattern set

**Inference:** The labeled reference pattern set for the HIA acceptance gate should be assembled from the public-domain CrochetPARADE showcase patterns plus the cube/sphere/Stanford-bunny stitch-mesh exemplars, because these are the only sources here with both a published deterministic stitch index (CrochetPARADE (row,stitch|global)) and reproducible generated geometry (stitch-mesh tiles), giving a ready ground-truth index map without KnitWit having to hand-author one from scratch. [claim:clm_inf07]
Showcase patterns are in the public domain while the user manual (including the grammar description) is released under Creative Commons BY-NC-SA, and the grammar itself is uncopyrightable and public domain. [claim:clm_010]
The crochet face set was used to generate stitch-mesh patterns for a cube, a sphere, and the Stanford bunny, with the sphere and bunny derived from triangle meshes via the Narayanan et al. 2019 pipeline. [claim:clm_043]
CrochetPARADE's website and all computational components are free and open source under GPLv3, ensuring the platform stays free and open in perpetuity. [claim:clm_009]

| Protocol element | Specification | Evidence |
|------------------|---------------|----------|
| Reference patterns | Public-domain CrochetPARADE showcase patterns plus cube/sphere/Stanford-bunny stitch-mesh exemplars | [claim:clm_inf07] |
| Ground-truth index map | Each stitch carries an unambiguous (type, row, position) label from the deterministic (row,stitch|global) index | [claim:clm_016] |
| Primary metric (HIA) | Fraction of (round,stitch) steps whose highlighted geometry equals the ground-truth entry; recommended pass threshold is 100% exact match | [claim:clm_inf06] |
| Secondary metric (DEL) | Root-mean-square of relative edge-length error, 0 = perfect target-length preservation, used as a spatial-plausibility check | [claim:clm_046] |

## 'Ghost next row' overlay and round-trip identity

**Inference:** The 'ghost next row' overlay can be derived incrementally and cheaply from the index map - by projecting only the next round's ops onto the existing positions of their previous-round insertion targets - rather than re-running the full force-directed layout, because layout convergence is the documented bottleneck (CrochetPARADE multi-minute on tens-of-thousands of stitches; Greer/Mould 700-800-stitch pieces failing to converge after 2+ minutes; Gray et al. up to 40,906s), whereas the next-row attachment relation is already O(1) per stitch in the IR. [claim:clm_inf08]
When attaching to a base row A, an even stitch index attaches to the next stitch of A in A's crochet direction, while an odd index attaches to the previous stitch on A. [claim:clm_019]
Each node carries explicit addressing/traversal properties — its layer integer, a 'start' boolean marking the first node of its layer, plus previous/next references and an array of nodes it inserts into — giving a layer-plus-position identity per stitch. [claim:clm_057]
All calculations run locally on the user's device with no central-server collection or internet transmission, at the cost of sluggish performance and multi-minute calculations for patterns of tens of thousands of stitches. [claim:clm_013]
Interactive 3D features include animating the pattern-creation process, highlighting and hiding selected stitches, changing yarn thickness and color, and accessing per-stitch information by hovering. [claim:clm_012]

### Persistent identity for inverse round-trip

**Inference:** For persistent stitch identity that survives round-trip with the inverse (mesh-to-pattern) engine, KnitWit should adopt the stitch-mesh current-loop / typed-edge identity (Next/Previous short-term, Future/Past long-term) as the interchange key between the forward IR and the inverse engine, because that representation is the only surveyed scheme proven to support both pattern->geometry generation and geometry->pattern derivation and to be edit-preserving (Narayanan et al. knittability-preserving edits; Wooly Graphs' explicit bidirectional analyze/generate framework). [claim:clm_inf10]
The system generates knittable augmented stitch meshes from 3D models, supports edits that preserve knittability, and schedules the execution order and location of each face for production on a knitting machine. [claim:clm_032]
The augmented stitch mesh data structure stores low-level knitting operations per-face and encodes the dependencies between faces using directed edge labels. [claim:clm_031]
The framework is explicitly designed both to analyze existing knitting objects from their graphs and to generate knitting objects from graphs, establishing a rigorous bidirectional mapping between graph structure and knit structure. [claim:clm_061]
Faces use short-term (orange) and long-term (purple) edge types, where the leading loop and free yarn cross the short-term edges and the long-term edges are crossed only by loops. [claim:clm_040]
Increases are realized by an 'inc' utility face that splits one future edge into two future edges, while decreases use sc2tog (two past edges to one future) and sc3tog (three past edges). [claim:clm_041]

## Academic feasibility vs product readiness

**Inference:** There is a real contradiction between academic feasibility and product readiness for the indexing-and-highlight capability: the discrete stitch-index/highlight mapping is product-ready (CrochetPARADE ships exact (row,stitch) highlight and deterministic indexing today), but the underlying 3D layout it would highlight onto is NOT product-ready for an amigurumi-first mobile app (force-directed convergence is multi-minute to non-convergent at 700+ stitches), so KnitWit should de-risk by decoupling the highlight map from the layout solver - shipping correct highlighting on a fast approximate/precomputed geometry rather than gating it on an exact physics layout - decision impact high. [claim:clm_inf11]
Force-directed layouts are slow: simple pieces (legs 318 stitches, arms 264 stitches) converged in under 5 seconds, while larger pieces (bunny head 798 stitches, body 708 stitches) did not converge even after running for over two minutes. [claim:clm_008]
The exact-length layout is far slower than baselines (Antique Diamonds 25s vs SFDP 0.074s; Triangle-5 at 1539 nodes took 40,906s vs SFDP 1.01s), evidence it does not scale to interactive mobile use without approximation. [claim:clm_049]
On simple beginner-level patterns the models were accurate in shape and size to their real-world counterparts, though similar rather than identical, with some differences attributed to the uniform edge-length-of-1 assumption. [claim:clm_005]
Across seven real knitting patterns (90 to 1183 nodes) the proposed method beat SFDP, ImPrEd, and KnitGrid on DEL; on Antique Diamonds it scored 0.07 versus 0.33 (SFDP), 0.55 (ImPrEd), and 0.20 (KnitGrid). [claim:clm_048]
CrochetPARADE uses a custom language grammar to define stitches and stitch patterns, parsing and checking patterns for correctness before building and rendering a 3D virtual model, eliminating the ambiguity of plain-English instructions. [claim:clm_015]
A prototype editor lets designers create patterns in 2D and view them in 3D; a user study showed the language expresses both 2D and 3D patterns and removes ambiguities of current notations. [claim:clm_025]
In a think-aloud study with six professional crochet designers, all but one reproduced the test pattern in the 2D editor, and four said reproducing it surfaced previously hidden ambiguities. [claim:clm_029]
Only five crochet stitches — chain, slip stitch, single crochet, sc2tog, and sc3tog — were actually modeled by the method, making the tile set explicitly incomplete. [claim:clm_042]
Determining whether a knit object of a given class exists for a given graph is NP-hard in general, but specific cases admit linear- and polynomial-time algorithms by exploiting properties of common knitting techniques. [claim:clm_060]

## Contradictions & open disagreements

**Inference:** There is a real contradiction between academic feasibility and product readiness for the indexing-and-highlight capability: the discrete stitch-index/highlight mapping is product-ready (CrochetPARADE ships exact (row,stitch) highlight and deterministic indexing today), but the underlying 3D layout it would highlight onto is NOT product-ready for an amigurumi-first mobile app (force-directed convergence is multi-minute to non-convergent at 700+ stitches), so KnitWit should de-risk by decoupling the highlight map from the layout solver - shipping correct highlighting on a fast approximate/precomputed geometry rather than gating it on an exact physics layout - decision impact high. [claim:clm_inf11]
**Inference:** Across the surveyed tools, three distinct stitch-identity schemes exist - positional (row,stitch|global) labels (CrochetPARADE), graph-node/insertion-point identity with layer+start+prev/next addressing (Seitz/HPI Digital Crochet), and current-loop/edge-typed stitch-mesh identity (Guo et al., Narayanan et al.) - and for an edit-tolerant interactive preview the graph-node insertion-point scheme is the most stable because identity is carried by structural connectivity rather than by a recomputed positional counter. [claim:clm_inf01]

| Disagreement | Side A | Side B | Resolution | Decision impact | Evidence |
|--------------|--------|--------|-------------------|-----------------|----------|
| Highlight feasibility vs layout feasibility | CrochetPARADE ships exact (row,stitch) highlight and per-stitch interaction today | Force-directed layout is multi-minute to non-convergent at 700+ stitches and only approximate when it does converge | Decouple the highlight map from the exact layout solver | high | [claim:clm_inf11] |
| Identity carrier choice | Positional (row,stitch|global) index is the shipped, human-readable label | Structural graph-node / current-loop identity is edit-stable | Use a GUID structural key with positional label as a derived projection | high | [claim:clm_inf01] |
| Layout speed vs fidelity | Exact-length DEL-optimal layout wins on accuracy across seven patterns | The exact-length layout is orders of magnitude slower and does not scale interactively | Precompute or approximate geometry; reserve exact layout for offline validation | medium | [claim:clm_049] |

## Implications

**Inference:** The Crochet IR v0.1 starter schema (pattern/pieces/rounds/ops with op enum and expected_stitch_count) currently lacks any persistent per-op identifier field, which is the single highest-leverage schema gap for highlight stability; KnitWit should add a required immutable op-level stitch_id (UUID minted on op creation) plus a derived round_index/pos_in_round projection so that highlighting and round-trip key off the GUID while the human-readable label is recomputed on demand. [claim:clm_inf03]
**Inference:** IR traversal order can be mapped to rendered geometry without drift by treating the linear op-creation order as the canonical Hamiltonian traversal and emitting exactly one mesh instance (or vertex group) per op in that order, because every surveyed system that guarantees correct stitch-to-geometry correspondence (CrochetPARADE sequential attachment, HPI linear construction, Gray et al. Hamiltonian/Eulerian recovery) relies on a single deterministic 1:1 traversal rather than re-deriving positions independently. [claim:clm_inf04]
**Inference:** The 'ghost next row' overlay can be derived incrementally and cheaply from the index map - by projecting only the next round's ops onto the existing positions of their previous-round insertion targets - rather than re-running the full force-directed layout, because layout convergence is the documented bottleneck (CrochetPARADE multi-minute on tens-of-thousands of stitches; Greer/Mould 700-800-stitch pieces failing to converge after 2+ minutes; Gray et al. up to 40,906s), whereas the next-row attachment relation is already O(1) per stitch in the IR. [claim:clm_inf08]

## Risks

**Speculation:** The highest-severity risk to KnitWit's highlight feature is UX-trust erosion (severity high, likelihood medium) from off-by-one drift introduced when an inc/dec edit silently renumbers positional labels mid-session; the concrete mitigation is to gate every parameter edit behind the HIA acceptance test against the stored ground-truth index map and to surface a stitch-count validator (expected_stitch_count vs realized) so a mismatch is caught before render, mirroring CrochetPARADE's blue/red tension flags as a precedent for inline correctness signalling. [claim:clm_spec01]
Stitches over- or under-stretched by more than ~15% relative to baseline height are flagged (blue=too loose, red=too stretched), and the engine converges to within ~10% of requested stitch lengths under default settings. [claim:clm_020]

| Risk | Severity | Likelihood | Mitigation | Evidence |
|------|----------|------------|------------|----------|
| UX-trust erosion from silent off-by-one renumbering on inc/dec edits | high | medium | Gate every parameter edit behind the HIA acceptance test plus an expected_stitch_count-vs-realized validator | [claim:clm_spec01] |
| Mobile performance trap from exact force-directed layout | high | high | Decouple highlighting from the layout solver; ship on precomputed/approximate geometry | [claim:clm_inf11] |
| Tension/drift mis-signalling at render time | medium | medium | Reuse CrochetPARADE's blue/red over/under-stretch flag precedent for inline correctness signals | [claim:clm_020] |

## Prototype experiments & decision-gate relevance

**Speculation:** The two prototype experiments that most de-risk gates G2 (Crochet-IR viability) and G3 (pattern-to-3D viability) for highlighting are a row-highlight-export harness that emits the GUID-keyed index map plus the HIA evaluator over the CrochetPARADE/stitch-mesh reference set, and an IR->stitch-graph converter that mints the persistent op GUIDs; building these before any physics-accurate layout work is the recommended next step because they validate identity stability and highlight correctness independently of the unconverged layout solver. [claim:clm_spec02]
**Inference:** The Crochet IR v0.1 starter schema (pattern/pieces/rounds/ops with op enum and expected_stitch_count) currently lacks any persistent per-op identifier field, which is the single highest-leverage schema gap for highlight stability; KnitWit should add a required immutable op-level stitch_id (UUID minted on op creation) plus a derived round_index/pos_in_round projection so that highlighting and round-trip key off the GUID while the human-readable label is recomputed on demand. [claim:clm_inf03]

| Gate | What the findings de-risk | Next prototype experiment | Evidence |
|------|---------------------------|----------------------------------------|----------|
| G2 (Crochet-IR viability) | Adding a GUID op-id plus derived projection closes the highest-leverage schema gap | IR->stitch-graph converter that mints persistent op GUIDs | [claim:clm_spec02] |
| G3 (pattern-to-3D viability) | Highlight correctness can be validated independently of the unconverged layout solver | Row-highlight-export harness emitting the GUID-keyed index map plus an HIA evaluator | [claim:clm_spec02] |
| G3 (pattern-to-3D viability) | Ghost-next-row is an O(1) per-stitch projection rather than a full re-layout | Incremental next-round projection prototype keyed off insert-target references | [claim:clm_inf08] |

## Open questions

- Which exact public-domain CrochetPARADE showcase patterns and stitch-mesh exemplars should seed the first labeled HIA reference set?
- What approximate/precomputed geometry backend best replaces the exact force-directed layout for amigurumi-scale pieces on mobile?
- Should the canonical IR fix US right-handed terminology and treat all UK/left-handed output purely as presentation transforms?
- What HIA failure rate, if any, is tolerable before a parameter edit is blocked from rendering?

## Sources

- src_20260614_kw005_04: Modeling crochet patterns with a force-directed graph layout
- src_20260614_kw005_05: CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger) — Repository README
- src_20260614_kw005_07: CrochetPARADE Manual (Crochet PAttern Renderer, Analyzer, and DEbugger)
- src_20260614_kw005_02: Digital Crochet: Toward a Visual Language for Pattern Description
- src_20260614_kw005_03: Visual Knitting Machine Programming
- src_20260614_kw005_00: Representing Crochet with Stitch Meshes
- src_20260614_kw005_08: A Graph Model and a Layout Algorithm for Knitting Patterns
- src_20260614_kw005_01: Language and Tool Support for 3D Crochet Patterns: Virtual Crochet with a Graph Structure (HPI Technical Report 137)
- src_20260614_kw005_06: Wooly Graphs: A Mathematical Framework for Knitting
