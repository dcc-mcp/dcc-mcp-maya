"""Set the value of an attribute on a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def set_attribute(node_name: str, attribute: str, value: object) -> dict:
    """Set the value of an attribute on a Maya node.

    Handles scalar, boolean, string, and simple vector values.

    Args:
        node_name: Name of the Maya node.
        attribute: Attribute name (e.g. ``"translateX"``, ``"visibility"``).
        value: New value.  Strings are set with ``setAttr -type "string"``.

    Returns:
        ActionResultModel dict with ``context.node_name``, ``context.attribute``,
        and ``context.value``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, node_name)
        if err:
            return err

        full_attr = "{}.{}".format(node_name, attribute)
        err = validate_node_exists(cmds, full_attr)
        if err:
            return err

        if isinstance(value, str):
            cmds.setAttr(full_attr, value, type="string")
        elif isinstance(value, (list, tuple)):
            cmds.setAttr(full_attr, *value)
        else:
            cmds.setAttr(full_attr, value)

        return skill_success(
            "Set {}.{} = {}".format(node_name, attribute, value),
            prompt="Use get_attribute to verify the new value.",
            node_name=node_name,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set attribute")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_attribute`."""
    return set_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
