---
name: maya-proxy-mesh
description: Maya proxy mesh management — create, swap, and manage low-res proxy stand-ins
dcc: maya
tags: [proxy, LOD, performance, stand-in, mesh]
version: "1.0.0"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-proxy-mesh

Maya Proxy Mesh skill. Provides actions for creating proxy (stand-in) meshes,
swapping between proxy and high-res geometry, and managing proxy visibility.

## Scripts

- `create_proxy` — Create a low-res proxy mesh from a high-res source object
- `swap_proxy` — Toggle visibility between proxy and high-res mesh
- `list_proxies` — List all proxy mesh pairs tracked by custom attributes
- `set_proxy_attribute` — Set rendering/display attributes on a proxy mesh
