"""Adjust the line width of an existing pfxToon node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_outline_width(
    toon_node: str,
    line_width: float,
    profile_line_width: float = -1.0,
) -> dict:
    """Set the line width of a pfxToon outline node.

    Args:
        toon_node: Name of the ``pfxToon`` node to modify.
        line_width: New stroke width (world-space units).
        profile_line_width: Width for profile/silhouette lines.  If ``-1``
            (default) it is left unchanged.

    Returns:
        ActionResultModel dict confirming the new values.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(toon_node):
            return error_result(
                "pfxToon node '{}' not found".format(toon_node),
                "Use list_toon_outlines to find available nodes",
            ).to_dict()

        if cmds.objectType(toon_node) != "pfxToon":
            return error_result(
                "'{}' is not a pfxToon node".format(toon_node),
                "Provide the name of a pfxToon node",
            ).to_dict()

        cmds.setAttr("{}.lineWidth".format(toon_node), line_width)

        applied_profile = None
        if profile_line_width >= 0.0:
            if cmds.attributeQuery("profileLineWidth", node=toon_node, exists=True):
                cmds.setAttr("{}.profileLineWidth".format(toon_node), profile_line_width)
                applied_profile = profile_line_width

        return success_result(
            "Set line width of '{}' to {}".format(toon_node, line_width),
            prompt="Use list_toon_outlines to inspect all outline nodes.",
            toon_node=toon_node,
            line_width=line_width,
            profile_line_width=applied_profile,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_outline_width failed")
        return error_result("Failed to set outline width for '{}'".format(toon_node), str(exc)).to_dict()


def main(**kwargs):
    return set_outline_width(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_outline_width("pfxToon1", 2.5)))
