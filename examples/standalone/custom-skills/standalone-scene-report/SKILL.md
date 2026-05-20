---
name: standalone-scene-report
description: |-
  Example headless-safe Maya skill for mayapy / maya.standalone. Creates a
  cube and returns a small scene report without using UI-only commands.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: example
    stage: authoring
    version: 1.0.0
    tags:
    - maya
    - standalone
    - mayapy
    - example
    tools: tools.yaml
---
# standalone-scene-report

Example custom skill for a `mayapy` / `maya.standalone` MCP service.

The script lazy-imports `maya.cmds` inside the callable and declares
`affinity: main`, so `MayaStandaloneDispatcher` serializes access to Maya's
process-global API.
