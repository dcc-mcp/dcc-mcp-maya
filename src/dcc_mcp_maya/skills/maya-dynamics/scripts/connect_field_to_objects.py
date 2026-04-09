"""Connect an existing dynamic field to particle/nCloth/nParticle objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List

logger = logging.getLogger(__name__)

_VALID_FIELD_TYPES = (
    "gravity",
    "turbulence",
    "radial",
    "uniform",
    "vortex",
    "drag",
    "newton",
    "air",
)

_VALID_MIRROR_AXES = ("x", "y", "z")


def connect_field_to_objects(
    field_node: str,
    objects: List[str],
) -> dict:
    """Connect an existing dynamic field to particle/nCloth/nParticle objects.

    Uses ``cmds.connectDynamic(fields=field_node)`` to wire the field
    forces to the given dynamic objects.

    Args:
        field_node: Name of the existing dynamic field node (or its
            transform).
        objects: List of dynamic object names (particle, nParticle,
            nCloth, nRigid) to receive the field influence.

    Returns:
        ActionResultModel dict with ``context.field_node`` and
        ``context.connected_objects``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not objects:
        return error_result(
            "No objects specified",
            "Provide at least one dynamic object name",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(field_node):
            return error_result(
                "Field node not found: {}".format(field_node),
                "'{}' does not exist in the scene".format(field_node),
            ).to_dict()

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return error_result(
                "Object(s) not found: {}".format(", ".join(missing)),
                "Ensure all objects exist before connecting the field",
            ).to_dict()

        cmds.connectDynamic(objects, fields=field_node)

        return success_result(
            "Connected field '{}' to {} object(s)".format(field_node, len(objects)),
            field_node=field_node,
            connected_objects=list(objects),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("connect_field_to_objects failed")
        return error_result("Failed to connect field '{}' to objects".format(field_node), str(exc)).to_dict()


def main(**kwargs):
    return connect_field_to_objects(**kwargs)


if __name__ == "__main__":
    import json

    result = connect_field_to_objects()
    print(json.dumps(result))
