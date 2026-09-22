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
    version: 1.1.0
    tags:
    - maya
    - bifrost
    - vnn
    - procedural-modeling
    - graph-authoring
    - simulation
    - cache
    search-hint: |-
      Bifrost graph, bifrostGraphShape, bifrostBoard, VNN, vnnCompound,
      create Bifrost graph, add Bifrost node, connect Bifrost ports,
      set Bifrost port value, procedural modeling graph, Bifrost simulation,
      cache Bifrost, Bifrost to polygons, bake Bifrost mesh, aero, liquid, foam
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

## Simulation and output

1. `cache_bifrost_simulation` once the graph evaluates the way you want —
   scrubbing an uncached Bifrost graph is slow and farm renders need the cache.
2. `convert_bifrost_to_polygons` to bake the evaluated output into a real
   `mesh` node that `maya-mesh-ops`, `maya-uv-ops` and `maya-geometry` can use.

## Scripts

- `add_bifrost_node` - Add a typed Bifrost node to a graph
- `cache_bifrost_simulation` - Write and attach a geometry cache for a graph's output
- `connect_bifrost_ports` - Connect or disconnect two ports in a Bifrost graph
- `convert_bifrost_to_polygons` - Convert a Bifrost output into a Maya polygon mesh
- `create_bifrost_graph` - Create an empty Bifrost graph container
- `create_bifrost_port` - Create a dynamic input or output port on a node
- `list_bifrost_graphs` - Inspect the Bifrost graphs in the scene
- `set_bifrost_property` - Set an unconnected Bifrost node port's default value
