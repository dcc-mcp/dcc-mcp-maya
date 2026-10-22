---
name: maya-texture-bake
description: |-
  Authoring stage — bake lighting, AO, normals, and custom maps from
  high-resolution sources to texture files. Use when generating static
  texture maps for game / render assets. Not for material assignment
  (maya-materials) or UV layout (maya-uv-ops).
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
    - baking
    - textures
    - ao
    - lighting
    - normals
    search-hint: |-
      bake texture map, AO normal, ambient occlusion, high to low res,
      static map, transfer maps, bake lighting
    tools: tools.yaml
    groups: groups.yaml
---
# maya-texture-bake (Authoring stage)

Bake lighting / AO / normals / custom shading networks to image
textures via Maya's bundled bake workflow. All four scripts are
main-thread-affine and CPU-heavy — set realistic `timeout_hint_secs`
in `tools.yaml`.

## Scripts

- `bake_textures` — Sample a mesh's unlit material `baseColor`/`color` network
  into non-empty IFF UV textures using Maya `convertSolidTx`. Each object must
  have one mesh shape, one shading group and one surface material; ambiguous
  assignments fail. `bake_type="diffuse"` means base-color sampling, not an
  Arnold diffuse lighting pass. Arnold RTT, full-render, normals, AO and UDIM
  baking are not implemented by this tool. The legacy `renderer="arnold"`
  argument is retained, but results identify `backend="maya.convertSolidTx"`.
  Renderer and selection are restored; partial failures retain verified files
  and report per-object errors. `overscan` is retained but unused.
- `bake_lighting` — Bake full lighting (diffuse + shadows) to a texture via `convertLightmap`
- `bake_ambient_occlusion` — Bake AO using a `mib_amb_occlusion` shader
- `transfer_maps` — Transfer normals/displacement/diffuse from high-res to low-res mesh
- `list_bake_sets` — List existing bake set nodes in the scene
