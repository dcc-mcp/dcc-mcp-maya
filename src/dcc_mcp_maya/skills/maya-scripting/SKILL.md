---
name: maya-scripting
description: Execute MEL and Python scripts inside Maya; broad scripting utilities across the Maya API. Use when automating tasks that lack dedicated tools. Not for specific modeling, animation, or rendering operations — use maya-mesh-ops, maya-animation, or maya-render for those.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - scripting
    - mel
    - python
    - utility
    - dangerous
    search-hint: automate task, run script, MEL Python, custom automation
    depends: []
    tools: tools.yaml
    groups: groups.yaml
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
