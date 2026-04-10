---
name: maya-blend-shape-utils
description: "Maya blend shape utilities — create, inspect, and drive blend shape deformers"
dcc: maya
version: "1.0.0"
tags: [maya, blend-shape, deformer, morph, facial]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-blend-shape-utils

Blend shape (morph target) management for Maya. Covers creating blend shape deformers,
adding/removing targets, querying and setting target weights, and connecting driver attributes.

## Scripts

- `create_blend_shape` — Create a blend shape deformer on a mesh with one or more target meshes
- `list_blend_shapes` — List all blend shape nodes in the scene or on a specific mesh
- `set_blend_shape_weight` — Set the weight of a blend shape target by index or name
- `get_blend_shape_weights` — Query all target names and their current weights for a blend shape node
