---
name: maya-proxy-mesh
description: Maya proxy mesh management — create, swap, and manage low-res proxy stand-ins
dcc: maya
tags:
- proxy
- LOD
- performance
- stand-in
- mesh
search-hint: proxy, level of detail, LOD, lightweight
version: 1.0.0
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_proxy
- name: list_proxies
  read_only_hint: true
  idempotent_hint: true
- name: set_proxy_attribute
  idempotent_hint: true
- name: swap_proxy
groups:
- name: modeling
  description: Geometry creation, editing, and UV tools
  default_active: true
  tools:
  - create_proxy
  - list_proxies
  - set_proxy_attribute
  - swap_proxy
---
# maya-proxy-mesh

Maya Proxy Mesh skill. Provides actions for creating proxy (stand-in) meshes,
swapping between proxy and high-res geometry, and managing proxy visibility.

## Scripts

- `create_proxy` — Create a low-res proxy mesh from a high-res source object
- `swap_proxy` — Toggle visibility between proxy and high-res mesh
- `list_proxies` — List all proxy mesh pairs tracked by custom attributes
- `set_proxy_attribute` — Set rendering/display attributes on a proxy mesh
