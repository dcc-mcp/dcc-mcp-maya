"""Set the viewport exposure value for a model panel."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Set the exposure (EV offset) on a viewport panel.

    Args:
        params: Dictionary containing:
            - panel (str): Model panel name.  Default 'modelPanel4'.
            - exposure (float): Exposure value (-20.0 – 20.0).  Default 0.0.

    Returns:
        ActionResultModel with panel and exposure applied.
    """
    panel = str(params.get("panel", "modelPanel4")).strip()
    try:
        exposure = float(params.get("exposure", 0.0))
    except (TypeError, ValueError):
        return error_result("Invalid parameters", "'exposure' must be a number.")

    try:
        if not cmds.modelPanel(panel, exists=True):
            return error_result("Panel not found", "No model panel named '{}'.".format(panel))

        cmds.modelEditor(panel, edit=True, exposure=exposure)
        return success_result(
            "Set exposure to {} on panel '{}'".format(exposure, panel),
            prompt="Use set_viewport_gamma or set_color_transform to continue colour grading.",
            panel=panel,
            exposure=exposure,
        )
    except Exception as exc:
        logger.exception("set_viewport_exposure failed")
        return error_result("Failed to set exposure on '{}'".format(panel), str(exc))
