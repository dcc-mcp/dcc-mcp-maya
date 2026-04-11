"""Set an attribute on a Maya oceanShader node."""

# Import future modules
from __future__ import annotations

# Import built-in modules


# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def set_ocean_attribute(shader: str, attribute: str, value: float) -> dict:
    """Set an attribute on an oceanShader node.

    Args:
        shader: Name of the oceanShader node.
        attribute: Attribute name (e.g. ``'waveHeight'``, ``'windSpeed'``).
        value: Numeric value to set.

    Returns:
        ActionResultModel dict confirming the attribute change.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(shader):
            return maya_error(
                "Node not found",
                "oceanShader '{}' does not exist".format(shader),
            )

        cmds.setAttr("{}.{}".format(shader, attribute), value)

        return maya_success(
            "Ocean attribute set",
            prompt="Attribute {}.{} = {}. Render or preview to see wave changes.".format(shader, attribute, value),
            shader=shader,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set ocean attribute")

def main(**kwargs):
    return set_ocean_attribute(**kwargs)

if __name__ == "__main__":
    import json

    result = set_ocean_attribute("oceanShader1", "waveHeight", 2.5)
    print(json.dumps(result))
