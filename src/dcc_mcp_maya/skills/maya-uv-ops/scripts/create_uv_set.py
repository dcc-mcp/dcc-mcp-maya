"""Create a new UV set on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional

def create_uv_set(object_name: str, uv_set_name: str, copy_from: Optional[str] = None) -> dict:
    """Create a new UV set on a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        uv_set_name: Name for the new UV set.
        copy_from: Optional existing UV set name to copy UVs from.

    Returns:
        ActionResultModel dict with ``context.uv_set_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error("Object not found: {}".format(object_name))

        existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
        if uv_set_name in existing:
            return maya_error("UV set '{}' already exists on '{}'".format(uv_set_name, object_name))

        if copy_from:
            if copy_from not in existing:
                return maya_error("Source UV set '{}' not found on '{}'".format(copy_from, object_name))
            cmds.polyUVSet(object_name, copy=True, uvSet=copy_from, newUVSet=uv_set_name)
        else:
            cmds.polyUVSet(object_name, create=True, uvSet=uv_set_name)

        return maya_success(
            "Created UV set '{}' on '{}'".format(uv_set_name, object_name),
            object_name=object_name,
            uv_set_name=uv_set_name,
            copied_from=copy_from,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to create UV set")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_uv_set`."""
    return create_uv_set(**kwargs)

if __name__ == "__main__":
    import json

    result = create_uv_set()
    print(json.dumps(result))
