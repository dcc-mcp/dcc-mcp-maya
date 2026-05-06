# Maya MCP Resources

Issue [#187](https://github.com/loonghao/dcc-mcp-maya/issues/187) wires
`dcc-mcp-maya` into the Rust [`ResourceRegistry`][resource-handle]
shipped by `dcc-mcp-core` 0.15.0.  Out of the box, MCP clients now see:

* **`scene://current`** — JSON snapshot of the live Maya scene
  (`pid`, `dcc`, `scene`, `selection`, `frame`, `frame_range`,
  `up_axis`, `units`, `version`, ...).  Refreshed by Maya `scriptJob`
  events whenever the scene changes; throttled to one publish per
  500 ms to absorb `DagObjectCreated` storms during bulk imports.
* **`maya-cmds://help/<command>`** — `cmds.help(command, language="python")`
  output for any Maya command name.
* **`maya-cmds://flags/<command>`** — flag enumeration via
  `cmds.help(command, flags=True)`.
* **`maya-api://signatures/<class>`** — public-method index for
  `maya.api.OpenMaya` / `OpenMayaAnim` / `OpenMayaUI` classes (e.g.
  `maya-api://signatures/MFnMesh`).
* **`maya-project://current`** — active workspace root + `fileRule`
  table for the running Maya session.

[resource-handle]: https://github.com/loonghao/dcc-mcp-core/blob/main/llms.txt

## Quick check

Once you have `dcc_mcp_maya.start_server()` running, point an MCP
client (Claude Desktop, Cursor, etc.) at the printed URL and watch
the resource surface light up:

```jsonc
// resources/list
{
  "resources": [
    { "uri": "scene://current", "name": "Current Scene", "mimeType": "application/json" },
    { "uri": "capture://current_window", ... },
    { "uri": "audit://recent", ... },
    { "uri": "maya-cmds://", "name": "Python-provided resource (maya-cmds)" },
    { "uri": "maya-api://", "name": "Python-provided resource (maya-api)" },
    { "uri": "maya-project://", "name": "Python-provided resource (maya-project)" }
  ]
}
```

```jsonc
// resources/read scene://current  (after a scene is open)
{
  "contents": [{
    "uri": "scene://current",
    "mimeType": "application/json",
    "text": "{\"available\":true,\"dcc\":\"maya\",\"scene\":\"/projects/foo/scenes/sh_010.ma\",...}"
  }]
}
```

```jsonc
// resources/read maya-cmds://help/polySphere
{
  "contents": [{
    "uri": "maya-cmds://help/polySphere",
    "mimeType": "text/plain",
    "text": "polySphere is undoable, queryable, and editable.\n\nFlags:\n -axis  -ax ..."
  }]
}
```

## Throttling: how `scene://current` stays cheap

Maya's `DagObjectCreated` event fires **once per node** during scene
imports.  Importing a 1000-node character into a clean scene therefore
fires 1000 events back-to-back; without throttling the server would
push 1000 `notifications/resources/updated` SSE frames per import.

The Maya adapter collapses these bursts to **at most one publish per
500 ms** using a lead-edge + trail-edge timer:

| Scenario                       | Publishes (typical)          |
|--------------------------------|------------------------------|
| Single edit (e.g. node rename) | 1 (lead-edge)                |
| 50-node import (50 ms)         | 1 (trail-edge after 500 ms)  |
| 1000-node import (2 s)         | ~5 (one per 500 ms window)   |
| Continuous edit storm          | ~2 per second (steady-state) |

Tune the throttle window (0.5 s default) by passing
`throttle_secs=...` when constructing
[`MayaResourceBinder`](#python-api).

## Configuration

| Variable                       | Default | Effect                                                   |
|--------------------------------|---------|----------------------------------------------------------|
| `DCC_MCP_MAYA_RESOURCES`       | `1`     | Set to `0` to disable Maya resource publishing entirely. |

When disabled, `scene://current` stays at the core default
`{"status": "no_scene_published"}` and the three `maya-*://` schemes
are not registered.  Use this to let an embedding host drive
`scene://current` itself.

## Python API

```python
from dcc_mcp_maya import (
    MayaResourceBinder,    # SOLID composition root
    install_resources,     # one-shot helper
    SCHEME_MAYA_CMDS,
    SCHEME_MAYA_API,
    SCHEME_MAYA_PROJECT,
    DEFAULT_SCENE_EVENTS,  # tuple of scriptJob event names we hook
    DEFAULT_SCENE_THROTTLE_SECS,
)
```

### `install_resources(server, *, snapshot_provider=None, install_scene_events=True, throttle_secs=0.5)`

Called automatically by `MayaMcpServer.register_builtin_actions()`
right after `register_project_tools`.  The default `snapshot_provider`
is the same `MayaContextSnapshotProvider.collect` callable used by the
`/v1/context` REST endpoint, so `scene://current` and `/v1/context`
report identical state.

### `MayaResourceBinder`

The composition root.  Every call into
`server._server.resources()` lives in this class so future schema
migrations are a single-file edit.  Skill scripts and plugin code
**must not** reach into the raw `ResourceHandle`; use the binder via
`MayaMcpServer._resources` if you need to publish ad-hoc updates.

```python
# Force a fresh publish (e.g. after a scripted edit your scriptJob
# events don't catch).
server._resources.publish_scene()                      # uses provider
server._resources.publish_scene({"explicit": "value"}) # bypass provider
```

## Authoring custom producers

Drop-in for skills that want to expose a custom URI scheme.  Create
the producer in your skill module and register it from a startup
hook:

```python
def my_camera_producer(uri: str) -> dict:
    """maya-camera://<camera_name> → JSON description of the camera."""
    name = uri.removeprefix("maya-camera://")
    import maya.cmds as cmds
    return {
        "mimeType": "application/json",
        "text": json.dumps({
            "focal_length": cmds.getAttr(f"{name}.focalLength"),
            "translate":    cmds.getAttr(f"{name}.translate")[0],
        }),
    }

# Register once, after MayaMcpServer.register_builtin_actions:
server._resources.handle.register_producer(
    "maya-camera://", my_camera_producer
)
```

## Prompts (next-tools, examples) — current status

Core 0.15.0 advertises `prompts: {listChanged: true}` and
`prompts/list` returns an empty array.  PR #373 implemented prompt
derivation from SKILL.md `examples` and `workflows`, but the wheel
shipped with 0.15.0 still returns `[]` for adapters that ship those
fields.  When the consumption path is live (0.15.1+), bundled Maya
skills will surface their `examples` automatically — no Maya-side
code change required.

## See also

* [`AGENTS.md`](../../AGENTS.md) — overview of the SOLID binder
  pattern (`ReadinessBinder`, `ProjectToolsIntegration`,
  `MayaResourceBinder`).
* [`docs/guide/scene.md`](./scene.md) — the existing scene-info tool
  surface, which now mirrors `scene://current`.
