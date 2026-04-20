---
name: maya-texture-bake
description: Maya texture baking — bake lighting, AO, normals, and custom maps from 3D geometry to texture
dcc: maya
version: 1.0.0
tags:
- maya
- baking
- textures
- ao
- lighting
- normals
search-hint: bake, texture, light map, normal map
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: bake_ambient_occlusion
- name: bake_lighting
- name: bake_textures
- name: list_bake_sets
  read_only_hint: true
  idempotent_hint: true
- name: list_color_spaces
  read_only_hint: true
  idempotent_hint: true
- name: set_color_management
  idempotent_hint: true
- name: transfer_maps
groups:
- name: shading-lighting
  description: Materials, shading, lighting, and environment tools
  default_active: false
  tools:
  - bake_ambient_occlusion
  - bake_lighting
  - bake_textures
  - list_bake_sets
  - list_color_spaces
  - set_color_management
  - transfer_maps
---
# maya-texture-bake

Texture baking utilities for Maya.  Bake lighting, ambient occlusion, normal maps,
and custom shading networks to image textures using Maya's built-in Convert to File
Texture or the Transfer Maps workflow.

## Scripts

- `bake_lighting` — Bake full lighting (diffuse + shadows) to a texture via `convertLightmap`
- `bake_ambient_occlusion` — Bake AO using a `mib_amb_occlusion` shader
- `transfer_maps` — Transfer normals/displacement/diffuse from high-res to low-res mesh
- `list_bake_sets` — List existing bake set nodes in the scene
