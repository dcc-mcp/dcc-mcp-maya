---
name: maya-namespaces
description: Maya namespace management — create, rename, merge, and remove namespaces. Use when organizing scenes with references and name collisions. Not for file referencing itself or scene structure — use maya-references or maya-scene for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - namespaces
    - pipeline
    - rigging
    - scene-management
    search-hint: organize namespaces, resolve name collision, namespace hierarchy
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-namespaces

Namespace utilities for Maya pipeline workflows. Manage asset namespaces for clean
scene organization, referencing, and rigging.

## Scripts

- `create_namespace` — Create a new namespace (optionally nested)
- `list_namespaces` — List all non-default namespaces with object counts
- `rename_namespace` — Rename an existing namespace
- `remove_namespace` — Remove a namespace (merge contents into parent)
