"""Set an attribute on a MASH node."""

# Import future modules
from __future__ import annotations

from typing import Any

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def set_mash_attribute(
    node: str,
    attribute: str,
    value: Any,
) -> dict:
    """Set an attribute value on a MASH node.

    Args:
        node: MASH node name.
        attribute: Attribute name (e.g. "amplitudeX", "pointCount").
        value: New value (numeric or string).

    Returns:
        ActionResultModel dict.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, node)
        if err:
            return err

        attr_path = "{}.{}".format(node, attribute)
        cmds.setAttr(attr_path, value)
        return skill_success(
            "Set {}.{} = {}".format(node, attribute, value),
            prompt="Render or playback to see MASH network changes.",
            node=node,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(
            exc,
            message="Failed to set MASH attribute",
            prompt="Check attribute name spelling and value type.",
        )


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_mash_attribute`."""
    return set_mash_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
