---
name: maya-render-farm
description: Maya render farm — prepare scenes, write render job configs, and submit
  to local or Deadline render queues
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    version: 1.0.0
    tags:
    - maya
    - render
    - farm
    - deadline
    - pipeline
    search-hint: render farm, deadline, batch, submit
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
