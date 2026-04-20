---
name: maya-cloth-sim
description: Maya nCloth simulation setup and management actions
dcc: maya
tags:
- cloth
- ncloth
- simulation
- dynamics
search-hint: cloth, ncloth, simulation, fabric, collision
version: 1.0.0
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: bake_cloth_cache
- name: create_ncloth
- name: list_ncloth_objects
  read_only_hint: true
  idempotent_hint: true
- name: set_ncloth_attribute
  idempotent_hint: true
groups:
- name: simulation-fx
  description: Dynamics, simulation, particles, and VFX tools
  default_active: false
  tools:
  - bake_cloth_cache
  - create_ncloth
  - list_ncloth_objects
  - set_ncloth_attribute
---
# Maya Cloth Sim Skill

Provides actions for creating nCloth simulations, setting solver properties and baking cloth cache.
