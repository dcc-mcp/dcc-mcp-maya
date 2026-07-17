---
name: maya-bifrost
description: |-
  Authoring stage - typed Bifrost procedural modeling and graph construction in Maya.
  Use to generate reproducible multi-style houses, create graph shapes or boards,
  add Bifrost nodes, set input defaults, and connect ports.
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
      set Bifrost port value, procedural modeling graph, random house,
      procedural house generator, cottage, cabin, modern house, townhouse
    tools: tools.yaml
    groups: groups.yaml
---
# maya-bifrost (Authoring stage)

Typed wrappers around Maya's supported Bifrost/VNN commands. The skill loads
`mayaVnnPlugin` and `bifrostGraph` on demand, then keeps graph changes on Maya's
main thread.

For a complete result in one call, use `generate_procedural_house`. Its `seed`
is reproducible across standalone mayapy and interactive Maya, while `style`
can select `cabin`, `cottage`, `modern`, `townhouse`, or choose randomly.

## Recommended flow

1. `generate_procedural_house` for a ready-to-view, seed-driven house graph.
2. `list_bifrost_graphs` to inspect the scene.
3. `create_bifrost_graph` when a new graph container is needed.
4. `add_bifrost_node` with a fully-qualified type such as
   `Modeling::Primitive::create_mesh_cube`.
5. `create_bifrost_port` when a dynamic port is required, such as inputs on
   `Core::Array::build_array` or an Object port on the graph `output` node.
6. `set_bifrost_property` for unconnected input defaults.
7. `connect_bifrost_ports` using paths such as `.cube.cube_mesh` and
   `.output.geometry`.

Use an explicit `Core::Array::build_array` node before ports that require
`array<Object>`; Bifrost does not implicitly promote an `Object` connection to
an object array.
