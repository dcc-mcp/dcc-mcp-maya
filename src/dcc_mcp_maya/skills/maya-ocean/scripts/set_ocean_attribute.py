"""Set an attribute on a Maya oceanShader node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_ocean_attribute(shader: str, attribute: str, value: float) -> dict:
    """Set an attribute on an oceanShader node.

    Args:
        shader: Name of the oceanShader node.
        attribute: Attribute name (e.g. ``'waveHeight'``, ``'windSpeed'``).
        value: Numeric value to set.

    Returns:
        ActionResultModel dict confirming the attribute change.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(shader):
            return error_result(
                "Node not found",
                "oceanShader '{}' does not exist".format(shader),
            ).to_dict()

        cmds.setAttr("{}.{}".format(shader, attribute), value)

        return success_result(
            "Ocean attribute set",
            prompt="Attribute {}.{} = {}. Render or preview to see wave changes.".format(shader, attribute, value),
            shader=shader,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_ocean_attribute failed")
        return error_result("Failed to set ocean attribute", str(exc)).to_dict()


def main(**kwargs):
    return set_ocean_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_ocean_attribute("oceanShader1", "waveHeight", 2.5)
    print(json.dumps(result))
