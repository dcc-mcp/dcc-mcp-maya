---
name: maya-bifrost
description: |-
  Authoring stage - typed Bifrost procedural modeling and graph construction in Maya.
  Use to create graph shapes or boards, add Bifrost nodes, set input defaults,
  and connect ports.
  Not for ordinary Maya DG nodes (maya-node-graph), polygon edits
  (maya-mesh-ops), or arbitrary Python/MEL (maya-scripting).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: authoring
    version: 1.0.0
    tags:
    - maya
    - bifrost
    - vnn
    - procedural-modeling
    - graph-authoring
    search-hint: |-
      Bifrost graph, bifrostGraphShape, bifrostBoard, VNN, vnnCompound,
      create Bifrost graph, add Bifrost node, connect Bifrost ports,
      set Bifrost port value, procedural modeling graph
    tools: tools.yaml
    groups: groups.yaml
---
# maya-bifrost (Authoring stage)

Typed wrappers around Maya's supported Bifrost/VNN commands. The skill loads
`mayaVnnPlugin` and `bifrostGraph` on demand, then keeps graph changes on Maya's
main thread.

## Recommended flow

1. `list_bifrost_graphs` to inspect the scene.
2. `create_bifrost_graph` when a new graph container is needed.
3. `add_bifrost_node` with a fully-qualified type such as
   `Modeling::Primitive::create_mesh_cube`.
4. `create_bifrost_port` when a dynamic port is required, such as inputs on
   `Core::Array::build_array` or an Object port on the graph `output` node.
5. `set_bifrost_property` for unconnected input defaults.
6. `connect_bifrost_ports` using paths such as `.cube.cube_mesh` and
   `.output.geometry`.

Use an explicit `Core::Array::build_array` node before ports that require
`array<Object>`; Bifrost does not implicitly promote an `Object` connection to
an object array.
