"""Set an attribute on a Maya oceanShader node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

        err = validate_node_exists(cmds, shader)
        if err:
            return err

        cmds.setAttr("{}.{}".format(shader, attribute), value)

        return skill_success(
            "Ocean attribute set",
            prompt="Attribute {}.{} = {}. Render or preview to see wave changes.".format(shader, attribute, value),
            shader=shader,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set ocean attribute")


@skill_entry
def main(**kwargs):
    return set_ocean_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
