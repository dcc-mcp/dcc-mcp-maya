"""Set a simulation attribute on a Maya Muscle cMuscleObject node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Union

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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
            return maya_error(
                "Muscle node '{}' not found".format(muscle_node),
                "Use list_muscles to see available nodes.",
            )

        cmds.setAttr("{}.{}".format(muscle_node, attribute), value)

        return maya_success(
            "Set {}.{} = {}".format(muscle_node, attribute, value),
            prompt="Attribute updated. Simulate the scene to see the effect.",
            node=muscle_node,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set attribute '{}'".format(attribute))

def main(**kwargs):
    return set_muscle_attribute(**kwargs)

if __name__ == "__main__":
    import json

    result = set_muscle_attribute("cMuscleObject1", "stiffness", 0.5)
    print(json.dumps(result))
