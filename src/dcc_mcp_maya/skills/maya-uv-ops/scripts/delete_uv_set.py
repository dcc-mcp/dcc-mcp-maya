"""Delete a UV set from a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules

def delete_uv_set(object_name: str, uv_set_name: str) -> dict:
    """Delete a UV set from a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        uv_set_name: Name of the UV set to delete.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name), "'{}' does not exist".format(object_name)
            )

        existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
        if uv_set_name not in existing:
            return maya_error(
                "UV set '{}' not found on '{}'".format(uv_set_name, object_name),
                "Available UV sets: {}".format(existing),
            )

        # Protect the only remaining UV set
        if len(existing) <= 1:
            return maya_error(
                "Cannot delete the only UV set on '{}'".format(object_name), "A mesh must have at least one UV set"
            )

        cmds.polyUVSet(object_name, delete=True, uvSet=uv_set_name)

        return maya_success(
            "Deleted UV set '{}' from '{}'".format(uv_set_name, object_name),
            object_name=object_name,
            uv_set_name=uv_set_name,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to delete UV set")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_uv_set`."""
    return delete_uv_set(**kwargs)

if __name__ == "__main__":
    import json

    result = delete_uv_set()
    print(json.dumps(result))
