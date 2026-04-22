---
name: maya-cloth-sim
description: Maya nCloth simulation setup and management — create cloth, set collision, and adjust properties. Use when simulating fabric and garments. Not for rigid-body dynamics or fluid — use maya-dynamics or maya-fluid for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - cloth
    - ncloth
    - simulation
    - dynamics
    search-hint: fabric simulation, garment cloth, nCloth collision
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# Maya Cloth Sim Skill

Provides actions for creating nCloth simulations, setting solver properties and baking cloth cache.
