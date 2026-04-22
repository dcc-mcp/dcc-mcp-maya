---
name: maya-cameras
description: Maya camera creation and attribute management — perspective, orthographic, film back, and focal length. Use when setting up viewing cameras for scenes. Not for camera sequencing or shot-based workflows — use maya-camera-sequence or maya-shot-export for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - camera
    - viewport
    - focal
    - film
    search-hint: setup camera, film back, focal length, perspective orthographic
    depends: []
    tools: tools.yaml
    groups: groups.yaml
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
