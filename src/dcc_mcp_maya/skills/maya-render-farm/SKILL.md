---
name: maya-render-farm
description: Maya render farm integration — prepare scenes, write render job configs, and submit to deadline queues. Use when sending scenes to distributed render systems. Not for local rendering or render layer setup — use maya-render or maya-render-layers for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - render
    - farm
    - deadline
    - pipeline
    search-hint: submit render job, distributed render, deadline queue, farm submission
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-render-farm

Render farm submission utilities for Maya. Exports job configurations, validates
scenes for farm readiness, and integrates with Deadline or custom render queues.

## Scripts

- `validate_scene_for_farm` — Check scene for missing files, unresolved references, and render settings
- `write_render_job` — Write a JSON render job spec for a render farm dispatcher
- `submit_to_deadline` — Submit the current scene to Thinkbox Deadline via the Deadline Python API
- `get_render_job_status` — Query the status of a submitted Deadline job by job ID
