"""Query current colour grading settings from a viewport model panel."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Return gamma, exposure, and colour transform for a viewport panel.

    Args:
        params: Dictionary containing:
            - panel (str): Model panel name.  Default 'modelPanel4'.

    Returns:
        ActionResultModel with gamma, exposure, and color_transform fields.
    """
    panel = str(params.get("panel", "modelPanel4")).strip()

    try:
        if not cmds.modelPanel(panel, exists=True):
            return error_result("Panel not found", "No model panel named '{}'.".format(panel))

        gamma = cmds.modelEditor(panel, query=True, gamma=True)
        exposure = cmds.modelEditor(panel, query=True, exposure=True)
        try:
            color_transform = cmds.modelEditor(panel, query=True, colorTransform=True)
        except Exception:
            color_transform = None

        return success_result(
            "Got colour settings for panel '{}'".format(panel),
            prompt="Use set_viewport_gamma or set_viewport_exposure to adjust.",
            panel=panel,
            gamma=gamma,
            exposure=exposure,
            color_transform=color_transform,
        )
    except Exception as exc:
        logger.exception("get_viewport_color_settings failed")
        return error_result(
            "Failed to get colour settings for panel '{}'".format(panel), str(exc)
        )
