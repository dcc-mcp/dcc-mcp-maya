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

Use `generate_procedural_house_showcase` when the result must be presented or
recorded. It stages all four styles with consecutive seeds, materials, a camera
orbit, and reveal animation. Its result includes ready-to-pass arguments for
`maya-render` → `capture_playblast_sequence`.

## Recommended flow

1. `generate_procedural_house_showcase` for a staged four-style preview, or
   `generate_procedural_house` for one ready-to-view house graph.
2. Chain the showcase result to `maya-render` → `capture_playblast_sequence`
   when image frames are required.
3. `list_bifrost_graphs` to inspect the scene.
4. `create_bifrost_graph` when a new graph container is needed.
5. `add_bifrost_node` with a fully-qualified type such as
   `Modeling::Primitive::create_mesh_cube`.
6. `create_bifrost_port` when a dynamic port is required, such as inputs on
   `Core::Array::build_array` or an Object port on the graph `output` node.
7. `set_bifrost_property` for unconnected input defaults.
8. `connect_bifrost_ports` using paths such as `.cube.cube_mesh` and
   `.output.geometry`.

For headless scene generation, run
`mayapy examples/standalone/build_procedural_house_showcase.py --output house-showcase.ma`.
The standalone script and GUI tool share the same pure staging contract and
Bifrost builder; only viewport capture requires an interactive model panel.

Use an explicit `Core::Array::build_array` node before ports that require
`array<Object>`; Bifrost does not implicitly promote an `Object` connection to
an object array.
