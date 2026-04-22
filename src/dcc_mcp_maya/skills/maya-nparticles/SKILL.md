---
name: maya-nparticles
description: Maya nParticles — create and configure nParticle systems, set fields,
  and query simulation state
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    version: 1.0.0
    tags:
    - maya
    - nparticles
    - dynamics
    - simulation
    - vfx
    search-hint: nparticle, particle, dynamics, simulation
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
