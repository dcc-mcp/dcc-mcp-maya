"""Set display or rendering attributes on a proxy mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Union

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def set_proxy_attribute(
    proxy: str,
    attribute: str,
    value: Union[bool, int, float],
) -> dict:
    """Set an attribute on a proxy mesh transform or shape.

    Args:
        proxy: Proxy mesh transform name.
        attribute: Attribute name, e.g. ``"castsShadows"``, ``"receiveShadows"``,
            ``"primaryVisibility"``, ``"overrideEnabled"``, ``"overrideDisplayType"``.
        value: Attribute value (bool, int, or float).

    Returns:
        ActionResultModel dict confirming the change.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, proxy)
        if err:
            return err

        full_attr = "{}.{}".format(proxy, attribute)
        attr_type = cmds.getAttr(full_attr, type=True)
        if attr_type == "bool":
            cmds.setAttr(full_attr, bool(value))
        elif attr_type in ("long", "short", "byte", "enum"):
            cmds.setAttr(full_attr, int(value))
        else:
            cmds.setAttr(full_attr, float(value))

        return skill_success(
            "Set {}.{} = {}".format(proxy, attribute, value),
            prompt="Attribute updated. Check the viewport to see the effect.",
            proxy=proxy,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set attribute '{}.{}'".format(proxy, attribute))


@skill_entry
def main(**kwargs):
    return set_proxy_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
