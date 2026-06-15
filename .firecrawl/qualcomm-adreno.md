Documentation

Game Developer Guide Close

Introduction

Highlights

What’s New

October 2025

July 2024

August 2021

February 2021

Guides

Qualcomm® Adreno™ GPU

Overview

Introduction to Snapdragon Adreno™

Tile-based Rendering

FlexRender™ technology (Hybrid Deferred and Direct Rendering mode)

Concurrent Binning

MSAA: Multisample anti-aliasing

Tile Shading Vulkan Extensions

Render Surfaces

sRGB textures and render targets

Universal bandwidth compression

Percentage Closer Filtering for depth textures

LRZ, Early-Z and Fast-Z

Low Resolution Z pass

Early Z rejection

Fast-Z

Texture Features

Texture compression

Floating point textures

Cube mapping with seamless edges

Video textures

Shaders

Unified shader architecture

Scalar architecture

GPU-Driven Rendering

Geometry instancing

Indirect draw calls

Low Priority Asychronous Compute (LPAC)

Mesh Shading

Raytracing

Introduction

How does raytracing differ from rasterization?

Hit detection

Qualcomm True HDR

Introduction

Light-to-display overview

HDR10

Traditional Game HDR

True HDR

Variable Rate Shading (VRS)

How does Variable Rate Shading work?

Effective ways to modify Shading Rate

Spec Sheets

Introduction

Renderer Architecture

Tile-based Rendering

Tile Shading Vulkan Extensions

Render Surface Target

Vertex and Index Buffers

Texture Features

Texture formats

Shaders

Compute Shaders

Mesh Shaders

Raytracing

Queries

Occlusion queries

Adreno GPU on Mobile: Best Practices

Feature Summary

Best Practices Summary

Renderer Architecture

Tile-based Rendering

Concurrent Binning

Render Surface Target

Z-Buffer

Vertex and Index Buffers

Texture Features

Shaders

Compute Shaders

Mesh Shading

Raytracing

Queries

XR/VR/AR (Extended Reality/Virtual Reality/Augmented Reality)

Renderer Architecture

Graphics API

Render Pass

Shader mode switching

Images

Buffer Best Practices

Vulkan

Triangle Screen Size

Features to avoid for performance reasons

Tile-based Rendering

Bin Minimization

FlexRender™ technology (Hybrid Deferred and Direct Rendering mode)

Concurrent Binning

Tile Shading Vulkan Extensions

Render Surfaces

sRGB textures and render targets

Upscaling

Bandwidth Optimization

Z-Buffer

LRZ, Early-Z and Fast-Z

Low Resolution Z pass

Early Z rejection

Fast-Z

Vertex and Index Buffers

Vertex buffer layout

Batching vertex buffer object updates

Index types

Texture Features

Sampling in Vulkan

Multiple textures

Texture compression

Floating point textures

Video textures

Shaders

Half-Precision

Instruction count

GPR minimization

Split up draw calls

Minimize ALU Cost

Avoid discarding pixels in the fragment shader

Avoid modifying depth in fragment shaders

Stay under performance-optimal resource limits

Minimize texture fetches in vertex shaders

Latency Hiding, and Load Balancing the Texture Pipe and Shader Pipe

DXC and Glslang and the Texture Pipe

Compiling and linking during initialization

Compute Shaders

GPU-Driven Rendering

Geometry instancing

Indirect draw calls

Low Priority Asychronous Compute (LPAC)

Mesh Shading

Raytracing

Hit detection

Application example: shadow generation

Optimization

2D operation hardware acceleration

Queries

Occlusion queries performance

Timer Query Accuracy

Qualcomm True HDR setup

Set EGLSurface format

Set color space

Set metadata

Get the luminance of display on Android

Variable Rate Shading (VRS)

XR/VR/AR (Extended Reality/Virtual Reality/Augmented Reality)

Stereographic Rendering

Foveated Rendering

Querying the driver version to implement version-specific workarounds

Vulkan

adb

Adreno APIs

Texture Compression Examples

Diffuse texture test

ATC Compression

ETC1 Compression

ETC2 Compression

Normal texture test

ATC Compression

ETC1 Compression

ETC2 Compression

Qualcomm® Oryon™ CPU

Tools

Event Tracing for Windows

Superluminal

Visual Studio

Architecture

Overview

General primer on the ARM architecture

Introduction to ARM Assembly

ARM64 and ARM64EC

Differences from X64

Performance optimization

Clocks and counters

Vectorization

Vector support in Snapdragon X

Specialized libraries

NEON intrinsics

Auto-vectorization

ISPC

Unreal Engine

Topology and threading/affinity

Example

Thread priority

Thread affinity

Best Practices

Compilation

Vectorization

Threading and affinity

Qualcomm® Kryo™ CPU

Overview

big.LITTLE Architecture

Understanding CPU utilization

Threading and Core Affinity

Power considerations

NEON Intrinsics and SIMD

Interfacing with DSP and GPU

Best practices

Summary

Avoid single-thread 100% CPU Utilization bottleneck

Avoid disk I/O or blocking operations on main/render threads

Use Neon for SIMD operations

Use big cores for compute intensive tasks

Use little cores for power efficient tasks

Multi-thread game initialization

Vulkan

Qualcomm® Hexagon™ DSP

Overview

FastRPC (Remote Procedural Call) and Android Native Hardware Buffers

Hexagon Programming Primer

Hexagon Vector eXtensions: HVX SIMD

Components

Snapdragon Profiler

Realtime

Trace

Snapshot

Vulkan in Snapdragon Profiler

Quick Start with Performance Analysis

Load-Balancing Texture Pipe and Shader Pipe

Testing Suggestions

Tutorials

Android

Android OS on Snapdragon

Introduction

Memory Management on Android

In Kotlin/Java, what is the best approximation of “how much memory can my app allocate?”

What is the easiest way to see what memory your app has allocated over time?

In Kotlin/Java what is the best approximation of memory your app has natively allocated?

In Kotlin/Java, what is the best approximation of graphics memory used by your app?

In adb, what is the best approximation of total memory used by your app?

In adb, what is the best approximation of memory available across the entire device?

In adb, what is the easiest way of approximating an app’s memory footprint over time?

In adb, what’s the best way to get the total graphics memory footprint across the entire device?

In adb, what’s the best way of examining an app’s graphics memory footprint?

In adb, what’s the best way of getting a finer-grained picture of an app’s graphics memory usage?

In adb, what is the best way of approximately reporting an app’s memory leaks?

What is the best way of investigating an app’s memory corruption?

How can I instrument C++ malloc calls?

Android Application Lifecycle Guidelines

NativeActivity Dependency Minimization

Lifecycle Callbacks

Lowmemorykiller Management

Multi-Window Disabling

Identifiers That Can’t Change After Publishing

Understanding and resolving Graphics Memory Loads

In a nutshell

What are Graphics Memory Loads (Unresolves)?

Why are Graphics Memory Loads expensive?

Detecting Graphics Memory Loads in Snapdragon Profiler

Identify application bottlenecks

How many frames per second?

Exploring potential bottlenecks

GPU-bound application

CPU-bound app

Vsync-bound app

Windows on Snapdragon

Windows on Snapdragon Detection

C++

Adreno GPU Detection

Get Started with Windows on Snapdragon Development

Introduction

Getting Started in Visual Studio

Prerequisites

Installing and configuring Visual Studio on the Development Host

Installing and configuring the Arm64 target device

Debugging

Remote debugging with Visual Studio

Connecting to Remote Debugger from Visual Studio

Distributing the application

Non-redistributable debug runtime

Visual Studio Performance Profiler

CPU and GPU profiling with PIX

DirectX 12

Setup on Development machine

Setup on Arm64 target device

Connecting to a remote PIX debugger

Examples

Launching for GPU capture on the Arm64 target

Launching for CPU capture

Troubleshooting PIX

Platform details

Snapdragon 8cx

Memory model

Neon SIMD

Key differences between Adreno and Desktop GPUs

References

Unreal Engine 5 for Windows on Snapdragon

Unreal Engine 4 for Windows on Snapdragon

Before you begin

Technical Prerequisites

Development machine

Target Arm64 Windows 10 machine

Building Unreal Engine from source to enable Windows Arm cross-compile

Producing builds

Additional notes

Remote debug

Build optimization

Third-party libraries

References

Legal notice

1. Guides
2. Qualcomm® Adreno™ GPU
3. Adreno GPU on Mobile: Best Practices

# Adreno GPU on Mobile: Best Practices

Download

Updated: Mar 03, 2026 80-78185-2  Rev: AL

On this page

- Feature Summary
- Best Practices Summary
- Renderer Architecture
- Tile-based Rendering
- Concurrent Binning
- Render Surface Target
- Z-Buffer
- Vertex and Index Buffers
- Texture Features
- Shaders
- Compute Shaders
- Mesh Shading
- Raytracing
- Queries
- XR/VR/AR (Extended Reality/Virtual Reality/Augmented Reality)
- Renderer Architecture
- Graphics API
- Render Pass
- Shader mode switching
- Images
- Buffer Best Practices
- Vulkan
- Swapchain
- Triangle Screen Size
- Features to avoid for performance reasons
- Tile-based Rendering
- Bin Minimization
- FlexRender™ technology (Hybrid Deferred and Direct Rendering mode)
- Concurrent Binning
- Tile Shading Vulkan Extensions
- VK\_QCOM\_tile\_memory\_heap
- VK\_QCOM\_tile\_shading
- Render Surfaces
- sRGB textures and render targets
- Upscaling
- Bandwidth Optimization
- Universal BandWidth Compression (UBWC)
- Z-Buffer
- LRZ, Early-Z and Fast-Z
- Low Resolution Z pass
- Early Z rejection
- Fast-Z
- Vertex and Index Buffers
- Vertex buffer layout
- Batching vertex buffer object updates
- Index types
- Texture Features
- Sampling in Vulkan
- Multiple textures
- Texture compression
- Floating point textures
- Video textures
- Shaders
- Half-Precision
- Instruction count
- GPR minimization
- Split up draw calls
- Minimize ALU Cost
- Minimize type casting
- Control Flow
- Pack shader interpolators
- Pack scalar constants
- Use built-in shader instructions
- Avoid discarding pixels in the fragment shader
- Avoid modifying depth in fragment shaders
- Stay under performance-optimal resource limits
- Minimize texture fetches in vertex shaders
- Latency Hiding, and Load Balancing the Texture Pipe and Shader Pipe
- Texture Fetch Bottleneck Optimization
- DXC and Glslang and the Texture Pipe
- Compiling and linking during initialization
- Compute Shaders
- GPU-Driven Rendering
- Geometry instancing
- Indirect draw calls
- Vertex streaming versus attribute fetching
- Low Priority Asychronous Compute (LPAC)
- Mesh Shading
- Raytracing
- Hit detection
- Application example: shadow generation
- Optimization
- General Considerations
- Prefer ray queries to ray pipelines
- Minimize calls to rayQueryProceed()
- Reuse one minimally-sized ray query object
- Access ray query data through intrinsics
- Avoid proceed() calls in loops for non-opaque traversal that “accept first fit”
- Use the optimal subgroup size
- 2D operation hardware acceleration
- Queries
- Occlusion queries performance
- Timer Query Accuracy
- Qualcomm True HDR setup
- Set EGLSurface format
- Set color space
- Set metadata
- Get the luminance of display on Android
- Variable Rate Shading (VRS)
- XR/VR/AR (Extended Reality/Virtual Reality/Augmented Reality)
- Stereographic Rendering
- Foveated Rendering
- Querying the driver version to implement version-specific workarounds
- Vulkan
- adb
- Adreno APIs

Adreno GPU on Mobile: Best Practices Guides documentation

# Adreno GPU on Mobile: Best Practices

## Feature Summary [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#feature-summary "Click to copy section url")

Adreno has a rich set of hardware and software features. Here is a quick-start overview of what’s available, linking to more information:

- [Renderer Architecture](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-renderer-architecture): Make the most of Adreno’s performance and battery usage by considering:

  - [renderpass](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vulkan-render-pass) and [subpass](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#vulkan-subpass-handling) management (including [image layout](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vulkan-image-layout), [memory buffer usage](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-buffer-best-practices), manual [GMEM](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vk-qcom-tile-shading-best-practices) [optimization](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vk-qcom-tile-memory-heap-best-practices), [z-buffer setup](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-z-buffer) and [shader submission](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-graphics-submits-compute-dispatches-separate))

  - [reduced fragment](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-upscaling-best-practices) [shader invocations](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#vrs)

  - [swapchain setup](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-swapchain-android-phones)

  - [less performant features to avoid](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-less-performant-features)


- [Tile-based Rendering](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-rendering): [FlexRender™](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#flex-render), mid-frame, constantly chooses between [binning/GMEM](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-bin-minimization) and [direct/system-memory](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-direct-mode-triggers) mode: optimize for both (ideally with [Vulkan extensions](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-tile-shading-vulkan-extensions))

- [Render Surface Target](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#render-surfaces): The image at the end of the frame involves [sRGB](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#srgb-texture) and [pixel formats](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-srgb-with-fastest-pixel-format), [upscaling optimizations](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-upscaling-best-practices), and ensuring [optimal layout](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-render-pass-efficiently)

- [Universal BandWidth Compression (UBWC)](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#universal-bandwidth-compression-ubwc): increases memory bus throughput and reduces battery power

- [Z-buffer](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-z-buffer): Depth buffers should use the [optimal pixel format](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-fastest-depth-format)

- [LRZ, Early-Z and Fast-Z](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#lrz-early-z-fast-z): Hardware acceleration for depth buffering can dramatically improve performance

- [Vertex and Index Buffers](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vertex-and-index-buffers-best-practices): [Vertex](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vertex-buffer-layout) and [index](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-index-buffer-layout) buffer layouts impact performance, as does [submission order of buffer changes](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-batching-vertex-buffer-object-updates)

- [Texture Features](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#texture-features): [Sampler setup](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-textures-sampling-vulkan-setup) and [texture formats](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#texture-compression) impact performance, as can leveraging [driver-optimized texture features](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#texture-features)

- [Shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#shaders): Adreno’s [unified](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#unified-shader-architecture)/ [scalar](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#scalar-architecture) shader architecture enables many shader-level optimizations

- [Compute Shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-compute-shaders): have some special considerations beyond [other shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#shaders)

- [GPU-Driven Rendering](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#gpu-driven-rendering): involves using [compute shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-compute-shaders) to offload more work from the CPU onto the GPU – consider a [tile-based](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vk-qcom-tile-shading-best-practices) approach

- [Low Priority Asychronous Compute (LPAC)](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#lpac): can efficiently perform some [compute shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-compute-shaders) concurrently with other processing on the Graphics Pipe

- [Mesh Shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-mesh-shading-best-practices) afford custom control over geometry generation and culling

- [Raytracing](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#raytracing): efficient simulation of light rays for beautiful imagery on low-power devices like mobile

- [OpenCL (download pdf)](https://developer.qualcomm.com/qfile/33472/80-nb295-11_a.pdf): is supported

- [2D Operation Hardware Acceleration](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-2d-operation-hardware-acceleration): is accessible through [graphic APIs](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-graphics-api)

- [Queries](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-queries): should be issued correctly to maximize performance and accuracy

- [Qualcomm True HDR](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#qualcomm-hdr): mobile devices featuring OLED screens support a higher dynamic range and wider color gamut: make use of this color depth

- [Variable Rate Shading (VRS)](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#vrs): allows a fragment shader to color one or more pixels at a time, so a fragment can represent one pixel or a group of pixels

- [Querying the driver version](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-querying-driver-version): helps you implement workarounds for older drivers and devices


## Best Practices Summary [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#best-practices-summary "Click to copy section url")

Here is a quick-start overview of some of the most relevant development best practices, linking to more information:

### [Renderer Architecture](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html\#renderer-architecture-device-specific) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#renderer-architecture "Click to copy section url")

- [Prefer Vulkan to OpenGL ES](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-graphics-api)

- [Follow Vulkan best practices](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vulkan-best-practices)

- [Minimize renderpasses correctly](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-minimize-render-passes)

- [Setup renderpasses efficiently](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-render-pass-efficiently)

- [Maximize Universal BandWidth Compression (UBWC)](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-universal-bandwidth-compression-ubwc-best-practices)

- [Manually optimize for GMEM](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-tile-shading-vulkan-extensions)

- [Depth-only render efficiently](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-depth-only-render-efficient-setup)

- [Use swapchain efficiently](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-swapchain-android-phones)

- [Pass VK\_PIPELINE\_CREATE\_LINK\_TIME\_OPTIMIZATION\_BIT\_EXT in shipping builds to maximize performance](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#pipeline-create-link-time-optimization-bit)

- [Use Vulkan Adreno Layer in nonshipping builds](https://docs.qualcomm.com/doc/80-78185-2/topic/vk_adreno_layer.html#vk-adreno-layer)

- [Use buffer best practices](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-buffer-best-practices)

- [Separate graphics submits and compute dispatches](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-graphics-submits-compute-dispatches-separate)

- [Maximize indirect draw calls](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-indirect-draw-calls-best-practices)

- [Avoid less performant features](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-less-performant-features)

- [Use framerate extrapolation](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-framerate-extrapolation)

- [Ideal screenspace triangle size is at least 4 pixels, and not much larger than a bin](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-triangle-screen-size)


### Tile-based Rendering [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#tile-based-rendering "Click to copy section url")

- [Minimize the number of bins](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-bin-minimization)

- [Use tile-based draws when it fits your algorithm](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vk-qcom-tile-shading-best-practices)

- [Prefer MSAA to other anti-aliasing techniques (for small-pixel form factors like mobile, consider no anti-aliasing)](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#prefer-msaa-or-no-aa)


### Concurrent Binning [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#concurrent-binning "Click to copy section url")

- [Issue each draw call such that it produces enough fragment shader work to parallelize with the next draw call’s binning](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-issue-enough-fragment-work-to-parallelize-with-binning)

- [Minimize dependencies – renderpass, barrier, Z-buffer-clear – that prevent concurrent binning](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-minimize-dependencies-renderpass-barrier-depth-target-clear)

- [Use the same Z-buffer (without clearing or invalidating it) between passes – or use separate Z-buffers per pass](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-logically-independent-depth-buffers-for-each-pass)


### [Render Surface Target](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html\#mobile-render-surface-target-device-specific) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#render-surface-target "Click to copy section url")

- [Use HDR (high dynamic range)](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-qualcomm-hdr-best-practices)

- [Use the fastest possible sRGB pixel format](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-srgb-with-fastest-pixel-format)

- [Use the lowest render target resolution that looks good and upscale: prefer SGSR when possible, or frame buffer blits otherwise.](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-upscaling-best-practices)

- [On Android, consider relying on SurfaceFlinger’s efficient bilinear rescale](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-upscaling-best-practices)

- [Maximize use of Variable Rate Shading](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vrs-best-practices)

- [If using Multiple Render Targets, stay below device performance limits](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#mobile-render-surface-target-device-specific)


### Z-Buffer [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#z-buffer "Click to copy section url")

- [Use the fastest possible depth format](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-fastest-depth-format)

- [Don’t disable LRZ (Low Resolution Z-Buffer)](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-lrz-do-not-disable) or [Early Z Rejection](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-early-z-rejection-do-not-disable)


### Vertex and Index Buffers [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#vertex-and-index-buffers "Click to copy section url")

- [Lay out vertex buffers optimally](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vertex-buffer-layout)

- [Minimize the size of vertex buffers](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vertexattributescompress)

- [Minimize the size of index buffers](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-indexbuffercompress)

- [Batch vertex buffer object updates](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-batching-vertex-buffer-object-updates)


### Texture Features [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#texture-features "Click to copy section url")

[Use ASTC texture compression in the sRGB format](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#use-astc-texture-compression)

### Shaders [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#shaders "Click to copy section url")

- [Use Adreno Offline Compiler to optimize shaders](https://qpm.qualcomm.com/#/main/tools/details/Adreno_GPU_Offline_Compiler)

- [Make instruction counts fit the instruction cache for binning, concurrent-binning, vertex, fragment, and compute shaders (LPAC compute shaders have a slightly larger instruction cache).](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-instruction-count) [Consider splitting up long shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-instruction-count-long-shader-splitting)

- [Minimize GPR (general purpose register) usage. Consider splitting up shaders that spill GPRs and cannot be further optimized](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-gpr-minimization)

- [Don’t reference too many unique vertex buffers, textures-and-SSBOs, samplers or uniform buffers](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-shader-unique-resource-performance-limits)

- [Minimize texture samples in vertex shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vertes-shader-minimize-texture-fetches)

- [Load-balance shader-pipe and texture-pipe](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-texture-latency-masking)

- [Separate graphics submits and compute dispatches](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-graphics-submits-compute-dispatches-separate)

- [Maximize half precision](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-maximize-half-precision)

- [Minimize type casting](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-minimize-type-casting)

- [Prefer built-in instructions](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-built-in-shader-instructions)

- [Use hardware accelerated blits, convolution kernels, etc](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-2d-operation-hardware-acceleration)

- [Use Android-phone pre-rotation on Vulkan](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-2d-operation-hardware-acceleration)


### Compute Shaders [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#compute-shaders "Click to copy section url")

- [Most shader advice applies to compute shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-shaders-performance-advice-summary)

- [Prefer fragment shaders to compute shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-prefer-fragment-to-compute-shaders)

- [Instruction counts and GPR limits are similar – but not identical – to other shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-compute-shaders-performance-like-other-shaders)

- [Minimize compute thread synchronization – when it’s necessary, prefer atomics](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-avoid-synchronizing-compute-threads)

- [Tune workgroup sizes and number of workgroups, taking into account shader stalls and whether the shaders read each others’ memory](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-compute-shader-workgroup-tuning)


### Mesh Shading [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#mesh-shading "Click to copy section url")

- [Most shader advice applies to mesh shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-shaders-performance-advice-summary)

- [Avoid amplification shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-avoidmeshshadingamplificationshaders)

- [Set the optimal wave count](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#mobile-meshshadingwavecountoptimal-specs)

- [Prefer per-vertex attributes to per-primitive attributes](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-prefervertexattributestoprimitiveattributes)

- [Keep mesh shader payload sizes under device limits](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-meshshaderpayloadunderlimit)

- [Consider using LPAC to load-balance with the Graphics Pipe](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#lpac)


### Raytracing [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#raytracing "Click to copy section url")

- [Prefer ray queries to ray pipelines](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-preferrayqueriestoraypipelines)

- [Minimize calls to rayQuery Proceed()](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-minimize-calls-to-ray-query-proceed)

- [Avoid proceed() calls in loops for non-opaque traversal that “accept first fit”](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-avoid-proceed-calls-in-accept-first-fit-loops)

- [Use only one ray query object; reuse as needed](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-one-ray-query-object)

- [Access ray query data through intrinsics](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-intrinsics-to-access-ray-query-data)

- [Prefer building, serializing and deserializing acceleration structures on the GPU](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-prefer-building-raytracing-acceleration-structures-on-gpu)

- [Refit and rebuild deformable raytraced meshes judiciously](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-raytracing-acceleration-structures-refitting-rebuilding)


### Queries [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#queries "Click to copy section url")

- [Use occlusion queries correctly for accuracy and efficiency](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-occlusion-query-correct-usage)

- [Use GPU timestamp queries correctly for accuracy](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-gpu-timestamp-query-correct-usage)


### XR/VR/AR (Extended Reality/Virtual Reality/Augmented Reality) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#xr-vr-ar-extended-reality-virtual-reality-augmented-reality "Click to copy section url")

- Use [foveated rendering](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-foveated-rendering) to likely drastically improve performance and battery life with few or no noticeable artifacts


## Renderer Architecture [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#renderer-architecture "Click to copy section url")

Here are some overarching issues to keep in mind while architecting a renderer that will make the most of Adreno’s performance and battery usage.

### Graphics API [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#graphics-api "Click to copy section url")

Prefer Vulkan to OpenGL ES. While Vulkan is not a perfect superset of OpenGL ES, in most respects it is more performant, more debuggable, and more fully featured.

### Render Pass [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#render-pass "Click to copy section url")

Minimize the number of render passes – for example, any time several consecutive passes use the same formatted color buffer, combine them (disabling depth and/or stencil if one or both are unused). [Snapdragon Profiler](https://docs.qualcomm.com/doc/80-78185-2/topic/sdp.html#sdp) shows how renderpasses and subpasses are (or are not) merged on its [Rendering Stages](https://docs.qualcomm.com/doc/80-78185-2/topic/sdp.html#sdp) metric.

When combining the results of multiple passes (as in deferred rendering or blending transparent objects with opaque objects), prefer using alpha blending to the alternatives (such as the discard instruction, shader branching, stencil testing and compute shaders).

Many applications are fragment-shader bound, and Adreno has many tools to optimize such applications:

- Render target resolutions can be efficiently [upscaled in several ways](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-upscaling-best-practices)

- [Variable Rate Shading](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vrs-best-practices) shades fewer pixels

- Framerate [Extrapolation](https://github.com/quic/adreno-gpu-opengl-es-code-sample-framework/tree/main/samples/amfe_power_saving) can also nearly double a fragment-bound application’s framerate


Depending on content, these features can involve little to no visual quality degradation.

When performing depth-only rendering (like a depth-prepass), use an empty fragment shader and disable frame buffer writes to [leverage Fast-Z](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#fast-z).

Invalidate framebuffer contents as early as possible, so the [driver doesn’t wastefully resolve GMEM render target memory to system memory](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-rendering):

VulkanOpenGL ES

To invalidate framebuffer contents as early as possible, correctly use VK\_ATTACHMENT\_LOAD\_OP\_CLEAR and VK\_ATTACHMENT\_LOAD\_OP\_DONT\_CARE on your renderpass (and VK\_QCOM\_render\_pass\_shader\_resolve if a nonstandard shader resolve is desired).

Correct subpass handling is also essential.

Vulkan introduced render ‘subpasses’, which allow developers to set up render pipelines that explicitly state their usage, render target interactions, dependencies, transitions, etc. This allows GPUs to make informed decisions about how to handle these frame buffer transitions efficiently. To efficiently use GMEM, proper subpass use is crucial in [tile-rendering architectures](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-rendering) such as the Adreno GPU.

A properly structured renderpass allows Vulkan to instruct the GPU to execute all subpasses on a per-tile basis. That is, the full subpass chain can be executed for each tile, thus avoiding the need to resolve subpasses to system memory after each pass. Proper setup of these subpasses is required for the Vulkan driver to “merge” the subpasses into one. This can result in gains of over 10% frametime depending on subpass chain complexity and configuration.

Generally, a good Vulkan renderpass involves the following:

- Subpass count > 1

- Renderpass has input targets

- Each resolve attachment is used in an exactly one subpass

- srcAccessMask is not VK\_ACCESS\_SHADER\_WRITE\_BIT, and dstAccessMask is not VK\_ACCESS\_SHADER\_READ\_BIT

- Starting from the second subpass where the input\_attachments field is used, the dstAccessMask must be set to VK\_ACCESS\_INPUT\_ATTACHMENT\_READ\_BIT


Note

Subpass merging only applies when the given surface is being rendered in binning mode. [Snapdragon Profiler](https://docs.qualcomm.com/doc/80-78185-2/topic/sdp.html#sdp) ‘Rendering Stages’ metric in [Trace](https://docs.qualcomm.com/doc/80-78185-2/topic/sdp.html#sdp-trace) capture identifies the mode these surfaces are being rendered with, and if proper merging has been done. Additionally, using the [Vulkan Adreno Layer](https://docs.qualcomm.com/doc/80-78185-2/topic/vk_adreno_layer.html#vk-adreno-layer) can also help identify if subpasses were not be merged properly by logging the VKDBGUTILWARN003 flag.

Sample Code:

- [SubPass](https://github.com/quic/adreno-gpu-vulkan-code-sample-framework/tree/main/samples/SubPass)

- [Tonemapping Efficiently](https://github.com/quic/adreno-gpu-vulkan-code-sample-framework/tree/main/samples/shaderResolveTonemap)


VulkanOpenGL ES

Pass VK\_PIPELINE\_CREATE\_LINK\_TIME\_OPTIMIZATION\_BIT\_EXT in shipping builds to maximize performance.

Prefer uniform buffers instead of push constants for performance.

### Shader mode switching [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#shader-mode-switching "Click to copy section url")

Minimize pipeline and compute kernel switching to avoid unnecessary internal synchronization – and particularly minimize alternating between graphics submits and compute dispatches.

In other words, separate graphics submits and compute dispatches as much as possible – ideally issue a series of only graphics submits followed by a series of only compute dispatches.

And even within the phase (or, possibly less optimally, phases) of the frame where graphics submits take place, minimize interleaving pipelines – for example, prefer (SubmitGraphicsPipelineA 2 times, SubmitGraphicsPipelineB) to (SubmitGraphicsPipelineA, SubmitGraphicsPipelineB, SubmitGraphicsPipelineA). The same rationale applies to dispatching compute kernels.

### Images [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#images "Click to copy section url")

Vulkan image layout datastructures should be as specific as possible. This is significantly more important for performance on Adreno hardware than on many other GPU’s.

[VK\_IMAGE\_CREATE\_MUTABLE\_FORMAT\_BIT should be avoided as much as possible on all devices prior to Adreno750.](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vk-image-create-mutable-format-bit)

### Buffer Best Practices [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#buffer-best-practices "Click to copy section url")

Flag all buffers read-only as much as possible.

Prefer Vertex Buffer Objects (VBOs) when possible.

Otherwise prefer uniform buffers (UBOs) provided the sum of their sizes for a given shader remain under 90% of 8K – 0.9\*8192 = 7372 bytes. Note that the maximum size reported by graphics APIs (in Vulkan, vkPhysicalDeviceLimits::maxUniformBufferRange) is only a correctness limit – not a performance limit. Note that the sum of all uniform buffers used by a shader – not just each uniform buffer individually – must stay under this limit to avoid this possible performance reduction.

For larger data sizes prefer textures over Shader Storage Buffer Objects (SSBOs).

If a UBO exceeds its optimal size, the compiler will attempt to determine which portion of the UBO may be accessed by the shader, and map only those portions of the UBO to constant RAM. Dynamic or indirect indexing might prevent this optimization, so if your UBO might exceed its optimal size (and you choose not to use textures or SSBOs), prefer static indexing.

Vulkan: use VK\_MEMORY\_PROPERTY\_LAZILY\_ALLOCATED\_BIT for buffers that are not read from outside of the renderpass (especially MSAA attachments, which are larger than non-MSAA attachments). For example, a Z-buffer that exists only to be cleared and used for typical z-buffering within a single renderpass should use this flag.

### Vulkan [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#vulkan "Click to copy section url")

[Avoid less performant features of the API](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vulkan-less-performant-features)

If you encounter VK\_DEVICE\_LOST, calling VK\_EXT\_device\_fault is your only option – calling any other part of the API is undefined.

[Vulkan image layout datastructures should be as specific as possible.](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vulkan-image-layout-specific)

#### Swapchain [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#swapchain "Click to copy section url")

Use VK\_PRESENT\_MODE\_FIFO\_KHR and minImageCount=3 to most efficiently utilize the GPU (VK\_PRESENT\_MODE\_MAILBOX\_KHR can sometimes help with frame pacing/latency, but often can cost significant battery and generate significant heat for no benefit, as it may renders frames that are not presented to the player)

Vulkan: use [prerotation](https://docs.vulkan.org/samples/latest/samples/performance/surface_rotation/README.html)

### Triangle Screen Size [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#triangle-screen-size "Click to copy section url")

Ideally every triangle rasterized shades at least 4 pixels; tune level-of-detail (LOD) systems and content accordingly.

If a triangle spans multiple tiles in binning mode, the full triangle will be rasterized per tile – there are no added vertices at tile boundaries. Therefore, many triangles much larger than the bin size in screenspace can be inefficient.

### Features to avoid for performance reasons [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#features-to-avoid-for-performance-reasons "Click to copy section url")

- Vulkan:

  - VK\_IMAGE\_CREATE\_MUTABLE\_FORMAT\_BIT: since the driver doesn’t know which view formats will be paired with the image, this often reduces performance. Additionally this flag usually degrades or disables [UBWC](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-universal-bandwidth-compression-ubwc-best-practices)

  - VK\_EXT\_conditional\_rendering is unlikely to improve performance unless it’s skipping a large amount work, as its overhead is substantial

  - VK\_EXT\_vertex\_input\_dynamic\_state should be used minimally – static pipelines are strictly more performant

  - Avoid [VkPipelineInputAssemblyStateCreateInfo::primitiveRestartEnable](https://registry.khronos.org/vulkan/specs/latest/man/html/VkPipelineInputAssemblyStateCreateInfo.html) – simply performing multiple draws will almost always outperform this approach


- Tessellation hardware stages (hull shader, tessellator, domain shader)

- Client-side vertex arrays

- User clip planes


## [Tile-based Rendering](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#tile-rendering) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#tile-based-rendering "Click to copy section url")

### Bin Minimization [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#bin-minimization "Click to copy section url")

Some performance bottlenecks for a render target can be alleviated by reducing the number of bins the driver generates (which, in turn, often increases the number of pixels each bin contains). The developer has several options:

- reduce frame buffer resolution

- use [Variable Rate Shading](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vrs-best-practices) (including foveated rendering) to render fewer fragments


- use fewer MSAA samples. In particular, MSAAx2 is likely to be practically free (while this can generate more bins, and lots of small draws in the extra bins may incur more binning overhead, this and the additional resolve time are usually small enough to be hidden by other bottlenecks)

- render to fewer render targets at once


### [FlexRender™ technology (Hybrid Deferred and Direct Rendering mode)](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#flex-render) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#flexrender-technology-hybrid-deferred-and-direct-rendering-mode "Click to copy section url")

The driver heuristics that determine [when to run binned or direct mode](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#flex-render) are not exposed to the developer, but generally these scenarios trigger direct mode:

- High ratio of texture samples in vertex shaders to vertices

- Small number of vertices and/or draws

- Use of tessellation or geometry shaders


### [Concurrent Binning](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#concurrent-binning-overview) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#concurrent-binning "Click to copy section url")

No additional steps are required to activate concurrent binning – but care should be taken to maximize its benefits.

Sequential render passes with dependencies might require synchronous binning – concurrent binning is only possible when there are “bubbles” in the render graph. Consider the renderpass chain:

![Concurrent Binning](<Base64-Image-Removed>)

_Pass C_ uses binning but – unfortunately – its binning process depends on _Pass B_, which depends on _Pass A_.

If we remove the binning dependencies from _Pass B_ – so _Pass C_’s vertex shader doesn’t require any inputs from _Pass B_ (perhaps by revisiting renderpass setup and barriers) – the driver might asynchronously perform binning during _PassB_ and/or _PassC_ on the concurrent binning pipe:

![Concurrent Binning](<Base64-Image-Removed>)

Another way concurrent binning can be prevented is reusing the same Z-buffer attachment with clears within a frame (you might issue these clears if, for example, the Z-buffer is being used for multiple purposes within a frame). These clears define dependencies, and thus prevent concurrent binning for every render pass or compute operation that uses this Z-buffer attachment.

Try to use the same Z-buffer – without clears or invalidations – over multiple render passes to allow concurrent binning. (If this is not possible, giving each renderpass its own Z-buffer also allows concurrent binning, though this risks using more memory bandwidth and costs memory)

Another common case that fails to leverage concurrent binning is when the application is VSYNC limited, and the first surface processes all the geometry. In such a scenario, try to schedule some independent work before submitting that geometry-heavy render pass so both the independent work and the first surface’s geometry binning can happen in parallel.

If your app is CPU-bound and you’re willing to accept up to one extra frame of latency, another approach is to continue issuing rendering work until your synchronization primitives indicate that the CPU is ready to submit work from frame N+2 but the GPU has not yet completed frame N. In this way, the driver is encouraged to perform frame N+1’s binning work concurrently with frame N’s non-binning work – particularly if most of the binning work occurs early in the frame.

### [Tile Shading Vulkan Extensions](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#tile-shading-vulkan-extensions) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#tile-shading-vulkan-extensions "Click to copy section url")

[Minimizing renderpasses](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-minimize-render-passes) is often critical to maximizing the benefits of using the tile shading Vulkan extensions, since this enables the developer to minimize synchronization and system memory usage in favor of [GMEM](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-rendering).

#### [VK\_QCOM\_tile\_memory\_heap](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#vk-qcom-tile-memory-heap-overview) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#vk_qcom_tile_memory_heap "Click to copy section url")

When your images and/or buffers fit the device’s tile memory constraints and are used over several render passes (as in deferred rendering), consider using [VK\_QCOM\_tile\_memory\_heap](https://registry.khronos.org/vulkan/specs/latest/man/html/VK_QCOM_tile_memory_heap.html) to allocate images and/or buffers on [GMEM](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-rendering) and have them stay resident as long as possible.

Use [VkTileMemorySizeInfoQCOM](https://registry.khronos.org/vulkan/specs/latest/man/html/VkTileMemorySizeInfoQCOM.html) to specify the amount of tile memory in use during the relevant render passes.

If an image/buffer is used only to hold intermediate results, allocate them in [GMEM](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-rendering) for as long as they are needed. This saves bandwidth, which can translate into battery and/or performance savings.

If a render pass is to use one resource in tiled memory – and then stop using that resource and start using another resource – consider using [VkTileMemorySizeInfoQCOM](https://registry.khronos.org/vulkan/specs/latest/man/html/VkTileMemorySizeInfoQCOM.html) to allocate just enough memory to accommodate the largest of the resources and then alias each resource, reading and storing as needed.

#### [VK\_QCOM\_tile\_shading](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#vk-qcom-tile-shading-overview) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#vk_qcom_tile_shading "Click to copy section url")

Always enable [VK\_QCOM\_tile\_memory\_heap](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vk-qcom-tile-memory-heap-best-practices) as well as VK\_QCOM\_tile\_shading so the driver efficiently uses whatever GMEM you leave unallocated. Using just VK\_QCOM\_tile\_shading alone is never recommended, because then the driver tends to use far less GMEM than it otherwise could.

Always use [VK\_DEPENDENCY\_BY\_REGION\_BIT](https://registry.khronos.org/vulkan/specs/latest/man/html/VkDependencyFlagBits.html) for subpass dependencies and pipeline barriers that might execute during [per-tile blocks](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-shading-per-tile-block) – omitting [VK\_DEPENDENCY\_BY\_REGION\_BIT](https://registry.khronos.org/vulkan/specs/latest/man/html/VkDependencyFlagBits.html) will probably deactivate [VK\_QCOM\_tile\_shading](https://registry.khronos.org/vulkan/specs/latest/man/html/VK_QCOM_tile_shading.html) and remove all associated benefits.

In the unlikely event that you find the driver employing [“Direct” Render Mode](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#flex-render) on a surface that uses a [per-tile block](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-shading-per-tile-block), performance on the [per-tile block](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-shading-per-tile-block) commands is likely very poor. Every effort should be made to discourage the driver from using [“Direct” Render Mode](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#flex-render) during [per-tile blocks](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-shading-per-tile-block).

**Attachment Limitations**

* * *

A developer might reasonably think to use [VK\_QCOM\_tile\_shading](https://registry.khronos.org/vulkan/specs/latest/man/html/VK_QCOM_tile_shading.html) to perform stores on a color attachment from a fragment shader to ensure that [GMEM](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-rendering) is used instead of system memory. However, the typical fragment shading pattern is practically guaranteed to be as – and typically much more – performant than this approach, so using [VK\_QCOM\_tile\_shading](https://registry.khronos.org/vulkan/specs/latest/man/html/VK_QCOM_tile_shading.html) to bind a color attachment as a storage image and access it through image load/store ops is not supported via fragment shader.

Similarly, neither compute nor fragment shaders may store to depth/stencil attachments, resolve attachments or input attachments – for such operations, the typical fragment shading pattern should be used.

On the other hand, storing to a color attachment from a compute shader is supported, and may perform acceptably.

**Optimizing** [Per-Tile Draws](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-shading-per-tile-draws)

* * *

Draws executed within a [per-tile block](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-shading-per-tile-block) ( [per-tile draws](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-shading-per-tile-draws)) are optimized for GPU-driven rendering – specifically the case where a per-tile dispatch invokes a per-tile compute shader that writes data to an indirect buffer, followed by a per-tile vkCmdDrawIndirect\* that consumes that same buffer.

Other than such GPU-driven rendering, [per-tile draws](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-shading-per-tile-draws) may not perform well – for CPU-driven rendering, we recommend standard execution (where, in a single draw call, the render pass or dynamic rendering scope’s entire render area is accessible and is optionally stored in [GMEM](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vk-qcom-tile-shading-best-practices) by the [VK\_QCOM\_tile\_memory\_heap extension](https://registry.khronos.org/vulkan/specs/latest/man/html/VK_QCOM_tile_memory_heap.html)).

Given this, hopefully it’s clear how [per-tile draws](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-shading-per-tile-draws) are specifically for GPU-driven draws with tile-dependent draw data – regular draws will likely see a performance loss if executed within per-tile blocks.

Finally, you should ensure that each [per-tile draw](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-shading-per-tile-draws) contains only primitives that cover the current tile, since [per-tile draw](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-shading-per-tile-draws) are not affected by the visibility pass – instead they are executed no matter how the draw rasterizes within the tile (even if the tile’s pixels will not be written to!)

Some empirical results of using the extension are [collected here](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#mobile-vk-qcom-tile-memory-heap-empirical-results).

## [Render Surfaces](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#render-surfaces) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#render-surfaces "Click to copy section url")

### [sRGB textures and render targets](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#srgb-texture) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#srgb-textures-and-render-targets "Click to copy section url")

Use [SRGB textures](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#srgb-texture):

VulkanOpenGL ES

Vulkan fully handles sRGB in both textures and swapchain presentable images.

The best-performing color format is:

- R10G10B10A2, as the hardware is optimized for this format

- R11G11B10A0 if even greater color depth is required, and alpha transparency is not

- RGBA16 if graduated transparency is required, or the (considerable) color depth of the above formats is insufficient


[Vulkan Sample: Qualcomm TrueHDR](https://github.com/quic/adreno-gpu-vulkan-code-sample-framework/tree/main/samples/hdrSwapchain)

### Upscaling [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#upscaling "Click to copy section url")

To reduce the load on the rendering hardware, an application can reduce the size of the render target used, e.g., if the native screen resolution is 1080p (1920x1080), it could be rendered to a 720p (1280x720) render target instead. Since the aspect ratio of the two resolutions is identical, the proportions of the image will not be affected.

The reduced-size render target will not completely fill the screen, but there are [numerous ways of upscaling](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-upscaling-best-practices) the reduced-size render target to match the full native display size.

This technique has been used successfully in console games, many of which make heavy demands on the GPU and, if rendering were done at full HD resolution, could miss framerate targets due to too much time spent during fragment shading.

Upscale to improve fragment-bound frames with:

Snapdragon Game Super ResolutionAndroid

[Snapdragon GSR](https://github.com/quic/snapdragon-gsr) is a single pass spatially-aware super resolution technique developed by Qualcomm Snapdragon Studios to achieve optimal super scaling quality at the best performance and power savings – it uses optimized image processing to, for most content, achieve a sharper, higher-quality image than the typical bilinear filtering approaches.

You can also do this yourself with your preferred graphics API. The upscaling can be done either at the end of the rendering process or at some point in the rendering pipeline – for example, one approach is to render the geometry at 1:1 resolution, but apply postprocessing effects using render targets of a lower resolution.

VulkanOpenGL ES

vkCmdBlitImage() provides a [hardware-accelerated path](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-use-2d-operation-hardware-acceleration) to upscaling an image prior to display.

On Android, at the end of the frame, if the final render target is a different resolution than the device’s native resolution then SurfaceFlinger will bilinearly rescale the final image to native resolution with efficiency.

### Bandwidth Optimization [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#bandwidth-optimization "Click to copy section url")

Applications becoming memory-bandwidth limited can be a bottleneck due to the physical limitation of the GPU’s data access rate. The rate is not constant and varies according to many factors, including but not limited to:

1. Location of the data: is it stored in RAM, VRAM, or one of the GPU caches?

2. Type of access: is it a read or a write operation? Is it atomic? Does it have to be coherent?

3. Viability of caching the data: can the hardware cache the data for subsequent operations that the GPU will be carrying out, and would it make sense to do this?


Cache misses can cause applications to become bandwidth-limited, which significantly reduces performance. These cache misses are often caused when applications draw or generate many primitives, or when shaders need to access many locations within textures.

Here are ways to minimize cache misses:

1. Reduce the amount of data the GPU needs to access to perform the dispatch or draw call that is hitting this constraint

2. In OpenGL, ensure that [client-side vertex data buffers](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-less-performant-features) are used for as few draw calls as possible – ideally, an application should never use them


Graphics APIs provide several methods that developers can use to reduce the bandwidth needed to transfer specific types of data.

The first method is [compressed texture internal formats](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#texture-compression), which sacrifice texture quality for the benefit of reduced size. Many of the compressed texture formats supported divide the input image into 4x4 blocks and perform the compression process separately for each block, rather than operating on the image as a whole. While this seems inefficient from the point of view of data compression theory, doing so has the advantage of each block being aligned on a 4-pixel boundary. This allows the GPU to retrieve more data with a single fetch instruction, because each compressed texture block holds 16 pixels instead of a single pixel, as in the case of an uncompressed texture. Also, the number of texture fetches can be reduced, provided that the shader does not need to sample texels that are too far apart.

The second method is to always use [packed vertex data formats](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vertexattributescompress), unless the vertex data sets would suffer greatly from a reduction in the precision of their components.

The third method is to always use [indexed draw calls](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-geometry-instancing), and always use an [index type that is as small as possible](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-indexbuffercompress) while still being able to address all the vertices for the mesh being drawn. This reduces the amount of index data that the GPU needs to access for each draw call, at the expense of slightly more complicated application logic.

#### [Universal BandWidth Compression (UBWC)](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#universal-bandwidth-compression-ubwc) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#universal-bandwidth-compression-ubwc "Click to copy section url")

Graphics APIs must be used correctly to maximize the use of [UBWC](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#universal-bandwidth-compression-ubwc). For example, VK\_IMAGE\_TILING\_OPTIMAL generally uses [UBWC](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#universal-bandwidth-compression-ubwc) as expected, but these Vulkan features almost certainly disable [UBWC](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#universal-bandwidth-compression-ubwc):

- [Compute Shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#compute-shaders-device-specific)

- Non-optimal tiling: VK\_IMAGE\_TILING\_LINEAR

- Any kind of Cpu readback from the Gpu, including VK\_EXT\_host\_image\_copy/VK\_IMAGE\_USAGE\_HOST\_TRANSFER\_BIT

- [VK\_KHR\_fragment\_shading\_rate](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#vrs)

- VK\_EXT\_fragment\_density\_map

- Aliased images: VK\_IMAGE\_CREATE\_ALIAS\_BIT

- Mutable images: VK\_IMAGE\_CREATE\_MUTABLE\_FORMAT\_BIT

- Sparse residency of any kind: VK\_IMAGE\_CREATE\_SPARSE\_RESIDENCY\_BIT, VK\_IMAGE\_CREATE\_SPARSE\_BINDING\_BIT, VK\_IMAGE\_CREATE\_SPARSE\_ALIASED\_BIT


## Z-Buffer [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#z-buffer "Click to copy section url")

The best-performing depth format is:

- D16, if stencil is unnecessary and this provides sufficient precision – which, in many cases where the developer is tuning a z-reverse implementation appropriately to content, it will

- D24\_S8, if stencil is required

- D32, if stencil is not required and D16 does not provide sufficient precision


[UBWC](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#universal-bandwidth-compression-ubwc) supports all these formats.

## LRZ, Early-Z and Fast-Z [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#lrz-early-z-and-fast-z "Click to copy section url")

### [Low Resolution Z pass](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#lrz) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#low-resolution-z-pass "Click to copy section url")

The ways in which [LRZ (Low Resolution Z-Buffer)](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-lrz-do-not-disable) and [Early Z Rejection](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-early-z-rejection-do-not-disable) optimizations can be disabled are complex.

Broadly speaking: blending, stencil use, manually writing to the depth buffer or UAVs, alpha-to-coverage use, the “discard” shader keyword, changing the depth comparison operator, reading from the framebuffer, or masked writes (whether to color channels or a subset of multiple render targets) all might disable [LRZ (Low Resolution Z-Buffer)](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-lrz-do-not-disable), [Early Z Rejection](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-early-z-rejection-do-not-disable) or both – so if any of these operations must be done, perform them as near the end of the frame as possible (or see if the details below allow any such operations for your specific case).

Warning

Several conditions cause the driver to disable LRZ for a period of time between two operations.

LRZ (test and write operations) will be disabled until the next API-surface-clear by performing any of the below, and then executing a depth-write:

> - changing the depth direction (eg the sign of the forward axis)
>
> - setting the depth function to ALWAYS or NOT\_EQUAL

LRZ write operations will be disabled until next API-surface-clear (note that test operations on the existing LRZ buffer will still be enabled) by performing:

> - any of the below, and then later performing a depth-write in the same draw:
>
>
> > - blending implemented with:
> >
> >
> >     > - the fixed-function pipeline
> >     >
> >     >     - logical operations that read from the framebuffer
> >
> >   - a color-masked write (eg writing to a subset of a buffer’s color channels using graphics API calls rather than shader code)
> >
> >   - a partial Multiple Render Target (MRT) write (eg writing to a subset of all specified render targets)
>
> - in any subpass, a depth-write and reading from any attachment modified in any prior subpass of this renderpass (the order of operations is irrelevant – it doesn’t matter if the depth-write happens before or after the read from the previously-modified-attachment)
>
> - any stencil operation (reads or writes) in almost any situation
>
> - a framebuffer fetch
>
> - “advanced” blending with extensions

LRZ (test and write operations) will be disabled for the current draw (note that by default the next draw will fully re-enable LRZ) if the fragment shader writes to:

> - a UAV (any kind of buffer)
>
> - depth or stencil

LRZ write operations will be disabled for the current draw (note that test operations on the existing LRZ buffer will still be enabled, and that by default the next draw will fully re-enable LRZ) if:

> - the draw’s active pipeline has alpha-to-coverage enabled
>
> - a fragment-shader:
>
>
> > - uses discard
> >
> >   - outputs sample coverage

Vulkan: LRZ (test and write operations) will be disabled if secondary command buffers are used (this limitation applies only for devices prior to Adreno650)

LRZ is fully active during direct rendering (presuming it isn’t [disabled for some other reason](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-lrz-do-not-disable)), but typically produces much less performance benefit than with binned rendering

### [Early Z rejection](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#early-z-rejection-overview) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#early-z-rejection "Click to copy section url")

Warning

Early Z-rejection is disabled if:

- Z-Buffer is written to from a fragment shader

- “Discard” shader instruction is used

- A fragment shader writes depth or stencil values – if these writes are necessary, perform them as late in the frame as possible

- Alpha-to-Coverage is enabled (minimize the use of this feature)


Adreno GPUs can reject occluded pixels at up to 4x the drawn pixel fill rate.

### [Fast-Z](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#fast-z) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#fast-z "Click to copy section url")

Hint the driver to engage Fast-Z by using an empty fragment shader and disabling frame buffer write masks for renderpasses that modify Z values only.

If fast-Z doesn’t activate by default for indirect draws, it can be switched on with [glsl.](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-early-zindirect)

## [Vertex and Index Buffers](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html\#vertex-and-index-buffers-device-specific) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#vertex-and-index-buffers "Click to copy section url")

### Vertex buffer layout [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#vertex-buffer-layout "Click to copy section url")

Pass a single vertex buffer to the vertex shader.

The vertex buffer should begin with an interleaved array of all attributes that are used by the vertex shader to calculate final vertex positions – often this is nothing more than vertex positions arranged like: (xyz\|xyz) – followed by one interleaved array of all other attributes.

Compress all attributes as much as possible.

For any asset with a coordinate range known in advance, try to map the data onto one of the supported, packed vertex data formats. Taking normal data as an example, it is possible to map XYZ components onto the GL\_UNSIGNED\_INT\_2\_10\_10\_10\_REV (OpenGL ES) format by normalizing the 10-bit unsigned integer data range of <0, 1024> onto the floating-point range <-1, 1>.

VulkanOpenGL ES

Vulkan does not yet support half-precision in vertex shaders.

The compiler will usually optimize the binning vertex shader to use only the vertex attributes the vertex shader – called a [position-only vertex shader](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#position-only-vertex-shader) – that needs to compute final vertex positions – any attributes that are simply forwarded to the fragment shader (by Vulkan’s “layout”/”out” or OpenGL’s “varying/flat”) will be “refactored” into code that runs immediately before the fragment shader, resulting in better performance.

In addition to the above, vertex information can be [laid out in a cache-friendly way over a range of devices](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#vertex-cache-size), such that triangles sharing the same vertex are more often clustered together – doing so can reduce vertex cache misses and increase performance.

### Batching vertex buffer object updates [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#batching-vertex-buffer-object-updates "Click to copy section url")

If you must modify Vertex Buffer Object contents on-the-fly when rendering a frame, batch as many of the VBO updates as possible before issuing any draw calls that use the modified VBO region. If using multiple VBOs, batch the updates for all the VBOs first, and then issue all the draw calls.

Not doing so might cause the driver to maintain multiple copies of an entire VBO, which reduces performance.

### Index types [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#index-types "Click to copy section url")

A geometry mesh can be represented by two separate arrays. One array holds the vertices, and the other holds sets of three indices into that array. Together, they define a set of triangles.

Adreno GPUs natively support 8-bit, 16-bit, and 32-bit index types.

Prefer 8-bit indices when possible, 16-bit indices when necessary, and try to avoid 32-bit indices.

## [Texture Features](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html\#texture-features-device-specific) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#texture-features "Click to copy section url")

### Sampling in Vulkan [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#sampling-in-vulkan "Click to copy section url")

Use VK\_DESCRIPTOR\_TYPE\_COMBINED\_IMAGE\_SAMPLER to access the GPU’s more performant Bindless mode. We’ve seen separate samplers exhibit 2-5% less fill rate compared to combined samplers.

### Multiple textures [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#multiple-textures "Click to copy section url")

_Multiple texturing_ or _multitexturing_ is the use of [more than one texture at a time on a polygon.](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#multitexturing-limits-device-specific)

Effective use of multiple textures significantly reduces overdraw, saves ALU cost for fragment shaders, and avoids unnecessary vertex transforms.

### [Texture compression](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#texture-compression) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#texture-compression "Click to copy section url")

See [Texture Compression Examples](https://docs.qualcomm.com/doc/80-78185-2/topic/texture_compression_examples.html#texture-compression-examples).

### [Floating point textures](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#floating-point-textures-overview) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#floating-point-textures "Click to copy section url")

Adreno GPUs support floating point texturing features including the following:

- Texturing and linear filtering of FP16 textures via the GL\_OES\_texture\_half\_float and GL\_OES\_texture\_half\_float\_linear extension

- Texturing from FP32 textures via GL\_OES\_texture\_float


For a complete listing of supported texture and surface formats, refer to the [Texture formats](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#texture-formats) Feature Table.

### [Video textures](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#video-textures-overview) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#video-textures "Click to copy section url")

[Video textures](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#video-textures-overview) are a standard API feature in Android (Honeycomb or later versions). Refer to Android documentation for additional details on surface textures at [http://developer.android.com/reference/android/graphics/SurfaceTexture.html](http://developer.android.com/reference/android/graphics/SurfaceTexture.html).

Apart from using the standard Android API as suggested, the standard OpenGL ES extension can also be used, e.g., if an application requires video textures. For more information, refer to [http://www.khronos.org/registry/gles/ extensions/OES/OES\_EGL\_image.txt](https://registry.khronos.org/OpenGL/extensions/OES/OES_EGL_image.txt).

## [Shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html\#shaders-device-specific) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#shaders "Click to copy section url")

### Half-Precision [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#half-precision "Click to copy section url")

Adreno’s [scalar architecture](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#scalar-architecture) can be twice as power-efficient and deliver twice the performance while processing a fragment shader – if that fragment shader uses medium-precision 16-bit floating point (mediump) processing instead of high-precision 32-bit (highp) floating point.

Use strict half-precision types as much as possible. When necessary, relaxed-precision will often produce 16-bit floating point code.

### Instruction count [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#instruction-count "Click to copy section url")

A shader’s instruction count fitting the instruction cache is usually critical for avoiding shader stalls and thus achieving optimal performance.

If a shader must exceed a target device’s instruction limit (particularly if that shader rarely stalls on texture fetches and other slow operations that might allow the driver to swap in a different shader), consider [splitting the shader into multiple parts](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-split-up-draw-calls).

Compute shaders that run on [LPAC](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#lpac) have a [slightly higher instruction limit than other shaders.](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#lpac-shader-instruction-count-device-specific) Compute shaders than run on the Graphics Pipeline have the [typical (slightly lower) limit.](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#instruction-count-device-specific)

A low [% Wave Context Occupancy](https://docs.qualcomm.com/doc/80-78185-2/topic/sdp.html#sdp) can indicate long shaders thrashing the instruction cache.

### GPR minimization [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#gpr-minimization "Click to copy section url")

Keeping every shader’s register usage (called GPRs or General Purpose Registers) under the device limits will ensure that the maximum number of simultaneous waves execute, maximizing performance.

Modifying GLSL to save even a single instruction can save a GPR. Not unrolling loops can also save GPRs, but that is up to the shader compiler. Always profile shaders to make sure the final solution chosen is the most efficient one for the target platform. Unrolled loops tend to put texture fetches toward the shader top, resulting in a need for more GPRs to hold the multiple texture coordinates and fetched results simultaneously.

For example, if unrolling the loop presented below:

```undefined
for (i = 0; i < 4; ++i) {
    diffuse += ComputeDiffuseContribution(normal, light[i]);
}
```

The code snippet would be replaced with:

```undefined
diffuse += ComputeDiffuseContribution(normal, light[0]);
diffuse += ComputeDiffuseContribution(normal, light[1]);
diffuse += ComputeDiffuseContribution(normal, light[2]);
diffuse += ComputeDiffuseContribution(normal, light[3]);
```

Use [Vulkan specialization constants to implement “uber-shaders”](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-branching-vulkan-specialization-constants) (shaders that combine multiple shaders into a single shader that use static branching) or avoid the “uber-shader” design altogether. Using “uber-shaders” (without [Vulkan specialization constants](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-branching-vulkan-specialization-constants)) can sometimes reduce state changes and batch draw calls – but this often increases GPR count, which can reduce performance overall.

If GPR usage is too high, consider [splitting the shader into multiple parts](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-split-up-draw-calls).

A low [% Wave Context Occupancy](https://docs.qualcomm.com/doc/80-78185-2/topic/sdp.html#sdp) can indicate thrashing GPRs with too much register usage.

### Split up draw calls [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#split-up-draw-calls "Click to copy section url")

If a shader has too many instructions to fit the Instruction Cache, or uses too many GPRs, splitting it into multiple shaders may improve performance.

Vulkan’s [subpasses](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#vulkan-subpass-handling), correctly authored, keep intermediate results in GMEM, and is often the fastest approach. [Vulkan tile shading extensions](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-tile-shading-vulkan-extensions) are another way to keep intermediate results in GMEM.

Alternatively, values generated by ShaderA can be written to a texture or SSBO and later retrieved via by ShaderB – or the results of ShaderA can be alpha-blended into the results of ShaderB. Be aware that this approach risks a memory bandwidth bottleneck, so make sure there is plausible headroom in [% Texture Pipes Busy](https://docs.qualcomm.com/doc/80-78185-2/topic/sdp.html#sdp) before attempting this optimization, and profile before and after making the change.

### Minimize ALU Cost [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#minimize-alu-cost "Click to copy section url")

Even when a shader fits within the [instruction cache](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-instruction-count), instruction choices involving [type-casting](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-minimize-type-casting) (including converting floating point values from 32-bit to [16-bit precision](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-maximize-half-precision)), [control flow (branches and loops)](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-shader-control-flow), [built-in shader instructions](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-built-in-shader-instructions) and more all impact ALU efficiency.

#### Minimize type casting [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#minimize-type-casting "Click to copy section url")

Minimize the number of type cast operations performed.

For example, assigning a float to a vec4 data type could prevent the compiler from performing optimizations.

For another example, the following code might be suboptimal:

```powershell
uniform sampler2D ColorTexture;
in vec2 TexC;
vec3 light(in vec3 amb, in vec3 diff)
{
    vec3 Color = texture(ColorTexture, TexC);
    Color *= diff + amb;
    return Color;
}
```

Here, the call to the texture function returns a vec4. There is an implicit type cast to vec3, which requires an additional instruction. Changing the code as follows might not require the additional instruction:

```powershell
uniform sampler2D ColorTexture;
in vec2 TexC;
vec4 light(in vec4 amb, in vec4 diff)
{
    vec4 Color = texture(ColorTexture, TexC);
    Color *= diff + amb;
    return Color;
}
```

For another example, the following code should take a single instruction:

```cpp
int4 ResultOfA(int4 a) {
    return a + 1;
}
```

Now suppose a slight error is introduced into the code. For the example, the floating-point constant value 1.0 is used, which is not the appropriate data type:

```cpp
int4 ResultOfA(int4 a) {
    return a + 1.0;
}
```

The code could now require eight instructions: the variable _a_ is converted to vec4, then, the addition is done in floating point. Finally, the result is converted back to the return type int4.

This discussion generally applies to converting floating point values from 32-bit to 16-bit precision as well.

#### Control Flow [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#control-flow "Click to copy section url")

Minimizing non-uniform looping and branching often helps reduce GPR and ALU usage.

Every time the branch encounters divergence, or where some elements of the thread branch one way and some elements branch in another, both branches will be taken and the results of the irrelevant branch ignored.

Here are several types of branches, listed from best to worst performance:

- Branching on a Vulkan specialization constant (no performance hit – the driver is guaranteed to strip any unused branches at shader-compile-time)

- Branching on a constant, known at compile time (possibly no performance hit – the driver might strip any unused branches at shader-compile-time)

- Branching on a uniform variable (some performance hit from loading and testing the uniform variable per-wave – and both branches may be executed)

- Branching on a variable modified inside the shader (maximum likelihood of a performance hit – the driver will probably execute both branches)


#### Pack shader interpolators [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#pack-shader-interpolators "Click to copy section url")

Shader-interpolated values (GLES varyings or Vulkan out variables) require a GPR (general purpose register) to hold data being fed into a fragment shader. Therefore, minimize their use.

Use constants where a value is uniform. Pack values together as all shader interpolated values have four components, whether they are used or not. Putting two vec2 texture coordinates into a single vec4 value is a common practice, but other strategies employ more creative packing and on-the-fly data compression.

Note

OpenGL ES 3.0 and ES 3.1 introduce various intrinsic functions to carry out packing operations.

#### Pack scalar constants [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#pack-scalar-constants "Click to copy section url")

Packing scalar constants into 4-vectors – or, failing that, 2-vectors – substantially improves hardware fetch effectiveness.

Consider the following code:

```java
float scale, bias;
vec4 a = Pos * scale + bias;
```

By changing the code as follows, fewer total instructions may be generated, because the compiler might replace several instructions with the more efficient “mad” instruction:

```java
vec2 scaleNbias;
vec4 a = Pos * scaleNbias.x + scaleNbias.y;
```

In this case, while the compiler might infer that the _scale_ and _bias_ variables should be stored in a single GPR to enable the “mad” instruction, it’s much more likely to store _scaleNbias_ in a single GPR, which in turn increases the likelihood of optimal instruction generation.

Note

OpenGL ES 3.0 and ES 3.1 introduce various intrinsic functions to carry out packing operations.

#### Use built-in shader instructions [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#use-built-in-shader-instructions "Click to copy section url")

Built-in functions are an important part of the glsl specification and should always be preferred to writing custom implementation. These functions are often optimized for specific shader profiles and for the capabilities of the hardware for which the shader was compiled.

Note

gl\_VertexID and gl\_InstanceID are removed as per the [GL\_KHR\_vulkan\_glsl](https://www.khronos.org/registry/vulkan/specs/misc/GL_KHR_vulkan_glsl.txt) extension, but gl\_InstanceIndex is available.

Note

gl\_Position, gl\_PointSize, gl\_ClipDistance, gl\_CullDistance are available in non-fragment stages

Refer to the [GL\_KHR\_vulkan\_glsl](https://www.khronos.org/registry/vulkan/specs/misc/GL_KHR_vulkan_glsl.txt) extension for details on changes to GLSL built-ins in Vulkan.

### Avoid discarding pixels in the fragment shader [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#avoid-discarding-pixels-in-the-fragment-shader "Click to copy section url")

Some developers believe that manually discarding (also known as killing) pixels in the fragment shader boosts performance. However:

- If some pixels in a thread are killed and others are not, the shader still executes

- It’s hard to predict how the shader compiler will generate microcode involving discard, so even in the unlikely case where performance is increased on one device or driver, this gain may be reversed on another device or driver


In theory, if all pixels in a thread are killed, the GPU will stop processing that thread as soon as possible. In practice, “as soon as possible” isn’t soon enough to help performance, and discard operations – like [modifying depth in fragment shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-modifying-depth-in-fragment-shaders) often [disable hardware optimizations](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-early-z-rejection-do-not-disable).

If a shader cannot avoid discard operations, the cost can be mitigated by executing the shader after (ideally all) opaque draw calls – generally, the later in the frame a discard operation takes place, the better.

### Avoid modifying depth in fragment shaders [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#avoid-modifying-depth-in-fragment-shaders "Click to copy section url")

Similar to [discarding fragments](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-avoid-discard-pixel), modifying depth in the fragment shader can [disable hardware optimizations](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-early-z-rejection-do-not-disable).

### Stay under performance-optimal resource limits [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#stay-under-performance-optimal-resource-limits "Click to copy section url")

Stay under target device performance limits with respect to the number of unique resources referenced by a shader:

- [vertex buffers](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#vertex-buffers-referenced-by-shader-device-specific)

- [uniform buffers](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#uniform-buffers-referenced-by-shader-device-specific)

- [samplers](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#samplers-limit-unique-in-shader-device-specific)

- [textures and SSBOs](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#textures-and-ssbos-limit-unique-in-shader-device-specific) (textures and SSBOs share hardware resources)


### Minimize texture fetches in vertex shaders [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#minimize-texture-fetches-in-vertex-shaders "Click to copy section url")

Adreno is based on a [unified shader architecture](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#unified-shader-architecture), which means vertex processing performance is similar to fragment processing performance.

However, for optimal performance it is best to [minimize texture sampling in vertex shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-texture-samples-in-vertex-shader-triggers-direct-mode) – and when this cannot be avoided, it is important to ensure that texture fetches in vertex shaders are localized (eg cache coherent) and always operate on compressed texture data.

One reason for this is that any such texture fetches will generally run twice – once in the [position-only shader](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#position-only-vertex-shader), and then again in the vertex shader – so you pay that cost twice.

The [position-only shader](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#position-only-vertex-shader) is designed to be very fast – but if it stalls on memory accesses, that often significantly slows the binning phase. If a vertex shader performs too many texture fetches in a vertex shader, the driver will switch to [Direct Mode](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-flex-render-best-practices), which is often less performant than [Binning Mode](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-flex-render-best-practices).

### Latency Hiding, and Load Balancing the Texture Pipe and Shader Pipe [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#latency-hiding-and-load-balancing-the-texture-pipe-and-shader-pipe "Click to copy section url")

To hide latency, and thus avoid shader stalls and increase performance, the Snapdragon™ Adreno™ GPU shader compiler converts some memory access requests into texture fetches.

To allow this, the data buffer must be read-only and a storage type – in Vulkan, this means a SSBO or Shader Storage Buffer Object (VK\_DESCRIPTOR\_TYPE\_STORAGE\_BUFFER) – as the texture pipe is capable only of reading. (The shader pipe can read and write).

Even with a read-only storage buffer, the Adreno driver will sometimes choose a global memory access over a texture fetch if it decides that the texture pipe is a bottleneck.

[Snapdragon Profiler](https://docs.qualcomm.com/doc/80-78185-2/topic/sdp.html#load-balance-shader-pipe-and-texture-pipe-sdp) can be used to monitor the effects of your changes on the texture pipe and shader pipe.

#### Texture Fetch Bottleneck Optimization [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#texture-fetch-bottleneck-optimization "Click to copy section url")

If texture fetches are a performance bottleneck, here are some optimization strategies:

- When possible, use vertex buffer objects instead of storage buffers. Note that most [GPU-driven rendering architectures](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#gpu-driven-rendering) are more likely to bottleneck the texture pipe, since they typically use storage buffers instead of vertex buffers

- Use uniform buffers objects instead of textures or storage buffers if the data fits in the [optimal uniform buffer size.](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-uniform-buffer-maximum-performant-size)

- Minimize texture fetches

- Minimize [texture cache misses](https://docs.qualcomm.com/doc/80-78185-2/topic/sdp.html#sdp) by rewriting shaders to access one cluster of data before moving to the next – texture cache misses significantly contribute to any texture pipe bottleneck. Hardware operates on blocks of 2x2 fragments, so shaders are more efficient if they access neighboring texels within a single block

- Avoid 3D textures, since fetching data from volume textures is expensive due to the complex filtering that needs to be performed to compute the result value

- Don’t exceed the performance limit the [number of samplers, as well as the sum of textures and SSBOs referenced by the shader](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-textures-ssbos-samplers-limit-unique-in-shader) (textures and SSBOs share hardware resources)

- Compress all textures to reduce memory usage and texture stalls

- Use mipmaps to better coalesce texture fetches and thus improve performance – at the cost of increased memory usage


Texture filtering can influence the speed of texture sampling. Filter performance is architecture/chip dependent, and you might see a benefit by using bilinear or nearest filtering over trilinear or anisotropic. Mipmap clamping may reduce the cost of using trilinear filtering, so the average cost might be lower in real-world cases. Nonetheless, adding anisotropic filtering multiplies with the degree of anisotropy – in other words, a 16x anisotropic lookup can be 16 times slower than a regular isotropic lookup. However, because anisotropic filtering is adaptive, this hit is taken only on fragments that require anisotropic filtering, which could be only a few fragments altogether. A rule of thumb for real world cases is that anisotropic filtering is, on average, less than double the cost of isotropic.

Shader-specific gradients, based on the dFdx and dFdy functions, cost more than a regular texture sample. These shader-specific gradients cannot be stored across lookups, so if a texture lookup is done again with the same gradients in the same sampler, it will incur the cost again.

In summary: usage of trilinear, anisotropic filtering, wide texture formats, 3D textures, texture lookup with gradients of different Lod, or gradients across a pixel quad may increase texture sampling time. The driver can be encouraged to [load-balance the texture pipe with the shader pipe](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-texture-latency-masking). [Snapdragon Profiler](https://docs.qualcomm.com/doc/80-78185-2/topic/sdp.html#load-balance-shader-pipe-and-texture-pipe-sdp) can be used to monitor the effects of your changes on the texture pipe and shader pipe.

### DXC and Glslang and the Texture Pipe [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#dxc-and-glslang-and-the-texture-pipe "Click to copy section url")

Many games and engines generate their shaders in one language and use conversion tools to translate these shaders into other languages – for example, HLSL can be converted to SPIRV using DXC or glslang.

These conversion tools might convert HLSL buffer types to GLSL storage buffers and vice versa – and, since storage buffers utilize the texture pipe, this can result in unexpected increases in texture usage.

The DXC documentation details what to expect when converting from HLSL to SPIRV: [https://github.com/Microsoft/DirectXShaderCompiler/blob/main/docs/SPIR-V.rst#constanttexturestructuredbyte-buffers](https://github.com/Microsoft/DirectXShaderCompiler/blob/main/docs/SPIR-V.rst#constanttexturestructuredbyte-buffers)

DXC’s texture format conversion is specifically documented as well: [https://github.com/microsoft/DirectXShaderCompiler/blob/main/docs/SPIR-V.rst#textures](https://github.com/microsoft/DirectXShaderCompiler/blob/main/docs/SPIR-V.rst#textures).

Aside from texture and buffer conversions, while most code generated from these tools works well on our hardware (and whenever possible we engage the creators of these tools to maintain and improve such code generation), sometimes these tools use instructions and idioms that perform well on PC and console, but have suboptimal performance on mobile GPUs.

### Compiling and linking during initialization [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#compiling-and-linking-during-initialization "Click to copy section url")

The compilation and linking of shaders is a time-consuming process that can produce framerate hitches if performed naively at runtime. It is recommended that shaders are loaded and compiled during initialization.

VulkanOpenGL ES

Performing all calls to vkCreateGraphicsPipelines() and vkCreateComputePipelines() during initialization should eliminate any framerate hitches due to shader compilation.

## [Compute Shaders](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html\#compute-shaders-device-specific) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#compute-shaders "Click to copy section url")

Prefer fragment shaders to compute shaders when possible, since compute shaders require kernel output to be written to memory before the next kernel can begin execute. By comparison fragment shaders use Adreno’s concurrent resolve hardware, which can write the results of a fragment program while allowing another fragment program to begin executing simultaneously.

Keep [instruction counts](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-instruction-count) below [device limits](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#instruction-count-device-specific) like any other shader (although issuing shaders to [LPAC has a slightly higher instruction limit](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#lpac-shader-instruction-count-device-specific)).

Tune [workgroup number](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#compute-shader-workgroup-number-multiples) (depending on whether shaders read each other’s memory) and [workgroup sizes](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#compute-shader-local-group-multiples) (depending on whether or not the shader significantly stalls in ways that cannot be optimized away) to avoid potential performance bottlenecks. Note the driver may not be able to execute the requested workgroup number or size optimally if the shader’s [GPR usage](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-gpr-minimization) or [instruction count](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-instruction-count) is too large to accommodate the simultaneous execution of the requested number of workgroups.

Warning

OpenGL ES: When calling glDispatchIndirect() with any workgroup size smaller than 64 – for example (32, 1, 1) = 32x1x1 = 32 – the Cpu may wait on the Gpu as a result of the driver mapping the indirect buffer to a larger workgroup size, since doing so involves a command buffer flush. To avoid this, use a workgroup size that is at least 64 – for example (64, 1, 1) = 64x1x1 = 64.

```typescript
layout(local_size_x = 32, local_size_y = 1, local_size_z = 1) in; //workgroup size = local_size_x*local_size_y*local_size_z = 32x1x1 = 32 -- make sure this equation produces at least 64 to avoid a Cpu-wait-on-Gpu
```

Avoid synchronizing compute threads if possible – if synchronization is required, prefer atomic operations between local groups to shader barriers.

[Separate graphics submits and compute dispatches as much as possible.](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-graphics-submits-compute-dispatches-separate)

## [GPU-Driven Rendering](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#gpu-driven-rendering) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#gpu-driven-rendering "Click to copy section url")

### [Geometry instancing](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#geometry-instancing-overview) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#geometry-instancing "Click to copy section url")

Geometry instancing calls include:

VulkanOpenGL ES

vkCmdDraw, vkCmdDrawIndexed, vkDrawIndirectCommand, and vkDrawIndexedIndirectCommand support instanced rendering.

### [Indirect draw calls](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#indirect-draw-calls-overview) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#indirect-draw-calls "Click to copy section url")

For example, if the renderer uses a scene graph, it is possible to cache the draw call arguments necessary to render a mesh’s nodes in a buffer object created at loading time. The buffer can then be used at render-time as an input to the glDrawArraysIndirect or glDrawElementsIndirect functions.

To ensure [fast-z mode for depth-only renderpasses](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#fast-z) that use indirect draws and SSBOs, activate SPIR-V ExecutionMode 4 (EarlyFragmentTest) by adding this qualifier in your GLSL shader:

```undefined
layout(early_fragment_tests) in;
```

[VK\_QCOM\_tile\_shading](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-vk-qcom-tile-shading-best-practices) can allow for efficient Gpu-driven implementations if [tile-based draws](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#tile-rendering) suit your algorithm.

#### Vertex streaming versus attribute fetching [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#vertex-streaming-versus-attribute-fetching "Click to copy section url")

Vertex streaming is more performant than attribute fetching when architecting your renderer in the [GPU-driven style](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#gpu-driven-rendering).

## [Low Priority Asychronous Compute (LPAC)](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#lpac) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#low-priority-asychronous-compute-lpac "Click to copy section url")

LPAC is available on A740 devices and higher.

Running a compute shader on LPAC requires extension [VK\_KHR\_global\_priority](https://registry.khronos.org/vulkan/specs/latest/man/html/VK_KHR_global_priority.html). Then you must request a queue that supports only compute and transfer and has [VkQueueGlobalPriority](https://registry.khronos.org/vulkan/specs/latest/man/html/VkQueueGlobalPriority.html) [VK\_QUEUE\_GLOBAL\_PRIORITY\_LOW\_EXT](https://registry.khronos.org/vulkan/specs/latest/man/html/VK_KHR_global_priority.html). This queue is the LPAC queue: it will run concurrently (and at a lower priority, generally taking longer to complete) than the graphics/compute/transfer queue (the Graphics Pipe).

LPAC has a slightly larger [instruction cache](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#lpac-shader-instruction-count-device-specific) than shaders than run on the Graphics Pipe.

## [Mesh Shading](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html\#mobile-mesh-shading-device-specific) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#mesh-shading "Click to copy section url")

Avoid amplification shaders unless necessary – while they often perform well, they also incur a nonzero performance cost.

Set the [optimal wave count](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#mobile-meshshadingwavecountoptimal-specs) when possible.

Per-vertex attributes typically perform better than per-primitive attributes (even when per-primitive attributes might theoretically result in a smaller attribute memory footprint) – many if not most algorithms can entirely avoid the PerPrimitiveEXT keyword.

Keep mesh shader payload sizes under [device limits](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#mesh-shading-payload-size-threshold) to avoid a performance bottleneck.

Consider using [LPAC](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#lpac) to load-balance with the Graphics Pipe.

## [Raytracing](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html\#mobile-raytracing-device-specific) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#raytracing "Click to copy section url")

### [Hit detection](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#raytracing-hit-detection-overview) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#hit-detection "Click to copy section url")

Vulkan implements hit detection with the VK\_KHR\_acceleration\_structure extension. This structure can be constructed on the CPU or GPU (we recommend [constructing it on the GPU](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-prefer-building-raytracing-acceleration-structures-on-gpu)). Unless your scene is entirely static, the structure will need to be updated as geometry and/or lights move. While this updating cost can be substantial, it can also be amortized over several frames, often with few or zero artifacts.

Developers can query ray-hit information during any shader stage via the VK\_KHR\_ray\_query extension – any algorithm that requires ray-occlusion information likely starts here:

![../_images/raytracing2.png](<Base64-Image-Removed>)

### Application example: shadow generation [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#application-example-shadow-generation "Click to copy section url")

![../_images/raytracing3.png](<Base64-Image-Removed>)

With a rasterization-only pipeline, shadow generation can be expensive and may not generate consistently good visual results.

With ray tracing, shadows can be added with a few lines of shader code and a reasonably optimal acceleration structure. Fine detail can be achieved without requiring intermediate surfaces or other algorithms – just querying per-pixel visibility provides precise occlusion information, the results of which can be further manipulated by other post-processing techniques.

![../_images/raytracing4.png](<Base64-Image-Removed>)

This sample generates a shadowmap in a subpass by raytracing from the main light source (a point-light). This query logic and the acceleration structure management are the only additions raytracing needs to determine pixel occlusion – the surrounding code remains the traditional rasterization approach.

```cpp
// Initialize the query object
rayQueryEXT rayQuery;
rayQueryInitializeEXT(
    rayQuery,
    accelStructure,
    gl_RayFlagsTerminateOnFirstHitEXT,
    cullMask,
    WorldPos,
    minDistance,
    DirectionToLight,
    LightDistance);

    // Traverse the query -- do once for the first hit
    while(rayQueryProceedEXT(rayQuery))
    {
        // Hit something! Logic can be added here depending on the type of intersection
    }

    // Get the last intersection information
    if(rayQueryGetIntersectionTypeEXT(rayQuery, true) != gl_RayQueryCommittedIntersectionNoneEXT)
    {
         // Got an intersection -- this pixel is occluded, so retrieve distance
         float intersectionDistance = rayQueryGetIntersectionTEXT(rayQuery, true);

         // ...
    }
```

### Optimization [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#optimization "Click to copy section url")

#### General Considerations [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#general-considerations "Click to copy section url")

##### Instruction cache

Good instruction cache practices are even more important than usual for ray tracing shaders – remove dead code, factor away non-uniform branches and looping and shrink each shader’s total instruction size so it fits [target devices’ instruction cache](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-instruction-count).

##### 16-bit Precision

[Half-precision](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-maximize-half-precision) is, as ever, an easy performance win that often involves few to no additional artifacts. The Vulkan API supports this with [VK\_KHR\_shader\_float16\_int8.](https://registry.khronos.org/vulkan/specs/1.3-extensions/man/html/VK_KHR_shader_float16_int8.html)

##### Culling

Simplifying acceleration structures speeds raytracing. Aggressively cull your geometry as much as your content allows – frustum culling, portal culling, level-of-detail, and other techniques may apply.

##### Acceleration structures

**Building on the GPU**

* * *

Acceleration structures are typically built fastest on the GPU with [vkCmdBuildAccelerationStructuresKHR](https://registry.khronos.org/vulkan/specs/latest/man/html/vkCmdBuildAccelerationStructuresKHR.html), [vkCmdBuildAccelerationStructuresIndirectKHR](https://registry.khronos.org/vulkan/specs/latest/man/html/vkCmdBuildAccelerationStructuresIndirectKHR.html), [vkCmdCopyAccelerationStructureToMemoryKHR](https://registry.khronos.org/vulkan/specs/latest/man/html/vkCmdCopyAccelerationStructureToMemoryKHR.html) and [vkCmdCopyMemoryToAccelerationStructureKHR](https://registry.khronos.org/vulkan/specs/latest/man/html/vkCmdCopyMemoryToAccelerationStructureKHR.html) – as opposed to API calls that execute on the CPU.

Pass the [optimal number of acceleration structures](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#raytracing-acceleration-structure-number-single-invocation) when possible.

Prefer concurrently operating on acceleration structures with [LPAC](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#lpac) (rather than using any CPU approaches such as VkDeferredOperationKHR) whenever concurrent processing of acceleration structures is desired.

**Deformable Raytraced Meshes: Refitting vs Rebuilding**

* * *

Try to cache as much of your acceleration structure as long as you can, amortizing any refitting (with [VK\_BUILD\_ACCELERATION\_STRUCTURE\_ALLOW\_UPDATE\_BIT\_KHR](https://registry.khronos.org/vulkan/specs/latest/man/html/VkBuildAccelerationStructureFlagBitsKHR.html)) and/or rebuilds (with [VK\_BUILD\_ACCELERATION\_STRUCTURE\_ALLOW\_BUILD\_BIT\_KHR](https://registry.khronos.org/vulkan/specs/latest/man/html/VkBuildAccelerationStructureFlagBitsKHR.html)) over multiple frames to stay within your frame budget.

Generally, refitting will be more efficient than rebuilding when a mesh hasn’t deformed much from the mesh’s original geometry (at the moment its acceleration structure was first built). Once the mesh’s deformation causes the originally-built acceleration structure to poorly fit the mesh’s current geometry, a rebuild will be more efficient than a refit. Of course this is highly content-dependent.

#### Prefer ray queries to ray pipelines [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#prefer-ray-queries-to-ray-pipelines "Click to copy section url")

A8x and higher supports [ray tracing pipelines](https://registry.khronos.org/vulkan/specs/latest/man/html/VK_KHR_ray_tracing_pipeline.html). However, when possible, we recommend using only [ray queries](https://registry.khronos.org/vulkan/specs/latest/man/html/VK_KHR_ray_query.html), as they are often comparatively more performant. But when ray queries alone are not expressive enough – or when porting an existing raytracing codebase to Adreno – ray pipeline support is ready to go, and performs well for many types of content.

##### Ray Queries

#### Minimize calls to rayQueryProceed() [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#minimize-calls-to-rayqueryproceed "Click to copy section url")

Our Vulkan SPIR-V compiler currently does not support function calls – therefore all calls to rayQueryProceed() are inlined. For example, if the application wraps calls to rayQueryProceed() in a ClosestHitTrace() function, and then calls ClosestHitTrace() in 10 different places in the code, the compiler could generate 10 copies of the traversal loop. The traversal loop might be 300 instructions, so this can easily result in shaders that don’t fit the [instruction cache and consequently perform poorly](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-instruction-count).

We’ve found that typically a couple of calls to proceed() doesn’t hurt performance. However, for larger numbers of traversal loops it becomes more challenging for our compiler to achieve reasonable register allocation, which results in [GPR spilling](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-gpr-minimization) and other performance degradations.

#### Reuse one minimally-sized ray query object [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#reuse-one-minimally-sized-ray-query-object "Click to copy section url")

Reuse the single ray query object as needed. A ray query object costs enough [GPRs that the concurrent wave count for the shader](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-gpr-minimization) may be reduced. Thus make every effort to avoid more then one ray query object, reusing that one object across different calls to rayQueryProceed(). This reuse should be possible unless recursion is used – which itself is usually avoidable. Minimize the size of the ray query object.

#### Access ray query data through intrinsics [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#access-ray-query-data-through-intrinsics "Click to copy section url")

Avoid copying data from a ray query into large, custom data structures – this will increase [GPR usage](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-gpr-minimization). Instead, use intrinsics to access the query object’s data.

#### Avoid proceed() calls in loops for non-opaque traversal that “accept first fit” [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#avoid-proceed-calls-in-loops-for-non-opaque-traversal-that-accept-first-fit "Click to copy section url")

When using gl\_RayFlagsTerminateOnFirstHitEXT or gl\_RayFlagsCullOpaqueEXT, there is no need to call rayQueryProceedEXT in a while loop – this easy simplification helps the compiler generate code with [fewer branches](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-shader-control-flow).

For example:

```typescript
rayQueryEXT rayQuery;
rayQueryInitializeEXT(rayQuery, rayTraceAS, gl_RayFlagsTerminateOnFirstHitEXT | gl_RayFlagsCullOpaqueEXT, cullMask, WorldPos, minDistance, DirectionToLight, LightDistance);

// Traverse the query. No need for a while(), since we want first hit or
// non-opaque intersections only
rayQueryProceedEXT(rayQuery));

// Determine if the shadow query collided
if(rayQueryGetIntersectionTypeEXT(rayQuery, true) != gl_RayQueryCommittedIntersectionNoneEXT)
{
    // Got an intersection == Shadow, do something
}
```

#### Use the optimal subgroup size [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#use-the-optimal-subgroup-size "Click to copy section url")

Avoid performance bottlenecks by setting the [device-specific optimal subgroup size](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#ray-query-optimal-subgroup-size).

##### Ray Pipelines

Minimize the size of all user-defined datastructures: ray payload, hit attributes, callable data and pipeline stack size.

[Prefer ray queries](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-preferrayqueriestoraypipelines) instead of ray pipelines when possible.

## 2D operation hardware acceleration [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#2d-operation-hardware-acceleration "Click to copy section url")

Adreno hardware accelerates common 2D operations:

- blits – with Vulkan, use vkCmdBlitImage()

- surface clears

- [Android-phone pre-rotation on Vulkan](https://docs.vulkan.org/samples/latest/samples/performance/surface_rotation/README.html) (recent OpenGL ES drivers do this automatically)

- rotation

- convolution kernels – for example, [with Vulkan’s VK\_QCOM\_Image\_Processing](https://github.com/quic/adreno-gpu-vulkan-code-sample-framework/tree/main/samples/BloomImageProcessing)


Graphics APIs like Vulkan and OpenGL ES often map to Adreno’s specialized, high-performance hardware.

## [Queries](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html\#queries-device-specific) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#queries "Click to copy section url")

### [Occlusion queries performance](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html\#occlusion-queries-device-specific) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#occlusion-queries-performance "Click to copy section url")

The [number of queries and their frame-latency](https://docs.qualcomm.com/doc/80-78185-2/topic/spec_sheets.html#occlusion-queries-device-specific) should be respected to maximize performance.

The performance of occlusion queries is further affected by the number of bins – the higher the [bin count](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-bin-minimization) the more expensive the queries.

Run occlusion queries in [direct mode](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-flex-render-best-practices) whenever possible. One way to ensure this occurs is to issue all the queries for a frame in one batch after a flush; for example: Render Opaque -> Render Translucent -> Flush -> Render Queries -> Switch FBO.

If the driver sees that only queries have been issued to the surface then it switches to [direct mode](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-flex-render-best-practices).

Note

The overhead of queries will show up as a higher “% CP Busy” metric in [Snapdragon Profiler](https://docs.qualcomm.com/doc/80-78185-2/topic/sdp.html#sdp).

We’ve seen cases where issuing many queries to a binned surface causes a CP overhead increase of 20-40% – and this overhead drops to 4-6% in direct mode.

### Timer Query Accuracy [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#timer-query-accuracy "Click to copy section url")

Timer queries should always be issued within a renderpass to maximize accuracy.

Timer queries are calculated over the entire set of binned tiles when in binning mode. For example, let’s assume that we have 50 draw calls and a [render target that requires 8 tiles to render.](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-bin-minimization) Let’s also assume we want to measure draw call 10 and instrument it with timer queries.

The entire command stream of 50 draws will be captured and run through the binning process to generate the [visibility streams](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#visibility-streams). During the rendering pass, the draw calls will be rendered according to the [visibility stream](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#visibility-streams) of each tile. Even if the geometry for draw call 10 only contributes to one tile, it will incur a small overhead for each tile (while processing the [visibility stream](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#visibility-streams)). This overhead and the actual rendering time will be accumulated and presented in the resulting timer query.

Note

The overhead mentioned above is small (2-5µs) but can add up if the draw call count is high and draws are present in many tiles. Starting with A5x, GPU optimizations to the [visibility stream](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#visibility-streams) have been added to reduce this overhead by “trimming” the end of the stream of draw calls that do not contribute to the tile. This optimization can be nullified if something like a full screen pass is issued as the last draw call to a render target.

## [Qualcomm True HDR setup](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#qualcomm-hdr) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#qualcomm-true-hdr-setup "Click to copy section url")

To enable [Qualcomm True HDR](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#qualcomm-hdr) in OpenGL ES, the following extensions must be supported:

- EGL\_EXT\_gl\_colorspace\_display\_p3

- EGL\_EXT\_gl\_colorspace\_bt2020\_pq

- EGL\_EXT\_surface\_SMPTE2086\_metadata


Note

Vulkan Swapchain/WSI for Android only supports VK\_COLOR\_SPACE\_DISPLAY\_P3\_NONLINEAR\_EXT. For additional information on how to enable this for Vulkan, check out the [Enhancing graphics with wide color content](https://developer.android.com/training/wide-color-gamut) guide from the Android Developers Documentation.

### Set EGLSurface format [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#set-eglsurface-format "Click to copy section url")

Set the EGLSurface format to R10G10B10A2:

```python
EGLConfig EGLConfigList [1]; int ConfigAttributes [] = {
    EGL_RED_SIZE,10
    EGL_GREEN_SIZE,10
    EGL_BLUE_SIZE,10
    EGL_ALPHA_SIZE,2
    EGL_COLOR_COMPONENT_TYPE_EXT,
EGL_COLOR_COMPONENT_TYPE_FIXED_EXT, EGL_NONE};

eglChooseConfig (eglDisplay,ConfigAttributes,EGLConfigList,1, eglNumConfigs);
```

### Set color space [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#set-color-space "Click to copy section url")

Set the color space of eglWindowSurface to EGL\_GL\_COLORSPACE\_BT2020\_PQ\_EXT.

```undefined
EGLint attribs[] = {EGL_GL_COLORSPACE_KHR,EGL_GL_COLORSPACE_BT2020_PQ_EXT,EGL_NONE };
EGLSurface eglSurface=eglCreateWidowSurface(eglDisplay,eglConfigParam, InWindow, attribs);
```

### Set metadata [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#set-metadata "Click to copy section url")

Set the metadata attributes of eglSurface.

```cpp
EGLint SurfaceAttribs [] = {
EGL_SMPTE2086_DISPLAY_PRIMARY_RX_EXT,       EGL_SMPTE2086_DISPLAY_PRIMARY_RY_EXT,
    EGL_SMPTE2086_DISPLAY_PRIMARY_GX_EXT,
    EGL_SMPTE2086_DISPLAY_PRIMARY_GY_EXT,
    EGL_SMPTE2086_DISPLAY_PRIMARY_BX_EXT,
    EGL_SMPTE2086_DISPLAY_PRIMARY_BY_EXT,
    EGL_SMPTE2086_WHITE_POINT_X_EXT,
    EGL_SMPTE2086_WHITE_POINT_Y_EXT,
    EGL_SMPTE2086_MAX_LUMINANCE_EXT,
    EGL_SMPTE2086_MIN_LUMINANCE_EXT
};
static const DisplayChromacities DisplayChromacityList [] = { {{0.70800f, 0.29200f, 0.17000f, 0.79700f, 0.13100f, 0.04600f, 0.31270f, 0.32900f}}, // DG_Rec2020 };
for (uint32_t i = 0; i < 8; i++)
{
    eglSurfaceAttrib(PImplData->eglDisplay,eglSurface, SurfaceAttribs[i],EGLint(DisplayChromacityList[0].ChromaVals[i]* EGL_METADATA_SCALING_EXT));
}
```

### Get the luminance of display on Android [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#get-the-luminance-of-display-on-android "Click to copy section url")

See: [https://developer.android.com/reference/android/view/Display.HdrCapabilities.html#getDesired](https://developer.android.com/reference/android/view/Display.HdrCapabilities.html#getDesired)

…for methods like:

- MaxAverageLuminance

- MaxLuminance

- MinLuminance


## [Variable Rate Shading (VRS)](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html\#vrs) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#variable-rate-shading-vrs "Click to copy section url")

Fewer pixels shaded means fewer rays queried – often with few to no additional artifacts. Use [VRS](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#vrs) as aggressively as your content allows.

VulkanOpenGL ES

[VRS](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#vrs) is exposed through the VK\_KHR\_fragment\_shading\_rate extension. VK\_KHR\_fragment\_shading\_rate takes a VkExtent2D argument where developers specify the width and height of the desired fragment size.

Note that [VRS](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#vrs) interoperates well with [foveated rendering](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html#mobile-foveated-rendering) – you can seamlessly use them simultaneously.

## XR/VR/AR (Extended Reality/Virtual Reality/Augmented Reality) [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#xr-vr-ar-extended-reality-virtual-reality-augmented-reality "Click to copy section url")

### Stereographic Rendering [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#stereographic-rendering "Click to copy section url")

The following API calls supports efficient stereographic rendering – the driver captures issued commands for one eye and replays them for the other. This saves CPU time (but has no impact on the GPU).

VulkanOpenGL ES

VK\_KHR\_multiview

### Foveated Rendering [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#foveated-rendering "Click to copy section url")

Use [foveated](https://www.qualcomm.com/news/onq/2021/07/evolution-high-performance-foveated-rendering-adreno) [rendering](https://www.qualcomm.com/developer/blog/2022/08/improving-foveated-rendering-fragment-density-map-offset-extension-vulkan) – and note that it interoperates well with [VRS](https://docs.qualcomm.com/doc/80-78185-2/topic/overview.html#vrs) ; you can seamlessly use them simultaneously.

## Querying the driver version to implement version-specific workarounds [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#querying-the-driver-version-to-implement-version-specific-workarounds "Click to copy section url")

Despite our best efforts, sometimes drivers ship with bugs.

When a future driver fixes some bugs, you may want to implement a workaround for certain versions of a driver and not others. Here’s how:

### Vulkan [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#vulkan "Click to copy section url")

“driverVersion” can be queried from VkPhysicalDeviceProperties – it returns the complete major/minor/patch number of the driver version.

For Adreno, the 32-bit number of the driverVersion is encoded as major-minor-patch. The first 10 bits is the major version, the second 10 bits is the minor version and the remaining 12 bits is for the patch version.

The major number is usually fixed, while the minor number changes with each release. Patches are the variations of a minor release. We primarily use the minor number to identify different driver versions, while the patch number is generally used to identify workarounds and fixes for a given driver version.

Sample code:

```cpp
#define VK_VERSION_MAJOR(version) ((uint32_t)(version) >> 22)

#define VK_VERSION_MINOR(version) (((uint32_t)(version) >> 12) & 0x3FFU)

#define VK_VERSION_PATCH(version) ((uint32_t)(version) & 0xFFFU)

// Workarounds for Adreno driver 676
if (VK_VERSION_MINOR(version) == 676)
{
   // Guard for known Adreno issue on patch < 17 and driver 676
   if (VK_VERSION_PATCH(version) < 17)
   {
      doWorkaround();
   }
   // After patch 17 we know the issue was addressed by the vendor
   else
   {
      doNormalFlow();
   }
}
```

### adb [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#adb "Click to copy section url")

To check the driver version, run the command:

```undefined
adb shell dumpsys SurfaceFlinger | grep GLES
```

Output is of the form:

```typescript
GLES: Qualcomm, Adreno (TM) 740, OpenGL ES 3.2 V\@0676.0 (GIT\@6f08ddb, I5e1ee3b043, 1669189803) (Date:11/23/22)
```

Given: V@0676 as above, 676 is the driver promotion/minor number.

Shader stats (like for [Snapdragon Profiler](https://docs.qualcomm.com/doc/80-78185-2/topic/sdp.html#sdp)) for vulkan needs driver support: 636 promotion/minor number and above qualifies.

## Adreno APIs [Click to copy section url](https://docs.qualcomm.com/doc/80-78185-2/topic/mobile_best_practices.html\#adreno-apis "Click to copy section url")

Adreno GPUs support industry-standard APIs including:

- OpenGL ES 1.x (fixed function pipeline)

- OpenGL ES 2.0 (programmable shader pipeline)

- OpenGL ES 3.0

- OpenGL ES 3.1 + AEP

- OpenGL ES 3.2

- EGL

- Vulkan 1.0

- Vulkan 1.1

- OpenCL 1.1e

- OpenCL 2.0 Full Profile

- DirectX 11 FL 9.3

- DirectX 12 FL 12


Last Published: Mar 03, 2026

Previous

Occlusion queries

Next

Texture Compression Examples

May contain U.S. and international export controlled information

Scroll To Top