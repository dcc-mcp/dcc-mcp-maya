---
name: maya-references
description: Maya file reference management — load, unload, replace, and query references with namespace handling. Use when linking external scene files. Not for namespace-only operations or import/export — use maya-namespaces or maya-scene for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - reference
    - namespace
    - scene
    search-hint: link external file, reference scene, unload reference, proxy reference
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
> **Deprecated (merge bucket):** This skill contains only thin \maya.cmds\ wrappers.
> Use \xecute_python\ with \maya-scripting/references/RECIPES.md#references\ instead.
> Will be removed in the next release.

# maya-references

Maya references skill. Provides actions for creating, listing, removing, reloading, and unloading file references, as well as listing namespaces.

## Scripts

- `create_reference` — Reference an external Maya file into the current scene
- `list_references` — List all file references in the current scene
- `remove_reference` — Remove a file reference from the current scene
- `reload_reference` — Reload a previously unloaded (or modified) file reference
- `unload_reference` — Unload a file reference without removing it from the scene
- `list_namespaces` — List all namespaces in the current scene
