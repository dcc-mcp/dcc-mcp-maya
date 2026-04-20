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
- dangerous
search-hint: script, mel, python, expression, execute
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: animation
  group: extended
- name: attributes
  group: extended
- name: cameras
  group: extended
- name: constraints
  group: extended
- name: deformer_advanced
  group: extended
- name: display
  group: extended
- name: dynamics
  group: extended
- name: execute_mel
  group: core
- name: execute_python
  group: core
- name: expressions
  group: extended
  read_only_hint: true
  idempotent_hint: true
- name: get_script_node
  group: extended
  read_only_hint: true
  idempotent_hint: true
- name: lighting
  group: extended
- name: list_mel_procedures
  group: extended
  read_only_hint: true
  idempotent_hint: true
- name: materials
  group: extended
- name: mesh_ops
  group: extended
- name: namespaces
  group: extended
- name: node_attrs
  group: extended
- name: node_graph
  group: extended
- name: references
  group: extended
- name: render
  group: extended
- name: render_layers
  group: extended
- name: rigging
  group: extended
- name: scene_utils
  group: extended
- name: sets
  group: extended
- name: skin_weights
  group: extended
- name: texture_bake
  group: extended
- name: utility
  group: extended
- name: uv_ops
  group: extended
- name: vertex_color
  group: extended
groups:
- name: core
  description: Core scripting tools — always active in minimal mode
  default_active: true
  tools:
  - execute_mel
  - execute_python
- name: extended
  description: Extended scripting utilities across all domains
  default_active: true
  tools:
  - animation
  - attributes
  - cameras
  - constraints
  - deformer_advanced
  - display
  - dynamics
  - expressions
  - get_script_node
  - lighting
  - list_mel_procedures
  - materials
  - mesh_ops
  - namespaces
  - node_attrs
  - node_graph
  - references
  - render
  - render_layers
  - rigging
  - scene_utils
  - sets
  - skin_weights
  - texture_bake
  - utility
  - uv_ops
  - vertex_color
---
# maya-scripting

Maya scripting skill. Provides actions for executing MEL and Python code inside Maya, plus a broad
set of utility scripts covering animation, attributes, cameras, materials, mesh operations,
rendering, rigging and more.

## Groups

- **core** — Core scripting tools (`execute_mel`, `execute_python`). Active by default in minimal mode.
- **extended** — Broad scripting utilities. Active by default in full mode; deactivated in minimal mode.

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
