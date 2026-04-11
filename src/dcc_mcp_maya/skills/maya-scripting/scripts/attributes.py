"""Maya generic attribute get/set actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_attribute(
    object_name: str,
    attribute: str,
) -> dict:
    """Get the value of an attribute on a Maya node.

    Supports numeric, string, boolean, and compound (vector/matrix) attributes.

    Args:
        object_name: Name of the Maya node.
        attribute: Attribute name (e.g. ``"translateX"``, ``"visibility"``,
            ``"color"``).

    Returns:
        ActionResultModel dict with ``context.value`` containing the attribute
        value.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        full_attr = "{}.{}".format(object_name, attribute)
        if not cmds.objExists(full_attr):
            return error_result(
                "Attribute not found: {}".format(full_attr),
                "The attribute '{}' does not exist on node '{}'".format(attribute, object_name),
            ).to_dict()

        raw = cmds.getAttr(full_attr)

        # Normalise compound results (list of tuples → flat list)
        if isinstance(raw, list) and raw and isinstance(raw[0], tuple):
            value = list(raw[0])
        else:
            value = raw

        return success_result(
            "Got {}.{} = {}".format(object_name, attribute, value),
            object_name=object_name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_attribute failed")
        return error_result(
            "Failed to get attribute {}.{}".format(object_name, attribute),
            str(exc),
        ).to_dict()


def set_attribute(
    object_name: str,
    attribute: str,
    value: Any,
    force: bool = False,
) -> dict:
    """Set the value of an attribute on a Maya node.

    Supports scalar (int/float/bool), string, and vector (list of 3 floats)
    attributes.  For locked attributes the call will fail unless *force* is
    True.

    Args:
        object_name: Name of the Maya node.
        attribute: Attribute name (e.g. ``"translateX"``, ``"visibility"``).
        value: New value.  Pass a list of 3 floats for compound (vector)
            attributes such as ``"translate"`` or ``"color"``.
        force: If True, temporarily unlock the attribute before setting.
            Default: False.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.attribute``, ``context.value``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        full_attr = "{}.{}".format(object_name, attribute)
        if not cmds.objExists(full_attr):
            return error_result(
                "Attribute not found: {}".format(full_attr),
                "The attribute '{}' does not exist on node '{}'".format(attribute, object_name),
            ).to_dict()

        # Check lock state
        is_locked = cmds.getAttr(full_attr, lock=True)
        if is_locked:
            if not force:
                return error_result(
                    "Attribute is locked: {}".format(full_attr),
                    "Use force=True to unlock and set the attribute",
                ).to_dict()
            cmds.setAttr(full_attr, lock=False)

        # Set value — handle compound (vector) vs scalar vs string
        if isinstance(value, (list, tuple)):
            cmds.setAttr(full_attr, *value)
        elif isinstance(value, str):
            cmds.setAttr(full_attr, value, type="string")
        else:
            cmds.setAttr(full_attr, value)

        # Re-lock if it was locked and force was used
        if is_locked and force:
            cmds.setAttr(full_attr, lock=True)

        return success_result(
            "Set {}.{} = {}".format(object_name, attribute, value),
            object_name=object_name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_attribute failed")
        return error_result(
            "Failed to set attribute {}.{} = {}".format(object_name, attribute, value),
            str(exc),
        ).to_dict()
