---
name: maya-attributes
description: |-
  Scene stage — read, write, lock, and create attributes on any Maya node.
  Use whenever you need to query or set an attribute value with a typed,
  validated tool instead of dropping into execute_python. Not for connecting
  attributes (use maya-node-graph) or scripting full procedures (use
  maya-scripting).
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
    - attribute
    - node
    - utility
    search-hint: |-
      get attribute, set attribute, add custom attribute, lock unlock attribute,
      list attributes, attribute value
    depends: []
    tools: tools.yaml
---
# maya-attributes (Scene stage)

Typed wrappers around the most common `maya.cmds` attribute calls
(`getAttr`, `setAttr`, `addAttr`, `deleteAttr`, `listAttr`).

These are kept as a dedicated skill — instead of being folded into
`maya-scripting` — because attribute editing is the single most common
operation an agent performs and it benefits from full `inputSchema`
validation, error classification, and idempotency hints.

## Scripts

- `get_attribute` — Get the value of an attribute on a Maya node
- `set_attribute` — Set the value of an attribute on a Maya node
- `add_attribute` — Add a custom attribute to a Maya node
- `delete_attribute` — Delete a custom (user-defined) attribute from a Maya node
- `list_attributes` — List attributes on a Maya node
