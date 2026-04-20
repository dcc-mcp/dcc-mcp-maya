---
name: maya-grooming
description: Maya XGen / nHair grooming and hair system actions
dcc: maya
tags:
- grooming
- hair
- xgen
- nhair
- dynamics
search-hint: groom, hair, xgen, nhair, follicle
version: 1.0.0
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_nhair_cache
- name: create_nhair_system
- name: list_hair_systems
  read_only_hint: true
  idempotent_hint: true
- name: set_nhair_attribute
  idempotent_hint: true
groups:
- name: simulation-fx
  description: Dynamics, simulation, particles, and VFX tools
  default_active: false
  tools:
  - add_nhair_cache
  - create_nhair_system
  - list_hair_systems
  - set_nhair_attribute
---
# Maya Grooming Skill

Provides actions for creating nHair systems, dynamic curves and managing hair/fur caches.
