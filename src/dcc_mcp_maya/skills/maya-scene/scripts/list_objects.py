"""List objects in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import make_scene_object


def list_objects(object_type: Optional[str] = None, dag: bool = True, include_transform: bool = False) -> dict:
    """List objects in the current Maya scene.

    Returns :class:`~dcc_mcp_core.SceneObject`-compatible dicts for
    cross-DCC interoperability when *dag* is True.  Non-DAG objects
    are returned as plain name strings.

    Args:
        object_type: Optional Maya type filter (e.g. ``"mesh"``, ``"transform"``).
        dag: If True, only return DAG nodes.
        include_transform: If True and *dag* is True, include
            translate/rotate/scale in each object entry.

    Returns:
        ActionResultModel dict with ``context.objects`` list and
        ``context.count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"dag": dag, "long": dag}
        if object_type:
            kwargs["type"] = object_type
        objects = cmds.ls(**kwargs) or []

        if dag:
            result = []
            for long_name in objects:
                obj = make_scene_object(cmds, long_name, include_transform=include_transform)
                result.append(obj)
        else:
            result = list(objects)

        return skill_success(
            "Found {} objects".format(len(result)),
            objects=result,
            count=len(result),
            prompt="Use get_scene_info for hierarchy or set_transform to modify objects.",
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
