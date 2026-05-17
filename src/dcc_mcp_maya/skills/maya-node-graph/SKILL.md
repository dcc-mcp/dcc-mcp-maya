---
name: maya-node-graph
description: |-
  Scene stage — connect / disconnect attributes, query construction history,
  and inspect DG / DAG topology. Use whenever you reason about how nodes
  drive each other or construction history. Not for attribute *value* edits
  (use maya-attributes), polygon topology cleanup (use maya-mesh-ops), or
  scene file lifecycle (use maya-scene).
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
    - node
    - attribute
    - graph
    - utility
    search-hint: |-
      node connection, attribute link, DG topology, construction history,
      list connections, transfer attributes, smooth subdivide
    depends: []
    tools: tools.yaml
---
# maya-node-graph (Scene stage)

Wires the Maya dependency graph: `connectAttr`, `disconnectAttr`,
`listConnections`, history queries, plus mesh-flavoured graph operations
that are conceptually construction-history / attribute-transfer operations
rather than polygon topology cleanup.

## Scripts

- `connect_attr` — Connect two Maya node attributes
- `disconnect_attr` — Disconnect two connected Maya node attributes
- `list_connections` — List nodes/attributes connected to a Maya node or attribute
- `get_dag_path` — Return the full DAG path of a Maya node
- `smooth_mesh` — Apply construction-history smoothing; use maya-mesh-ops for topology cleanup
- `list_history` — List construction history nodes for a Maya object
- `delete_history` — Delete the construction history on a Maya object
- `apply_symmetry` — Apply mesh symmetry to a polygon object
- `transfer_attributes` — Transfer mesh attributes (UVs, normals, vertex colors) from one mesh to another
