---
name: maya-ocean
description: Maya ocean (Bifrost/Maya Ocean shader) surface simulation actions
dcc: maya
tags:
- ocean
- fluid
- simulation
- environment
search-hint: ocean, water, wave, fluid, simulation
version: 1.0.0
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_ocean_wake
- name: create_ocean
- name: list_ocean_surfaces
  read_only_hint: true
  idempotent_hint: true
- name: set_ocean_attribute
  idempotent_hint: true
groups:
- name: simulation-fx
  description: Dynamics, simulation, particles, and VFX tools
  default_active: false
  tools:
  - add_ocean_wake
  - create_ocean
  - list_ocean_surfaces
  - set_ocean_attribute
---
# Maya Ocean Skill

Provides actions for creating and configuring Maya ocean surfaces, wake effects and foam.
