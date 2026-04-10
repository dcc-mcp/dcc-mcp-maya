"""List available OCIO colour transforms registered in Maya."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Return all colour transform names available in the current Maya session.

    Args:
        params: Dictionary (no required fields).

    Returns:
        ActionResultModel with a list of transform name strings.
    """
    try:
        transforms = cmds.colorManagementPrefs(query=True, renderingSpaceNames=True) or []
        # Also include any view transforms
        try:
            view_transforms = cmds.colorManagementPrefs(query=True, viewTransformNames=True) or []
        except Exception:
            view_transforms = []

        all_transforms = list(transforms) + [
            v for v in view_transforms if v not in transforms
        ]
        return success_result(
            "Found {} colour transforms".format(len(all_transforms)),
            prompt="Use set_color_transform to apply one to a viewport panel.",
            transforms=all_transforms,
            count=len(all_transforms),
        )
    except Exception as exc:
        logger.exception("list_color_transforms failed")
        return error_result("Failed to list colour transforms", str(exc))
