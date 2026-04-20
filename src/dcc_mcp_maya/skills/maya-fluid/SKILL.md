---
name: maya-fluid
description: Maya fluid (nFluid/legacy fluid container) simulation actions
dcc: maya
tags:
- fluid
- simulation
- dynamics
- nfluid
search-hint: fluid, container, voxel, simulation
version: 1.0.0
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_fluid_container
- name: delete_fluid_container
  destructive_hint: true
  idempotent_hint: true
- name: list_fluid_containers
  read_only_hint: true
  idempotent_hint: true
- name: set_fluid_attribute
  idempotent_hint: true
groups:
- name: simulation-fx
  description: Dynamics, simulation, particles, and VFX tools
  default_active: false
  tools:
  - create_fluid_container
  - delete_fluid_container
  - list_fluid_containers
  - set_fluid_attribute
---
# Maya Fluid Skill

Provides actions for creating and managing Maya fluid containers and nFluid dynamics simulations.
