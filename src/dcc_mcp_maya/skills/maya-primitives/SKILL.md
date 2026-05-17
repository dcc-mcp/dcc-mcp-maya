---
name: maya-primitives
description: |-
  Authoring stage — schema-validated quick path for creating polygon
  primitives and editing transforms. Use for predictable, agent-driven
  primitive creation; the parameters are validated by inputSchema and the
  results carry structured object names. For complex mesh editing use
  maya-mesh-ops, for materials use maya-materials, and for arbitrary
  modelling code drop into maya-scripting.
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
    - geometry
    - primitives
    - create
    - transform
    search-hint: |-
      create sphere cube cylinder plane, set transform, get transform, rename,
      delete object, primitive geometry, basic shape, polySphere polyCube,
      batch primitives, random transforms, many cubes procedural
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-primitives (Authoring stage)

Schema-validated quick path for creating polygon primitives and reading /
writing transforms. The eight scripts here are intentionally narrow: they
exist so an agent can do "create N spheres / cubes / cylinders" without
falling back to `execute_python` and losing input validation,
`ToolAnnotations`, and the structured envelope.

## When to use this skill (vs alternatives)

| Goal | Use |
|------|-----|
| Place 10 spheres at scripted positions | **maya-primitives** (schema-validated) |
| Bevel an existing mesh | maya-mesh-ops |
| Build a procedural lattice from scratch | maya-scripting + execute_python |
| Set a custom user attribute | maya-attributes |

## Scripts

- `create_sphere` — Create a polygon sphere
- `create_cube` — Create a polygon cube
- `create_cylinder` — Create a polygon cylinder
- `create_plane` — Create a polygon plane
- `set_transform` — Set translate/rotate/scale on an object
- `get_transform` — Get translate/rotate/scale of an object
- `rename_object` — Rename an object in the scene
- `delete_objects` — Delete objects from the Maya scene
