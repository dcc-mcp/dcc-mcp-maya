"""Set display or rendering attributes on a proxy mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Union

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(proxy):
            return error_result(
                "Proxy mesh '{}' not found".format(proxy),
                "Use list_proxies to see available proxy meshes.",
            ).to_dict()

        full_attr = "{}.{}".format(proxy, attribute)
        attr_type = cmds.getAttr(full_attr, type=True)
        if attr_type == "bool":
            cmds.setAttr(full_attr, bool(value))
        elif attr_type in ("long", "short", "byte", "enum"):
            cmds.setAttr(full_attr, int(value))
        else:
            cmds.setAttr(full_attr, float(value))

        return success_result(
            "Set {}.{} = {}".format(proxy, attribute, value),
            prompt="Attribute updated. Check the viewport to see the effect.",
            proxy=proxy,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_proxy_attribute failed")
        return error_result("Failed to set attribute '{}.{}'".format(proxy, attribute), str(exc)).to_dict()


def main(**kwargs):
    return set_proxy_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_proxy_attribute("proxy1", "castsShadows", False)
    print(json.dumps(result))
