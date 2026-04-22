---
name: maya-nparticles
description: Maya nParticles — create and configure nParticle systems, set fields, and adjust properties. Use when creating particle effects like smoke, dust, or sparks. Not for fluid dynamics or cloth simulation — use maya-fluid or maya-cloth-sim for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - nparticles
    - dynamics
    - simulation
    - vfx
    search-hint: particle effect, smoke dust sparks, nParticle system
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-nparticles

nParticle system utilities for Maya Nucleus simulations. Creates particle emitters,
attaches fields, configures nucleus solvers, and queries particle counts.

## Scripts

- `create_nparticle_emitter` — Create an nParticle emitter with a nucleus solver
- `set_nparticle_attribute` — Set attributes on an nParticle shape (radius, mass, etc.)
- `add_field_to_nparticles` — Connect a dynamic field (gravity, turbulence) to particles
- `list_nparticle_systems` — List all nParticle and nucleus nodes in the scene
