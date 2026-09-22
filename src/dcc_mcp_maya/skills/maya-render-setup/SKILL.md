---
name: maya-render-setup
description: |-
  Pipeline stage - Maya render setup: renderSetup layers, collections and
  overrides, Arnold AOVs, legacy renderLayer nodes, and per-layer / per-AOV
  output path planning for compositing. Use to split a scene into render
  layers, drive per-layer attribute overrides, add or toggle AOVs, and lay
  out the file structure a comp script expects. Not for the actual render or
  export (maya-render / maya-render-farm / maya-shot-export), not for shot
  geometry export (maya-shot-export), and not for colour management or
  renderer image format settings (maya-render).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: pipeline
    version: 1.0.0
    tags:
    - maya
    - render
    - render-setup
    - render-layer
    - collection
    - override
    - aov
    - arnold
    - compositing
    search-hint: |-
      render setup, render layer, renderLayer, renderSetup, current render layer,
      switch render layer, layer collection, collection members, render override,
      absolute override, relative override, connection override, per-layer
      override, AOV, add AOV, list AOVs, enable AOV, disable AOV, remove AOV,
      arnold aov, aiAOV, aovList, multipass, render passes, comp outputs,
      output path template, frame padding, separate AOV folders
    tools: tools.yaml
    groups: groups.yaml
---
# maya-render-setup (Pipeline stage)

Typed wrappers around Maya's render setup surfaces. Three surfaces exist and
they are **not** interchangeable:

- **renderSetup** (`maya.app.renderSetup.model.renderSetup`) — layers,
  collections, overrides. Default for new work and the only switching path
  verified to work.
- **legacy render layers** (`cmds.createRenderLayer` /
  `cmds.editRenderLayerGlobals`) — pre-2017 `renderLayer` nodes. Readable
  always; switching is ignored by Maya in headless sessions, so the tool
  reports that instead of pretending it worked.
- **AOVs** — Arnold `aiAOV` nodes wired into
  `defaultArnoldRenderOptions.aovList`. Arnold-specific and fail-closed when
  the renderer is unavailable.

## Layer workflow

1. `create_render_layer` — name it, set `renderable`, optionally `activate`.
2. `create_render_collection` — populate with `members` (explicit nodes) or
   `pattern` (name glob). Not both.
3. `create_render_override` — override `node.attribute` for everything the
   collection selects. `absolute` sets a value, `relative` offsets it,
   `connection` wires another attribute.
4. `set_current_render_layer` — switch layers before rendering.
5. `plan_comp_outputs` — lay out where the frames should land per layer / AOV.

## AOV workflow

1. `add_aov` — create and wire into `aovList`. Names are unique.
2. `list_aovs` — inspect what is connected and its enabled state.
3. `set_aov_enabled` — skip an AOV for one render without losing it.
4. `remove_aov` — disconnect and delete when it is genuinely done.

Prefer `set_aov_enabled(enabled=false)` over `remove_aov` when the AOV may be
needed later: removal deletes the node and cannot be undone.

## Arnold prerequisites

Two things catch people out, both verified on Maya 2025:

- `defaultArnoldRenderOptions` does **not** exist until an `aiOptions` node is
  created. Setting `defaultRenderGlobals.currentRenderer` to `arnold` is not
  enough. The AOV tools create the node when missing.
- `aovList` reports `size == 0` through `getAttr(s=True)` even when populated,
  so the next free index comes from `listConnections`. The contract does this
  correctly; do not reimplement it.

## Batch / headless caveat

In `maya.standalone`, renderSetup collections are created correctly but
membership queries (`getStaticNames`) return empty because the model relies on
UI evaluation. Creation, overrides and layer switching all work; membership
readback should be trusted in an interactive session.

## Scope

This skill plans and configures. It does not render or export:

- render frames → `maya-render` / `maya-render-farm`
- export shot geometry → `maya-shot-export`
- image format, colour management → `maya-render`

## Scripts

- `add_aov` - Create an Arnold AOV and wire it into the render options output list
- `create_render_collection` - Create a renderSetup collection, or replace an existing collection's members
- `create_render_layer` - Create a renderSetup render layer and optionally make it visible
- `create_render_override` - Override an attribute for everything a renderSetup collection selects
- `list_aovs` - List the AOVs wired into Arnold's render options
- `list_render_layers` - List renderSetup layers, the visible layer, and legacy renderLayer nodes
- `plan_comp_outputs` - Plan per-layer and per-AOV output paths for a compositing hand-off
- `remove_aov` - Disconnect and delete an Arnold AOV
- `set_aov_enabled` - Enable or disable an existing Arnold AOV without disconnecting it
- `set_current_render_layer` - Switch the current render layer (renderSetup or legacy)
