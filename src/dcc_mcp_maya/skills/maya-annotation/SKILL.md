---
name: maya-annotation
<<<<<<< HEAD
description: "Maya annotation node listing and management"
dcc: maya
version: "1.0.0"
tags: [maya, annotation, viewport, label]
=======
description: "Maya viewport annotations — create, update, list and remove text/arrow annotation nodes"
dcc: maya
version: "1.0.0"
tags: [maya, annotation, viewport, text]
>>>>>>> origin/main
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-annotation

<<<<<<< HEAD
Maya annotation skill. Provides actions for querying annotation nodes in Maya.

## Scripts

- `list_annotations` — List all annotation nodes in the scene with their text and transform info
=======
Maya annotation skill. Provides actions for creating and managing annotation nodes
(text notes attached to objects or positions in the viewport).

## Scripts

- `create_annotation` — Create a text annotation attached to an object or world position
- `list_annotations` — List all annotation nodes in the scene
- `update_annotation` — Change the text or position of an existing annotation
- `delete_annotation` — Delete an annotation node
>>>>>>> origin/main
