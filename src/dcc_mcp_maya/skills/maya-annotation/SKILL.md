---
name: maya-annotation
description: Maya viewport annotations — create, update, list and remove text/arrow annotation nodes
dcc: maya
version: 1.0.0
tags:
- maya
- annotation
- viewport
- text
search-hint: annotation, label, text, viewport, note, create annotation
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_annotation
- name: delete_annotation
  destructive_hint: true
  idempotent_hint: true
- name: list_annotations
  read_only_hint: true
  idempotent_hint: true
- name: update_annotation
  idempotent_hint: true
---
# maya-annotation

Maya annotation skill. Provides actions for creating and managing annotation nodes
(text notes attached to objects or positions in the viewport).

## Scripts

- `create_annotation` — Create a text annotation attached to an object or world position
- `list_annotations` — List all annotation nodes in the scene
- `update_annotation` — Change the text or position of an existing annotation
- `delete_annotation` — Delete an annotation node
