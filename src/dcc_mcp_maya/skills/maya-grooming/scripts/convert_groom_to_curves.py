"""Convert XGen groom splines to Maya NURBS curves."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def convert_groom_to_curves(
    groom_node: str,
    group_name: Optional[str] = None,
    live: bool = False,
) -> dict:
    """Convert XGen interactive groom splines to NURBS curves.

    Args:
        groom_node: Name of the groom shape or its transform.
        group_name: Optional name for the resulting curves group node.
        live: If ``True``, curves stay live-connected to the groom.

    Returns:
        ActionResultModel dict with ``context.curves_group`` and ``context.curve_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not groom_node:
        return error_result("No groom node specified", "Provide a groom shape or transform name.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(groom_node):
            return error_result(
                "Groom node '{}' does not exist".format(groom_node),
                "Check the node name with list_groomables.",
            ).to_dict()

        convert_kwargs = {"groomToNurbsCurves": True, "live": live}
        result_nodes = cmds.igConvertGroom(groom_node, **convert_kwargs) or []

        # Group resulting curves
        curves = [n for n in result_nodes if cmds.objectType(n) == "nurbsCurve"]
        transforms = [n for n in result_nodes if cmds.objectType(n) == "transform"]
        all_curves = curves + transforms

        group_node = None
        if all_curves:
            g_kwargs = {}
            if group_name:
                g_kwargs["name"] = group_name
            group_node = cmds.group(all_curves, **g_kwargs)

        return success_result(
            "Converted groom '{}' to {} curve(s)".format(groom_node, len(all_curves)),
            prompt=(
                "Curves created under group '{}'. You can now animate, rig, or export them.".format(group_node)
                if group_node
                else "No curves were generated. Check the groom has strands painted."
            ),
            curves_group=group_node,
            curve_count=len(all_curves),
            live=live,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("convert_groom_to_curves failed")
        return error_result("Failed to convert groom to curves", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return convert_groom_to_curves(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(convert_groom_to_curves("groomDescription1")))
