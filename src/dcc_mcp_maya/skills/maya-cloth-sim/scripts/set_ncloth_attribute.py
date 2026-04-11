"""Set an attribute on a Maya nCloth shape node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_ncloth_attribute(ncloth_shape: str, attribute: str, value: float) -> dict:
    """Set a named attribute on an nCloth shape node.

    Args:
        ncloth_shape: Name of the nCloth shape node.
        attribute: Attribute name (e.g. ``'thickness'``, ``'friction'``).
        value: Numeric value to set.

    Returns:
        ActionResultModel dict confirming the attribute change.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(ncloth_shape):
            return error_result(
                "Node not found",
                "nCloth shape '{}' does not exist".format(ncloth_shape),
            ).to_dict()

        cmds.setAttr("{}.{}".format(ncloth_shape, attribute), value)

        return success_result(
            "nCloth attribute set",
            prompt="nCloth {}.{} = {}. Run simulation to see effect.".format(ncloth_shape, attribute, value),
            ncloth_shape=ncloth_shape,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_ncloth_attribute failed")
        return error_result("Failed to set nCloth attribute", str(exc)).to_dict()


def main(**kwargs):
    return set_ncloth_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_ncloth_attribute("nCloth1", "thickness", 0.1)
    print(json.dumps(result))
