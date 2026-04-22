---
name: maya-attributes
description: Maya node attribute get/set and custom attribute management
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    version: 1.0.0
    tags:
    - maya
    - attribute
    - node
    - utility
    search-hint: attribute, property, value, lock, unlock, set attr
    depends: []
    tools: tools.yaml
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
