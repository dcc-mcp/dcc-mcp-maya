# Actions API Reference

This page documents the action script interface contract — what every action script must implement to be registered as an MCP tool.

## Action Script Contract

Each `.py` file inside a skill's `scripts/` directory must define a **top-level function with the same name as the file stem**.

### Minimal Example

```python
# scripts/create_sphere.py
"""Create a polygon sphere in the Maya scene."""


def create_sphere(
    name: str = "pSphere1",
    radius: float = 1.0,
    subdivisions_x: int = 20,
    subdivisions_y: int = 20,
    translate: list = None,
) -> dict:
    """Create a polygon sphere.

    Args:
        name: Name for the new sphere.
        radius: Sphere radius in scene units.
        subdivisions_x: Longitude subdivisions.
        subdivisions_y: Latitude subdivisions.
        translate: [x, y, z] position. Defaults to [0, 0, 0].

    Returns:
        dict: ``{"name": str, "success": bool, "message": str}``
    """
    import maya.cmds as cmds

    if translate is None:
        translate = [0.0, 0.0, 0.0]

    sphere, _ = cmds.polySphere(
        name=name,
        radius=radius,
        subdivisionsX=subdivisions_x,
        subdivisionsY=subdivisions_y,
    )
    cmds.move(*translate, sphere)

    return {
        "name": sphere,
        "success": True,
        "message": f"Created sphere '{sphere}' at {translate}",
    }
```

## Naming Convention

| Component | Rule |
|-----------|------|
| File name | `snake_case.py` |
| Function name | Must match file stem exactly |
| MCP tool name | `{skill_name.replace("-","_")}__{script_stem}` |

Example: skill `maya-primitives`, script `create_sphere.py` → MCP tool `maya_primitives__create_sphere`

## Parameter Types

MCP serializes all parameters as JSON. Supported Python type annotations:

| Python Type | JSON | Example |
|-------------|------|---------|
| `str` | string | `"pSphere1"` |
| `int` | number | `20` |
| `float` | number | `1.5` |
| `bool` | boolean | `true` |
| `list` | array | `[0, 1, 0]` |
| `dict` | object | `{"key": "val"}` |
| `Optional[str]` | string or null | `null` |

## Return Value

Actions **must** return a JSON-serializable value. The recommended convention is a `dict` with at minimum:

```python
{
    "success": True,   # or False
    "message": "Human-readable result description",
}
```

Additional fields are passed through to the MCP host as-is.

### Error Handling

Raise a standard Python exception for errors — `dcc-mcp-core` catches it and returns an MCP error response:

```python
def set_keyframe(object_name: str, attribute: str, time: float, value: float) -> dict:
    import maya.cmds as cmds

    if not cmds.objExists(object_name):
        raise ValueError(f"Object '{object_name}' does not exist")

    cmds.setKeyframe(object_name, attribute=attribute, time=time, value=value)
    return {"success": True, "message": f"Keyframe set at time {time}"}
```

## Module-Level Docstring

The module-level docstring (first line) becomes the MCP tool description shown to the AI host:

```python
"""Create a polygon sphere in the Maya scene."""  # ← This becomes the tool description

def create_sphere(...) -> dict:
    ...
```

## Lazy Imports

Always import `maya.cmds` (and other Maya modules) **inside the function**, not at module level. This allows the scripts to be imported and parsed during skill discovery without requiring a running Maya session:

```python
# ✅ Correct
def create_sphere(...):
    import maya.cmds as cmds
    cmds.polySphere(...)

# ❌ Incorrect — fails during discovery outside Maya
import maya.cmds as cmds

def create_sphere(...):
    cmds.polySphere(...)
```

## Complete Example: get_session_info

```python
"""Return Maya version, scene path, and basic session statistics."""


def get_session_info() -> dict:
    """Return Maya version, current scene path, FPS, and object counts.

    Returns:
        dict with keys:
            - maya_version (str): Maya version string, e.g. "2026"
            - scene_path (str): Absolute path to current scene, or "" if unsaved
            - fps (float): Frames per second
            - total_objects (int): Total DAG object count
            - mesh_count (int): Number of polygon meshes
            - camera_count (int): Number of cameras
    """
    import maya.cmds as cmds

    scene_path = cmds.file(query=True, sceneName=True) or ""
    fps_map = {
        "film": 24.0, "pal": 25.0, "ntsc": 30.0,
        "show": 48.0, "palf": 50.0, "ntscf": 60.0,
        "game": 15.0,
    }
    fps_name = cmds.currentUnit(query=True, time=True)
    fps = fps_map.get(fps_name, 24.0)

    all_objects = cmds.ls(dag=True, long=True) or []
    meshes = cmds.ls(type="mesh", long=True) or []
    cameras = cmds.ls(type="camera", long=True) or []

    return {
        "maya_version": cmds.about(version=True),
        "scene_path": scene_path,
        "fps": fps,
        "total_objects": len(all_objects),
        "mesh_count": len(meshes),
        "camera_count": len(cameras),
    }
```
