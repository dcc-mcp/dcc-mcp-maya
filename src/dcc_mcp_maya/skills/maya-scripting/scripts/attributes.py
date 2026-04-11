"""Maya generic attribute get/set actions."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_success

# Import built-in modules
from typing import Any


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        full_attr = "{}.{}".format(object_name, attribute)
        if not cmds.objExists(full_attr):
            return maya_error(
                "Attribute not found: {}".format(full_attr),
                "The attribute '{}' does not exist on node '{}'".format(attribute, object_name),
            )

        raw = cmds.getAttr(full_attr)

        # Normalise compound results (list of tuples → flat list)
        if isinstance(raw, list) and raw and isinstance(raw[0], tuple):
            value = list(raw[0])
        else:
            value = raw

        return maya_success(
            "Got {}.{} = {}".format(object_name, attribute, value),
            object_name=object_name,
            attribute=attribute,
            value=value,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_error(
            "Failed to get attribute {}.{}".format(object_name, attribute),
            str(exc),
        )


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        full_attr = "{}.{}".format(object_name, attribute)
        if not cmds.objExists(full_attr):
            return maya_error(
                "Attribute not found: {}".format(full_attr),
                "The attribute '{}' does not exist on node '{}'".format(attribute, object_name),
            )

        # Check lock state
        is_locked = cmds.getAttr(full_attr, lock=True)
        if is_locked:
            if not force:
                return maya_error(
                    "Attribute is locked: {}".format(full_attr),
                    "Use force=True to unlock and set the attribute",
                )
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

        return maya_success(
            "Set {}.{} = {}".format(object_name, attribute, value),
            object_name=object_name,
            attribute=attribute,
            value=value,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_error(
            "Failed to set attribute {}.{} = {}".format(object_name, attribute, value),
            str(exc),
        )
