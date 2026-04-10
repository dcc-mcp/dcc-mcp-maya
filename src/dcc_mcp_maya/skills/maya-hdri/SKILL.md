---
name: maya-hdri
description: "Maya HDRI environment lighting — load HDR images, configure IBL domes, adjust exposure and rotation"
dcc: maya
version: "1.0.0"
tags: [maya, hdri, ibl, lighting, environment]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-hdri

HDRI / Image-Based Lighting (IBL) utilities for Maya. Supports native Maya IBL nodes
and the Arnold aiSkyDomeLight workflow.

## Scripts

- `load_hdri` — Load an HDR image as an IBL environment (Maya IBL or Arnold dome)
- `set_hdri_exposure` — Adjust the exposure of an existing IBL / dome node
- `set_hdri_rotation` — Rotate the HDR environment around the Y axis
- `list_hdri_nodes` — List all IBL / aiSkyDomeLight nodes in the scene
