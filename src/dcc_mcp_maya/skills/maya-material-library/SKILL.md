---
name: maya-material-library
description: |-
  Authoring stage — save / load reusable material presets and bind, reload,
  or repath bounded local texture maps. Use for cross-shot look reuse and
  typed Designer-to-Maya texture handoff. For one-off shader CRUD use
  maya-materials; for final rendering use maya-render.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: authoring
    version: 1.2.0
    tags:
    - maya
    - materials
    - library
    - shading
    - presets
    - textures
    - udim
    search-hint: |-
      reuse material, material preset, shader library, share material,
      load preset, save preset, JSON shader, assign texture, bind map,
      reload texture, repath texture, Designer maps, UDIM
    tools: tools.yaml
    groups: groups.yaml
---
# maya-material-library (Authoring stage)

Save, load, list, and delete JSON material presets, and manage explicit local
texture bindings. Lives next to
`maya-materials` so the agent decision tree is clear:

| Goal | Use |
|------|-----|
| Build a fresh shader and assign it | maya-materials |
| Save a shader for reuse later | **maya-material-library** |
| Reapply a saved look-dev preset | **maya-material-library** |
| Bind Designer-authored base-color / roughness / normal maps | **maya-material-library** |
| Reload regenerated maps or move them between roots | **maya-material-library** |

`assign_texture` is the typed degraded path when an external Painter workflow
is unavailable. It supports bounded local files and
up to 256 `<UDIM>` tiles, rejects occupied material slots, applies `sRGB` to
base color and `Raw` to data maps, and verifies the native Maya graph. Each
call binds one explicit slot so failures remain attributable and recoverable.

`reload_textures` accepts at most 64 explicit Maya file nodes. It reissues the
native path and returns aggregate size / mtime evidence for the concrete file
or UDIM set; this proves which regenerated disk payload Maya was asked to
reload, not subjective render correctness.

`repath_textures` preserves paths relative to explicit old/new roots,
prevalidates every destination, reads back every native write, and rolls the
whole bounded batch back on partial failure.

Arnold render-to-texture migration and subjective/visual validation remain in
the wider rendering and Core verification tracks; these tools do not claim
that a rendered frame is visually correct.

## Scripts

- `save_material` — Serialize a material and its attributes to a JSON preset file
- `load_material` — Recreate a material from a JSON preset and assign it optionally
- `list_material_presets` — List all preset files in a material library directory
- `delete_material_preset` — Remove a material preset file from the library
- `assign_texture` — Bind one base-color, roughness, or normal map to `aiStandardSurface` with color-space, UDIM, graph, and path readback
- `reload_textures` — Reissue up to 64 explicit file-node paths and return bounded disk evidence
- `repath_textures` — Transactionally move up to 64 texture paths between explicit roots
