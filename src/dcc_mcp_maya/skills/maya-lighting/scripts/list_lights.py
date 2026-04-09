"""List all lights in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Supported Maya light types and their corresponding command/node names
_LIGHT_TYPE_MAP = {
    "point": "pointLight",
    "spot": "spotLight",
    "directional": "directionalLight",
    "area": "areaLight",
    "ambient": "ambientLight",
}


def list_lights(include_default: bool = False) -> dict:
    """List all lights in the current Maya scene.

    Args:
        include_default: If True, include the ``defaultLight`` which Maya creates
            internally.  Default: False.

    Returns:
        ActionResultModel dict with ``context.lights`` list of dicts containing
        ``name``, ``shape``, ``light_type``, ``intensity``, ``color``,
        ``visible``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        light_shapes = cmds.ls(type="light") or []
        # Also catch spotLight / pointLight / directionalLight / areaLight by hierarchy
        for extra_type in ("spotLight", "pointLight", "directionalLight", "areaLight", "ambientLight"):
            extra = cmds.ls(type=extra_type) or []
            for node in extra:
                if node not in light_shapes:
                    light_shapes.append(node)

        results = []
        for shape in light_shapes:
            if not include_default and shape == "defaultLight":
                continue
            transform_list = cmds.listRelatives(shape, parent=True) or [shape]
            transform = transform_list[0]
            try:
                intensity = cmds.getAttr("{}.intensity".format(shape))
            except Exception:
                intensity = None
            try:
                color_raw = cmds.getAttr("{}.color".format(shape))
                color = list(color_raw[0]) if color_raw else None
            except Exception:
                color = None
            try:
                visible = bool(cmds.getAttr("{}.visibility".format(transform)))
            except Exception:
                visible = True
            results.append(
                {
                    "name": transform,
                    "shape": shape,
                    "light_type": cmds.objectType(shape),
                    "intensity": intensity,
                    "color": color,
                    "visible": visible,
                }
            )

        return success_result(
            "Found {} light(s)".format(len(results)),
            lights=results,
            count=len(results),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_lights failed")
        return error_result("Failed to list lights", str(exc)).to_dict()



def main(**kwargs):
    return list_lights(**kwargs)


if __name__ == "__main__":
    import json
    result = list_lights()
    print(json.dumps(result))
