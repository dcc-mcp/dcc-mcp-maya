---
name: maya-asset-sync
description: Consume and publish content-addressed USD revisions with native-editable or fidelity-first Maya modes.
license: MIT
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: interchange
    version: 1.0.0
    tags: [maya, usd, asset-sync, animation-curves, skeleton, materials, lookdev]
    search-hint: "sync asset, Houdini to Maya, editable animation curves, skeleton USD, material sync"
    tools: tools.yaml
---

# maya-asset-sync

Typed cross-DCC revision sync using the shared `dcc-mcp-core.asset_sync` contract.
Filesystem roots are operator-owned environment configuration.

`sync_usd_revision` offers two deliberate editability modes:

- `native`: MayaUSD imports hierarchy, joints, animation as native Maya curves,
  geometry and shader networks for direct editing.
- `usd_proxy`: a `mayaUsdProxyShape` references the immutable layer and retains
  maximum USD composition fidelity for non-destructive layer edits.

The result reports native animCurve, joint, NURBS curve, material, texture and
bounding-box evidence so callers can verify what remained controllable. Native
material evidence also identifies imported Arnold `standardSurface` PBR
materials, their metalness, specular roughness, IOR, transmission, coat, and
connected shader inputs instead of treating a material count as proof of
lookdev fidelity.

Image-texture evidence is path- and color-management-aware. Each bounded
`image_textures` record reports the node and node type, Maya-resolved path and
path attribute, resolved existence, color space, string absoluteness, an
operator-project-relative path when the resolved dependency is under the active
workspace, whether the node came from this import, and any material inputs
reachable through a bounded downstream shading graph. Maya may expand a
portable project path after scene open, so use `under_workspace` and
`workspace_relative_path` rather than treating `is_absolute` alone as a
portability verdict. `file_textures` and
`missing_textures` remain available with their legacy behavior; use
`image_texture_evidence_total`, `image_texture_evidence_limit`, and
`image_texture_evidence_truncated` to audit whether the detailed evidence is
complete.

`rig_expectation` makes rig preservation auditable instead of best-effort:

- `auto` preflights the USD and requires Maya joints whenever a standard
  `UsdSkelSkeleton` is present.
- `skeleton` requires both source `UsdSkel` data and imported Maya joints.
- `skinned` additionally requires authored joint indices/weights and imported
  Maya `skinCluster` nodes.
- `ignore` keeps the legacy permissive behavior for intentionally rigid assets.
