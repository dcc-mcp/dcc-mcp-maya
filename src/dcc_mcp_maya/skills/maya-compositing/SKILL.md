---
name: maya-compositing
description: |-
  Pipeline stage - build node-based compositing networks inside Maya: read
  rendered imagery from disk, stack it in a layeredTexture with per-layer
  blend modes and opacity, merge passes with blend/over/add/multiply, and
  wire colour and maths utility nodes. Use to combine a beauty pass with
  AOVs, mattes or keyed elements for in-scene review or render. Not for
  deciding where renders land (render_setup.plan_comp_outputs), not for
  render layers and AOV setup (maya-render-setup), and not for rendering
  frames (maya-render / maya-render-farm).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: pipeline
    version: 1.0.0
    tags:
    - maya
    - compositing
    - comp
    - layered-texture
    - blend-mode
    - aov
    - merge
    - keyer
    - utility-node
    search-hint: |-
      compositing, comp network, comp tree, layered texture, layeredTexture,
      layer stack, blend mode, over, add, multiply, subtract, difference,
      layer opacity, isVisible, merge passes, combine AOVs, beauty plus AOV,
      keyer, luminance key, reverse, multiplyDivide, divide, clamp, setRange,
      image reader, file node, fileTextureName, frame extension, read EXR
    tools: tools.yaml
    groups: groups.yaml
---
# maya-compositing (Pipeline stage)

Builds the shading/utility node network that combines **already-rendered**
imagery inside Maya, so a comp can be reviewed or rendered without leaving the
scene. It is the companion to `render_setup.plan_comp_outputs`, which decides
where those images land on disk.

## Typical flow

1. `create_image_reader` — one per image sequence. Set
   `use_frame_extension=True` for `name.####.exr` sequences, and `frame_offset`
   when the render starts at a non-zero frame.
2. `create_layer_stack` — an empty `layeredTexture` to stack into.
3. `add_comp_layer` — connect each reader, choosing `blend_mode` and `opacity`.
4. `list_comp_layers` — verify order, modes and opacity before rendering.
5. `merge_comp_layers` — shortcut for two sources: `blend` gives a uniform mix
   via `blender`, the other operations stack with the matching blend mode.
6. `create_comp_node` + `connect_comp_nodes` — insert `reverse`,
   `multiplyDivide`, `luminance`, `clamp` or `setRange` for keys and grades.

## Verified Maya behaviours

Three things are easy to get wrong and invisible under a mock (all verified on
Maya 2025):

- `layeredTexture.inputs` reports `size == 0` via `getAttr(s=True)` before the
  first connection, and `listConnections(..., plugs=True)` on the array returns
  the **source** plugs (`f1.outColor`), not the destination elements. Neither
  reveals an index, so the layer index comes from probing each element - and
  that also lets a removed layer's slot be reused.
- `grade` and `colorCorrect` exist as node types but `createNode` returns an
  `unknown` node in a batch session, so they are not offered.
- `file.imageName` does not exist; only `fileTextureName` is settable.

Input plugs differ per node type: `multiplyDivide` uses `input1`/`input2`,
`plusMinusAverage` uses `input3D`, and `reverse`/`clamp` use a plain `input`.

## Scope

This skill builds comp networks. It does not render or plan paths:

- where renders land → `render_setup.plan_comp_outputs` (`maya-render-setup`)
- render layers, AOVs → `maya-render-setup`
- rendering frames → `maya-render` / `maya-render-farm`

## Scripts

- `add_comp_layer` - Connect a source into the next free layer of a comp stack
- `connect_comp_nodes` - Wire two comp nodes together
- `create_comp_node` - Create a reverse / multiplyDivide / luminance / clamp / setRange node
- `create_image_reader` - Create a file node that reads rendered imagery from disk
- `create_layer_stack` - Create an empty layeredTexture stack to composite layers into
- `list_comp_layers` - List the layers currently connected into a comp stack
- `merge_comp_layers` - Combine two or more sources into a single comp output
- `remove_comp_layer` - Disconnect one layer from a comp stack, keeping its source node
