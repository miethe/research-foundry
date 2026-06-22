---
id: mwb_20260622_dr_knitwit_mobile_runtime_architecture_engine
evidence_bundle_id: bundle_20260614_intent_research_20260614_which_mobile_3d
target_page: meatywiki/decisions/knitwit_mobile_runtime_architecture_engine_selec.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_which_mobile_3d_runtime_stack_and: Apple deprecated
  SceneKit (clm_001), it is not recommended for new apps (clm_002), and it gets only critical bug fixes
  w'
key_claims:
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf13
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_001
  - clm_002
  - clm_003
  - clm_023
  - clm_036
  - clm_062
  - clm_063
  - clm_071
  - clm_021
  - clm_038
  - clm_008
  - clm_045
  - clm_049
  - clm_022
  - clm_041
  - clm_051
  - clm_004
  - clm_006
  - clm_014
  - clm_068
  - clm_069
  - clm_028
  - clm_034
  - clm_052
  - clm_012
  - clm_039
  - clm_056
  - clm_050
  - clm_053
  - clm_029
  - clm_031
  - clm_015
  - clm_016
  - clm_017
  - clm_018
  - clm_054
  - clm_057
  - clm_027
  - clm_042
  - clm_005
  - clm_007
  - clm_025
  - clm_058
  - clm_060
  - clm_013
  - clm_059
  - clm_043
  - clm_026
  - clm_010
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: KnitWit Mobile Runtime Architecture: Engine Selection and IR-to-GPU Playback Pipeline for Mid-Range Phones

## Context

- Apple officially deprecated SceneKit across all platforms at WWDC25. [claim:clm_001]
- The deprecation is a soft deprecation — existing SceneKit apps keep working and no rewrite is required, but SceneKit is not recommended for new apps or significant updates. [claim:clm_002]
- SceneKit is entering maintenance mode: Apple will only fix critical bugs, with no new features or optimizations expected going forward. [claim:clm_003]
- RealityKit is supported on visionOS, iOS, macOS, and iPadOS, and as of WWDC25 it is newly supported on tvOS. [claim:clm_004]
- RealityKit is designed around the open USD standard introduced by Pixar in 2012, whereas SceneKit serializes assets into proprietary SCN files that are not a unified industry standard. [claim:clm_005]
- SceneKit uses a node-based scene graph with predefined node properties, while RealityKit uses an Entity Component System where behavior is added by attaching components to entities. [claim:clm_006]
- SceneKit/SCN and other DCC-tool assets must be converted to USD/USDZ for RealityKit, via Xcode export to a Universal Scene Description Package or via the xcrun scntool CLI. [claim:clm_007]
- SceneView is an Android view that integrates both ARCore and Google Filament for 3D and AR rendering. [claim:clm_008]
- The project explicitly positions itself as the forthcoming replacement for Sceneform. [claim:clm_009]
- AR is opt-in: SceneView provides a 3D-only mode while ArSceneView adds ARCore on top of 3D, so a Filament-only 3D viewport can run without ARCore. [claim:clm_010]
- The library is built around Kotlin, which the maintainers cite as the reason newer ARCore features integrate faster than in the older API surface. [claim:clm_011]
- The canonical SceneView SDK is described as a Jetpack Compose + Filament 3D/AR SDK for Android (with iOS and Web variants). [claim:clm_012]
- Google archived Sceneform in 2021 and ships no first-party declarative AR renderer; SceneView descends from the maintained community fork and is the actively-developed, Jetpack-Compose-native way to build 3D/AR on Android. [claim:clm_013]
- SceneView is a Composable rendering a Filament-only 3D viewport, while ARSceneView is SceneView plus ARCore with the camera following real-world tracking. [claim:clm_014]
- The IL2CPP scripting backend always performs byte-code stripping regardless of the editor's Stripping Level setting, so Unity recommends setting Stripping Level to Disabled because other levels add little size benefit and can cause native-code registration problems. [claim:clm_015]
- IL2CPP converts C# to C++ ahead-of-time and compiles it into the app binary, which can produce larger universal binaries or per-architecture slices than the Mono backend. [claim:clm_016]
- A Unity universal (fat) build bundles a 32-bit and a 64-bit slice containing the same executable for two architectures, roughly doubling the binary size versus a single-architecture build. [claim:clm_017]
- Apple enforces binary size limits that vary by MinimumOSVersion: 80 MB total __TEXT for <7.0, 60 MB per architecture slice for 7.x-8.x, and 500 MB for the Mach-O file for 9.0+. [claim:clm_018]
- Unity ships a MapFileParser utility that parses the Xcode-generated map file to attribute executable size contributions to individual scripts, plugins, and engine code. [claim:clm_019]
- The article is scoped to a dated Unity/XCode/iOS era, applying to Unity versions 5.2.0p1 and higher, XCode 7 and higher, and iOS 9.0 and higher. [claim:clm_020]
- react-native-filament is a React Native library for rendering 3D graphics in-app via React components, wrapping Google's Filament engine. [claim:clm_021]
- The native Filament dependency adds only about 4MB to the downloadable app size. [claim:clm_022]
- The library uses native GPU rendering: Metal on iOS and OpenGL/Vulkan on Android. [claim:clm_023]
- Filament is a native C++ physically based rendering (PBR) engine, and the library is GPU-accelerated by Metal and OpenGL/Vulkan. [claim:clm_024]
- react-native-filament renders on separate threads rather than the JS/UI thread. [claim:clm_025]
- The maintainer states Filament is battle-tested and react-native-filament is used in production apps with millions of users. [claim:clm_026]
- Only .glb files can be loaded directly; other formats (gltf, obj, FBX) must be converted to .glb first. [claim:clm_027]
- addUpdateRange(start, count) queues a sub-range of the data array to be updated on the GPU, where start is the position to begin and count is the number of components to update. [claim:clm_028]
- The updateRanges array lets you re-upload only some components of stored vectors (e.g., just the color component), with ranges added via addUpdateRange(). [claim:clm_029]
- clearUpdateRanges() resets the queued update ranges. [claim:clm_030]
- Setting needsUpdate = true flags the attribute as changed so it is re-sent to the GPU; it defaults to false and should be set after modifying the array. [claim:clm_031]
- The usage property defines the intended usage pattern for optimization (default StaticDrawUsage; DynamicDrawUsage is among valid values) and setUsage(value) sets it, though usage cannot be changed after a buffer's initial use. [claim:clm_032]
- BufferAttribute stores per-attribute geometry data (positions, indices, normals, colors, UVs, custom attributes) for efficient passing to the GPU. [claim:clm_033]
- Per-frame vertex position updates in Filament are pushed by calling VertexBuffer::setBufferAt with a BufferDescriptor over a fixed-location, fixed-size buffer whose contents change between frames. [claim:clm_034]
- The setBufferAt approach lets a developer maintain a dynamically changing mesh without re-creating the entire VertexBuffer each frame. [claim:clm_035]
- A Filament maintainer confirms that calling setBufferAt to mutate an existing vertex buffer in place is a fully supported, correct usage pattern. [claim:clm_036]
- Mutating a vertex buffer's contents via setBufferAt is distinct from the separately-debated capability of swapping a renderable from one vertex buffer to a different one (the subject of issue #1279). [claim:clm_037]
- Thermion is a framework for building cross-platform 3D applications with Dart and/or Flutter. [claim:clm_038]
- The ThermionViewer class exposes an API for creating and interacting with 3D scenes that are rendered by Google's Filament engine. [claim:clm_039]
- The viewer can load and manipulate entities, lights, skyboxes, and background elements, and play/pause/manipulate skeletal and morph-target animations. [claim:clm_040]
- Thermion targets iOS, macOS, Android, and Windows plus a Web/WASM build, giving broad mobile, desktop, and web reach from a single codebase. [claim:clm_041]
- Thermion ingests glTF models and KTX/PNG/JPEG textures and supports skinning and morph-target animations for playback. [claim:clm_042]
- Web support is still experimental and currently requires manually compiling Thermion to WebAssembly (via Emscripten) before deployment. [claim:clm_043]
- Thermion splits into thermion_flutter (the Flutter rendering-surface plugin) and thermion_dart (the viewer logic), separating the Flutter embedding layer from the platform-agnostic rendering API. [claim:clm_044]
- Filament is a single-codebase real-time physically based rendering engine targeting Android, iOS, Linux, macOS, Windows, and WASM. [claim:clm_045]
- Filament is explicitly designed to be as small and efficient as possible on Android, signaling a lightweight mobile footprint posture relative to full game engines. [claim:clm_046]
- Filament's graphics backends span OpenGL 4.1+/ES 3.0+, Metal, Vulkan 1.0, WebGPU, and WebGL 2.0, covering desktop, mobile, and web targets. [claim:clm_047]
- gltfio is a native glTF 2.0 loader for Filament, supporting compression and material extensions including KHR_draco_mesh_compression, KHR_materials_clearcoat, and KHR_materials_transmission. [claim:clm_048]
- The latest Filament release is v1.71.6, published 2026-06-10, indicating active ongoing maintenance. [claim:clm_049]
- LowLevelMesh is a container for vertex data that lets developers create and update RealityKit meshes using their own custom vertex format. [claim:clm_050]
- LowLevelMesh requires iOS 18 / iPadOS 18 / macOS 15 (Sequoia) / visionOS 2 (with tvOS 26), setting the minimum deployment-target floor for any KnitWit feature that depends on it. [claim:clm_051]
- Mesh contents in a LowLevelMesh can be updated either on the CPU with Swift or on the GPU via Metal compute shaders, enabling low-cost dynamic per-frame updates. [claim:clm_052]
- A MeshResource created from a LowLevelMesh retains a reference to it, so RealityKit reflects any mesh changes at render time without rebuilding the entity, supporting interactive playback. [claim:clm_053]
- The LowLevelMesh.Part sub-type maps a range of primitives to a material index, enabling per-region (per-part) material assignment such as highlight or recolor of mesh regions. [claim:clm_054]
- LowLevelMesh defines Attribute and Layout sub-types that map custom vertex attributes into memory and into RealityKit shader attributes, giving full control over the vertex buffer format. [claim:clm_055]
- Sceneform Maintained is an ARCore Android SDK that uses Google Filament as its 3D engine, and is presented as the continuation of the archived Sceneform project. [claim:clm_056]
- The SDK ingests glTF and GLB 3D model files natively from assets, res/raw, local file, or http/https URL, replacing the older sfa/sfb/fbx/obj plugin pipeline. [claim:clm_057]
- The maintainers explicitly state the framework is no longer updated and recommend using SceneView instead, signaling maturity/abandonment risk for the Android-native path. [claim:clm_058]
- Two successor lineages are documented: a Java continuation (Sceneform Maintained, this repo) and a Kotlin successor (SceneView/sceneview-android), both built on Filament + ARCore. [claim:clm_059]
- The latest release is version 1.23.0 (dated 2023-08-04), with no newer releases, consistent with the stated 'not actively updated' status. [claim:clm_060]
- Sceneform Maintained tracks the latest versions of the ARCore SDK and Google Filament, and supports animations on loaded glTF/GLB models. [claim:clm_061]
- AssetLoader ingests a single blob of glTF 2.0 content in either JSON or GLB form and produces a FilamentAsset, providing a direct glTF-to-Filament import path. [claim:clm_062]
- A FilamentAsset is defined as a bundle of Filament textures, vertex buffers, and index buffers, establishing a direct glTF-to-GPU-buffer mapping rather than an intermediate scene format. [claim:clm_063]
- Both binary GLB and JSON-based glTF 2.0 files are accepted by createAsset, which returns a single-instance asset or null on failure, matching the OBJ/GLTF contract's glTF path. [claim:clm_064]
- AssetLoader deliberately does not fetch external buffer data or create textures itself; that upload boundary is delegated to ResourceLoader, which obtains the URI list from the asset. [claim:clm_065]
- createInstancedAsset consumes a glTF 2.0 file and produces a primary asset with one or more instances, enabling multiple instances to share geometry for per-piece assembly use cases. [claim:clm_066]
- The AssetLoader.h header carries a 2019 Android Open Source Project / Google copyright, indicating it is the official upstream Filament importer interface. [claim:clm_067]
- setBufferAt(Engine&, bufferIndex, BufferDescriptor&&, byteOffset=0) does a partial copy-init into a single buffer slot at a byte offset, and byteOffset must be a multiple of 4. [claim:clm_068]
- A VertexBuffer set supports a maximum of 8 buffers, so attributes like position/color/uv can live in separate, independently updatable buffer slots. [claim:clm_069]
- Enabling buffer objects mode (enableBufferObjects(bool=true)) requires clients to call setBufferObjectAt rather than setBufferAt, and allows sharing data between VertexBuffer objects. [claim:clm_070]
- setBufferObjectAt() swaps in a whole GPU BufferObject (hot-swap), enabling recolor/restream by buffer swap instead of re-uploading vertex data. [claim:clm_071]
- setBufferAtAsync() is a non-blocking asynchronous version of setBufferAt() that copy-initializes the buffer and invokes a completion callback when the upload finishes. [claim:clm_072]

## Decision

SceneKit must be excluded as a forward-looking engine choice: Apple soft-deprecated it across all platforms at WWDC25 and put it in maintenance mode (critical bug fixes only, no new features or optimizations), so any KnitWit feature needing future GPU/perf work on SceneKit would be building on a frozen runtime. [claim:clm_inf02]

## Rationale

- Apple deprecated SceneKit (clm_001), it is not recommended for new apps (clm_002), and it gets only critical bug fixes with no new optimizations (clm_003). A performance-sensitive new app should not target a frozen engine. [claim:clm_inf02]
- Filament covers Metal+GL/Vulkan (clm_023/clm_045), in-place mutation (clm_036) and hot-swap (clm_071), direct glTF->buffer import (clm_062/clm_063), RN/Flutter/Android bindings (clm_021/clm_038/clm_008), and is actively maintained (clm_049). No other candidate scores across all four axes. [claim:clm_inf05]
- react-native-filament (clm_021/clm_022) and Thermion (clm_038/clm_041) give one cross-platform 3D layer; RealityKit offers ECS and tvOS/visionOS reach (clm_004/clm_006) but an iOS-18 LowLevelMesh floor (clm_051); SceneView provides the Android-native Filament path (clm_014). [claim:clm_inf06]
- FilamentAsset is already textures+vertex+index buffers (clm_063); setBufferAt updates a single slot at a 4-byte-aligned byteOffset (clm_068) with up to 8 slots (clm_069); three.js addUpdateRange targets a start/count span (clm_028); LowLevelMesh updates in place (clm_052). Mapping each round to a contiguous index range makes per-round partial updates feasible. Round/stitch indices align to the IR v0.1 rounds[].index and expected_stitch_count fields. [claim:clm_inf09]
- SceneView (clm_008/clm_012), react-native-filament (clm_021), Thermion (clm_038/clm_039), and Sceneform Maintained (clm_056) are each documented as Filament wrappers; Filament itself is a single-codebase engine (clm_045). Converging on Filament minimizes per-platform renderer divergence. [claim:clm_inf01]
- SceneKit is deprecated (clm_002), so the native dynamic-mesh successor is LowLevelMesh (clm_050) which requires iOS 18+ (clm_051). Filament renders via Metal on iOS (clm_023, clm_045) with no documented OS-18 floor, making it the lower-floor option. [claim:clm_inf03]
- Filament setBufferAt mutation is maintainer-confirmed (clm_034/clm_036) with byte-offset partial copy (clm_068) and buffer-object hot-swap (clm_071); LowLevelMesh updates without entity rebuild (clm_052/clm_053); three.js addUpdateRange re-uploads only a component sub-range (clm_028/clm_029/clm_031). [claim:clm_inf04]
- Unity IL2CPP AOT-compiles C# into the binary (clm_016) and fat builds nearly double size (clm_017) against Apple's size limits (clm_018); react-native-filament adds only ~4MB (clm_022). For a single 3D feature the Unity engine overhead is disproportionate. [claim:clm_inf07]
- LowLevelMesh.Part maps a primitive range to a material index (clm_054); Filament allows up to 8 independently updatable buffer slots (clm_069) and buffer-object hot-swap (clm_071); three.js can re-upload just the color component (clm_029). Highlight = scoped material/color update, not a rebuild. [claim:clm_inf08]
- Filament gltfio imports glTF directly to GPU buffers (clm_062/clm_063), Sceneform (clm_057), react-native-filament .glb (clm_027), and Thermion (clm_042) all ingest glTF; RealityKit uses USD and needs SCN/DCC->USDZ conversion (clm_005/clm_007), so iOS-native requires a parallel USDZ export. [claim:clm_inf10]
- react-native-filament adds ~4MB (clm_022), renders off the JS/UI thread (clm_025), but loads only .glb directly (clm_027), so the generator must target .glb to use this path. [claim:clm_inf11]
- Sceneform Maintained is self-marked abandoned (clm_058) with last release 1.23.0 (clm_060); SceneView is the Compose-native actively-developed successor (clm_013/clm_012); both are Filament+ARCore lineages (clm_059). [claim:clm_inf12]
- One Filament wrapper (clm_021/clm_038) is a single codebase vs native RealityKit+SceneView with a USDZ pipeline (clm_007); offsetting risks are Thermion's experimental web (clm_043) and vendor-only production claims (clm_026). 3D-only mode avoids ARCore weight (clm_010). [claim:clm_inf13]

## Consequences

- Filament is the strongest single primary engine choice for KnitWit because it uniquely combines (a) Metal-on-iOS plus OpenGL/Vulkan-on-Android backends, (b) a maintainer-confirmed in-place vertex-buffer mutation path plus a whole-buffer hot-swap path, (c) a native glTF 2.0/.glb importer that maps directly to vertex/index buffers, and (d) front-end bindings for native-Android, React Native, and Flutter -- a combination no competing engine in the evidence matches. [claim:clm_inf05]
- The recommended decision rule is: default to native Filament when an iOS-17-or-earlier floor or maximal control is required; choose react-native-filament or Thermion when the team already owns a React Native or Flutter codebase and wants one 3D layer; and choose RealityKit (iOS) + SceneView/Filament (Android) only when deep platform-native AR/ECS integration outweighs maintaining two renderers and an iOS 18 floor is acceptable. [claim:clm_inf06]
- The recommended IR-to-GPU runtime data flow is: Crochet IR pieces[].rounds[].ops (op enum mr|sc|inc|dec|...) expand to a per-stitch node/edge stitch-graph carrying round_index and stitch_index, which is laid out into a single interleaved vertex buffer plus an index buffer where each round occupies a contiguous index range; row-advance and ghost-overlay then call only a sub-range buffer update (Filament setBufferAt at the round's byteOffset, or three.js addUpdateRange over that round's component span), keeping per-frame CPU work proportional to one round rather than the whole mesh. [claim:clm_inf09]
- Filament is the de facto cross-platform substrate for this decision: SceneView/Sceneform on Android, react-native-filament on React Native, and Thermion on Flutter all wrap the same Filament engine, so a Filament-centric architecture is portable across native-Android, RN, and Flutter front-ends while iOS is the only major target requiring a non-Filament native path. [claim:clm_inf01]
- On iOS the only vendor-sanctioned native dynamic-mesh path is RealityKit LowLevelMesh, which imposes a hard iOS 18 / iPadOS 18 deployment-target floor; teams needing to support iOS 17 or earlier on mid-range phones must instead use a Filament-based stack (react-native-filament / Thermion / native Filament), which carries no such OS floor. [claim:clm_inf03]
- All four viable runtimes expose a partial / sub-range GPU buffer update API that satisfies KnitWit's row-advance and recolor requirement without full re-uploads: Filament setBufferAt(byteOffset) and setBufferObjectAt hot-swap, RealityKit LowLevelMesh CPU/GPU in-place update, and three.js BufferAttribute.addUpdateRange(start,count); incremental row-by-row buffer mutation is therefore an engine-supported feature, not a workaround, on every candidate except deprecated SceneKit. [claim:clm_inf04]
- Unity is the weakest fit for an amigurumi-first viewer on binary-size grounds: its IL2CPP backend AOT-compiles C# into the app and universal builds roughly double size by bundling 32-bit and 64-bit slices, whereas react-native-filament's native dependency adds only ~4MB -- an order-of-magnitude-class delta that matters for a single-feature 3D preview rather than a whole game. [claim:clm_inf07]
- Per-region highlight and recolor (current-row, ghost-next-row, piece isolation) map cleanly onto engine primitives without per-frame geometry rebuilds: RealityKit LowLevelMesh.Part assigns a primitive range to a material index, Filament's 8-slot vertex buffer lets a separate per-vertex color slot be updated independently, and three.js updateRanges can re-upload only the color component -- so highlight state can be encoded as material-index or color-buffer changes scoped to the active round's index range. [claim:clm_inf08]
- glTF/.glb should be the interchange format between KnitWit's pattern->3D generator and the runtime, because every Filament-based candidate ingests glTF 2.0 natively (Filament gltfio AssetLoader, Sceneform Maintained, react-native-filament .glb-only, Thermion) and Filament's loader maps glTF directly to vertex/index buffers; RealityKit is the lone exception, requiring conversion to USD/USDZ, which argues for emitting both glTF (Android/cross-platform) and USDZ (iOS-native) from the same stitch-graph if a RealityKit path is kept. [claim:clm_inf10]
- react-native-filament's ~4MB add and off-JS-thread rendering make it the lowest-friction way to add interactive 3D to a React Native KnitWit app, but its .glb-only loader means the pattern->3D generator must always emit binary .glb (not JSON glTF), making .glb the canonical runtime export rather than an optional one. [claim:clm_inf11]
- The Android-native path has a clear successor ordering: Sceneform Maintained (Java, last release 1.23.0 in Aug 2023, self-marked 'not updated anymore') should be treated as study-only legacy, while the Kotlin/Jetpack-Compose SceneView is the actively-developed Filament+ARCore renderer and the correct Android-native target; both sit on Filament, so migrating between them changes the binding layer, not the rendering substrate. [claim:clm_inf12]
- The cross-platform-vs-native tradeoff favors a single Filament-based 3D layer for KnitWit's MVP: one renderer (react-native-filament or Thermion) avoids maintaining two divergent codebases and two glTF/USDZ asset pipelines, at the cost of Filament's experimental/immature edges (Thermion's web build needs manual WASM compilation; react-native-filament/Thermion are smaller-community wrappers vs Apple-first-party RealityKit) -- a maintenance-cost reduction that is well-supported but whose runtime maturity on mid-range phones is not independently benchmarked in this evidence set. [claim:clm_inf13]

## Links

- [[claim:clm_001]]
- [[claim:clm_002]]
- [[claim:clm_003]]
- [[claim:clm_023]]
- [[claim:clm_036]]
- [[claim:clm_062]]
- [[claim:clm_063]]
- [[claim:clm_071]]
- [[claim:clm_021]]
- [[claim:clm_038]]
- [[claim:clm_008]]
- [[claim:clm_045]]
- [[claim:clm_049]]
- [[claim:clm_022]]
- [[claim:clm_041]]
- [[claim:clm_051]]
- [[claim:clm_004]]
- [[claim:clm_006]]
- [[claim:clm_014]]
- [[claim:clm_068]]
- [[claim:clm_069]]
- [[claim:clm_028]]
- [[claim:clm_034]]
- [[claim:clm_052]]
- [[claim:clm_012]]
- [[claim:clm_039]]
- [[claim:clm_056]]
- [[claim:clm_050]]
- [[claim:clm_053]]
- [[claim:clm_029]]
- [[claim:clm_031]]
- [[claim:clm_015]]
- [[claim:clm_016]]
- [[claim:clm_017]]
- [[claim:clm_018]]
- [[claim:clm_054]]
- [[claim:clm_057]]
- [[claim:clm_027]]
- [[claim:clm_042]]
- [[claim:clm_005]]
- [[claim:clm_007]]
- [[claim:clm_025]]
- [[claim:clm_058]]
- [[claim:clm_060]]
- [[claim:clm_013]]
- [[claim:clm_059]]
- [[claim:clm_043]]
- [[claim:clm_026]]
- [[claim:clm_010]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
