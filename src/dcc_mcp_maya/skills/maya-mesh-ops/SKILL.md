---
name: maya-mesh-ops
description: Maya polygon mesh operations — subdivision, cleanup, boolean, UV-based selection and proxy generation
dcc: maya
version: 1.0.0
tags:
- maya
- mesh
- polygon
- geometry
- topology
search-hint: mesh, bevel, bridge, extrude, combine, separate
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: apply_subdivision
  idempotent_hint: true
- name: cleanup_mesh
- name: combine_meshes
- name: create_proxy_mesh
- name: extract_faces
- name: get_mesh_edge_info
  read_only_hint: true
  idempotent_hint: true
- name: get_poly_count
  read_only_hint: true
  idempotent_hint: true
- name: merge_vertices
- name: mirror_mesh
- name: select_by_material
- name: separate_mesh
- name: triangulate
groups:
- name: modeling
  description: Geometry creation, editing, and UV tools
  default_active: true
  tools:
  - apply_subdivision
  - cleanup_mesh
  - combine_meshes
  - create_proxy_mesh
  - extract_faces
  - get_mesh_edge_info
  - get_poly_count
  - merge_vertices
  - mirror_mesh
  - select_by_material
  - separate_mesh
  - triangulate
---
