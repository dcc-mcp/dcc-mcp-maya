"""Add a Maya Toon outline stroke to objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def create_toon_outline(
    objects: Optional[List[str]] = None,
    line_width: float = 1.0,
    name: Optional[str] = None,
) -> dict:
    """Add a pfxToon outline stroke to the specified objects.

    Args:
        objects: List of mesh/transform names to apply toon outline to.
                 If empty or None, the current selection is used.
        line_width: Initial profile line width (0.0 – 10.0).
        name: Optional name for the pfxToon node.

    Returns:
        ActionResultModel dict with ``context.toon_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        targets = list(objects) if objects else cmds.ls(selection=True) or []

        if targets:
            cmds.select(targets, replace=True)

        # assignNewPfxToon returns the pfxToon transform name
        mel.eval("assignNewPfxToon")

        # Retrieve the newly created pfxToon node
        toon_nodes = cmds.ls(type="pfxToon") or []
        if not toon_nodes:
            return error_result(
                "Failed to create pfxToon node",
                "assignNewPfxToon did not create a pfxToon node.",
            ).to_dict()

        toon_node = toon_nodes[-1]

        if name and name != toon_node:
            toon_node = cmds.rename(toon_node, name)

        cmds.setAttr("{}.profileLineWidth".format(toon_node), line_width)

        return success_result(
            "Created toon outline '{}'".format(toon_node),
            prompt=(
                "Toon outline created on {} object(s). "
                "Use set_toon_attribute to adjust line width/color.".format(len(targets) if targets else "selected")
            ),
            toon_node=toon_node,
            objects=targets,
            line_width=line_width,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_toon_outline failed")
        return error_result("Failed to create toon outline", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return create_toon_outline(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_toon_outline()))
