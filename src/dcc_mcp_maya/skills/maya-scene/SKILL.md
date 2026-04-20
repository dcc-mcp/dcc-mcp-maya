---
name: maya-scene
description: Maya scene management — create, open, save, list, select and manipulate scene objects
dcc: maya
version: 1.0.0
tags:
- maya
- scene
- hierarchy
- open
- save
- manage
search-hint: new scene, open, save, list objects, hierarchy, select
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: center_pivot
  group: scene-management
- name: create_locator
  group: scene-management
- name: duplicate_object
  group: scene-management
- name: export_scene
  group: scene-management
  read_only_hint: true
  idempotent_hint: true
- name: freeze_transforms
  group: scene-management
- name: get_bounding_box
  group: scene-management
  read_only_hint: true
  idempotent_hint: true
- name: get_scene_info
  description: Return a hierarchical DAG description of the current scene
  group: core
  read_only_hint: true
  idempotent_hint: true
- name: get_selection
  description: Return the current Maya selection
  group: core
  read_only_hint: true
  idempotent_hint: true
- name: get_session_info
  description: Return Maya version, scene path, and basic session statistics
  group: core
  read_only_hint: true
  idempotent_hint: true
- name: group_objects
  group: scene-management
- name: list_cameras
  group: scene-management
  read_only_hint: true
  idempotent_hint: true
- name: list_objects
  description: List objects in the current Maya scene
  group: scene-management
  read_only_hint: true
  idempotent_hint: true
- name: lock_object
  group: scene-management
- name: new_scene
  description: Create a new empty Maya scene
  group: scene-management
  destructive_hint: true
  idempotent_hint: true
- name: open_scene
  description: Open a Maya scene file from disk
  group: scene-management
  destructive_hint: true
  idempotent_hint: true
- name: parent_object
  group: scene-management
- name: save_scene
  description: Save the current Maya scene
  group: scene-management
- name: select_by_type
  group: scene-management
- name: set_frame_rate
  group: scene-management
  idempotent_hint: true
- name: set_selection
  description: Set the active Maya selection
  group: scene-management
  idempotent_hint: true
- name: set_visibility
  group: scene-management
  idempotent_hint: true
groups:
- name: core
  description: Core read-only scene queries — always active in minimal mode
  default_active: true
  tools:
  - get_scene_info
  - get_selection
  - get_session_info
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
