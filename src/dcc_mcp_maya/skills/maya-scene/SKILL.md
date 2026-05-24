---
name: maya-scene
description: |-
  Scene stage — scene file lifecycle and DAG navigation. Use for new / open /
  save scenes, hierarchy queries, selection management, and top-level
  organisation. Not for mesh editing or interchange (FBX/OBJ): use
  maya-mesh-ops or maya-geometry instead.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: scene
    version: 1.1.0
    tags:
    - maya
    - scene
    - hierarchy
    - selection
    - dag
    search-hint: |-
      manage scene file, open save scene, hierarchy query, selection,
      camera list, frame rate, locator, group parent, freeze pivot, bounding box
    tools: tools.yaml
    groups: groups.yaml
---
# maya-scene (Scene stage)

Scene file lifecycle (new / open / save) plus DAG navigation: list,
select, group, parent, freeze, lock, query bounding boxes, list
cameras, set frame rate, etc.

## Groups

- **core** (`default_active: true`) — Read-only scene queries (`get_scene_info`,
  `get_selection`, `get_session_info`). Active in minimal mode.
- **scene-management** (deactivated in minimal mode) — write-side tools:
  open / save / group / parent / set selection, etc. Activate with
  `activate_group("scene-management")` when the agent needs to mutate the
  scene.

## Scripts

- `new_scene` — Create a new empty Maya scene
- `save_scene` — Canonical native .ma/.mb scene save; use maya-geometry for FBX/OBJ interchange
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
- `set_frame_rate` — Change the scene's playback frame rate
- `list_cameras` — List all cameras in the scene
- `create_locator` — Create a Maya locator node
- `find_by_pattern` — Find nodes by Maya wildcard pattern
