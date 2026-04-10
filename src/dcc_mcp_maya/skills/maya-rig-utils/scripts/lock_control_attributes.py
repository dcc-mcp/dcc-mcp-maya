"""Lock and hide specified attributes on a rig control."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)

_DEFAULT_ATTRS = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"]


def run(params: Dict[str, object]) -> object:
    """Lock and optionally hide attributes on a rig control transform.

    Args:
        params: Dictionary containing:
            - control (str): Name of the control transform.  Required.
            - attributes (list[str]): Attribute short names to lock.
                                      Default: all translate/rotate/scale/visibility.
            - hide (bool): Also set keyable=False to hide from channel box.
                           Default True.
            - unlock (bool): Unlock instead of locking.  Default False.

    Returns:
        ActionResultModel with locked attribute list.
    """
    control = str(params.get("control", "")).strip()
    raw_attrs = params.get("attributes", None)
    hide = bool(params.get("hide", True))
    unlock = bool(params.get("unlock", False))

    if not control:
        return error_result("Invalid parameters", "'control' is required.")

    if raw_attrs is not None:
        if not isinstance(raw_attrs, (list, tuple)):
            return error_result("Invalid parameters", "'attributes' must be a list.")
        attrs = [str(a) for a in raw_attrs]
    else:
        attrs = list(_DEFAULT_ATTRS)

    try:
        if not cmds.objExists(control):
            return error_result("Control not found", "No node named '{}'.".format(control))

        modified = []
        for attr in attrs:
            full = "{}.{}".format(control, attr)
            if not cmds.attributeQuery(attr, node=control, exists=True):
                continue
            cmds.setAttr(full, lock=not unlock)
            if hide:
                cmds.setAttr(full, keyable=unlock)
            modified.append(attr)

        action = "Unlocked" if unlock else "Locked"
        return success_result(
            "{} {} attributes on control '{}'".format(action, len(modified), control),
            prompt="Use set_control_color to visually distinguish locked controls.",
            control=control,
            attributes=modified,
            unlocked=unlock,
        )
    except Exception as exc:
        logger.exception("lock_control_attributes failed")
        return error_result(
            "Failed to lock/unlock attributes on '{}'".format(control), str(exc)
        )
