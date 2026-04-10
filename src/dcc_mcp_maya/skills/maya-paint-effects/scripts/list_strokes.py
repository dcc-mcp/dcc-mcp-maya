"""List all Paint Effects stroke nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_strokes() -> dict:
    """List all Paint Effects stroke nodes in the scene.

    Returns:
        ActionResultModel dict with ``strokes`` list containing name, transform,
        brush node, and visibility for each stroke.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        stroke_nodes = cmds.ls(type="stroke") or []
        strokes = []
        for sn in stroke_nodes:
            info = {"stroke_node": sn, "transform": "", "brush_node": "", "visibility": True}
            parents = cmds.listRelatives(sn, parent=True) or []
            if parents:
                info["transform"] = parents[0]
                try:
                    info["visibility"] = bool(cmds.getAttr("{}.visibility".format(parents[0])))
                except Exception:
                    pass

            # Linked brush node via brush attribute
            try:
                brush_conn = cmds.listConnections("{}.brush".format(sn), type="brush") or []
                info["brush_node"] = brush_conn[0] if brush_conn else ""
            except Exception:
                pass

            strokes.append(info)

        return success_result(
            "Found {} Paint Effects stroke(s)".format(len(strokes)),
            prompt="Use delete_stroke to remove or attach_stroke_to_surface to add more.",
            strokes=strokes,
            count=len(strokes),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_strokes failed")
        return error_result("Failed to list Paint Effects strokes", str(exc)).to_dict()


def main(**kwargs):
    return list_strokes(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_strokes()))
