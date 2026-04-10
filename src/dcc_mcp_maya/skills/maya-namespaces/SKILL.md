---
name: maya-namespaces
description: "Maya namespace management — create, rename, merge, and remove namespaces for asset organization"
dcc: maya
version: "1.0.0"
tags: [maya, namespaces, pipeline, rigging, scene-management]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-namespaces

Namespace utilities for Maya pipeline workflows. Manage asset namespaces for clean
scene organization, referencing, and rigging.

## Scripts

- `create_namespace` — Create a new namespace (optionally nested)
- `list_namespaces` — List all non-default namespaces with object counts
- `rename_namespace` — Rename an existing namespace
- `remove_namespace` — Remove a namespace (merge contents into parent)
