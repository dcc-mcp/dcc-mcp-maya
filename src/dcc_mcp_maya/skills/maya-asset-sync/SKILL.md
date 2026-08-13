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
