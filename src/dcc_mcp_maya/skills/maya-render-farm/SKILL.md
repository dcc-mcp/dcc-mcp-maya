---
name: maya-render-farm
description: |-
  Pipeline stage — render farm integration: validate scenes, write job
  configs, submit to Deadline (or compatible render queues). Use for
  distributed render submission. Not for local renders (maya-render) or
  render layer setup.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: pipeline
    version: 1.1.0
    tags:
    - maya
    - render
    - farm
    - deadline
    - pipeline
    - submission
    search-hint: |-
      submit render job, distributed render, deadline queue, farm submission,
      validate scene for farm, render job spec, render job status
    depends:
    - maya-render
    tools: tools.yaml
    groups: groups.yaml
---
# maya-render-farm (Pipeline stage)

Render farm submission. Layered on top of `maya-render` (which handles
*local* render globals): this skill validates the scene for farm
readiness, writes a JSON job spec, and optionally submits to Deadline
through its Python API.

## Scripts

- `validate_scene_for_farm` — Check scene for missing files, unresolved references, render settings
- `write_render_job` — Write a JSON render job spec for a render farm dispatcher
- `submit_to_deadline` — Submit the current scene to Thinkbox Deadline via the Deadline Python API
- `get_render_job_status` — Query the status of a submitted Deadline job by job ID
