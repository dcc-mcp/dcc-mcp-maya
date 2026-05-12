# Maya bulk rigid-body spheres → FBX (token-efficient MCP path)

This workflow is optimized for **few MCP round-trips** and **main-thread safety**:

1. **Direct Maya MCP** — Prefer a single `maya_scripting__execute_python` (or equivalent) call that builds geometry, runs your solver (Bullet / Bifrost / etc.), bakes motion if needed, then selects roots for export. Avoid dozens of `create_sphere` tool calls through the wire.
2. **Gateway MCP** — Use `search_tools` → `describe_tool` → `call_tool` once for `execute_python`, or `call_tools` with `calls: [{tool_slug, arguments}, …]` when you must chain **known** slugs (e.g. `load_skill` then `export_fbx`) without extra HTTP round-trips.
3. **Discovery without inflating `tools/list`** — On the Maya adapter, call MCP `dcc_capability_manifest` with `{loaded_only: false}` for a compact index of all actions; set `DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST=1` if your client still pulls a heavy `tools/list`.
4. **FBX contract** — When calling `maya_geometry__export_fbx`, pin **`fbx_version`**, **`bake_animation`**, and **`start_frame` / `end_frame`** for cross-Maya handoff; see `skills/maya-geometry/SKILL.md` § Cross-Maya FBX contract.
5. **cmds documentation** — Read MCP resources `maya-cmds://help/<command>` and `maya-cmds://flags/<command>` (via `resources/read` on the Maya server, or through the gateway with the exact URI returned by `resources/list`).

The snippet below is **illustrative**: adjust solver imports and plugin names for your Maya version.

```python
# Body for execute_python — run on Maya main thread via MCP.
import random
import maya.cmds as cmds
import maya.mel as mel

def main():
    cmds.file(new=True, force=True)
    ground = cmds.polyPlane(width=40, height=40, sx=1, sy=1, name="ground")[0]
    cmds.move(0, -0.55, 0, ground)
    roots = []
    for i in range(10):
        sph = cmds.polySphere(radius=0.35, sx=12, sy=8, name="ball_{}".format(i))[0]
        cmds.move(random.uniform(-4, 4), random.uniform(2, 8), random.uniform(-4, 4), sph)
        roots.append(sph)
    cmds.select(roots, replace=True)
    return {
        "success": True,
        "message": "Created 10 spheres (add Bullet/Bifrost rig + bake here)",
        "context": {"roots": roots},
    }

main()
```

After simulation and bake, call `maya_geometry__export_fbx` with an absolute path and the FBX parameters from the skill contract.
