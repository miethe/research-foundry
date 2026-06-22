---
id: mwb_20260622_dr_knitwit_stitch_highlight_rendering_overlay
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_is_the
target_page: meatywiki/decisions/knitwit_stitch_highlight_rendering_overlay_techn.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_what_is_the_most_performant_mobile: clm_009 says keep
  opaque objects non-blended; clm_006 shows blending kills early-ZS/FPK; clm_008/clm_045 recommend split'
key_claims:
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf07
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
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf10
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_009
  - clm_012
  - clm_006
  - clm_008
  - clm_045
  - clm_007
  - clm_044
  - clm_049
  - clm_017
  - clm_029
  - clm_001
  - clm_011
  - clm_048
  - clm_047
  - clm_021
  - clm_002
  - clm_005
  - clm_031
  - clm_032
  - clm_034
  - clm_035
  - clm_013
  - clm_016
  - clm_024
  - clm_026
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: KnitWit Stitch-Highlight Rendering: Overlay Technique and Incremental-Update Benchmark for Mobile Playback

## Context

- Collapsing many objects into fewer, larger draw calls generally improves performance; e.g. paint 1000 sprites with a single drawArrays() or drawElements() call. [claim:clm_001]
- Drawing from static, unchanging VAOs is faster than mutating a VAO per draw because browsers can cache fetch limits for unchanged VAOs but must revalidate and recalculate limits when VAOs change. [claim:clm_002]
- Almost any change to a framebuffer object's attachment bindings invalidates its framebuffer completeness, so hot framebuffers should be set up ahead of time. [claim:clm_003]
- Delete GPU objects eagerly rather than waiting for the garbage collector, because at the API level 'deleting' only releases the handle that refers to the underlying object, which is freed only once unused in the implementation. [claim:clm_004]
- Texture atlasing (packing multiple images into one texture) and degenerate triangles (zero-area triangles that get skipped) let discontinuous geometry stay in a single drawArrays(TRIANGLE_STRIP) batch. [claim:clm_005]
- Blending disables key overdraw-removal optimizations on Arm GPUs, specifically early ZS testing and Forward Pixel Kill (FPK), which is especially costly for UIs and 2D games with many sprite layers. [claim:clm_006]
- Each blended layer per pixel consumes GPU cycles regardless of shader simplicity, so the number of blended layers per pixel should be monitored and minimized. [claim:clm_007]
- Splitting large UI elements into separate opaque and transparent portions lets early ZS or FPK remove the overdraw beneath the opaque parts that blending would otherwise prevent. [claim:clm_008]
- Blending and alpha-to-coverage should always be disabled for opaque objects to preserve overdraw-removal optimizations. [claim:clm_009]
- Blending is comparatively efficient on Arm GPUs because the destination color is held on-chip in the tile buffer, but unorm formats are preferred over floating-point and only simple FP16/R11G11B10 blends are hardware-accelerated on Valhall. [claim:clm_010]
- BatchedMesh is a multi-draw batch-rendering mesh for many objects sharing one material but differing geometries or transforms, reducing draw calls to improve rendering performance. [claim:clm_011]
- setColorAt assigns a per-instance color (a Vector4 can be used to define alpha) and getColorAt reads it back, enabling per-instance tinting such as per-stitch or per-round highlights. [claim:clm_012]
- setMatrixAt sets a per-instance local transformation matrix, but negatively scaled matrices are not supported. [claim:clm_013]
- Per-object frustum culling and object sorting both default to true, with transparent materials sorted back-to-front and opaque ones front-to-back to reduce overdraw artifacts. [claim:clm_014]
- The constructor fixes capacity via maxInstanceCount (max instances) and maxVertexCount (max vertices across all unique geometries). [claim:clm_015]
- Buffers can be resized after construction via setInstanceCount and setGeometrySize, instances removed with deleteInstance, and optimize repacks sub-geometries to reclaim space left by deletions. [claim:clm_016]
- Mali tile-based GPUs split the screen into 16x16 pixel tiles, build per-tile primitive lists in a geometry pass, then shade each tile to completion before moving to the next in the fragment pass. [claim:clm_017]
- Each shader core processes one 16x16 pixel tile to completion before starting the next, the defining characteristic of fragment-pass tile rendering. [claim:clm_018]
- A typical 32bpp color + 32bpp packed depth/stencil framebuffer working set is ~16MB at 1080p and ~64MB at 4K2K. [claim:clm_019]
- External DRAM bandwidth costs roughly 120mW per 1GByte/s, whereas on-chip tile memory accesses are about an order of magnitude cheaper energy-wise. [claim:clm_020]
- Because a whole 16x16 tile's color/depth/stencil working set is kept in fast on-chip RAM coupled to the shader core, blending is fast and power-efficient since the destination color is readily available. [claim:clm_021]
- Transaction Elimination skips writing a tile's color back to main memory entirely when a CRC compare shows the tile contents are unchanged from what is already in memory. [claim:clm_022]
- Depth and stencil tile contents are never written back to main memory if the application discards them via glDiscardFramebufferEXT / glInvalidateFramebuffer (or driver inference). [claim:clm_023]
- On an Nvidia RTX 3090, the system runs yarn-level simulation in 1.05 ms/frame and fiber-level rendering in 23.6 ms/frame. [claim:clm_024]
- The rendering pipeline reaches near-ground-truth quality while being ~120,000x faster than a path-traced fiber-level reference. [claim:clm_025]
- The real-time method optimizes only ~100K yarn segments instead of the dense fiber geometry of the reference. [claim:clm_026]
- The path-traced reference models contain 51M, 55M, and 61M fiber segments, illustrating the fiber-count gap the method avoids. [claim:clm_027]
- Knit geometry's intricate yarn-and-fiber structure (each yarn = plies of tens-to-hundreds of twisted fibers) is the core obstacle to real-time high-fidelity knit rendering. [claim:clm_028]
- INFERENCE: The pipeline is desktop-GPU-only (all timings on an RTX 3090, no mobile/low-power numbers reported), indicating full yarn/fiber detail is out of mid-range-phone budget and approximate stitch-graph meshes are the mobile-viable path. [claim:clm_029]
- Arm's Fragment Pre-pass is a Hidden Surface Removal technique that runs a first pass over fragments to determine which ones will be visible in the final result before shading. [claim:clm_030]
- On a Fortnite parachute scene, Arm measured a 6.5% reduction in overall GPU cycles and a 16.1% reduction in floating-point arithmetic operations with the Fragment Pre-pass enabled. [claim:clm_031]
- On Justice Online Mobile, Arm measured a 4.6% reduction in GPU cycles and a 15.9% reduction in floating-point arithmetic operations from the Fragment Pre-pass. [claim:clm_032]
- The Fragment Pre-pass can perform Hidden Surface Removal on a useful subset of transparent draw calls where a hardware prepass would normally give up, but not on all transparent primitives. [claim:clm_033]
- When the Fragment Pre-pass does not apply, Arm's other Hidden Surface Removal technologies such as Forward Pixel Kill remain active to provide some hidden-surface removal. [claim:clm_034]
- The Fragment Pre-pass is supported on Arm's 2024-2025 generation GPUs: Mali-G625, Mali-G725, and Immortalis-G925. [claim:clm_035]
- BatchedMesh used the multiDraw[Arrays|Elements]Instanced APIs in earlier versions, but that feature was deprecated, removing the true-instanced multidraw path. [claim:clm_036]
- The current BatchedMesh emulates instancing by repeating the non-instanced multidraw parameters, which is slower than the true instanced variant. [claim:clm_037]
- Author-reported benchmarks show the instanced multidraw approach gives roughly 1.5x speedup on an integrated GPU and around 2x on a dedicated GPU versus plain multidrawElements. [claim:clm_038]
- Benchmarks were run on a single machine: AMD Ryzen 9 7940HS, 32 GB RAM, Radeon 780M integrated GPU, and an NVIDIA GeForce RTX 4080 dedicated GPU. [claim:clm_039]
- Firefox lacks multiDraw*Instanced support, so the author requests that three.js provide the instanced rendering mechanism plus a fallback for Firefox — a cross-browser portability constraint. [claim:clm_040]
- Every Arm GPU since the Mali-T620 includes Forward Pixel Kill (FPK), which automatically removes occluded fragments that early ZS testing does not kill. [claim:clm_041]
- Arm advises minimizing overdraw by rendering opaque objects front-to-back and limiting blended transparent layers, since front-to-back order maximizes the early depth/stencil test's effectiveness. [claim:clm_042]
- Arm warns developers not to depend on FPK alone, because an early-ZS test is always more energy-efficient and consistent and also works on older Mali GPUs without hidden surface removal. [claim:clm_043]
- From Mali-G725 / Immortalis-G925 onward, Fragment Prepass reliably removes overdrawn fragments independent of draw order, letting apps disable software front-to-back sorting and cut the CPU cost of issuing draw calls. [claim:clm_044]
- Arm recommends splitting large UI elements into separate opaque and transparent portions so early ZS or FPK can remove the overdraw beneath the opaque parts. [claim:clm_045]
- Arm explicitly prohibits blending on floating-point framebuffers (including multisampled ones), as it disables overdraw-removal optimizations such as early ZS and FPK. [claim:clm_046]
- Arm advises monitoring the per-pixel blended-layer count because high layer counts quickly consume GPU cycles even when individual blend shaders are simple. [claim:clm_047]
- Arm's guidance favors batching geometry and avoiding many small draw calls to reduce per-draw CPU and tiling/binning overhead, though no short verbatim batching excerpt could be confirmed from the binary PDF body. [claim:clm_048]
- Adreno uses FlexRender to switch mid-frame between binning/GMEM mode and direct/system-memory mode, so developers should optimize for both. [claim:clm_049]
- The FlexRender driver heuristics are not developer-exposed, but high vertex-shader texture sampling, few vertices/draws, or tessellation/geometry shaders tend to trigger direct (non-tiled) mode. [claim:clm_050]
- A properly structured renderpass lets the GPU run the full subpass chain per-tile, avoiding resolves to system memory after each pass, with gains of over 10% frametime. [claim:clm_051]
- For images/buffers that fit tile-memory constraints and are reused across render passes (as in deferred rendering), VK_QCOM_tile_memory_heap allocates them on GMEM to stay resident as long as possible, saving bandwidth. [claim:clm_052]
- Invalidating framebuffer contents as early as possible prevents the driver from wastefully resolving GMEM render-target memory to system memory. [claim:clm_053]
- Qualcomm advises minimizing render passes by combining consecutive passes that use the same formatted color buffer, which is critical to maximizing GMEM benefit from the tile shading extensions. [claim:clm_054]

## Decision

The recommended highlight technique is per-stitch instanced color (BatchedMesh.setColorAt over an opaque single-material batch), with the ghost-next-row drawn as a SEPARATE small transparent pass limited to only the next round's instances, so the opaque highlight body preserves early-ZS/FPK overdraw removal while transparency cost is bounded to one thin blended layer. [claim:clm_inf02]

## Rationale

- clm_009 says keep opaque objects non-blended; clm_006 shows blending kills early-ZS/FPK; clm_008/clm_045 recommend splitting opaque vs transparent portions; clm_007 says minimize blended layers. So the highlight body should be opaque (clm_012 instanced color) and only the ghost row should blend, isolated as a separate pass over a single round's instances. [claim:clm_inf02]
- clm_007/clm_047 name per-pixel blended-layer count as the metric to monitor; clm_044/clm_035 mean a pre-prepass Mali device is the worst-case class to include; clm_049 means an Adreno FlexRender device must be tested separately; clm_017 grounds overdraw in 16x16 tiles; clm_029 fixes the test scale at approximate stitch-graph meshes, not fiber geometry. [claim:clm_inf07]
- clm_001/clm_048 establish that fewer larger draw calls win; clm_011 makes BatchedMesh a single multi-draw batch sharing one material; clm_012 gives per-instance setColorAt/getColorAt (Vector4 alpha). Combining these, per-round recolor touches only the per-instance color buffer in one batch, which dominates the alternatives on draw-call count and update cost. [claim:clm_inf01]
- clm_001/clm_011 collapse the piece to ~1 draw so CPU draw-call cost is negligible; clm_006/clm_007/clm_047 establish that each blended layer per pixel burns cycles and disables overdraw removal regardless of shader simplicity; clm_021 notes blending itself is on-chip-cheap, so the binding constraint is layer COUNT/overdraw, not stitch count or batch draws. [claim:clm_inf03]
- clm_002 penalizes mutating VAOs each draw vs static VAOs; vertex-color groups recolor by writing the geometry's color attribute (mutating the VAO/its buffers) whereas clm_012's setColorAt writes a per-instance color buffer leaving the shared geometry static (clm_011), so instancing avoids the revalidation cost per row-advance. [claim:clm_inf04]
- clm_001 favors collapsing into fewer draws and clm_005 shows degenerate-triangle batching keeps discontinuous geometry in one draw; an index-range sub-draw per round contradicts that by adding draws per highlight band, whereas clm_012 keeps everything in one batch and only flips per-instance colors. [claim:clm_inf05]
- clm_006 establishes the blending penalty; clm_031/clm_032 quantify Fragment Prepass recovery at only 4.6-6.5% cycles; clm_035/clm_044 limit reliable prepass to Mali-G725/Immortalis-G925-class parts, so on the broad mid-range install base only FPK fallback (clm_034) applies and overdraw from transparent layers is essentially unmitigated. [claim:clm_inf06]
- clm_011 batches per-stitch geometry; clm_012/clm_013 address color and transform per instance index; clm_016 lets instances be added/removed/repacked. An index<->op table aligned to the IR's rounds[].ops[] therefore preserves identity in both directions provided the index map is maintained across optimize/deleteInstance repacks. [claim:clm_inf08]
- The evidence (clm_011/clm_012/clm_013/clm_016) only covers BatchedMesh instance addressing, never decimation/LOD behavior; absence of any LOD-preservation evidence is itself the risk, so the safe inference is to decouple the identity-bearing instanced layer from any LOD-able shell rather than rely on undocumented ID survival. [claim:clm_inf09]
- clm_011/clm_012 are shipped documented APIs (product-ready); clm_024/clm_026/clm_029 show the high-fidelity knit pipeline is desktop-only at ~24 ms/frame with no low-power benchmarks, placing fiber fidelity on the academic-only side and confirming approximate stitch-graph meshes as the productizable target. [claim:clm_inf10]

## Consequences

- A reusable mobile stitch-mesh highlight benchmark protocol should fix: (test mesh) a ~600-1500-instance amigurumi piece rendered as one BatchedMesh; (device class) at least one pre-2024 mid-range Mali phone WITHOUT Fragment Prepass plus one Adreno FlexRender device; (metrics) frame time at 30/60 FPS targets, per-pixel blended-layer count / overdraw, and draw-call count per row-advance - because these are exactly the levers the vendor guidance names as the failure points. [claim:clm_inf07]
- For per-stitch highlight mapping at amigurumi scale (hundreds-to-low-thousands of stitches), three.js BatchedMesh ranks first on the combined draw-call/update/fidelity axis because setColorAt rewrites only the advancing round's per-instance colors while the whole piece stays a single batched draw, beating per-vertex vertex-color groups (which re-upload geometry-buffer ranges), naive per-object draws (one draw per stitch), and a separate overlay pass (extra blended draws). [claim:clm_inf01]
- The dominant mid-range-phone bottleneck for this workload is per-pixel blended-layer overdraw, not draw-call count: at amigurumi stitch counts a single batched opaque draw keeps draw calls near 1, so the 30-60 FPS budget breaks first when stacked transparent ghost/overlay layers raise per-pixel blended-layer count rather than when stitch count rises. [claim:clm_inf03]
- Per-vertex vertex-color groups are the weakest mapping technique for incremental playback because advancing one round forces a partial vertex-buffer (VAO) re-upload, which clm_002 says makes the browser revalidate and recalculate fetch limits, whereas instanced per-instance color updates a separate instance buffer and leaves the geometry VAO static. [claim:clm_inf04]
- Index-range sub-draws (one drawElements per advancing round over a contiguous index range) are a viable middle option for highlight-only playback but lose to instanced color because each highlighted round becomes its own draw call, so draw-call count grows linearly with the number of distinct highlight states rather than staying at one batched draw. [claim:clm_inf05]
- On Arm Mali/Immortalis the cost difference between an opaque instanced highlight and a blended overlay is structural, not marginal: clm_006 shows blending disables early-ZS and FPK, and the Fragment Prepass only recovers single-digit-percent GPU-cycle savings (4.6-6.5% on real game scenes, clm_031/clm_032) and only on 2024-2025 GPUs (clm_035), so older mid-range Mali phones get no prepass relief and pay full overdraw for every stacked transparent layer. [claim:clm_inf06]
- Per-stitch IR identity is preserved across playback and the inverse round-trip by mapping each Crochet IR op (mr|ch|sc|hdc|dc|tr|inc|dec|... within pieces[].rounds[].ops[]) to a stable BatchedMesh instance index, since clm_012's getColorAt/setColorAt are index-addressed and clm_013's setMatrixAt is per-instance; the same instance-ID-to-op map then drives both forward row-highlight playback and reverse mesh->round visualization. [claim:clm_inf08]
- The single biggest unproven risk for productizing instanced per-stitch highlights is LOD/decimation identity loss (severity: high; likelihood: medium): none of the gathered sources document that per-stitch instance IDs survive mesh decimation, so a mitigation is to keep the per-stitch instance layer SEPARATE from any decimated background shell and to LOD only the non-identity-bearing geometry, preserving the instance<->IR-op map at every LOD. [claim:clm_inf09]
- The instanced per-stitch approach sits on the PRODUCT-READY side for the forward highlight/ghost-row visualizer (built from shipped, documented three.js BatchedMesh APIs and vendor mobile-GPU guidance), whereas full yarn/fiber fidelity sits on the ACADEMIC-FEASIBILITY-ONLY side: clm_024/clm_029 show the SIGGRAPH 2025 real-time knit method runs only on a desktop RTX 3090 at 23.6 ms/frame with no mobile numbers, so approximate stitch-graph meshes - not fiber rendering - are the mobile-viable path. [claim:clm_inf10]

## Links

- [[claim:clm_009]]
- [[claim:clm_012]]
- [[claim:clm_006]]
- [[claim:clm_008]]
- [[claim:clm_045]]
- [[claim:clm_007]]
- [[claim:clm_044]]
- [[claim:clm_049]]
- [[claim:clm_017]]
- [[claim:clm_029]]
- [[claim:clm_001]]
- [[claim:clm_011]]
- [[claim:clm_048]]
- [[claim:clm_047]]
- [[claim:clm_021]]
- [[claim:clm_002]]
- [[claim:clm_005]]
- [[claim:clm_031]]
- [[claim:clm_032]]
- [[claim:clm_034]]
- [[claim:clm_035]]
- [[claim:clm_013]]
- [[claim:clm_016]]
- [[claim:clm_024]]
- [[claim:clm_026]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
