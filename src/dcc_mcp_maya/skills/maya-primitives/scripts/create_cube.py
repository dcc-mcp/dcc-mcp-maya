"""Create a polygon cube."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional


# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def create_cube(
    width: float = 1.0,
    height: float = 1.0,
    depth: float = 1.0,
    name: Optional[str] = None,
) -> dict:
    """Create a polygon cube.

    Args:
        width: Cube width. Default: 1.0.
        height: Cube height. Default: 1.0.
        depth: Cube depth. Default: 1.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.polyCube(width=width, height=height, depth=depth)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return maya_success(
            f"Created cube: {obj}",
            object_name=obj,
            width=width,
            height=height,
            depth=depth,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create cube")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_cube`."""
    return create_cube(**kwargs)

if __name__ == "__main__":
    import json

    result = create_cube()
    print(json.dumps(result))
