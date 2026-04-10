"""Create a Maya Paint Effects stroke."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def create_stroke(
    brush_path: Optional[str] = None,
    position: Optional[List[float]] = None,
    name: Optional[str] = None,
) -> dict:
    """Create a Paint Effects stroke at a world position using MEL.

    Paint Effects strokes are created via the ``paintEffects`` MEL API.
    ``brush_path`` should be an absolute path to a ``.mel`` brush preset file
    in the Maya brush library (e.g. ``$MAYA_LOCATION/brushes/flowers/roses.mel``).
    If omitted, Maya uses the currently active brush.

    Args:
        brush_path: Full path to a ``.mel`` brush preset (optional).
        position: XYZ world coordinates for the stroke start point. Defaults to [0, 0, 0].
        name: Optional name for the resulting stroke transform.

    Returns:
        ActionResultModel dict with ``context.stroke_node`` and ``context.transform``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    pos = position if position is not None else [0.0, 0.0, 0.0]
    if len(pos) != 3:
        return error_result(
            "Invalid position '{}': must be a list of 3 floats".format(pos),
            "Provide [x, y, z] world coordinates.",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        if brush_path:
            mel.eval('source "{}"'.format(brush_path.replace("\\", "/")))

        # Place a single stroke via MEL at given position
        mel.eval(
            "paintEffectsTool; paint3d -attrSet 1 -pressureAttrX {x} "
            "-pressureAttrY {y} -pressureAttrZ {z};".format(x=pos[0], y=pos[1], z=pos[2])
        )

        # Retrieve newly created stroke nodes
        strokes = cmds.ls(type="stroke") or []
        stroke_node = strokes[-1] if strokes else None

        if not stroke_node:
            return error_result(
                "No stroke node was created",
                "Ensure a valid brush is active or specify brush_path.",
            ).to_dict()

        transform = cmds.listRelatives(stroke_node, parent=True, fullPath=False)
        transform_name = transform[0] if transform else stroke_node

        if name and name != transform_name:
            transform_name = cmds.rename(transform_name, name)
            stroke_node = cmds.listRelatives(transform_name, shapes=True, fullPath=False)
            stroke_node = stroke_node[0] if stroke_node else transform_name

        return success_result(
            "Created Paint Effects stroke '{}'".format(stroke_node),
            prompt=(
                "Stroke created at {}. Use set_brush_attribute to modify appearance, "
                "or convert_stroke_to_poly to get polygon geometry.".format(pos)
            ),
            stroke_node=stroke_node,
            transform=transform_name,
            position=pos,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_stroke failed")
        return error_result("Failed to create stroke", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return create_stroke(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_stroke(position=[0.0, 0.0, 0.0])))
