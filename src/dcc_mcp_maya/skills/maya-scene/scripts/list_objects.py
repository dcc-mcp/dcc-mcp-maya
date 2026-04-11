"""List objects in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def list_objects(object_type: Optional[str] = None, dag: bool = True) -> dict:
    """List objects in the current Maya scene.

    Args:
        object_type: Optional Maya type filter (e.g. ``"mesh"``, ``"transform"``).
        dag: If True, only return DAG nodes.

    Returns:
        ActionResultModel dict with ``context.objects`` list.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"dag": dag}
        if object_type:
            kwargs["type"] = object_type
        objects = cmds.ls(**kwargs) or []
        return maya_success(
            f"Found {len(objects)} objects",
            objects=objects,
            count=len(objects),
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list objects")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_objects`."""
    return list_objects(**kwargs)


if __name__ == "__main__":
    import json

    result = list_objects()
    print(json.dumps(result))
