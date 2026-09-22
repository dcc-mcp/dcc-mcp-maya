---
name: maya-particles
description: |-
  Authoring stage - Maya particle systems: nParticle and classic particle
  creation, emitters (omni, directional, surface, curve, volume), particle
  look and physics attributes, and geometry instancing. Use for particle
  effects such as dust, sparks, rain and debris. Not for cloth or rigid body
  simulation (maya-dynamics), Bifrost volumetric work (maya-bifrost), or
  keyframe editing (maya-animation).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: authoring
    version: 1.0.0
    tags:
    - maya
    - particles
    - nparticle
    - emitter
    - instancer
    - vfx
    - simulation
    search-hint: |-
      nParticle, particle system, particle, emitter, point emitter, volume emitter,
      surface emitter, curve emitter, emit particles, rate, speed, spread,
      lifespan, particle render type, spheres, sprites, blobby, cloud, streak,
      instancer, instance geometry onto particles, particle instancer,
      rotationPP, cycle sequential debris variation
    tools: tools.yaml
    groups: groups.yaml
---
# maya-particles (Authoring stage)

Typed wrappers around Maya's particle commands. Both particle families are
covered:

- **nParticle** (`kind="nparticle"`) — Nucleus-driven, collides with nCloth /
  nRigid, cachable. The right default for new work.
- **classic particles** (`kind="classic"`) — legacy `particle` nodes, kept for
  compatibility with older rigs and MEL scripts.

## Particle workflow

1. `create_particle_system` — pick `kind`, set `lifespan`, `lifespan_mode` and
   `particle_render_type` up front.
2. `create_emitter` — choose `emitter_type`; pass `targets` to connect it in
   one call, or omit and connect later.
3. `set_emitter_properties` — tune `rate`, `speed`, `speed_random`, `spread`.
4. `set_particle_properties` — tune the look: `radius`, `opacity`,
   `particle_render_type`, and physics: `conserve`, `drag`, `mass`, `bounce`.
5. `create_particle_instancer` — replace point rendering with real geometry.
   Use `cycle="sequential"` with several source objects for debris variation.
   Maya's `-cycle` only accepts `none` or `sequential`; `random` is rejected.
6. Collide with the world via `maya-dynamics create_nrigid`, then cache with
   `maya-dynamics create_ncache`.

## Scale note

nParticle inherits the Nucleus solver's `space_scale`. If particles look like
they are moving through treacle, check `maya-dynamics set_nucleus_properties`
before touching any emitter value.

## Scripts

- `create_particle_system` - Create an nParticle or classic particle system
- `create_emitter` - Create an omni / directional / surface / curve / volume emitter
- `create_particle_instancer` - Instance source geometry onto a particle system
- `list_particles` - List particle systems, emitters and instancers
- `set_emitter_properties` - Edit rate, speed, spread and other emitter attributes
- `set_particle_properties` - Edit particle look and physics attributes
