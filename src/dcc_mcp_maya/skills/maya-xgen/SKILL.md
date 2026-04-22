---
name: maya-xgen
description: Maya XGen hair and fur operations — create, list, preview, and manage XGen descriptions. Use when generating hair, fur, or feather grooms. Not for nHair dynamics or general grooming — use maya-grooming or maya-dynamics for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - xgen
    - hair
    - fur
    - grooming
    search-hint: hair fur generation, XGen description, groom hair
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-xgen

Maya XGen skill. Provides actions for creating and managing XGen hair/fur descriptions,
controlling groom modifiers, and querying XGen collections.

## Scripts

- `create_description` — Create an XGen description on a mesh
- `list_descriptions` — List all XGen descriptions in the scene
- `delete_description` — Delete an XGen description
- `set_xgen_attribute` — Set an attribute on an XGen description or modifier
- `get_xgen_attribute` — Get an attribute value from an XGen description
