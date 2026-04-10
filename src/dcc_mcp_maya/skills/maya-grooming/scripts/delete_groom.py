"""Delete an XGen interactive groom description."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_groom(groom_node: str) -> dict:
    """Delete an XGen interactive groom description and its associated nodes.

    Args:
        groom_node: Name of the groom shape or transform node to delete.

    Returns:
        ActionResultModel dict confirming deletion.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not groom_node:
        return error_result("No groom node specified", "Provide the groom shape or transform name.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(groom_node):
            return error_result(
                "Groom node '{}' does not exist".format(groom_node),
                "Check the node name with list_groomables.",
            ).to_dict()

        # Collect the transform if a shape was passed
        node_type = cmds.objectType(groom_node)
        if node_type == "igmGroom":
            parents = cmds.listRelatives(groom_node, parent=True, fullPath=False) or []
            target = parents[0] if parents else groom_node
        else:
            target = groom_node

        cmds.delete(target)

        return success_result(
            "Deleted groom '{}'".format(groom_node),
            prompt="Groom deleted. Use create_groom to add a new one.",
            deleted_node=groom_node,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_groom failed")
        return error_result("Failed to delete groom", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return delete_groom(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_groom("groomDescription1")))
