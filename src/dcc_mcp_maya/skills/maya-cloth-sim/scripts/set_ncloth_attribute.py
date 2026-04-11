"""Set an attribute on a Maya nCloth shape node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

        err = validate_node_exists(cmds, ncloth_shape)
        if err:
            return err

        cmds.setAttr("{}.{}".format(ncloth_shape, attribute), value)

        return skill_success(
            "nCloth attribute set",
            prompt="nCloth {}.{} = {}. Run simulation to see effect.".format(ncloth_shape, attribute, value),
            ncloth_shape=ncloth_shape,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set nCloth attribute")


@skill_entry
def main(**kwargs):
    return set_ncloth_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
