"""Set an attribute on a Maya nCloth shape node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def set_ncloth_attribute(ncloth_shape: str, attribute: str, value: float) -> dict:
    """Set a named attribute on an nCloth shape node.

    Args:
        ncloth_shape: Name of the nCloth shape node.
        attribute: Attribute name (e.g. ``'thickness'``, ``'friction'``).
        value: Numeric value to set.

    Returns:
        ActionResultModel dict confirming the attribute change.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(ncloth_shape):
            return maya_error(
                "Node not found",
                "nCloth shape '{}' does not exist".format(ncloth_shape),
            )

        cmds.setAttr("{}.{}".format(ncloth_shape, attribute), value)

        return maya_success(
            "nCloth attribute set",
            prompt="nCloth {}.{} = {}. Run simulation to see effect.".format(ncloth_shape, attribute, value),
            ncloth_shape=ncloth_shape,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set nCloth attribute")


def main(**kwargs):
    return set_ncloth_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_ncloth_attribute("nCloth1", "thickness", 0.1)
    print(json.dumps(result))
