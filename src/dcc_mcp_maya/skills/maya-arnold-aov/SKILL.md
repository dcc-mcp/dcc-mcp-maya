---
name: maya-arnold-aov
description: Arnold AOV (Arbitrary Output Variable) management for multi-pass rendering
dcc: maya
tags:
- arnold
- aov
- render
- passes
search-hint: arnold, aov, render pass, beauty, lighting
version: 1.0.0
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_aov
- name: delete_aov
  destructive_hint: true
  idempotent_hint: true
- name: enable_aov
  idempotent_hint: true
- name: list_aovs
  read_only_hint: true
  idempotent_hint: true
- name: set_aov_attribute
  idempotent_hint: true
groups:
- name: rendering
  description: Render settings, layers, passes, and output tools
  default_active: false
  tools:
  - add_aov
  - delete_aov
  - enable_aov
  - list_aovs
  - set_aov_attribute
---
# Maya Arnold AOV Skill

Provides Arnold AOV creation, listing, deletion, and attribute management.
Supports standard AOV types (beauty, diffuse, specular, Z, N, P, etc.) and custom AOVs.

## Scripts

- `add_aov` — Add a new Arnold AOV to the render settings
- `list_aovs` — List all existing Arnold AOVs
- `delete_aov` — Delete an Arnold AOV by name
- `set_aov_attribute` — Set an attribute on an Arnold AOV node
- `enable_aov` — Enable or disable an Arnold AOV
