"""Set display or rendering attributes on a proxy mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Union


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

        if not cmds.objExists(proxy):
            return maya_error(
                "Proxy mesh '{}' not found".format(proxy),
                "Use list_proxies to see available proxy meshes.",
            )

        full_attr = "{}.{}".format(proxy, attribute)
        attr_type = cmds.getAttr(full_attr, type=True)
        if attr_type == "bool":
            cmds.setAttr(full_attr, bool(value))
        elif attr_type in ("long", "short", "byte", "enum"):
            cmds.setAttr(full_attr, int(value))
        else:
            cmds.setAttr(full_attr, float(value))

        return maya_success(
            "Set {}.{} = {}".format(proxy, attribute, value),
            prompt="Attribute updated. Check the viewport to see the effect.",
            proxy=proxy,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set attribute '{}.{}'".format(proxy, attribute))


def main(**kwargs):
    return set_proxy_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_proxy_attribute("proxy1", "castsShadows", False)
    print(json.dumps(result))
