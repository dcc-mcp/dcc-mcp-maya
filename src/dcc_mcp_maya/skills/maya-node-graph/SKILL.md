---
name: maya-node-graph
description: Maya node graph operations — connect and disconnect attributes, query construction history and DG topology. Use when working with dependency graph connections. Not for attribute value editing or scene file operations — use maya-attributes or maya-scene for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - node
    - attribute
    - graph
    - utility
    search-hint: node connection, DG topology, construction history, attribute link
    depends: []
    tools: tools.yaml
---
# maya-node-graph

Maya node graph skill. Provides actions for connecting and disconnecting attributes, querying history, and managing mesh topology.

## Scripts

- `connect_attr` — Connect two Maya node attributes
- `disconnect_attr` — Disconnect two connected Maya node attributes
- `list_connections` — List nodes/attributes connected to a Maya node or attribute
- `get_dag_path` — Return the full DAG path of a Maya node
- `smooth_mesh` — Apply smooth mesh preview or subdivision to a polygon mesh
- `list_history` — List construction history nodes for a Maya object
- `delete_history` — Delete the construction history on a Maya object
- `apply_symmetry` — Apply mesh symmetry to a polygon object
- `transfer_attributes` — Transfer mesh attributes (UVs, normals, vertex colors) from one mesh to another
