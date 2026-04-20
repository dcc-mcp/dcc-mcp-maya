---
name: maya-deformers
description: Maya advanced deformers — cluster, lattice, wire, sculpt and deformer stack management
dcc: maya
version: 1.0.0
tags:
- maya
- deformer
- rigging
- cluster
- lattice
search-hint: deformer, bend, twist, lattice, nonlinear
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: apply_subdivision
  idempotent_hint: true
- name: cleanup_mesh
- name: create_cluster
- name: create_lattice
- name: sculpt_deformer
- name: set_cluster_weights
  idempotent_hint: true
- name: wire_deformer
groups:
- name: rigging
  description: Rigging, deformation, and skinning tools
  default_active: false
  tools:
  - apply_subdivision
  - cleanup_mesh
  - create_cluster
  - create_lattice
  - sculpt_deformer
  - set_cluster_weights
  - wire_deformer
---
