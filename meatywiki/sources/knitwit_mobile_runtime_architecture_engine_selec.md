---
id: mwb_20260614_knitwit_mobile_runtime_architecture_engine_selec
evidence_bundle_id: bundle_20260614_intent_research_20260614_which_mobile_3d
target_page: meatywiki/sources/knitwit_mobile_runtime_architecture_engine_selec.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_which_mobile_3d_runtime_stack_and: 72
  supported claim(s) across 12 source card(s).'
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
links:
  source_cards:
  - src_20260614_kw008_00
  - src_20260614_kw008_01
  - src_20260614_kw008_02
  - src_20260614_kw008_03
  - src_20260614_kw008_04
  - src_20260614_kw008_05
  - src_20260614_kw008_06
  - src_20260614_kw008_07
  - src_20260614_kw008_08
  - src_20260614_kw008_09
  - src_20260614_kw008_10
  - src_20260614_kw008_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# KnitWit Mobile Runtime Architecture: Engine Selection and IR-to-GPU Playback Pipeline for Mid-Range Phones

## Summary

Source note distilled from research run rf_run_20260614_which_mobile_3d_runtime_stack_and: 72 supported claim(s) across 12 source card(s).

## Key claims

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

## Sources

- src_20260614_kw008_00 — google/filament — Real-time physically based rendering engine (official repo)
- src_20260614_kw008_01 — Filament Issue #1445 — Question: correct way to update vertex buffer data
- src_20260614_kw008_02 — SceneView/sceneform-android — Sceneform Maintained (ARCore + Filament)
- src_20260614_kw008_03 — SceneView — 3D/AR Android View with ARCore and Google Filament (Kotlin successor)
- src_20260614_kw008_04 — Bring your SceneKit project to RealityKit — WWDC25 Session 288
- src_20260614_kw008_05 — LowLevelMesh | Apple Developer Documentation (RealityKit)
- src_20260614_kw008_06 — Thermion — open-source 3D rendering toolkit for Flutter and Dart (Filament-backed)
- src_20260614_kw008_07 — react-native-filament — React Native wrapper for Google Filament (Margelo)
- src_20260614_kw008_08 — IL2CPP build size optimizations
- src_20260614_kw008_09 — Filament VertexBuffer.h (libs/filament/include/filament/VertexBuffer.h)
- src_20260614_kw008_10 — Filament gltfio AssetLoader.h (glTF 2.0 importer)
- src_20260614_kw008_11 — three.js Docs — BufferAttribute

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
