---
name: maya-cameras
description: Maya camera creation and attribute management
dcc: maya
version: 1.0.0
tags:
- maya
- camera
- scene
search-hint: camera, film, focal, persp, orthographic
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_camera
- name: get_camera_info
  read_only_hint: true
  idempotent_hint: true
- name: list_all_cameras
  read_only_hint: true
  idempotent_hint: true
- name: set_active_camera
  idempotent_hint: true
- name: set_camera_attribute
  idempotent_hint: true
groups:
- name: rendering
  description: Render settings, layers, passes, and output tools
  default_active: false
  tools:
  - create_camera
  - get_camera_info
  - list_all_cameras
  - set_active_camera
  - set_camera_attribute
---
# maya-cameras

Maya cameras skill. Provides actions for creating cameras, querying and setting
camera attributes (focal length, clipping, aperture), and activating a camera in
the viewport.

## Scripts

- `create_camera` — Create a new Maya camera with optional position, rotation and focal length
- `set_camera_attribute` — Set a named attribute on a camera node (focalLength, nearClipPlane, etc.)
- `get_camera_info` — Return focal length, clipping, aperture and transform info for a camera
- `set_active_camera` — Set the active viewport camera for a model panel
