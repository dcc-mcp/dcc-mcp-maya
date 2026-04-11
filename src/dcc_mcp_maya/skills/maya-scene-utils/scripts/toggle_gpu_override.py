"""Toggle the GPU override display mode on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def toggle_gpu_override(
    object_name: str,
    enabled: bool = True,
) -> dict:
    """Toggle the GPU override display mode on a polygon mesh.

    Maya's GPU cache override (``gpuCacheSupportedTypes`` / hardware
    ``displayMode``) is set via the transform's ``overrideDisplayType``
    attribute.  When *enabled* is True the object uses a bounding-box (2)
    display type to hint the GPU path; set False to restore normal (0).

    Note: This is a lightweight approximation for environments without a
    full GPU cache plug-in.  It exposes the ``overrideEnabled`` /
    ``overrideDisplayType`` attributes that are available on every Maya node.

    Args:
        object_name: Transform or shape node name.
        enabled: True to enable GPU override display (bounding box mode),
            False to restore normal display.  Default: True.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.enabled``, ``context.display_type``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        if enabled:
            # 2 = bounding box display type
            cmds.setAttr("{}.overrideEnabled".format(object_name), True)
            cmds.setAttr("{}.overrideDisplayType".format(object_name), 2)
            display_type = 2
        else:
            cmds.setAttr("{}.overrideEnabled".format(object_name), False)
            cmds.setAttr("{}.overrideDisplayType".format(object_name), 0)
            display_type = 0

        return success_result(
            "{} GPU override on '{}'".format("Enabled" if enabled else "Disabled", object_name),
            object_name=object_name,
            enabled=enabled,
            display_type=display_type,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("toggle_gpu_override failed")
        return error_result("Failed to toggle GPU override on '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`toggle_gpu_override`."""
    return toggle_gpu_override(**kwargs)


if __name__ == "__main__":
    import json

    result = toggle_gpu_override()
    print(json.dumps(result))
