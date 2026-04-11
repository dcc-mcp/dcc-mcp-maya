"""Adjust the line width of an existing pfxToon node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, toon_node)
        if err:
            return err

        if cmds.objectType(toon_node) != "pfxToon":
            return skill_error(
                "'{}' is not a pfxToon node".format(toon_node),
                "Provide the name of a pfxToon node",
            )

        cmds.setAttr("{}.lineWidth".format(toon_node), line_width)

        applied_profile = None
        if profile_line_width >= 0.0:
            if cmds.attributeQuery("profileLineWidth", node=toon_node, exists=True):
                cmds.setAttr("{}.profileLineWidth".format(toon_node), profile_line_width)
                applied_profile = profile_line_width

        return skill_success(
            "Set line width of '{}' to {}".format(toon_node, line_width),
            prompt="Use list_toon_outlines to inspect all outline nodes.",
            toon_node=toon_node,
            line_width=line_width,
            profile_line_width=applied_profile,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set outline width for '{}'".format(toon_node))


@skill_entry
def main(**kwargs):
    return set_outline_width(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
