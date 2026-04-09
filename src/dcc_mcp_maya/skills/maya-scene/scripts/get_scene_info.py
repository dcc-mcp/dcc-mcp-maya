"""Return a hierarchical DAG description of the current scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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

        return success_result(
            "Scene info: {} transform node(s)".format(len(nodes)),
            nodes=nodes,
            count=len(nodes),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_scene_info failed")
        return error_result("Failed to get scene info", str(exc)).to_dict()


def main(**kwargs):
    return get_scene_info(**kwargs)


if __name__ == "__main__":
    import json

    result = get_scene_info()
    print(json.dumps(result))
