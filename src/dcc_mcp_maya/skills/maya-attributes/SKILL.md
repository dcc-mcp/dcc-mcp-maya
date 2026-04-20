---
name: maya-attributes
description: Maya node attribute get/set and custom attribute management
dcc: maya
version: 1.0.0
tags:
- maya
- attribute
- node
- utility
search-hint: attribute, property, value, lock, unlock, set attr
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_attribute
- name: delete_attribute
  destructive_hint: true
  idempotent_hint: true
- name: get_attribute
  read_only_hint: true
  idempotent_hint: true
- name: list_attributes
  read_only_hint: true
  idempotent_hint: true
- name: set_attribute
  idempotent_hint: true
---
# maya-attributes

Maya attributes skill. Provides actions for getting and setting attribute values,
and managing custom attributes on Maya nodes.

## Scripts

- `get_attribute` — Get the value of an attribute on a Maya node
- `set_attribute` — Set the value of an attribute on a Maya node
- `add_attribute` — Add a custom attribute to a Maya node
- `delete_attribute` — Delete a custom (user-defined) attribute from a Maya node
- `list_attributes` — List attributes on a Maya node
