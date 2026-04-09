"""Normalize UV coordinates to fit within the 0-1 UV tile."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def normalize_uvs(
    object_name: str,
    layout_u: float = 1.0,
    layout_v: float = 1.0,
    preserve_aspect: bool = True,
) -> dict:
    """Normalize UV coordinates to fit within the 0-1 UV tile.

    Args:
        object_name: Transform or mesh shape name.
        layout_u: Target U dimension (0 < value <= 1).  Default: 1.0.
        layout_v: Target V dimension (0 < value <= 1).  Default: 1.0.
        preserve_aspect: When True, scale uniformly to preserve aspect ratio.
            Default: True.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not (0 < layout_u <= 1):
        return error_result(
            "Invalid layout_u: {}".format(layout_u),
            "layout_u must be in range (0, 1]",
        ).to_dict()
    if not (0 < layout_v <= 1):
        return error_result(
            "Invalid layout_v: {}".format(layout_v),
            "layout_v must be in range (0, 1]",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        cmds.polyNormalizeUV(
            object_name,
            normalizeType=1,
            preserveAspectRatio=preserve_aspect,
            centerOnTile=True,
            ch=False,
        )

        return success_result(
            "Normalized UVs on '{}' (layout_u={}, layout_v={})".format(object_name, layout_u, layout_v),
            object_name=object_name,
            layout_u=layout_u,
            layout_v=layout_v,
            preserve_aspect=preserve_aspect,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("normalize_uvs failed")
        return error_result("Failed to normalize UVs on '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return normalize_uvs(**kwargs)


if __name__ == "__main__":
    import json

    result = normalize_uvs()
    print(json.dumps(result))
