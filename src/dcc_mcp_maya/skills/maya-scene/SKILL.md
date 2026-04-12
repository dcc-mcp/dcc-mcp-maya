---
name: maya-scene
description: "Maya scene management — create, open, save, list, select and manipulate scene objects"
dcc: maya
version: "1.0.0"
tags: [maya, scene, hierarchy]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
tools:
  - name: new_scene
    description: "Create a new empty Maya scene"
    source_file: scripts/new_scene.py
    read_only: false
    destructive: true
    idempotent: false
  - name: save_scene
    description: "Save the current Maya scene"
    source_file: scripts/save_scene.py
    read_only: false
    destructive: false
    idempotent: true
  - name: open_scene
    description: "Open a Maya scene file from disk"
    source_file: scripts/open_scene.py
    read_only: false
    destructive: true
    idempotent: false
  - name: list_objects
    description: "List objects in the current Maya scene"
    source_file: scripts/list_objects.py
    read_only: true
    destructive: false
    idempotent: true
  - name: get_selection
    description: "Return the current Maya selection"
    source_file: scripts/get_selection.py
    read_only: true
    destructive: false
    idempotent: true
  - name: set_selection
    description: "Set the active Maya selection"
    source_file: scripts/set_selection.py
    read_only: false
    destructive: false
    idempotent: false
  - name: get_scene_info
    description: "Return a hierarchical DAG description of the current scene"
    source_file: scripts/get_scene_info.py
    read_only: true
    destructive: false
    idempotent: true
  - name: get_session_info
    description: "Return Maya version, scene path, and basic session statistics"
    source_file: scripts/get_session_info.py
    read_only: true
    destructive: false
    idempotent: true
---

# maya-scene

Maya scene management skill. Provides actions for creating, opening, saving scenes, listing and selecting objects, managing hierarchy, and querying scene state.

## Scripts

- `new_scene` — Create a new empty Maya scene
- `save_scene` — Save the current Maya scene
- `open_scene` — Open a Maya scene file
- `list_objects` — List objects in the current Maya scene
- `get_selection` — Return the current Maya selection
- `set_selection` — Set the active Maya selection
- `get_session_info` — Return Maya version, scene path, and basic stats
- `group_objects` — Group a list of objects under a new group node
- `parent_object` — Set or clear the parent of an object
- `select_by_type` — Select all objects of a given Maya type
- `duplicate_object` — Duplicate an object in the Maya scene
- `freeze_transforms` — Freeze the transforms of an object
- `center_pivot` — Center the pivot point of an object to its bounding box center
- `get_bounding_box` — Query the world-space bounding box of an object
- `set_visibility` — Show or hide an object
- `lock_object` — Lock or unlock the transform attributes of an object
- `get_scene_info` — Return a hierarchical DAG description of the current scene
- `export_scene` — Export the entire current scene to a file
- `set_frame_rate` — Change the scene's playback frame rate
- `list_cameras` — List all cameras in the scene
- `create_locator` — Create a Maya locator node
