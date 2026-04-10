"""Set an attribute on a Maya oceanShader node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any

logger = logging.getLogger(__name__)


def set_ocean_attribute(name: str, attribute: str, value: Any) -> dict:
    """Set an attribute on an oceanShader node.

    Common attributes: ``waveHeight``, ``waveSpeed``, ``waveTurbulence``,
    ``waveLength``, ``waveDirectionSpread``, ``numFrequencies``,
    ``windUV`` (list of 2 floats).

    Args:
        name: Name of the oceanShader node.
        attribute: Attribute name to set.
        value: New value (scalar or list for vector attributes).

    Returns:
        ActionResultModel dict indicating success or failure.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not name:
        return error_result("Missing required parameter 'name'", "Provide the oceanShader node name.").to_dict()
    if not attribute:
        return error_result("Missing required parameter 'attribute'", "Provide the attribute name.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(name):
            return error_result(
                "Node '{}' not found".format(name),
                "Use list_oceans to find valid ocean names.",
            ).to_dict()

        attr_path = "{}.{}".format(name, attribute)
        if isinstance(value, (list, tuple)):
            cmds.setAttr(attr_path, *value)
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set {}.{} = {}".format(name, attribute, value),
            prompt="Attribute updated. Use list_oceans to verify the current state.",
            node=name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_ocean_attribute failed")
        return error_result("Failed to set ocean attribute", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return set_ocean_attribute(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_ocean_attribute(name="oceanShader1", attribute="waveHeight", value=1.5)))
