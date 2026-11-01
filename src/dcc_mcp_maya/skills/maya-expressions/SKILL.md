---
name: maya-expressions
description: |-
  Authoring stage Maya expression nodes: create, list, delete procedural
  expressions that drive attributes. Use for procedural animation / rig
  logic. Not for keyframe animation (maya-animation) or arbitrary scripting
  (maya-scripting).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: authoring
    version: 1.1.0
    tags:
    - maya
    - expression
    - scripting
    - procedural
    search-hint: |-
      procedural animation, expression node, drive attribute, expression node,
      expression-driven motion, drive translateX with sin
    tools: tools.yaml
    groups: groups.yaml
---
# maya-expressions (Authoring stage)

Lifecycle for Maya expression nodes (`expression` DG nodes). Four small
scripts � kept as a dedicated skill rather than folded into
`maya-scripting` because they have a stable schema and benefit from
typed parameters.

## Scripts

- `create_expression` � Create a Maya expression node
- `list_expressions` � List Maya expression nodes in the scene
- `delete_expression` � Delete a Maya expression node by name
- `get_expression_string` � Read the MEL expression body of a node

## Restricted mode

`create_expression` and `edit_expression` are **code-bearing**: the expression
string is evaluated by Maya and a MEL expression can embed `python(...)`. When
`DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT=1` is set before Maya starts, both tools
return a structured operator-policy refusal before touching the host. This is
an adapter-local tool policy, not a sandbox: read-only tools (`list_expressions`,
`delete_expression`) remain available, and code already present in the session
is out of scope. See `dcc_mcp_maya._code_policy` for the canonical inventory.
