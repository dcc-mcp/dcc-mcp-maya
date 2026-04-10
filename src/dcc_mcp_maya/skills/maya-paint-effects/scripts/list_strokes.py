"""List all Maya Paint Effects stroke nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_strokes() -> dict:
    """List all Paint Effects stroke nodes in the scene.

    Returns:
        ActionResultModel dict with ``context.strokes`` and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        stroke_nodes = cmds.ls(type="stroke") or []
        strokes = []
        for node in stroke_nodes:
            info = {"name": node}
            transform = cmds.listRelatives(node, parent=True, fullPath=False)
            info["transform"] = transform[0] if transform else None
            for attr in ("brush.brushType", "brush.globalScale"):
                try:
                    info[attr.split(".")[-1]] = cmds.getAttr("{}.{}".format(node, attr))
                except Exception:
                    pass
            strokes.append(info)

        return success_result(
            "Found {} stroke(s)".format(len(strokes)),
            prompt=(
                "Use set_brush_attribute to modify stroke properties, "
                "or convert_stroke_to_poly to convert to geometry."
            ),
            strokes=strokes,
            count=len(strokes),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_strokes failed")
        return error_result("Failed to list strokes", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return list_strokes(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_strokes()))
