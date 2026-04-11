"""Return a hierarchical DAG description of the current scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def get_scene_info(include_transforms: bool = True) -> dict:
    """Return a hierarchical DAG description of the current scene.

    For each DAG transform node the result includes the node's name, type,
    direct parent and immediate children so callers can reconstruct the full
    hierarchy without additional queries.

    Args:
        include_transforms: If True (default), each node entry also carries its
            world-space translate/rotate/scale values.

    Returns:
        ActionResultModel dict with ``context.nodes`` (list of dicts) and
        ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        transforms = cmds.ls(type="transform", long=True) or []
        nodes = []
        for long_name in transforms:
            short_name = long_name.split("|")[-1]
            node = {
                "name": short_name,
                "long_name": long_name,
                "type": cmds.objectType(long_name),
                "parent": (cmds.listRelatives(long_name, parent=True, fullPath=True) or [None])[0],
                "children": cmds.listRelatives(long_name, children=True, fullPath=True) or [],
            }
            if include_transforms:
                node["translate"] = list(cmds.getAttr("{}.translate".format(long_name))[0])
                node["rotate"] = list(cmds.getAttr("{}.rotate".format(long_name))[0])
                node["scale"] = list(cmds.getAttr("{}.scale".format(long_name))[0])
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
