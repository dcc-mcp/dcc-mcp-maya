"""Set a simulation attribute on a Maya Muscle cMuscleObject node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Union

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(muscle_node):
            return error_result(
                "Muscle node '{}' not found".format(muscle_node),
                "Use list_muscles to see available nodes.",
            ).to_dict()

        cmds.setAttr("{}.{}".format(muscle_node, attribute), value)

        return success_result(
            "Set {}.{} = {}".format(muscle_node, attribute, value),
            prompt="Attribute updated. Simulate the scene to see the effect.",
            node=muscle_node,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_muscle_attribute failed")
        return error_result("Failed to set attribute '{}'".format(attribute), str(exc)).to_dict()


def main(**kwargs):
    return set_muscle_attribute(**kwargs)


if __name__ == "__main__":
    import json
    result = set_muscle_attribute("cMuscleObject1", "stiffness", 0.5)
    print(json.dumps(result))
