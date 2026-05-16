"""List objects in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_objects(object_type: Optional[str] = None, dag: bool = True) -> dict:
    """List objects in the current Maya scene.

    Args:
        object_type: Optional Maya type filter (e.g. ``"mesh"``, ``"transform"``).
        dag: If True, only return DAG nodes.

    Returns:
        ToolResult dict with ``context.objects`` list.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Boolean ``ls`` flags require the Maya UI thread; see get_session_info.
        if object_type:
            objects = cmds.ls(type=object_type) or []
        elif dag:
            objects = cmds.ls(type="transform") or []
        else:
            objects = cmds.ls() or []
        return skill_success(
            f"Found {len(objects)} objects",
            objects=objects,
            count=len(objects),
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list objects")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_objects`."""
    return list_objects(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
