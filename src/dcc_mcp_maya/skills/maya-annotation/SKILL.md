---
name: maya-annotation
description: Maya viewport annotations — create, update, list, and remove text and arrow annotations. Use when adding visual notes and markers in the viewport. Not for scene helpers or locators — use maya-scene-utils for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - annotation
    - viewport
    - text
    search-hint: viewport note, text annotation, arrow marker, visual note
    depends: []
    tools: tools.yaml
---
> **Deprecated (merge bucket):** This skill contains only thin \maya.cmds\ wrappers.
> Use \xecute_python\ with \maya-scripting/references/RECIPES.md#annotation\ instead.
> Will be removed in the next release.

# maya-annotation

Maya annotation skill. Provides actions for creating and managing annotation nodes
(text notes attached to objects or positions in the viewport).

## Scripts

- `create_annotation` — Create a text annotation attached to an object or world position
- `list_annotations` — List all annotation nodes in the scene
- `update_annotation` — Change the text or position of an existing annotation
- `delete_annotation` — Delete an annotation node
