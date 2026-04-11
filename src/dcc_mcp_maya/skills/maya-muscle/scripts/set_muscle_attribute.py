"""Set a simulation attribute on a Maya Muscle cMuscleObject node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Union

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def set_muscle_attribute(
    muscle_node: str,
    attribute: str,
    value: Union[float, int, bool],
) -> dict:
    """Set an attribute on a cMuscleObject node.

    Args:
        muscle_node: cMuscleObject node name.
        attribute: Attribute name, e.g. ``"stiffness"``, ``"jiggle"``, ``"radius0"``.
        value: New attribute value.

    Returns:
        ActionResultModel dict confirming the change.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(muscle_node):
            return skill_error(
                "Muscle node '{}' not found".format(muscle_node),
                "Use list_muscles to see available nodes.",
            )

        cmds.setAttr("{}.{}".format(muscle_node, attribute), value)

        return skill_success(
            "Set {}.{} = {}".format(muscle_node, attribute, value),
            prompt="Attribute updated. Simulate the scene to see the effect.",
            node=muscle_node,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set attribute '{}'".format(attribute))


@skill_entry
def main(**kwargs):
    return set_muscle_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
