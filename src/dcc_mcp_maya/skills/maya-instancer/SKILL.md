---
name: maya-instancer
description: Maya instancer utilities — create and configure particle instancers for scattering geometry
dcc: maya
version: 1.0.0
tags:
- maya
- instancer
- particles
- scatter
- motion-graphics
search-hint: instancer, particle instancer, instance, scatter
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_instance_object
- name: create_instancer
- name: list_instancers
  read_only_hint: true
  idempotent_hint: true
- name: set_instancer_attribute
  idempotent_hint: true
groups:
- name: simulation-fx
  description: Dynamics, simulation, particles, and VFX tools
  default_active: false
  tools:
  - add_instance_object
  - create_instancer
  - list_instancers
  - set_instancer_attribute
---
# maya-instancer

Particle instancer tools for Maya. Allows scattering geometry across particle systems,
configuring per-instance attributes, and managing instancer nodes.

## Scripts

- `create_instancer` — Create a particle instancer node linking a particle system to instance geometry
- `add_instance_object` — Add an additional geometry object to an existing instancer
- `set_instancer_attribute` — Configure instancer per-particle attributes (rotation, scale, visibility)
- `list_instancers` — List all instancer nodes and their linked particle systems and geometry
