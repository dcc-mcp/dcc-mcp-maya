"""Set the colour transform (OCIO view transform) for a viewport panel."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Assign an OCIO view transform to a model panel.

    Args:
        params: Dictionary containing:
            - panel (str): Model panel name.  Default 'modelPanel4'.
            - transform (str): Colour transform name (e.g. 'sRGB gamma',
                               'Linear', 'Raw').  Required.

    Returns:
        ActionResultModel with panel and transform applied.
    """
    panel = str(params.get("panel", "modelPanel4")).strip()
    transform = str(params.get("transform", "")).strip()

    if not transform:
        return error_result("Invalid parameters", "'transform' is required.")

    try:
        if not cmds.modelPanel(panel, exists=True):
            return error_result("Panel not found", "No model panel named '{}'.".format(panel))

        cmds.modelEditor(panel, edit=True, colorTransform=transform)
        return success_result(
            "Set colour transform '{}' on panel '{}'".format(transform, panel),
            prompt="Use list_color_transforms to see all available transforms.",
            panel=panel,
            transform=transform,
        )
    except Exception as exc:
        logger.exception("set_color_transform failed")
        return error_result(
            "Failed to set colour transform on '{}'".format(panel), str(exc)
        )
