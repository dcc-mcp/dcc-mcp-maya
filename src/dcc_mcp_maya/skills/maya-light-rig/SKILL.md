---
name: maya-light-rig
description: Maya light rig — create standard three-point lighting rigs, HDRI dome setups, and manage light groups
dcc: maya
version: 1.0.0
tags:
- maya
- lighting
- light-rig
- three-point
- hdri
search-hint: light, rig, three-point, studio setup
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_hdri_dome
- name: create_three_point_rig
- name: list_light_rigs
  read_only_hint: true
  idempotent_hint: true
- name: set_light_rig_intensity
  idempotent_hint: true
groups:
- name: shading-lighting
  description: Materials, shading, lighting, and environment tools
  default_active: false
  tools:
  - create_hdri_dome
  - create_three_point_rig
  - list_light_rigs
  - set_light_rig_intensity
---
# maya-light-rig

Light rig creation and management for Maya. Provides standard lighting setups
such as three-point rigs and HDRI dome lights for rapid scene illumination.

## Scripts

- `create_three_point_rig` — Create a standard key/fill/rim three-point light rig
- `create_hdri_dome` — Create a skydome/environment light from an HDR image
- `list_light_rigs` — List all lights grouped under rig transform nodes
- `set_light_rig_intensity` — Scale intensity of all lights within a named rig
