"""Set the viewport gamma correction value for a model panel."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Set the gamma correction value on a named viewport panel.

    Args:
        params: Dictionary containing:
            - panel (str): Model panel name.  Default 'modelPanel4'.
            - gamma (float): Gamma value (0.1 – 5.0).  Default 2.2.

    Returns:
        ActionResultModel with panel and gamma applied.
    """
    panel = str(params.get("panel", "modelPanel4")).strip()
    try:
        gamma = float(params.get("gamma", 2.2))
    except (TypeError, ValueError):
        return error_result("Invalid parameters", "'gamma' must be a number.")

    if gamma <= 0:
        return error_result("Invalid parameters", "'gamma' must be > 0.")

    try:
        if not cmds.modelPanel(panel, exists=True):
            return error_result("Panel not found", "No model panel named '{}'.".format(panel))

        cmds.modelEditor(panel, edit=True, gamma=gamma)
        return success_result(
            "Set gamma to {} on panel '{}'".format(gamma, panel),
            prompt="Use set_viewport_exposure to further adjust colour balance.",
            panel=panel,
            gamma=gamma,
        )
    except Exception as exc:
        logger.exception("set_viewport_gamma failed")
        return error_result("Failed to set gamma on '{}'".format(panel), str(exc))
