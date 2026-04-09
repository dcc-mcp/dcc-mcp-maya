---
name: maya-node-graph
description: "Maya node graph — connect/disconnect attributes, query history and topology"
dcc: maya
version: "1.0.0"
tags: [maya, node, attribute, graph, utility]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
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
