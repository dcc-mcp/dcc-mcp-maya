"""Delete objects from the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List


# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def delete_objects(object_names: List[str]) -> dict:
    """Delete objects from the Maya scene.

    Args:
        object_names: List of object names to delete.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not object_names:
            return maya_success("No objects to delete")
        existing = cmds.ls(object_names) or []
        if existing:
            cmds.delete(existing)
        return maya_success(
            f"Deleted {len(existing)} objects",
            deleted=existing,
            requested=object_names,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete objects")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_objects`."""
    return delete_objects(**kwargs)

if __name__ == "__main__":
    import json

    result = delete_objects()
    print(json.dumps(result))
