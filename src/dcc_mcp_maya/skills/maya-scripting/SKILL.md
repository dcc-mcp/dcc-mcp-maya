---
name: maya-scripting
description: "Thin-harness skill — execute arbitrary Maya Python / MEL when no domain skill matches. Prefer this over inventing calls from training-data memory: load it, read RECIPES.md (if available), then call execute_python / execute_mel. Not for high-level pipeline workflows — use maya-shot-export, maya-render-farm, maya-pipeline, maya-scene-assembly for those."
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
    search-hint: fallthrough, no-matching-tool, write-custom, arbitrary-task, automate task, run script, MEL Python, custom automation
    depends: []
    tools: tools.yaml
    groups: groups.yaml
    recipes: references/RECIPES.md
    introspection: references/INTROSPECTION.md
    prompts:
    - name: maya-scripting__fallthrough
      description: "No matching tool found. Consider loading maya-scripting and writing a Python snippet. Search references/RECIPES.md first."
---
# maya-scripting

Thin-harness skill — the **explicit fall-through entry point** when no domain
skill matches a user request.

When an agent cannot find a dedicated tool for a Maya operation, it should
fall back to this skill: load it, read `references/RECIPES.md` (if available),
then call `execute_python` or `execute_mel` to write the call directly.

This follows the [Bitter Lesson](https://sotasync.com/reader/2026-04-24-bitter-lesson-agent-harnesses/):
LLMs have already been trained on the native protocol (`maya.cmds`,
`OpenMaya`, `mel.eval`). Wrapping every API in helpers adds friction; a thin
harness with good error messages lets agents self-heal.

**Decision tree:**

```
Intent matches a domain skill (shot export, render farm, scene assembly)?
  → load that skill.
Intent matches a primitive (create cube, move object, set attr)?
  → load maya-scripting, read RECIPES.md, call execute_python.
Error on a wrapped tool?
  → read _meta.dcc.raw_trace, switch to execute_python with the corrected call.
```

## Groups

- **core** — Core scripting tools (`execute_mel`, `execute_python`). Active by default in both minimal and full mode.
- **introspect** — Maya API introspection tools (`introspect_list_module`, `introspect_signature`, `introspect_search`, `introspect_eval`). Deactivated in minimal mode; load with `activate_group("introspect")` or `load_skill("maya-scripting")`. Consult `references/INTROSPECTION.md` for usage patterns.
- **extended** — Broad scripting utilities. Active by default in full mode; deactivated in minimal mode.

## Scripts

- `execute_mel` — Execute a MEL script inside Maya
- `execute_python` — Execute Python code inside Maya's interpreter
- `introspect_list_module` — List public names in maya.cmds, OpenMaya, or any Python module (paginated)
- `introspect_signature` — Return flag list / method signature for a fully-qualified Maya API name
- `introspect_search` — Case-insensitive search over module names and cmds flag names
- `introspect_eval` — Evaluate a single read-only Python expression inside Maya (main-thread)
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
