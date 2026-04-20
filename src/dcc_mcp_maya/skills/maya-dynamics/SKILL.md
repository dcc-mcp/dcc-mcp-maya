---
name: maya-dynamics
description: Maya nDynamics — nucleus, nCloth, nRigid and dynamic fields
dcc: maya
version: 1.0.0
tags:
- maya
- dynamics
- ncloth
- simulation
- effects
search-hint: dynamics, particle, ncloth, fluid, simulation
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: connect_field_to_objects
- name: create_dynamic_field
- name: create_ncloth
- name: create_nrigid
- name: create_nucleus
- name: list_ncloth_nodes
  read_only_hint: true
  idempotent_hint: true
- name: list_nrigid_nodes
  read_only_hint: true
  idempotent_hint: true
- name: set_ncloth_attribute
  idempotent_hint: true
- name: set_nrigid_attribute
  idempotent_hint: true
- name: set_nucleus_attribute
  idempotent_hint: true
groups:
- name: simulation-fx
  description: Dynamics, simulation, particles, and VFX tools
  default_active: false
  tools:
  - connect_field_to_objects
  - create_dynamic_field
  - create_ncloth
  - create_nrigid
  - create_nucleus
  - list_ncloth_nodes
  - list_nrigid_nodes
  - set_ncloth_attribute
  - set_nrigid_attribute
  - set_nucleus_attribute
---
