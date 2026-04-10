"""Set an attribute on a Maya Muscle cMuscleObject node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

# Common muscle attributes and their descriptions
_MUSCLE_ATTRS = {
    "radius": "Capsule cross-section radius",
    "squash": "Squash multiplier (0–2)",
    "stretch": "Stretch multiplier (0–2)",
    "rest": "Rest length override (0 = auto)",
    "maxSquash": "Maximum squash limit",
    "maxStretch": "Maximum stretch limit",
}


def set_muscle_attribute(muscle_node: str, attribute: str, value: object) -> dict:
    """Set an attribute on a cMuscleObject node.

    Args:
        muscle_node: Name of the cMuscleObject shape or its transform.
        attribute: Attribute name (e.g. ``radius``, ``squash``, ``stretch``).
        value: New attribute value (numeric).

    Returns:
        ActionResultModel dict confirming the change.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not muscle_node or not attribute:
        return error_result(
            "muscle_node and attribute are required",
            "Provide the muscle node name and attribute.",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(muscle_node):
            return error_result(
                "Muscle node '{}' does not exist".format(muscle_node),
                "Check the node name with list_muscles.",
            ).to_dict()

        full_attr = "{}.{}".format(muscle_node, attribute)
        if not cmds.attributeQuery(attribute, node=muscle_node, exists=True):
            return error_result(
                "Attribute '{}' does not exist on '{}'".format(attribute, muscle_node),
                "Common attributes: {}".format(", ".join(_MUSCLE_ATTRS.keys())),
            ).to_dict()

        cmds.setAttr(full_attr, value)

        return success_result(
            "Set {}.{} = {}".format(muscle_node, attribute, value),
            prompt="Attribute updated. Simulate to see the effect on the skin mesh.",
            node=muscle_node,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_muscle_attribute failed")
        return error_result("Failed to set muscle attribute", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return set_muscle_attribute(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_muscle_attribute("cMuscleObject1", "radius", 1.5)))
