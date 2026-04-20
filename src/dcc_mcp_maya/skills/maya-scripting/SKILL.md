---
name: maya-scripting
description: Execute MEL/Python scripts inside Maya; broad scripting utilities across all domains
dcc: maya
version: 1.0.0
tags:
- maya
- scripting
- mel
- python
- utility
search-hint: script, mel, python, expression, execute
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: animation
- name: attributes
- name: cameras
- name: constraints
- name: deformer_advanced
- name: display
- name: dynamics
- name: execute_mel
- name: execute_python
- name: expressions
- name: get_script_node
  read_only_hint: true
  idempotent_hint: true
- name: lighting
- name: list_mel_procedures
  read_only_hint: true
  idempotent_hint: true
- name: materials
- name: mesh_ops
- name: namespaces
- name: node_attrs
- name: node_graph
- name: references
- name: render
- name: render_layers
- name: rigging
- name: scene_utils
- name: sets
- name: skin_weights
- name: texture_bake
- name: utility
- name: uv_ops
- name: vertex_color
---
# maya-scripting

Maya scripting skill. Provides actions for executing MEL and Python code inside Maya, plus a broad
set of utility scripts covering animation, attributes, cameras, materials, mesh operations,
rendering, rigging and more.

## Scripts

- `execute_mel` — Execute a MEL script inside Maya
- `execute_python` — Execute Python code inside Maya's interpreter
- `animation` — Animation curve and keyframe scripting utilities
- `attributes` — Attribute query and set utilities
- `cameras` — Camera creation and property utilities
- `constraints` — Constraint creation utilities
- `deformer_advanced` — Advanced deformer scripting (blend shapes, clusters, etc.)
- `display` — Viewport display mode and visibility utilities
- `dynamics` — nCloth / nParticle / fluid dynamics utilities
- `expressions` — Maya expression node utilities
- `lighting` — Light creation and property utilities
- `materials` — Material creation, assignment, and shading-network utilities
- `mesh_ops` — Mesh operation utilities (extrude, merge, smooth, etc.)
- `namespaces` — Namespace management utilities
- `node_attrs` — Generic node attribute inspection utilities
- `node_graph` — Node connection and graph traversal utilities
- `references` — File reference management utilities
- `render` — Render settings and playblast utilities
- `render_layers` — Render layer management utilities
- `rigging` — Joint, IK, and skin-weight scripting utilities
- `scene_utils` — Scene file and workspace utilities
- `sets` — Object set management utilities
- `skin_weights` — Skin weight query and export utilities
- `texture_bake` — Texture baking utilities
- `uv_ops` — UV layout and projection utilities
- `utility` — Miscellaneous scene query helpers
- `vertex_color` — Vertex colour paint and query utilities
