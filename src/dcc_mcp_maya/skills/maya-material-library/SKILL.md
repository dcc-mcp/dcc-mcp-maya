---
name: maya-material-library
description: |-
  Authoring stage — save / load / manage reusable material presets as JSON
  side-files. Use for cross-shot or cross-asset shader reuse. Not for
  building a one-off material on the fly (use maya-materials) or final
  rendering (use maya-render).
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
    - materials
    - library
    - shading
    - presets
    search-hint: |-
      reuse material, material preset, shader library, share material,
      load preset, save preset, JSON shader
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-material-library (Authoring stage)

Save, load, list, and delete JSON material presets. Lives next to
`maya-materials` so the agent decision tree is clear:

| Goal | Use |
|------|-----|
| Build a fresh shader and assign it | maya-materials |
| Save a shader for reuse later | **maya-material-library** |
| Reapply a saved look-dev preset | **maya-material-library** |

## Scripts

- `save_material` — Serialize a material and its attributes to a JSON preset file
- `load_material` — Recreate a material from a JSON preset and assign it optionally
- `list_material_presets` — List all preset files in a material library directory
- `delete_material_preset` — Remove a material preset file from the library
