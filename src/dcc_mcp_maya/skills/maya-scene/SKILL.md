---
name: maya-scene
description: Maya scene management — create, open, save, list, select and manipulate scene objects
dcc: maya
version: 1.0.0
tags:
- maya
- scene
- hierarchy
search-hint: new scene, open, save, list objects, hierarchy, select
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: center_pivot
- name: create_locator
- name: duplicate_object
- name: export_scene
  read_only_hint: true
  idempotent_hint: true
- name: freeze_transforms
- name: get_bounding_box
  read_only_hint: true
  idempotent_hint: true
- name: get_scene_info
  description: Return a hierarchical DAG description of the current scene
  read_only_hint: true
  idempotent_hint: true
- name: get_selection
  description: Return the current Maya selection
  read_only_hint: true
  idempotent_hint: true
- name: get_session_info
  description: Return Maya version, scene path, and basic session statistics
  read_only_hint: true
  idempotent_hint: true
- name: group_objects
- name: list_cameras
  read_only_hint: true
  idempotent_hint: true
- name: list_objects
  description: List objects in the current Maya scene
  read_only_hint: true
  idempotent_hint: true
- name: lock_object
- name: new_scene
  description: Create a new empty Maya scene
  destructive_hint: true
  idempotent_hint: true
- name: open_scene
  description: Open a Maya scene file from disk
  destructive_hint: true
  idempotent_hint: true
- name: parent_object
- name: save_scene
  description: Save the current Maya scene
- name: select_by_type
- name: set_frame_rate
  idempotent_hint: true
- name: set_selection
  description: Set the active Maya selection
  idempotent_hint: true
- name: set_visibility
  idempotent_hint: true
groups:
- name: scene-management
  description: Scene management, organization, and navigation tools
  default_active: true
  tools:
  - center_pivot
  - create_locator
  - duplicate_object
  - export_scene
  - freeze_transforms
  - get_bounding_box
  - get_scene_info
  - get_selection
  - get_session_info
  - group_objects
  - list_cameras
  - list_objects
  - lock_object
  - new_scene
  - open_scene
  - parent_object
  - save_scene
  - select_by_type
  - set_frame_rate
  - set_selection
  - set_visibility
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
