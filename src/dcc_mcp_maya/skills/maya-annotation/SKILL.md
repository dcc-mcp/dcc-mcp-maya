---
name: maya-annotation
description: Maya viewport annotations — create, update, list and remove text/arrow
  annotation nodes
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    version: 1.0.0
    tags:
    - maya
    - annotation
    - viewport
    - text
    search-hint: annotation, label, text, viewport, note, create annotation
    depends: []
    tools: tools.yaml
---
# maya-annotation

Maya annotation skill. Provides actions for creating and managing annotation nodes
(text notes attached to objects or positions in the viewport).

## Scripts

- `create_annotation` — Create a text annotation attached to an object or world position
- `list_annotations` — List all annotation nodes in the scene
- `update_annotation` — Change the text or position of an existing annotation
- `delete_annotation` — Delete an annotation node
