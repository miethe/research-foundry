* * *

* * *

[Skip Navigation](https://developer.apple.com/documentation/realitykit/lowlevelmesh#app-main)

- [RealityKit](https://developer.apple.com/documentation/realitykit)
- LowLevelMesh

Class

# LowLevelMesh

A container for vertex data that you can use to create and update meshes using your own format.

iOS 18.0+iPadOS 18.0+Mac Catalyst 18.0+macOS 15.0+tvOS 26.0+visionOS 2.0+

```
@MainActor
class LowLevelMesh
```

## [Mentioned in](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#mentions)

[Creating a plane with low-level mesh](https://developer.apple.com/documentation/realitykit/creating-a-plane-with-low-level-mesh)

## [Overview](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#overview)

Use `LowLevelMesh` when you want to bring your own vertex format to RealityKit or update your data frequently. To update your data in `LowLevelMesh`, you can either use Swift for CPU processing, or Metal Compute Shaders for GPU processing.

Express your vertex by creating a [`LowLevelMesh.Descriptor`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/descriptor-swift.struct) that describes your layout, along with the required index and vertex capacities. This descriptor is similar to [`MTLVertexDescriptor`](https://developer.apple.com/documentation/Metal/MTLVertexDescriptor), with additional semantics that make the data available in your shaders.

To use `LowLevelMesh`, first define your own vertex structure, either in a Metal header or using a Swift structure:

```
struct MyVertex {
    var position: SIMD3<Float> = .zero
    var color: UInt32 = .zero
}
```

Next, describe your structure to `LowLevelMesh` by creating a list of vertex attributes and a vertex layout. This description informs `LowLevelMesh` how to represent the vertex data in memory:

```
extension MyVertex {
    static var vertexAttributes: [LowLevelMesh.Attribute] = [\
        .init(semantic: .position, format: .float3, offset: MemoryLayout<Self>.offset(of: \.position)!),\
        .init(semantic: .color, format: .uchar4Normalized_bgra, offset: MemoryLayout<Self>.offset(of: \.color)!)\
    ]

    static var vertexLayouts: [LowLevelMesh.Layout] = [\
        .init(bufferIndex: 0, bufferStride: MemoryLayout<Self>.stride)\
    ]

    static var descriptor: LowLevelMesh.Descriptor {
        var desc = LowLevelMesh.Descriptor()
        desc.vertexAttributes = MyVertex.vertexAttributes
        desc.vertexLayouts = MyVertex.vertexLayouts
        desc.indexType = .uint32
        return desc
    }
}
```

Create a [`LowLevelMesh.Descriptor`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/descriptor-swift.struct) and `LowLevelMesh`, and assign your mesh data and parts:

```
func triangleMesh() throws -> LowLevelMesh {
    var desc = MyVertex.descriptor
    desc.vertexCapacity = 3
    desc.indexCapacity = 3

    let mesh = try LowLevelMesh(descriptor: desc)

    mesh.withUnsafeMutableBytes(bufferIndex: 0) { rawBytes in
        let vertices = rawBytes.bindMemory(to: MyVertex.self)
        vertices[0] = MyVertex(position: [-1, -1, 0], color: 0xFF00FF00)
        vertices[1] = MyVertex(position: [ 1, -1, 0], color: 0xFFFF0000)
        vertices[2] = MyVertex(position: [ 0,  1, 0], color: 0xFF0000FF)
    }

    mesh.withUnsafeMutableIndices { rawIndices in
        let indices = rawIndices.bindMemory(to: UInt32.self)
        indices[0] = 0
        indices[1] = 1
        indices[2] = 2
    }

    let meshBounds = BoundingBox(min: [-1, -1, 0], max: [1, 1, 0])
    mesh.parts.replaceAll([\
        LowLevelMesh.Part(\
            indexCount: 3,\
            topology: .triangle,\
            bounds: meshBounds\
        )\
    ])

    return mesh
}
```

To finish, create a [`MeshResource`](https://developer.apple.com/documentation/realitykit/meshresource) from the `LowLevelMesh`, and add it to a [`ModelComponent`](https://developer.apple.com/documentation/realitykit/modelcomponent). You can then add this model to any [`Entity`](https://developer.apple.com/documentation/realitykit/entity) in your scene:

```
func triangleEntity() throws -> Entity {
    let lowLevelMesh = try triangleMesh()
    let resource = try MeshResource(from: lowLevelMesh)

    let modelComponent = ModelComponent(mesh: resource, materials: [UnlitMaterial()])

    let entity = Entity()
    entity.name = "Triangle"
    entity.components.set(modelComponent)
    entity.scale *= 0.1
    return entity
}
```

The low-level mesh creates a triangular shape in your RealityKit scene:

![A screenshot of an isosceles triangle, floating in a kitchen scene. The triangle appears light gray in color.](https://docs-assets.developer.apple.com/published/53f5fd30d54e5aaa8c9b02f628ac1f48/lowlevelmesh-triangle-unlit.jpg)

The [`MeshResource`](https://developer.apple.com/documentation/realitykit/meshresource) retains a reference to the `LowLevelMesh`, reflecting any changes when the renderer updates.

## [Topics](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#topics)

### [Creating a low-level mesh](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#Creating-a-low-level-mesh)

[`init(descriptor: LowLevelMesh.Descriptor) throws`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/init(descriptor:))

Constructs a low-level mesh from a descriptor.

### [Describing a low-level mesh](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#Describing-a-low-level-mesh)

[`let descriptor: LowLevelMesh.Descriptor`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/descriptor-swift.property)

The definition of the structure of this low-level mesh.

[`var parts: LowLevelMesh.PartsCollection`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/parts)

A mutable collection of parts.

[`var indexCapacity: Int`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/indexcapacity)

The capacity of the index buffer, measured in indices.

[`var vertexCapacity: Int`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/vertexcapacity)

The capacity of the vertex buffer, measured in vertices.

### [Accessing mesh data on the CPU with Swift](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#Accessing-mesh-data-on-the-CPU-with-Swift)

[`func withUnsafeBytes(bufferIndex: Int, (UnsafeRawBufferPointer) -> Void)`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/withunsafebytes(bufferindex:_:))

Reads a Metal vertex buffer synchronously on the CPU.

[`func withUnsafeMutableBytes(bufferIndex: Int, (UnsafeMutableRawBufferPointer) -> Void)`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/withunsafemutablebytes(bufferindex:_:))

Updates a Metal vertex buffer synchronously on the CPU.

[`func withUnsafeIndices((UnsafeRawBufferPointer) -> Void)`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/withunsafeindices(_:))

Reads the index buffer synchronously on the CPU.

[`func withUnsafeMutableIndices((UnsafeMutableRawBufferPointer) -> Void)`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/withunsafemutableindices(_:))

Updates the index buffer synchronously on the CPU.

[`func replaceUnsafeMutableBytes(bufferIndex: Int, (UnsafeMutableRawBufferPointer) -> Void)`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/replaceunsafemutablebytes(bufferindex:_:))

Replaces a Metal vertex buffer synchronously on the CPU.

[`func replaceUnsafeMutableIndices((UnsafeMutableRawBufferPointer) -> Void)`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/replaceunsafemutableindices(_:))

Replaces the index buffer synchronously on the CPU.

### [Accessing mesh data on the GPU with Metal](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#Accessing-mesh-data-on-the-GPU-with-Metal)

[`func read(bufferIndex: Int, using: any MTLCommandBuffer) -> any MTLBuffer`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/read(bufferindex:using:))

Retrieves a Metal vertex buffer at the specified index, for GPU reading.

[`func readIndices(using: any MTLCommandBuffer) -> any MTLBuffer`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/readindices(using:))

Retrieves the Metal index buffer for GPU reading.

[`func replace(bufferIndex: Int, using: any MTLCommandBuffer) -> any MTLBuffer`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/replace(bufferindex:using:))

Retrieves a Metal vertex buffer you can use to replace the contents of the specified buffer on the GPU using Metal.

[`func replaceIndices(using: any MTLCommandBuffer) -> any MTLBuffer`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/replaceindices(using:))

Retrieves a Metal index buffer that you can use to replace the indices of this low-level mesh.

### [Structures](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#Structures)

[`struct Attribute`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/attribute)

An object that determines how to store vertex attribute data in memory and map it to RealityKit shader attributes.

[`struct Descriptor`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/descriptor-swift.struct)

An object that describes the data format and layout of the buffers in a low-level mesh.

[`struct Layout`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/layout)

An object that describes a set of attributes that share a buffer index, offset, and stride.

[`struct Part`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/part)

An object that describes a range of primitives to display, and their material index.

[`struct PartsCollection`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/partscollection)

An object that holds a mutable collection low-level mesh parts.

### [Enumerations](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#Enumerations)

[`enum VertexSemantic`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/vertexsemantic)

Designates the intended usage of a vertex attribute.

## [Relationships](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#relationships)

### [Conforms To](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#conforms-to)

- [`Sendable`](https://developer.apple.com/documentation/Swift/Sendable)
- [`SendableMetatype`](https://developer.apple.com/documentation/Swift/SendableMetatype)

## [See Also](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#see-also)

### [Updatable meshes](https://developer.apple.com/documentation/realitykit/lowlevelmesh\#Updatable-meshes)

[Integrating virtual objects with your environment](https://developer.apple.com/documentation/realitykit/integrating-virtual-objects-with-your-environment)

Create an immersive game using native anchor support, environmental blending, model manipulation, and mesh instance duplication.

[Creating a spatial drawing app with RealityKit](https://developer.apple.com/documentation/realitykit/creating-a-spatial-drawing-app-with-realitykit)

Use low-level mesh and texture APIs to achieve fast updates to a person’s brush strokes by integrating RealityKit with ARKit and SwiftUI.

[Creating a plane with low-level mesh](https://developer.apple.com/documentation/realitykit/creating-a-plane-with-low-level-mesh)

Create a low-level mesh and set its vertex positions and normals to form a plane.

[`struct Descriptor`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/descriptor-swift.struct)

An object that describes the data format and layout of the buffers in a low-level mesh.

[`struct Part`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/part)

An object that describes a range of primitives to display, and their material index.

[`struct Layout`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/layout)

An object that describes a set of attributes that share a buffer index, offset, and stride.

[`struct Attribute`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/attribute)

An object that determines how to store vertex attribute data in memory and map it to RealityKit shader attributes.

[`enum VertexSemantic`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/vertexsemantic)

Designates the intended usage of a vertex attribute.

[`struct PartsCollection`](https://developer.apple.com/documentation/realitykit/lowlevelmesh/partscollection)

An object that holds a mutable collection low-level mesh parts.

[`class LowLevelBuffer`](https://developer.apple.com/documentation/realitykit/lowlevelbuffer)

[`class LowLevelInstanceData`](https://developer.apple.com/documentation/realitykit/lowlevelinstancedata)

Current page is LowLevelMesh