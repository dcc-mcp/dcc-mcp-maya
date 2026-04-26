---
name: maya-hdri
description: Maya HDRI environment lighting — load HDR images, configure IBL domes, and adjust exposure. Use when setting up image-based ambient lighting. Not for standard light creation or material authoring — use maya-lighting or maya-materials for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - hdri
    - ibl
    - lighting
    - environment
    search-hint: IBL setup, HDRI dome, environment lighting, ambient illumination
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
> **Deprecated (merge bucket):** This skill contains only thin \maya.cmds\ wrappers.
> Use \xecute_python\ with \maya-scripting/references/RECIPES.md#hdri\ instead.
> Will be removed in the next release.

# maya-hdri

HDRI / Image-Based Lighting (IBL) utilities for Maya. Supports native Maya IBL nodes
and the Arnold aiSkyDomeLight workflow.

## Scripts

- `load_hdri` — Load an HDR image as an IBL environment (Maya IBL or Arnold dome)
- `set_hdri_exposure` — Adjust the exposure of an existing IBL / dome node
- `set_hdri_rotation` — Rotate the HDR environment around the Y axis
- `list_hdri_nodes` — List all IBL / aiSkyDomeLight nodes in the scene
