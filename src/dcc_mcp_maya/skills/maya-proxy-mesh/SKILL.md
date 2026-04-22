---
name: maya-proxy-mesh
description: Maya proxy mesh management — create, swap, and manage low-res proxy stand-ins. Use when working with level-of-detail workflows. Not for full scene assembly or rendering — use maya-scene-assembly or maya-render for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - proxy
    - lod
    - performance
    - mesh
    search-hint: LOD proxy, low res stand-in, level of detail, swap proxy
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-proxy-mesh

Maya Proxy Mesh skill. Provides actions for creating proxy (stand-in) meshes,
swapping between proxy and high-res geometry, and managing proxy visibility.

## Scripts

- `create_proxy` — Create a low-res proxy mesh from a high-res source object
- `swap_proxy` — Toggle visibility between proxy and high-res mesh
- `list_proxies` — List all proxy mesh pairs tracked by custom attributes
- `set_proxy_attribute` — Set rendering/display attributes on a proxy mesh
