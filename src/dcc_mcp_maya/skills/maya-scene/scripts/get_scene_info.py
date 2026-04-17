"""Return a hierarchical DAG description of the current scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import object_transform_from_node, scene_object_from_node


def get_scene_info(include_transforms: bool = True) -> dict:
    """Return a hierarchical DAG description of the current scene.

    For each DAG transform node the result includes the node's name, type,
    direct parent and immediate children so callers can reconstruct the full
    hierarchy without additional queries.

    Uses :func:`dcc_mcp_maya.api.scene_object_from_node` and
    :func:`dcc_mcp_maya.api.object_transform_from_node` to produce
    ``SceneObject``- and ``ObjectTransform``-compatible dicts for
    cross-DCC interoperability.

    Args:
        include_transforms: If True (default), each node entry also carries its
            world-space translate/rotate/scale values via ``ObjectTransform``
            schema.

    Returns:
        ToolResult dict with ``context.nodes`` (list of dicts) and
        ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        transforms = cmds.ls(type="transform", long=True) or []
        nodes = []
        for long_name in transforms:
            node = scene_object_from_node(cmds, long_name)
            node["children"] = cmds.listRelatives(long_name, children=True, fullPath=True) or []
            if include_transforms:
                try:
                    xform = object_transform_from_node(cmds, long_name)
                    node["translate"] = xform["translate"]
                    node["rotate"] = xform["rotate"]
                    node["scale"] = xform["scale"]
                except Exception:
                    pass
            nodes.append(node)

        return skill_success(
            "Scene info: {} transform node(s)".format(len(nodes)),
            nodes=nodes,
            count=len(nodes),
            prompt="Use set_transform or assign_material to modify listed objects.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get scene info")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_scene_info`."""
    return get_scene_info(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
