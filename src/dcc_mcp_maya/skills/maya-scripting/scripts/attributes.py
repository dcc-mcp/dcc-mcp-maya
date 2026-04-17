"""Maya generic attribute get/set actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Any

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_success

from dcc_mcp_maya.api import validate_node_exists


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
        ToolResult dict with ``context.value`` containing the attribute
        value.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        full_attr = "{}.{}".format(object_name, attribute)
        err = validate_node_exists(cmds, full_attr)
        if err:
            return err

        raw = cmds.getAttr(full_attr)

        # Normalise compound results (list of tuples → flat list)
        if isinstance(raw, list) and raw and isinstance(raw[0], tuple):
            value = list(raw[0])
        else:
            value = raw

        return skill_success(
            "Got {}.{} = {}".format(object_name, attribute, value),
            object_name=object_name,
            attribute=attribute,
            value=value,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_error(
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
        ToolResult dict with ``context.object_name``,
        ``context.attribute``, ``context.value``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        full_attr = "{}.{}".format(object_name, attribute)
        err = validate_node_exists(cmds, full_attr)
        if err:
            return err

        # Check lock state
        is_locked = cmds.getAttr(full_attr, lock=True)
        if is_locked:
            if not force:
                return skill_error(
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

        return skill_success(
            "Set {}.{} = {}".format(object_name, attribute, value),
            object_name=object_name,
            attribute=attribute,
            value=value,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_error(
            "Failed to set attribute {}.{} = {}".format(object_name, attribute, value),
            str(exc),
        )
