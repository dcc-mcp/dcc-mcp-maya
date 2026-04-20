---
name: maya-nparticles
description: Maya nParticles — create and configure nParticle systems, set fields, and query simulation state
dcc: maya
version: 1.0.0
tags:
- maya
- nparticles
- dynamics
- simulation
- vfx
search-hint: nparticle, particle, dynamics, simulation
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_field_to_nparticles
- name: create_nparticle_emitter
- name: list_nparticle_systems
  read_only_hint: true
  idempotent_hint: true
- name: set_nparticle_attribute
  idempotent_hint: true
groups:
- name: simulation-fx
  description: Dynamics, simulation, particles, and VFX tools
  default_active: false
  tools:
  - add_field_to_nparticles
  - create_nparticle_emitter
  - list_nparticle_systems
  - set_nparticle_attribute
---
# maya-nparticles

nParticle system utilities for Maya Nucleus simulations. Creates particle emitters,
attaches fields, configures nucleus solvers, and queries particle counts.

## Scripts

- `create_nparticle_emitter` — Create an nParticle emitter with a nucleus solver
- `set_nparticle_attribute` — Set attributes on an nParticle shape (radius, mass, etc.)
- `add_field_to_nparticles` — Connect a dynamic field (gravity, turbulence) to particles
- `list_nparticle_systems` — List all nParticle and nucleus nodes in the scene
