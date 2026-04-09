"""Assign a material to one or more objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List

logger = logging.getLogger(__name__)

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def assign_material(material_name: str, objects: List[str]) -> dict:
    """Assign a material to one or more objects.

    Args:
        material_name: Name of the shading group **or** the material node.
        objects: List of mesh/transform object names.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Accept either SG or material name
        if cmds.objectType(material_name) != "shadingEngine":
            connections = cmds.listConnections(
                "{}.outColor".format(material_name),
                type="shadingEngine",
            )
            if not connections:
                return error_result(
                    "No shading group found for '{}'".format(material_name),
                    "Connect material to a shading group first or use assign_material with the SG name",
                ).to_dict()
            sg = connections[0]
        else:
            sg = material_name

        existing = cmds.ls(objects)
        if not existing:
            return error_result(
                "No objects found",
                "None of the requested objects exist: {}".format(objects),
            ).to_dict()

        cmds.sets(existing, edit=True, forceElement=sg)
        return success_result(
            "Assigned '{}' to {} object(s)".format(sg, len(existing)),
            shading_group=sg,
            objects=existing,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("assign_material failed")
        return error_result("Failed to assign material", str(exc)).to_dict()


def main(**kwargs):
    return assign_material(**kwargs)


if __name__ == "__main__":
    import json

    result = assign_material()
    print(json.dumps(result))
