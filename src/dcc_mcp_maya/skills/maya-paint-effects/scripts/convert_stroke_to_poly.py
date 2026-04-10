"""Convert a Maya Paint Effects stroke to polygon geometry."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def convert_stroke_to_poly(name: str, quad_output: bool = True) -> dict:
    """Convert a Paint Effects stroke to polygon geometry using MEL.

    Internally calls ``doPaintEffectsToPoly`` which wraps the standard
    ``Modify > Convert > Paint Effects to Polygons`` workflow.

    Args:
        name: Name of the stroke transform or shape to convert.
        quad_output: If True (default), request quad polygon output; otherwise triangles.

    Returns:
        ActionResultModel dict with ``context.poly_mesh`` name.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not name:
        return error_result(
            "Missing required parameter 'name'",
            "Provide the stroke transform or shape name.",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        if not cmds.objExists(name):
            return error_result(
                "Node '{}' not found".format(name),
                "Use list_strokes to find valid stroke names.",
            ).to_dict()

        # Select the stroke transform before conversion
        cmds.select(name, replace=True)

        quad_flag = 1 if quad_output else 0
        mel.eval("doPaintEffectsToPoly(1, 0, 1, {}, 100000)".format(quad_flag))

        # Newly created meshes will appear in selection after conversion
        new_meshes = cmds.ls(selection=True) or []
        poly_mesh = new_meshes[0] if new_meshes else None

        if not poly_mesh:
            return error_result(
                "Conversion produced no mesh",
                "Ensure the stroke has geometry (non-zero brush scale).",
            ).to_dict()

        return success_result(
            "Converted stroke '{}' to polygon mesh '{}'".format(name, poly_mesh),
            prompt=(
                "Polygon mesh created. The original stroke is still present. "
                "Delete the stroke with delete_stroke if it is no longer needed."
            ),
            poly_mesh=poly_mesh,
            source_stroke=name,
            quad_output=quad_output,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("convert_stroke_to_poly failed")
        return error_result("Failed to convert stroke to polygon", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return convert_stroke_to_poly(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(convert_stroke_to_poly(name="stroke1Transform")))
