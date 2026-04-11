"""List all Paint Effects stroke nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules


# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def list_strokes() -> dict:
    """List all Paint Effects stroke nodes in the scene.

    Returns:
        ActionResultModel dict with ``strokes`` list containing name, transform,
        brush node, and visibility for each stroke.
    """

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

        return maya_success(
            "Found {} Paint Effects stroke(s)".format(len(strokes)),
            prompt="Use delete_stroke to remove or attach_stroke_to_surface to add more.",
            strokes=strokes,
            count=len(strokes),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list Paint Effects strokes")


def main(**kwargs):
    return list_strokes(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_strokes()))
