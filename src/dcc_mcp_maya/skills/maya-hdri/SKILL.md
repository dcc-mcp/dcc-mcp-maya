---
name: maya-hdri
description: Maya HDRI environment lighting — load HDR images, configure IBL domes, adjust exposure and rotation
dcc: maya
version: 1.0.0
tags:
- maya
- hdri
- ibl
- lighting
- environment
search-hint: hdri, ibl, environment, dome light, image based lighting
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: list_hdri_nodes
  read_only_hint: true
  idempotent_hint: true
- name: load_hdri
- name: set_hdri_exposure
  idempotent_hint: true
- name: set_hdri_rotation
  idempotent_hint: true
groups:
- name: shading-lighting
  description: Materials, shading, lighting, and environment tools
  default_active: false
  tools:
  - list_hdri_nodes
  - load_hdri
  - set_hdri_exposure
  - set_hdri_rotation
---
# maya-hdri

HDRI / Image-Based Lighting (IBL) utilities for Maya. Supports native Maya IBL nodes
and the Arnold aiSkyDomeLight workflow.

## Scripts

- `load_hdri` — Load an HDR image as an IBL environment (Maya IBL or Arnold dome)
- `set_hdri_exposure` — Adjust the exposure of an existing IBL / dome node
- `set_hdri_rotation` — Rotate the HDR environment around the Y axis
- `list_hdri_nodes` — List all IBL / aiSkyDomeLight nodes in the scene
