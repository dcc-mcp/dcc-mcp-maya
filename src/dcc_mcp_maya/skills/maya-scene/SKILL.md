---
name: maya-scene
description: Maya scene management — create new scenes, open, save, import, export, and list scene contents. Use when managing scene files and top-level hierarchy. Not for individual object creation or mesh editing — use maya-primitives or maya-mesh-ops for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - scene
    - hierarchy
    - open
    - save
    - manage
    search-hint: manage scene file, open save import export, scene hierarchy
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-scene

Maya scene management skill. Provides actions for creating, opening, saving scenes, listing and selecting objects, managing hierarchy, and querying scene state.

## Groups

- **core** — Core read-only scene queries (`get_scene_info`, `get_selection`, `get_session_info`). Active by default in minimal mode.
- **scene-management** — Scene management, organization, and navigation tools. Active by default in full mode; deactivated in minimal mode.

## Scripts

- `new_scene` — Create a new empty Maya scene
- `save_scene` — Save the current Maya scene
- `open_scene` — Open a Maya scene file
- `list_objects` — List objects in the current Maya scene
- `get_selection` — Return the current Maya selection
- `get_scene_info` — Return a hierarchical DAG description of the current scene
- `get_session_info` — Return Maya version, scene path, and basic stats
- `set_selection` — Set the active Maya selection
- `group_objects` — Group a list of objects under a new group node
- `parent_object` — Set or clear the parent of an object
- `select_by_type` — Select all objects of a given Maya type
- `duplicate_object` — Duplicate an object in the Maya scene
- `freeze_transforms` — Freeze the transforms of an object
- `center_pivot` — Center the pivot point of an object to its bounding box center
- `get_bounding_box` — Query the world-space bounding box of an object
- `set_visibility` — Show or hide an object
- `lock_object` — Lock or unlock the transform attributes of an object
- `export_scene` — Export the entire current scene to a file
- `set_frame_rate` — Change the scene's playback frame rate
- `list_cameras` — List all cameras in the scene
- `create_locator` — Create a Maya locator node
